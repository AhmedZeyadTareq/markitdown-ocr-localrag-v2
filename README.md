# MarkItDown-OCR-LocalRAG

A powerful, modular, and local-first Python toolkit that extracts, OCRs, reorganizes, and retrieves answers from documents (PDFs, images, scanned files) using **MarkItDown**, **Tesseract OCR**, and **Local RAG** techniques with the help of **Ollama LLMs** — no cloud, no APIs, 100% private.

---

## 📥 Installation Requirements

Before using the project, ensure you have the following installed:

### 1. Python Libraries
```bash
pip install -r requirements.txt
```

### 2. Ollama (for Local Language Models)
Download and install [Ollama](https://ollama.com/) on your system. Make sure you pull a local model like `gemma:2b` or `gemma3:12b`:
```bash
ollama pull gemma:2b
```
gemma3:12b Recommended
### 3. Tesseract OCR Engine
You must install Tesseract separately because `pytesseract` is only a Python wrapper.

- **Windows:**
  - Download from: https://github.com/tesseract-ocr/tesseract
  - https://github.com/UB-Mannheim/tesseract/wiki
  - Add the Tesseract installation path (e.g., `C:\Program Files\Tesseract-OCR`) to your system PATH.

- **Linux (Ubuntu):**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

- **Mac:**
```bash
brew install tesseract
```

---

## 🚀 How It Works

The project operates in four intelligent phases:

### 1. Extract (Structured Extraction)
- Tries to extract structured content from documents using `MarkItDown`, producing clean Markdown text when possible.

### 2. OCR (Fallback Strategy)
- If `MarkItDown` fails (e.g., scanned PDF/image), automatically switches to `Tesseract OCR` to extract readable text.

### 3. Reorganize (Content Structuring)
- Uses a **local Ollama model** (e.g., `gemma3:12b`) to reorganize the raw extracted text into highly readable, structured, and corrected Markdown format.

### 4. RAG (Local Question Answering)
- Embeds the organized text with `HuggingFace sentence-transformers`.
- Stores it in a `FAISS` vector database.
- Creates a **RetrievalQA** chain that allows you to ask **contextual questions** about the content directly from your machine, fully offline.

---

## 🧩 Project Structure

```bash
markitdown-ocr-localrag/
├── src/
│   ├── __init__.py
│   ├── convert_file.py      # Extraction + OCR fallback
│   ├── rag_chat.py          # Local RAG system
│   └── markitdown_ocr_rag.py # Main orchestrator class
├── main.py                  # CLI entry point
├── requirements.txt         # Required packages
├── README.md                 # This file
```

---

## ⚡ How to Use

### 1. Clone and Setup
```bash
git clone https://github.com/AhmedZeyadTareq/markitdown-ocr-localrag.git
cd markitdown-ocr-localrag
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Make sure Tesseract OCR and Ollama are properly installed.

### 2. Run the Project
```bash
python main.py
```

You will be prompted to:
- Enter the path to your document.
- Enter your question about the document.

The system will automatically:
- Extract ➔ OCR if needed ➔ Reorganize ➔ Build RAG ➔ Answer your question.

### 3. Example Usage in Python
```python
from src.markitdown_ocr_rag import MarkitdownOCRLocalRAG
from src.rag_chat import start_rag_chat

pipeline = MarkitdownOCRLocalRAG()

organized_md = pipeline.extract_and_reorganize("example.pdf")

qa_chain = start_rag_chat(organized_md, pipeline.ollama_model)
answer = qa_chain.invoke({"query": "Summarize the key points."})["result"]
print(answer)

```

---

## 🔥 Why This Project is Powerful

- **Multi-Strategy Extraction**: Always guarantees best-effort text extraction (structured first, OCR fallback second).
- **Local First**: No internet dependencies, no API keys.
- **Privacy**: All processing remains fully on your machine.
- **High Accuracy**: Uses SOTA models from HuggingFace + Ollama.
- **Modular Design**: Easy to extend, plug-and-play components.

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

