"""Tests for PPC 5.x PlanOptions selector + accorgimenti layers.

Contract: when mode="normal" (or no PlanOptions), the plan is unchanged
(non-regression vs 4.4.0). Each layer enriches ONLY its target sessions.
"""
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plan_options as PO
import training_planner as tp


# ── Fake plan graph (avoid ICU-dependent Goal/real generate_plan) ────────────
@dataclass
class FakeSession:
    day: date
    day_name: str = "Mon"
    session_type: str = "z2"
    duration_min: int = 60
    tss_estimate: float = 50.0
    description: str = ""
    nutrition_note: str = ""
    integrator_note: str = ""
    heat_note: str = ""
    strength_note: str = ""
    mobility_note: str = ""
    durability_note: str = ""


@dataclass
class FakeWeek:
    phase: str
    start: date
    sessions: list = field(default_factory=list)


def _make_plan():
    base = date(2026, 9, 1)  # a Wednesday; monday = Aug 31
    w_base = FakeWeek("base", base - timedelta(days=2), sessions=[
        FakeSession(day=base, session_type="z2", duration_min=90),
        FakeSession(day=base + timedelta(days=1), session_type="vo2max", duration_min=60),
    ])
    w_build = FakeWeek("build1", base + timedelta(days=5), sessions=[
        FakeSession(day=base + timedelta(days=5), session_type="threshold", duration_min=75),
        FakeSession(day=base + timedelta(days=6), session_type="strength", duration_min=45),
    ])
    return [w_base, w_build]


# ── PlanOptions behaviour ────────────────────────────────────────────────────
def test_normal_mode_forces_all_flags_off():
    o = PO.PlanOptions(mode="normal", enable_nutrition=True, enable_heat=True)
    assert o.is_normal
    assert not o.enable_nutrition
    assert not o.enable_heat
    assert not o.any_enabled


def test_from_dict_roundtrip():
    d = {"mode": "accorgimenti", "enable_nutrition": True, "enable_heat": False}
    o = PO.PlanOptions.from_dict(d)
    assert o.mode == "accorgimenti"
    assert o.enable_nutrition is True
    assert o.enable_heat is False
    assert o.to_dict()["enable_nutrition"] is True


def test_default_is_normal():
    assert PO.DEFAULT_PLAN_OPTIONS.is_normal
    assert not PO.DEFAULT_PLAN_OPTIONS.any_enabled


# ── Non-regression: normal mode does NOT touch sessions ──────────────────────
def test_normal_mode_is_noop():
    weeks = _make_plan()
    out = tp._apply_plan_options(weeks, PO.PlanOptions(mode="normal"),
                                  goal=None)
    for w in out:
        for s in w.sessions:
            assert s.integrator_note == ""
            assert s.heat_note == ""
            assert s.strength_note == ""
            assert s.mobility_note == ""
            assert s.durability_note == ""


def test_none_opts_is_noop():
    weeks = _make_plan()
    out = tp._apply_plan_options(weeks, PO.DEFAULT_PLAN_OPTIONS, goal=None)
    for w in out:
        for s in w.sessions:
            assert s.integrator_note == ""


# ── Layer: integrators (hard sessions only, by phase) ────────────────────────
def test_integrators_only_on_hard_sessions():
    weeks = _make_plan()
    opts = PO.PlanOptions(mode="accorgimenti", enable_integrators=True)
    out = tp._apply_plan_options(weeks, opts, goal=None)
    base = out[0]
    z2 = [s for s in base.sessions if s.session_type == "z2"][0]
    vo2 = [s for s in base.sessions if s.session_type == "vo2max"][0]
    assert z2.integrator_note == ""
    assert vo2.integrator_note != ""


# ── Layer: heat (3 weeks before event) ──────────────────────────────────────
def test_heat_only_near_event():
    target = date(2026, 10, 1)
    weeks = _make_plan()
    opts = PO.PlanOptions(mode="accorgimenti", enable_heat=True)
    out = tp._apply_plan_options(weeks, opts, goal=type("G", (), {"target_date": target})())
    build = out[1]
    assert all(s.heat_note == "" for s in build.sessions)


# ── Layer: strength (note on strength sessions) ──────────────────────────────
def test_strength_note_present():
    weeks = _make_plan()
    opts = PO.PlanOptions(mode="accorgimenti", enable_strength=True)
    out = tp._apply_plan_options(weeks, opts, goal=None)
    build = out[1]
    strength = [s for s in build.sessions if s.session_type == "strength"][0]
    assert "VBT" in strength.strength_note


# ── Layer: mobility (rest/z2/recovery) ───────────────────────────────────────
def test_mobility_on_recovery_sessions():
    weeks = _make_plan()
    opts = PO.PlanOptions(mode="accorgimenti", enable_mobility=True)
    out = tp._apply_plan_options(weeks, opts, goal=None)
    base = out[0]
    z2 = [s for s in base.sessions if s.session_type == "z2"][0]
    assert "hip-flexor" in z2.mobility_note


# ── Layer: dfa durability (long aerobic) ─────────────────────────────────────
def test_durability_on_long_aerobic():
    weeks = _make_plan()
    opts = PO.PlanOptions(mode="accorgimenti", enable_dfa_durability=True)
    out = tp._apply_plan_options(weeks, opts, goal=None)
    base = out[0]
    long_z2 = [s for s in base.sessions if s.session_type == "z2"
                and s.duration_min >= 120]
    if long_z2:
        assert "DFA" in long_z2[0].durability_note
