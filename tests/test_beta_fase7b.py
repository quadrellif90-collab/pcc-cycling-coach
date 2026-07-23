"""BETA Fase 7b — test per nutrition (carb periodization + supplement + race fuel)."""
from nutrition import compute_nutrition, supplement_list, race_fueling, CARB_PERIODIZATION


def test_carb_periodization_bounds():
    for dt in CARB_PERIODIZATION:
        n = compute_nutrition(dt, 72, 120)
        assert "g" in n["daily_g"]
        assert n["during_g"] >= 0  # 0 nei giorni di riposo è corretto


def test_high_intensity_more_carbs_than_rest():
    hi = compute_nutrition("high_intensity", 72, 120)
    rest = compute_nutrition("rest", 72, 0)
    hi_g = int(hi["daily_g"].split("-")[1].replace(" g", ""))
    rest_g = int(rest["daily_g"].split("-")[1].replace(" g", ""))
    assert hi_g > rest_g


def test_supplement_list_evidence():
    sup = supplement_list()
    assert len(sup) >= 5
    keys = {s["key"] for s in sup}
    assert {"caffeine", "beta_alanine", "nitrate", "bicarbonate", "creatine"}.issubset(keys)


def test_race_fueling_scales():
    short = race_fueling(1.0, 72)
    long = race_fueling(5.0, 72)
    assert long["carb_total_g"] > short["carb_total_g"]
    assert long["carb_per_h_g"] >= short["carb_per_h_g"]
    assert long["caffeine_mg"] == short["caffeine_mg"]  # dose/kg costante
    assert "source" in long
