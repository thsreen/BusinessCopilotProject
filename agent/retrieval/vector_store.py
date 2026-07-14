
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ChromaDB persistence directory – lives at the project root alongside ``data/``.
CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db"
)
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
# Cache file that records the set of filenames that were last indexed, so we
# can detect additions, removals, or renames across runs.
INDEX_CACHE = os.path.join(CHROMA_DIR, ".indexed_files.json")

# Module-level singleton – populated on first successful creation.
_vector_store = None

def get_vector_store(force_rebuild: bool = False):

    global _vector_store
    if _vector_store is not None and not force_rebuild:
        return _vector_store

    # Late imports to avoid circular dependencies and defer loading cost
    from langchain_chroma import Chroma
    from agent.retrieval.embeddings import get_embeddings
    from agent.retrieval.chunker import chunk_all_docs

    embeddings = get_embeddings()

    # --- Change detection ---
    # Load the previously indexed file set from the cache (if it exists).
    indexed_files = set()
    if os.path.exists(INDEX_CACHE):
        with open(INDEX_CACHE, "r") as f:
            indexed_files = set(json.load(f))

    # Scan the current docs directory.
    current_files = set()
    docs_dir = os.path.join(DATA_DIR, "docs")
    if os.path.exists(docs_dir):
        for fname in os.listdir(docs_dir):
            if fname.endswith(".md"):
                current_files.add(fname)

    # Decide whether to rebuild: forced, file set changed, or first run (no
    # persisted Chroma directory yet).
    rebuild = (
        force_rebuild
        or (current_files != indexed_files)
        or not os.path.exists(CHROMA_DIR)
    )

    if rebuild and current_files:
        # There are documents to index — chunk, embed, and persist.
        chunks = chunk_all_docs(DATA_DIR)
        if chunks:
            texts = [c["content"] for c in chunks]
            metadatas = [
                {"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks
            ]

            _vector_store = Chroma.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas,
                persist_directory=CHROMA_DIR,
            )

            # Persist the now-current file set so future runs can detect changes.
            os.makedirs(CHROMA_DIR, exist_ok=True)
            with open(INDEX_CACHE, "w") as f:
                json.dump(list(current_files), f)

            return _vector_store
        else:
            # No chunks were produced (e.g. documents were empty or only
            # contained blank lines). Fall through to load/create an empty
            # Chroma collection below.
            pass

    # Either no rebuild was needed, or rebuild was attempted but produced
    # no chunks. Load the existing collection (which may be empty).
    # Any exception from the Chroma constructor will propagate to the caller
    # (retrieval_node catches and degrades gracefully).
    _vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    return _vector_store

def rebuild_vector_store():

    return get_vector_store(force_rebuild=True)
