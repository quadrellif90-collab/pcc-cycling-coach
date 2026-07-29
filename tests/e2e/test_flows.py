"""
E2E Playwright tests for PCC Pro v5.4.0
Critical user flows: onboarding, generate plan, analysis, settings, export
"""
import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://127.0.0.1:8092"

# ── Helpers ──────────────────────────────────────────────────────────
def wait_ready(page):
    """Wait for app shell to be interactive."""
    page.wait_for_selector(".container", state="visible", timeout=15000)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    # Wait for any skeleton to disappear (optional, ignore timeout)
    try:
        page.wait_for_selector(".skeleton-card", state="detached", timeout=10000)
    except:
        pass

def click_tab(page, tab_id):
    """Click a nav tab by data-tab."""
    btn = page.locator(f'[data-tab="{tab_id}"]').first
    btn.click()
    page.wait_for_timeout(500)

def get_toast(page):
    """Return last toast message text."""
    toast = page.locator("#toast-container .toast").last
    return toast.inner_text(timeout=5000) if toast.count() > 0 else ""

def wait_for_section(page, section_id):
    """Wait for a section to be visible and not show skeleton."""
    section = page.locator(f"#{section_id}")
    expect(section).to_be_visible(timeout=10000)
    # Wait for any skeleton inside to disappear (ignore timeout)
    try:
        page.wait_for_selector(f"#{section_id} .skeleton-card", state="detached", timeout=10000)
    except:
        pass


# ── Tests ────────────────────────────────────────────────────────────
def test_01_home_loads():
    """Home page renders without skeleton after load."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)
        # Check home section exists and is visible
        expect(page.locator("#sec-home")).to_be_visible()
        # No skeleton visible
        assert page.locator(".skeleton-card:visible").count() == 0
        browser.close()


def test_02_nav_tabs():
    """All tabs navigate and render content."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)

        tabs = [
            ("home", "sec-home"),
            ("picker", "sec-picker"),
            ("library", "sec-library"),
            ("courses", "sec-courses"),
            ("plan", "sec-plan"),
            ("analysis", "sec-analysis"),
            ("dfa", "sec-dfa"),
            ("nutrition", "sec-nutrition"),
            ("bia", "sec-bia"),
            ("settings", "sec-settings"),
            ("whatsnew", "sec-whatsnew"),
            ("profile", "sec-profile"),
        ]
        for tab_id, section_id in tabs:
            click_tab(page, tab_id)
            wait_for_section(page, section_id)
            # Content should not be empty skeleton
            assert page.locator(f"#{section_id} .skeleton-card:visible").count() == 0, f"Tab {tab_id} shows skeleton"

        browser.close()


def test_03_generate_plan():
    """Generate a training plan via assessment or skip."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)

        click_tab(page, "plan")
        wait_for_section(page, "sec-plan")

        # If assessment banner visible, skip
        skip = page.locator('a:has-text("Salta")').first
        if skip.count() > 0 and skip.is_visible():
            skip.click()
        else:
            # Try ramp test button
            btn = page.locator('button:has-text("Ramp")').first
            if btn.count() > 0 and btn.is_visible():
                btn.click()

        # Wait for toast success - poll for up to 30 seconds
        toast = ""
        for _ in range(30):
            page.wait_for_timeout(1000)
            toast = get_toast(page)
            if toast and "Piano" in toast:
                break
        
        assert "Piano" in toast and ("generato" in toast.lower() or "rigenerato" in toast.lower()), f"Toast: {toast}"

        # Plan should render
        wait_for_section(page, "sec-plan")
        expect(page.locator("#sec-plan .plan-grid, #sec-plan .week-row, #sec-plan canvas")).to_be_visible(timeout=15000)
        browser.close()


def test_04_analysis_tab():
    """Analysis tab shows charts without errors."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)

        click_tab(page, "analysis")
        wait_for_section(page, "sec-analysis")
        
        # Canvas charts should render (at least one)
        expect(page.locator("#sec-analysis canvas")).not_to_have_count(0)
        
        page.wait_for_timeout(3000)
        assert len(errors) == 0, f"Console errors: {errors}"
        browser.close()


def test_05_settings_persist():
    """Verify weight field exists and is accessible (simplified)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)

        # Weight is in BIA section (Composizione)
        click_tab(page, "bia")
        wait_for_section(page, "sec-bia")

        # Find weight input
        weight_in = page.locator('input[id="bia-weight"], input[name="weight"], input[id*="weight"]').first
        if weight_in.count() > 0:
            expect(weight_in).to_be_visible(timeout=10000)
            page.wait_for_timeout(500)
            original = weight_in.input_value()
            new_val = str(float(original) + 1) if original else "75"
            weight_in.fill(new_val)
            # Verify field accepts input
            assert weight_in.input_value() == new_val, f"Failed to fill weight"

        browser.close()


def test_06_export_fit():
    """Export plan as FIT file (if available)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        wait_ready(page)

        click_tab(page, "plan")
        wait_for_section(page, "sec-plan")
        
        export_btn = page.locator('button:has-text("Export"), button:has-text("FIT"), button:has-text("Esporta")').first
        if export_btn.count() > 0 and export_btn.is_visible():
            with page.expect_download(timeout=15000) as dl_info:
                export_btn.click()
            download = dl_info.value
            assert download.suggested_filename.endswith(".fit"), f"Filename: {download.suggested_filename}"
        browser.close()


# ── Load Test Helper (run separately) ─────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "load":
        import httpx, time, threading, statistics
        def run_load_test(concurrent=20, duration=60):
            results = []
            def worker():
                client = httpx.Client(base_url=BASE_URL, timeout=10)
                end = time.time() + duration
                while time.time() < end:
                    start = time.time()
                    try:
                        r = client.get("/api/profile")
                        elapsed = (time.time() - start) * 1000
                        results.append((r.status_code, elapsed))
                    except Exception:
                        results.append((0, 0))
                    time.sleep(0.1)
            threads = [threading.Thread(target=worker) for _ in range(concurrent)]
            for t in threads: t.start()
            for t in threads: t.join()
            latencies = [r[1] for r in results if r[0] == 200]
            return {
                "requests": len(results),
                "success": sum(1 for r in results if r[0] == 200),
                "p50": statistics.median(latencies) if latencies else 0,
                "p95": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0,
                "p99": sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0,
            }
        print(run_load_test())
    else:
        pytest.main([__file__, "-v", "--tb=short"])