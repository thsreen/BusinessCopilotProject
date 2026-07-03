---
title: "Problem Framing Document"
subtitle: "NovaCart AI Operations Copilot"
author: "AI Engineering Team"
date: "July 2026"
---

---

## Executive Summary

NovaCart, a mid-sized e-commerce company processing 50,000--200,000 orders monthly across three fulfillment centers, requires an AI-powered decision-support agent to assist Business Operations Analysts with daily KPI monitoring, trend analysis, policy retrieval, and escalation triage. This document defines the problem scope, user persona, success criteria, and known failure modes for the AI Operations Copilot -- a read-only, safety-constrained conversational agent built on LangGraph with dual-LLM support (Ollama and OpenAI).

---

## 1. Domain & Scenario

| Attribute | Value |
|---|---|
| Scenario | Business Operations -- AI Operations Copilot (Decision Support Only) |
| Track | Track A -- Framework-Based (LangGraph) |
| Safety Class | Decision Support Only -- no data modification, no action execution |
| Industry | E-commerce |
| Company | NovaCart (fictional) |

---

## 2. Company Profile

**NovaCart** is a mid-sized e-commerce company operating in North America with:

- **Employees:** ~520
- **Fulfillment Centers:** 3 (Austin-TX, Newark-NJ, Reno-NV)
- **Monthly Order Volume:** 50,000--200,000
- **Active SKUs:** ~25,000
- **Product Categories:** 8 (Electronics, Clothing, Home & Garden, Books, Sports & Outdoors, Beauty & Health, Toys & Games, Automotive)
- **Leadership:** CEO Maria Torres, COO James Chen, VP Operations Michael Okonkwo

---

## 3. User Persona

| Attribute | Detail |
|---|---|
| **Name** | Sarah Mitchell |
| **Role** | Business Operations Analyst |
| **Department** | Operations (reports to VP Operations) |
| **Experience** | 5 years in operations analysis, 2 years at NovaCart |
| **Technical Skill** | Comfortable with Excel and dashboards; not a data engineer |
| **Daily Tools** | KPI dashboards, CSV exports, weekly reports, email, Slack |

### Daily Workflow

| Time | Activity |
|---|---|
| 8:30 AM | Pull daily KPIs from dashboards (order volume, fulfillment, returns, CSAT) |
| 9:00 AM | Morning ops standup -- present KPI snapshot and flag anomalies |
| 10:00 AM | Ad-hoc analysis requests from leadership (trends, comparisons, root causes) |
| 1:00 PM | Investigate escalations or incidents reported overnight |
| 3:00 PM | Prepare weekly ops report (Mondays) or monthly business review (1st week) |

### Pain Points

1. **Data Fragmentation:** KPIs live in dashboards, policies in a handbook, incidents in a separate tracker -- no single query interface
2. **Manual Analysis:** 60--70% of time spent pulling and cross-referencing data instead of analyzing it
3. **Recurring Questions:** Same operational questions asked repeatedly (fulfillment status, return rate spikes, policy lookups)
4. **Slow Escalation:** Determining when and how to escalate requires consulting multiple documents

---

## 4. Problem Statement

> Business Operations Analysts at NovaCart spend the majority of their time manually aggregating data from disparate sources to answer routine operational questions, delaying decision-making and increasing the risk of missed anomalies. An AI Operations Copilot can provide instant, data-backed answers, flag anomalies proactively, and escalate complex or out-of-scope issues to human analysts -- all within a strict read-only, safety-constrained framework.

---

## 5. Scope

### 5.1 Inputs

| Input Type | Examples |
|---|---|
| Natural language questions | "What was the average fulfillment time last week?" |
| Metric queries | "Show me return rates for electronics in March" |
| Policy lookups | "What's the policy on fulfillment delays?" |
| Trend analysis requests | "Compare order volumes between Q1 and Q2" |
| Escalation requests | "I need to speak to a manager about Warehouse A" |

### 5.2 Outputs

| Output Type | Description |
|---|---|
| Textual Analysis | Answer with specific data points, trend context, and citations |
| Policy Explanations | Procedure steps from SOPs and handbook, with escalation thresholds |
| Anomaly Flags | Notable deviations from expected patterns, with data evidence |
| Confidence Indicators | Explicit High/Medium/Low rating with uncertainty disclaimers |
| Escalation Instructions | Contact information, escalation ID, expected response time |

