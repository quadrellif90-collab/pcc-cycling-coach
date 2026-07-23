# Copyright 2024-2026 PPC — Programming Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""BETA Fase 7b — Nutrizione + Integrazione per ciclisti.

Fonti scientifiche (2024-2026):
- GSSI SSE 231 (Burke): carb quotidiani 7-12 g/kg BM; pre-gara 1-4 g/kg a
  1-4h (glucosio+fruttosio); DURANTE 30-90 g/h (fino 120) in miscele
  glucosio-fruttosio 1:0.8; POST 1.0-1.2 g/kg/h per 4h. Paradigma
  "fuel for the work required" (periodizzazione carb sul carico).
- Jeukendrup / UCI Sports Nutrition Project 2026: nutrizione di gara
  individualizzata, context-specific.
- PMC12239112 (systematic review + meta-analysis RCT): supplement Gruppo A
  alta evidenza = caffeine (3-6 mg/kg a 40-75 min), beta-alanine (cronica,
  buffering), nitrate/beetroot, bicarbonate, creatine, glycerol. Attenzione
  CYP1A2 / abitudine caffeina modulano la risposta.

Il modulo è AUTONOMO: NON modifica training_planner. Ritorna dict pronti per
card UI / export PDF (Fase 7c).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# ── Periodizzazione carboidrati (g/kg BM) per tipo di giorno ────────────────
# Basato su GSSI SSE 231 "fuel for the work required".
CARB_PERIODIZATION = {
    "high_intensity": {"label": "Allenamento ad alta intensità / gara", "g_per_kg": (8, 12),
                        "during_g_per_h": (60, 90), "note": "Carico massimo, glucosio-fruttosio 1:0.8"},
    "moderate":       {"label": "Allenamento moderato (Z2-Z3)", "g_per_kg": (5, 8),
                        "during_g_per_h": (30, 60), "note": "Carb moderati, sufficienti al lavoro"},
    "low_recovery":   {"label": "Recupero / giorno facile", "g_per_kg": (3, 5),
                        "during_g_per_h": (0, 30), "note": "Carb più bassi, rigenerazione"},
    "rest":           {"label": "Riposo", "g_per_kg": (3, 5),
                        "during_g_per_h": (0, 0), "note": "Mantenimento, evitare eccesso"},
}

# ── Protocolli supplement (Gruppo A, alta evidenza) ─────────────────────────
SUPPLEMENTS = {
    "caffeine": {
        "name": "Caffeina", "evidence": "Alta",
        "protocol": "3-6 mg/kg, 40-75 min prima",
        "use": "Gara / HIIT. Varia per CYP1A2 e abitudine.",
        "caution": "Evitare abitudine; non la sera (sonno).",
    },
    "beta_alanine": {
        "name": "Beta-alanina", "evidence": "Alta",
        "protocol": "4-6 g/giorno cronico (diviso), 4+ sett",
        "use": "Sforzi >2 min (VO2max, soglia). Buffer intramuscolare.",
        "caution": "Parestesia (formicolio) dose singola alta; usare retarded.",
    },
    "nitrate": {
        "name": "Nitrato (barbabietola)", "evidence": "Media-Alta",
        "protocol": "6-13 mmol, 2-3h prima (cronica 5-6 gg rafforza)",
        "use": "Crono, soglia, endurance <2.5h. Minor effetto nei très allenati.",
        "caution": "Effetto ridotto negli élite; variabile individuo.",
    },
    "bicarbonate": {
        "name": "Bicarbonato", "evidence": "Alta",
        "protocol": "0.2-0.3 g/kg, 60-90 min prima",
        "use": "Sforzi 1-4 min (VO2max, ripetute). Buffer extracellulare.",
        "caution": "Disturbi GI a dosi alte; testare in allenamento.",
    },
    "creatine": {
        "name": "Creatina", "evidence": "Alta",
        "protocol": "3-5 g/giorno (o load 0.3 g/kg x5-7 gg)",
        "use": "Scatti, sprint, potenza. Combinabile con forza (7a).",
        "caution": "Idratazione; non sinergico con caffeina acuta.",
    },
    "glycerol": {
        "name": "Glicerolo", "evidence": "Media",
        "protocol": "1.0-1.2 g/kg con acqua, 2h prima",
        "use": "Idratazione+gran fondo/caldo (retenzione fluidi).",
        "caution": "Carico gastrico; testare tolleranza.",
    },
}


@dataclass
class DailyCarbs:
    day_type: str
    bodyweight_kg: float
    during_min: int = 0

    def to_dict(self) -> dict:
        spec = CARB_PERIODIZATION.get(self.day_type, CARB_PERIODIZATION["moderate"])
        lo, hi = spec["g_per_kg"]
        daily_lo = round(lo * self.bodyweight_kg)
        daily_hi = round(hi * self.bodyweight_kg)
        dlo, dhi = spec["during_g_per_h"]
        during = round((dlo + dhi) / 2 * (self.during_min / 60.0)) if self.during_min > 0 else 0
        return {
            "day_type": self.day_type,
            "label": spec["label"],
            "daily_g": f"{daily_lo}-{daily_hi} g",
            "daily_g_per_kg": f"{lo}-{hi} g/kg",
            "during_g": during,
            "during_range_g_per_h": f"{dlo}-{dhi} g/h" if dhi else "—",
            "note": spec["note"],
        }


def compute_nutrition(day_type: str = "moderate", bodyweight_kg: float = 72.0,
                      during_min: int = 0) -> dict:
    """Calcola carboidrati giornalieri + durante sforzo per un atleta."""
    dc = DailyCarbs(day_type, bodyweight_kg, during_min)
    return dc.to_dict()


def supplement_list() -> list[dict]:
    """Ritorna i protocolli supplement evidence-based (Gruppo A)."""
    return [{"key": k, **v} for k, v in SUPPLEMENTS.items()]


def race_fueling(duration_h: float, bodyweight_kg: float = 72.0) -> dict:
    """Piano di gara: carb durante (g/h) + caffeina pre, basati su Jeukendrup 2026.

    duration_h: durata stimata gara in ore.
    """
    if duration_h < 1.5:
        per_h = 45
        note = "Sforzo breve: 30-60 g/h sufficienti."
    elif duration_h < 2.5:
        per_h = 70
        note = "Medio: 60-90 g/h (glucosio-fruttosio 1:0.8)."
    else:
        per_h = 90
        note = "Lungo (>2.5h): fino 90-120 g/h tollerabili; individualizzare."
    total = round(per_h * duration_h)
    return {
        "duration_h": duration_h,
        "carb_per_h_g": per_h,
        "carb_total_g": total,
        "carb_total_g_per_kg": round(total / bodyweight_kg, 1),
        "caffeine_mg": round(4 * bodyweight_kg),  # ~4 mg/kg pre-gara
        "note": note,
        "source": "Jeukendrup / UCI Sports Nutrition Project 2026; GSSI SSE 231",
    }


if __name__ == "__main__":
    import json
    print("NUTRIZIONE (moderato, 72kg):", json.dumps(compute_nutrition("moderate", 72, 90), indent=2, ensure_ascii=False))
    print("GARA 4h:", json.dumps(race_fueling(4.0, 72), indent=2, ensure_ascii=False))
    print("SUPPLEMENT:", json.dumps(supplement_list(), indent=2, ensure_ascii=False)[:400])
