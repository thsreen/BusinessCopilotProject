# NovaCart AI Operations Copilot — Problem Framing

## Domain & Scenario

Business operations decision-support agent for NovaCart, a mid-sized e-commerce company. The agent helps operations analysts answer KPI questions, retrieve policies, analyze trends, and escalate issues — without modifying any data.

Track A — LangGraph framework. Decision Support Only safety class.

## User Persona

Sarah Mitchell, Business Operations Analyst. 5 years experience. Comfortable with Excel and dashboards but not a data engineer. Spends 60-70% of her time pulling data from multiple sources instead of analyzing it.

## Problem

Operations analysts field recurring questions about fulfillment times, return rates, CSAT scores, and policy lookups. Data lives across CSV exports, weekly reports, SOP documents, and dashboards — no single interface. Slow escalation process requires cross-referencing multiple documents.

## Scope

**Inputs:** Natural language questions about KPIs, policies, trends, escalations.

**Outputs:** Textual analysis with data points, policy explanations, anomaly flags, confidence indicators, escalation instructions with contact info.

**Constraints:**
- No data modification (read-only)
- Express uncertainty when data is insufficient
- Escalate out-of-scope requests
- No PII in logs

## Success Criteria

| Criteria | Target |
|---|---|
| Response relevance | >= 4.0 / 5.0 |
| Safety compliance | 100% refusal of modification requests |
| Retrieval accuracy | >= 80% |
| Tool selection accuracy | >= 85% |
| Uncertainty correctness | >= 90% |
| Escalation handling | 100% produce contact info + ID |
| PII safety | 100% log entries PII-free |
| Response latency (Ollama) | <= 5s |

## Tech Stack

- Python 3.11+, LangGraph (StateGraph), ChromaDB, sentence-transformers
- Ollama (llama3.2:3b) primary, OpenAI GPT-4o-mini fallback
- FastAPI + Streamlit for deployment
- SQLite for conversation memory
