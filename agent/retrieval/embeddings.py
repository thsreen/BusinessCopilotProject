"""Embedding provider abstraction — supports Ollama, OpenAI, and HuggingFace.

Provides a single *get_embeddings* factory function that returns a LangChain
embedding model instance. The provider is selected via the environment variable
``EMBEDDING_PROVIDER`` (defaults to ``"huggingface"`` if unset or unrecognised).

Fallback chain:
    1. If ``EMBEDDING_PROVIDER=openai`` and a valid API key is configured,
       instantiate ``OpenAIEmbeddings`` (model ``text-embedding-3-small``).
    2. If ``EMBEDDING_PROVIDER=ollama`` (or fallback), try
       ``OllamaEmbeddings`` (model ``nomic-embed-text``) with a connectivity
       test. If the test fails, clear the singleton and continue.
    3. Final fallback — ``HuggingFaceEmbeddings`` (model ``all-MiniLM-L6-v2``)
       from ``langchain_community``, which works fully offline.

Once initialised the embedding model is cached as a module-level singleton so
that repeated calls reuse the same instance without re-initialisation.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Module-level singleton — populated on first successful initialisation and
# reused for the lifetime of the process.
_embedding_model = None


def get_embeddings():
    """Get (or create) the embedding model based on configuration.

    Checks the ``EMBEDDING_PROVIDER`` environment variable and attempts to
    initialise the corresponding LangChain embeddings class. On failure it
    falls through to the next provider in the chain. The result is cached in
    the module-level ``_embedding_model`` variable.

    Environment variables consumed:
        - ``EMBEDDING_PROVIDER``: ``"openai"``, ``"ollama"``, or any other
          value (falls back to HuggingFace).
        - ``OPENAI_API_KEY``    : Required for the OpenAI provider. Ignored
          if set to the placeholder ``"sk-your-key-here"``.
        - ``OLLAMA_BASE_URL``   : Optional; defaults to
          ``http://localhost:11434``.

    Returns:
        A LangChain ``Embeddings`` instance (``OpenAIEmbeddings``,
        ``OllamaEmbeddings``, or ``HuggingFaceEmbeddings``).

    Raises:
        ImportError: If *none* of the providers could be loaded — this can
                     happen when neither ``langchain-ollama``,
                     ``langchain-openai``, nor ``sentence-transformers`` is
                     installed.
    """
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    provider = os.environ.get("EMBEDDING_PROVIDER", "huggingface").lower()

    # --- OpenAI provider ---
    # Only attempt if the provider is explicitly "openai" AND a real (non-
    # placeholder) key exists.
    if provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings

            api_key = os.environ.get("OPENAI_API_KEY", "")
            if api_key and api_key != "sk-your-key-here":
                _embedding_model = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=api_key,
                )
                return _embedding_model
        except Exception:
            pass  # Silently fall through to the next provider

    # --- Ollama provider ---
    # Attempted when the provider is "ollama" OR as a pre-HuggingFace fallback.
    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings

            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            _embedding_model = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=base_url,
            )
            # Test that the Ollama server is actually reachable; if not,
            # clear the singleton and let the HuggingFace fallback handle it.
            _embedding_model.embed_query("test")
            return _embedding_model
        except Exception:
            _embedding_model = None  # Allow the fallback to proceed

    # --- HuggingFace fallback (fully offline) ---
    # This is the safest default: it requires no network, no API key, and
    # works out of the box with `pip install sentence-transformers`.
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return _embedding_model
    except Exception:
        raise ImportError(
            "No embedding provider available. Install langchain-ollama, "
            "langchain-openai, or sentence-transformers."
        )
