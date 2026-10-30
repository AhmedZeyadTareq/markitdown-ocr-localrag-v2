"""Uses the real embedding model (downloaded once, then cached), but not Ollama."""
from backend.rag import DocumentRAG

# Thirty near-identical sections: meaning-based search alone can't tell "12" from "21"
REPORT = "\n\n".join(
    f"## Section {i}: Workstream {i}\nWorkstream {i} is led by engineer number {i * 7}. Its budget is {i * 1000} dollars. "
    "The team reviewed requirements, wrote design notes, and ran tests on staging."
    for i in range(1, 31)
)


def test_exact_numbers_are_found(tmp_path):
    rag = DocumentRAG(REPORT, str(tmp_path / "index"), log=lambda _: None)
    top = rag.retrieve("Who leads workstream 12 and what is its budget?")[0]
    assert "Workstream 12 is led by engineer number 84" in top


def test_index_is_reused_until_text_changes(tmp_path):
    index_dir = str(tmp_path / "index")
    DocumentRAG(REPORT, index_dir, log=lambda _: None)

    messages = []
    DocumentRAG(REPORT, index_dir, log=messages.append)
    assert any("Loaded saved search index" in m for m in messages)

    messages.clear()
    DocumentRAG(REPORT + "\n\nAppendix: new text.", index_dir, log=messages.append)
    assert any("Building search index" in m for m in messages)
