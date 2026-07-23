"""BETA Fase 7e (DIY) — test per my_progress (aderenza personale pian/eseg)."""
from my_progress import compute_my_adherence, iso_week_monday
import datetime as dt


def test_iso_week_monday():
    assert iso_week_monday(dt.date(2026, 7, 23)) in ("2026-W30", "2026-W29")


def test_compute_my_adherence_basic():
    plan = [
        {"start": "2026-07-20", "tss_target": 450, "phase": "Build"},
        {"start": "2026-07-27", "tss_target": 500, "phase": "Build"},
    ]
    # simula che la settimana 1 abbia 400 TSS eseguiti, la 2 zero
    actual = {iso_week_monday(dt.date(2026, 7, 20)): 400.0}
    rows = compute_my_adherence(plan, actual)
    assert len(rows) == 2
    r0 = rows[0]
    assert r0["planned_tss"] == 450.0
    assert r0["actual_tss"] == 400.0
    assert r0["tss_ratio"] == round(400/450, 2)
    assert r0["flag"] in ("green", "amber", "red")
    # settimana 2: previsto 500, eseguito 0 -> flag red
    assert rows[1]["actual_tss"] == 0.0
    assert rows[1]["flag"] == "red"


def test_compute_my_adherence_empty_actual():
    plan = [{"start": "2026-07-20", "tss_target": 450, "phase": "Base"}]
    rows = compute_my_adherence(plan, {})
    assert rows[0]["actual_tss"] == 0.0
    assert rows[0]["flag"] == "red"


def test_compute_my_adherence_no_plan():
    assert compute_my_adherence([], {}) == []
