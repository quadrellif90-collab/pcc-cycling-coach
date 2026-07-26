# Copyright 2024-2026 PCC — Performance Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""BETA Fase 7a — Libreria Forza + Mobilità per ciclisti.

Fonti scientifiche (2024-2026):
- Llanos-Lagos 2025 (Eur J Appl Physiol, meta-analisi 17 studi, 262 ciclisti):
  la forza PESANTE migliora l'efficienza di pedalata (ES=0.353, p=0.012),
  TT e time-to-exhaustion. Effetto marcato nei Master (>40).
- Vikmoen 2021: beneficio in entrambi i sessi (uomini e donne).
- Warneke 2025 (Delphi): stretching cronico riduce il rischio infortuni;
  routine 15 min/giorno (hip flexor + hamstring) migliora potenza e riduce
  infortuni (Dynamic Cyclist / Roadman 2026).

Il modulo è AUTONOMO: NON modifica training_planner. Le sedute sono dizionari
pronti per essere renderizzati nel planner o esportati in PDF/HTML (Fase 7c).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ── Libreria esercizi forza (heavy, compound, evidence-based) ────────────────
# Ogni esercizio: nome, gruppo, note. %1RM dal protocollo Llanos-Lagos 2025.
STRENGTH_EXERCISES = {
    "back_squat":       {"name": "Back Squat",        "group": "gambe",      "note": "Multi-articolare, base forza ciclista"},
    "front_squat":      {"name": "Front Squat",       "group": "gambe",      "note": "Più carico core/posizione,友好 alla bici"},
    "romanian_deadlift":{"name": "Romanian Deadlift", "group": "posteriori", "note": "Hamstring/glute, antitodo a pedalata"},
    "deadlift":         {"name": "Deadlift",          "group": "posteriori", "note": "Catena posteriore completa"},
    "hip_thrust":       {"name": "Hip Thrust",        "group": "glutei",     "note": "Estensione anca, potenza sprint"},
    "leg_press":        {"name": "Leg Press",         "group": "gambe",      "note": "Variante controllata"},
    "bulgarian_split":  {"name": "Bulgarian Split Squat", "group": "monopodalico", "note": "Stabilità + forza asimmetrica"},
    "step_up":          {"name": "Step-up pesante",   "group": "monopodalico", "note": "Transfer bike-specific"},
    "calf_raise":       {"name": "Calf Raise",        "group": "polpacci",   "note": "Spinta, prevenzione crampi"},
    "core_antirotation":{"name": "Pallof Press / Plank", "group": "core",    "note": "Stabilità tronco"},
    "pull_up":          {"name": "Pull-up / Row",     "group": "schiena",    "note": "Postura, contro sbilanciamento bici"},
}

# ── Libreria mobilità (Warneke 2025 + routine 15 min) ───────────────────────
MOBILITY_EXERCISES = {
    "hip_flexor_stretch":  {"name": "Stretching flessori anca", "area": "anca",      "dur_s": 90,  "note": "Contro accorciamento da bici"},
    "hamstring_stretch":   {"name": "Stretching ischiocrurali", "area": "posteriore", "dur_s": 90, "note": "Riduce infortuni (Warneke 2025)"},
    "piriformis_stretch":  {"name": "Stretching piriforme",      "area": "gluteo",    "dur_s": 60,  "note": "Sciatica/prevenzione"},
    "thoracic_rotation":   {"name": "Rotazione toracica",        "area": "schiena",   "dur_s": 60,  "note": "Mobilità tronco"},
    "cat_cow":             {"name": "Cat-Cow",                   "area": "schiena",   "dur_s": 60,  "note": "Articolazione colonna"},
    "worlds_greatest":     {"name": "World's Greatest Stretch", "area": "catena",    "dur_s": 90,  "note": "Full-body dinamico"},
    "ankle_dorsiflexion":  {"name": "Dorsiflessione caviglia",   "area": "caviglia",  "dur_s": 60,  "note": "Range pedalata"},
    "neck_release":        {"name": "Rilascio cervicale",        "area": "collo",     "dur_s": 45,  "note": "Tensione da posizione"},
}

# Protocolli forza per fase (Llanos-Lagos 2025: mantenere forza in-season).
# set x rep x %1RM; 2-3 sedute/sett in preparazione, 1-2 in competizione.
STRENGTH_PROTOCOLS = {
    "base":      {"sessions_per_week": 2, "sets": 4, "reps": 6,  "pct_1rm": 85, "exercises": ["back_squat", "romanian_deadlift", "hip_thrust", "core_antirotation"]},
    "build":     {"sessions_per_week": 2, "sets": 4, "reps": 5,  "pct_1rm": 87, "exercises": ["front_squat", "deadlift", "bulgarian_split", "pull_up"]},
    "peak":      {"sessions_per_week": 1, "sets": 3, "reps": 4,  "pct_1rm": 90, "exercises": ["back_squat", "hip_thrust", "calf_raise"]},
    "taper":     {"sessions_per_week": 1, "sets": 2, "reps": 3,  "pct_1rm": 88, "exercises": ["back_squat", "romanian_deadlift"]},
    "race_week": {"sessions_per_week": 0, "sets": 0, "reps": 0,  "pct_1rm": 0,  "exercises": []},
}

