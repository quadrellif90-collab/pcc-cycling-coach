# Copyright 2024-2026 PCC — Performance Cycling Coach
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


def supplement_doses(bodyweight_kg: float) -> list[dict]:
    """DOSI ASSOLUTE (mg/g) calcolate sul peso dell'atleta.

    Ogni supplemento ha un range per-kg (es. caffeina 3-6 mg/kg); qui si
    moltiplica per il peso reale e si ritorna il range assoluto, così l'atleta
    vede '270-540 mg' invece di solo '3-6 mg/kg'. Fonti: PMC12239112 (review
    Gruppo A), Jeukendrup/UCI 2026.
    """
    out = []
    for k, v in SUPPLEMENTS.items():
        proto = v.get("protocol", "")
        mg_per_kg = None
        g_per_kg = None
        # estrae il range mg/kg o g/kg dal protocollo testuale
        import re
        m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*mg/kg", proto)
        if m:
            mg_per_kg = (float(m.group(1)), float(m.group(2)))
        g = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*g/kg", proto)
        if g:
            g_per_kg = (float(g.group(1)), float(g.group(2)))
        entry = {"key": k, "name": v["name"], "evidence": v["evidence"]}
        if mg_per_kg:
            lo = round(mg_per_kg[0] * bodyweight_kg)
            hi = round(mg_per_kg[1] * bodyweight_kg)
            entry["dose"] = f"{lo}-{hi} mg"
            entry["dose_mg_range"] = [lo, hi]
        elif g_per_kg:
            lo = round(g_per_kg[0] * bodyweight_kg, 1)
            hi = round(g_per_kg[1] * bodyweight_kg, 1)
            entry["dose"] = f"{lo}-{hi} g"
            entry["dose_g_range"] = [lo, hi]
        else:
            entry["dose"] = proto  # protocollo non per-kg (es. 4-6 g/giorno cronico)
        entry["protocol"] = proto
        entry["use"] = v.get("use", "")
        entry["caution"] = v.get("caution", "")
        out.append(entry)
    return out


def _mifflin_tdee(weight_kg: float, height_cm: float, age: int, sex: str,
                 activity: float = 1.5) -> float:
    """TDEE via Mifflin-St Jeor (1995) × fattore attività.

    activity: 1.2 sedentario … 1.9 molto attivo. Per ciclisti in preparazione
    usare 1.6-1.9. Fonte: Mifflin & St Jeor 1995 (più accurato di Harris-Benedict).
    """
    s = 5 if sex.lower().startswith("m") else -161
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + s
    return bmr * activity


