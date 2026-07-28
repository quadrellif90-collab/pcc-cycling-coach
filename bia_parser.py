"""PCC — Parser BIA (Body Impedance Analysis) + mappatura Intervals.icu.

Flusso ibrido (vedi parse_bia_pdf):
  1. testo nativo presente -> parse_bia_text (regex robusto)
  2. PDF scansionato + chiave cloud vision in .env -> bia_vision (modello z.ai)
  3. PDF scansionato + Tesseract -> OCR -> parse_bia_text
  4. nessun testo / nessun OCR -> scanned=True (UI chiede import manuale)

Il parser testuale e' ispirato a NutriCoach (normalizzazione virgola->
punto PRIMA di rimuovere la punteggiatura + sanity-check post-estrazione:
ECW>TBW => ECW=TBW-ICW, PhA fuori 1-20 gradi scartato). Questo risolve
il bug AKERN dove la virgola decimale italiana sparisce e i valori di
riferimento vengono scambiati per la misurazione.

Campi estratti:
  weight_kg, height_cm, bmi,
  fat_mass_kg, fat_mass_pct, fat_free_mass_kg, fat_free_mass_pct,
  tbw_l, ecw_l, icw_l, hydration_pct,
  bcm_kg, smm_kg, asmm_kg, muscle_mass_kg,
  bone_kg, protein_kg, protein_pct,
  visceral_fat, metabolic_age, phase_angle, chi
"""

import re
import json
import unicodedata
from dataclasses import dataclass, asdict
from typing import Optional


# ── Pattern di estrazione (etichetta -> campo) ────────────────────────────────
# Ogni campo puo' avere piu' varianti IT/EN. I pattern catturano il primo
# numero valido DOPO l'etichetta, gestendo unita' attaccate (75.2kg, 43.0L, 74°).
_FIELD_PATTERNS = {
    "weight_kg": [r"peso", r"weight", r"body weight", r"\bwt\b"],
    "height_cm": [r"altezza", r"height", r"statura", r"\bht\b"],
    "bmi": [r"bmi", r"imc", r"indice di massa corporea"],
    "fat_mass_kg": [r"massa grassa", r"fat mass", r"\bf\.?m\.?", r"\bfm\b"],
    "fat_mass_pct": [r"massa grassa", r"fat mass", r"\bf\.?m\.?", r"\bfm\b",
                     r"percentuale di grasso"],
    "fat_free_mass_kg": [r"massa magra", r"fat free", r"\bf\.?f\.?m\.?", r"\bffm\b"],
    "fat_free_mass_pct": [r"massa magra", r"fat free", r"\bffm\b"],
    "tbw_l": [r"acqua totale", r"total body water", r"\btbw\b"],
    "ecw_l": [r"acqua extra", r"extracellular", r"\becw\b"],
    "icw_l": [r"acqua intra", r"intracellular", r"\bicw\b"],
    "hydration_pct": [r"idratazione", r"hydration", r"tbw/ffm"],
    "bcm_kg": [r"massa cellulare", r"body cell", r"\bbcm\b"],
    "smm_kg": [r"massa muscolo", r"skeletal muscle", r"\bsmm\b", r"\bmms\b"],
    "asmm_kg": [r"massa muscolare appendicolare", r"appendicular", r"\basmm\b"],
    "muscle_mass_kg": [r"massa muscolare", r"muscle mass"],
    "bone_kg": [r"massa ossea", r"bone mass"],
    "protein_kg": [r"massa proteica", r"proteine", r"protein"],
    "protein_pct": [r"massa proteica", r"proteine", r"protein"],
    "visceral_fat": [r"grasso viscerale", r"visceral fat"],
    "metabolic_age": [r"eta metabolica", r"metabolic age"],
    "phase_angle": [r"angolo di fase", r"phase angle", r"\bpha\b", r"ph a"],
    "chi": [r"indice nutrizionale", r"\(chi\)"],
}

# unita' numeriche: cattura numero (decimale, virgola o punto)
_NUM = r"(-?\d+(?:[.,]\d+)?)"


