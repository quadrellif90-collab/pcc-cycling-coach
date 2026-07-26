# Copyright 2024-2026 PCC — Performance Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""PCC — Piano alimentare settimanale (vista presentazionale di nutrition.py).

QUESTO MODULO NON CALCOLA MACRO. Legge `day_macros()` da nutrition.py (l'unico
motore: TDEE Mifflin + obiettivo + compensazione carico) e SCOMPONE quei macro
nei pasti con timing/ alimenti evidence-based (Jeukendrup/UCI 2026, Burke 2018,
Areta 2013, Phillips 2016). Così la card "Piano alimentare" e la card
"Nutrizione completa" mostrano gli STESSI numeri.

Fonti (2024-2026):
  - Jeukendrup & UCI Sports Nutrition Project 2026 (fuel timing, race fueling)
  - Burke 2018 / ISSN (macro distribution, protein timing)
  - Morton 2018 (protein 1.6-2.2 g/kg)
  - Areta 2013 (protein timing: 20-25 g ogni 3h)
  - Phillips 2016 (leucine threshold per sintonizzazione proteica)
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
    food_grams: dict = field(default_factory=dict)  # alimento -> grammi (evidence-based)


@dataclass
class DailyDiet:
    day_type: str
    meals: list[Meal] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    total_kcal: float = 0.0
    total_carb: float = 0.0
    total_protein: float = 0.0
    total_fat: float = 0.0


def _meal(name, foods, timing, carb, protein_g=0, fat=0, note="", grams=None):
    return Meal(name=name, foods=foods, timing=timing, carb_g=carb,
                protein_g=protein_g, fat_g=fat, note=note,
                food_grams=grams or {})


