"""PCC 5.x — Pedaling asymmetry / LEOMO MPI context layer (importabile).

Status: CONTEXT layer. Smart power pedals (Favero Assioma, Garmin Rally,
Wahoo POWRLINK) and the LEOMO system export pedal metrics: left/right power
balance, torque effectiveness (TE) and pedal smoothness (PS) per leg, plus
LEOMO's Motion Performance Index (MPI). These describe neuromuscular
ASYMMETRY and pedaling efficiency — a different axis from the metabolic/
power-duration profile, so they belong as importable CONTEXT, not as a new
training model.

Inputs accepted (fully offline):
  - JSON: {ride_id, date, left_balance_pct, left_te, right_te,
           left_ps, right_ps, mpi}
  - CSV with the same column names (one row, comma-separated)
  - (future) FIT bytes — only if the FIT lib exposes the pedal fields; for
    now JSON/CSV is the reliable path because device exports vary.

Derived metric (single, transparent formula):
  asymmetry_index = |L - R| / (L + R)   over whichever pair is supplied
  (balance, TE, or PS). Literature flags meaningful neuromuscular asymmetry
  above ~10-15% balance disparity (e.g. Bini & Diefenthaeler 2017 on TE/PS;
  Asymmetry Index convention). We flag > 0.10 (10%) as "da monitorare".

Storage: <profile_dir>/pedal_asymmetry_history.json (list, newest first).
Mirrors cpep_history.json / custom_charts.json (local-first, per-profile).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Optional


# Asymmetry threshold (fraction). > 0.10 = >10% disparity => flag.
ASYMMETRY_FLAG = 0.10


def _ai(left: Optional[float], right: Optional[float]) -> Optional[float]:
    """Asymmetry Index = |L-R|/(L+R). None if either missing."""
    if left is None or right is None:
        return None
    s = left + right
    if s == 0:
        return None
    return abs(left - right) / s


def _coerce(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


def parse_pedal_json(body: dict) -> dict:
    """Normalise a single pedal-metric record from JSON."""
    rec = {
        "ride_id": body.get("ride_id") or body.get("id") or "",
        "date": body.get("date") or "",
        "left_balance_pct": _coerce(body.get("left_balance_pct")),
        "right_balance_pct": _coerce(body.get("right_balance_pct")),
        "left_te": _coerce(body.get("left_te")),
        "right_te": _coerce(body.get("right_te")),
        "left_ps": _coerce(body.get("left_ps")),
        "right_ps": _coerce(body.get("right_ps")),
        "mpi": _coerce(body.get("mpi")),
    }
    # balance pair: if only left given, derive right = 100 - left
    if rec["left_balance_pct"] is not None and rec["right_balance_pct"] is None:
        rec["right_balance_pct"] = round(100.0 - rec["left_balance_pct"], 2)
    if rec["right_balance_pct"] is not None and rec["left_balance_pct"] is None:
        rec["left_balance_pct"] = round(100.0 - rec["right_balance_pct"], 2)
    rec["asymmetry_balance"] = _ai(rec["left_balance_pct"], rec["right_balance_pct"])
    rec["asymmetry_te"] = _ai(rec["left_te"], rec["right_te"])
    rec["asymmetry_ps"] = _ai(rec["left_ps"], rec["right_ps"])
    rec["flag"] = any(
        (a is not None and a > ASYMMETRY_FLAG)
        for a in (rec["asymmetry_balance"], rec["asymmetry_te"], rec["asymmetry_ps"])
    )
    return rec


def parse_pedal_csv(text: str) -> dict:
    """Parse one-row CSV with header columns matching the JSON keys."""
    reader = csv.DictReader(io.StringIO(text))
    row = next(reader, None)
    if not row:
        raise ValueError("CSV vuoto o senza intestazioni")
    # normalise header keys (lowercase, strip)
    norm = {k.strip().lower(): v for k, v in row.items()}
    mapped = {
        "ride_id": norm.get("ride_id") or norm.get("id"),
        "date": norm.get("date"),
        "left_balance_pct": norm.get("left_balance_pct"),
        "right_balance_pct": norm.get("right_balance_pct"),
        "left_te": norm.get("left_te"),
        "right_te": norm.get("right_te"),
        "left_ps": norm.get("left_ps"),
        "right_ps": norm.get("right_ps"),
        "mpi": norm.get("mpi"),
    }
    return parse_pedal_json(mapped)


def parse_pedal_payload(body: bytes) -> dict:
    """Accept JSON bytes or CSV text. Returns a normalised record."""
    text = body.decode("utf-8", errors="replace").strip()
    if text.lstrip().startswith("{"):
        return parse_pedal_json(json.loads(text))
    # else treat as CSV
    return parse_pedal_csv(text)


def _history_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        d = Path.home() / ".domestique" / "profiles" / aid
        return d / "pedal_asymmetry_history.json"
    except Exception:
        return None


def save_record(rec: dict) -> bool:
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
        rec = dict(rec)
        rec["imported"] = datetime.now().isoformat(timespec="seconds")
        hist.insert(0, rec)
        hist = hist[:50]
        p.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def load_latest() -> Optional[dict]:
    p = _history_path()
    if p and p.exists():
        try:
            hist = json.loads(p.read_text(encoding="utf-8")) or []
            return hist[0] if hist else None
        except Exception:
            return None
    return None


def load_history() -> list[dict]:
    p = _history_path()
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []
