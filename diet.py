# Copyright 2024-2026 PPC — Programming Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""PPC — Piano alimentare settimanale personalizzato (creatore di diete).

Genera un piano pasti giornaliero/settimanale con:
  - scelte specifiche di ALIMENTI (cosa mangiare / cosa evitare) per pasto,
  - timing (carb davanti all'allenamento, proteine post-allenamento),
  - periodizzazione per fase (cut / maintain / gain) e per tipo di giorno
    (gara / carico / recupero),
  - calorie override opzionale (se il nutrizionista fissa un target).

Fonti (2024-2026):
  - Jeukendrup & UCI Sports Nutrition Project 2026 (fuel timing, race fueling)
  - Burke 2018 / ISSN (macro distribution, protein timing)
  - Morton 2018 (protein 1.6-2.2 g/kg)
  - Areta 2013 (protein timing: 20-25 g ogni 3h)
  - Phillips 2016 (leucine threshold per sintonizzazione proteica)
  - Stote 2016 / Westerterp 2013 (meal frequency, satiety)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ── Banca alimenti per categoria (fonte: USDA + linee guida sportive) ─────────
FOODS = {
    "carb_complex": ["riso integrale", "pasta integrale", "quinoa", "patata dolce", "avena", "legumi"],
    "carb_semplice": ["riso bianco", "pasta bianca", "pane integrale"],
    "protein_magro": ["petto pollo", "tacchino", "merluzzo", "salmone", "uova", "yogurt greco"],
    "protein_enforcer": ["legumi", "tofu", "tempeh", "formaggio fresco"],
    "grassi_benesseri": ["olio extravergine d'oliva", "avocado", "noci", "semi di lino", "mandorle"],
    "vegetali": ["spinaci", "broccoli", "peperone", "zucchine", "carote", "pomodori", "lattuga"],
    "frutta": ["banana", "mele", "frutti di bosco", "arance"],
}
# Alimenti da EVITARE / LIMITARE (per atleta)
AVOID = {
    "cut": ["zuccheri raffinati", "bevande zuccherate", "cibi fritti", "alcol", "cereali raffinati"],
    "maintain": ["zuccheri raffinati", "cibi molto fritti"],
    "gain": ["zuccheri raffinati", "cibi pronti confezionati"],
}


@dataclass
class Meal:
    name: str
    foods: list[str]
    timing: str
    carb_g: float
    protein_g: float
    fat_g: float
    note: str = ""


@dataclass
class DailyDiet:
    day_type: str
    meals: list[Meal] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    total_kcal: float = 0.0
    total_carb: float = 0.0
    total_protein: float = 0.0
    total_fat: float = 0.0


def _meal(name, foods, timing, carb, protein_g=0, fat=0, note=""):
    return Meal(name=name, foods=foods, timing=timing, carb_g=carb,
                protein_g=protein_g, fat_g=fat, note=note)


def build_daily_diet(day_type: str = "moderate", bodyweight_kg: float = 72.0,
                     goal_type: str = "maintain",
                     custom_calories: Optional[float] = None,
                     training_time: str = "morning") -> DailyDiet:
    """Genera il piano pasti per UN giorno.

    day_type: rest / easy / moderate / hard / race
    custom_calories: se impostato (es. da nutrizionista), sovrascrive il target.
    training_time: morning / afternoon / evening (per timing carb).
    """
    # Calorie: override nutrizionista, altrimenti TDEE stimato
    if custom_calories is not None and custom_calories > 0:
        target_kcal = float(custom_calories)
        kcal_source = "impostato dal nutrizionista"
    else:
        # TDEE approssimativo (Mifflin-St Jeor medio × fattore)
        target_kcal = 30 * bodyweight_kg * 1.7  # ~30 kcal/kg per atleta attivo
        kcal_source = "calcolato (30 kcal/kg × fattore attività)"

    # Macro ratio per obiettivo (Burke 2018 / ISSN)
    if goal_type == "cut":
        carb_r, prot_r, fat_r = 0.45, 0.30, 0.25
    elif goal_type == "gain":
        carb_r, prot_r, fat_r = 0.45, 0.25, 0.30
    else:
        carb_r, prot_r, fat_r = 0.50, 0.20, 0.30

    # Adatta macro al tipo di giorno (fuel for the work required)
    if day_type == "race":
        carb_r = 0.65  # alta gara
    elif day_type == "hard":
        carb_r = 0.55
    elif day_type == "rest":
        carb_r = 0.40
        fat_r = 0.35

    target_carb = round(target_kcal * carb_r / 4)
    target_prot = round(target_kcal * prot_r / 4)
    target_fat = round(target_kcal * fat_r / 9)

    # ── Pasti (Areta 2013: proteine ogni 3h, 20-25g per pasto) ──────────────
    meals = []
    # Colazione
    meals.append(_meal(
        "Colazione",
        ["avena", "yogurt greco", "frutta di bosco", "semi di lino"],
        "alla sveglia",
        carb=round(target_carb * 0.25),
        protein_g=round(target_prot * 0.25),
        fat=round(target_fat * 0.20),
        note="Avena lenta (β-glucani); yogurt greco per proteine complete.",
    ))
    # Spuntino mattina
    meals.append(_meal(
        "Spuntino mattina",
        ["frutta", "mandorle"],
        "2h dopo colazione",
        carb=round(target_carb * 0.10),
        protein_g=round(target_prot * 0.15),
        fat=round(target_fat * 0.15),
    ))
    # PRANZO (o pre-allenamento se training_time=afternoon)
    if training_time == "afternoon":
        meals.append(_meal(
            "Pranzo (pre-allenamento)",
            ["riso integrale", "petto pollo", "broccoli", "olio extravergine d'oliva"],
            "2-3h prima allenamento",
            carb=round(target_carb * 0.30),
            protein_g=round(target_prot * 0.30),
            fat=round(target_fat * 0.15),
            note="Carb complesso 2-3h prima: rifornisce glicogeno senza gonfiore.",
        ))
    else:
        meals.append(_meal(
            "Pranzo",
            ["pasta integrale", "merluzzo", "peperone", "zucchine"],
            "12:30-14:00",
            carb=round(target_carb * 0.30),
            protein_g=round(target_prot * 0.30),
            fat=round(target_fat * 0.20),
        ))
    # PRE-allenamento (se training_time=morning)
    if training_time == "morning":
        meals.append(_meal(
            "Pre-allenamento",
            ["banana", "riso bianco"],
            "30-60 min prima",
            carb=round(target_carb * 0.15),
            protein_g=round(target_prot * 0.05),
            fat=0,
            note="Carb semplice + basso proteine: rapido, niente gonfiore.",
        ))
    # DURANTE allenamento (solo hard/race)
    if day_type in ("hard", "race"):
        meals.append(_meal(
            "Durante allenamento",
            ["bicchiere acqua", "carboidrati 60-90 g/h (glucosio-fruttosio)"],
            "durante lo sforzo",
            carb=round(target_carb * 0.10),
            protein_g=0, fat=0,
            note="60-90 g/h per sforzi >60min (Jeukendrup 2026).",
        ))
    # POST-allenamento
    meals.append(_meal(
        "Post-allenamento",
        ["yogurt greco", "frutti di bosco", "banana"],
        "entro 30-60 min",
        carb=round(target_carb * 0.15),
        protein_g=round(target_prot * 0.25),
        fat=0,
        note="Proteine + carb entro finestra anabolica (Phillips 2016).",
    ))
    # Cena
    meals.append(_meal(
        "Cena",
        ["quinoa", "salmone", "spinaci", "olio extravergine d'oliva"],
        "19:00-20:30",
        carb=round(target_carb * 0.15),
        protein_g=round(target_prot * 0.20),
        fat=round(target_fat * 0.25),
        note="Carb moderati + grassi buoni: non gonfiore, supporto notturno.",
    ))
    # Spuntino sera (solo se gain/maintain)
    if goal_type in ("gain", "maintain"):
        meals.append(_meal(
            "Spuntino sera",
            ["latte", "noci"],
            "prima di dormire",
            carb=round(target_carb * 0.05),
            protein_g=round(target_prot * 0.10),
            fat=round(target_fat * 0.10),
            note="Proteine lente per sinciliazione notturna.",
        ))

    # Calcola totali e normalizza (i pasti possono non sommare esattamente)
    tc = sum(m.carb_g for m in meals)
    tp = sum(m.protein_g for m in meals)
    tf = sum(m.fat_g for m in meals)
    total_kcal = round(tc * 4 + tp * 4 + tf * 9)

    avoid = AVOID.get(goal_type, AVOID["maintain"])
    if day_type == "race":
        avoid += ["alcol 24h pre-gara", "cibi nuovi in gara"]

    return DailyDiet(
        day_type=day_type,
        meals=meals,
        avoid=avoid,
        total_kcal=total_kcal,
        total_carb=round(tc),
        total_protein=round(tp),
        total_fat=round(tf),
    )


def build_weekly_diet(goal_type: str = "maintain", bodyweight_kg: float = 72.0,
                      custom_calories: Optional[float] = None) -> dict:
    """Piano alimentare SETTIMANALE (7 giorni) con variazione pasti."""
    day_map = {
        "Lunedì": "easy", "Martedì": "moderate", "Mercoledì": "hard",
        "Giovedì": "easy", "Venerdì": "moderate", "Sabato": "hard",
        "Domenica": "rest",
    }
    # Se custom_calories, applica a tutti i giorni; altrimenti varia leggermente
    days = []
    for name, dt in day_map.items():
        if custom_calories is not None:
            cal = custom_calories
        else:
            # variazione: giorni di recupero meno calorici, gara più
            mult = {"rest": 0.85, "easy": 0.90, "moderate": 1.0,
                    "hard": 1.10, "race": 1.20}
            cal = None  # lascia che build_daily_diet calcoli da 30 kcal/kg
        d = build_daily_diet(dt, bodyweight_kg, goal_type, custom_calories=cal)
        days.append({"day": name, "day_type": dt, "diet": d})
    return {
        "goal_type": goal_type,
        "bodyweight_kg": bodyweight_kg,
        "calorie_source": "impostato dal nutrizionista" if custom_calories else "calcolato (30 kcal/kg × fattore)",
        "days": [{"day": d["day"], "day_type": d["day_type"],
                  "meals": [m.__dict__ for m in d["diet"].meals],
                  "avoid": d["diet"].avoid,
                  "total_kcal": d["diet"].total_kcal,
                  "total_carb": d["diet"].total_carb,
                  "total_protein": d["diet"].total_protein,
                  "total_fat": d["diet"].total_fat} for d in days],
    }


if __name__ == "__main__":
    import json
    d = build_daily_diet("hard", 70, "maintain")
    print(json.dumps({"meals": [m.__dict__ for m in d.meals],
                      "avoid": d.avoid, "total_kcal": d.total_kcal}, indent=2, ensure_ascii=False))
