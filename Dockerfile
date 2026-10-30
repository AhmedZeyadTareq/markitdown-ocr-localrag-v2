# syntax=docker/dockerfile:1
# MarkItDown OCR LocalRAG: the web app and API in one image, served on port 8000.
# Ollama runs outside this image: on the host, or as a separate container (see docker-compose.yml).

# ---------- Build the web app into static files ----------
# The output is plain HTML/JS, so build it natively even when making an image for another CPU type
FROM --platform=$BUILDPLATFORM node:24-slim AS web
WORKDIR /web
ENV NEXT_TELEMETRY_DISABLED=1
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# Empty API URL: the browser calls the API on the same address it loaded the page from
RUN NEXT_PUBLIC_API_URL="" npm run build


# ---------- Python app ----------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface

# Tesseract and Poppler: OCR fallback for scanned files when the chosen model can't read images
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Created early: changing ownership of files later would copy them into a new layer
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data "$HF_HOME" \
    && chown app /data "$HF_HOME"

WORKDIR /app

# CPU-only PyTorch: the default build bundles GPU libraries worth several GB, and the embedding model
# runs fast enough on CPU. The large models run in Ollama, which has its own GPU support.
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

# Download the embedding model at build time, so the container never needs the internet for search
ARG EMBED_MODEL=BAAI/bge-base-en-v1.5
ENV EMBED_MODEL=${EMBED_MODEL}
USER app
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBED_MODEL'])"

COPY backend/ backend/
COPY cli.py ./
COPY --from=web /web/out web/out

ENV OUTPUTS_DIR=/data \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    OLLAMA_MODEL=gemma3:12b

VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

CMD ["python", "-m", "backend.api"]
