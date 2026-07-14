"""
Intent router node — decides which downstream node should handle the query.

Purpose:
    After guardrails pass, this node classifies the user's intent by
    keyword matching against two sets of intent keywords imported from
    agent.intent:

    - KNOWLEDGE_KEYWORDS  → route to retrieval  (vector-store lookup)
    - TOOL_KEYWORDS       → route to tools       (KPI / trend / escalate)

    If neither set matches, the query is sent directly to the LLM.
    There is no LLM-based classification fallback — that would add an
    extra 3-10s Ollama call for every non-standard query. Instead,
    the LLM generates a response from its training knowledge (with
    low confidence), and the uncertainty node adds a disclaimer.

State modifications:
    - Sets state["next_step"] to "retrieval", "tools", or "llm".
"""

from agent.state import AgentState
from agent.intent import KNOWLEDGE_KEYWORDS, TOOL_KEYWORDS
from agent.logging.logger import get_logger

logger = get_logger(__name__)


def router_node(state: AgentState) -> AgentState:
    """LangGraph node — classify user intent and set the next graph step.

    Uses static keyword matching (fast path, no LLM call):
      - KNOWLEDGE_KEYWORDS → retrieval
      - TOOL_KEYWORDS → tools
      - neither → llm (direct LLM response, low confidence if no data)

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``.
            Writes ``state["next_step"]``.

    Returns:
        The mutated *state* dictionary.
    """
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
