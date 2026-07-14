
import os
from dotenv import load_dotenv

load_dotenv()

# Module-level singleton — populated on first successful initialisation and
# reused for the lifetime of the process.
_embedding_model = None

def get_embeddings():

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