def _norm(s: str) -> str:
    """Normalizza: minuscolo, accenti rimossi, virgola->punto PRIMA di
    rimuovere la punteggiatura (cosi' i decimali 75,2 non diventano 752)."""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(",", ".")
    s = re.sub(r"[^a-z0-9 .]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_field(label: str):
    n = _norm(label)
    for field, patterns in _FIELD_PATTERNS.items():
        for p in patterns:
            if p in n:
                return field
    return None


def _parse_number(token: str):
    m = re.search(_NUM, token.replace(",", "."))
    return float(m.group(1)) if m else None


def parse_bia_text(text: str) -> dict:
    """Estrae i campi BIA da testo (PDF testuale o OCR incollato).

    Robusto a: righe multiple o blob unico, unita' attaccate al numero,
    varianti IT/EN, virgola decimale italiana. Sanity-check post-estrazione
    per rumore OCR AKERN (ECW>TBW => ECW=TBW-ICW; PhA fuori 1-20 scartato).
    """
    norm = _norm(text)
    fields = {}
    for field, patterns in _FIELD_PATTERNS.items():
        if field in fields:
            continue
        for p in patterns:
            pat = r"(?<![a-z])" + re.escape(p.strip()) + r"(?![a-z])"
            for m in re.finditer(pat, norm):
                after = norm[m.end(): m.end() + 30]
                if field in ("tbw_l", "ecw_l", "icw_l"):
                    # preferisci numero seguito da 'l' (litri)
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*[lL]\b", after)
                elif field == "phase_angle":
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*[°\u00b0]|"
                                   r"\(\s*(\d+(?:\.\d+)?)\s*deg", after)
                elif field in ("fat_mass_pct", "fat_free_mass_pct", "protein_pct",
                               "hydration_pct"):
                    # cerca numero seguito da '%'
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*%", after)
                elif field in ("fat_mass_kg", "fat_free_mass_kg", "bcm_kg",
                               "smm_kg", "asmm_kg", "muscle_mass_kg", "bone_kg",
                               "protein_kg", "weight_kg"):
                    # cerca numero seguito da 'kg'
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*kg\b", after)
                elif field in ("height_cm",):
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*cm\b", after)
                elif field == "chi":
                    # AKERN: "Indice nutrizionale (CHI) 109.16 (mg...)"
                    # L'OCR puo' inserire rumore. Strategia:
                    # 1) cerca "(chi) NUM"
                    # 2) tra i numeri nei 50 char, prendi quello che (da solo
                    #    o /10) rientra nel range CHI (40-600); preferisci il
                    #    piu' vicino alla label.
                    nm = re.search(r"\(chi\)\s*\(?\s*(\d+(?:\.\d+)?)", after)
                    if not nm:
                        cands = re.findall(r"(\d+(?:\.\d+)?)", after[:50])
                        for c in cands:
                            v = float(c)
                            if 40 <= v <= 600 or (v > 600 and v / 10 <= 600):
                                nm = re.match(r"(\d+(?:\.\d+)?)", c)
                                break
                elif field == "visceral_fat":
                    nm = re.search(r"\(?\s*(\d+(?:\.\d+)?)", after)
                else:
                    nm = re.search(r"\(?\s*(?<![a-z0-9.])(\d+(?:\.\d+)?)", after)
                if nm:
                    val = float(nm.group(1))
                    fields[field] = val
                    break
            if field in fields:
                break

    # Sanity-check post-estrazione (rumore OCR AKERN/Biavector)
    f = fields
    if f.get("tbw_l") and f.get("icw_l") and f.get("ecw_l") and f["ecw_l"] > f["tbw_l"]:
        f["ecw_l"] = round(f["tbw_l"] - f["icw_l"], 1)
    if f.get("phase_angle") is not None and (f["phase_angle"] > 20 or f["phase_angle"] < 1):
        f.pop("phase_angle", None)
    # OCR puo' perdere la virgola sui litri (43.0L -> 430L) o su CHI
    # (109.16 -> 1091.6). Se un valore e' ~10x fuori range e diviso per 10
    # rientra, correggilo.
    for _k in ("tbw_l", "ecw_l", "icw_l", "chi"):
        v = f.get(_k)
        if v is not None:
            lo, hi = _BIA_RANGES.get(_k, (0, 1e9))
            if v > hi and v / 10.0 <= hi:
                f[_k] = round(v / 10.0, 1)

    return {"fields": f, "raw_lines": len([l for l in text.splitlines() if l.strip()])}


def parse_bia_vision_json(data: dict) -> dict:
    """Mappa il JSON strutturato ritornato dal modello vision (z.ai/OpenAI)
    nei campi BIA. I valori fuori range vengono scartati (il modello puo'
    ancora sbagliare), ma applichiamo il sanity-check /10 per la virgola
    decimale persa (es. CHI 1091.6 -> 109.16)."""
    fields = {}
    for k, v in (data or {}).items():
        if v is None:
            continue
        try:
            val = float(str(v).replace(",", "."))
        except (ValueError, TypeError):
            continue
        # sanity-check: se fuori range ma /10 rientra, corigi
        lo, hi = _BIA_RANGES.get(k, (float("-inf"), float("inf")))
        if val > hi and val / 10.0 <= hi:
            val = round(val / 10.0, 2)
        fields[k] = val
    return {"fields": fields, "raw_lines": 0, "vision": True}


