"""
Retrieval node — performs vector-similarity search against ChromaDB.

Purpose:
    When the router detects a knowledge-seeking intent, this node
    queries the ChromaDB vector store for the top-k most semantically
    similar documents relative to the user's input.

State modifications:
    - Sets state["retrieved_docs"] to a list of dicts, each containing
      ``content``, ``source``, and ``score``. Empty list on failure.
    - Sets state["error"] if the vector-store call throws.
"""

from agent.state import AgentState
from agent.retrieval.vector_store import get_vector_store
from agent.retrieval.embeddings import get_embeddings


def retrieval_node(state: AgentState) -> AgentState:
    """
    LangGraph node — retrieve relevant documents from ChromaDB.

    Uses the configured embedding model to encode the user's query and
    runs ``similarity_search`` with ``k=4``. The top-4 results are
    unpacked into a serializable dict list so they can be passed
    downstream without LangChain document objects.

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``
            (or the last message content as fallback). Writes
            ``state["retrieved_docs"]`` — a list of
            ``{"content": str, "source": str, "score": float}``.

    Returns:
        The mutated *state* dictionary.
    """
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")

    try:
        store = get_vector_store()
        # k=4 provides enough coverage for context assembly without
        # overwhelming the LLM prompt with irrelevant passages.
        results = store.similarity_search(user_text, k=4)
        docs = []
        for doc in results:
            docs.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "score": doc.metadata.get("score", 0.0),
            })
        state["retrieved_docs"] = docs
    except Exception as e:
        # Graceful degradation: if the vector store is unavailable,
        # the LLM node will still generate a response from its own
        # knowledge — just without context passages.
        state["retrieved_docs"] = []
        state["error"] = str(e)

    return state
