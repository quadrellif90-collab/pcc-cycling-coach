"""BETA Fase 7a — test per strength_mobility (forza + mobilità)."""
from strength_mobility import (
    build_strength_plan, build_mobility_plan, strength_summary,
    STRENGTH_PROTOCOLS, MOBILITY_ROUTINE,
)


def test_strength_base_has_sessions():
    plan = build_strength_plan("base", 4)
    assert len(plan) == 4
    assert all(len(w["sessions"]) > 0 for w in plan)


def test_strength_race_week_empty():
    plan = build_strength_plan("race_week", 1)
    assert plan[0]["sessions"] == []


def test_strength_pct_within_bounds():
    for w in build_strength_plan("build", 6):
        for s in w["sessions"]:
            assert 70 <= s["pct_1rm"] <= 95


def test_mobility_daily_15min():
    mob = build_mobility_plan(7)
    assert len(mob) == 7
    assert mob[0]["minutes"] == 15
    assert len(mob[0]["sequence"]) == len(MOBILITY_ROUTINE["sequence"])


def test_summary_keys():
    s = strength_summary("peak")
    assert s["sessions_per_week"] == STRENGTH_PROTOCOLS["peak"]["sessions_per_week"]
    assert "source" in s
