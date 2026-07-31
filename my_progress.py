# Copyright 2024-2026 PCC — Performance Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""BETA Fase 7e (verticale DIY) — Il mio calendario / aderenza personale.

Lettura ATTIVITÀ REALI del proprio profilo intervals.icu (self) e confronto
col TSS pianificato dal piano di Domestique → aderenza personale
(pianificato vs eseguito). Niente rubrica multi-atleta: è la verticale
atleta-singolo, quindi lavora sul profilo attivo (self) dell'app.

Logica pura + wrapper ICU (best-effort, non blocca se non ci sono credenziali).
"""
from __future__ import annotations
import datetime as _dt
from typing import Optional


def iso_week_monday(d: _dt.date) -> str:
    """Ritorna la label ISO week (es. '2026-W30') per una data."""
    return d.strftime("%G-W%V")


def compute_my_adherence(plan_weeks: list[dict], actual_by_week: dict) -> list[dict]:
    """Funzione pura. Confronta il piano (tss_target settimanale) con le
    attività reali (TSS eseguito per settimana).

    plan_weeks: [{"start": "2026-07-20", "tss_target": 450, "phase": "Build"}, ...]
    actual_by_week: {"2026-W30": 420.0, ...}   # TSS eseguito per ISO-week

    Ritorna una lista di righe con planned/actual/flag per ogni settimana
    che abbia un piano O attività.
    """
    rows = []
    for wk in plan_weeks:
        start = wk.get("start")
        planned = float(wk.get("tss_target", 0) or 0)
        try:
            d = _dt.date.fromisoformat(start)
            wl = iso_week_monday(d)
        except Exception:
            wl = wk.get("week_label", "?")
        actual = float(actual_by_week.get(wl, 0) or 0)
        # aderenza TSS (su TSS, non su n. sessioni — il self non ha conteggio sessioni)
        if planned > 0:
            ratio = round(actual / planned, 2)
            if ratio >= 0.85:
                flag = "green"
            elif ratio >= 0.60:
                flag = "amber"
            else:
                flag = "red"
        else:
            ratio, flag = 0.0, "red" if actual == 0 else "green"
        rows.append({
            "week_label": wl,
            "start": start,
            "phase": wk.get("phase", ""),
            "planned_tss": round(planned, 1),
            "actual_tss": round(actual, 1),
            "tss_ratio": ratio,
            "flag": flag,
            "delta_tss": round(actual - planned, 1),
        })
    return rows


def fetch_actual_tss_by_week(api_key: str, athlete_id: str,
                             oldest: str, newest: str) -> dict:
    """Legge le attività reali da intervals.icu e somma il TSS per ISO-week.
    Richiede credenziali self valide. Best-effort: rilancia l'eccezione al
    chiamante (che la gestisce con un messaggio UX)."""
    import httpx
    url = (f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
           f"?oldest={oldest}&newest={newest}")
    r = httpx.get(url, auth=("API_KEY", api_key), timeout=20)
    r.raise_for_status()
    acts = r.json() or []
    out: dict[str, float] = {}
    for a in acts:
        # ICU restituisce 'start_date_local' (es. '2026-07-21') e 'training_load'
        # o 'tss' a seconda dei campi; usiamo 'training_load' se presente,
        # altrimenti i campi TSS noti (activity_tss / tss / ctl).
        sd = a.get("start_date_local") or a.get("startDate") or a.get("date")
        if not sd:
            continue
        try:
            d = _dt.date.fromisoformat(sd[:10])
        except Exception:
            continue
        tss = (a.get("training_load") or a.get("activity_tss") or
               a.get("tss") or 0)
        try:
            tss = float(tss)
        except Exception:
            tss = 0.0
        out[iso_week_monday(d)] = out.get(iso_week_monday(d), 0.0) + tss
    return out


def load_plan_weeks() -> list[dict]:
    """Legge plans/current_plan.json (dove PCC salva il piano generato) e
    ritorna le settimane con sessions + start + tss_target + phase. Se non
    c'è un piano, lista vuota."""
    import json, os
    from pathlib import Path
    candidates = [
        Path(__file__).parent / "plans" / "current_plan.json",
        Path(__file__).parent / "current_plan.json",
    ]
    data = None
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = None
            break
    if not data:
        return []
    # Include the FULL week dict (sessions, phase, start, tss_target, etc.)
    # so callers like api_my_push_plan can push every session to intervals.icu
    return data.get("weeks", []) or data.get("plan_json", {}).get("weeks", []) or []
