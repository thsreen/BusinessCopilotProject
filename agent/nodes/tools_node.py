"""
Tools execution node — dispatches to operational tools based on intent.

Purpose:
    When the router detects a tool-oriented intent (or when guardrails
    flag an escalation), this node selects and invokes the appropriate
    backend function from the ``agent.tools`` package.

    Three tools are available:
      - escalate       → human escalation (priority, short-circuits other tools)
      - trend_analysis → temporal trend analysis
      - query_kpi      → KPI / metric data queries

State modifications:
    - Sets state["tool_calls"] — record of each tool invocation.
    - Sets state["tool_results"] — list of result dicts from tools.
    - For escalation: sets state["response"], state["confidence"],
      and state["escalation_handled"] directly so the LLM node can
      be skipped.
"""

from agent.state import AgentState
from agent.intent import ESCALATION_KEYWORDS, TREND_KEYWORDS, QUERY_KPI_KEYWORDS
from agent.tools.query_kpi import query_kpi_data
from agent.tools.trend_analysis import get_trend_analysis
from agent.tools.escalate import escalate_to_analyst


def tools_node(state: AgentState) -> AgentState:
    """
    LangGraph node — select and execute the appropriate tool.

    Tool selection priority (first match wins):
      1. Escalation keywords → ``escalate_to_analyst``
      2. Trend keywords      → ``get_trend_analysis``
      3. KPI query keywords  → ``query_kpi_data``

    Escalation is checked first because it is a user-requested action
    that should bypass all other processing. After execution, every
    tool call is recorded in ``state["tool_calls"]`` and its result
    is appended to ``state["tool_results"]``. For escalations the
    response is assembled directly so the graph can end.

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``
            (or the last message content as fallback) and optional
            ``escalation_reason``. Writes ``tool_calls``, ``tool_results``,
            and for escalation also ``response``, ``confidence``, and
            ``escalation_handled``.

    Returns:
        The mutated *state* dictionary.
    """
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")
    text_lower = user_text.lower()

    results = []
    calls = []

    selected_tool = None
    tool_args = {}

    # --- Escalation takes priority ---
    if any(kw in text_lower for kw in ESCALATION_KEYWORDS):
        selected_tool = "escalate"
        tool_args = {
            "query": user_text,
            "reason": state.get("escalation_reason", "User requested escalation"),
        }

    # --- Trend analysis for temporal questions ---
    elif any(kw in text_lower for kw in TREND_KEYWORDS):
        selected_tool = "trend_analysis"
        tool_args = {"query": user_text}

    # --- KPI data queries ---
    elif any(kw in text_lower for kw in QUERY_KPI_KEYWORDS):
        selected_tool = "query_kpi"
        tool_args = {"query": user_text}

    # --- Dynamic fallback: LLM router classified as tools ---
    # If no static keywords matched but the LLM-based router determined
    # this is a tools query, try a general KPI lookup.
    if not selected_tool and state.get("classification") == "tools":
        selected_tool = "query_kpi"
        tool_args = {"query": user_text}

    if selected_tool:
        call_record = {"tool": selected_tool, "args": tool_args}
        try:
            if selected_tool == "query_kpi":
                result = query_kpi_data(**tool_args)
            elif selected_tool == "trend_analysis":
                result = get_trend_analysis(**tool_args)
            elif selected_tool == "escalate":
                result = escalate_to_analyst(**tool_args)
                state["escalation_handled"] = True
                # Assemble a self-contained response for escalation so
                # the LLM node is not needed — the graph can go straight
                # to the uncertainty check and then end.
                state["response"] = (
                    f"**Escalation ID:** {result.get('escalation_id', 'N/A')}\n\n"
                    f"{result.get('message', '')}\n\n"
                    f"**Contact:** {result.get('escalated_to', 'Tier-1 Operations Lead')} - ops-lead@novacart.com\n\n"
                    f"**Response Time:** {result.get('response_time', 'Within 30 minutes during business hours.')}\n\n"
                    f"Reference your Escalation ID in any follow-up communication."
                )
                state["confidence"] = 1.0
            else:
                result = {"error": f"Unknown tool: {selected_tool}"}

            call_record["result"] = result
            calls.append(call_record)
            results.append(result)

        except Exception as e:
            # Capture the error so the LLM node can still formulate
            # a helpful response explaining what went wrong.
            call_record["error"] = str(e)
            calls.append(call_record)
            results.append({"error": str(e)})

    state["tool_calls"] = calls
    state["tool_results"] = results

    return state
