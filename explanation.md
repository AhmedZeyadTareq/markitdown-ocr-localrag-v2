# How to run MarkItDown OCR LocalRAG with Docker: a simple guide

This guide explains, step by step, the different ways to run the app with Docker.
Read **Part 1** first. It explains the idea in two minutes, and then everything else is easy.

---

## Part 1: The big idea

### The app has two parts

| Part | What it does | Where it comes from |
|---|---|---|
| **1. The app** | The web page, reading documents (PDF, Word, …), OCR, search | The **Docker image** on GitHub |
| **2. Ollama** | Runs the AI model (`gemma3:12b`) that reads images, organizes text, and answers questions | Installed separately |

**Important:** the app image **never** contains Ollama. The app always needs an Ollama to talk to.
The only question is **where that Ollama runs**:

- **On your PC** (you installed the Ollama program yourself), or
- **Inside Docker** (Docker runs Ollama for you, so you install nothing).

### Words you will see

| Word | Simple meaning |
|---|---|
| **Docker image** | A ready-made package of the app, like an installer. Ours is stored on GitHub at `ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2`. |
| **Container** | A running copy of the image, like an installed and opened program. |
| **Volume** | A storage box Docker keeps for the app's data (your documents). It stays even if the container is deleted. |
| **Port 8080** | The "door" you open in your browser: `localhost:8080`. |

---

## Part 2: The three scenarios

| | Scenario | Ollama runs… | Do you need the code? | Who is it for |
|---|---|---|---|---|
| **1A** | Ready-made image | **On your PC** (already installed) | ❌ No | You already have Ollama ✅ (**this is you**) |
| **1B** | Ready-made image | **Inside Docker** | ❌ No (only 1 small file) | Someone who has **only Docker**, no Ollama |
| **2** | Build the image yourself | On your PC **or** inside Docker | ✅ Yes | Developers who changed the code |

```
Scenario 1A                         Scenario 1B
┌──────────── Your PC ───────────┐  ┌──────────── Your PC ─────────────────────┐
│                                │  │  ┌──────────── Docker ────────────────┐  │
│  Ollama (installed program)    │  │  │  Ollama container                  │  │
│        ▲                       │  │  │        ▲                           │  │
│        │ asks the AI           │  │  │        │ asks the AI               │  │
│  ┌── Docker ──────────────┐    │  │  │  App container                     │  │
│  │  App container         │    │  │  └────────────────────────────────────┘  │
│  └────────────────────────┘    │  │                                          │
│  Browser → localhost:8080      │  │  Browser → localhost:8080                │
└────────────────────────────────┘  └──────────────────────────────────────────┘
```

**Scenario 2** looks exactly like 1A or 1B. The only difference is that the app image is **built on your PC from the code** instead of downloaded ready-made from GitHub.

---

## Before every scenario: start Docker

1. Press the **Windows key**, type `Docker Desktop`, press **Enter**.
2. Wait until the Docker window shows **"Engine running"** (bottom left). This takes about 1 minute.
3. Press the **Windows key**, type `PowerShell`, press **Enter**. A PowerShell window opens.

> **How to run a command in this guide:** select the whole line in the grey box, press **Ctrl + C** to copy,
> click inside PowerShell, **right-click** once to paste, then press **Enter**.

---

## Scenario 1A: ready-made image + the Ollama on your PC

**Use this if:** Ollama is installed on your PC. **Downloads:** only the app image (a few GB, first time only).

### Step 1: Check Ollama has a model
Run:
```
ollama list
```
✅ You should see a line with `gemma3:12b`.
❌ If the list is empty, run this, and wait for it to finish (about 8 GB):
```
ollama pull gemma3:12b
```

### Step 2: Start the app
Run this **whole line**:
```
docker run -d --name markitdown-ocr-localrag -p 127.0.0.1:8080:8000 -v markitdown-ocr-localrag-data:/data --add-host=host.docker.internal:host-gateway ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2
```
The first time, you see `Downloading…` and `Pull complete` lines for a few minutes.
✅ At the end you see **one long line of letters and numbers** (like `3f9a1c7e…`). The app has started.

### Step 3: Wait until it's ready
Run:
```
docker ps
```
Look at the line with `markitdown-ocr-localrag`:
- `(health: starting)`: wait 30 seconds, run `docker ps` again.
- `(healthy)`: ✅ ready, go to Step 4.

### Step 4: Open the app
Open Chrome or Edge, type `localhost:8080` in the address bar, and press **Enter**.
✅ The app opens. Bottom left shows **`gemma3:12b`**, so the app is connected to your Ollama.

Then go to **Part 3: Using the app**.

---

## Scenario 1B: ready-made image + Ollama inside Docker

