"""Have the local model restructure extracted text into clean Markdown, without losing content."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend import config, llm

SYSTEM_PROMPT = (
    "You're a Markdown organizer. Reorganize the content for clarity, structure, and readability. "
    "Do not delete or summarize any content. Preserve all original information exactly as-is, "
    "just improve its organization and Markdown formatting. Keep the original heading levels. "
    "Output only the reorganized Markdown, with no introduction, notes, or closing remarks."
)


def reorganize(text, log=print, on_progress=None):
    """Works part by part so long documents fit in the model's context window.
    on_progress(done, total) is called before each part and once at the end."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=config.ORGANIZE_CHUNK_CHARS, chunk_overlap=0)
    chunks = splitter.split_text(text)

    parts = []
    for i, chunk in enumerate(chunks, 1):
        log(f"[🧠] Reorganizing part {i}/{len(chunks)}...")
        if on_progress:
            on_progress(i - 1, len(chunks))
        organized = llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Rewrite the following content in markdown format and fix it:\n{chunk}"},
        ]).strip()

        if len(organized) < config.MIN_KEPT_RATIO * len(chunk):
            log(f"[⚠️] Part {i} came back too short (model likely dropped content), keeping it as extracted.")
            organized = chunk
        parts.append(organized)

    if on_progress:
        on_progress(len(chunks), len(chunks))
    log("[✔] Content reorganized.")
    return "\n\n".join(parts)
