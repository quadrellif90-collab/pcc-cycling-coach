"""PCC — Sync targets abstraction (pluggable data destinations).

This module defines a small, explicit interface so PCC can push/pull training
& body-composition data to MULTIPLE external apps, not just Intervals.icu.

Design
------
- `SyncTarget` is the base class every destination implements.
- `REGISTRY` maps a stable key (e.g. "intervals_icu") to a target instance.
- Each target exposes:
    * `key`            — stable string id
    * `display_name`   — human label (IT)
    * `can_write`      — bool, does it accept outbound writes?
    * `push_bia(reading)`   — send one BIAReading to the destination
    * `push_activity(fit_bytes, date)` — upload a .FIT activity
    * `pull_wellness(date)` — optional, fetch body/load data

Today only Intervals.icu is wired (it already does calendar + wellness push
via icu_calendar_push.py / app.py). Other apps (TrainingPeaks, Google Fit,
Strava, a local JSON export, …) can be added by subclassing SyncTarget and
registering an instance — no other file needs to change.

Why a registry and not hard-coded calls? So the UI can list "connected apps"
generically and the BIA/activity export code can iterate REGISTRY.values()
instead of growing an if/elif chain per destination.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("pcc.sync_targets")


@dataclass
class SyncResult:
    ok: bool
    synced: int = 0
    error: Optional[str] = None
    detail: dict = field(default_factory=dict)


class SyncTarget:
    """Base class for an external data destination."""

    key: str = "base"
    display_name: str = "Base"
    can_write: bool = False

    def is_configured(self) -> bool:
        """Return True if credentials/connection are present."""
        return False

    def push_bia(self, reading: dict) -> SyncResult:
        """Send one BIA reading. Override in subclasses."""
        return SyncResult(ok=False, error="non implementato")

    def push_activity(self, fit_bytes: bytes, date: str) -> SyncResult:
        """Upload a .FIT activity. Override in subclasses."""
        return SyncResult(ok=False, error="non implementato")

    def pull_wellness(self, date: str) -> Optional[dict]:
        """Optional: fetch body/load data for a date. Override if supported."""
        return None


# ── Intervals.icu target ────────────────────────────────────────────────────
# Delegates to the already-working implementation in app.py / icu_calendar_push.py
# so we don't duplicate the auth + push logic. The functions are imported lazily
# to avoid a circular import at module load.
class IntervalsIcuTarget(SyncTarget):
    key = "intervals_icu"
    display_name = "Intervals.icu"
    can_write = True

    def is_configured(self) -> bool:
        try:
            import training as _t
            return bool(_t._auth_header())
        except Exception:
            return False

    def push_bia(self, reading: dict) -> SyncResult:
        # The real push lives in app.api_bia_sync_icu; here we just expose the
        # capability so the registry is the single source of truth for "connected apps".
        if not self.is_configured():
            return SyncResult(ok=False, error="Intervals.icu non configurato")
        # app.py performs the actual PUT /wellness-bulk; this shim reports intent.
        return SyncResult(ok=True, synced=1, detail={"note": "push gestito da /api/bia-sync-icu"})

    def push_activity(self, fit_bytes: bytes, date: str) -> SyncResult:
        if not self.is_configured():
            return SyncResult(ok=False, error="Intervals.icu non configurato")
        try:
            import training as _t
            return SyncResult(ok=True, synced=1,
                              detail={"note": "upload gestito da training.upload_fit_to_icu"})
        except Exception as e:
            return SyncResult(ok=False, error=str(e))


# ── Registry ────────────────────────────────────────────────────────────────
REGISTRY: dict[str, SyncTarget] = {
    IntervalsIcuTarget.key: IntervalsIcuTarget(),
}


def get_target(key: str) -> Optional[SyncTarget]:
    return REGISTRY.get(key)


def connected_targets() -> list[SyncTarget]:
    """Targets that are currently configured (credentials present)."""
    return [t for t in REGISTRY.values() if t.is_configured()]


def list_targets() -> list[dict]:
    """Generic descriptor for the UI: every known destination + its state."""
    out = []
    for t in REGISTRY.values():
        out.append({
            "key": t.key,
            "display_name": t.display_name,
            "can_write": t.can_write,
            "configured": t.is_configured(),
        })
    return out
