import os

import pytest

from backend import storage


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("report.pdf", "report_pdf"),
        ("My Report (v2).PDF", "My_Report_v2_PDF"),
        (r"C:\docs\..\evil.txt", "evil_txt"),
        ("../../etc/passwd", "passwd"),
        ("notes", "notes"),
        ("...", "document"),
    ],
)
def test_doc_id_is_safe_and_readable(filename, expected):
    assert storage.doc_id_for(filename) == expected


def test_same_name_different_extension_get_separate_folders():
    assert storage.doc_id_for("report.pdf") != storage.doc_id_for("report.docx")


def test_results_kept_while_document_unchanged(make_file):
    doc = make_file("memo.txt", "version one")
    paths = storage.output_paths(doc)
    storage.save_extraction("extracted text", doc, paths, log=lambda _: None)

    storage.discard_if_document_changed(doc, paths, log=lambda _: None)

    assert os.path.exists(paths["raw"])


def test_results_discarded_when_document_changes(make_file):
    doc = make_file("memo.txt", "version one")
    paths = storage.output_paths(doc)
    storage.save_extraction("extracted text", doc, paths, log=lambda _: None)
    storage.save_content("organized text", paths["organized"], log=lambda _: None)

    make_file("memo.txt", "version two")
    messages = []
    storage.discard_if_document_changed(doc, paths, log=messages.append)

    assert not os.path.exists(paths["raw"])
    assert not os.path.exists(paths["organized"])
    assert "has changed" in messages[0]


def test_results_without_fingerprint_are_not_trusted(make_file):
    doc = make_file("old.txt", "text")
    paths = storage.output_paths(doc)
    storage.save_content("from an older version of the app", paths["raw"], log=lambda _: None)

    storage.discard_if_document_changed(doc, paths, log=lambda _: None)

    assert not os.path.exists(paths["raw"])


def test_uploading_same_file_again_keeps_results():
    doc_id = storage.save_upload("a.txt", b"hello")
    paths = storage.paths_for(doc_id)
    original = storage.source_file(paths)
    storage.save_extraction("hello", original, paths, log=lambda _: None)

    storage.save_upload("a.txt", b"hello")

    assert os.path.exists(paths["raw"])


def test_uploading_different_file_under_same_name_discards_results():
    doc_id = storage.save_upload("a.txt", b"hello")
    paths = storage.paths_for(doc_id)
    storage.save_extraction("hello", storage.source_file(paths), paths, log=lambda _: None)

    storage.save_upload("a.txt", b"something else")

    assert not os.path.exists(paths["raw"])
    with open(storage.source_file(paths), "rb") as f:
        assert f.read() == b"something else"


def test_upload_without_extension_can_be_found_and_replaced():
    doc_id = storage.save_upload("README", b"first")
    paths = storage.paths_for(doc_id)
    assert storage.source_file(paths) is not None

    storage.save_upload("README", b"second")

    assert len(os.listdir(paths["folder"])) == 2  # the original and meta.json
    with open(storage.source_file(paths), "rb") as f:
        assert f.read() == b"second"


def test_source_file_falls_back_to_original_location(make_file):
    doc = make_file("cli.txt", "text")
    paths = storage.output_paths(doc)
    storage.write_meta(paths, filename="cli.txt", source_path=doc)
    assert storage.source_file(paths) == doc

    os.remove(doc)
    assert storage.source_file(paths) is None


def test_delete_removes_only_the_documents_folder(make_file):
    doc = make_file("keep.txt", "text")
    doc_id = storage.save_upload("keep.txt", b"text")

    storage.delete_document(doc_id)

    assert doc_id not in storage.list_doc_ids()
    assert os.path.exists(doc), "the user's own file must never be deleted"


def test_damaged_meta_doesnt_break_the_document():
    doc_id = storage.save_upload("a.txt", b"hello")
    paths = storage.paths_for(doc_id)
    with open(paths["meta"], "w", encoding="utf-8") as f:
        f.write("{not json")
    assert storage.read_meta(paths) == {}


def test_differently_cased_upload_uses_the_existing_folders_name(outputs):
    storage.save_upload("Report.PDF", b"%PDF")
    if not os.path.isdir(os.path.join(str(outputs), "report_pdf")):
        pytest.skip("this file system tells Report_PDF and report_pdf apart, so they're separate documents")
    assert storage.doc_id_for("report.pdf") == "Report_PDF"
    assert storage.list_doc_ids() == ["Report_PDF"]
