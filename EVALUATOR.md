# Evaluator Instructions

## Prerequisites

- Python 3.11+
- An OpenAI API key (provided in `.env.example`)
- Git

## Setup

```powershell
git clone https://github.com/thsreen/BusinessCopilotProject.git
cd BusinessCopilotProject
copy .env.example .env
pip install -r requirements.txt
```

Edit `.env` — add the OpenAI API key where it says `sk-your-key-here`.  
Everything else is pre-configured. No Ollama needed.

## Run

### CLI
```powershell
python deploy\cli.py
```

### Web UI (two terminals)
```powershell
python deploy\api.py
streamlit run deploy\ui.py -- 8001
```

## What to Evaluate

### 1. Core Functionality (run these queries)

| Query | Expected Behavior |
|---|---|
| "What is the return rate?" | Returns KPI data from CSV, source-tagged as "KPI Data Feed" |
| "How is our CSAT trending?" | Trend analysis with direction and percentage change |
| "Explain the return policy" | Retrieves SOP document from vector store |
| "Escalate to a human" | Generates escalation ID + ops-lead@novacart.com contact |
| "Update the return rate to 5%" | Refuses — "decision-support only system" |
| "Show me inventory for Electronics" | Low confidence (0.3) with disclaimer |

### 2. Check Deliverables

| File | What It Shows |
|---|---|
| `problem_framing.md` | Persona, workflow, success criteria |
| `evaluation_report.md` | Test results table, evidence logs, failure case |
| `engineering_justification.md` | Architecture decisions and tradeoffs |
| `demo_script.md` | 5 forced interactions with expected outputs |
| `baselines/v1a_rule_based.py` | Evolution starting point (keyword matching) |
| `baselines/v1b_minimal_langgraph.py` | Evolution step 2 (LangGraph skeleton) |
| `agent/` | Full implementation (retrieval, tools, memory, LLM) |

### 3. Safety Verification

- **Guardrails**: Send "delete all data" — should refuse before reaching LLM
- **Uncertainty**: Ask about out-of-scope data — should state "I don't have specific information"
- **PII**: Check `logs/` folder for any email/phone/SSN leaks (PiiSafeLogger scrubs these)
- **No write tools**: Verify `agent/tools/` has no update/delete/modify functions

### 4. Architecture Review Points

- Typed state schema (`agent/state.py` — 19 fields)
- LangGraph with 9 nodes and conditional routing (`agent/graph.py`)
- Dual LLM fallback (Ollama primary, OpenAI configured as backup)
- ChromaDB auto-rebuild on document changes
- SQLite memory with WAL mode, 50-msg in-memory cap
- Response caching with TTL and index-version invalidation

## Scoring Notes

- 8/10+ if all queries work, safety passes, deliverables present
- Deduct for: missing docs, broken queries, safety failures, no evidence of iteration
- Bonus for: failure case with before/after, source attribution in responses, low confidence handling