### 5.3 Constraints (Non-Negotiable)

| ID | Constraint | Enforcement Mechanism |
|---|---|---|
| C1 | Must refuse requests to modify data, policies, or trigger actions | Guardrails node + prompt rules |
| C2 | Must express uncertainty instead of guessing when data is insufficient | Uncertainty node + confidence threshold |
| C3 | Must provide escalation to a human analyst for out-of-scope requests | Escalation tool + contact info |
| C4 | Must not store sensitive business data or PII in logs | PiiSafeLogger with regex scrubbing |
| C5 | Read-only: cannot execute workflows, change system state, or trigger external actions | Tool design (no write tools) |

### 5.4 Assumptions

1. KPI data is available in CSV format with daily granularity (180 days of historical data)
2. Operational documents (handbook, SOPs, incident reports) are available in Markdown
3. The agent has network access to either Ollama (local) or OpenAI API (cloud)
4. Users are NovaCart employees with basic operational domain knowledge
5. The system operates in English (single-language scope for v1)

---

## 6. Success Criteria & Metrics

| Criterion | Measurement Method | Target |
|---|---|---|
| Response Relevance | User rating (1--5 scale) across test scenarios | >= 4.0 / 5.0 |
| Safety Compliance | % of data-modification requests correctly refused | 100% |
| Retrieval Accuracy | % of retrieved documents relevant to query | >= 80% |
| Tool Selection Accuracy | % of queries where correct tool is selected | >= 85% |
| Uncertainty Correctness | % of uncertain responses that correctly express limits | >= 90% |
| Escalation Handling | % of escalation requests that produce contact info + ID | 100% |
| PII Safety | % of log entries free of PII (audit) | 100% |
| Response Latency (Local) | Time from input to response (Ollama, llama3.2:3b) | <= 5,000 ms |
| Response Latency (API) | Time from input to response (OpenAI, gpt-4o-mini) | <= 2,000 ms |

---

## 7. Example User Questions

The following questions represent the range of query types the agent must handle:

| # | Question | Type | Complexity |
|---|---|---|---|
| 1 | "What was the average order fulfillment time last week?" | KPI Query | Low |
| 2 | "Show me any anomalies in daily order volumes this month." | Anomaly Detection | Medium |
| 3 | "Compare return rates between electronics and clothing categories." | Comparison | Medium |
| 4 | "What caused the spike in customer wait time in April?" | Root Cause Analysis | High |
| 5 | "I need a summary of this week's operational metrics for the standup." | Multi-metric Synthesis | Medium |
| 6 | "What's the policy on fulfillment delays according to SOP-001?" | Policy Retrieval | Low |
| 7 | "Escalate this to a human -- I need someone to look at Warehouse A." | Escalation | Low |
| 8 | "Update the return policy to allow 30-day returns." | Safety Refusal | Low |

---

## 8. Known Failure Modes & Edge Cases

| Failure Mode | Category | Expected Handling |
|---|---|---|
| User attempts to modify data/policies | Safety | Refuse via guardrails node; explain read-only constraint |
| Question references data outside available period | Data Gap | Express uncertainty; offer available date range |
| Ambiguous query ("how are things?") | Ambiguity | Request clarification; suggest specific metrics |
| User includes PII in input (email, phone) | PII | Refuse processing; request non-PII input |
| KPI data file is missing or corrupted | Data Error | Log error; inform user with graceful message |
| Multi-turn rapid-fire questions | Session Management | Maintain context via memory; answer sequentially |
| LLM provider unavailable (Ollama/OpenAI down) | Infrastructure | Auto-fallback to alternative provider |
| User disputes data accuracy | Disagreement | Suggest escalation to human analyst for verification |
| Report narrative contradicts KPI data (intentional data inconsistency) | Data Integrity | Surface the inconsistency; flag for human review |
| Multi-step causal question ("Why did X happen and what did we do about it?") | Complexity | Decompose into retrieval + tool query + synthesis |

---

*Document version 1.0 | Prepared for Capstone Evaluation*
