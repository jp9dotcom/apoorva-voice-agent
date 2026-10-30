"""Provider-neutral chat completion client configuration."""
from dataclasses import dataclass
import os

from openai import OpenAI


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    key_env: str
    model_env: str


PROVIDERS = {
    # Local Ollama server; the API key is a compatibility placeholder.
    "ollama": ProviderConfig("ollama", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "", "OLLAMA_MODEL"),
    "openrouter": ProviderConfig("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
    "gemini": ProviderConfig("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "GEMINI_MODEL"),
    "groq": ProviderConfig("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL"),
}


class ProviderError(RuntimeError):
    """Raised when a provider cannot be configured."""


def create_client(provider: str | None = None) -> tuple[OpenAI, str]:
    selected = (provider or os.getenv("APOORVA_PROVIDER", "ollama")).strip().lower()
    config = PROVIDERS.get(selected)
    if config is None:
        raise ProviderError(f"Unknown provider '{selected}'. Choose one of: {', '.join(PROVIDERS)}")
    api_key = os.getenv(config.key_env, "").strip() if config.key_env else "ollama"
    model = (os.getenv(config.model_env) or os.getenv("APOORVA_MODEL", "")).strip()
    if config.key_env and not api_key:
        raise ProviderError(f"{config.key_env} is not set")
    if selected == "ollama" and not model:
        model = "qwen3.5:4b"
    if selected == "groq" and not model:
        model = "qwen/qwen3.8-27b"
    if any(marker in model.lower() for marker in ("prompt-guard", "llama-guard", "safeguard")):
        raise ProviderError(
            f"{model} is a safety classifier, not a conversation model. "
            "Choose a general chat model with tool-use support."
        )
    if not model or model == "replace-with-a-tool-capable-model-id":
        raise ProviderError(f"Set {config.model_env} (or APOORVA_MODEL) to a model supported by {selected}")
    try:
        return OpenAI(base_url=config.base_url, api_key=api_key, timeout=60.0, max_retries=2), model
    except Exception as exc:
        raise ProviderError(f"Could not initialize {selected}: {exc}") from exc
