"""BETA Fase 4.5 — test per recommend_block_model.

Verifica la regola basata sulla meta-analisi Sports Med 2024:
POL > THR/pyramidal per VO2peak solo <12 settimane; oltre, pyramidal
è equivalente e più sostenibile in mantenimento.
"""
from training_planner import recommend_block_model


def test_short_plan_stays_polarized():
    assert recommend_block_model(4) == "polarized"
    assert recommend_block_model(8) == "polarized"
    assert recommend_block_model(12) == "polarized"


def test_long_plan_switches_to_pyramidal():
    assert recommend_block_model(13) == "pyramidal"
    assert recommend_block_model(24) == "pyramidal"


def test_none_is_polarized():
    assert recommend_block_model(None) == "polarized"
