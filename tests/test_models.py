"""Model choice, with Ollama replaced by a fake that has three installed models."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import config, llm, settings
from backend.api import app

INSTALLED = {
    "gemma3:12b": ("completion", "vision"),
    "qwen2.5:0.5b": ("completion",),
    "nomic-embed-text:latest": ("embedding",),
}


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    models = [
        SimpleNamespace(model=name, size=1e9 * (i + 1), modified_at=i, details=SimpleNamespace(parameter_size=None))
        for i, name in enumerate(INSTALLED)
    ]
    monkeypatch.setattr(llm.ollama, "list", lambda: SimpleNamespace(models=models))
    monkeypatch.setattr(llm, "_capabilities", lambda model, modified_at: INSTALLED[model])
    monkeypatch.setattr(config, "OLLAMA_MODEL", "gemma3:12b")


def test_lists_chat_models_and_marks_which_read_images():
    models = {m["name"]: m["vision"] for m in llm.list_models()}
    assert models == {"gemma3:12b": True, "qwen2.5:0.5b": False}, "embedding-only models can't be chosen"


def test_default_model_comes_from_config():
    assert settings.current_model() == "gemma3:12b"
    assert llm.status()["vision"]


def test_choice_is_remembered():
    llm.select_model("qwen2.5:0.5b")
    assert settings.current_model() == "qwen2.5:0.5b"
    status = llm.status()
    assert status["model_available"] and not status["vision"]


def test_models_not_installed_cant_be_chosen():
    with pytest.raises(ValueError, match="isn't installed"):
        llm.select_model("llama9:70b")
    assert settings.current_model() == "gemma3:12b"


def test_missing_saved_model_is_reported_not_hidden():
    settings.set_model("removed-model:7b")
    status = llm.status()
    assert status["model"] == "removed-model:7b" and not status["model_available"]


def test_api_switches_model():
    client = TestClient(app)
    response = client.put("/api/model", json={"model": "qwen2.5:0.5b"})
    assert response.status_code == 200
    assert response.json()["model"] == "qwen2.5:0.5b"
    assert client.get("/api/status").json()["model"] == "qwen2.5:0.5b"


def test_api_rejects_unknown_model():
    response = TestClient(app).put("/api/model", json={"model": "nope:1b"})
    assert response.status_code == 400
    assert "ollama pull nope:1b" in response.json()["detail"]


@pytest.mark.parametrize("reported, shown", [("11.8B", "12B"), ("494.03M", "0.5B"), ("3.2B", "3.2B"), ("7B", "7B"), (None, None)])
def test_sizes_are_shown_in_billions(reported, shown):
    assert llm._billions(reported) == shown
