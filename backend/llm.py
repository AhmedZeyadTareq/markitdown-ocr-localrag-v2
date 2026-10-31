"""Everything that talks to Ollama."""
import re
from functools import lru_cache

import ollama
from openai import OpenAI

from backend import config, settings


@lru_cache(maxsize=64)
def _cached_capabilities(model, modified_at):
    # modified_at is part of the cache key, so a re-pulled model is checked again
    return tuple(ollama.show(model).capabilities or ())


def _capabilities(model, modified_at):
    # Failures aren't cached (lru_cache skips exceptions), so a brief Ollama hiccup doesn't hide vision for good
    try:
        return _cached_capabilities(model, modified_at)
    except Exception:
        return ()


def _billions(parameter_size):
    """Ollama reports sizes like "11.8B" or "494.03M"; show both in billions, e.g. "12B" and "0.5B"."""
    match = re.match(r"([\d.]+)\s*([KMB])", parameter_size or "", re.IGNORECASE)
    if not match:
        return parameter_size or None
    billions = float(match[1]) / {"K": 1e6, "M": 1e3, "B": 1}[match[2].upper()]
    return f"{round(billions)}B" if billions >= 10 else f"{billions:.1f}".rstrip("0").rstrip(".") + "B"


def list_models():
    """Installed models that can chat, largest first. Raises ConnectionError if Ollama isn't running."""
    models = []
    for m in ollama.list().models:
        capabilities = _capabilities(m.model, str(m.modified_at))
        # Embedding-only models can't answer questions; models from older Ollama versions report no capabilities
        if capabilities and "completion" not in capabilities:
            continue
        models.append({
            "name": m.model,
            "vision": "vision" in capabilities,
            "parameters": _billions(m.details.parameter_size) if m.details else None,
            "size_gb": round((m.size or 0) / 1e9, 1),
        })
    return sorted(models, key=lambda m: -m["size_gb"])


def _find(models, name):
    return next((m for m in models if m["name"] in (name, f"{name}:latest")), None)


def status():
    """What the app needs to know before using the model: is Ollama running, is the chosen model installed,
    and can it read images."""
    model = settings.current_model()
    try:
        models = list_models()
    except Exception:
        return {"ollama": False, "model": model, "model_available": False, "vision": False, "models": []}
    found = _find(models, model)
    return {
        "ollama": True,
        "model": model,
        "model_available": found is not None,
        "vision": bool(found and found["vision"]),
        "models": models,
    }


def select_model(name):
    """Saves the model choice. Raises ValueError if it isn't installed."""
    found = _find(list_models(), name)
    if not found:
        raise ValueError(f"{name} isn't installed. Run: ollama pull {name}")
    settings.set_model(found["name"])
    return found["name"]


def chat(messages, stream=False):
    """Returns the reply text, or a generator of text pieces when stream=True."""
    response = ollama.chat(
        model=settings.current_model(),
        messages=messages,
        options={"num_ctx": config.NUM_CTX},
        stream=stream,
    )
    if stream:
        return (part["message"]["content"] for part in response)
    return response["message"]["content"]


def vision_client():
    """MarkItDown reads images through an OpenAI-style client; Ollama serves a compatible API locally."""
    return OpenAI(base_url=f"{config.OLLAMA_HOST.rstrip('/')}/v1", api_key="ollama")


def friendly_error(error):
    model = settings.current_model()
    if isinstance(error, ConnectionError):
        return "Can't reach Ollama. Start the Ollama app and try again."
    if isinstance(error, ollama.ResponseError):
        if error.status_code == 404:
            return f"The model {model} isn't installed. Run: ollama pull {model}, or pick another model."
        return f"Ollama error: {error.error}"
    return str(error) or error.__class__.__name__
