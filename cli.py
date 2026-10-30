"""Command-line version of the app. Run with: python cli.py"""
import sys

# Windows consoles default to cp1252, which can't print the emoji status messages
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os

from backend import config, llm, storage
from backend.extract import extract
from backend.organize import reorganize
from backend.rag import DocumentRAG

MENU = """
Choose an option:
1. Extract only
2. Extract + reorganize with the LLM
3. Chat with a document
0. Exit
"""


def ask_yes_no(prompt, default=True):
    answer = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not answer else answer.startswith("y")


def ask_file_path():
    while True:
        file_path = input("Enter the path to your document: ").strip().strip('"')
        if os.path.isfile(file_path):
            return file_path
        print(f"[❌] File not found: {file_path}")


def get_extracted(file_path, paths):
    if os.path.exists(paths["raw"]) and ask_yes_no(f"Found saved extraction ({paths['raw']}). Reuse it?"):
        return storage.load_content(paths["raw"])
    content = extract(file_path)
    storage.save_extraction(content, file_path, paths)
    return content


def get_organized(file_path, paths):
    if os.path.exists(paths["organized"]) and ask_yes_no(f"Found saved organized version ({paths['organized']}). Reuse it?"):
        return storage.load_content(paths["organized"])
    organized = reorganize(get_extracted(file_path, paths))
    storage.save_content(organized, paths["organized"])
    return organized


def chat(text, index_dir):
    rag = DocumentRAG(text, index_dir)
    print("\n[✅] Document is ready! You can now ask questions. Type 'q' to quit.\n")
    while True:
        question = input("Enter your question: ").strip()
        if not question:
            continue
        if question.lower() == "q":
            print("Exiting chat.")
            break
        print("\nAnswer:\n", rag.ask(question), "\n")


def run_option(choice):
    file_path = ask_file_path()
    paths = storage.output_paths(file_path)
    storage.discard_if_document_changed(file_path, paths)
    # Lets the web UI list this document and re-extract it from its original location
    storage.write_meta(paths, filename=os.path.basename(file_path), source_path=os.path.abspath(file_path))

    if choice == "1":
        storage.save_extraction(extract(file_path), file_path, paths)

    elif choice == "2":
        organized = reorganize(get_extracted(file_path, paths))
        storage.save_content(organized, paths["organized"])

    elif choice == "3":
        print("Chat over which version?\n  r. Raw extracted text (faster, exactly as in the document)\n  o. LLM-organized text")
        if input("Enter r / o: ").strip().lower() == "o":
            chat(get_organized(file_path, paths), paths["index_organized"])
        else:
            chat(get_extracted(file_path, paths), paths["index_raw"])


def choose_model():
    status = llm.status()
    if not status["ollama"]:
        print("[⚠️] Ollama isn't running: only extraction of text documents will work. Start the Ollama app for the rest.")
        return
    if not status["models"]:
        print(f"[⚠️] No models installed. Run: ollama pull {config.OLLAMA_MODEL}")
        return

    print("\nInstalled models:")
    for i, m in enumerate(status["models"], 1):
        marker = "*" if m["name"] == status["model"] else " "
        details = ", ".join(filter(None, [m["parameters"], "reads images" if m["vision"] else "text only"]))
        print(f" {marker} {i}. {m['name']} ({details})")

    default = status["model"] if status["model_available"] else status["models"][0]["name"]
    while True:
        answer = input(f"Choose a model [Enter = {default}]: ").strip()
        if not answer:
            name = default
            break
        if answer.isdigit() and 1 <= int(answer) <= len(status["models"]):
            name = status["models"][int(answer) - 1]["name"]
            break
        print("Enter a number from the list.")

    llm.select_model(name)
    if not next(m for m in status["models"] if m["name"] == name)["vision"]:
        print(f"[⚠️] {name} can't read images: scanned files will use Tesseract, and images inside documents are skipped.")
    print(f"Using {name}.")


def main():
    choose_model()
    print(f"Results are saved in {config.OUTPUTS_DIR}")
    while True:
        print(MENU)
        choice = input("Enter 0 / 1 / 2 / 3: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        if choice not in ("1", "2", "3"):
            print("Invalid choice, try again.")
            continue

        try:
            run_option(choice)
        except Exception as e:
            print(f"[❌] {llm.friendly_error(e)}")


if __name__ == "__main__":
    main()