def build_daily_diet(day_type: str = "moderate", bodyweight_kg: float = 72.0,
                     goal_type: str = "maintain",
                     custom_calories: Optional[float] = None,
                     training_time: str = "morning",
                     height_cm: float = 178.0, age: int = 30, sex: str = "m",
                     activity: float = 1.7,
                     planned_tss_today: float = 0.0, prev_day_tss: float = 0.0) -> DailyDiet:
    """Genera il piano pasti per UN giorno.

    I macro TOTALI del giorno vengono da `day_macros()` (nutrition.py, motore
    unico). Qui vengono solo SCOMPOSTI nei pasti con timing/ alimenti.
    custom_calories: se impostato (es. da nutrizionista), sovrascrive il target
    e ricalcola i macro mantenendo la ripartizione dell'obiettivo.
    """
    from nutrition import day_macros

    dm = day_macros(day_type, goal_type, bodyweight_kg, height_cm, age, sex,
                    activity, planned_tss_today, prev_day_tss)
    target_kcal = dm["target_kcal"]
    target_carb = dm["carb_g"]
    target_prot = dm["protein_g"]
    target_fat = dm["fat_g"]

    # Se il nutrizionista fissa calorie, rispetta la ripartizione % dell'obiettivo
    if custom_calories is not None and custom_calories > 0:
        tot = target_kcal if target_kcal > 0 else 1
        p_carb = target_carb * 4 / tot
        p_prot = target_prot * 4 / tot
        p_fat = target_fat * 9 / tot
        target_kcal = float(custom_calories)
        target_carb = round(target_kcal * p_carb / 4)
        target_prot = round(target_kcal * p_prot / 4)
        target_fat = round(target_kcal * p_fat / 9)

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
        grams={"avena": 60, "yogurt greco": 150, "frutta di bosco": 80, "semi di lino": 10},
    ))
    # Spuntino mattina
    meals.append(_meal(
        "Spuntino mattina",
        ["frutta", "mandorle"],
        "2h dopo colazione",
        carb=round(target_carb * 0.10),
        protein_g=round(target_prot * 0.15),
        fat=round(target_fat * 0.15),
        grams={"frutta": 150, "mandorle": 20},
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
            grams={"riso integrale": 90, "petto pollo": 150, "broccoli": 150, "olio extravergine d'oliva": 10},
        ))
    else:
        meals.append(_meal(
            "Pranzo",
            ["pasta integrale", "merluzzo", "peperone", "zucchine"],
            "12:30-14:00",
            carb=round(target_carb * 0.30),
            protein_g=round(target_prot * 0.30),
            fat=round(target_fat * 0.20),
            grams={"pasta integrale": 80, "merluzzo": 150, "peperone": 100, "zucchine": 120},
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
            grams={"banana": 100, "riso bianco": 50},
        ))
    # DURANTE allenamento (solo hard/race)
    if day_type in ("hard", "race", "high_intensity", "vo2max", "threshold"):
        meals.append(_meal(
            "Durante allenamento",
            ["bicchiere acqua", "carboidrati 60-90 g/h (glucosio-fruttosio)"],
            "durante lo sforzo",
            carb=round(target_carb * 0.10),
            protein_g=0, fat=0,
            note="60-90 g/h per sforzi >60min (Jeukendrup 2026).",
            grams={},
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
        grams={"yogurt greco": 150, "frutti di bosco": 80, "banana": 100},
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
        grams={"quinoa": 70, "salmone": 140, "spinaci": 120, "olio extravergine d'oliva": 10},
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
            note="Proteine lente per sincetizzazione notturna.",
            grams={"latte": 200, "noci": 25},
        ))

    # Calcola totali (somma pasti; può discostarsi di <2% per arrotondamenti)
    tc = sum(m.carb_g for m in meals)
    tp = sum(m.protein_g for m in meals)
    tf = sum(m.fat_g for m in meals)
    # NORMALIZZA al totale esatto di day_macros (motore unico) così i pasti
    # sommano ESATTAMENTE al target — nessun numero divergente.
    if tc > 0:
        kc = target_carb / tc
        for m in meals:
            m.carb_g = round(m.carb_g * kc)
    if tp > 0:
        kp = target_prot / tp
        for m in meals:
            m.protein_g = round(m.protein_g * kp)
    if tf > 0:
        kf = target_fat / tf
        for m in meals:
            m.fat_g = round(m.fat_g * kf)
    tc = sum(m.carb_g for m in meals)
    tp = sum(m.protein_g for m in meals)
    tf = sum(m.fat_g for m in meals)
    # Compensa il residuo di arrotondamento sull'ultimo pasto (così la somma
    # è ESATTAMENTE il target, nessun numero divergente).
    if meals:
        last = meals[-1]
        last.carb_g += target_carb - tc
        last.protein_g += target_prot - tp
        last.fat_g += target_fat - tf
    tc = sum(m.carb_g for m in meals)
    tp = sum(m.protein_g for m in meals)
    tf = sum(m.fat_g for m in meals)
    total_kcal = round(tc * 4 + tp * 4 + tf * 9)

    avoid = AVOID.get(goal_type, AVOID["maintain"])
    if day_type in ("race", "high_intensity"):
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
                      custom_calories: Optional[float] = None,
                      height_cm: float = 178.0, age: int = 30, sex: str = "m",
                      activity: float = 1.7) -> dict:
    """Piano alimentare SETTIMANALE (7 giorni) con variazione pasti.

    I macro totali settimanali derivano da day_macros (motore unico); la
    variazione giornaliera riflette il tipo di giorno (recupero vs carico),
    coerente con 'fuel for the work required'.
    """
    from nutrition import day_macros
    day_map = {
        "Lunedì": "easy", "Martedì": "moderate", "Mercoledì": "hard",
        "Giovedì": "easy", "Venerdì": "moderate", "Sabato": "hard",
        "Domenica": "rest",
    }
    days = []
    for name, dt in day_map.items():
        # variazione carico: easy/rest meno carb del giorno, hard di più
        planned = 250 if dt == "hard" else (120 if dt == "moderate" else 40)
        prev = 250 if dt in ("hard", "moderate") else 40
        d = build_daily_diet(dt, bodyweight_kg, goal_type, custom_calories,
                             height_cm=height_cm, age=age, sex=sex,
                             activity=activity,
                             planned_tss_today=planned, prev_day_tss=prev)
        days.append({"day": name, "day_type": dt, "diet": d})
    return {
        "goal_type": goal_type,
        "bodyweight_kg": bodyweight_kg,
        "calorie_source": ("impostato dal nutrizionista" if custom_calories
                           else "motore unico PCC (Mifflin + obiettivo + carico)"),
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
    d = build_daily_diet("hard", 75, "cut", height_cm=180, age=35, sex="m")
    print(json.dumps({"meals": [m.__dict__ for m in d.meals],
                      "avoid": d.avoid, "total_kcal": d.total_kcal},
                     indent=2, ensure_ascii=False))
