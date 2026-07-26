"""Tests for PCC 5.1 — altitude layer + real strength/mobility injection.

These verify the new accorgimenti behaviour grounded in the 2025-2026
WorldTour / pro literature review (docs/ricerca_worldtour_pro_2025-2026.md):
- altitude layer adds a note in the 3 weeks before the event
- strength layer injects a real strength session when the week has none
- mobility layer injects a real mobility session when the week has none
- normal mode still leaves every layer note empty (non-regression)
"""
import sys
from datetime import date, timedelta

sys.path.insert(0, r"C:\Users\Siviglino\Desktop\PCC\PCC")

import plan_options as PO
import training_planner as tp


def _first_session_by_type(weeks, stype):
    for w in weeks:
        for s in w.sessions:
            if (s.session_type or "") == stype:
                return s
    return None


def test_altitude_layer_annotates_pre_event():
    goal = tp.Goal(goal_type="event", target_date=date.today() + timedelta(days=30),
                   target_ftp=250, target_weight_kg=70)
    opts = PO.PlanOptions(mode="accorgimenti", enable_altitude=True)
    phases, weeks = tp.generate_plan(goal, plan_options=opts)
    # at least one endurance session inside the 21d altitude window is noted
    noted = [s for w in weeks for s in w.sessions
             if (s.session_type or "") in ("z2", "long_z2", "endurance")
             and s.altitude_note]
    assert noted, "altitude layer should annotate pre-event endurance sessions"


def test_strength_layer_injects_real_session_when_absent():
    goal = tp.Goal(goal_type="general", target_ftp=250, target_weight_kg=70)
    opts = PO.PlanOptions(mode="accorgimenti", enable_strength=True)
    phases, weeks = tp.generate_plan(goal, plan_options=opts)
    injected = _first_session_by_type(weeks, "strength")
    assert injected is not None, "strength layer should inject a real strength session"
    assert injected.strength_note, "injected strength session must carry the note"


def test_mobility_layer_injects_real_session_when_absent():
    goal = tp.Goal(goal_type="general", target_ftp=250, target_weight_kg=70)
    opts = PO.PlanOptions(mode="accorgimenti", enable_mobility=True)
    phases, weeks = tp.generate_plan(goal, plan_options=opts)
    injected = _first_session_by_type(weeks, "mobility")
    assert injected is not None, "mobility layer should inject a real mobility session"
    assert injected.mobility_note, "injected mobility session must carry the note"


def test_normal_mode_has_no_layer_notes_including_altitude():
    goal = tp.Goal(goal_type="general", target_ftp=250, target_weight_kg=70)
    opts = PO.PlanOptions(mode="normal")
    phases, weeks = tp.generate_plan(goal, plan_options=opts)
    for w in weeks:
        for s in w.sessions:
            assert not s.integrator_note
            assert not s.heat_note
            assert not s.strength_note
            assert not s.mobility_note
            assert not s.durability_note
            assert not s.altitude_note
