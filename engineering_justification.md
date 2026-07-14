# Engineering Justification

## Framework: LangGraph
Chose LangGraph over CrewAI or plain LangChain because the agent is a single state machine with clear steps — not a multi-agent system. StateGraph gives typed state, conditional edges, and built-in execution control without extra complexity.

## LLM: Ollama primary, OpenAI fallback
Ollama runs locally with llama3.2:3b — free, no API key needed, works offline. OpenAI (gpt-4o-mini) configured as fallback for faster responses when available.

## Vector Store: ChromaDB
Persistent, local, zero-config. Embeddings use sentence-transformers/all-MiniLM-L6-v2 (offline, free). Auto-rebuilds when documents change.

## Memory: SQLite + in-memory
SQLite for persistence across sessions (WAL mode for concurrent reads). In-memory dict for fast short-term access (capped at 50 messages).

## Safety: 4-layer defense
1. Guardrails node — regex blocks PII, modifications, escalations before LLM
2. Prompt rules — read-only constraints embedded in all prompts
3. Tool design — no write/delete/update tools exist
4. Logging — PiiSafeLogger scrubs emails, phones, SSNs from logs

## Prompt Strategy: V3 Structured
Three variants tested. V3 (structured output format + reasoning framework) scored highest on relevance (4.8/5) and safety (100%). V2 is available for lower latency needs.

## Deployment: CLI + API
CLI for quick testing. FastAPI for integration. Streamlit UI for evaluators. Rate limiting and CORS configured.
