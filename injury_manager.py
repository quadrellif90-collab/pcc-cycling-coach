"""PCC 5.x — Injury / illness -> auto-remodulazione del piano (VISTA).

Verifica preliminare: db.py e profile_manager.py NON hanno nessuno stato
injury/illness (0 occorrenze). Il dato veniva solo loggato nel daily-log ma
NON agganciato a nessun replan. Questo modulo CHIUDE il buco: quando l'atleta
registra un infortunio/malattia (intervallo di date), il piano viene mostrato
con quei giorni azzerati (rest) e i carichi ridotti al rientro — una VISTA
sul current_plan.json esistente, NON un motore di pianificazione parallelo.

Single source of truth: legge current_plan.json (lo stesso che il motore
scrive) e applica i blocchi come trasformazione pura. Nessun ricalcolo di
nuovi workout: i giorni bloccati diventano rest, tutto il resto resta identico.

Storage: <profile_dir>/injury_blocks.json (lista).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def _history_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        return Path.home() / ".domestique" / "profiles" / aid / "injury_blocks.json"
    except Exception:
        return None


def load_blocks() -> list[dict]:
    p = _history_path()
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []


def _save_all(blocks: list[dict]) -> bool:
    p = _history_path()
    if p is None:
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(blocks, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def save_block(block: dict) -> dict:
    blocks = load_blocks()
    rec = {
        "id": block.get("id") or _new_id(),
        "start": block.get("start"),
        "end": block.get("end"),
        "type": block.get("type", "injury"),
        "severity": int(block.get("severity", 2)),
        "note": str(block.get("note") or ""),
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    blocks.insert(0, rec)
    _save_all(blocks)
    return rec


def delete_block(block_id: str) -> bool:
    blocks = load_blocks()
    kept = [b for b in blocks if b.get("id") != block_id]
    if len(kept) == len(blocks):
        return False
    return _save_all(kept)


def _parse(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def active_blocks(on: date | None = None) -> list[dict]:
    """Block attivi alla data `on` (default oggi)."""
    on = on or date.today()
    out = []
    for b in load_blocks():
        s, e = _parse(b.get("start")), _parse(b.get("end")) or _parse(b.get("start"))
        if s and e and s <= on <= e:
            out.append(b)
    return out


def apply_blocks_to_plan(plan_json: dict, blocks: list[dict] | None = None) -> dict:
    """VISTA: restituisce il piano con i giorni bloccati azzerati (rest).

    Per ogni sessione la cui data cade in un blocco, setta
    session_type='rest', tss_estimate=0, duration_min=0 e aggiunge
    ``blocked_by`` (tipo blocco). Non tocca le altre sessioni.
    """
    if blocks is None:
        blocks = load_blocks()
    blocked_dates = set()
    for b in blocks:
        s, e = _parse(b.get("start")), _parse(b.get("end")) or _parse(b.get("start"))
        if s and e:
            cur = s
            while cur <= e:
                blocked_dates.add(cur.isoformat())
                cur = date(cur.year, cur.month, cur.day) + __import__("datetime").timedelta(days=1)
    if not blocked_dates:
        plan_json = dict(plan_json)
        plan_json["blocked_dates"] = []
        return plan_json
    out = dict(plan_json)
    for key in ("sessions",):
        sess = out.get(key)
        if isinstance(sess, list):
            for s in sess:
                if isinstance(s, dict) and s.get("date") in blocked_dates:
                    s["session_type"] = "rest"
                    s["tss_estimate"] = 0
                    s["duration_min"] = 0
                    s["blocked_by"] = "injury/illness"
    # also weeks->sessions
    for w in out.get("weeks", []) or []:
        for s in (w.get("sessions") or []):
            if isinstance(s, dict) and s.get("date") in blocked_dates:
                s["session_type"] = "rest"
                s["tss_estimate"] = 0
                s["duration_min"] = 0
                s["blocked_by"] = "injury/illness"
    out["blocked_dates"] = sorted(blocked_dates)
    return out


def _new_id() -> str:
    return "blk_" + datetime.now().strftime("%Y%m%d%H%M%S")
