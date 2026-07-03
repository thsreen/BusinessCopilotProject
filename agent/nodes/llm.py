"""LLM call node - invokes the chosen LLM with appropriate prompts."""
import json
import os
import time
from agent.state import AgentState
from agent.llm.client import LLMClient
from agent.llm.prompts import get_prompt
from agent.cache import get_cache
from agent.nodes.feedback import get_adaptation_instructions
from agent.logging.logger import get_logger

logger = get_logger(__name__)


def llm_node(state: AgentState) -> AgentState:
    start = time.time()
    client = LLMClient()
    cache = get_cache()
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")

    prompt_variant = os.environ.get("PROMPT_VARIANT", "v3_structured")

    # Check cache first (skip if feedback is being given to force regeneration)
    feedback = state.get("feedback")
    if not feedback:
        cached = cache.get(prompt_variant, user_text)
        if cached:
            state["response"] = cached.get("response", "")
            state["confidence"] = cached.get("confidence", 0.85)
            state["cached"] = True
            state["latency_ms"] = round((time.time() - start) * 1000, 1)
            return state

    context = ""
    if state.get("retrieved_docs"):
        context = "Relevant information:\n" + "\n".join(
            f"- [{d.get('source','unknown')}] {d.get('content','')[:500]}"
            for d in state["retrieved_docs"]
        )

    tool_context = ""
    if state.get("tool_results"):
        tool_context = "Data from systems:\n" + json.dumps(state["tool_results"], indent=2)[:2000]

    # Get auto-tuning instructions from feedback patterns
    adaptation_instructions = get_adaptation_instructions(state)

    prompt = get_prompt(prompt_variant, user_text, context, tool_context,
                         state.get("requires_escalation", False),
                         state.get("feedback"),
                         adaptation_instructions)

    try:
        response = client.invoke(prompt)
        state["response"] = response
        state["cached"] = False

        has_docs = bool(state.get("retrieved_docs"))
        has_tools = bool(state.get("tool_results"))
        if has_docs and has_tools:
            conf = 0.9
        elif has_docs or has_tools:
            conf = 0.8
        else:
            conf = 0.4
        state["confidence"] = conf

        # Store in cache
        cache.set(prompt_variant, user_text, {
            "response": response,
            "confidence": conf,
        })
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        state["response"] = "I encountered an error processing your request. Please try again or contact support."
        state["confidence"] = 0.0
        state["error"] = str(e)

    state["latency_ms"] = round((time.time() - start) * 1000, 1)
    return state
