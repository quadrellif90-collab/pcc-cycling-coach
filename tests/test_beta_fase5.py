"""BETA Fase 5 — test per daily_recalculate_adjustment.

Verifica che la combinazione di segnali HRV/sonno/DFA/TSB produca un
fattore di aggiustamento coerente e nei limiti 0.80-1.10.
"""
from training_planner import daily_recalculate_adjustment


def test_empty_signals_neutral():
    a = daily_recalculate_adjustment()
    assert a["factor"] == 1.0
    assert a["recommendation"]


def test_low_hrv_reduces_load():
    a = daily_recalculate_adjustment(hrv_ms=15)
    assert a["factor"] < 1.0
    assert a["factor"] >= 0.80


def test_good_readiness_allows_full():
    a = daily_recalculate_adjustment(hrv_ms=50, sleep_score=85, tsb=20)
    assert a["factor"] > 1.0
    assert a["factor"] <= 1.10


def test_factor_clamped():
    a = daily_recalculate_adjustment(hrv_ms=5, hooper=28, sleep_score=30, tsb=-40)
    assert a["factor"] >= 0.80  # non scende sotto il clamp
    a2 = daily_recalculate_adjustment(hrv_ms=80, sleep_score=100, tsb=40)
    assert a2["factor"] <= 1.10  # non sale sopra il clamp
