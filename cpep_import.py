"""PCC 5.x — CPET / INSCYD lab-test PDF import (context layer).

Status: IMPORT LAYER only. It extracts physiological benchmarks from a lab
test PDF (CPET, INSCYD report, metabolic cart) and stores them as ATHLETE
CONTEXT — not as a replacement for the field-derived estimates in
metabolic_decoder.py. The two are complementary: the lab values are the
gold-standard anchor; the field decoder is the continuous tracker.

Extraction is best-effort regex over PyPDF2 text (lab PDFs have no standard
schema). Every value carries a `found` flag so the UI can show "estratto dal
PDF" vs "non trovato". Patterns target the most common phrasings:

  VO2max:      "VO2max 58.2 ml/min/kg", "VO2max 4.12 L/min", "VO2 peak 57"
  HRmax:       "HRmax 182 bpm", "Fc max 181"
  VT1/LT1:     "VT1 210 W", "Lactate threshold 1 2.0 mmol" (power or lactate)
  VT2/LT2:     "VT2 320 W", "OBLA 4 mmol/L", "RC 350 W"
  Lactate max: "Lactate max 12.4 mmol/L", "Peak lactate 13"
  VLamax:      "VLamax 0.71", "Glycolytic power 0.7 mmol/L/s"  (INSCYD)
  FatMax:      "FatMax 145 W", "Peak fat oxidation 0.45 g/min"
  CP:          "Critical power 265 W", "CP 260"

Sources for the physiological meaning:
  - ACSM Guidelines for Exercise Testing (CPET protocol)
  - Beneke 2003 (max lactate steady state)
  - INSCYD VLamax metric (glycolytic power)
  - Achten et al. 2002 (FATmax)

Storage: <profile_dir>/cpep_history.json (list, newest first). Mirrors the
existing bia_history.json pattern so it is local-first and profile-scoped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


def _to_float(x: str) -> Optional[float]:
    try:
        return float(x.replace(",", "."))
    except (ValueError, AttributeError):
        return None


# (key, list of regexes) — first match wins per key.
_PATTERNS = {
    "vo2max_ml_kg_min": [
        r"VO[2₂] ?max[\s:]*?([0-9]{2,3}[.,][0-9])\s*(?:ml/?min/?kg|ml/min/kg)",
        r"VO[2₂] ?peak[\s:]*?([0-9]{2,3}[.,][0-9])\s*ml/?min/?kg",
    ],
    "vo2max_l_min": [
        r"VO[2₂] ?max[\s:]*?([0-9][.,][0-9]{1,2})\s*L/min",
        r"VO[2₂] ?peak[\s:]*?([0-9][.,][0-9]{1,2})\s*L/min",
    ],
    "hr_max": [
        r"HR ?max[\s:]*?([0-9]{2,3})\s*(?:bpm|ppm)?",
        r"Fc ?max[\s:]*?([0-9]{2,3})",
    ],
    "vt1_power_w": [
        r"VT[12][\s:]*?([0-9]{2,3})\s*W",
        r"Lactate[ -]?threshold[ -]?1[\s:]*?([0-9]{2,3})\s*W",
    ],
    "vt2_power_w": [
        r"VT2[\s:]*?([0-9]{2,3})\s*W",
        r"OBLA[\s:]*?([0-9]{2,3})\s*W",
        r"RC[\s:]*?([0-9]{2,3})\s*W",
    ],
    "lactate_max_mmol": [
        r"(?:Peak |Max )?[Ll]actate[\s:]*?([0-9]{1,2}[.,][0-9])\s*mmol",
        r"[Ll]actate[ -]?max[\s:]*?([0-9]{1,2}[.,][0-9])\s*mmol/L",
    ],
    "vlamax_mmol_l_s": [
        r"V[ L]?[Aa]max[\s:]*?([0-9][.,][0-9]{1,2})",
        r"Glycolytic[ -]?power[\s:]*?([0-9][.,][0-9]{1,2})",
    ],
    "fatmax_w": [
        r"Fat[ -]?max[\s:]*?([0-9]{2,3})\s*W",
        r"Peak[ -]?fat[ -]?oxidation[\s:]*?([0-9]{2,3})\s*W",
    ],
    "cp_w": [
        r"Critical[ -]?power[\s:]*?([0-9]{2,3})\s*W",
        r"\bCP[\s:]*?([0-9]{2,3})\s*W",
    ],
}


def parse_cpep_pdf(pdf_bytes: bytes) -> dict:
    """Extract CPET/INSCYD benchmarks from a lab PDF (best-effort).

    Returns a dict with one key per metric; each value is either a float
    (found) or None (not found in the PDF). Also returns ``raw_text_len`` and
    ``found`` (list of metric keys extracted).
    """
    result: dict = {k: None for k in _PATTERNS}
    raw_text = ""
    try:
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                pass
        raw_text = "\n".join(parts)
    except Exception as e:
        result["_error"] = f"PDF non leggibile: {e}"
        return result

    for key, pats in _PATTERNS.items():
        for pat in pats:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                val = _to_float(m.group(1))
                if val is not None:
                    result[key] = val
                    break

    result["found"] = [k for k, v in result.items() if v is not None and not k.startswith("_")]
    result["raw_text_len"] = len(raw_text)
    return result


# ── storage (mirrors bia_history.json pattern) ────────────────────────────

def _cpep_history_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        d = Path.home() / ".domestique" / "profiles" / aid
        return d / "cpep_history.json"
    except Exception:
        return None


def save_cpep_record(record: dict) -> bool:
    p = _cpep_history_path()
    if p is None:
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        hist = []
        if p.exists():
            try:
                hist = json.loads(p.read_text(encoding="utf-8")) or []
            except Exception:
                hist = []
        from datetime import datetime
        record = dict(record)
        record["imported"] = datetime.now().isoformat(timespec="seconds")
        hist.insert(0, record)
        hist = hist[:20]
        p.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def load_latest_cpep() -> Optional[dict]:
    p = _cpep_history_path()
    if p and p.exists():
        try:
            hist = json.loads(p.read_text(encoding="utf-8")) or []
            return hist[0] if hist else None
        except Exception:
            return None
    return None