def full_nutrition_plan(goal_type: str = "maintain",
                        bodyweight_kg: float = 72.0, height_cm: float = 178.0,
                        age: int = 30, sex: str = "m",
                        activity: float = 1.7,
                        planned_tss_today: float = 0.0,
                        prev_day_tss: float = 0.0) -> dict:
    """Piano nutrizionale COMPLETO e individualizzato.

    Calcola: TDEE, obiettivo (deficit/mantenimento/surplus), macro su base
    scientifica, e COMPENSAZIONE sul carico di oggi + del giorno prima
    ("fuel for the work required", GSSI SSE 231 / Burke 2018).

    Obiettivi:
      - 'cut'     dimagrimento: deficit 300-500 kcal (Mountjoy 2018 IOC; Burke 2018
                  raccomanda NON <30 kcal/kg per evitare perdita di FTP/massa).
      - 'maintain' mantenimento / forma: TDEE + carb matching al carico.
      - 'gain'    aumento massa-lean / ipertrofia: surplus +300-500 kcal.

    Compensazione: se il TSS di oggi o di ieri è alto, i carboidrati salgono
    verso 8-12 g/kg (lavoro richiesto); se basso, scendono a 3-5 g/kg.
    """
    tdee = _mifflin_tdee(bodyweight_kg, height_cm, age, sex, activity)
    # bilancio calorico per obiettivo
    if goal_type == "cut":
        target_kcal = tdee - 400  # deficit moderato (Mountjoy 2018: 300-500)
        note_goal = ("Deficit ~400 kcal: dimagrimento preservando FTP/massa "
                     "(IOC 2018: non scendere <30 kcal/kg).")
    elif goal_type == "gain":
        target_kcal = tdee + 400  # surplus ipertrofia
        note_goal = "Surplus ~400 kcal: supporto ipertrofia/potenza (Burd 2009)."
    else:
        target_kcal = tdee
        note_goal = "Mantenimento / forma: TDEE coperto, carb matching al carico."
    target_kcal = round(target_kcal)

    # Proteine: 1.6-1.8 g/kg (Morton 2018 meta; Phillips 2016) — 1.8 se cut/gain
    protein_g_per_kg = 1.8 if goal_type in ("cut", "gain") else 1.6
    protein_g = round(protein_g_per_kg * bodyweight_kg)
    protein_kcal = protein_g * 4

    # Grassi: 25-30% delle kcal (ISSNA 2018)
    fat_kcal = target_kcal * 0.27
    fat_g = round(fat_kcal / 9)

    # Carboidrati = resto delle kcal (soggetti a compensazione carico)
    carb_kcal = target_kcal - protein_kcal - fat_kcal
    carb_g_base = max(round(carb_kcal / 4), 0)

    # COMPENSAZIONE sul carico: mappa TSS -> g/kg carb (GSSI SSE 231)
    # Questo è un RANGE CONSIGLIATO (min dai macro, max da carico) — NON
    # sovrascrive il bilancio calorico dell'obiettivo (altrimenti il deficit
    # verrebbe "mangiato" dai carboidrati e diventerebbe surplus).
    load = planned_tss_today + prev_day_tss * 0.5  # ieri pesa metà
    if load >= 350:
        carb_g_per_kg_high = 11.0   # giorno di gara / carico alto
    elif load >= 200:
        carb_g_per_kg_high = 8.0
    elif load >= 80:
        carb_g_per_kg_high = 6.0
    else:
        carb_g_per_kg_high = 4.0    # recupero / facile
    carb_g_adjusted = round(carb_g_per_kg_high * bodyweight_kg)
    # Il carboidrato effettivo resta quello coerente col bilancio calorico;
    # esponiamo il range [base, da-carico] come guida "fuel for the work required".
    # base = carb minimo fisiologico (3 g/kg, GSSI SSE 231 recovery floor);
    # da-carico = carb richiesto dal lavoro. Il range ha sempre min <= max.
    carb_g_min = round(3.0 * bodyweight_kg)
    carb_g = carb_g_base
    carb_kcal_adj = carb_g * 4
    total_kcal = protein_kcal + fat_kcal + carb_kcal_adj

    return {
        "goal_type": goal_type,
        "note_goal": note_goal,
        "tdee_kcal": round(tdee),
        "target_kcal": round(total_kcal),
        "macros": {
            "protein_g": protein_g, "protein_g_per_kg": protein_g_per_kg,
            "fat_g": fat_g,
            "carb_g": carb_g, "carb_g_per_kg": round(carb_g / bodyweight_kg, 1),
            "carb_kcal": carb_kcal_adj,
        },
        "load_compensation": {
            "planned_tss_today": planned_tss_today,
            "prev_day_tss": prev_day_tss,
            "load_index": round(load),
            "carb_g_per_kg_range": [3.0, carb_g_per_kg_high],
            "carb_g_range": [carb_g_min, carb_g_adjusted],
            "basis": "fuel for the work required (GSSI SSE 231 / Burke 2018)",
        },
        "sources": ["Mountjoy 2018 IOC", "Burke 2018 ISSN", "GSSI SSE 231",
                    "Jeukendrup/UCI 2026", "Morton 2018 protein", "Mifflin 1995"],
    }


def day_macros(day_type: str, goal_type: str = "maintain",
               bodyweight_kg: float = 72.0, height_cm: float = 178.0,
               age: int = 30, sex: str = "m", activity: float = 1.7,
               planned_tss_today: float = 0.0, prev_day_tss: float = 0.0) -> dict:
    """Macro giornalieri UNICI per tipo di giorno + obiettivo.

    Fonete unica per la card 'Piano alimentare' (ex diet.py) e per la card
    'Nutrizione completa': entrambe leggono qui, così i numeri non divergono.
    I pasti sono la SCOMPOSIZIONE di questi macro (vedi diet.py), non un
    calcolo parallelo.
    """
    plan = full_nutrition_plan(goal_type, bodyweight_kg, height_cm, age, sex,
                               activity, planned_tss_today, prev_day_tss)
    macros = plan["macros"]
    # I macro totali del giorno SONO quelli del piano (bilancio coerente con
    # obiettivo). Il tipo di giorno modula solo il RANGE di carb consigliato
    # (fuel for the work required) esposto a parte, NON altera il bilancio.
    carb_g = macros["carb_g"]
    protein_g = macros["protein_g"]
    fat_g = macros["fat_g"]
    # range carb consigliato per il giorno (g/kg): base da bilancio → da carico
    base_g_per_kg = round(carb_g / bodyweight_kg, 1)
    load_g_per_kg = plan["load_compensation"]["carb_g_per_kg_range"][1]
    if day_type in ("high_intensity", "race", "vo2max", "threshold", "sweetspot"):
        day_carb_g_per_kg = load_g_per_kg
    elif day_type in ("moderate", "tempo", "z2", "long_z2", "overunder"):
        day_carb_g_per_kg = round((base_g_per_kg + load_g_per_kg) / 2, 1)
    else:  # low_recovery, rest, recovery
        day_carb_g_per_kg = base_g_per_kg
    return {
        "day_type": day_type,
        "goal_type": goal_type,
        "target_kcal": plan["target_kcal"],
        "carb_g": carb_g,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carb_kcal": carb_g * 4,
        "protein_kcal": protein_g * 4,
        "fat_kcal": fat_g * 9,
        "carb_g_per_kg": base_g_per_kg,
        "carb_g_per_kg_day": day_carb_g_per_kg,
        "protein_g_per_kg": round(protein_g / bodyweight_kg, 2),
        "load_compensation": plan["load_compensation"],
        "sources": plan["sources"],
    }


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
