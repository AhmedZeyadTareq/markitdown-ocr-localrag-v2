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


def _pdf_with_text_page_and_scanned_page(path, text, scanned_text):
    """Page 1 has a real text layer; page 2 is only a picture of text, like a scanned sheet."""
    import io

    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 300), "white")
    ImageDraw.Draw(image).text((40, 100), scanned_text, fill="black", font=ImageFont.load_default(size=64))
    jpeg = io.BytesIO()
    image.save(jpeg, "JPEG", quality=95)
    jpeg = jpeg.getvalue()

    text_stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    image_stream = b"q 540 0 0 135 36 600 cm /Im1 Do Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R"
        b" /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R /Resources << /XObject << /Im1 7 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(text_stream), text_stream),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(image_stream), image_stream),
        b"<< /Type /XObject /Subtype /Image /Width 1200 /Height 300 /ColorSpace /DeviceRGB /BitsPerComponent 8"
        b" /Filter /DCTDecode /Length %d >>\nstream\n%s\nendstream" % (len(jpeg), jpeg),
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(pdf))
    return str(path)


def test_scanned_pages_in_a_text_pdf_are_read_without_the_model(no_model, tmp_path):
    pdf = _pdf_with_text_page_and_scanned_page(tmp_path / "mixed.pdf", "Typed page about budgets", "INVOICE 4417")
    markdown = extract(pdf, log=lambda _: None)
    assert "Typed page about budgets" in markdown
    assert "## Scanned pages (read via OCR)" in markdown and "### Page 2" in markdown
    assert "4417" in markdown
