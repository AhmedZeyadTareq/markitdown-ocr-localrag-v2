import pytest

from backend.extract import clean_markdown, extract


def test_ocr_markers_become_plain_paragraphs():
    markdown = "## Page 2\n\n*[Image OCR]\nThe codename is Falcon.\n\nLaunch: March 3.\n[End OCR]*\n"
    assert clean_markdown(markdown) == "## Page 2\n\nThe codename is Falcon.\n\nLaunch: March 3.\n"


def test_text_documents_extract_without_the_model(no_model, make_file):
    doc = make_file("notes.md", "# Notes\n\nThe office wifi password is ORANGE-77.")
    assert "ORANGE-77" in extract(doc, log=lambda _: None)


def test_empty_document_explains_why_it_failed(no_model, make_file):
    doc = make_file("empty.txt", "")
    with pytest.raises(ValueError, match="No text found"):
        extract(doc, log=lambda _: None)
