"""Where processed documents live on disk, shared by the command line (cli.py) and the web API (backend/api.py).

Each document gets a folder in outputs/:
    outputs/<name>_<ext>/
        original.<ext>     uploaded file (web UI only)
        meta.json          original filename and, for the command line, the file's location
        document.sha256    fingerprint of the document the results came from
        extracted.md       raw extracted text
        organized.md       LLM-reorganized text
        index_raw/         saved search index for extracted.md
        index_organized/   saved search index for organized.md
"""
import glob
import hashlib
import json
import os
import re
import shutil

from backend import config

VERSIONS = ("raw", "organized")


def base_name(filename):
    """The file's own name. Splits on both / and \\, since uploads from Windows can carry backslash paths
    and os.path.basename on Linux (e.g. in Docker) only splits on /."""
    return re.split(r"[\\/]", filename)[-1]


def doc_id_for(filename):
    name, ext = os.path.splitext(base_name(filename))
    # Include the extension so report.pdf and report.docx don't share (and reuse) each other's outputs
    doc_id = f"{name}_{ext.lstrip('.')}" if ext else name
    doc_id = re.sub(r"_+", "_", re.sub(r"[^\w.-]+", "_", doc_id))
    return _existing_id(doc_id.strip("_.") or "document")


def _existing_id(doc_id):
    """On Windows and macOS, folder names ignore case, so Report.PDF and report.pdf share one folder.
    Use the name that folder already has, so the id matches the one the document is listed under."""
    folder = os.path.join(config.OUTPUTS_DIR, doc_id)
    if not os.path.isdir(folder):
        return doc_id
    for existing in list_doc_ids():
        if existing.lower() == doc_id.lower() and os.path.samefile(os.path.join(config.OUTPUTS_DIR, existing), folder):
            return existing
    return doc_id


def paths_for(doc_id):
    folder = os.path.join(config.OUTPUTS_DIR, doc_id)
    return {
        "folder": folder,
        "raw": os.path.join(folder, "extracted.md"),
        "organized": os.path.join(folder, "organized.md"),
        "index_raw": os.path.join(folder, "index_raw"),
        "index_organized": os.path.join(folder, "index_organized"),
        "fingerprint": os.path.join(folder, "document.sha256"),
        "meta": os.path.join(folder, "meta.json"),
    }


def output_paths(file_path):
    return paths_for(doc_id_for(file_path))


def fingerprint_bytes(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint_file(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def save_content(content, output_file, log=print):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    log(f"[✔] Content saved to {output_file}")


def load_content(input_file):
    with open(input_file, encoding="utf-8") as f:
        return f.read()


def _saved_fingerprint(paths):
    return load_content(paths["fingerprint"]).strip() if os.path.exists(paths["fingerprint"]) else None


def discard_results(paths):
    """Removes extracted and organized text. Search indexes rebuild themselves when their text changes."""
    for version in VERSIONS:
        if os.path.exists(paths[version]):
            os.remove(paths[version])


def discard_if_document_changed(file_path, paths, log=print):
    """Saved results are only reused if they came from this exact version of the document."""
    if not any(os.path.exists(paths[v]) for v in VERSIONS):
        return
    if _saved_fingerprint(paths) == fingerprint_file(file_path):
        return
    log(f"[⚠️] {os.path.basename(file_path)} has changed since it was last processed. Re-extracting...")
    discard_results(paths)


def save_extraction(content, file_path, paths, log=print):
    save_content(content, paths["raw"], log)
    with open(paths["fingerprint"], "w", encoding="utf-8") as f:
        f.write(fingerprint_file(file_path))


def read_meta(paths):
    # A damaged meta.json only loses the original filename; it mustn't break the whole library
    try:
        with open(paths["meta"], encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def write_meta(paths, **values):
    meta = read_meta(paths) | values
    os.makedirs(paths["folder"], exist_ok=True)
    with open(paths["meta"], "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def save_upload(filename, data):
    """Stores an uploaded file as the document's original. Returns its doc id."""
    doc_id = doc_id_for(filename)
    paths = paths_for(doc_id)
    os.makedirs(paths["folder"], exist_ok=True)

    # A different file under the same name makes earlier results stale
    saved = _saved_fingerprint(paths)
    if saved and saved != fingerprint_bytes(data):
        discard_results(paths)

    for old in glob.glob(os.path.join(paths["folder"], "original*")):
        os.remove(old)
    ext = os.path.splitext(base_name(filename))[1].lower()  # may be empty, e.g. for README
    with open(os.path.join(paths["folder"], f"original{ext}"), "wb") as f:
        f.write(data)
    write_meta(paths, filename=base_name(filename), source_path=None)
    return doc_id


def source_file(paths):
    """The document to (re-)extract from: the uploaded copy, or the file the command line was pointed at."""
    uploaded = glob.glob(os.path.join(paths["folder"], "original*"))
    if uploaded:
        return uploaded[0]
    source_path = read_meta(paths).get("source_path")
    return source_path if source_path and os.path.isfile(source_path) else None


def list_doc_ids():
    if not os.path.isdir(config.OUTPUTS_DIR):
        return []
    return sorted(d for d in os.listdir(config.OUTPUTS_DIR) if os.path.isdir(os.path.join(config.OUTPUTS_DIR, d)))


def delete_document(doc_id):
    shutil.rmtree(paths_for(doc_id)["folder"], ignore_errors=True)
