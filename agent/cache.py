
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

        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: OrderedDict = OrderedDict()

    def _make_key(self, prompt_variant: str, user_input: str) -> str:

        version = _get_store_version()
        raw = f"{prompt_variant}:::{user_input.strip().lower()}:::{version}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt_variant: str, user_input: str) -> dict | None:

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

        key = self._make_key(prompt_variant, user_input)
        self._cache[key] = {"timestamp": time.time(), "data": data}
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def invalidate(self, prompt_variant: str, user_input: str):

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
