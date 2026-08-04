# -*- coding: utf-8 -*-
"""PCC — Terra API integration (Huawei Health / wearables).

Bridge between a Terra (tryterra.co) developer app and PCC's local DB.

Flow
----
1. User clicks "Collega Huawei Health" → we build the Terra authenticate URL
   (``/api/terra/auth-url``) with a random ``reference_id`` kept in memory.
2. Terra redirects to Huawei's consent page; on success Terra bounces back to
   ``/oauth/terra/callback?user_id=...&reference_id=...``.
3. We exchange the user_id for an access token (``/auth/getAccessToken``) and
   persist ``TERRA_USER_ID`` / ``TERRA_ACCESS_TOKEN`` / ``TERRA_EXPIRES_AT`` in
   the active profile's ``.env`` (same pattern as ICU OAuth tokens).
4. ``/api/terra/sync`` pulls the last N days of activity/sleep/body via the
   Terra v2 REST API and upserts into PCC's ``wellness`` table
   (hrv, rhr, sleep_secs, sleep_score) and ``activities`` (rides/workouts).

Credentials: global app creds (TERRA_CLIENT_ID/SECRET/API_KEY) come from
``.oauth.env`` (see config.py); per-user tokens live in the profile .env.

Notes
-----
- Huawei Health data via Terra: heart rate, HRV (rmssd), sleep, stress, SpO2,
  steps, calories, GPS workouts. NO cycling power (the watch has no power
  meter) — this feeds wellness/readiness, not TSS/power analytics.
- Terra is a paid third-party API: you need a developer app on tryterra.co
  and the user must have an account on Huawei Health with cloud sync on.
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import date, datetime, timedelta
from typing import Optional

log = logging.getLogger("pcc.terra")

# In-memory CSRF-like store for in-flight auth flows: reference_id → metadata.
# Single-use, 10-minute TTL — mirrors the ICU OAuth state store.
_TERRA_FLOWS: dict = {}

_TERRA_TTL = 600  # seconds


def _prune_flows(now: float | None = None) -> None:
    now = now or time.time()
    for rid in [k for k, v in _TERRA_FLOWS.items() if now - v.get("ts", 0) > _TERRA_TTL]:
        _TERRA_FLOWS.pop(rid, None)


# ── Config / connectivity ──────────────────────────────────────────────────────

def is_configured() -> bool:
    """True when the global Terra app credentials are present."""
    import config
    return bool(config.TERRA_CLIENT_ID and config.TERRA_CLIENT_SECRET)


def get_connected(profile_env: dict) -> bool:
    """True when the active profile has a Terra user bound."""
    return bool((profile_env or {}).get("TERRA_USER_ID"))


def _headers(profile_env: dict) -> dict:
    """Build the Terra API headers from global creds + profile token."""
    import config
    return {
        "x-api-key": config.TERRA_API_KEY,
        "dev-id": config.TERRA_CLIENT_ID,
        "Authorization": "Bearer " + (profile_env.get("TERRA_ACCESS_TOKEN") or ""),
    }


# ── Auth flow ─────────────────────────────────────────────────────────────────

def build_auth_url(return_to: str = "/") -> str:
    """Build the Terra authenticate URL for Huawei Health.

    Terra uses ``reference_id`` as the correlation id (like OAuth state).
    We store it in memory so the callback can verify it came from us.
    """
    import urllib.parse
    import config
    _prune_flows()
    reference_id = "pcc_" + secrets.token_hex(8)
    _TERRA_FLOWS[reference_id] = {"ts": time.time(), "return_to": return_to}
    params = urllib.parse.urlencode({
        "resource": "HUAWEI",
        "reference_id": reference_id,
        "auth_success_redirect_url": config.TERRA_REDIRECT_URI,
        "auth_failure_redirect_url": config.TERRA_REDIRECT_URI,
    })
    return f"{config.TERRA_AUTH_URL}?{params}"


def handle_callback(user_id: str = "", reference_id: str = "") -> tuple[bool, str, str]:
    """Verify a Terra callback and exchange user_id for an access token.

    Returns (ok, return_to, error_reason).
    """
    import config
    _prune_flows()
    flow = _TERRA_FLOWS.pop(reference_id, None)
    if not flow:
        return False, "/", "state"  # unknown / expired reference_id
    if not user_id:
        return False, flow.get("return_to") or "/", "denied"
    if not is_configured():
        return False, flow.get("return_to") or "/", "not_configured"
    try:
        import httpx
        resp = httpx.post(
            config.TERRA_TOKEN_URL,
            json={
                "client_id": config.TERRA_CLIENT_ID,
                "client_secret": config.TERRA_CLIENT_SECRET,
                "user_id": user_id,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning("EVENT=terra_token_exchange status=%s body=%s",
                        resp.status_code, (resp.text or "")[:200])
            return False, flow.get("return_to") or "/", "exchange"
        tok = resp.json()
        access_token = tok.get("access_token")
        if not access_token:
            return False, flow.get("return_to") or "/", "exchange"
        expires_in = tok.get("expires_in") or 3600
        _persist_tokens(user_id, access_token, expires_in)
        return True, flow.get("return_to") or "/", ""
    except Exception as e:  # network / parse
        log.exception("EVENT=terra_token_exchange_error")
        return False, flow.get("return_to") or "/", f"network:{type(e).__name__}"


def _persist_tokens(user_id: str, access_token: str, expires_in: float) -> None:
    """Write the Terra tokens into the active profile's .env."""
    from profile_manager import ProfileManager
    pm = ProfileManager.get()
    pm._env["TERRA_USER_ID"] = user_id
    pm._env["TERRA_ACCESS_TOKEN"] = access_token
    pm._env["TERRA_EXPIRES_AT"] = str(int(time.time()) + int(expires_in))
    pm._persist_env()


