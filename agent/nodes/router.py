
from agent.state import AgentState
from agent.intent import KNOWLEDGE_KEYWORDS, TOOL_KEYWORDS
from agent.logging.logger import get_logger

logger = get_logger(__name__)

def router_node(state: AgentState) -> AgentState:

    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")
    text_lower = user_text.lower()

    needs_knowledge = any(kw in text_lower for kw in KNOWLEDGE_KEYWORDS)
    needs_tools = any(kw in text_lower for kw in TOOL_KEYWORDS)

    if needs_knowledge:
        state["next_step"] = "retrieval"
    elif needs_tools:
        state["next_step"] = "tools"
    else:
        state["next_step"] = "llm"

    return state
