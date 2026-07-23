"""BETA Fase 7c — test per plan_export (compositore HTML integrato)."""
from plan_export import build_plan_html


def test_html_contains_sections():
    html = build_plan_html(
        athlete_name="Mario Rossi", goal_name="Gran Fondo",
        strength_plan=[{"week": 1, "sessions": [{"exercise": "Back Squat", "sets": 4, "reps": 6, "pct_1rm": 85}]}],
        strength_summary={"sessions_per_week": 2, "sets": 4, "reps": 6, "pct_1rm": 85, "source": "X"},
        mobility_plan=[{"minutes": 15, "sequence": [{"exercise": "Stretching flessori anca", "duration_s": 90}]}],
        nutrition_day={"label": "Gara", "daily_g": "800-1000 g", "daily_g_per_kg": "10-12 g/kg",
                       "during_g": 120, "during_range_g_per_h": "90-120 g/h", "note": "n"},
        supplements=[{"name": "Caffeina", "evidence": "Alta", "protocol": "4 mg/kg", "caution": "c"}],
        race_fueling={"duration_h": 4, "carb_per_h_g": 90, "carb_total_g": 360, "carb_total_g_per_kg": 5, "caffeine_mg": 288, "source": "J"},
    )
    for marker in ["Mario Rossi", "Gran Fondo", "Ciclismo", "Forza in palestra",
                   "Mobilità", "Nutrizione", "Back Squat", "Caffeina", "Piano di gara (4"]:
        assert marker in html, f"manca: {marker}"
    assert html.strip().startswith("<!DOCTYPE html>")


def test_html_escapes():
    html = build_plan_html(athlete_name='<script>alert(1)</script>')
    assert "<script>alert(1)</script>" not in html  # deve essere escaped
    assert "&lt;script&gt;" in html