def disconnect(profile_env: dict) -> None:
    """Remove Terra tokens from the active profile."""
    from profile_manager import ProfileManager
    pm = ProfileManager.get()
    for k in ("TERRA_USER_ID", "TERRA_ACCESS_TOKEN", "TERRA_EXPIRES_AT"):
        pm._env.pop(k, None)
    pm._persist_env()


# ── Pull (v2 REST API) ────────────────────────────────────────────────────────

def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _get(profile_env: dict, path: str, params: dict) -> dict:
    import config
    import httpx
    url = f"{config.TERRA_BASE}{path}"
    resp = httpx.get(url, params=params, headers=_headers(profile_env), timeout=30)
    resp.raise_for_status()
    return resp.json()


def pull_sleep(profile_env: dict, days: int = 14) -> list[dict]:
    """Fetch sleep records for the last ``days`` days. Returns raw data rows."""
    end = date.today()
    start = end - timedelta(days=days)
    try:
        data = _get(profile_env, "/v2/sleep", {
            "user_id": profile_env.get("TERRA_USER_ID", ""),
            "start_date": _fmt(start),
            "end_date": _fmt(end),
        })
    except Exception as e:
        log.warning("EVENT=terra_pull_sleep error=%s", type(e).__name__)
        return []
    rows = data.get("data") or []
    return rows if isinstance(rows, list) else []


def pull_body(profile_env: dict, days: int = 30) -> list[dict]:
    """Fetch body metrics (weight, BMI, body fat) for the last ``days`` days."""
    end = date.today()
    start = end - timedelta(days=days)
    try:
        data = _get(profile_env, "/v2/body", {
            "user_id": profile_env.get("TERRA_USER_ID", ""),
            "start_date": _fmt(start),
            "end_date": _fmt(end),
        })
    except Exception as e:
        log.warning("EVENT=terra_pull_body error=%s", type(e).__name__)
        return []
    rows = data.get("data") or []
    return rows if isinstance(rows, list) else []


def pull_activity(profile_env: dict, days: int = 14) -> list[dict]:
    """Fetch workouts/activity for the last ``days`` days."""
    end = date.today()
    start = end - timedelta(days=days)
    try:
        data = _get(profile_env, "/v2/activity", {
            "user_id": profile_env.get("TERRA_USER_ID", ""),
            "start_date": _fmt(start),
            "end_date": _fmt(end),
        })
    except Exception as e:
        log.warning("EVENT=terra_pull_activity error=%s", type(e).__name__)
        return []
    rows = data.get("data") or []
    return rows if isinstance(rows, list) else []


# ── Mapping into PCC DB ───────────────────────────────────────────────────────

def _day_of(iso: str) -> str:
    """'2026-08-04T00:00:00Z' → '2026-08-04' (defensive)."""
    if not iso:
        return date.today().strftime("%Y-%m-%d")
    return iso[:10]


