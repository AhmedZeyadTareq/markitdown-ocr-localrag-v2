# MarkItDown OCR LocalRAG

[![CI](https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/actions/workflows/ci.yml)

Read any document (PDFs, Word files, slide decks, spreadsheets, scanned pages, photos), turn it into clean Markdown, and ask questions about it. Everything runs on your own computer with **MarkItDown**, **OCR**, **Ollama**, and **local RAG** search. No cloud, no API keys, nothing leaves your machine.

It comes as a web app, a command-line tool, and a ready-made Docker image.

---

## 🐳 Quick start with Docker

You only need [Docker](https://www.docker.com/products/docker-desktop/). The image contains the web app, the API, Tesseract, Poppler, and the search model, and works without internet once the models are downloaded. Ollama, which runs the AI model, runs separately: either the one already on your computer, or a container started for you.

### Option A: you already have Ollama
```bash
docker run -d --name markitdown-ocr-localrag -p 127.0.0.1:8080:8000 -v markitdown-ocr-localrag-data:/data \
  --add-host=host.docker.internal:host-gateway ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2
```
Open http://localhost:8080. The app reaches Ollama on your computer, and lists the models you've installed there.

On **Linux**, Ollama only accepts connections from the computer itself by default. Let containers reach it by starting it with `OLLAMA_HOST=0.0.0.0 ollama serve` (or the same setting in its systemd service).

### Option B: everything in containers (no Ollama needed)
Download [`docker-compose.yml`](docker-compose.yml) (or clone this repository), then in the same folder:
```bash
docker compose up -d
```
Open http://localhost:8080. The first start downloads the model, about 8 GB for `gemma3:12b`. Follow progress with `docker compose logs -f model`. The app starts once the download finishes.

- **NVIDIA GPU** (much faster): also download [`docker-compose.gpu.yml`](docker-compose.gpu.yml), then `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d`.
- **Another model:** create a `.env` file next to it (see [`.env.example`](.env.example)) with, for example, `OLLAMA_MODEL=gemma3:4b`.
- **Add more models later:** `docker compose exec ollama ollama pull llama3.2-vision`. They appear in the app's model list.

On Macs, Docker can't use the GPU. For speed, install Ollama natively and use Option A.

### Updating, stopping, your data
- **Update:** `docker pull ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2`, then recreate the container (Option A) or run `docker compose up -d` (Option B).
- **Stop / start:** `docker stop markitdown-ocr-localrag` / `docker start markitdown-ocr-localrag`, or `docker compose stop` / `docker compose start`.
- **Your data** (documents, extracted text, search indexes, chosen model) lives in a Docker volume, so it survives restarts and updates. To use a folder on your computer instead, replace the volume with a path, e.g. `-v ./outputs:/data`.

Images are published for Intel/AMD and ARM (including Apple Silicon). Releases are tagged by version, e.g. `ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2:1.0.0`.

---

## ✨ What it does

1. **Extract**: [MarkItDown](https://github.com/microsoft/markitdown) turns the document into Markdown, keeping headings, lists, and tables.
2. **Read images**: the `markitdown-ocr` plugin sends images inside documents, and scanned pages, to your local vision model (`gemma3:12b` by default), so mixed documents don't silently lose their scanned parts. With a model that can't read images, fully scanned files fall back to Tesseract OCR.
3. **Organize** (optional): the local model restructures the text into clean Markdown, part by part so long documents fit, and keeps the original text for any part where it would drop content.
4. **Ask**: hybrid search (meaning-based vectors + BM25 keywords, so exact names and numbers are found) picks the relevant passages, and the model answers using only those. In the web app, the passages are highlighted on the page.

Results are saved per document and reused next time, unless the document has changed (checked by fingerprint).

---

## 📥 Install without Docker

| What | Why | Install |
|---|---|---|
| Python 3.11 | runs the backend | [python.org](https://www.python.org/downloads/) |
| [Ollama](https://ollama.com/) + a vision model | reads images, organizes text, answers questions | `ollama pull gemma3:12b` |
| Tesseract OCR | fallback for scanned files when the model can't read images | Windows: `winget install UB-Mannheim.TesseractOCR` · Mac: `brew install tesseract` · Ubuntu: `sudo apt install tesseract-ocr` |
| Poppler | lets Tesseract read scanned PDFs | Windows: `winget install oschwartz10612.Poppler` · Mac: `brew install poppler` · Ubuntu: `sudo apt install poppler-utils` |
| Node.js 20+ | builds and runs the web app (not needed for the command line) | [nodejs.org](https://nodejs.org/) |

On Windows, Tesseract and Poppler are found in their default install folders even if they aren't on PATH.

> **Choosing a model:** `gemma3:12b` needs about 9 GB of memory. With less GPU memory it still works but part of it runs on the CPU, which is slower. `gemma3:4b` is several times faster with somewhat lower quality. See "Using another model" below.

```bash
git clone https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2.git
cd markitdown-ocr-localrag-v2
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac / Linux
pip install -r requirements.txt
ollama pull gemma3:12b
```

To build the Docker image yourself from the cloned folder: `docker compose up -d --build`, or `docker build -t markitdown-ocr-localrag .`

---

## 🖥️ Web app

From PowerShell:
```powershell
.\start.ps1
```
This starts the API (port 8000) and the web app (port 3000), then opens http://localhost:3000. The first run also installs the web app's packages. If PowerShell blocks scripts, run `powershell -ExecutionPolicy Bypass -File .\start.ps1`.

To start the two parts by hand (any OS):
```bash
python -m backend.api           # terminal 1
cd web && npm install && npm run dev   # terminal 2
```
Or build the web app once (`cd web && npm run build`) and run only `python -m backend.api`: it then serves the app too, at http://localhost:8000.

- **Add documents** with the button, or drop files anywhere on the page.
- **Extracted text / Organized** switches between the two versions; **Organize text** creates the second one.
- **Ask this document**: answers stream in and the passages they came from are highlighted. Click a passage number to jump to it.
- **Model** (bottom left) lists every model installed in Ollama. Pick one and it's used for reading images, organizing, and answering. Models that can't read images are marked "text only".
- **Delete** removes the document's folder from `outputs/`. Your original file is never touched.

## ⌨️ Command line

```bash
python cli.py
```
```
1. Extract only
2. Extract + reorganize with the LLM
3. Chat with a document (raw or organized text)
0. Exit
```
It starts by listing your installed models so you can pick one. Documents processed here also appear in the web app.

## 🐍 From Python

```python
from backend.extract import extract
from backend.organize import reorganize
from backend.rag import DocumentRAG

text = extract("report.pdf")
organized = reorganize(text)

rag = DocumentRAG(organized, index_dir="report_index")
print(rag.ask("Summarize the key points."))
```

---

## 🤖 Using another model

Install it with Ollama, and it appears in the model list (web app and command line) automatically:
```bash
ollama pull gemma3:4b
```
Your choice is saved in `outputs/settings.json` and shared by the web app and the command line. For the full experience, pick a model that can read images (for example `gemma3`, `qwen2.5vl`, or `llama3.2-vision`). With a text-only model, scanned files are read with Tesseract and images inside documents are skipped.

Switching models never breaks saved results: search uses its own embedding model, and text organized by another model stays as it is until you organize it again.

## ⚙️ Settings

All settings live in [`backend/config.py`](backend/config.py). Override any of them with an environment variable of the same name:

| Variable | Default | What it controls |
|---|---|---|
| `OLLAMA_MODEL` | `gemma3:12b` | model used until you pick one in the app |
| `OLLAMA_HOST` | `http://localhost:11434` | where Ollama is running |
| `EMBED_MODEL` | `BAAI/bge-base-en-v1.5` | embedding model for search |
| `NUM_CTX` | `8192` | how much text the model reads at once (tokens) |
| `ORGANIZE_CHUNK_CHARS` | `6000` | size of each part when organizing |
| `TOP_K` | `4` | passages taken from each search |
| `OUTPUTS_DIR` | `./outputs` | where results are saved |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | where the API listens |

Example (PowerShell):
```powershell
$env:OLLAMA_MODEL = "gemma3:4b"; .\start.ps1
```

---

## 🧩 Project structure

```
├── backend/
│   ├── config.py      settings (overridable with environment variables)
│   ├── extract.py     MarkItDown + local vision model, Tesseract fallback
│   ├── organize.py    restructures text with the local model, part by part
│   ├── rag.py         hybrid search (FAISS + BM25) and answers
│   ├── storage.py     per-document folders in outputs/, fingerprints
│   ├── settings.py    choices saved in outputs/settings.json (the selected model)
│   ├── llm.py         everything that talks to Ollama, including the installed-model list
│   └── api.py         FastAPI server for the web app (streams progress and answers, serves the built app)
├── web/               Next.js web app
├── tests/             pytest suite
├── cli.py             command-line app
├── start.ps1          starts the API and web app together
├── Dockerfile         one image: web app + API + OCR tools + search model
├── docker-compose.yml the image plus an Ollama container (docker-compose.gpu.yml adds NVIDIA GPUs)
└── outputs/           saved results, one folder per document (git-ignored)
```

Each document's folder in `outputs/` holds the uploaded original, `extracted.md`, `organized.md`, the search indexes, and a fingerprint of the document they came from.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```
The tests use a temporary outputs folder and don't need Ollama running. The search tests use the embedding model, which is downloaded once on first run.

For the web app: `cd web && npx tsc --noEmit && npm run lint`.

---

## 👨‍💻 Developed By
### **Ahmed Zeyad Tareq**  
📌 Data Scientist & AI Developer | 🎓 Master of AI Engineering
- 📞 WhatsApp: +905533333587 
- [GitHub](https://github.com/AhmedZeyadTareq) | [LinkedIn](https://www.linkedin.com/in/ahmed-zeyad-tareq) | [Kaggle](https://www.kaggle.com/ahmedzeyadtareq)


## 📄 License
MIT License © Ahmed Zeyad Tareq

---

## 🌟 Support
If you like this project, give it a ⭐ on GitHub and share!  
Got ideas for improvements? Feel free to open a Pull Request or create an Issue. 🚀
