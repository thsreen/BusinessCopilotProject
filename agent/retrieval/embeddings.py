"""Embedding provider abstraction - supports both Ollama and OpenAI."""
import os
from dotenv import load_dotenv

load_dotenv()

_embedding_model = None


def get_embeddings():
    """Get the embedding model based on configuration."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    provider = os.environ.get("EMBEDDING_PROVIDER", "huggingface").lower()

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
            pass

    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            _embedding_model = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=base_url,
            )
            # Test connection
            _embedding_model.embed_query("test")
            return _embedding_model
        except Exception:
            _embedding_model = None

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        return _embedding_model
    except Exception:
        raise ImportError(
            "No embedding provider available. Install langchain-ollama, "
            "langchain-openai, or sentence-transformers."
        )
