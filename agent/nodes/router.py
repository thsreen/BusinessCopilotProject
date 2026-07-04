"""
Intent router node — decides which downstream node should handle the query.

Purpose:
    After guardrails pass, this node classifies the user's intent by
    keyword matching against two sets of intent keywords imported from
    agent.intent:

    - KNOWLEDGE_KEYWORDS  → route to retrieval  (vector-store lookup)
    - TOOL_KEYWORDS       → route to tools       (KPI / trend / escalate)

    If neither set matches, the query is sent directly to the LLM.

State modifications:
    - Sets state["next_step"] to "retrieval", "tools", or "llm".
"""

from agent.state import AgentState
from agent.intent import KNOWLEDGE_KEYWORDS, TOOL_KEYWORDS


def router_node(state: AgentState) -> AgentState:
    """
    LangGraph node — classify user intent and set the next graph step.

    Heuristic: if the input contains any keyword from KNOWLEDGE_KEYWORDS,
    it is treated as a knowledge-seeking query. Otherwise, if it contains
    any keyword from TOOL_KEYWORDS, it is treated as a data/tool query.
    If neither, the LLM handles it directly.

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``
            (or the last message content as fallback). Writes
            ``state["next_step"]`` with the selected route.

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
