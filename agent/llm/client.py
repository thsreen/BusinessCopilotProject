"""Unified LLM client supporting OpenAI and Ollama.

Architecture
-----------
This module provides a single LLMClient class that abstracts over two
language model backends: OpenAI (GPT-4o-mini, etc.) and Ollama (local
models like Llama 3.2).  The active provider is selected at construction
time via the ``LLM_PROVIDER`` environment variable.

Fallback behaviour
------------------
If the primary provider raises any exception, ``invoke()`` automatically
attempts the other provider before giving up.  This makes the system
resilient in environments where, e.g., the local Ollama server may be
temporarily unavailable but an OpenAI key is available, or vice versa.

Environment variables
---------------------
LLM_PROVIDER     : "openai" | "ollama" (default: "ollama")
LLM_MODEL        : model name for Ollama (default: "llama3.2:3b")
LLM_TEMPERATURE  : sampling temperature (default: "0.3")
LLM_MAX_TOKENS   : max generated tokens  (default: "1024")
OPENAI_API_KEY   : API key for OpenAI
OPENAI_MODEL     : model name for OpenAI (default: "gpt-4o-mini")
OLLAMA_BASE_URL  : Ollama server URL     (default: "http://localhost:11434")
"""
import os
from dotenv import load_dotenv

# Load .env file at import time so environment variables are available
# for the entire module's lifetime.
load_dotenv()


class LLMClient:
    """Unified client that routes to OpenAI or Ollama based on config.

    Usage::

        client = LLMClient()
        reply = client.invoke("What was the order volume yesterday?")
    """

    def __init__(self):
        """Initialise the client by reading configuration from environment variables.

        All settings fall back to sensible defaults so the client works
        out-of-the-box with an Ollama instance running locally.
        """
        # Which provider to try first: "openai" or "ollama".
        self.provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
        # Model name used by Ollama (OpenAI model is read separately in _invoke_openai).
        self.model = os.environ.get("LLM_MODEL", "llama3.2:3b")
        # Sampling temperature – lower values produce more deterministic output.
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        # Maximum number of tokens the model is allowed to generate.
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "1024"))

    def invoke(self, prompt: str, **kwargs) -> str:
        """Send a prompt to the configured LLM provider with automatic fallback.

        Parameters
        ----------
        prompt : str
            The user message or system prompt to send.
        **kwargs
            Additional arguments forwarded to the provider-specific method.
            Supported keys:
            - ``model``: override the model name for this call only.

        Returns
        -------
        str
            The model's text response, or a user-facing error message if
            both providers fail.

        Side effects
        ------------
        Logs error information via ``print`` for connectivity issues
        (integration with a proper logging system is left to the caller).
        """
        try:
            if self.provider == "openai":
                return self._invoke_openai(prompt, **kwargs)
            else:
                return self._invoke_ollama(prompt, **kwargs)
        except Exception as e:
            # --- Automatic fallback ---
            # If the primary provider fails (network error, auth failure,
            # timeout, etc.) we attempt the other provider transparently.
            # This trades a small latency penalty for higher resilience.
            fallback_provider = "ollama" if self.provider == "openai" else "openai"
            try:
                if fallback_provider == "openai":
                    return self._invoke_openai(prompt, **kwargs)
                else:
                    return self._invoke_ollama(prompt, **kwargs)
            except Exception:
                # Both providers have been exhausted.  Return a generic
                # message instead of propagating the exception so that
                # upper layers can always expect a string.
                return "I encountered an error connecting to both language model providers. Please check your API configuration (Ollama running? OpenAI key set?) and try again."

    def _invoke_openai(self, prompt: str, **kwargs) -> str:
        """Call the OpenAI Chat Completions API.

        Parameters
        ----------
        prompt : str
            The user message to send.
        **kwargs
            May contain ``model`` to override the default OpenAI model.

        Returns
        -------
        str
            The assistant's response content, stripped of leading/trailing whitespace.

        Raises
        ------
        openai.OpenAIError
            Propagated on API failure (auth, rate-limit, server error).
        """
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        # Detect the placeholder key from the template .env file and bail
        # early with a helpful message rather than waiting for an auth error.
        if not api_key or api_key == "sk-your-key-here":
            return "OpenAI API key not configured. Set OPENAI_API_KEY in your .env file, or switch to Ollama by setting LLM_PROVIDER=ollama."

        client = OpenAI(api_key=api_key)
        model = kwargs.get("model", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _invoke_ollama(self, prompt: str, **kwargs) -> str:
        """Call the Ollama ``/api/generate`` endpoint via HTTP.

        Parameters
        ----------
        prompt : str
            The user message to send.
        **kwargs
            May contain ``model`` to override the default Ollama model.

        Returns
        -------
        str
            The model's response text, or a user-facing error message if
            the connection fails or the endpoint returns an error.

        Raises
        ------
        httpx.HTTPStatusError
            Propagated when the server returns a non-2xx status (after
            raise_for_status).
        """
        import httpx

        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = kwargs.get("model", self.model)

        try:
            # Timeout of 60 seconds to accommodate longer generations on
            # resource-constrained machines.
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "No response generated.")
        except httpx.ConnectError:
            # Ollama is not running or the URL is wrong.  Return a
            # diagnostic message to guide the user.
            return (f"Cannot connect to Ollama at {base_url}. Please ensure Ollama is running "
                    f"and the model '{model}' is pulled. Alternatively, set LLM_PROVIDER=openai to use OpenAI.")
        except Exception:
            # Catch-all for any other HTTP or parsing error.
            return ("The language model encountered an unexpected error. "
                    "Please try again or switch to OpenAI by setting LLM_PROVIDER=openai.")
