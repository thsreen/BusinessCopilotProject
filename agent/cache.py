"""
In-memory LRU response cache keyed by (prompt_variant, user_input, store_version).

Purpose:
  Avoid re-generating LLM responses for identical or near-identical queries
  within a configurable time-to-live (TTL). This reduces latency and saves
  API calls when the agent is asked the same question repeatedly.

Architecture:
  - Cache keys are SHA-256 hashes of ``{prompt_variant}:::{normalised_input}:::{store_version}``.
  - The store version is derived from the set of indexed filenames in the
    Chroma DB directory. Whenever the document store is re-indexed, the
    version changes and the cache is effectively invalidated.
  - Internally uses an ``OrderedDict`` for O(1) LRU eviction: on every hit
    the entry is moved to the end; when capacity is exceeded the oldest
    entry (front of the dict) is popped.
  - Thread-safe within a single process because all access is GIL-protected;
    cross-process safety is not required (each process has its own cache).

Global singleton:
  ``_cache = ResponseCache()`` is created at module import time. Callers
  should use ``get_cache()`` to retrieve it rather than importing ``_cache``
  directly.
"""
import time
import hashlib
import json
import os
from collections import OrderedDict
from agent.logging.logger import get_logger

logger = get_logger(__name__)

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
INDEX_CACHE = os.path.join(CHROMA_DIR, ".indexed_files.json")


def _get_store_version() -> str:
    """Return a short hex digest of the current index manifest.

    The version is computed as the first 8 hex characters of the MD5 hash
    of the sorted list of filenames in ``.indexed_files.json``. When the
    document corpus is rebuilt (e.g. during ``ingest.py``), this hash
    changes and previously cached responses become stale.

    Returns:
        "0" if the index manifest does not exist or cannot be read;
        otherwise an 8-character hex string.
    """
    if not os.path.exists(INDEX_CACHE):
        return "0"
    try:
        with open(INDEX_CACHE, "r") as f:
            files = json.load(f)
        return hashlib.md5("|".join(sorted(files)).encode()).hexdigest()[:8]
    except Exception:
        return "0"


class ResponseCache:
    """LRU cache for LLM responses keyed by (prompt_variant, user_input, store_version).

    Attributes:
        maxsize: Maximum number of entries before the oldest is evicted.
        ttl: Time-to-live in seconds; entries older than this are treated
             as misses.
    """

    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        """Initialise an empty cache with the given capacity and TTL.

        Args:
            maxsize: Maximum number of cache entries (default 100).
            ttl: Entry lifetime in seconds (default 3600 = 1 hour). After
                 this period ``get()`` will return None and the stale entry
                 is purged lazily.
        """
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: OrderedDict = OrderedDict()

    def _make_key(self, prompt_variant: str, user_input: str) -> str:
        """Build a deterministic SHA-256 cache key.

        The key incorporates:
          1. The active prompt variant (so different strategies don't collide).
          2. The lowercased, stripped user input (for case-insensitive matching).
          3. The current store version (so re-indexing invalidates old entries).

        Args:
            prompt_variant: Name of the prompt strategy (e.g. "v3_structured").
            user_input: Raw user query.

        Returns:
            A 64-character hex string (SHA-256 digest).
        """
        version = _get_store_version()
        raw = f"{prompt_variant}:::{user_input.strip().lower()}:::{version}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt_variant: str, user_input: str) -> dict | None:
        """Retrieve a cached response if it exists and has not expired.

        On a hit the entry is promoted to the most-recently-used position.

        Args:
            prompt_variant: The active prompt variant.
            user_input: The raw user query (case-insensitive matching).

        Returns:
            The cached response dict if found and fresh; None otherwise.
        """
        key = self._make_key(prompt_variant, user_input)
        if key not in self._cache:
            return None
        entry = self._cache[key]
        if time.time() - entry["timestamp"] > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        logger.debug(f"Cache hit for key={key[:12]}...")
        return entry["data"]

    def set(self, prompt_variant: str, user_input: str, data: dict):
        """Store a response in the cache, evicting the oldest entry if full.

        Args:
            prompt_variant: The active prompt variant.
            user_input: The raw user query.
            data: The response dict to cache (any JSON-serialisable dict).
        """
        key = self._make_key(prompt_variant, user_input)
        self._cache[key] = {"timestamp": time.time(), "data": data}
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, prompt_variant: str, user_input: str):
        """Remove a specific entry from the cache, if it exists.

        Args:
            prompt_variant: The active prompt variant.
            user_input: The raw user query.
        """
        key = self._make_key(prompt_variant, user_input)
        self._cache.pop(key, None)

    def clear(self):
        """Remove all entries from the cache."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return the current number of cached entries."""
        return len(self._cache)


_cache = ResponseCache()


def get_cache() -> ResponseCache:
    """Return the module-level ResponseCache singleton.

    This is the recommended way to access the cache throughout the
    codebase (rather than importing ``_cache`` directly).
    """
    return _cache
