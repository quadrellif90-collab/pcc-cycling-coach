"""Smoke test: generate_plan honors plan_options end-to-end without ICU.

Builds a minimal Goal and asserts that, with accorgimenti enabled, the
produced sessions carry the layer notes (no ICU fetch required for a plain
'general' goal with current_ctl supplied).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plan_options as PO
import training_planner as tp


def _minimal_goal():
    return tp.Goal(
        goal_type="general",
        target_date=None,
        hours_per_week=6,
        max_weekday_hours=1.5,
        max_weekend_hours=3.0,
        rest_days=[0],
        plan_weeks=6,
    )


def test_generate_plan_normal_has_no_layer_notes():
    goal = _minimal_goal()
    phases, weeks = tp.generate_plan(
        goal, current_ctl=50, plan_options=PO.PlanOptions(mode="normal"))
    notes = []
    for w in weeks:
        for s in w.sessions:
            notes += [s.integrator_note, s.heat_note, s.strength_note,
                      s.mobility_note, s.durability_note, s.nutrition_note]
    assert all(n == "" for n in notes), "normal mode leaked a layer note"


def test_generate_plan_with_nutrition_adds_notes():
    goal = _minimal_goal()
    phases, weeks = tp.generate_plan(
        goal, current_ctl=50,
        plan_options=PO.PlanOptions(mode="accorgimenti", enable_nutrition=True))
    nutri = [s.nutrition_note for w in weeks for s in w.sessions
             if s.session_type != "rest"]
    assert any(n != "" for n in nutri), "nutrition layer produced nothing"


def test_generate_plan_with_integrators_marks_hard():
    goal = _minimal_goal()
    phases, weeks = tp.generate_plan(
        goal, current_ctl=50,
        plan_options=PO.PlanOptions(mode="accorgimenti", enable_integrators=True))
    hard = [s for w in weeks for s in w.sessions
            if s.session_type in ("vo2max", "threshold", "sprint")]
    if hard:
        assert any(s.integrator_note != "" for s in hard)
