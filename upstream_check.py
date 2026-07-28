"""Upstream (Domestique) version checker — PCC Pro.

Checks the latest release of `platypus45/domestique` via GitHub API and
compares it to the base version PCC was forked from (UPSTREAM_BASE).

License: both PCC and Domestique are Apache-2.0, so merge is always legal.
This module only INFORMS and CLASSIFIES risk — it never auto-merges.

Usage:
    from upstream_check import check_upstream
    result = check_upstream()  # synchronous, network call
    # result = {
    #   "upstream_tag": "v3.7.0",
    #   "upstream_title": "Which blocks did you actually do...",
    #   "base_version": "v3.5.2",
    #   "has_update": True,
    #   "risk": "safe" | "review" | "big_rewrite",
    #   "summary": "3 fix in planner, 0 riscritture",
    # }
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

UPSTREAM_REPO = "platypus45/domestique"
GITHUB_API = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
_BASE_FILE = Path(__file__).resolve().parent / "UPSTREAM_BASE"

# Keywords that signal a high-risk upstream change (planner rewrite, major refactor)
_HIGH_RISK_TAGS = [
    "rewrite", "refactor", "redesign", "redone", "from scratch",
    "replaced", "migration", "breaking", "remove",
]
# Files/directories that are safe to cherry-pick (not touching our extensions)
_SAFE_DIRS = [
    "templates/", "static/", "workouts/", "tests/", "scripts/",
    "docs/", "CHANGELOG", "README", "VERSION",
]


def _load_base_version() -> str:
    """Read the upstream version PCC was forked from."""
    try:
        return _BASE_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "v0.0.0"


def _fetch_latest_release() -> dict[str, Any] | None:
    """Fetch latest release data from GitHub API. Returns None on error."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            GITHUB_API,
            headers={"User-Agent": "PCC-Pro/5.3.5", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        log.warning("upstream check failed: %s", exc)
        return None


def _classify_risk(
    release_body: str,
    changelog_excerpt: str | None,
) -> str:
    """Classify upstream change risk: 'safe', 'review', or 'big_rewrite'.

    - 'safe': only touch UI, scripts, workouts, docs — no planner/core logic.
    - 'review': planner changes but incremental (backportable).
    - 'big_rewrite': training_planner.py rewritten from scratch or core engine changed.
    """
    body_lower = (release_body or "").lower()
    # Check for high-risk signals in the full release body
    for tag in _HIGH_RISK_TAGS:
        if tag in body_lower:
            # False positive for "removed" if talking about small removal
            if tag == "remove" and "removed" in body_lower:
                # Check context — if entire files removed vs a feature removed
                if "file" in body_lower or "workout" in body_lower:
                    continue  # safe — workout/library removals
            return "big_rewrite"

    if changelog_excerpt:
        excerpt_lower = changelog_excerpt.lower()
        for tag in _HIGH_RISK_TAGS:
            if tag in excerpt_lower:
                return "big_rewrite"
        # Incremental planner changes are "review" level
        if "training_planner" in excerpt_lower or "planner" in excerpt_lower:
            # Unless it's just test additions
            if "test" in excerpt_lower and "rewrite" not in excerpt_lower:
                pass  # might still be review
            return "review"

    return "safe"


def _format_release_date(iso_str: str | None) -> str:
    """Format ISO date string to readable format."""
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso_str[:10]


def _parse_fixes_summary(body: str) -> list[str]:
    """Extract bullet-point fixes/features from release body (Markdown)."""
    items: list[str] = []
    for line in body.splitlines():
        line = line.strip().lstrip("*-+ ")
        if line.startswith("#") or not line:
            continue
        if len(line) > 12 and len(line) < 200:
            items.append(line)
    return items[:8]  # cap at 8 items


def check_upstream() -> dict[str, Any]:
    """Check upstream Domestique for new releases.

    Returns dict with keys:
        upstream_tag, upstream_title, upstream_body, upstream_date,
        base_version, has_update, risk, summary, summary_items
    """
    base = _load_base_version()
    data = _fetch_latest_release()

    if data is None:
        return {
            "upstream_tag": None,
            "upstream_title": None,
            "upstream_body": None,
            "upstream_date": None,
            "base_version": base,
            "has_update": False,
            "risk": "unknown",
            "summary": "Rete non disponibile o errore API GitHub",
            "summary_items": [],
        }

    tag = data.get("tag_name", "")
    title = data.get("name", "")
    body = data.get("body", "")
    pub_date = data.get("published_at", "")

    # Compare versions
    has_update = tag > base if tag else False

    # Classify risk
    risk = _classify_risk(body, body[:500])

    # Build summary items
    items = _parse_fixes_summary(body)
    if risk == "safe":
        summary = f"{tag} — modifiche UI/script/docs, backportabile"
    elif risk == "review":
        summary = f"{tag} — modifiche al planner, da revisionare singolarmente"
    elif risk == "big_rewrite":
        summary = f"{tag} — riscrittura rilevante, valutare con attenzione"
    else:
        summary = f"{tag} — verifica manuale necessaria"

    return {
        "upstream_tag": tag,
        "upstream_title": title,
        "upstream_body": body[:2000],  # cap for UI display
        "upstream_date": _format_release_date(pub_date),
        "base_version": base,
        "has_update": has_update,
        "risk": risk,
        "summary": summary,
        "summary_items": items,
        "error": None,
    }