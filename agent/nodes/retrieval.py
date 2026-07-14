
from agent.state import AgentState
from agent.retrieval.vector_store import get_vector_store
from agent.retrieval.embeddings import get_embeddings

def retrieval_node(state: AgentState) -> AgentState:

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
