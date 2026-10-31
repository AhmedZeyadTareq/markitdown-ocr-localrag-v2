"""Turn a document into Markdown text.

MarkItDown handles the structure (PDF, Word, PowerPoint, Excel, HTML, ...). With the local vision model
available, its markitdown-ocr plugin also reads images inside documents and scanned pages. Tesseract is the
fallback for fully scanned files when the model isn't available.
"""
import glob
import os
import re
import shutil

import pytesseract
from markitdown import MarkItDown
from pdf2image import convert_from_path
from PIL import Image

from backend import llm

# On Windows these tools are often installed but missing from PATH, so look in their usual install locations
if not shutil.which("tesseract"):
    _default_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default_tesseract):
        pytesseract.pytesseract.tesseract_cmd = _default_tesseract

POPPLER_PATH = None
if not shutil.which("pdfinfo"):
    _candidates = glob.glob(os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\oschwartz10612.Poppler_*\poppler-*\Library\bin"))
    if _candidates:
        POPPLER_PATH = sorted(_candidates)[-1]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

# MarkItDown's default image prompt asks for a "caption", which makes the model invent text
VISION_PROMPT = (
    "Transcribe all text in this image exactly as written, in reading order. Format tables as Markdown tables. "
    "Do not add, guess, summarize, or comment. If the image contains no text, describe its content in one factual sentence. "
    "Output only the transcription."
)

# The OCR plugin wraps text read from images in "*[Image OCR] ... [End OCR]*", which renders as one italic line
OCR_MARKERS = re.compile(r"\*\[Image OCR\]\s*(.*?)\s*\[End OCR\]\*", re.DOTALL)


def clean_markdown(markdown):
    return OCR_MARKERS.sub(lambda m: m.group(1).strip(), markdown)


def _build_markitdown(status, log):
    if status["vision"]:
        log(f"[👁️] Images and scanned pages will be read by {status['model']}.")
        return MarkItDown(
            enable_plugins=True,
            llm_client=llm.vision_client(),
            llm_model=status["model"],
            llm_prompt=VISION_PROMPT,
        )
    if status["model_available"]:
        reason = f"{status['model']} can't read images"
    else:
        reason = "The model isn't available"
    log(f"[⚠️] {reason}: images inside documents will be skipped (Tesseract reads scanned pages).")
    return MarkItDown()


def _tesseract(file_path, log):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
    elif ext in IMAGE_EXTENSIONS:
        images = [Image.open(file_path)]
    else:
        raise ValueError(f"No text found, and OCR doesn't support {ext or 'this'} files.")

    text = "\n\n".join(pytesseract.image_to_string(img, lang="eng").strip() for img in images)
    if not text.strip():
        raise ValueError("No text found in this document, even with OCR.")
    log("[✔] Text extracted via OCR.")
    return text


def _textless_pdf_pages(file_path):
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer

    return [
        number for number, page in enumerate(extract_pages(file_path), 1)
        if not any(isinstance(element, LTTextContainer) and element.get_text().strip() for element in page)
    ]


def _ocr_scanned_pdf_pages(file_path, log):
    """Without a model that reads images, MarkItDown skips scanned pages in a PDF that also has text pages.
    Reads those pages with Tesseract and returns them as a section to add at the end, or "" if there are none."""
    try:
        pages = _textless_pdf_pages(file_path)
        if not pages:
            return ""
        log(f"[🔁] Page(s) {', '.join(map(str, pages))} have no text layer, reading them via OCR...")
        sections = []
        for number in pages:
            image = convert_from_path(file_path, first_page=number, last_page=number, poppler_path=POPPLER_PATH)[0]
            text = pytesseract.image_to_string(image, lang="eng").strip()
            if text:
                sections.append(f"### Page {number}\n\n{text}")
    except Exception as e:
        log(f"[⚠️] Couldn't read the scanned pages via OCR: {e}")
        return ""
    if not sections:
        return ""
    log(f"[✔] {len(sections)} scanned page(s) read via OCR, added at the end.")
    return "\n\n## Scanned pages (read via OCR)\n\n" + "\n\n".join(sections)


def extract(file_path, log=print):
    status = llm.status()
    try:
        log("[🔍] Trying structured text extraction via MarkItDown...")
        markdown = _build_markitdown(status, log).convert(file_path).markdown
        if markdown.strip():
            log("[✔] Markdown extracted via MarkItDown.")
            markdown = clean_markdown(markdown)
            if not status["vision"] and file_path.lower().endswith(".pdf"):
                markdown += _ocr_scanned_pdf_pages(file_path, log)
            return markdown
        log("[⚠️] No text found via MarkItDown, falling back to OCR...")
    except Exception as e:
        log(f"[❌] MarkItDown failed: {e}")
        log("[🔁] Falling back to OCR...")

    try:
        return _tesseract(file_path, log)
    except Exception as e:
        log(f"[❌] OCR failed: {e}")
        raise
