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
    assert high["load_compensation"]["carb_g_per_kg_range"][1] >= 11.0
    assert low["load_compensation"]["carb_g_per_kg_range"][1] <= 4.0
    assert high["load_compensation"]["carb_g_range"][1] > low["load_compensation"]["carb_g_range"][1]


def test_motori_nutrizione_coerenti():
    """Contratto: full_nutrition_plan, day_macros e diet devono dare gli
    STESSI macro totali (nessun numero divergente tra le card)."""
    from nutrition import full_nutrition_plan, day_macros
    from diet import build_daily_diet
    for gt in ("cut", "maintain", "gain"):
        plan = full_nutrition_plan(gt, 75, 180, 35, "m")
        dm = day_macros("hard", gt, 75, 180, 35, "m")
        assert dm["carb_g"] == plan["macros"]["carb_g"]
        assert dm["protein_g"] == plan["macros"]["protein_g"]
        assert dm["fat_g"] == plan["macros"]["fat_g"]
        diet = build_daily_diet("hard", 75, gt, height_cm=180, age=35, sex="m",
                                planned_tss_today=250, prev_day_tss=250)
        ratio = diet.total_kcal / plan["target_kcal"]
        assert 0.99 <= ratio <= 1.01, f"{gt}: pasti {diet.total_kcal} != target {plan['target_kcal']}"


def test_deficit_coerente():
    """cut < maintain < gain (il deficit deve essere reale, non surplus)."""
    cut = full_nutrition_plan("cut", 75, 180, 35, "m")["target_kcal"]
    maint = full_nutrition_plan("maintain", 75, 180, 35, "m")["target_kcal"]
    gain = full_nutrition_plan("gain", 75, 180, 35, "m")["target_kcal"]
    assert cut < maint < gain


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
