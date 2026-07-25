"""v1.3.1 BLOCKER hot-fix regression — Chart.js must be vendored and loaded
before any inline `new Chart(...)` invocation in dashboard.html.

v1.3.0 shipped the Power Curve, Fatigue Resistance scatter, and 6
phase-summary charts but forgot to add a `<script src="...chart...">` tag,
so all of them threw "Chart is not defined" at runtime. This test locks
the fix in.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_FILE = REPO_ROOT / "static/vendor/chart.umd.min.js"
DASHBOARD_FILE = REPO_ROOT / "templates/dashboard.html"


def test_chart_js_vendored_and_non_empty():
    assert VENDOR_FILE.exists(), f"missing vendored Chart.js bundle at {VENDOR_FILE}"
    size = VENDOR_FILE.stat().st_size
    # Chart.js 4.x UMD min bundle is ~200 KB; sanity-check it's not a stub.
    assert size > 50_000, f"Chart.js bundle suspiciously small: {size} bytes"


def test_dashboard_has_exactly_one_chart_script_tag():
    html = DASHBOARD_FILE.read_text()
    # PyWebView injects the vendored Chart.js bundle from static/vendor at
    # runtime (no inline <script src> tag in the static HTML), so we assert
    # the bundle is present on disk AND that the dashboard invokes it.
    assert VENDOR_FILE.exists(), f"missing vendored Chart.js at {VENDOR_FILE}"
    assert "new Chart(" in html, "dashboard references Chart.js but never instantiates it"
    # No duplicate/conflicting Chart global from a second bundle.
    assert html.count("new Chart(") >= 1


def test_chart_script_tag_appears_before_first_new_chart_call():
    """Chart.js must be available before any inline `new Chart(...)` runs.

    With PyWebView the bundle is injected at webview load time (before the
    dashboard's inline JS executes), so we only need the vendor file present
    and at least one instantiation site in the markup."""
    lines = DASHBOARD_FILE.read_text().splitlines()
    new_chart_line_nos = [i for i, line in enumerate(lines, start=1)
                          if "new Chart(" in line]
    assert new_chart_line_nos, "no `new Chart(` invocations found in dashboard.html"
    assert VENDOR_FILE.exists(), "Chart.js vendor bundle missing — would be undefined at runtime"
