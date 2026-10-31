# MarkItDown OCR LocalRAG

[![CI](https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/actions/workflows/ci.yml)

Read any document (PDFs, Word files, slide decks, spreadsheets, scanned pages, photos), turn it into clean Markdown, and ask questions about it. Everything runs on your own computer with **MarkItDown**, **OCR**, **Ollama**, and **local RAG** search. No cloud, no API keys, nothing leaves your machine.

It comes as a web app, a command-line tool, and a ready-made Docker image.

---

## 🐳 Quick start with Docker

With Docker you don't install Python, Node.js, Tesseract, or anything else: it's all inside the image (web app, API, OCR tools, and search model). Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running.

The AI model itself runs in [Ollama](https://ollama.com/), which is separate. Either use the Ollama already on your computer, or let Docker run it for you.

### Which way?

| You want to… | Use | Download the code? |
|---|---|---|
| Just use the app, and Ollama is already installed | [1A: ready-made image + your Ollama](#1a-ready-made-image--your-ollama) | No |
| Just use the app, with no Ollama on your computer | [1B: ready-made image + Ollama in Docker](#1b-ready-made-image--ollama-in-docker) | No (one file) |
| Build the image from the code yourself (e.g. after changing it) | [2: build the image yourself](#2-build-the-image-yourself) | Yes |

Whichever you pick, the app opens at **http://localhost:8080**, only on your own computer. See [Using the app](#-using-the-app) for what to do next.

### 1A: ready-made image + your Ollama

1. Check that Ollama is running and has a model: `ollama list`. If the list is empty, run `ollama pull gemma3:12b` (or `gemma3:4b` for computers with less memory).
2. Start the app (one line, works in PowerShell, Command Prompt, and Mac/Linux terminals):
   ```bash
   docker run -d --name markitdown-ocr-localrag -p 127.0.0.1:8080:8000 -v markitdown-ocr-localrag-data:/data --add-host=host.docker.internal:host-gateway ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2
   ```
   The first time, Docker downloads the image (a few GB).
3. Open http://localhost:8080. The **Model** box (bottom left) lists the models installed in your Ollama.

What the command means:

| Part | Meaning |
|---|---|
| `-d` | runs in the background, so you can close the terminal |
| `--name markitdown-ocr-localrag` | a name for stopping and starting it later |
| `-p 127.0.0.1:8080:8000` | the app is at `localhost:8080`, reachable only from this computer |
| `-v markitdown-ocr-localrag-data:/data` | your documents and results are kept in a Docker volume, so they survive restarts and updates |
| `--add-host=host.docker.internal:host-gateway` | lets the app reach the Ollama running on your computer |

On **Linux**, Ollama only accepts connections from the computer itself by default. Let containers reach it by starting it with `OLLAMA_HOST=0.0.0.0 ollama serve` (or the same setting in its systemd service).

### 1B: ready-made image + Ollama in Docker

You only need one file, [`docker-compose.yml`](docker-compose.yml). It describes three containers: **ollama** (runs the AI model), **model** (downloads the model once, then stops), and **app** (this app, which starts after the download).

1. Make a folder and download the file into it:
   ```bash
   mkdir markitdown
   cd markitdown
   curl -O https://raw.githubusercontent.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/main/docker-compose.yml
   ```
   In Windows PowerShell, type `curl.exe` instead of `curl`. Or open the link in a browser and save the file.
2. *(Optional)* Use a smaller model: in the same folder, create a file named `.env` containing `OLLAMA_MODEL=gemma3:4b` (see [`.env.example`](.env.example)). Do this before the first start.
3. Start everything:
   ```bash
   docker compose up -d
   ```
   The first start downloads the model, about 8 GB for `gemma3:12b`. Follow it with `docker compose logs -f model`.
4. When the download finishes, open http://localhost:8080.

- **NVIDIA GPU** (much faster): also download [`docker-compose.gpu.yml`](docker-compose.gpu.yml) into the folder (same `curl` command, ending in `docker-compose.gpu.yml`), then start with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d`.
- **Add more models later:** `docker compose exec ollama ollama pull llama3.2-vision`. They appear in the app's model list.
- On **Macs**, Docker can't use the GPU. For speed, install Ollama natively and use 1A.

### 2: build the image yourself

Building needs the code, but still nothing besides Docker.

1. Get the code: `git clone https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2.git`, or [download the ZIP](https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/archive/refs/heads/main.zip) and unzip it. Then open a terminal in that folder (`cd markitdown-ocr-localrag-v2`).
2. Build and start. The first build takes several minutes.
   - **With your own Ollama** (like 1A):
     ```bash
     docker build -t markitdown-ocr-localrag .
     docker run -d --name markitdown-ocr-localrag -p 127.0.0.1:8080:8000 -v markitdown-ocr-localrag-data:/data --add-host=host.docker.internal:host-gateway markitdown-ocr-localrag
     ```
   - **With Ollama in Docker** (like 1B):
     ```bash
     docker compose up -d --build
     ```
3. Open http://localhost:8080. After changing the code, run the same build command again (for `docker run`, remove the old container first with `docker rm -f markitdown-ocr-localrag`).

### Stop, update, remove

| | 1A / 2 with `docker run` | 1B / 2 with `docker compose` |
|---|---|---|
| Stop | `docker stop markitdown-ocr-localrag` | `docker compose stop` |
| Start again | `docker start markitdown-ocr-localrag` | `docker compose start` |
| See logs | `docker logs -f markitdown-ocr-localrag` | `docker compose logs -f app` |
| Update to the latest version | `docker pull ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2`, then `docker rm -f markitdown-ocr-localrag`, then the `docker run` command again | `docker compose pull`, then `docker compose up -d` |
| Remove the app and **all its documents** | `docker rm -f markitdown-ocr-localrag`, then `docker volume rm markitdown-ocr-localrag-data` | `docker compose down -v` |

If you built the image yourself (2), updating means getting the new code (`git pull`) and building again.

**Your data** (documents, extracted text, search indexes, chosen model) lives in a Docker volume, so stopping, restarting, and updating never lose it. To keep it in a folder on your computer instead, replace the volume with a path, e.g. `-v ./outputs:/data`.

Images are published for Intel/AMD and ARM (including Apple Silicon). Releases are tagged by version, e.g. `ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2:1.0.0`.

### Troubleshooting

| Problem | Fix |
|---|---|
| The page doesn't open | Is Docker Desktop running? Check that the app is up with `docker ps` (or `docker compose ps`), and look at the logs (see above) |
| "Can't reach Ollama" (1A) | Start the Ollama app on your computer. On Linux, see the note in 1A |
| The model list is empty | 1A: `ollama pull gemma3:12b`. 1B: wait until the model download finishes |
| Port 8080 is already in use | Use another port: change `127.0.0.1:8080:8000` to e.g. `127.0.0.1:8090:8000` and open `localhost:8090` (in 1B, edit it in `docker-compose.yml`) |
| Answers are very slow | Pick a smaller model such as `gemma3:4b`, or use the NVIDIA GPU setup |
| Scanned pages or pictures aren't read well | Pick a model that can read images (not marked "text only") in the **Model** box |

---

## 🧭 Using the app

The same whether you run it with Docker or without it (see Web app below).

1. **Add documents**: click **Add documents**, or drop files anywhere on the page (PDF, Word, PowerPoint, Excel, HTML, text, images, and more). Each one is read automatically.
2. **Read the text**: the middle of the page shows what was extracted. **Organize text** asks the model to restructure it into clean headings, lists, and tables. **Extracted text / Organized** switches between the two versions.
3. **Ask this document**: type a question on the right. The answer streams in, using only the document, and the passages it came from are highlighted. Click a passage number to jump to it.
4. **Model** (bottom left) lists every model installed in Ollama. Pick one and it's used for reading images, organizing, and answering. Models that can't read images are marked "text only".
5. **Delete** removes the app's copy of a document and everything saved for it. Your original file is never touched.

---

## ✨ What it does

1. **Extract**: [MarkItDown](https://github.com/microsoft/markitdown) turns the document into Markdown, keeping headings, lists, and tables.
2. **Read images**: the `markitdown-ocr` plugin sends images inside documents, and scanned pages, to your local vision model (`gemma3:12b` by default), so mixed documents don't silently lose their scanned parts. With a model that can't read images, scanned files and scanned pages inside PDFs are read with Tesseract OCR instead (images inside other documents are skipped).
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

See [Using the app](#-using-the-app) for what to do once it's open.

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
| `WEB_ORIGINS` | *(none)* | extra web addresses allowed to use the API, comma-separated (e.g. behind a reverse proxy) |

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
