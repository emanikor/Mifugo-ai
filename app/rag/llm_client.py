"""
Thin client for the local Ollama server.

Critical rule for this whole file: if Ollama is unreachable, we FAIL LOUDLY
with a clear message. We never fall back to a cloud LLM API, because that
would silently break the "100% offline" guarantee this entire product is
built on — and in a region with no reliable connectivity, a hidden network
call wouldn't just be a privacy problem, it would just hang or fail anyway.
"""
import requests

from app.config import settings


class OllamaUnavailableError(Exception):
    """Raised when the local Ollama server can't be reached or errors out."""


def generate(prompt: str, *, system: str | None = None) -> str:
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(
            url, json=payload, timeout=settings.ollama_timeout_seconds
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise OllamaUnavailableError(
            "Could not reach the local Ollama server. Make sure the Ollama "
            "container is running (`docker compose up ollama`) and that the "
            f"model '{settings.ollama_model}' has been pulled."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OllamaUnavailableError(
            f"Ollama did not respond within {settings.ollama_timeout_seconds}s. "
            "The model may still be loading, or the machine may be under-"
            "resourced for this model size."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise OllamaUnavailableError(f"Ollama returned an error: {exc}") from exc

    data = response.json()
    return data.get("response", "").strip()
