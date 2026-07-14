
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

# Track the actual bound port for the root page
_port_actual: int = 8000

# Simple in-memory rate limiter
_requests: dict[str, list[float]] = {}
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))
RATE_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))

def _check_rate_limit(client_ip: str):

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

    message: str
    session_id: Optional[str] = ""
    feedback: Optional[str] = None
    prompt_variant: Optional[str] = None

class ChatResponse(BaseModel):

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

@app.get("/")
async def root():
    """Root endpoint — returns an HTML page with API instructions."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""
    <html><body style="font-family:sans-serif;max-width:700px;margin:40px auto">
    <h1>NovaCart AI Operations Copilot</h1>
    <p>API is running. Use these endpoints:</p>
    <ul>
      <li><a href="/health">GET /health</a> — Health check</li>
      <li><b>POST /chat</b> — Send a chat message</li>
      <li><b>POST /reset</b> — Reset session memory</li>
    </ul>
    <h3>Test with curl:</h3>
    <pre>curl -X POST http://localhost:%d/chat -H "Content-Type: application/json" -d "{\\"message\\": \\"What is the return rate?\\"}"</pre>
    </body></html>
    """ % _port_actual)

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        prompt_variant=os.environ.get("PROMPT_VARIANT", "v3_structured"),
        llm_provider=os.environ.get("LLM_PROVIDER", "ollama"),
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, fast_request: Request):

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

@app.get("/session")
async def create_session():

    from agent.memory.manager import MemoryManager
    mm = MemoryManager()
    sid = mm.create_session()
    return {"session_id": sid}

@app.post("/reset")
async def reset_session(session_id: str):

    from agent.memory.manager import MemoryManager
    mm = MemoryManager()
    mm.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    import socket

    host = os.environ.get("HOST", "0.0.0.0")
    start_port = int(os.environ.get("PORT", "8000"))
    max_attempts = 100

    port = start_port
    for attempt in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                break
            except OSError:
                if attempt < max_attempts - 1:
                    port += 1
                else:
                    print(f"ERROR: No available port found after {max_attempts} attempts")
                    sys.exit(1)

    if port != start_port:
        print(f"Port {start_port} was in use, using port {port} instead")
    _port_actual = port
    print(f"Starting NovaCart Ops Copilot API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
