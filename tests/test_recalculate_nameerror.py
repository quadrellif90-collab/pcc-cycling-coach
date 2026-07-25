"""Regression test per il NameError pre-esistente in recalculate_plan.

training_planner.recalculate_plan chiamava plan_week(..., plan_options=opts)
ma `opts` non era definito nello scope -> NameError che faceva crashare
auto-recalc / regenerate in certe condizioni. Fix: la firma accetta
plan_options e lo risolve in opts (PO.DEFAULT_PLAN_OPTIONS se None).
"""

import sys

sys.path.insert(0, ".")

import training_planner as tp
from datetime import date


def test_recalculate_plan_no_nameerror():
    """recalculate_plan deve girare senza NameError anche senza plan_options."""
    goal = tp.Goal(goal_type="general", hours_per_week=8.0)
    _, weeks = tp.generate_plan(goal=goal)
    # Prima crashava con NameError: name 'opts' is not defined
    try:
        new_phases, all_weeks, info = tp.recalculate_plan(
            goal=goal, current_plan_weeks=weeks, current_ctl=40.0,
        )
    except NameError as e:
        raise AssertionError(f"recalculate_plan ancora crasha NameError: {e}")
    assert isinstance(all_weeks, list)
    assert "action" in info


def test_recalculate_plan_passes_plan_options():
    """Se si passa PlanOptions, deve essere onorato senza errori."""
    import plan_options as PO
    goal = tp.Goal(goal_type="event", target_date=date(2026, 9, 1),
                   target_ftp=243, target_weight_kg=70)
    _, weeks = tp.generate_plan(goal=goal)
    opts = PO.PlanOptions(mode="accorgimenti", enable_heat=True)
    try:
        tp.recalculate_plan(goal=goal, current_plan_weeks=weeks,
                             current_ctl=40.0, plan_options=opts)
    except NameError as e:
        raise AssertionError(f"recalculate_plan con plan_options crasha: {e}")