# ── Range fisiologici per validazione ─────────────────────────────────────────
_BIA_RANGES = {
    "weight_kg": (20.0, 250.0),
    "height_cm": (100.0, 230.0),
    "bmi": (10.0, 60.0),
    "fat_mass_kg": (1.0, 120.0),
    "fat_mass_pct": (2.0, 60.0),
    "fat_free_mass_kg": (20.0, 200.0),
    "fat_free_mass_pct": (40.0, 98.0),
    "tbw_l": (10.0, 80.0),
    "ecw_l": (1.0, 40.0),
    "icw_l": (5.0, 70.0),
    "hydration_pct": (30.0, 80.0),
    "bcm_kg": (10.0, 80.0),
    "smm_kg": (5.0, 80.0),
    "asmm_kg": (3.0, 60.0),
    "muscle_mass_kg": (5.0, 80.0),
    "bone_kg": (1.0, 20.0),
    "protein_kg": (1.0, 40.0),
    "protein_pct": (5.0, 40.0),
    "visceral_fat": (1.0, 40.0),
    "metabolic_age": (5.0, 120.0),
    "phase_angle": (1.0, 20.0),
    "chi": (40.0, 600.0),
}

# Mappa nome campo interno <-> campo nel JSON del modello vision
_VISION_FIELD_MAP = {
    "weight_kg": "weight_kg", "height_cm": "height_cm", "bmi": "bmi",
    "fat_mass_kg": "fat_mass_kg", "fat_mass_pct": "fat_mass_pct",
    "fat_free_mass_kg": "fat_free_mass_kg", "fat_free_mass_pct": "fat_free_mass_pct",
    "tbw_l": "tbw_l", "ecw_l": "ecw_l", "icw_l": "icw_l",
    "hydration_pct": "hydration_pct", "bcm_kg": "bcm_kg", "smm_kg": "smm_kg",
    "asmm_kg": "asmm_kg", "muscle_mass_kg": "muscle_mass_kg",
    "bone_kg": "bone_kg", "protein_kg": "protein_kg", "protein_pct": "protein_pct",
    "visceral_fat": "visceral_fat", "metabolic_age": "metabolic_age",
    "phase_angle": "phase_angle", "chi": "chi",
}


@dataclass
class BIAReading:
    date: str = ""
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    bmi: Optional[float] = None
    fat_mass_kg: Optional[float] = None
    fat_mass_pct: Optional[float] = None
    fat_free_mass_kg: Optional[float] = None
    fat_free_mass_pct: Optional[float] = None
    tbw_l: Optional[float] = None
    ecw_l: Optional[float] = None
    icw_l: Optional[float] = None
    hydration_pct: Optional[float] = None
    bcm_kg: Optional[float] = None
    smm_kg: Optional[float] = None
    asmm_kg: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    bone_kg: Optional[float] = None
    protein_kg: Optional[float] = None
    protein_pct: Optional[float] = None
    visceral_fat: Optional[float] = None
    metabolic_age: Optional[float] = None
    phase_angle: Optional[float] = None
    chi: Optional[float] = None
    source: str = "manual"
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)

    def filled_fields(self):
        return {k: v for k, v in asdict(self).items()
                if v is not None and k not in ("date", "source", "raw_text")}

    def validated_fields(self):
        out = {}
        for k, v in self.filled_fields().items():
            lo, hi = _BIA_RANGES.get(k, (float("-inf"), float("inf")))
            if lo <= v <= hi:
                out[k] = v
        return out


