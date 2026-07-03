"""Tool: Escalate to a human operations analyst."""
import os
import datetime
from agent.filelock import locked_json_read_write

ESCALATION_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "logs", "escalations.json"
)


def escalate_to_analyst(reason: str = "", details: str = "", query: str = "") -> dict:
    """Log an escalation request and return instructions."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "reason": reason or "User requested escalation",
        "details": details or query,
        "status": "logged",
    }

    with locked_json_read_write(ESCALATION_LOG, default=[]) as escalations:
        escalations.append(entry)
        escalation_id = f"ESC-{len(escalations):03d}"

    return {
        "escalation_id": escalation_id,
        "status": "escalated",
        "message": "Your request has been escalated to a human operations analyst.",
        "instructions": "Please contact the operations team at ops-lead@novacart.com for follow-up. "
                        "Reference your escalation ID for faster handling.",
        "escalated_to": "Tier-1 Operations Lead",
        "response_time": "Expected response within 30 minutes during business hours.",
    }
