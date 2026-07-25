"""Tests for the notifications layer (Fase 1 — smart notifications).

Pure-function coverage: day_status RLGL mapping, renderers return correct
channel routing, and the engine degrades gracefully when SMTP/toast are
absent (no real network / no Windows needed).
"""
import sys
from pathlib import Path

# Make the repo root importable when run from tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import notifications as N


def test_day_status_red_on_deep_fatigue():
    assert N.day_status(tsb=-30) == N.STATUS_RED
    assert N.day_status(readiness_status="POOR") == N.STATUS_RED
    assert N.day_status(hrv_band="below") == N.STATUS_RED


def test_day_status_yellow_band():
    assert N.day_status(tsb=-15) == N.STATUS_YELLOW
    assert N.day_status(hrv_band="above") == N.STATUS_YELLOW
    assert N.day_status(readiness_status="MODERATE") == N.STATUS_YELLOW


def test_day_status_green_default():
    assert N.day_status() == N.STATUS_GREEN
    assert N.day_status(tsb=10, readiness_status="GOOD", hrv_band="in_band") == N.STATUS_GREEN


def test_render_rlgl_flag_only_red():
    assert N.render_rlgl_flag(N.STATUS_GREEN, tsb=10) is None
    note = N.render_rlgl_flag(N.STATUS_RED, tsb=-28)
    assert note is not None
    assert N.CHANNEL_TOAST in note["channels"]
    assert N.CHANNEL_CALENDAR in note["channels"]


def test_render_workout_of_day_none_when_missing():
    assert N.render_workout_of_day(None) is None
    note = N.render_workout_of_day({"session_type": "vo2max", "duration_min": 60,
                                     "target_w": "320W"})
    assert note is not None
    assert N.CHANNEL_EMAIL in note["channels"]
    assert "vo2max" in note["body"].lower()


def test_render_workout_swap_only_hard_low_readiness():
    # fresh readiness + hard session -> no swap
    assert N.render_workout_swap("GOOD", {"session_type": "vo2max"}) is None
    # poor readiness + hard session -> swap suggested
    note = N.render_workout_swap("POOR", {"session_type": "threshold"})
    assert note is not None
    assert "Endurance Z2" in note["body"]
    # poor readiness + easy session -> no swap
    assert N.render_workout_swap("POOR", {"session_type": "z2"}) is None


def test_render_etftp_drift_threshold():
    assert N.render_etftp_drift(200, 201) is None          # <2%
    note = N.render_etftp_drift(200, 210)                  # +5%
    assert note is not None
    assert N.CHANNEL_EMAIL in note["channels"]


def test_render_hrv_trend_three_down_days():
    assert N.render_hrv_trend([-1, -1]) is None            # too short
    note = N.render_hrv_trend([0, -1, -2, -1])             # 3 consecutive down
    assert note is not None
    assert N.CHANNEL_EMAIL in note["channels"]


def test_render_missed_workout_always():
    note = N.render_missed_workout("2026-08-01")
    assert note["type"] == "missed_workout"
    assert "2026-08-01" in note["body"]


def test_render_fueling_reminder_only_long():
    assert N.render_fueling_reminder({"duration_min": 60}) is None
    note = N.render_fueling_reminder({"duration_min": 120})
    assert note is not None
    assert "60" in note["body"]


def test_render_monotony_alert_threshold():
    assert N.render_monotony_alert(1.5) is None
    note = N.render_monotony_alert(2.4)
    assert note is not None
    assert N.CHANNEL_EMAIL in note["channels"]


def test_engine_degrades_without_smtp_and_toast():
    """No SMTP creds, no toast lib -> dispatch must not raise, returns falsy.

    RLGL flag declares [toast, calendar] channels (no email), so dispatch
    only attempts toast here. Assert no crash + toast attempt recorded.
    """
    eng = N.NotificationEngine(N.NotificationSettings(enabled=True))
    note = N.render_rlgl_flag(N.STATUS_RED, tsb=-28)
    result = eng.dispatch(note)
    # toast attempted (lib absent on this host -> False), calendar is a view hint
    assert result.get("toast") in (False, True)   # bool, never crash
    # no email channel declared for rlgl_flag -> key absent, not an error
    assert "email" not in result


def test_engine_respects_active_types_filter():
    settings = N.NotificationSettings(enabled=True, active_types=["rlgl_flag"])
    eng = N.NotificationEngine(settings)
    # a rlgl note should be processed
    r = eng.dispatch(N.render_rlgl_flag(N.STATUS_RED, tsb=-28))
    assert "skipped" not in r
    # a morning note should be skipped (not in active_types)
    m = eng.dispatch(N.render_morning_readiness(
        {"score": 80, "status": "GOOD", "advice": "go"}, N.STATUS_GREEN))
    assert m.get("skipped") is True


def test_morning_bundle_builds_red_state():
    eng = N.NotificationEngine(N.NotificationSettings(enabled=True))
    notes = eng.morning_bundle(
        {"score": 30, "status": "POOR", "advice": "rest"},
        tsb=-30, hrv_band="below")
    types = [n["type"] for n in notes]
    assert "morning_readiness" in types
    assert "rlgl_flag" in types   # red day => flag included
