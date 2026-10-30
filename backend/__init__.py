"""Local document reading: extraction, OCR, organizing, and question answering, all on this computer."""
import os
import warnings

from backend import config

warnings.filterwarnings("ignore", category=DeprecationWarning)

# These must be set before Hugging Face libraries are imported
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")


def _embedding_model_cached():
    hub = os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface"), "hub")
    return os.path.isdir(os.path.join(hub, "models--" + config.EMBED_MODEL.replace("/", "--")))


# Once the embedding model is downloaded, stop Hugging Face from checking the internet for updates on every start
if _embedding_model_cached():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
