# NovaCart Ops Copilot

AI assistant for business operations at NovaCart e-commerce. Answers KPI queries, policy questions, trend analysis, and escalations.

## Setup

```powershell
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` — set `LLM_PROVIDER=ollama` and make sure Ollama is running with `llama3.2:3b`.

## Run

```powershell
python deploy\cli.py
```

Or with the web UI:

```powershell
python deploy\api.py       # Terminal 1
streamlit run deploy\ui.py -- 8001  # Terminal 2
```

## Data

Synthetic NovaCart data is in `data/`. Vector store and SQLite are auto-created on first run.
