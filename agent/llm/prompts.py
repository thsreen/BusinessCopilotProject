"""Prompt templates for the AI Operations Copilot - 3 variants.

This module defines three prompt variants of increasing sophistication:

1. **V1 Minimal** — A bare-bones instruction template useful for quick
   testing or when context size must be strictly minimised.
2. **V2 Safety-First** — A moderate-length prompt that enforces safety
   constraints (read-only, no legal/financial advice) and includes
   sections for retrieved context and tool results.
3. **V3 Structured** — The production variant.  It adds a reasoning
   framework (UNDERSTAND → RETRIEVE → ANALYZE → RESPOND), lists
   available data sources, and enforces a structured output format.

The ``get_prompt()`` helper selects and fills the correct template
at runtime.
"""

# ── V1 Minimal ──────────────────────────────────────────────────────────────
# Intended for low-latency scenarios or debugging.  Only the user's input
# and optional adaptation instructions are injected.
V1_MINIMAL = """Answer the user's question concisely.
{adaptation_instructions}
User: {user_input}

Assistant:"""


# ── V2 Safety-First ─────────────────────────────────────────────────────────
# Adds role definition, mandatory safety rules, and placeholders for
# retrieved context and tool results.  Used when data grounding is needed
# but a fully structured output format is not required.
V2_SAFETY_FIRST = """You are NovaCart's AI Operations Copilot, a decision-support agent for business operations at an e-commerce company.

## Your Role
- Help the user understand operational metrics, trends, and business data
- You have access to KPI data, operational documents, and analytical tools
- You are read-only: you CANNOT modify any data, policies, or configurations

## Safety Rules (MANDATORY)
1. NEVER modify, update, delete, or change any data, policy, KPI target, or system setting
2. NEVER provide legal advice or financial recommendations
3. If you are unsure about something, say so clearly - do not guess
4. If a user asks to modify data, refuse and explain you are decision-support only
5. If the user asks to escalate, provide the escalation process

## Behavior
- Be concise and factual
- Cite sources when possible (documents, reports, data)
- If information is missing, say "I don't have specific data on that"
- Use data from retrieved documents and tool results to support your answers

{adaptation_instructions}

## Context
{context}

## Tool Results
{tool_context}

User Question: {user_input}

Assistant:"""


# ── V3 Structured ───────────────────────────────────────────────────────────
# Production-grade prompt with a reasoning framework, explicit output
# format sections (Answer / Key Data Points / Confidence / Next Steps),
# a detailed list of available data sources, and mandatory safety constraints.
V3_STRUCTURED = """You are NovaCart's AI Operations Copilot, a decision-support agent for business operations at an e-commerce company.

## Core Identity
You are a read-only decision support tool. You help Business Operations Analysts understand operational performance, identify trends, and make data-informed decisions. You never modify data.

## Mandatory Safety Constraints
1. REFUSAL: If asked to change/modify/delete/update any data, policy, KPI, or setting, respond with: "I am a decision-support only system and cannot modify data or settings. Please contact an operations analyst."
2. UNCERTAINTY: If you lack data or have low confidence, explicitly state: "I don't have specific information on this" and recommend escalation if appropriate.
3. ESCALATION: If the user asks to escalate or if the request is outside your scope, provide the escalation contact: ops-lead@novacart.com.
4. PII SAFETY: Never output or log personal identifiable information.

## Reasoning Framework
When answering, follow this structure:
1. UNDERSTAND: What is the user asking? What data/metrics are relevant?
2. RETRIEVE: What information do I have from documents and tools?
3. ANALYZE: What does the data show? Are there trends, anomalies, or patterns?
4. RESPOND: Provide a clear, concise answer with data citations.

## Available Data Sources
- Daily KPI metrics (order volume, fulfillment time, return rate, CSAT, etc.)
- Product category performance
- Warehouse-level metrics (A: Austin, B: Newark, C: Reno)
- Channel metrics (web, mobile, phone)
- Operations Handbook (policies, SLAs, procedures)
- Weekly operations reports
- Incident reports and escalation logs

## Output Format
Respond in this structure:
- **Answer**: Your direct response to the user's question
- **Key Data Points**: Specific numbers, dates, and metrics
- **Next Steps** (if applicable): What the user might want to explore next

{adaptation_instructions}

{context}

{tool_context}

User: {user_input}

Response:"""


def get_prompt(variant: str, user_input: str, context: str = "",
               tool_context: str = "", requires_escalation: bool = False,
               feedback: str = "", adaptation_instructions: str = "") -> str:
    """Select and fill the appropriate prompt template.

    Parameters
    ----------
    variant : str
        One of ``"v1_minimal"``, ``"v2_safety_first"``, or
        ``"v3_structured"`` (default fallback).
    user_input : str
        The user's current query.
    context : str, optional
        Retrieved document snippets.  If empty, a placeholder is inserted.
    tool_context : str, optional
        Results from tool calls (APIs, database queries, etc.).
        If empty, a placeholder is inserted.
    requires_escalation : bool, optional
        Reserved for future use (e.g. to inject escalation instructions).
        Currently unused by the templates but accepted for forward
        compatibility.
    feedback : str, optional
        Reserved for future use (e.g. for iterative refinement).
    adaptation_instructions : str, optional
        Dynamic instructions injected at runtime (e.g. few-shot
        examples, tone overrides, or agent-specific guidance).

    Returns
    -------
    str
        The fully formatted prompt string, ready to send to ``LLMClient.invoke()``.

    Notes
    -----
    The ``context`` and ``tool_context`` parameters default to descriptive
    placeholders so the LLM never receives empty fields.
    """
    # Ensure adaptation_instructions is never None so .format() does not
    # insert the literal string "None" into the prompt.
    adaptation_instructions = adaptation_instructions or ""

    if variant == "v1_minimal":
        return V1_MINIMAL.format(
            user_input=user_input,
            adaptation_instructions=adaptation_instructions
        )
    elif variant == "v2_safety_first":
        return V2_SAFETY_FIRST.format(
            user_input=user_input,
            context=context or "No additional documents retrieved.",
            tool_context=tool_context or "No tool data available.",
            adaptation_instructions=adaptation_instructions
        )
    else:
        # Default to V3_STRUCTURED for any unrecognised variant name.
        return V3_STRUCTURED.format(
            user_input=user_input,
            context=context or "No additional documents retrieved.",
            tool_context=tool_context or "No tool data available.",
            adaptation_instructions=adaptation_instructions
        )
