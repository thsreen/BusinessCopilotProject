"""
LLM invocation node — calls the configured language model with assembled context.

Purpose:
    After retrieval and/or tool execution, this node:
      1. Checks a response cache (skipped when feedback is present).
      2. Assembles context from retrieved docs and tool results.
      3. Retrieves any auto-tuning instructions from the feedback store.
      4. Builds the prompt via ``get_prompt`` with the chosen variant.
      5. Invokes the LLM via ``LLMClient.invoke``.
      6. Assigns a confidence score based on available evidence.
      7. Caches the response for future cache hits.

State modifications:
    - Sets state["response"] — the LLM output text.
    - Sets state["confidence"] — float 0.0–1.0 based on evidence.
    - Sets state["cached"] — bool indicating cache hit.
    - Sets state["latency_ms"] — round-trip time in milliseconds.
    - Sets state["error"] on failure.
"""

import json
import os
import re
import time
from agent.state import AgentState
from agent.llm.client import LLMClient
from agent.llm.prompts import get_prompt
from agent.cache import get_cache
from agent.nodes.feedback import get_adaptation_instructions
from agent.logging.logger import get_logger

logger = get_logger(__name__)


def _strip_confidence_line(text: str) -> str:
    """Remove any ``**Confidence**:`` line the LLM may have generated.

    The system prompt no longer asks for a confidence rating (the UI
    displays the actual system confidence instead), but older cached
    responses or model inertia may still produce one.  This function
    strips it so there is no contradiction between the LLM's text and
    the system's metadata.

    Matches lines like:
      - **Confidence**: High - based on data availability
      - **Confidence**: Low / Medium

    Args:
        text: The raw LLM response text.

    Returns:
        Cleaned text with confidence lines removed.
    """
    return re.sub(
        r'^-?\s?\*\*Confidence\*\*:.*(?:\n|$)',
        '',
        text,
        flags=re.MULTILINE,
    ).strip()


def llm_node(state: AgentState) -> AgentState:
    """
    LangGraph node — generate a response via the LLM.

    Pipeline within this node:
      1. **Cache lookup** — if the same (variant, user_text) pair was
         previously answered and no new feedback is present, return the
         cached response immediately.
      2. **Context assembly** — concatenate retrieved documents and
         tool results into plain-text / JSON context blocks.
      3. **Adaptation instructions** — pull any prompt-tuning rules
         that were automatically generated from past negative feedback.
      4. **Prompt construction** — delegate to ``get_prompt`` which
         selects the template variant and fills in all sections.
      5. **LLM call** — ``client.invoke(prompt)`` with error handling.
      6. **Confidence scoring** — see confidence heuristics below.
      7. **Cache write** — store the result for future requests.

    Confidence heuristics:
        - docs + tools available → 0.9
        - either docs or tools   → 0.8
        - neither                → 0.4 (LLM knowledge only)

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``,
            ``messages``, ``retrieved_docs``, ``tool_results``,
            ``requires_escalation``, ``feedback``, and the environment
            variable ``PROMPT_VARIANT``. Writes ``response``,
            ``confidence``, ``cached``, ``latency_ms``, and ``error``.

    Returns:
        The mutated *state* dictionary.
    """
    start = time.time()
    client = LLMClient()
    cache = get_cache()
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")

    # Allow switching prompt templates at deploy time without code changes.
    prompt_variant = os.environ.get("PROMPT_VARIANT", "v3_structured")

    # --- Cache check ---
    # Skip cache when feedback is being submitted so the LLM re-evaluates
    # with the new adaptation instructions baked in.
    feedback = state.get("feedback")
    if not feedback:
        cached = cache.get(prompt_variant, user_text)
        if cached:
            state["response"] = _strip_confidence_line(cached.get("response", ""))
            state["confidence"] = cached.get("confidence", 0.85)
            state["cached"] = True
            state["latency_ms"] = round((time.time() - start) * 1000, 1)
            return state

    # --- Context assembly ---
    context = ""
    if state.get("retrieved_docs"):
        # Truncate each document's content to 500 characters to keep the
        # prompt within token limits while preserving key information.
        context = "Relevant information:\n" + "\n".join(
            f"- [{d.get('source','unknown')}] {d.get('content','')[:500]}"
            for d in state["retrieved_docs"]
        )

    tool_context = ""
    if state.get("tool_results"):
        # Serialise tool results as JSON; cap at 2000 characters to avoid
        # overflowing the context window with large data dumps.
        tool_context = "Data from systems:\n" + json.dumps(state["tool_results"], indent=2)[:2000]

    # --- Auto-tuning instructions from feedback patterns ---
    adaptation_instructions = get_adaptation_instructions(state)

    prompt = get_prompt(
        prompt_variant,
        user_text,
        context,
        tool_context,
        state.get("requires_escalation", False),
        state.get("feedback"),
        adaptation_instructions,
    )

    try:
        response = client.invoke(prompt)
        state["response"] = _strip_confidence_line(response)
        state["cached"] = False

        # Derive confidence from the evidence available.
        has_docs = bool(state.get("retrieved_docs"))
        has_tools = bool(state.get("tool_results"))
        if has_docs and has_tools:
            conf = 0.9
        elif has_docs or has_tools:
            conf = 0.8
        else:
            conf = 0.4
        state["confidence"] = conf

        # Cache the (variant, input) → response mapping.
        cache.set(prompt_variant, user_text, {
            "response": response,
            "confidence": conf,
        })
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        state["response"] = (
            "I encountered an error processing your request. "
            "Please try again or contact support."
        )
        state["confidence"] = 0.0
        state["error"] = str(e)

    state["latency_ms"] = round((time.time() - start) * 1000, 1)
    return state
