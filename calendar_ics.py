"""PCC 5.x — Calendar subscription feed (.ics / webcal VIEW).

Genera un feed VCALENDAR dalle sessioni PIANIFICATE in current_plan.json.
E' una VISTA pura: legge lo stesso piano che il motore usa per tutto il resto
(single source of truth) e lo espone come .ics sottoscrivibile, così l'atleta
può vedere gli allenamenti in Google/Apple Calendar senza export manuale.

Se il piano non c'e', ritorna un VCALENDAR vuoto (valido). Solo stdlib.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _plan_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        return Path.home() / ".domestique" / "profiles" / aid / "plan" / "current_plan.json"
    except Exception:
        return None


def _dtstamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _to_ical_dt(date_str: str, duration_min: int) -> tuple[str, str]:
    """Return (DTSTART UTC, DTEND UTC) for a session date."""
    try:
        base = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        base = datetime.utcnow()
    start = base.replace(hour=7, minute=0, second=0)  # default 07:00 local slot
    end = start + timedelta(minutes=int(duration_min or 60))
    return (start.strftime("%Y%m%dT%H%M%SZ"), end.strftime("%Y%m%dT%H%M%SZ"))


def build_ics() -> str:
    p = _plan_path()
    sessions: list[dict] = []
    if p and p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8")) or {}
            sessions = data.get("sessions", []) or data.get("days", []) or []
            # flat list of sessions may be nested under weeks
            if not sessions and isinstance(data.get("weeks"), list):
                for w in data["weeks"]:
                    sessions.extend(w.get("sessions", []) or [])
        except Exception:
            sessions = []
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PCC//Performance Cycling Coach//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:PCC - Piano di allenamento",
        f"DTSTAMP:{_dtstamp()}",
    ]
    uid_base = _dtstamp()
    for i, s in enumerate(sessions):
        date = s.get("date") or ""
        if not date:
            continue
        dur = int(s.get("duration_min") or s.get("tss_estimate") or 60)
        stype = s.get("session_type") or s.get("from_type") or "ride"
        title = s.get("title") or f"PCC: {stype}"
        tss = s.get("tss_estimate") or s.get("planned_tss") or ""
        desc = f"Tipo: {stype}"
        if tss:
            desc += f" | TSS stimato: {tss}"
        start, end = _to_ical_dt(date, dur)
        lines += [
            "BEGIN:VEVENT",
            f"UID:pcc-{i}-{uid_base}",
            f"DTSTAMP:{_dtstamp()}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
