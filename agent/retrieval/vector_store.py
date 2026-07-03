"""ChromaDB vector store wrapper for document retrieval."""
import json
import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
INDEX_CACHE = os.path.join(CHROMA_DIR, ".indexed_files.json")

_vector_store = None


def get_vector_store(force_rebuild: bool = False):
    """Get or create the vector store. Rebuilds if data has changed."""
    global _vector_store
    if _vector_store is not None and not force_rebuild:
        return _vector_store

    from langchain_chroma import Chroma
    from agent.retrieval.embeddings import get_embeddings
    from agent.retrieval.chunker import chunk_all_docs

    embeddings = get_embeddings()

    # Check if we need to rebuild
    indexed_files = set()
    if os.path.exists(INDEX_CACHE):
        with open(INDEX_CACHE, "r") as f:
            indexed_files = set(json.load(f))

    current_files = set()
    docs_dir = os.path.join(DATA_DIR, "docs")
    if os.path.exists(docs_dir):
        for fname in os.listdir(docs_dir):
            if fname.endswith(".md"):
                current_files.add(fname)

    rebuild = force_rebuild or (current_files != indexed_files) or not os.path.exists(CHROMA_DIR)

    if rebuild and current_files:
        chunks = chunk_all_docs(DATA_DIR)
        if chunks:
            texts = [c["content"] for c in chunks]
            metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks]

            _vector_store = Chroma.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas,
                persist_directory=CHROMA_DIR,
            )

            # Cache indexed file list
            os.makedirs(CHROMA_DIR, exist_ok=True)
            with open(INDEX_CACHE, "w") as f:
                json.dump(list(current_files), f)

            return _vector_store
        else:
            # No documents to index - create empty store
            pass

    try:
        _vector_store = Chroma(
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
    except Exception:
        _vector_store = None

    return _vector_store


def rebuild_vector_store():
    """Force rebuild the vector store."""
    return get_vector_store(force_rebuild=True)
