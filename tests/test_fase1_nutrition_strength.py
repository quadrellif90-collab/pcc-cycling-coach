"""Test Fase 1: calcolo nutrizione/forza individualizzato sull'atleta."""
from nutrition import supplement_doses, full_nutrition_plan, compute_nutrition
from strength_mobility import build_strength_plan


def test_supplement_doses_weight_based():
    # caffeina 3-6 mg/kg x 72kg => 216-432 mg (non solo "3-6 mg/kg")
    doses = {d["key"]: d for d in supplement_doses(72.0)}
    caf = doses["caffeine"]
    assert "mg" in caf["dose"]
    lo, hi = caf["dose_mg_range"]
    assert lo == 216 and hi == 432
    # peso diverso => dose diversa (individualizzazione)
    doses90 = {d["key"]: d for d in supplement_doses(90.0)}
    assert doses90["caffeine"]["dose_mg_range"][1] == 540


def test_full_nutrition_plan_cut():
    p = full_nutrition_plan("cut", 80, 180, 35, "m", 1.7)
    assert p["target_kcal"] < p["tdee_kcal"]  # deficit
    assert p["macros"]["protein_g"] >= round(1.8 * 80) - 1
    assert "Mountjoy 2018 IOC" in p["sources"]


def test_full_nutrition_load_compensation():
    # giorno di carico alto => carb g/kg alto
    high = full_nutrition_plan("maintain", 70, 175, 30, "m", 1.7,
                               planned_tss_today=400, prev_day_tss=300)
    low = full_nutrition_plan("maintain", 70, 175, 30, "m", 1.7,
                              planned_tss_today=30, prev_day_tss=0)
    assert high["load_compensation"]["carb_g_per_kg"] >= 11.0
    assert low["load_compensation"]["carb_g_per_kg"] <= 4.0
    assert high["macros"]["carb_g"] > low["macros"]["carb_g"]


def test_compute_nutrition_weight():
    n = compute_nutrition("high_intensity", 70, 90)
    # 8-12 g/kg x 70 => 560-840 g
    assert n["daily_g"] in ("560-840 g", "560-840 g")


def test_strength_load_kg():
    plan = build_strength_plan("base", 1, one_rm_kg=120.0)
    s = plan[0]["sessions"][0]
    # Back Squat base 85% di 120kg => ~102 kg
    assert "load_kg" in s
    assert abs(s["load_kg"] - round(120 * 0.85, 1)) < 0.5
