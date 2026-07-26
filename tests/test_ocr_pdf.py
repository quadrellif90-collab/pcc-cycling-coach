"""Tests for the OCR layer + parser integration (PCC 5.0).

These run WITHOUT a Tesseract binary installed, so they verify the critical
property: OCR is OPTIONAL and the app degrades gracefully (no crash, no cloud).
A scanned PDF simply reports scanned=True / empty text when Tesseract is
absent; when present, ocr_pdf.ocr_pdf_text returns the rasterized text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz
import ocr_pdf
import bia_parser
import diet_parser


def _make_scanned_pdf() -> bytes:
    """A PDF whose text layer is empty (simulates a scan)."""
    doc = fitz.open()
    page = doc.new_page()
    # no text inserted -> get_text() is empty, mimicking a scanned image
    return doc.tobytes()


def test_tesseract_unavailable_is_false():
    # On CI/this host Tesseract may or may not be present; we only assert the
    # helper returns a bool and ocr_pdf_text never raises.
    assert isinstance(ocr_pdf.tesseract_available(), bool)
    # Must not raise regardless of Tesseract presence.
    result = ocr_pdf.ocr_pdf_text(_make_scanned_pdf())
    assert result is None or isinstance(result, str)


def test_bia_parser_scanned_does_not_crash():
    out = bia_parser.parse_bia_pdf(_make_scanned_pdf())
    assert "scanned" in out
    # With no Tesseract, it stays scanned=True and returns no crash.
    assert out["scanned"] is True
    assert "reading" in out


def test_diet_parser_scanned_does_not_crash():
    out = diet_parser.parse_diet_pdf(_make_scanned_pdf())
    assert "raw_text" in out
    assert "ocr_used" in out
    assert isinstance(out["ocr_used"], bool)


def test_ocr_pdf_importable():
    assert hasattr(ocr_pdf, "ocr_pdf_text")
    assert hasattr(ocr_pdf, "tesseract_available")
