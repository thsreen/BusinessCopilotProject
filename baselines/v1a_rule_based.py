"""Phase 2 - V1a: Rule-Based Baseline Agent
Pure keyword-matching agent. No LLM, no LangGraph.
Demonstrates limitations: brittle, no understanding, no safety, no memory of context."""

import datetime
import json
import os
import re

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "v1a_baseline.log")

# Template responses keyed by keyword
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

# Escalation keywords (to trigger "escalate" response)
ESCALATION_KEYWORDS = ["escalate", "human", "manager", "supervisor", "complaint", "urgent"]

# Refusal keywords (data modification requests)
REFUSAL_KEYWORDS = ["update", "change", "modify", "delete", "remove", "set", "override"]

# Safety violations - requests the agent must refuse
SAFETY_PATTERNS = [
    (r"change\s+(the\s+)?(return|policy|rule|kpi|target)", "I cannot modify data or policies. This is a decision-support only system."),
    (r"update\s+(the\s+)?(data|record|order|inventory)", "I cannot modify data. Please contact an operations analyst for changes."),
    (r"delete\s+(the\s+)?(order|record|customer|data)", "I cannot delete data. This system is read-only."),
    (r"set\s+(the\s+)?(target|threshold|limit|sla)", "I cannot change configuration settings. Please escalate to an operations manager."),
]


def log_interaction(user_input: str, response: str, method: str = "rule_match"):
    """Log the interaction to a file."""
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
    """Check if the input violates safety rules. Returns refusal message or None."""
    user_input_lower = user_input.lower()
    for pattern, refusal_msg in SAFETY_PATTERNS:
        if re.search(pattern, user_input_lower):
            return refusal_msg
    for kw in REFUSAL_KEYWORDS:
        if kw in user_input_lower:
            return f"I am a decision-support only system and cannot '{kw}' any data or settings. Please escalate to an operations analyst if you need changes made."
    return None


def check_escalation(user_input: str) -> str | None:
    """Check if the user is asking for escalation."""
    user_input_lower = user_input.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in user_input_lower:
            return "Your request has been noted. To escalate to a human analyst, please contact the operations team at ops-lead@novacart.com with your reference details."
    return None


def get_response(user_input: str) -> str:
    """Get a response based on keyword matching."""
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
