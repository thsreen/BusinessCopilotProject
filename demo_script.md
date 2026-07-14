# Demo Script

## Setup
- Run `python deploy\cli.py`
- Ensure Ollama is running with `ollama list` showing `llama3.2:3b`

## Interaction 1: KPI Query

**User:** What is the current return rate?
**Expected:** Agent returns return rate percentage with source tagged as "KPI Data Feed". Shows average, min, max, and latest value.

## Interaction 2: Policy Lookup

**User:** Explain the return policy
**Expected:** Agent retrieves SOP-003 document from vector store and summarizes the 30-day return policy with source citation.

## Interaction 3: Trend Analysis

**User:** How is our CSAT score trending?
**Expected:** Agent runs trend analysis tool and returns average CSAT, direction (stable/improving/declining), and percentage change.

## Interaction 4: Safety Refusal

**User:** Update the return rate to 5%
**Expected:** Agent refuses with "I am a decision-support only system and cannot modify data or settings."

## Interaction 5: Escalation

**User:** Escalate to a human
**Expected:** Agent generates escalation ID, provides contact (ops-lead@novacart.com), and estimated response time.

## Verification
- All interactions should complete within 10s each
- Confidence should be HIGH (>=0.75) for data-backed queries
- Escalation and safety refusal should work without LLM involvement
