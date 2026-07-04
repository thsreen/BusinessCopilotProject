"""Phase 2 - V1a: Rule-Based Baseline Agent
============================================

Pure keyword-matching agent.  No LLM, no LangGraph, no external API calls.

Purpose in the project
----------------------
This file defines the simplest possible "assistant" so we can contrast it
against more sophisticated versions (v1b, v2, etc.).  It demonstrates the
limitations of a purely rule-based approach:

    * Brittle matching – "fulfillment time" works but "how long to ship" does not.
    * No natural-language understanding – synonyms, typos, and paraphrases all fail.
    * No memory of conversation context – each turn is independent.
    * No safety reasoning – refusals are also keyword-based and easily bypassed.
    * No integration with real data – all responses are hard-coded strings.

Usage
-----
    python baselines/v1a_rule_based.py

Then type questions at the prompt.  Type ``quit``, ``exit``, or ``bye`` to stop.

File location
-------------
This file lives under ``baselines/`` to keep it separate from the main
application code in ``src/``."""

import datetime
import json
import os
import re

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# All interactions (user input, response, match method) are appended as JSON
# lines to this file so we can audit and compare baseline vs. agent behaviour.
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "v1a_baseline.log")

# ---------------------------------------------------------------------------
# Response dictionary
# ---------------------------------------------------------------------------

# Maps a keyword (or phrase) to a canned answer.  The first keyword found in
# the user's lower-cased input wins.
RESPONSES = {
    "fulfillment": "Fulfillment time is currently within acceptable range. For specific numbers, please check the daily KPI dashboard.",
    "return rate": "The return rate is monitored daily. Current return rate is within the 8% target threshold.",
    "csat": "Customer satisfaction score is tracked. Current CSAT is above the 4.2 target.",
    "order volume": "Order volume fluctuates daily. Average daily volume is approximately 4,000-5,000 orders.",
    "warehouse a": "Warehouse A is located in Austin, TX. It handles Electronics, Books, and Beauty & Health products.",
    "warehouse b": "Warehouse B is located in Newark, NJ. It handles Clothing, Home & Garden, and Automotive products.",
    "warehouse c": "Warehouse C is located in Reno, NV. It handles Sports & Outdoors, Toys & Games, and Automotive products.",
    "kpi": "Key Performance Indicators include: Order Volume, Fulfillment Time, Return Rate, CSAT, Wait Time, Revenue, and Inventory Accuracy.",
    "hello": "Hello! I am the NovaCart Ops Assistant. I can help you with basic operational questions. Try asking about fulfillment, return rates, CSAT, or KPIs.",
    "hi": "Hello! I am the NovaCart Ops Assistant. I can help you with basic operational questions. Try asking about fulfillment, return rates, CSAT, or KPIs.",
    "help": "I can answer questions about: fulfillment, return rates, CSAT, order volume, warehouses, KPIs, and more. Just ask!",
}

# ---------------------------------------------------------------------------
# Safety / refusal machinery
# ---------------------------------------------------------------------------

# Words that suggest the user wants to talk to a human (→ escalate).
ESCALATION_KEYWORDS = ["escalate", "human", "manager", "supervisor", "complaint", "urgent"]

# Words that suggest the user is trying to modify data (→ refuse).
REFUSAL_KEYWORDS = ["update", "change", "modify", "delete", "remove", "set", "override"]

# (regex_pattern, refusal_message) pairs checked *before* any keyword match.
# These catch common "do something destructive" phrases with more nuance than
# the simple keyword list above.
SAFETY_PATTERNS = [
    (r"change\s+(the\s+)?(return|policy|rule|kpi|target)", "I cannot modify data or policies. This is a decision-support only system."),
    (r"update\s+(the\s+)?(data|record|order|inventory)", "I cannot modify data. Please contact an operations analyst for changes."),
    (r"delete\s+(the\s+)?(order|record|customer|data)", "I cannot delete data. This system is read-only."),
    (r"set\s+(the\s+)?(target|threshold|limit|sla)", "I cannot change configuration settings. Please escalate to an operations manager."),
]


def log_interaction(user_input: str, response: str, method: str = "rule_match"):
    """Append one interaction to the JSON-lines log file.

    Parameters
    ----------
    user_input : str
        The raw text the user typed.
    response : str
        The text the assistant replied with.
    method : str
        How the response was produced — ``"rule_match"``, ``"safety_refusal"``,
        ``"escalation"``, or ``"fallback"``.  This makes it easy to analyse
        later which code path fired for each query.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "user_input": user_input,
        "response": response,
        "method": method,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_safety(user_input: str) -> str | None:
    """Test *user_input* against known refusal patterns.

    Two layers are checked (in order):

    1. ``SAFETY_PATTERNS`` — regex-based checks that catch multi-word
       destructive phrases (e.g. "change the return policy").
    2. ``REFUSAL_KEYWORDS`` — simple substring checks for verbs like
       "delete", "override", etc.

    Returns
    -------
    str or None
        A refusal message if a pattern matched, else ``None``.
    """
    user_input_lower = user_input.lower()
    for pattern, refusal_msg in SAFETY_PATTERNS:
        if re.search(pattern, user_input_lower):
            return refusal_msg
    for kw in REFUSAL_KEYWORDS:
        if kw in user_input_lower:
            return f"I am a decision-support only system and cannot '{kw}' any data or settings. Please escalate to an operations analyst if you need changes made."
    return None


def check_escalation(user_input: str) -> str | None:
    """Decide whether the user is asking to speak to a human.

    If any of the ``ESCALATION_KEYWORDS`` appear in the input, return a
    canned escalation message.  Otherwise return ``None``.
    """
    user_input_lower = user_input.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in user_input_lower:
            return "Your request has been noted. To escalate to a human analyst, please contact the operations team at ops-lead@novacart.com with your reference details."
    return None


def get_response(user_input: str) -> str:
    """Produce a reply for *user_input* using a strict priority chain.

    Priority (first match wins)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Safety refusal (regex, then keyword)
    2. Escalation request
    3. Keyword match against ``RESPONSES``
    4. Generic fallback ("I don't know")

    Every path calls :func:`log_interaction` so the session can be replayed
    or analysed later.
    """
    # 1. Check safety
    safety_msg = check_safety(user_input)
    if safety_msg:
        log_interaction(user_input, safety_msg, "safety_refusal")
        return safety_msg

    # 2. Check escalation
    esc_msg = check_escalation(user_input)
    if esc_msg:
        log_interaction(user_input, esc_msg, "escalation")
        return esc_msg

    # 3. Keyword matching
    user_input_lower = user_input.lower()
    for keyword, response in RESPONSES.items():
        if keyword in user_input_lower:
            log_interaction(user_input, response, "rule_match")
            return response

    # 4. Fallback
    fallback = "I'm sorry, I don't have information about that. I can answer questions about fulfillment, return rates, CSAT, order volume, warehouses, and KPIs. Try rephrasing your question."
    log_interaction(user_input, fallback, "fallback")
    return fallback


def main():
    """REPL loop: read a line, reply via :func:`get_response`, repeat."""
    print("=" * 60)
    print("  NovaCart Ops Assistant v1a (Rule-Based Baseline)")
    print("  Decision Support Only - Read Only System")
    print("=" * 60)
    print("\nType 'quit' to exit, 'help' for available topics.\n")

    history = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Assistant: Goodbye!")
            break

        response = get_response(user_input)
        history.append({"user": user_input, "assistant": response})
        print(f"Assistant: {response}\n")

    print(f"\nSession logged. {len(history)} interactions recorded.")


if __name__ == "__main__":
    main()
