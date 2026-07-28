"""PCC — Parser BIA (Body Impedance Analysis) + mappatura Intervals.icu.

Supporta report di bilance BIA / bioimpedenziometri (InBody, Tanita, AKERN
BODYGRAM, Garmin Index, ecc.). Il PDF puo' essere:
  - testuale (export nativo): il testo viene estratto e parsato via regex;
  - scansionato (immagine): il testo non e' estraibile -> il parser ritorna
    `scanned: True` e l'UI chiede all'atleta di incollare i valori o usare
    un export testuale (il backend PCC non include OCR).

Campi estratti (schema comune, unita incluse):
  weight_kg, height_cm, bmi,
  fat_mass_kg, fat_mass_pct,
  fat_free_mass_kg, fat_free_mass_pct,
  tbw_l (acqua totale), ecw_l, icw_l, hydration_pct,
  bcm_kg (massa cellulare), smm_kg (massa muscolo-scheletrica),
  asmm_kg (massa muscolare appendicolare), muscle_mass_kg,
  bone_kg, protein_kg, protein_pct,
  visceral_fat, metabolic_age, phase_angle (PhA, gradi),
  chi (indice nutrizionale, opzionale)

Mappatura -> Intervals.icu /wellness (POST /athlete/{id}/wellness/{date}):
  weight      -> weight
  fat_mass_pct-> bodyFat        (ICU lo intende come %)
  fat_mass_pct-> pctBodyFat
  fat_free_kg -> (nessun campo diretto; non inviato)
  muscle_mass -> muscleMass     (usiamo SMM se presente, altrimenti FFM)
  hydration_pct-> hydration
  bone_kg     -> boneMass
  protein_kg  -> protein
  bmi         -> bmi
  visceral_fat-> visceralFat
  metabolic_age-> metabolicAge
ICU NON gestisce dieta/piano alimentare: quella parte resta locale.
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# Pattern: cattura "Etichetta 12.3 unita" o "Etichetta: 12.3".
# L'etichetta puo' essere IT o EN. I valori sono float (ammessi decimali).
_LABEL_PATTERNS = {
    "weight_kg": [
        r"peso\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"weight\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"body\s*weight\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "height_cm": [
        r"altezza\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*cm",
        r"height\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*cm",
    ],
    "bmi": [
        r"bmi\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"imc\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"indice\s*di\s*massa\s*corporea\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
    "fat_mass_kg": [
        r"massa\s*grassa\s*\(fm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"fat\s*mass\s*\(fm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"\bfm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "fat_mass_pct": [
        r"massa\s*grassa\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"fat\s*mass\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"\bfm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"percentuale\s*di\s*grasso\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
    "fat_free_mass_kg": [
        r"massa\s*magra\s*\(ffm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"fat\s*free\s*mass\s*\(ffm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"\bffm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "fat_free_mass_pct": [
        r"massa\s*magra\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"fat\s*free\s*mass\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
    ],
    "tbw_l": [
        r"acqua\s*totale\s*\(tbw\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
        r"total\s*body\s*water\s*\(tbw\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
        r"\btbw\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
    ],
    "ecw_l": [
        r"acqua\s*extra\s*cellulare\s*\(ecw\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
        r"\becw\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
    ],
    "icw_l": [
        r"acqua\s*intra\s*cellulare\s*\(icw\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
        r"\bicw\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*l",
    ],
    "hydration_pct": [
        r"idratazione\s*tissutale\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"hydration\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"tbw/ffm\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
    ],
    "bcm_kg": [
        r"massa\s*cellulare\s*\(bcm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"\bbcm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "smm_kg": [
        r"massa\s*muscolo[- ]?scheletrica\s*\(smm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"skeletal\s*muscle\s*mass\s*\(smm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"\bsmm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "asmm_kg": [
        r"massa\s*muscolare\s*appendicolare\s*\(asmm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"appendicular\s*skeletal\s*muscle\s*mass\s*\(asmm\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"\basmm\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "muscle_mass_kg": [
        r"massa\s*muscolare\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"muscle\s*mass\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "bone_kg": [
        r"massa\s*ossea\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"bone\s*mass\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "protein_kg": [
        r"proteine\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
        r"protein\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*kg",
    ],
    "protein_pct": [
        r"proteine\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
        r"protein\s*[:\.]?\s*(\d+(?:[.,]\d+)?)\s*%",
    ],
    "visceral_fat": [
        r"grasso\s*viscerale\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"visceral\s*fat\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
    "metabolic_age": [
        r"et[aà]\s*metabolica\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"metabolic\s*age\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
    "phase_angle": [
        r"angolo\s*di\s*fase\s*\(pha\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"phase\s*angle\s*\(pha\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"\bpha\b\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
    "chi": [
        r"indice\s*nutrizionale\s*\(chi\)\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
        r"chi\s*[:\.]?\s*(\d+(?:[.,]\d+)?)",
    ],
}


# Range fisiologici plausibili per un essere umano adulto.
# Usati per scartare valori estratti da PDF illeggibili (es. AKERN Biavector
# dove il primo numero dopo l'etichetta e' il valore di riferimento, non la
# misurazione, oppure la virgola decimale italiana scompare nell'OCR).
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
    source: str = "manual"  # manual | pdf | pdf_scanned
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)

    def filled_fields(self):
        return {k: v for k, v in asdict(self).items()
                if v is not None and k not in ("date", "source", "raw_text")}

    def validated_fields(self):
        """Campi con valore dentro il range fisiologico plausibile."""
        out = {}
        for k, v in self.filled_fields().items():
            lo, hi = _BIA_RANGES.get(k, (float("-inf"), float("inf")))
            if lo <= v <= hi:
                out[k] = v
        return out


def _restore_decimal(field_name: str, val: float) -> tuple:
    """Se il valore e' fuori range fisiologico, prova a dividerlo per
    10/100/1000 per recuperare una virgola decimale persa nell'OCR
    (es. AKERN Biavector: '13,1' -> '131', '73,1%' -> '731%',
    '43,71' -> '4371'). Ritorna (valore_corretto, ripristinato)."""
    lo, hi = _BIA_RANGES.get(field_name, (float("-inf"), float("inf")))
    if lo <= val <= hi:
        return val, False
    for div in (10, 100, 1000):
        cand = val / div
        if lo <= cand <= hi:
            return round(cand, 2), True
    return val, False


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_bia_text(text: str) -> dict:
    """Estrae i campi BIA dal testo del PDF (PDF testuale).

    I valori estratti vengono filtrati per range fisiologico: i PDF AKERN
    Biavector (testuali o scansionati via OCR) producono spesso numeri
    errati (valore di riferimento invece della misurazione, o virgola
    decimale italiana persa). I valori fuori range vengono scartati per
    non salvare misurazioni impossibili.
    """
    low = text.lower()
    r = BIAReading(source="pdf")
    found = {}
    restored = {}
    for field_name, patterns in _LABEL_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, low)
            if m:
                try:
                    val = _num(m.group(1))
                    val, fixed = _restore_decimal(field_name, val)
                    if fixed:
                        restored[field_name] = True
                    setattr(r, field_name, val)
                    found[field_name] = val
                except ValueError:
                    pass
                break
    # Deriva le percentuali mancanti da kg / peso (se peso presente)
    if r.weight_kg and r.weight_kg > 0:
        if r.fat_mass_kg is not None and r.fat_mass_pct is None:
            r.fat_mass_pct = round(r.fat_mass_kg / r.weight_kg * 100, 1)
            found["fat_mass_pct"] = r.fat_mass_pct
        if r.fat_free_mass_kg is not None and r.fat_free_mass_pct is None:
            r.fat_free_mass_pct = round(r.fat_free_mass_kg / r.weight_kg * 100, 1)
            found["fat_free_mass_pct"] = r.fat_free_mass_pct
        if r.muscle_mass_kg is None and r.smm_kg is not None:
            r.muscle_mass_kg = r.smm_kg
            found["muscle_mass_kg"] = r.muscle_mass_kg
    r.raw_text = text
    # Filtra per range fisiologico: scarta i valori impossibili (non
    # ripristinabili dividendo per 10/100/1000)
    validated = r.validated_fields()
    # Se dopo il filtro restano pochi campi utili, il PDF non e' affidabile:
    # ritorna scanned=True cosi' l'UI chiede all'atleta di confermare/inserire.
    reliable = len(validated) >= 2 and "weight_kg" in validated
    # reading ritornato all'UI contiene SOLO i campi validati (non quelli
    # scartati per range), cosi' prefillBIAform non precompila valori assurdi.
    clean = BIAReading(source="pdf", date=r.date, raw_text=text)
    for k, v in validated.items():
        setattr(clean, k, v)
    restored_fields = sorted(restored.keys())
    if restored_fields:
        note = ("Virgola decimale ripristinata via OCR su: %s. "
                "Verifica i valori." % ", ".join(restored_fields))
    elif not reliable:
        note = ("Valori non affidabili (fuori range fisiologico). Controlla e "
                "inserisci manualmente o incolla il testo del report.")
    else:
        note = None
    return {
        "scanned": not reliable,
        "reading": clean.to_dict(),
        "found_fields": sorted(validated.keys()),
        "rejected_fields": sorted(set(found) - set(validated)),
        "restored_fields": restored_fields,
        "missing_fields": sorted(set(_LABEL_PATTERNS) - set(validated.keys())),
        "unreliable": not reliable,
        "note": note,
    }


def parse_bia_pdf(pdf_bytes: bytes) -> dict:
    """Estrae testo dal PDF via PyMuPDF; se vuoto -> scansionato.

    Nel caso scansionato, ritorna anche le immagini delle pagine (PNG base64)
    cosi' l'UI puo' mostrarle all'atleta e fargli inserire/confermare i valori.
    """
    import io
    import base64
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"scanned": True, "error": "PyMuPDF non installato",
                "reading": BIAReading(source="pdf_scanned").to_dict(),
                "found_fields": [], "missing_fields": sorted(_LABEL_PATTERNS),
                "pages": []}
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = []
    page_images = []
    for i, pg in enumerate(doc):
        parts.append(pg.get_text() or "")
        # renderizza la pagina in PNG base64 per l'UI (utile nei PDF scansionati)
        try:
            pix = pg.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
            img_bytes = pix.tobytes("png")
            page_images.append("data:image/png;base64," + base64.b64encode(img_bytes).decode("ascii"))
        except Exception:
            pass
    text = "\n".join(parts).strip()
    if not text:
        # PCC 5.0 — OCR layer: a scanned PDF may still be readable if Tesseract
        # is installed. Try OCR; if it yields text, parse it like a text export.
        try:
            import ocr_pdf
            ocr_text = ocr_pdf.ocr_pdf_text(pdf_bytes)
        except Exception:
            ocr_text = None
        if ocr_text:
            from bia_parser import parse_bia_text
            reading = parse_bia_text(ocr_text)
            reading["scanned"] = False
            reading["source"] = "pdf_ocr"
            reading["pages"] = page_images
            reading["note"] = ("PDF scansionato letto via OCR (Tesseract). "
                                "Verifica i valori estratti.")
            return reading
        return {"scanned": True,
                "reading": BIAReading(source="pdf_scanned").to_dict(),
                "found_fields": [], "missing_fields": sorted(_LABEL_PATTERNS),
                "note": "PDF scansionato: testo non estraibile. Incolla i valori o usa l'import manuale.",
                "pages": page_images}
    return parse_bia_text(text)


# ── Mappatura BIA -> Intervals.icu /wellness ───────────────────────────────
# Campi verificati accettati da ICU per questo atleta (PUT /wellness-bulk):
#   weight, bodyFat (%)
# Campi RIFIUTATI da ICU (422): pctBodyFat, muscleMass, hydration, bmi,
#   boneMass, protein, visceralFat, metabolicAge
# Li escludiamo per non far fallire l'intera push.
ICU_WELLNESS_FIELDS = [
    "weight", "bodyFat",
]


def to_icu_wellness(r: BIAReading, date: str) -> dict:
    """Costruisce il payload ICU /wellness per una misurazione BIA.

    Restituisce {"date":..., "payload": {...}} con solo i campi disponibili
    e ACCETTATI da Intervals.icu (weight, bodyFat).
    """
    d = r.to_dict()
    payload = {}
    if r.weight_kg is not None:
        payload["weight"] = round(r.weight_kg, 1)
    if r.fat_mass_pct is not None:
        payload["bodyFat"] = round(r.fat_mass_pct, 1)
    use_date = date or r.date or ""
    return {"date": use_date, "payload": payload}
