import json
import os

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.api import app


@pytest.fixture
def client(no_model):
    return TestClient(app)


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def upload(client, name="notes.md", content=b"# Notes\n\nThe office wifi password is ORANGE-77."):
    response = client.post("/api/documents", files={"file": (name, content)})
    assert response.status_code == 200
    return response.json()


def test_upload_extract_and_read(client):
    doc = upload(client)
    assert doc["id"] == "notes_md" and not doc["has_raw"]

    stream = events(client.post(f"/api/documents/{doc['id']}/extract"))
    assert stream[-1]["type"] == "done"
    assert stream[-1]["document"]["has_raw"]

    text = client.get(f"/api/documents/{doc['id']}/text").json()["text"]
    assert "ORANGE-77" in text
    assert [d["id"] for d in client.get("/api/documents").json()] == ["notes_md"]


def test_empty_upload_is_rejected(client):
    response = client.post("/api/documents", files={"file": ("empty.md", b"")})
    assert response.status_code == 400


def test_failed_extraction_is_reported_in_the_stream(client):
    doc = upload(client, "blank.txt", b" ")
    stream = events(client.post(f"/api/documents/{doc['id']}/extract"))
    assert stream[-1]["type"] == "error"
    assert "No text found" in stream[-1]["message"]


def test_chat_needs_the_text_first(client):
    doc = upload(client)
    response = client.post(f"/api/documents/{doc['id']}/chat", json={"question": "Password?", "version": "organized"})
    assert response.status_code == 409


def test_bad_version_is_rejected(client):
    doc = upload(client)
    assert client.get(f"/api/documents/{doc['id']}/text?version=final").status_code == 400


def test_unknown_document_is_404(client):
    assert client.get("/api/documents/nope_pdf").status_code == 404
    assert client.post("/api/documents/nope_pdf/extract").status_code == 404


def test_delete(client):
    doc = upload(client)
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 200
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404


def test_health_answers_without_ollama(client):
    assert client.get("/api/health").json() == {"ok": True}


def test_built_web_app_is_served_alongside_the_api(client):
    if not os.path.isdir(config.WEB_DIST):
        pytest.skip("web app not built (cd web && npm run build)")
    page = client.get("/")
    assert page.status_code == 200 and "MarkItDown OCR LocalRAG" in page.text
    assert client.get("/api/documents").status_code == 200, "API routes must win over the web app"
