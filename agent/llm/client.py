"""Unified LLM client supporting OpenAI and Ollama."""
import os
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Unified client that routes to OpenAI or Ollama based on config."""

    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
        self.model = os.environ.get("LLM_MODEL", "llama3.2:3b")
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "1024"))

    def invoke(self, prompt: str, **kwargs) -> str:
        try:
            if self.provider == "openai":
                return self._invoke_openai(prompt, **kwargs)
            else:
                return self._invoke_ollama(prompt, **kwargs)
        except Exception as e:
            # Fallback: try the other provider
            fallback_provider = "ollama" if self.provider == "openai" else "openai"
            try:
                if fallback_provider == "openai":
                    return self._invoke_openai(prompt, **kwargs)
                else:
                    return self._invoke_ollama(prompt, **kwargs)
            except Exception:
                return "I encountered an error connecting to both language model providers. Please check your API configuration (Ollama running? OpenAI key set?) and try again."

    def _invoke_openai(self, prompt: str, **kwargs) -> str:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY", "")
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
        import httpx
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = kwargs.get("model", self.model)
        try:
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
            return (f"Cannot connect to Ollama at {base_url}. Please ensure Ollama is running "
                    f"and the model '{model}' is pulled. Alternatively, set LLM_PROVIDER=openai to use OpenAI.")
        except Exception:
            return ("The language model encountered an unexpected error. "
                    "Please try again or switch to OpenAI by setting LLM_PROVIDER=openai.")
