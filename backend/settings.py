"""Choices the user makes in the app, saved in outputs/settings.json so they survive restarts
and are shared by the web app and the command line."""
import json
import os

from backend import config


def _path():
    return os.path.join(config.OUTPUTS_DIR, "settings.json")


def _load():
    try:
        with open(_path(), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(values):
    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(_load() | values, f, indent=2)


def current_model():
    """The model picked in the app, or OLLAMA_MODEL from config if none was picked yet."""
    return _load().get("model") or config.OLLAMA_MODEL


def set_model(name):
    _save({"model": name})
