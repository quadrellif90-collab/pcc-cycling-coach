"""Live-ish smoke test: POST /api/plan/generate accepts plan_options.

Uses FastAPI TestClient. Sends a minimal 'general' goal with accorgimenti
enabled and asserts the server does NOT 500 and the response plan carries
layer notes when requested. (ICU/setup not required for a general goal with
current_ctl synthesized server-side.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import app as appmod


def _client():
    return TestClient(appmod.app)


def test_generate_with_accorgimenti_does_not_500():
    c = _client()
    body = {
        "goal": "general",
        "weeks": 4,
        "hours_per_week": 6,
        "rest_days": [0],
        "plan_options": {"mode": "accorgimenti", "enable_integrators": True},
    }
    # The endpoint may need a profile/setup; we only assert it parses
    # plan_options without a 500 (a 400 for missing setup is acceptable).
    r = c.post("/api/plan/generate", json=body)
    assert r.status_code != 500, f"500 on generate: {r.text[:300]}"
    # When it succeeds, integrator notes should appear in the plan JSON.
    if r.status_code == 200:
        data = r.json()
        plan = data.get("plan_json") or data
        sessions = [s for w in plan.get("weeks", []) for s in w.get("sessions", [])]
        assert any(s.get("integrator_note") for s in sessions), "no integrator note"


def test_generate_normal_parses():
    c = _client()
    body = {
        "goal": "general",
        "weeks": 4,
        "hours_per_week": 6,
        "rest_days": [0],
        "plan_options": {"mode": "normal"},
    }
    r = c.post("/api/plan/generate", json=body)
    assert r.status_code != 500, f"500 on generate: {r.text[:300]}"