def _build_reading(fields: dict, source: str, date: str = "", raw: str = "") -> BIAReading:
    """Costruisce BIAReading dai campi estratti, mappando i nomi del parser
    (peso/weight, fm/fat_mass_kg, ecc.) su quelli interni."""
    r = BIAReading(source=source, date=date, raw_text=raw)
    # mappa campo parser -> campo interno
    alias = {
        "peso": "weight_kg", "altezza": "height_cm",
        "fm": "fat_mass_kg", "ffm": "fat_free_mass_kg",
        "tbw": "tbw_l", "ecw": "ecw_l", "icw": "icw_l",
        "bcm": "bcm_kg", "smm": "smm_kg", "asmm": "asmm_kg",
        "pha": "phase_angle", "hydration": "hydration_pct",
        "protein": "protein_kg", "mineral": "bone_kg",
        "fmi": "fat_mass_pct", "ffmi": "fat_free_mass_pct",
        "bmr": None,  # metabolismo basale non e' un campo BIA
    }
    for k, v in fields.items():
        if k in _VISION_FIELD_MAP:
            setattr(r, _VISION_FIELD_MAP[k], v)
        elif k in alias and alias[k]:
            setattr(r, alias[k], v)
    # calcola percentuali da kg se mancano
    if r.weight_kg and r.weight_kg > 0:
        if r.fat_mass_kg is not None and r.fat_mass_pct is None:
            r.fat_mass_pct = round(r.fat_mass_kg / r.weight_kg * 100, 1)
        if r.fat_free_mass_kg is not None and r.fat_free_mass_pct is None:
            r.fat_free_mass_pct = round(r.fat_free_mass_kg / r.weight_kg * 100, 1)
    return r


def parse_bia_pdf(pdf_bytes: bytes) -> dict:
    """Estrae BIA da PDF: ibrido nativo -> cloud vision -> Tesseract -> scan."""
    try:
        import fitz
        import io
        import base64
    except ImportError:
        return {"scanned": True, "error": "PyMuPDF non installato",
                "reading": BIAReading(source="pdf_scanned").to_dict(),
                "found_fields": [], "missing_fields": sorted(_VISION_FIELD_MAP)}

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    page_images = []
    for pg in doc:
        parts.append(pg.get_text() or "")
        try:
            pix = pg.get_pixmap(matrix=fitz.Matrix(1.6, 1.6))
            page_images.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
        except Exception:
            pass
    text = "\n".join(parts).strip()

    # 1. testo nativo
    if text:
        parsed = parse_bia_text(text)
        r = _build_reading(parsed["fields"], "pdf", raw=text)
        return _finalize(r, False, None, page_images, None)

    # 2. cloud vision (se chiave configurata)
    try:
        import bia_vision
        if bia_vision.vision_configured():
            vdata = bia_vision.extract_bia_via_vision(pdf_bytes)
            if vdata:
                parsed = parse_bia_vision_json(vdata)
                r = _build_reading(parsed["fields"], "pdf_vision")
                return _finalize(r, False, "Estratto via cloud vision (modello). "
                                "Verifica i valori.", page_images, "pdf_vision")
    except Exception:
        pass

    # 3. Tesseract OCR
    try:
        import ocr_pdf
        ocr_text = ocr_pdf.ocr_pdf_text(pdf_bytes)
        if ocr_text:
            parsed = parse_bia_text(ocr_text)
            r = _build_reading(parsed["fields"], "pdf_ocr", raw=ocr_text)
            return _finalize(r, False, "PDF scansionato letto via OCR (Tesseract). "
                            "Verifica i valori.", page_images, "pdf_ocr")
    except Exception:
        pass

    # 4. nessun testo leggibile
    return {"scanned": True,
            "reading": BIAReading(source="pdf_scanned").to_dict(),
            "found_fields": [], "missing_fields": sorted(_VISION_FIELD_MAP),
            "note": "PDF scansionato: testo non estraibile. Incolla i valori o usa l'import manuale.",
            "pages": page_images}


def _finalize(r: BIAReading, scanned: bool, note: Optional[str],
              pages: list, source: Optional[str]) -> dict:
    validated = r.validated_fields()
    reliable = len(validated) >= 2 and "weight_kg" in validated
    clean = BIAReading(source=source or r.source, date=r.date, raw_text=r.raw_text)
    for k, v in validated.items():
        setattr(clean, k, v)
    return {
        "scanned": scanned or not reliable,
        "reading": clean.to_dict(),
        "found_fields": sorted(validated.keys()),
        "rejected_fields": sorted(set(r.filled_fields()) - set(validated)),
        "missing_fields": sorted(set(_VISION_FIELD_MAP) - set(validated.keys())),
        "unreliable": not reliable,
        "note": note or (None if reliable else
                         "Valori non affidabili (fuori range). Inserisci manualmente."),
        "pages": pages,
    }


# ── Mappatura BIA -> Intervals.icu /wellness ──────────────────────────────────
ICU_WELLNESS_FIELDS = ["weight", "bodyFat"]


def to_icu_wellness(r: BIAReading, date: str) -> dict:
    d = r.to_dict()
    payload = {}
    if r.weight_kg is not None:
        payload["weight"] = round(r.weight_kg, 1)
    if r.fat_mass_pct is not None:
        payload["bodyFat"] = round(r.fat_mass_pct, 1)
    use_date = date or r.date or ""
    return {"date": use_date, "payload": payload}
