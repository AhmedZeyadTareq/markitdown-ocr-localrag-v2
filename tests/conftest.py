import pytest

from backend import config, llm


@pytest.fixture(autouse=True)
def outputs(tmp_path, monkeypatch):
    """Every test gets its own empty outputs folder, so real documents are never touched."""
    folder = tmp_path / "outputs"
    monkeypatch.setattr(config, "OUTPUTS_DIR", str(folder))
    return folder


@pytest.fixture
def no_model(monkeypatch):
    """Extraction without Ollama: plain MarkItDown, Tesseract fallback."""
    monkeypatch.setattr(
        llm, "status",
        lambda: {"ollama": False, "model": config.OLLAMA_MODEL, "model_available": False, "vision": False, "models": []},
    )


@pytest.fixture
def make_file(tmp_path):
    def make(name, content):
        path = tmp_path / "docs" / name
        path.parent.mkdir(exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return str(path)

    return make
