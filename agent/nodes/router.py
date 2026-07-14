"""
Intent router node — decides which downstream node should handle the query.

Purpose:
    After guardrails pass, this node classifies the user's intent and sets
    the next graph step. Classification uses a two-tier approach:

    1. **Static keyword matching** (fast path) — checks the input against
       ``KNOWLEDGE_KEYWORDS`` and ``TOOL_KEYWORDS`` from agent.intent.
    2. **LLM-based classification** (dynamic fallback) — if no keywords
       match, a lightweight LLM call classifies the query into one of:
       ``"retrieval"`` (needs documents), ``"tools"`` (needs KPI data),
       or ``"llm"`` (direct answer). Results are cached to avoid
       repeated LLM calls for similar queries.

State modifications:
    - Sets state["next_step"] to "retrieval", "tools", or "llm".
"""

from agent.state import AgentState
from agent.intent import KNOWLEDGE_KEYWORDS, TOOL_KEYWORDS
from agent.logging.logger import get_logger

logger = get_logger(__name__)

# Cache for LLM-based classification results — keyed by normalized query text.
_classification_cache: dict[str, str] = {}


def _classify_with_llm(query: str) -> str:
    """Use the LLM to classify a query that no keywords matched.

    Checks the cache first. On a miss, sends a minimal classification
    prompt to the LLM and expects a single-word reply.

    Args:
        query: The user's input text.

    Returns:
        One of ``"retrieval"``, ``"tools"``, or ``"llm"``.
    """
    normalized = query.strip().lower()
    cached = _classification_cache.get(normalized)
    if cached:
        return cached

    try:
        from agent.llm.client import LLMClient

        client = LLMClient()
        classification_prompt = (
            'Classify the following user query into exactly one category.\n'
            'Answer with exactly one word: retrieval, tools, or llm.\n\n'
            '- "retrieval" if the user is asking about policies, procedures, documentation, '
            'definitions, company info, or anything found in a knowledge base.\n'
            '- "tools" if the user is asking about numbers, KPIs, metrics, comparisons, '
            'trends, or operational data that requires a database or analytics tool.\n'
            '- "llm" if the query is a general question, greeting, brainstorming, or '
            'anything the LLM can answer from its own knowledge.\n\n'
            f'Query: {query}\n'
            'Category:'
        )
        response = client.invoke(classification_prompt)
    except Exception:
        logger.warning("LLM classification failed, falling back to LLM direct route")
        _classification_cache[normalized] = "llm"
        return "llm"

    response_lower = response.strip().lower()
    if "retrieval" in response_lower:
        result = "retrieval"
    elif "tools" in response_lower or "tool" in response_lower:
        result = "tools"
    else:
        result = "llm"

    _classification_cache[normalized] = result
    logger.info(f"LLM classified '{query[:60]}' as '{result}'")
    return result


def router_node(state: AgentState) -> AgentState:
    """LangGraph node — classify user intent and set the next graph step.

    Uses static keyword matching first (fast path). When no keywords
    match, falls back to an LLM-based classification that understands
    nuanced intent (e.g. "Are we shipping on time?" → tools).

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

    # Fast path: static keyword matching
    needs_knowledge = any(kw in text_lower for kw in KNOWLEDGE_KEYWORDS)
    needs_tools = any(kw in text_lower for kw in TOOL_KEYWORDS)

    if needs_knowledge:
        state["next_step"] = "retrieval"
    elif needs_tools:
        state["next_step"] = "tools"
    else:
        # Dynamic fallback: use LLM to classify unrecognised queries.
        # Store the classification in state so downstream nodes can use it.
        llm_route = _classify_with_llm(user_text)
        state["next_step"] = llm_route
        state["classification"] = llm_route

    return state
