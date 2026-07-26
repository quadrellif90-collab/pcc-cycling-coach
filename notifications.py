"""Smart-notification delivery layer for PCC (Fase 1 — il focus utente: avvisi/notifiche/email).

PCC is local-first: notifications are computed from the SAME signals the
planner already derives (readiness score, TSB, HRV band, plan calendar) and
delivered through channels the user owns — desktop toast + email via the
user's own SMTP server. No PCC cloud, no third-party push service.

Design rules (single source of truth):
* This module NEVER recomputes training state. It consumes
  ``readiness.compute_readiness`` / ``continuous_policy`` outputs that the
  rest of the app already produces. Notifications are a VIEW over the engine.
* Pure functions (``day_status``, ``render_*``) take plain data and return
  plain dicts -> unit-testable without I/O.
* ``NotificationEngine`` wraps I/O (smtplib / toast) behind methods that
  degrade gracefully (missing SMTP creds -> skip email, log; no toast lib ->
  skip toast, log).

Twelve notification types (see docs/ricerca_notifiche_smart_2024-2026.md):
  1 Morning Readiness Report   7 Morning Readiness (email+toast, R/Y/G)
  2 RLGL Day Flag              TSB<-25 / HRV-1SD -> Red Day
  3 Workout of the Day         sessione, target W/zone, meteo
  4 Workout swap advisory      readiness bassa + intensa -> swap
  5 Breakthrough/PR detect     new best power curve -> toast
  6 eFTP/zone drift alert      eFTP >2% -> email aggiorna zone
  7 HRV trend warning          3+ gg calo -> email overreaching/illness
  8 Missed workout re-plan     non eseguita -> toast + ricolloca
  9 Weekly Review email        domenica: carico/compliance/HRV/focus
 10 Pre-race Form countdown     TSB proiettato + checklist taper
 11 Fueling reminder           sessione >90min -> toast 60-90 g/h
 12 Monotony/Strain alert      Foster monotony >2.0 -> email varia
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Optional

_log = logging.getLogger("domestique.notifications")

# ── Channels ────────────────────────────────────────────────────────────────
CHANNEL_TOAST = "toast"
CHANNEL_EMAIL = "email"
CHANNEL_CALENDAR = "calendar"   # colour the day in the plan calendar

# ── RLGL-style day status (reuses continuous_policy semantics) ───────────────
STATUS_RED = "red"      # rest / recovery
STATUS_YELLOW = "yellow"  # low-intensity only
STATUS_GREEN = "green"    # train as planned

TSB_RED_FLOOR = -25      # mirrors continuous_policy.TSB_LOW_FLOOR
TSB_YELLOW_FLOOR = -10   # below this (but > red) -> yellow


def day_status(tsb: Optional[float] = None,
               readiness_status: Optional[str] = None,
               hrv_band: Optional[str] = None) -> str:
    """Map today's signals to an RLGL-style day status.

    Red when deep fatigue (TSB < -25) OR HRV below band OR readiness POOR.
    Yellow when TSB in (-25, -10] OR HRV above band (stress) OR readiness MODERATE.
    Green otherwise (or when signals are missing -> assume trainable).
    """
    rs = (readiness_status or "").upper()
    if tsb is not None and tsb < TSB_RED_FLOOR:
        return STATUS_RED
    if hrv_band == "below":
        return STATUS_RED
    if rs == "POOR":
        return STATUS_RED
    if tsb is not None and tsb < TSB_YELLOW_FLOOR:
        return STATUS_YELLOW
    if hrv_band == "above":   # two-sided HRV rule: spike = stress
        return STATUS_YELLOW
    if rs == "MODERATE":
        return STATUS_YELLOW
    return STATUS_GREEN


# ── Per-notification renderers (pure: data -> message dict) ──────────────────
def render_morning_readiness(readiness: dict, day_st: str) -> dict:
    score = readiness.get("score")
    status = readiness.get("status", "UNKNOWN")
    emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(day_st, "⚪")
    body = (
        f"Readiness: {status} (score {score if score is not None else 'n/a'})\n"
        f"Today's training status: {day_st.upper()}\n"
        f"Advice: {readiness.get('advice', '')}"
    )
    return {
        "type": "morning_readiness",
        "title": f"{emoji} Morning Readiness — {day_st.upper()}",
        "body": body,
        "channels": [CHANNEL_TOAST, CHANNEL_EMAIL],
    }


def render_rlgl_flag(day_st: str, tsb: Optional[float] = None) -> Optional[dict]:
    if day_st != STATUS_RED:
        return None
    body = ("Red Day: deep fatigue detected"
            + (f" (TSB {tsb:.0f})" if tsb is not None else "")
            + ". Rest or recovery ride only — do not train hard.")
    return {
        "type": "rlgl_flag",
        "title": "🔴 Red Day — recovery",
        "body": body,
        "channels": [CHANNEL_TOAST, CHANNEL_CALENDAR],
    }


def render_workout_of_day(session: Optional[dict]) -> Optional[dict]:
    if not session:
        return None
    name = session.get("session_type", "workout")
    target = session.get("target_w") or session.get("ftp_pct") or ""
    dur = session.get("duration_min", "")
    body = f"Today: {name}"
    if target:
        body += f" — target {target}"
    if dur:
        body += f" ({dur} min)"
    return {
        "type": "workout_of_day",
        "title": "🚴 Workout of the Day",
        "body": body,
        "channels": [CHANNEL_EMAIL],
    }


def render_workout_swap(readiness_status: Optional[str],
                         session: Optional[dict]) -> Optional[dict]:
    """Advisory: low readiness + a hard planned session -> suggest swap."""
    if (readiness_status or "").upper() not in ("POOR", "MODERATE"):
        return None
    if not session:
        return None
    st = (session.get("session_type") or "").lower()
    if st not in ("vo2max", "threshold", "high_aerobic", "anaerobic", "sprint"):
        return None
    return {
        "type": "workout_swap",
        "title": "⚠️ Suggested swap",
        "body": (f"Readiness is {readiness_status}. Consider swapping "
                 f"{session.get('session_type')} -> Endurance Z2 today."),
        "channels": [CHANNEL_TOAST],
    }


def render_pr_detect(best_efforts: Optional[dict]) -> Optional[dict]:
    """Xert-style: a new best power curve entry -> celebrate."""
    if not best_efforts:
        return None
    improved = [d for d, v in best_efforts.items()
                if isinstance(v, dict) and v.get("is_new_best")]
    if not improved:
        return None
    body = "New personal best(s): " + ", ".join(improved)
    return {
        "type": "pr_detect",
        "title": "🏆 New PR!",
        "body": body,
        "channels": [CHANNEL_TOAST],
    }


def render_etftp_drift(old_etftp: Optional[float],
                       new_etftp: Optional[float]) -> Optional[dict]:
    if not old_etftp or not new_etftp or old_etftp <= 0:
        return None
    pct = (new_etftp - old_etftp) / old_etftp * 100.0
    if abs(pct) < 2.0:
        return None
    body = (f"eFTP changed {pct:+.1f}% ({old_etftp:.0f} -> {new_etftp:.0f} W). "
            f"Update your training zones?")
    return {
        "type": "etftp_drift",
        "title": "📊 eFTP / zone drift",
        "body": body,
        "channels": [CHANNEL_EMAIL],
    }


def render_hrv_trend(hrv_7d_series: Optional[list]) -> Optional[dict]:
    """3+ consecutive days below baseline -> possible overreaching/illness."""
    if not hrv_7d_series or len(hrv_7d_series) < 3:
        return None
    recent = hrv_7d_series[-3:]
    if all(v is not None and v < 0 for v in recent):  # signed deviation vs baseline
        return {
            "type": "hrv_trend",
            "title": "📉 HRV trend warning",
            "body": ("HRV down 3+ days vs baseline — possible overreaching or "
                     "illness. Consider a recovery day."),
            "channels": [CHANNEL_EMAIL],
        }
    return None


def render_missed_workout(session_date: str) -> dict:
    return {
        "type": "missed_workout",
        "title": "🔁 Missed workout",
        "body": (f"Session planned {session_date} was not completed — it has "
                 f"been auto-relocated to the next free slot."),
        "channels": [CHANNEL_TOAST, CHANNEL_CALENDAR],
    }


def render_weekly_review(summary: dict) -> dict:
    body = (
        f"Load: {summary.get('load', 'n/a')}\n"
        f"Compliance: {summary.get('compliance', 'n/a')}\n"
        f"HRV trend: {summary.get('hrv_trend', 'n/a')}\n"
        f"Next week focus: {summary.get('focus', 'n/a')}"
    )
    return {
        "type": "weekly_review",
        "title": "📅 Weekly Review",
        "body": body,
        "channels": [CHANNEL_EMAIL],
    }


def render_prerace_countdown(days_to_event: int, projected_tsb: Optional[float],
                              taper_checklist: Optional[list]) -> dict:
    body = f"Event in {days_to_event} days."
    if projected_tsb is not None:
        body += f" Projected Form (TSB): {projected_tsb:.0f}."
    if taper_checklist:
        body += "\nTaper checklist:\n- " + "\n- ".join(taper_checklist)
    return {
        "type": "prerace_countdown",
        "title": f"🏁 Event in {days_to_event}d",
        "body": body,
        "channels": [CHANNEL_EMAIL],
    }


def render_fueling_reminder(session: Optional[dict]) -> Optional[dict]:
    if not session:
        return None
    dur = session.get("duration_min") or 0
    kj = session.get("kj") or 0
    if dur < 90 and kj < 1500:
        return None
    return {
        "type": "fueling_reminder",
        "title": "🍌 Fueling reminder",
        "body": "Long/hard session tomorrow — prepare 60–90 g/h carbs.",
        "channels": [CHANNEL_TOAST],
    }


def render_monotony_alert(monotony: Optional[float]) -> Optional[dict]:
    if monotony is None or monotony < 2.0:
        return None
    return {
        "type": "monotony_alert",
        "title": "🔁 Monotony / Strain",
        "body": (f"Training monotony {monotony:.1f} (≥2.0) — vary intensity "
                 f"to reduce overuse risk (Foster 1998)."),
        "channels": [CHANNEL_EMAIL],
    }


# ── Engine (I/O) ──────────────────────────────────────────────────────────────
@dataclass
class SMTPConfig:
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    to_addr: str = ""
    use_tls: bool = True


@dataclass
class NotificationSettings:
    enabled: bool = False
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    toast_enabled: bool = True
    # which notification types are active (empty = all)
    active_types: list = field(default_factory=list)
    # local send times (24h "HH:MM")
    morning_time: str = "07:00"
    weekly_review_dow: int = 6   # Sunday


class NotificationEngine:
    """Wraps I/O for the pure renderers. Degrades gracefully."""

    def __init__(self, settings: NotificationSettings):
        self.settings = settings

    # -- toast (best-effort, Windows-friendly) --
    def send_toast(self, title: str, body: str) -> bool:
        if not self.settings.toast_enabled:
            return False
        try:
            from plyer import notification as plyer_notify  # type: ignore
            plyer_notify.notify(title=title, message=body, app_name="PCC")
            return True
        except Exception as exc:  # plyer missing / non-Windows / no D-Bus
            _log.info("toast skipped (%s): %s", type(exc).__name__, exc)
            return False

    # -- email (user-owned SMTP) --
    def send_email(self, to_addr: str, subject: str, body: str) -> bool:
        s = self.settings.smtp
        if not (s.host and s.user and s.password and s.from_addr):
            _log.info("email skipped: SMTP not configured")
            return False
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = s.from_addr
        msg["To"] = to_addr or s.to_addr
        msg.set_content(body)
        try:
            if s.use_tls:
                with smtplib.SMTP(s.host, s.port, timeout=20) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(s.user, s.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(s.host, s.port, timeout=20) as server:
                    server.login(s.user, s.password)
                    server.send_message(msg)
            return True
        except Exception as exc:
            _log.warning("email send failed: %s", exc)
            return False

    # -- dispatch one rendered notification --
    def dispatch(self, note: dict) -> dict:
        """Send ``note`` over its declared channels. Returns per-channel results."""
        results: dict[str, bool] = {}
        channels = note.get("channels", [])
        if self.settings.active_types and note.get("type") not in self.settings.active_types:
            return {"skipped": True}
        for ch in channels:
            if ch == CHANNEL_TOAST:
                results[ch] = self.send_toast(note["title"], note["body"])
            elif ch == CHANNEL_EMAIL:
                results[ch] = self.send_email(
                    self.settings.smtp.to_addr, note["title"], note["body"])
            # CHANNEL_CALENDAR is handled by the calendar view, not here
        return results

    # -- convenience: build + dispatch the morning bundle --
    def morning_bundle(self, readiness: dict, tsb: Optional[float],
                       hrv_band: Optional[str]) -> list[dict]:
        st = day_status(tsb=tsb, readiness_status=readiness.get("status"),
                        hrv_band=hrv_band)
        notes = [render_morning_readiness(readiness, st)]
        rlgl = render_rlgl_flag(st, tsb)
        if rlgl:
            notes.append(rlgl)
        return notes
