"""PCC 5.x — Activity classification + RPE -> re-plan view (JOIN-style).

Single source of truth: the planner's existing rematch engine
(training_planner.rematch_week / classify_rematch) and the rider's real
activity history. This module ONLY assembles a per-ride insight object and
stores athlete session-RPE; it does not invent a new training model.

- Protocol classification from a completed ride uses its intensity factor
  (IF = avg_power / FTP) mapped to Coggan/Allen zones (Allen & Coggan,
  "Training and Racing with a Power Meter", 2010). A ride's IF band implies
  its dominant energy system / workout type.
- Planned-vs-actual match reuses training_planner.rematch_week on the
  current week, so "done / ambiguous / no_match / missed / unplanned" all
  come from the ONE engine that also drives /api/plan/rematch.
- RPE (session RPE, Foster 1998; Hulin 2014 for acute:chronic) is logged by
  the athlete against a completed ride and surfaced so a divergence between
  perceived and prescribed load can trigger a re-plan (JOIN-style).

Storage: RPE is kept in a small JSON sidecar per profile
(<profile_dir>/rpe_log.json), keyed by ride id. This keeps the local-first
model (no external account) and never overwrites FIT-derived data.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from training_planner import rematch_week  # noqa: F401  (engine reuse)


# IF-band -> dominant protocol (Coggan/Allen zones). IF = avg_power / FTP.
def classify_protocol_from_if(if_value: Optional[float]) -> str:
    if if_value is None or if_value <= 0:
        return "sconosciuto"
    if if_value < 0.60:
        return "Recupero (Z1)"
    if if_value < 0.76:
        return "Endurance (Z2)"
    if if_value < 0.90:
        return "Tempo (Z3)"
    if if_value < 1.00:
        return "Soglia (Z4)"
    if if_value < 1.15:
        return "VO2max (Z5)"
    if if_value < 1.30:
        return "Anaerobico (Z6)"
    return "Sprint (Z7)"


def _rpe_path(profile_dir: Path) -> Path:
    return profile_dir / "rpe_log.json"


def load_rpe_log(profile_dir: Path) -> dict:
    p = _rpe_path(profile_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def save_rpe(profile_dir: Path, ride_id: str, rpe: float, note: str = "") -> dict:
    """Log athlete session-RPE (0-10) for a completed ride.

    Returns the updated per-ride entry. Invalid RPE is rejected (0-10).
    """
    if not (0 <= rpe <= 10):
        raise ValueError("RPE must be 0-10")
    log = load_rpe_log(profile_dir)
    log[ride_id] = {
        "rpe": round(float(rpe), 1),
        "note": note or "",
        "logged": date.today().isoformat(),
    }
    _rpe_path(profile_dir).write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return log[ride_id]


def build_activity_insights(
    activities: list[dict],
    plan: dict,
    profile_dir: Path,
    ftp: Optional[float],
    days: int = 14,
) -> list[dict]:
    """Assemble per-ride insight rows (protocol, match, RPE, unplanned)."""
    rpe_log = load_rpe_log(profile_dir)
    # Build current-week rematch preview to reuse the ONE engine.
    today = date.today()
    week = None
    week_idx = None
    try:
        from app import _load_current_week_dto  # local import to avoid cycle
        week, week_idx = _load_current_week_dto(plan, today)
    except Exception:
        week, week_idx = (None, None)
    rematch_by_day: dict = {}
    if week:
        try:
            from app import _collect_week_activities
            actual = _collect_week_activities(week, today, include_today=True)
            preview = rematch_week(week, actual, today)
            for s in preview.get("sessions", []):
                rematch_by_day[s.get("day") or s.get("date")] = s
        except Exception:
            pass

    cutoff = (today - timedelta(days=days)).isoformat()
    rows: list[dict] = []
    for a in activities:
        d = a.get("date") or ""
        if d and d < cutoff:
            continue
        avg = a.get("avg_power")
        if_value = (avg / ftp) if (avg and ftp) else None
        proto = classify_protocol_from_if(if_value)
        rid = a.get("id") or a.get("ride_id") or ""
        rem = rematch_by_day.get(d)
        # unplanned = ride exists but no same-day planned session matched.
        unplanned = (d not in rematch_by_day) if d else True
        rows.append({
            "date": d,
            "name": a.get("name") or "",
            "protocol": proto,
            "if": round(if_value, 2) if if_value else None,
            "tss": a.get("tss"),
            "duration_min": a.get("duration_min"),
            "match_status": (rem or {}).get("status") if rem else ("unplanned" if unplanned else None),
            "unplanned": unplanned and not rem,
            "rpe": (rpe_log.get(rid) or {}).get("rpe"),
            "rpe_note": (rpe_log.get(rid) or {}).get("note", ""),
            "id": rid,
        })
    return rows
