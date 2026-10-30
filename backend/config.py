"""All settings in one place. Each one can be overridden with an environment variable of the same name,
e.g. in PowerShell:  $env:OLLAMA_MODEL = "gemma3:4b"; .\\start.ps1
"""
import os


def _env(name, default, cast=str):
    value = os.environ.get(name, "").strip()
    return cast(value) if value else default


APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where each document's extracted text, organized text, and search index are saved
OUTPUTS_DIR = _env("OUTPUTS_DIR", os.path.join(APP_DIR, "outputs"))

# Local models
OLLAMA_MODEL = _env("OLLAMA_MODEL", "gemma3:12b")  # reads images, organizes text, and answers questions
OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434")  # the ollama package reads this variable too
if "://" not in OLLAMA_HOST:
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"
EMBED_MODEL = _env("EMBED_MODEL", "BAAI/bge-base-en-v1.5")  # turns text into vectors for search
NUM_CTX = _env("NUM_CTX", 8192, int)  # how much text the model reads at once, in tokens

# Organizing: each part plus its rewritten output must fit in NUM_CTX
ORGANIZE_CHUNK_CHARS = _env("ORGANIZE_CHUNK_CHARS", 6000, int)
# A rewritten part shorter than this fraction of the original means the model dropped content
MIN_KEPT_RATIO = 0.6

# Search
SEARCH_CHUNK_CHARS = 800
SEARCH_CHUNK_OVERLAP = 100
TOP_K = _env("TOP_K", 4, int)  # passages taken from each of the two searches

# Web API
API_HOST = _env("API_HOST", "127.0.0.1")
API_PORT = _env("API_PORT", 8000, int)
WEB_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]  # the Next.js dev server
# The built web app (cd web && npm run build). When it exists, the API serves it too, so one port is enough.
WEB_DIST = _env("WEB_DIST", os.path.join(APP_DIR, "web", "out"))
