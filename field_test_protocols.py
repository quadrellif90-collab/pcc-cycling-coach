"""PCC 5.x — Field-test protocol manager (chiude il loop FTP, vedi #2).

Sport-science 2026: i principali field test per stimare la FTP (Functional
Threshold Power) sono:

  * 20-min TT         -> FTP = P_avg_20min * 0.95        (Allen & Coggan)
  * Ramp 1-min steps  -> FTP = P_peak * 0.75             (P_peak = ultimo step
                          completato; stima comune da ramp test)
  * 4 x 8-min         -> FTP = best 8-min avg * 0.90    (protocollo "8-min")
  * 4 x 4-min         -> FTP = best 4-min avg * 0.90    (protocollo "4-min",
                          usato per atleti più esplosivi; approssimazione)
  * 60-min best       -> FTP = P_avg_60min              (gold standard pratico)

Questo modulo NON è un motore parallelo: è una VISTA che, dato il risultato
di un test sul campo, calcola la FTP stimata e la propone come contesto.
L'aggiornamento effettivo della FTP nel profilo usa lo stesso path del
meccanismo "FTP continuo" (#2): scrive via ProfileManager / metric log, così
il resto del motore (zone, plan, power-duration) resta single source of truth.

Storage del risultato test: <profile_dir>/field_tests.json (lista, newest first).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


PROTOCOLS = {
    "20min": {
        "label": "20 min Time Trial",
        "inputs": [("avg_w", "Potenza media 20 min (W)")],
        "ftp_factor": 0.95,
        "ftp_field": "avg_w",
        "note": "Allen & Coggan: FTP = P_media_20min x 0.95",
    },
    "ramp": {
        "label": "Ramp test (step 1 min)",
        "inputs": [("peak_w", "Potenza di picco / ultimo step (W)")],
        "ftp_factor": 0.75,
        "ftp_field": "peak_w",
        "note": "FTP ~ P_peak x 0.75 (stima da ramp; da validare con 20-min)",
    },
    "8min": {
        "label": "4 x 8 min (miglior blocco)",
        "inputs": [("best8_w", "Miglior 8 min avg (W)")],
        "ftp_factor": 0.90,
        "ftp_field": "best8_w",
        "note": "FTP = best 8-min avg x 0.90",
    },
    "4min": {
        "label": "4 x 4 min (miglior blocco)",
        "inputs": [("best4_w", "Miglior 4 min avg (W)")],
        "ftp_factor": 0.90,
        "ftp_field": "best4_w",
        "note": "FTP = best 4-min avg x 0.90 (approssimazione per profili esplosivi)",
    },
    "60min": {
        "label": "60 min best effort",
        "inputs": [("avg60_w", "Potenza media 60 min (W)")],
        "ftp_factor": 1.0,
        "ftp_field": "avg60_w",
        "note": "FTP = P_media_60min (gold standard pratico)",
    },
}


def list_protocols() -> list[dict]:
    return [{"id": k, "label": v["label"], "inputs": v["inputs"], "note": v["note"]}
            for k, v in PROTOCOLS.items()]


def estimate_ftp(protocol: str, values: dict) -> dict:
    """Calcola FTP stimata da un protocollo + valori misurati.

    Ritorna {ftp_w, factor, note, valid}. `valid=False` se protocollo o
    valore mancante/non numerico.
    """
    p = PROTOCOLS.get(protocol)
    if not p:
        return {"valid": False, "error": "protocollo sconosciuto"}
    field = p["ftp_field"]
    raw = values.get(field)
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return {"valid": False, "error": f"valore '{field}' non valido"}
    ftp = round(val * p["ftp_factor"], 1)
    return {"valid": True, "ftp_w": ftp, "factor": p["ftp_factor"],
            "field": field, "input_value": val, "note": p["note"]}


def _history_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        d = Path.home() / ".domestique" / "profiles" / aid
        return d / "field_tests.json"
    except Exception:
        return None


def save_test(protocol: str, values: dict, ftp_w: float) -> bool:
    p = _history_path()
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
        rec = {
            "protocol": protocol,
            "protocol_label": PROTOCOLS.get(protocol, {}).get("label", protocol),
            "values": values,
            "ftp_w": ftp_w,
            "dated": datetime.now().isoformat(timespec="seconds"),
        }
        hist.insert(0, rec)
        hist = hist[:30]
        p.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def load_tests() -> list[dict]:
    p = _history_path()
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []


def latest_ftp() -> Optional[float]:
    tests = load_tests()
    return tests[0]["ftp_w"] if tests else None
