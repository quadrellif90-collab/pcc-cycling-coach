"""PCC — OCR layer for scanned PDFs (BIA / blood-panel / diet exports).

Local-first: no cloud OCR. Uses PyMuPDF (fitz) to rasterize each page and
pytesseract to read it. Tesseract is an OPTIONAL external binary — if it is
not installed, :func:`ocr_pdf_text` returns ``None`` and the caller falls
back to its existing "scanned PDF, paste values" UX (no crash, no cloud).

The Windows installer bundles Tesseract; the CI build installs it via
``choco install tesseract`` and points ``pytesseract.tesseract_cmd`` at the
choco path so the bundled EXE works out of the box.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

try:
    import pytesseract
except Exception:  # pragma: no cover - wrapper import is mandatory at runtime
    pytesseract = None

# Common places a Tesseract binary may live (Windows choco, Winget, manual).
_TESSERACT_CANDIDATES = (
    "tesseract",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Siviglino\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
)


def _local_tesseract_candidates():
    """Tesseract bundled next to the running EXE (PyInstaller onefile/folder)."""
    import sys
    exe_dir = getattr(sys, "executable", "")
    if not exe_dir:
        return []
    base = Path(exe_dir).parent
    return [
        str(base / "tesseract.exe"),
        str(base / "tesseract_bin" / "tesseract.exe"),
    ]


def _tesseract_cmd() -> Optional[str]:
    """Return a usable tesseract binary path, or None if absent."""
    for cand in list(_TESSERACT_CANDIDATES) + _local_tesseract_candidates():
        if cand == "tesseract":
            if shutil.which("tesseract"):
                return "tesseract"
        elif os.path.exists(cand):
            return cand
    return None


def tesseract_available() -> bool:
    """True if a Tesseract binary is reachable (OCR will work)."""
    return _tesseract_cmd() is not None


def _configure() -> bool:
    """Point pytesseract at the binary if present; return False if OCR unusable."""
    if pytesseract is None:
        return False
    cmd = _tesseract_cmd()
    if cmd is None:
        return False
    try:
        pytesseract.pytesseract.tesseract_cmd = cmd
        # When bundled next to the EXE, tessdata lives in <exe_dir>/tessdata.
        import sys
        base = Path(getattr(sys, "executable", "")).parent
        td = base / "tessdata"
        if td.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(td)
    except Exception:
        pass
    return True


def ocr_pdf_text(pdf_bytes: bytes, lang: str = "eng+ita") -> Optional[str]:
    """OCR a scanned PDF. Returns extracted text, or None if OCR unavailable
    or the PDF yields no text (caller should fall back to manual entry).

    Args:
        pdf_bytes: raw PDF file content.
        lang: Tesseract language string (e.g. "eng+ita" for EN+IT).
    """
    if not _configure():
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None
    pages_text: list[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(img_bytes))
                text = pytesseract.image_to_string(img, lang=lang)
            except Exception:
                # fall back to raw pixmap buffer if PIL import path hiccups
                text = pytesseract.image_to_string(io.BytesIO(img_bytes), lang=lang)
            pages_text.append(text or "")
    finally:
        doc.close()
    joined = "\n".join(pages_text).strip()
    return joined or None


def ocr_pdf_file(path: str, lang: str = "eng+ita") -> Optional[str]:
    """Convenience wrapper: OCR a PDF on disk."""
    try:
        with open(path, "rb") as fh:
            return ocr_pdf_text(fh.read(), lang=lang)
    except Exception:
        return None