def sync_wellness(profile_env: dict, days: int = 14) -> dict:
    """Pull sleep/body and upsert into the wellness table.

    Returns {"sleep": n, "body": n, "skipped": n}.
    """
    import db
    conn = db.get_db()
    n_sleep = n_body = n_skip = 0

    for row in pull_sleep(profile_env, days):
        d = _day_of(row.get("start_time") or row.get("end_time"))
        if not d:
            n_skip += 1
            continue
        # sleep_durations / sleep_scores shapes vary by provider; read defensively.
        durations = row.get("sleep_durations") or {}
        asleep = (durations.get("asleep") or {}).get("seconds")
        scores = row.get("sleep_scores") or {}
        score = scores.get("overall")
        hrv = row.get("hrv")
        rhr = row.get("resting_heart_rate") or row.get("rhr")
        if isinstance(hrv, dict):
            hrv = hrv.get("rmssd")
        try:
            sleep_secs = int(float(asleep)) if asleep is not None else None
        except (TypeError, ValueError):
            sleep_secs = None
        try:
            sleep_score = int(float(score)) if score is not None else None
        except (TypeError, ValueError):
            sleep_score = None
        try:
            hrv_f = float(hrv) if hrv is not None else None
        except (TypeError, ValueError):
            hrv_f = None
        try:
            rhr_i = int(float(rhr)) if rhr is not None else None
        except (TypeError, ValueError):
            rhr_i = None
        _upsert_wellness(conn, d, hrv=hrv_f, rhr=rhr_i,
                         sleep_secs=sleep_secs, sleep_score=sleep_score,
                         raw=row)
        n_sleep += 1

    for row in pull_body(profile_env, days):
        d = _day_of(row.get("date") or row.get("created_at") or "")
        if not d:
            n_skip += 1
            continue
        # body payload: {"weight_data": {"weight_kg": ...}, "body_fat": ...}
        weight_data = row.get("weight_data") or {}
        w = weight_data.get("weight_kg")
        try:
            w_f = float(w) if w is not None else None
        except (TypeError, ValueError):
            w_f = None
        if w_f is not None:
            from profile_manager import ProfileManager
            pm = ProfileManager.get()
            try:
                pm.save_athlete({"weight_kg": w_f})
            except Exception:
                log.warning("EVENT=terra_weight_update_failed", exc_info=True)
        n_body += 1

    conn.commit()
    _invalidate_readiness_cache()
    return {"sleep": n_sleep, "body": n_body, "skipped": n_skip}


def sync_activities(profile_env: dict, days: int = 14) -> dict:
    """Pull workouts and upsert into the activities table (best-effort).

    Returns {"activities": n, "skipped": n}.
    """
    import db
    conn = db.get_db()
    n_act = n_skip = 0
    for row in pull_activity(profile_env, days):
        d = _day_of(row.get("start_time") or row.get("end_time"))
        if not d:
            n_skip += 1
            continue
        rid = row.get("id")
        if not rid:
            n_skip += 1
            continue
        meta = row.get("metadata") or {}
        sport = meta.get("sport") or row.get("sport") or "workout"
        duration = row.get("duration")  # Terra v2 uses seconds in `duration`
        try:
            dur = int(float(duration)) if duration is not None else None
        except (TypeError, ValueError):
            dur = None
        dist_m = row.get("distance_metres")
        try:
            dist_km = round(float(dist_m) / 1000.0, 2) if dist_m is not None else None
        except (TypeError, ValueError):
            dist_km = None
        hr = row.get("heart_rate") or {}
        avg_hr = hr.get("avg_bpm")
        max_hr = hr.get("max_bpm")
        cal = row.get("calories")
        try:
            cal_f = float(cal) if cal is not None else None
        except (TypeError, ValueError):
            cal_f = None
        # Upsert into activities (id = "terra_" + terra id to avoid collisions)
        aid = f"terra_{rid}"
        existing = conn.execute(
            "SELECT id FROM activities WHERE id = ?", (aid,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE activities SET date=?, sport=?, duration_sec=?, "
                "avg_hr=?, distance_km=?, calories=?, raw_json=? WHERE id=?",
                (d, sport, dur, avg_hr, dist_km, cal_f,
                 __import__("json").dumps(row), aid))
        else:
            conn.execute(
                "INSERT INTO activities (id, date, name, sport, duration_sec, "
                "avg_hr, distance_km, calories, raw_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, d, sport, sport, dur, avg_hr, dist_km, cal_f,
                 __import__("json").dumps(row)))
        n_act += 1
    conn.commit()
    _invalidate_readiness_cache()
    return {"activities": n_act, "skipped": n_skip}


def _upsert_wellness(conn, d: str, hrv=None, rhr=None,
                     sleep_secs=None, sleep_score=None, raw=None) -> None:
    existing = conn.execute("SELECT date FROM wellness WHERE date = ?", (d,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE wellness SET hrv = COALESCE(?, hrv), "
            "rhr = COALESCE(?, rhr), sleep_secs = COALESCE(?, sleep_secs), "
            "sleep_score = COALESCE(?, sleep_score) WHERE date = ?",
            (hrv, rhr, sleep_secs, sleep_score, d))
    else:
        conn.execute(
            "INSERT INTO wellness (date, ctl, atl, hrv, rhr, sleep_secs, "
            "sleep_score, eftp, raw_json) VALUES (?, NULL, NULL, ?, ?, ?, ?, NULL, ?)",
            (d, hrv, rhr, sleep_secs, sleep_score,
             __import__("json").dumps(raw or {})))


def _invalidate_readiness_cache() -> None:
    """Invalidate composite-readiness caches (same pattern as HRV import)."""
    try:
        import app as _app
        for k in list(_app._cache.keys()):
            if k.startswith("readiness_composite_"):
                _app._cache.pop(k, None)
                _app._cache_ts.pop(k, None)
    except Exception:
        pass
