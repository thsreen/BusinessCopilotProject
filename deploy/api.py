"""
FastAPI web service for the AI Operations Copilot.

Provides three endpoints:
  - ``GET /health`` — Health check returning status, version, and
    active prompt variant.
  - ``POST /chat`` — Main chat endpoint. Accepts a ``ChatRequest`` JSON
    body, runs the agent via ``run_agent()`` in a thread pool, and
    returns a ``ChatResponse``.
  - ``POST /reset`` — Reset a session's memory.

Rate limiting:
  Simple in-memory sliding-window rate limiter keyed by client IP.
  Default: 30 requests per 60-second window. Configurable via the
  ``RATE_LIMIT_REQUESTS`` and ``RATE_LIMIT_WINDOW_SEC`` environment
  variables. When the limit is exceeded the endpoint returns HTTP 429.

CORS:
  Configured from the ``CORS_ORIGINS`` env var (comma-separated list).
  Defaults to ``http://localhost:3000,http://localhost:8000``.

Thread pool:
  A ``ThreadPoolExecutor(max_workers=4)`` is used to run the synchronous
  ``run_agent()`` call without blocking the asyncio event loop.
"""
import os
import sys
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from agent.graph import run_agent
from agent.logging.logger import get_logger

logger = get_logger("api")
_executor = ThreadPoolExecutor(max_workers=4)

# Simple in-memory rate limiter
_requests: dict[str, list[float]] = {}
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))
RATE_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))


def _check_rate_limit(client_ip: str):
    """Enforce a sliding-window rate limit for *client_ip*.

    Purges timestamps older than the window, then checks whether the
    count of requests in the current window exceeds the limit.

    Args:
        client_ip: The client's IP address (or ``x-forwarded-for`` value).

    Raises:
        HTTPException (429): If the rate limit has been exceeded.

    Side effects:
        Appends the current timestamp to the in-memory list for *client_ip*.
    """
    now = time.time()
    window_start = now - RATE_WINDOW
    if client_ip not in _requests:
        _requests[client_ip] = []
    # Prune timestamps outside the current window to prevent unbounded growth.
    _requests[client_ip] = [t for t in _requests[client_ip] if t > window_start]
    if len(_requests[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait before sending more requests.")
    _requests[client_ip].append(now)

app = FastAPI(
    title="NovaCart AI Operations Copilot API",
    description="Decision-support agent for business operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Request body for the ``POST /chat`` endpoint.

    Attributes:
        message: The user's question or command (required, non-empty).
        session_id: Optional session identifier for memory continuity.
        feedback: Optional feedback signal ("positive" or "negative")
            to trigger auto-tuning.
        prompt_variant: Optional prompt strategy override.
    """
    message: str
    session_id: Optional[str] = ""
    feedback: Optional[str] = None
    prompt_variant: Optional[str] = None


class ChatResponse(BaseModel):
    """Response body returned by the ``POST /chat`` endpoint.

    Attributes:
        response: The assistant's textual reply.
        session_id: The active session identifier.
        confidence: Self-assessed confidence score (0.0 – 1.0).
        latency_ms: Total end-to-end latency in milliseconds.
        requires_escalation: Whether the agent recommends human escalation.
        error: Error message if something went wrong; None otherwise.
    """
    response: str
    session_id: str
    confidence: float
    latency_ms: float
    requires_escalation: bool
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response body for the ``GET /health`` endpoint.

    Attributes:
        status: Always ``"ok"`` when the service is running.
        version: API version string.
        prompt_variant: The currently active prompt strategy.
        llm_provider: The configured LLM backend (e.g. "ollama", "openai").
    """
    status: str
    version: str
    prompt_variant: str
    llm_provider: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint.

    Returns basic service metadata without invoking the agent graph.

    Returns:
        HealthResponse with current status, version, prompt variant,
        and LLM provider.
    """
    return HealthResponse(
        status="ok",
        version="1.0.0",
        prompt_variant=os.environ.get("PROMPT_VARIANT", "v3_structured"),
        llm_provider=os.environ.get("LLM_PROVIDER", "ollama"),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, fast_request: Request):
    """Main chat endpoint.

    Accepts a user message, runs the agent synchronously in a thread
    pool, and returns the response.

    Rate limiting is applied based on the client's IP (or the
    ``x-forwarded-for`` header if behind a reverse proxy).

    Args:
        chat_request: The validated JSON body (see ``ChatRequest``).
        fast_request: FastAPI's built-in Request object for extracting
            client IP metadata.

    Returns:
        ChatResponse with the agent's answer and metadata.

    Raises:
        HTTPException (400): If the message is blank.
        HTTPException (429): If the client's rate limit is exceeded.
    """
    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    client_ip = fast_request.headers.get("x-forwarded-for", fast_request.client.host if fast_request.client else "unknown")
    _check_rate_limit(client_ip)

    logger.info(f"Chat request: session={chat_request.session_id[:8] if chat_request.session_id else 'new'}, "
                f"variant={chat_request.prompt_variant or 'default'}")

    # run_agent is synchronous; offload to the thread pool so the event
    # loop is not blocked.
    result = await asyncio.get_event_loop().run_in_executor(
        _executor, run_agent,
        chat_request.message,
        chat_request.session_id or None,
        chat_request.feedback,
        chat_request.prompt_variant,
    )

    return ChatResponse(
        response=result.get("response", "No response generated."),
        session_id=result.get("session_id", ""),
        confidence=result.get("confidence", 0.0),
        latency_ms=result.get("total_latency_ms", 0.0),
        requires_escalation=result.get("requires_escalation", False),
        error=result.get("error"),
    )


@app.post("/reset")
async def reset_session(session_id: str):
    """Reset (clear) the memory for a given session.

    Args:
        session_id: The session identifier to reset.

    Returns:
        A dict confirming the reset with the session_id echoed back.
    """
    from agent.memory.manager import MemoryManager
    mm = MemoryManager()
    mm.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting NovaCart Ops Copilot API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
