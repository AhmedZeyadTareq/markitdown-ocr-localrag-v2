"""Web API for the Next.js UI. Run with: python -m backend.api  (serves on http://127.0.0.1:8000)

If the web app has been built (web/out), it's served from the same address, e.g. in the Docker image."""
import asyncio
import json
import os
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config, llm, storage
from backend.extract import extract
from backend.organize import reorganize
from backend.rag import DocumentRAG

app = FastAPI(title="MarkItDown OCR LocalRAG")
app.add_middleware(CORSMiddleware, allow_origins=config.WEB_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def reject_other_sites(request, call_next):
    """Browsers let any website send form uploads and plain POSTs to this server; CORS only hides the replies.
    So changes are accepted only from this app's own pages (or from tools like curl, which send no Origin)."""
    origin = request.headers.get("origin")
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and origin
        and origin not in config.WEB_ORIGINS
        and urlsplit(origin).netloc != request.headers.get("host")
    ):
        return JSONResponse({"detail": "Requests from other websites aren't allowed."}, status_code=403)
    return await call_next(request)


_doc_locks: dict[str, threading.Lock] = {}
# Search indexes for the most recently asked documents, kept in memory so follow-up questions are fast
RAG_CACHE_SIZE = 8
_rag_cache: OrderedDict[tuple[str, str], tuple[str, DocumentRAG]] = OrderedDict()
_rag_cache_lock = threading.Lock()
_rag_build_locks: dict[tuple[str, str], threading.Lock] = {}


def _lock_for(doc_id):
    return _doc_locks.setdefault(doc_id, threading.Lock())


def _paths(doc_id):
    if doc_id not in storage.list_doc_ids():
        raise HTTPException(404, "Document not found.")
    return storage.paths_for(doc_id)


def _check_version(version):
    if version not in storage.VERSIONS:
        raise HTTPException(400, "version must be 'raw' or 'organized'.")


def _summary(doc_id):
    paths = storage.paths_for(doc_id)
    meta = storage.read_meta(paths)
    files = [paths["raw"], paths["organized"], paths["meta"]]
    updated = max((os.path.getmtime(f) for f in files if os.path.exists(f)), default=os.path.getmtime(paths["folder"]))
    return {
        "id": doc_id,
        "filename": meta.get("filename", doc_id),
        "has_raw": os.path.exists(paths["raw"]),
        "has_organized": os.path.exists(paths["organized"]),
        "can_extract": storage.source_file(paths) is not None,
        "raw_chars": os.path.getsize(paths["raw"]) if os.path.exists(paths["raw"]) else 0,
        "updated_at": datetime.fromtimestamp(updated, timezone.utc).isoformat(),
    }


def _stream(work):
    """Runs work(emit) in a thread and streams every emitted event to the browser as Server-Sent Events."""

    async def events():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def emit(event):
            loop.call_soon_threadsafe(queue.put_nowait, event)

        def runner():
            try:
                work(emit)
            except Exception as e:
                emit({"type": "error", "message": llm.friendly_error(e)})
            finally:
                emit(None)

        loop.run_in_executor(None, runner)
        while (event := await queue.get()) is not None:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _logger(emit):
    return lambda message: emit({"type": "log", "message": message})


def _extract(paths, emit):
    source = storage.source_file(paths)
    if source is None:
        raise ValueError("The original file isn't available anymore. Add it again to read it.")
    log = _logger(emit)
    storage.save_extraction(extract(source, log), source, paths, log)


@app.get("/api/health")
def health():
    """For container health checks: answers as soon as the server is up, without contacting Ollama."""
    return {"ok": True}


@app.get("/api/status")
def status():
    """Ollama state, the chosen model, and every installed model that can be chosen."""
    return llm.status()


class ModelChoice(BaseModel):
    model: str


