"""PCC — Cloud vision layer per BIA PDF (ibrido: cloud se chiave in .env).

Se e' configurata BIA_VISION_API_KEY, il PDF viene renderizzato in immagini
e inviato a un modello vision (z.ai/OpenAI-compatible) che ritorna JSON
strutturato con i campi BIA. Qualita' molto superiore a Tesseract su referti
AKERN/Biavector (virgole decimali preservate, colonne non confuse).

Config (.env):
  BIA_VISION_API_KEY=sk-...          (obbligatoria per attivare il layer)
  BIA_VISION_BASE_URL=https://api.z.ai/v1   (default z.ai)
  BIA_VISION_MODEL=glm-4v-flash      (modello vision; cambia se necessario)

Se la chiave non c'e', vision_configured() ritorna False e il chiamante
cade back su Tesseract (ocr_pdf).
"""

import os
import io
import json
import base64
import re

try:
    import fitz
except ImportError:
    fitz = None

# Prompt: chiede SOLO JSON strutturato, valori del paziente (non riferimenti)
_BIA_VISION_PROMPT = """Sei un sistema di estrazione dati da referti BIA (composizione corporea, es. AKERN Biavector, InBody, Tanita, BODYGRAM).
Leggi l'immagine e ritorna ESCLUSIVAMENTE un oggetto JSON con i valori MISURATI del paziente (NON i valori di riferimento/range tra parentesi).
Usa null se un campo non e' presente. I decimali usano la virgola italiana (es. 13,1 -> 13.1): convertili in numero con punto.
Campi:
{
  "weight_kg": number,
  "height_cm": number,
  "bmi": number,
  "fat_mass_kg": number,
  "fat_mass_pct": number,
  "fat_free_mass_kg": number,
  "fat_free_mass_pct": number,
  "tbw_l": number,
  "ecw_l": number,
  "icw_l": number,
  "hydration_pct": number,
  "bcm_kg": number,
  "smm_kg": number,
  "asmm_kg": number,
  "muscle_mass_kg": number,
  "bone_kg": number,
  "protein_kg": number,
  "protein_pct": number,
  "visceral_fat": number,
  "metabolic_age": number,
  "phase_angle": number,
  "chi": number
}
Rispondi SOLO con il JSON, senza testo aggiuntivo."""


def vision_configured() -> bool:
    return bool(os.getenv("BIA_VISION_API_KEY"))


def _render_pages(pdf_bytes: bytes, dpi: int = 72):
    if fitz is None:
        return []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        out = []
        for pg in doc:
            pix = pg.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
            # JPEG e' molto piu' leggero del PNG: evita 413 (Request Entity
            # Too Large) su endpoint come z.ai con pagine A4 ad alta risoluzione.
            out.append(("jpeg", pix.tobytes("jpeg")))
        return out
    except Exception:
        return []


def _extract_json(text: str):
    """Estrae il primo oggetto JSON da una risposta che puo' contenere
    markdown ```json ... ``` o testo spurio."""
    if not text:
        return None
    # tenta parse diretto
    try:
        return json.loads(text)
    except Exception:
        pass
    # cerca blocco ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # cerca primo { ... } bilanciato
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def extract_bia_via_vision(pdf_bytes: bytes) -> dict:
    """Renderizza il PDF e chiama il modello vision. Ritorna dict dei campi
    BIA, o None su errore/non configurato."""
    if not vision_configured():
        return None
    try:
        import httpx
    except ImportError:
        return None

    api_key = os.getenv("BIA_VISION_API_KEY")
    base_url = os.getenv("BIA_VISION_BASE_URL", "https://api.z.ai/api/paas/v4").rstrip("/")
    model = os.getenv("BIA_VISION_MODEL", "glm-4.7-flash")

    imgs = _render_pages(pdf_bytes)
    if not imgs:
        return None
    b64 = [base64.b64encode(b).decode("ascii") for _, b in imgs]
    mime = [("image/jpeg" if fmt == "jpeg" else "image/png") for fmt, _ in imgs]

    content = [{"type": "text", "text": _BIA_VISION_PROMPT}]
    for b, m in zip(b64, mime):
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{m};base64,{b}"}})

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                      "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role": "user", "content": content}],
                  "temperature": 0,
                  "response_format": {"type": "json_object"}},
            timeout=120,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(msg)
    except Exception:
        return None