**Use this if:** the PC has **no Ollama**, only Docker. (It also works if Ollama is installed; it just won't use it.)
**Downloads:** the app image (a few GB) **and** the AI model again inside Docker (about 8 GB). First time only.

### Step 1: If you tried 1A before, remove it (so port 8080 is free)
```
docker rm -f markitdown-ocr-localrag
```
"No such container" is fine; it means there was nothing to remove.

### Step 2: Make a folder and go into it
```
mkdir markitdown-test; cd markitdown-test
```

### Step 3: Download the one file 1B needs
```
curl.exe -O https://raw.githubusercontent.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2/main/docker-compose.yml
```
This file (`docker-compose.yml`) tells Docker to start **3 containers**:
1. **ollama**: runs the AI.
2. **model**: downloads `gemma3:12b` once, then stops.
3. **app**: this app. It starts **after** the model download finishes.

### Step 4: Start everything
```
docker compose up -d
```

### Step 5: Watch the AI model download
```
docker compose logs -f model
```
You see the download progress. This is about 8 GB, so it can take a long time.
✅ When it says `success` and stops moving, press **Ctrl + C** to leave this view. (The app keeps running.)

### Step 6: Open the app
Open the browser, type `localhost:8080`, and press **Enter**.

Then go to **Part 3: Using the app**.

> **Want a smaller, faster model?** Before Step 4, create a file named `.env` in the `markitdown-test` folder
> containing exactly this line: `OLLAMA_MODEL=gemma3:4b`

---

## Scenario 2: build the image yourself from the code

**Use this if:** you changed the code and want to run *your* version. Otherwise use 1A or 1B.

### Step 1: If you tried 1A before, remove it
```
docker rm -f markitdown-ocr-localrag
```

### Step 2: Download the code and go into its folder
```
git clone https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag-v2.git; cd markitdown-ocr-localrag-v2
```
(No git? Download the ZIP from the GitHub page, **Code → Download ZIP**, unzip it, and open PowerShell in that folder.)

### Step 3: Build and start. Choose **one**:

**2 + your Ollama (like 1A):** run these two lines, one after the other:
```
docker build -t markitdown-ocr-localrag .
```
```
docker run -d --name markitdown-ocr-localrag -p 127.0.0.1:8080:8000 -v markitdown-ocr-localrag-data:/data --add-host=host.docker.internal:host-gateway markitdown-ocr-localrag
```

**2 + Ollama inside Docker (like 1B):** run:
```
docker compose up -d --build
```

The first build takes several minutes.

### Step 4: Open the app
Browser → `localhost:8080`. Then go to **Part 3: Using the app**.

---

## Part 3: Using the app (same in every scenario)

1. **Add a document:** click **Add documents** (top left) and choose a PDF, Word, Excel, PowerPoint file, or a photo. Or drag the file onto the page.
   ✅ The extracted text appears in the middle.
2. **Organize (optional):** click **Organize text**. The AI rewrites the text with clean headings and tables.
   Switch between **Extracted text** and **Organized** at the top.
3. **Ask a question:** type it on the right side (for example `What is this document about?`) and press **Enter**.
   ✅ The answer appears word by word. Click a passage number under the answer to jump to where it came from.
4. **Model** (bottom left): choose which AI model to use. Models marked **"text only"** can't read images or scanned pages.
5. **Delete:** removes the app's copy of a document. Your original file on your PC is never touched.

---

## Part 4: Everyday commands

Run these in PowerShell. For **1B** and **2 + compose**, first go into the same folder you started from (for example `cd markitdown-test`).

| I want to… | 1A, or 2 with `docker run` | 1B, or 2 with `docker compose` |
|---|---|---|
| Stop the app | `docker stop markitdown-ocr-localrag` | `docker compose stop` |
| Start it again | `docker start markitdown-ocr-localrag` | `docker compose start` |
| See what's wrong (logs) | `docker logs markitdown-ocr-localrag` | `docker compose logs app` |
| Get the newest version | `docker pull ghcr.io/ahmedzeyadtareq/markitdown-ocr-localrag-v2`, then `docker rm -f markitdown-ocr-localrag`, then run the Step 2 line of 1A again | `docker compose pull`, then `docker compose up -d` |
| Delete the app **and all its documents** | `docker rm -f markitdown-ocr-localrag`, then `docker volume rm markitdown-ocr-localrag-data` | `docker compose down -v` |

Your documents are **kept** when you stop, start, restart, or update. They're only deleted by the last row.

---

## Part 5: If something goes wrong

| What you see | What to do |
|---|---|
| `failed to connect to the docker API` | Docker Desktop isn't running. Start it and wait for "Engine running". |
| `localhost:8080` doesn't open | Run `docker ps`. If the app isn't listed or isn't `(healthy)`, look at the logs (Part 4). |
| "Can't reach Ollama" (1A) | Start the Ollama app on your PC (look for its icon near the clock). |
| Model list is empty | 1A: run `ollama pull gemma3:12b`. 1B: the model is still downloading, so wait (Step 5 of 1B). |
| `port is already allocated` | Something else uses 8080, often an old run of another scenario. Remove it: `docker rm -f markitdown-ocr-localrag`, or in the 1B folder: `docker compose down`. |
| `Conflict. The container name … is already in use` | You already ran 1A once. Start it with `docker start markitdown-ocr-localrag`, or remove it with `docker rm -f markitdown-ocr-localrag` and run Step 2 again. |
| Answers are very slow | Choose a smaller model such as `gemma3:4b` (run `ollama pull gemma3:4b` first in 1A). |

Still stuck? Copy everything the "logs" command shows and share it.
