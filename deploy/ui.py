"""
Streamlit web UI for the NovaCart AI Operations Copilot.

Connects to the FastAPI backend and provides a chat interface with
conversation history, confidence visualization, and session management.

Usage:
    streamlit run deploy/ui.py [-- 8000]
"""

import os
import sys
import json
import requests
import streamlit as st
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────

API_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("API_PORT", "8001"))
API_BASE = f"http://localhost:{API_PORT}"

st.set_page_config(
    page_title="NovaCart Ops Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ───────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = ""
if "session_created" not in st.session_state:
    st.session_state.session_created = False


def create_session() -> str:
    """Send a hello message to get a session ID."""
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"message": "hello", "session_id": ""},
            timeout=10,
        )
        if resp.ok:
            return resp.json().get("session_id", "")
    except requests.ConnectionError:
        st.error(f"Cannot connect to API at {API_BASE}")
    return ""


def send_message(message: str, feedback: str = None) -> dict | None:
    """Send a message to the API and return the response dict."""
    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id,
                "feedback": feedback,
            },
            timeout=120,
        )
        if resp.ok:
            data = resp.json()
            if not st.session_state.session_id:
                st.session_state.session_id = data.get("session_id", "")
            return data
        else:
            st.error(f"API error: {resp.status_code} — {resp.text}")
    except requests.ConnectionError:
        st.error(f"Cannot connect to API at {API_BASE}")
    except requests.Timeout:
        st.error("Request timed out after 120s")
    return None


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <style>
        .sidebar-logo { text-align: center; margin-bottom: 1rem; }
        .sidebar-logo h1 { font-size: 1.5rem; margin: 0; }
        .sidebar-logo p { font-size: 0.8rem; color: #666; margin: 0; }
        hr { margin: 1rem 0; }
        </style>
        <div class="sidebar-logo">
        <h1>📊 NovaCart</h1>
        <p>AI Operations Copilot</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Session")

    if not st.session_state.session_created:
        if st.button("🆕 Start New Session", use_container_width=True):
            sid = create_session()
            if sid:
                st.session_state.session_id = sid
                st.session_state.session_created = True
                st.session_state.messages = []
                st.rerun()
    else:
        st.markdown(f"**ID:** `{st.session_state.session_id[:12]}...`")
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = create_session()
            st.session_state.messages = []
            st.rerun()

    st.markdown("### Info")
    st.markdown(f"**API:** `{API_BASE}`")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3).json()
        st.markdown(f"**LLM:** `{health.get('llm_provider', '?')}`")
        st.markdown(f"**Prompt:** `{health.get('prompt_variant', '?')}`")
    except Exception:
        st.markdown("**API Status:** ⚠️ Offline")

    st.markdown("---")
    st.markdown("**Quick Tests**")
    for label, q in [
        ("📈 Return Rate", "What is the current return rate?"),
        ("📋 CSAT Trend", "How is our CSAT score trending?"),
        ("📦 Fulfillment SLA", "What is our SLA for fulfillment?"),
        ("📄 Return Policy", "Explain the return policy"),
        ("🚨 Escalate", "Escalate to a human manager"),
    ]:
        if st.button(label, use_container_width=True, key=f"q_{q[:20]}"):
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("Thinking..."):
                result = send_message(q)
            if result:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("response", "No response."),
                    "confidence": result.get("confidence", 0.0),
                    "latency_ms": result.get("latency_ms", 0),
                    "requires_escalation": result.get("requires_escalation", False),
                    "error": result.get("error"),
                })
            st.rerun()


# ── Main chat area ─────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .chat-header { text-align: center; padding: 1rem 0; border-bottom: 1px solid #eee; margin-bottom: 1rem; }
    .chat-header h1 { margin: 0; font-size: 1.8rem; }
    .chat-header p { margin: 0; color: #666; font-size: 0.9rem; }
    .confidence-high { color: #22c55e; font-weight: 600; }
    .confidence-med { color: #eab308; font-weight: 600; }
    .confidence-low { color: #ef4444; font-weight: 600; }
    .meta-row { display: flex; gap: 1rem; font-size: 0.8rem; color: #888; margin-top: 0.3rem; }
    .escalation-badge { background: #fef3c7; color: #92400e; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }
    .error-badge { background: #fee2e2; color: #991b1b; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }
    .feedback-btn { font-size: 0.75rem; padding: 0.1rem 0.4rem; cursor: pointer; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="chat-header"><h1>📊 NovaCart Ops Copilot</h1>'
    '<p>Ask questions about KPIs, policies, trends, and operations</p></div>',
    unsafe_allow_html=True,
)

if not st.session_state.session_created:
    st.info("👈 Click **Start New Session** in the sidebar to begin.")
else:
    # Display chat history
    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        with st.chat_message(role):
            st.markdown(msg["content"])

            if role == "assistant":
                confidence = msg.get("confidence", 0.0)
                latency = msg.get("latency_ms", 0)
                requires_esc = msg.get("requires_escalation", False)
                error = msg.get("error")

                if error:
                    st.error(f"\u26a0\ufe0f **Error:** {error[:200]}")
                if requires_esc:
                    st.warning(
                        "\U0001f6a8 **Escalation recommended** \u2014 This query may need a human analyst. "
                        "Contact ops-lead@novacart.com for follow-up."
                    )
                if confidence < 0.4:
                    st.warning(
                        "\U0001f4c9 **Low confidence** \u2014 The response above is based on general knowledge "
                        "without specific data backing. Please verify with a human analyst."
                    )
                elif confidence < 0.75:
                    st.info(
                        f"\U0001f4ca **Medium confidence ({confidence:.0%})** \u2014 "
                        "Some data was available, but results should be cross-checked."
                    )
                else:
                    st.success(f"\u2705 **High confidence ({confidence:.0%})** \u2014 Response is backed by data.")

                meta_cols = st.columns([1, 4])
                with meta_cols[0]:
                    st.caption(f"\u26a1 {latency:.0f}ms")

                if i == len(st.session_state.messages) - 1:
                    fb_cols = st.columns([1, 10])
                    with fb_cols[0]:
                        fb_positive = st.button(
                            "👍",
                            key=f"fb_pos_{i}",
                            help="Mark as helpful",
                        )
                        fb_negative = st.button(
                            "👎",
                            key=f"fb_neg_{i}",
                            help="Mark as not helpful",
                        )
                        if fb_positive:
                            with st.spinner("Submitting feedback..."):
                                send_message("", feedback="positive")
                            st.toast("Feedback recorded 👍", icon="✅")
                        if fb_negative:
                            with st.spinner("Submitting feedback..."):
                                send_message("", feedback="negative")
                            st.toast("Feedback recorded 👎", icon="📝")

    # Chat input
    prompt = st.chat_input("Ask about KPIs, policies, trends...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Thinking..."):
            result = send_message(prompt)
        if result:
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("response", "No response."),
                "confidence": result.get("confidence", 0.0),
                "latency_ms": result.get("latency_ms", 0),
                "requires_escalation": result.get("requires_escalation", False),
                "error": result.get("error"),
            })
            st.rerun()
