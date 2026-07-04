"""Tool: Escalate to a human operations analyst.

Logs an escalation request to a JSON file on disk and returns a structured
response with a unique escalation ID and instructions for the user to follow
up with the operations team.

Thread-safety for concurrent escalations is handled via a file-lock helper
(*locked_json_read_write*) so that multiple agent instances can append without
corrupting the log.
"""
import os
import datetime
from agent.filelock import locked_json_read_write

# Path to the escalation log – stored under the project-root ``logs/``
# directory so it survives container restarts.
ESCALATION_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "logs",
    "escalations.json",
)


def escalate_to_analyst(
    reason: str = "", details: str = "", query: str = ""
) -> dict:
    """Log an escalation request and return contact instructions.

    Appends a new entry to the escalation JSON file (creating the file and
    containing directory if they do not exist). Each entry receives a
    monotonically increasing escalation ID (e.g. ``ESC-001``) derived from
    the total number of entries after the append.

    Args:
        reason:  A short explanation of why the escalation is needed.
                 Defaults to "User requested escalation" when empty.
        details: Free-text context or additional notes. Falls back to the
                 *query* value if omitted.
        query:   Legacy fallback for the *details* field. Included to
                 maintain compatibility with callers that pass the original
                 user query here.

    Returns:
        A dictionary containing:
            - escalation_id : Unique ID formatted as ``ESC-{NNN}``.
            - status        : ``"escalated"``.
            - message       : A user-facing confirmation message.
            - instructions  : How to follow up with the operations team.
            - escalated_to  : The team / role the issue was sent to.
            - response_time : Expected SLA for first response.
    """
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "reason": reason or "User requested escalation",
        "details": details or query,
        "status": "logged",
    }

    # Lock, read, append, write – the helper handles file creation / init
    with locked_json_read_write(ESCALATION_LOG, default=[]) as escalations:
        escalations.append(entry)
        escalation_id = f"ESC-{len(escalations):03d}"

    return {
        "escalation_id": escalation_id,
        "status": "escalated",
        "message": "Your request has been escalated to a human operations analyst.",
        "instructions": (
            "Please contact the operations team at ops-lead@novacart.com for "
            "follow-up. Reference your escalation ID for faster handling."
        ),
        "escalated_to": "Tier-1 Operations Lead",
        "response_time": "Expected response within 30 minutes during business hours.",
    }
