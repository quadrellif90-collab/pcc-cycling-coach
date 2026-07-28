"""PCC — OCR layer per PDF BIA scansionati.

Estrae il testo dai PDF che non contengono un layer testuale (scansioni,
foto di bilance/referti) usando PyMuPDF per il rendering delle pagine e
Tesseract per il riconoscimento ottico.

Il backend chiama questa funzione da `bia_parser.parse_bia_pdf` quando il
testo nativo del PDF e' vuoto. Se Tesseract non e' installato, ritorna
una stringa vuota (il chiamante gestisce il caso "scansionato non leggibile").

Dipendenze:
  - PyMuPDF  (fitz)        -> rendering pagine in PNG
  - Tesseract OCR engine   -> binario di sistema (PATH o percorso esplicito)
  - language pack ita+eng -> in tessdata/
"""

import io
import os
import shutil
import subprocess


def _tesseract_cmd() -> str:
    """Ritorna il path del binario tesseract, o '' se non trovato."""
    _candidates = (
        "C:/Program Files/Tesseract-OCR/tesseract.exe",
        "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe",
        "/usr/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    )
    for _c in _candidates:
        if os.path.isfile(_c):
            return _c
    _found = shutil.which("tesseract")
    return _found or ""


def _tessdata_dir() -> str:
    """Trova la cartella tessdata con i language pack installati.

    Nota: Tesseract usa TESSDATA_PREFIX COME cartella dei .traineddata
    (NON ci aggiunge "/tessdata"). Quindi il prefix e' la cartella tessdata
    stessa, es. "C:/Program Files/Tesseract-OCR/tessdata".
    """
    for _cand in (
        "C:/Program Files/Tesseract-OCR/tessdata",
        "C:/Program Files (x86)/Tesseract-OCR/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tessdata",
        "/opt/homebrew/share/tessdata",
    ):
        if os.path.isdir(_cand):
            return _cand
    return ""


def _ocr_page(png_bytes: bytes, lang: str, tessdata_dir: str, tesseract_bin: str) -> str:
    """Esegue tesseract come subprocess su un PNG in memoria (pipe).

    Piu' robusto di pytesseract in ambienti con threading/import complessi
    (uvicorn, servizi Windows) perche' non dipende da pytesseract.
    """
    env = dict(os.environ)
    if tessdata_dir:
        env["TESSDATA_PREFIX"] = tessdata_dir
    try:
        proc = subprocess.run(
            [tesseract_bin, "stdin", "stdout", "-l", lang, "--psm", "6"],
            input=png_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            env=env,
        )
        if proc.returncode == 0:
            return proc.stdout.decode("utf-8", "ignore")
    except Exception:
        pass
    return ""


def ocr_pdf_text(pdf_bytes: bytes, dpi: int = 220, lang: str = "ita+eng") -> str:
    """Ritorna il testo OCR del PDF, o '' se non leggibile / OCR assente.

    Il testo e' normalizzato (spazi multipli compressi, righe vuote tagliate)
    perche' i pattern del parser BIA sono case-insensitive e tollerano
    spazi, ma non gradiscono rumore eccessivo.
    """
    tesseract_bin = _tesseract_cmd()
    if not tesseract_bin:
        return ""
    try:
        import fitz
        from PIL import Image
    except Exception:
        return ""

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return ""

    tessdata_dir = _tessdata_dir()
    chunks = []
    for pg in doc:
        try:
            pix = pg.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                img = img.convert("L")
            except Exception:
                pass
            import io as _io
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes_page = buf.getvalue()
            text = _ocr_page(png_bytes_page, lang, tessdata_dir, tesseract_bin)
            if text.strip():
                chunks.append(text)
        except Exception:
            continue

    full = "\n".join(chunks).strip()
    lines = [" ".join(ln.split()) for ln in full.splitlines() if ln.strip()]
    return "\n".join(lines)