MOBILITY_ROUTINE = {
    "minutes": 15,
    "frequency": "quotidiano (post-bici o sera)",
    "sequence": ["hip_flexor_stretch", "hamstring_stretch", "piriformis_stretch",
                 "thoracic_rotation", "worlds_greatest", "ankle_dorsiflexion", "neck_release"],
}


@dataclass
class StrengthSession:
    phase: str
    exercise: str
    sets: int
    reps: int
    pct_1rm: int
    rest_s: int = 180
    note: str = ""

    def to_dict(self, one_rm_kg: float = 0.0) -> dict:
        ex = STRENGTH_EXERCISES.get(self.exercise, {})
        d = {
            "phase": self.phase,
            "exercise": ex.get("name", self.exercise),
            "group": ex.get("group", ""),
            "sets": self.sets, "reps": self.reps, "pct_1rm": self.pct_1rm,
            "rest_s": self.rest_s, "note": ex.get("note", "") or self.note,
        }
        # Carico assoluto calcolato sull'1RM dell'atleta (kg), se noto.
        if one_rm_kg and one_rm_kg > 0:
            load = round(one_rm_kg * self.pct_1rm / 100.0, 1)
            d["load_kg"] = load
            d["one_rm_kg"] = one_rm_kg
        return d


@dataclass
class MobilitySession:
    area: str
    exercise: str
    duration_s: int
    note: str = ""

    def to_dict(self) -> dict:
        ex = MOBILITY_EXERCISES.get(self.exercise, {})
        return {
            "area": ex.get("area", self.area),
            "exercise": ex.get("name", self.exercise),
            "duration_s": ex.get("dur_s", self.duration_s),
            "note": ex.get("note", "") or self.note,
        }


def build_strength_plan(phase: str = "base", weeks: int = 4,
                        one_rm_kg: float = 0.0) -> list[dict]:
    """Genera il piano di forza per N settimane in una fase.

    one_rm_kg: 1RM dell'atleta (Squat) per calcolare i carichi assoluti in kg
    (Llanos-Lagos 2025 usa %1RM; il kg reale serve all'atleta in palestra).
    Se 0, ritorna solo %1RM.
    """
    proto = STRENGTH_PROTOCOLS.get(phase, STRENGTH_PROTOCOLS["base"])
    out = []
    if proto["sessions_per_week"] == 0:
        return [{"week": w + 1, "sessions": []} for w in range(weeks)]
    for w in range(weeks):
        # leggero incremento del carico nel corso delle settimane ( progressione )
        ramp = min(3, w)  # +0/+1/+2/+3% dopo la 4a settimana resta a +3
        pct = max(70, min(95, proto["pct_1rm"] + ramp))
        sessions = []
        for ex in proto["exercises"]:
            sessions.append(StrengthSession(
                phase=phase, exercise=ex, sets=proto["sets"],
                reps=proto["reps"], pct_1rm=int(pct),
            ).to_dict(one_rm_kg=one_rm_kg))
        out.append({"week": w + 1, "sessions": sessions,
                    "sessions_per_week": proto["sessions_per_week"]})
    return out


def build_mobility_plan(days: int = 7) -> list[dict]:
    """Routine mobilità quotidiana (Warneke 2025, 15 min)."""
    out = []
    for d in range(days):
        seq = []
        for ex in MOBILITY_ROUTINE["sequence"]:
            seq.append(MobilitySession(
                area="", exercise=ex, duration_s=0).to_dict())
        out.append({"day": d + 1, "minutes": MOBILITY_ROUTINE["minutes"],
                    "sequence": seq})
    return out


def strength_summary(phase: str = "base") -> dict:
    """Riepilogo per card UI: protocollo + esercizi."""
    proto = STRENGTH_PROTOCOLS.get(phase, STRENGTH_PROTOCOLS["base"])
    return {
        "phase": phase,
        "sessions_per_week": proto["sessions_per_week"],
        "sets": proto["sets"], "reps": proto["reps"], "pct_1rm": proto["pct_1rm"],
        "exercises": [STRENGTH_EXERCISES[e]["name"] for e in proto["exercises"]],
        "source": "Llanos-Lagos 2025 (Eur J Appl Physiol); Vikmoen 2021",
    }


if __name__ == "__main__":
    import json
    print("FORZA base:", json.dumps(strength_summary("base"), indent=2, ensure_ascii=False))
    print("MOBILITÀ:", json.dumps(build_mobility_plan(1)[0], indent=2, ensure_ascii=False))
