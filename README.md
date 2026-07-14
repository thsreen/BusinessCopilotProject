# NovaCart Ops Copilot

AI assistant for business operations. Answers KPI queries, policy questions, trend analysis, and escalations.

## Setup

```powershell
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` — add your OpenAI API key. That's it.

## Run

```powershell
python deploy\cli.py
```

Or web UI:

```powershell
python deploy\api.py
streamlit run deploy\ui.py -- 8001
```

## Docs

- `problem_framing.md` — Persona, scope, success criteria
- `evaluation_report.md` — Test results, evidence logs, failure case
- `engineering_justification.md` — Architecture decisions
- `demo_script.md` — 5 demo interactions
- `EVALUATOR.md` — Instructions for evaluators