@app.put("/api/model")
def choose_model(choice: ModelChoice):
    try:
        llm.select_model(choice.model)
    except ConnectionError as e:
        raise HTTPException(503, llm.friendly_error(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return llm.status()


@app.get("/api/documents")
def list_documents():
    docs = [_summary(d) for d in storage.list_doc_ids()]
    return sorted(docs, key=lambda d: d["updated_at"], reverse=True)


@app.post("/api/documents")
def upload_document(file: UploadFile = File(...)):
    # Plain def so FastAPI runs it in a worker thread: waiting on the document lock mustn't block the event loop
    if not file.filename:
        raise HTTPException(400, "The upload has no filename.")
    data = file.file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    doc_id = storage.doc_id_for(file.filename)
    with _lock_for(doc_id):
        storage.save_upload(file.filename, data)
    return _summary(doc_id)


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    _paths(doc_id)
    return _summary(doc_id)


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    _paths(doc_id)
    with _lock_for(doc_id):
        storage.delete_document(doc_id)
        with _rag_cache_lock:
            for version in storage.VERSIONS:
                _rag_cache.pop((doc_id, version), None)
    return {"deleted": doc_id}


@app.get("/api/documents/{doc_id}/text")
def get_text(doc_id: str, version: str = "raw"):
    paths = _paths(doc_id)
    _check_version(version)
    if not os.path.exists(paths[version]):
        raise HTTPException(404, f"No {version} text yet.")
    return {"text": storage.load_content(paths[version])}


@app.post("/api/documents/{doc_id}/extract")
def extract_document(doc_id: str):
    paths = _paths(doc_id)

    def work(emit):
        with _lock_for(doc_id):
            _extract(paths, emit)
        emit({"type": "done", "document": _summary(doc_id)})

    return _stream(work)


@app.post("/api/documents/{doc_id}/reorganize")
def reorganize_document(doc_id: str):
    paths = _paths(doc_id)

    def work(emit):
        with _lock_for(doc_id):
            if not os.path.exists(paths["raw"]):
                _extract(paths, emit)
            organized = reorganize(
                storage.load_content(paths["raw"]),
                log=_logger(emit),
                on_progress=lambda done, total: emit({"type": "progress", "done": done, "total": total}),
            )
            storage.save_content(organized, paths["organized"], _logger(emit))
        emit({"type": "done", "document": _summary(doc_id)})

    return _stream(work)


class ChatRequest(BaseModel):
    question: str
    version: str = "raw"


def _rag_for(doc_id, version, paths, log):
    key = (doc_id, version)
    text = storage.load_content(paths[version])
    digest = storage.fingerprint_bytes(text.encode("utf-8"))
    # One build per document version at a time: two first questions mustn't write the same index folder at once
    with _rag_build_locks.setdefault(key, threading.Lock()):
        with _rag_cache_lock:
            cached = _rag_cache.get(key)
            if cached and cached[0] == digest:
                _rag_cache.move_to_end(key)
                return text, cached[1]
        rag = DocumentRAG(text, paths[f"index_{version}"], log)
        with _rag_cache_lock:
            _rag_cache[key] = (digest, rag)
            _rag_cache.move_to_end(key)
            while len(_rag_cache) > RAG_CACHE_SIZE:
                _rag_cache.popitem(last=False)
    return text, rag


@app.post("/api/documents/{doc_id}/chat")
def chat(doc_id: str, request: ChatRequest):
    paths = _paths(doc_id)
    _check_version(request.version)
    if not os.path.exists(paths[request.version]):
        raise HTTPException(409, f"Create the {request.version} text before asking about it.")
    question = request.question.strip()
    if not question:
        raise HTTPException(400, "Ask a question.")

    def work(emit):
        if (doc_id, request.version) not in _rag_cache:
            # Loading the embedding model and index can take several seconds on the first question
            emit({"type": "log", "message": "[🔄] Preparing search..."})
        text, rag = _rag_for(doc_id, request.version, paths, _logger(emit))
        sources = rag.retrieve(question)
        # Character positions let the UI highlight exactly where each passage sits in the document
        emit({"type": "sources", "sources": [{"text": s, "start": rag.start_of(s, text)} for s in sources]})
        for token in rag.answer_stream(question, sources):
            emit({"type": "token", "text": token})
        emit({"type": "done"})

    return _stream(work)


# Registered last so every /api route above takes precedence
if os.path.isdir(config.WEB_DIST):
    app.mount("/", StaticFiles(directory=config.WEB_DIST, html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
