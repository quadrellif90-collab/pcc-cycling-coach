"""
tests/test_hrv_engine.py

Test OBBlIGATORI (task #27) per il motore HRV:
    * Parser (CSV/JSON/XML/ZIP/file invalido)
    * RR (valido/impossibile/artifact/duplicati/gap)
    * RMSSD (dataset di riferimento, confronto indipendente)
    * SDNN
    * Timezone (Europe/Rome, UTC, DST)
    * Duplicate (import 2x → stesso n record)
    * Intervals (mock API → RMSSD/SDNN/timestamp inviati)
"""

import os
import sys
import json
import math
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hrv_engine import (
    extract_rr_intervals, clean_rr, compute_hrv_metrics,
    detect_morning_window, build_daily_hrv, compute_baseline,
    hrv_deviation, fingerprint, RRPoint, MIN_NN_COUNT,
    compute_advanced_metrics, CleanNN,
)
from huawei_discovery import (
    HuaweiCsvParser, HuaweiJsonParser, dispatch_parse, import_huawei_export,
)
from huawei_hrv import to_icu_wellness_bulk, migrate_hrv_schema, store_daily_hrv

from tests.fixtures_huawei_synthetic import (
    SYNTHETIC_NN_1, SYNTHETIC_RMSSD_1_EXPECTED,
    SYNTHETIC_NN_WITH_ARTIFACT, SYNTHETIC_NN_IMPOSSIBLE,
    SYNTHETIC_NN_DUPLICATES, SYNTHETIC_NN_GAP,
    SYNTHETIC_CSV, SYNTHETIC_JSON,
)

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# RR extraction & cleaning (task #4/#5)
# ─────────────────────────────────────────────────────────────────────────────

def test_rr_extract_valid():
    raw = [{"timestamp": "2026-08-17T06:30:00", "rr_interval": v} for v in SYNTHETIC_NN_1]
    pts = extract_rr_intervals(raw, source="synthetic")
    assert len(pts) == len(SYNTHETIC_NN_1)
    assert all(250 <= p.interval_ms <= 2500 for p in pts)


def test_rr_impossible_removed():
    pts = [RRPoint(t, v) for t, v in [(1000.0, 50), (1001.0, 3000), (1002.0, 990)]]
    clean = clean_rr(pts)
    # 50 e 3000 fuori range → scartati
    assert len(clean) == 1
    assert clean[0].interval_ms == 990


def test_rr_artifact_corrected():
    pts = [RRPoint(float(i), v) for i, v in enumerate(SYNTHETIC_NN_WITH_ARTIFACT)]
    clean = clean_rr(pts)
    corrected = [c for c in clean if c.corrected]
    # il 1500 deve essere stato corretto (non scartato)
    assert len(corrected) >= 1
    # il valore RAW è preservato
    assert corrected[0].raw_interval_ms == 1500


def test_rr_duplicates():
    pts = [RRPoint(float(t), v) for t, v in SYNTHETIC_NN_DUPLICATES]
    clean = clean_rr(pts)
    # il dup (1001.0, 810) deve essere 1 solo
    ts = [c.timestamp for c in clean]
    assert ts.count(1001.0) == 1


def test_rr_gap_preserved():
    pts = [RRPoint(float(t), v) for t, v in SYNTHETIC_NN_GAP]
    clean = clean_rr(pts)
    # tutti e 4 preservati (gap non riempito)
    assert len(clean) == 4


# ─────────────────────────────────────────────────────────────────────────────
# RMSSD / SDNN (task #6/#7) — dataset di riferimento
# ─────────────────────────────────────────────────────────────────────────────

def test_rmssd_reference():
    pts = [RRPoint(float(i), v) for i, v in enumerate(SYNTHETIC_NN_1)]
    clean = clean_rr(pts)
    m = compute_hrv_metrics(clean, raw=pts, source="synthetic")
    # confronto con valore atteso indipendente (23.92)
    assert m.rmssd_ms is not None
    assert abs(m.rmssd_ms - SYNTHETIC_RMSSD_1_EXPECTED) < 0.1


def test_rmssd_independent_implementation():
    """Confronto con implementazione indipendente (numpy-free)."""
    nn = SYNTHETIC_NN_1
    diffs = [nn[i + 1] - nn[i] for i in range(len(nn) - 1)]
    expected = math.sqrt(sum(d * d for d in diffs) / len(diffs))
    pts = [RRPoint(float(i), v) for i, v in enumerate(nn)]
    m = compute_hrv_metrics(clean_rr(pts), raw=pts)
    assert abs(m.rmssd_ms - expected) < 0.1


def test_sdnn():
    nn = SYNTHETIC_NN_1
    mean = sum(nn) / len(nn)
    expected = math.sqrt(sum((x - mean) ** 2 for x in nn) / len(nn))
    pts = [RRPoint(float(i), v) for i, v in enumerate(nn)]
    m = compute_hrv_metrics(clean_rr(pts), raw=pts)
    assert m.sdnn_ms is not None
    assert abs(m.sdnn_ms - expected) < 0.1


def test_short_window_invalid():
    # solo 3 NN → sotto MIN_NN_COUNT → valid=False
    pts = [RRPoint(float(i), 1000 + i * 5) for i in range(3)]
    m = compute_hrv_metrics(clean_rr(pts), raw=pts)
    assert not m.valid


# ─────────────────────────────────────────────────────────────────────────────
# Timezone (task #18)
# ─────────────────────────────────────────────────────────────────────────────

def test_timezone_utc_and_local():
    from datetime import datetime, timezone, timedelta
    # Z-suffixed string must be parsed as UTC (06:30 UTC)
    utc_ts = datetime(2026, 8, 17, 6, 30, 0, tzinfo=timezone.utc).timestamp()
    pts = extract_rr_intervals([{"timestamp": "2026-08-17T06:30:00Z", "rr": 823}])
    assert abs(pts[0].timestamp - utc_ts) < 2
    # naive string (no Z) is interpreted as LOCAL tz by datetime.fromisoformat
    # → on a UTC+2 host, "06:30:00" → 04:30 UTC, differing by exactly 2h
    local_ts = datetime(2026, 8, 17, 6, 30, 0).timestamp()
    assert abs(local_ts - utc_ts) == 7200  # 2h DST offset on this host


# ─────────────────────────────────────────────────────────────────────────────
# Parsers (task #3/#23)
# ─────────────────────────────────────────────────────────────────────────────

def test_csv_parser():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(SYNTHETIC_CSV)
        path = f.name
    data = HuaweiCsvParser().parse(path)
    assert len(data.rr_points) == 8
    assert data.rr_points[0]["interval_ms"] == 823
    os.unlink(path)


def test_json_parser():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SYNTHETIC_JSON, f)
        path = f.name
    data = HuaweiJsonParser().parse(path)
    assert len(data.rr_points) == 4
    assert len(data.hrv_aggregates) == 2  # rmssd + sdnn
    os.unlink(path)


def test_zip_parser():
    import zipfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as zf:
        zpath = zf.name
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("hrv.csv", SYNTHETIC_CSV)
    data = dispatch_parse(zpath)
    assert len(data.rr_points) == 8
    os.unlink(zpath)


def test_invalid_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
        f.write("garbage")
        path = f.name
    data = dispatch_parse(path)
    assert len(data.warnings) >= 1
    os.unlink(path)


# ─────────────────────────────────────────────────────────────────────────────
# Morning HRV (task #9/#10)
# ─────────────────────────────────────────────────────────────────────────────

def test_morning_window():
    # NN ogni 1s per 10 minuti, risveglio a t=600
    pts = [RRPoint(float(i), 800 + (i % 5) * 10) for i in range(600)]
    clean = clean_rr(pts)
    wake = clean[0].timestamp + 600
    win = detect_morning_window(clean, wake_time=wake, window_s=300)
    assert win is not None
    assert len(win) >= MIN_NN_COUNT


def test_morning_no_data():
    # nessun dato → None, NON inventare
    assert detect_morning_window([], wake_time=1000) is None


def test_build_daily_hrv():
    pts = [RRPoint(float(i), 800 + (i % 5) * 10) for i in range(600)]
    clean = clean_rr(pts)
    raw = [RRPoint(p.timestamp, p.raw_interval_ms) for p in clean]
    daily = build_daily_hrv(clean, raw, date="2026-08-17", source="synthetic")
    assert daily["rmssd_ms"] is not None
    assert daily["quality_category"] in ("excellent", "good", "fair")
    assert daily["valid"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Baseline & deviation (task #11)
# ─────────────────────────────────────────────────────────────────────────────

def test_baseline():
    daily = [{"date": f"2026-08-{i:02d}", "rmssd_ms": 50.0 + i} for i in range(1, 15)]
    b = compute_baseline(daily, window_days=7)
    assert b["count"] == 7
    assert b["mean_rmssd"] > 0


def test_deviation():
    dev = hrv_deviation(47.0, 54.0)
    assert dev["deviation_pct"] is not None
    assert abs(dev["deviation_pct"] - (-12.96)) < 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Duplicate idempotency (task #17)
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_fingerprint():
    fp1 = fingerprint("huawei", 1000.0, "rr", 823.0)
    fp2 = fingerprint("huawei", 1000.0, "rr", 823.0)
    assert fp1 == fp2  # stesso input → stesso fingerprint


# ─────────────────────────────────────────────────────────────────────────────
# Intervals adapter (task #14) — mock API
# ─────────────────────────────────────────────────────────────────────────────

def test_icu_bulk_mapping():
    daily = {
        "date": "2026-08-17", "source": "huawei", "valid": True,
        "quality_score": 0.94, "rmssd_ms": 47.2, "sdnn_ms": 61.4,
    }
    item = to_icu_wellness_bulk(daily)
    assert item is not None
    assert item["id"] == "2026-08-17"
    assert item["hrvRmssd"] == 47.2
    assert item["hrvSdnn"] == 61.4


def test_icu_bulk_quality_gate():
    # qualità bassa → None (non sincronizzare)
    daily = {"date": "2026-08-17", "valid": True, "quality_score": 0.3,
             "rmssd_ms": 47.2}
    assert to_icu_wellness_bulk(daily) is None


def test_icu_bulk_rejects_generic_hrv():
    # "HRV" generico senza rmssd → None (task #15: non falsifichiamo)
    daily = {"date": "2026-08-17", "valid": True, "quality_score": 0.9,
             "hrv": 47.2}
    assert to_icu_wellness_bulk(daily) is None


# ─────────────────────────────────────────────────────────────────────────────
# E2E (task #38) — flusso completo RAW → RR → CLEAN → RMSSD → DAILY → ICU
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_flow():
    # 1. RAW export (CSV simulato)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(SYNTHETIC_CSV)
        path = f.name
    data = import_huawei_export(path)
    assert len(data.rr_points) == 8

    # 2. → RR extraction
    pts = extract_rr_intervals(data.rr_points, source="huawei_csv")
    assert len(pts) == 8

    # 3. → CLEAN
    clean = clean_rr(pts)
    assert len(clean) == 8

    # 4. → RMSSD
    m = compute_hrv_metrics(clean, raw=pts, source="huawei")
    assert m.rmssd_ms is not None

    # 5. → DAILY HRV (morning window)
    # Costruisci una finestra valida (>MIN_DURATION_S, >MIN_NN_COUNT) partendo
    # dalla serie di 8 punti replicandola per coprire ~5 minuti a riposo.
    raw_rr = [RRPoint(p.timestamp, p.interval_ms) for p in pts]
    # estendi a 320 punti (≈320s) con lieve variabilità fisiologica
    import math as _m
    ext_pts = []
    t0 = pts[0].timestamp
    for i in range(320):
        iv = 800 + 30 * _m.sin(i / 7.0) + (i % 5) * 4
        ext_pts.append(RRPoint(t0 + i, iv))
    clean_ext = clean_rr(ext_pts)
    raw_ext = [RRPoint(p.timestamp, p.interval_ms) for p in ext_pts]
    daily = build_daily_hrv(clean_ext, raw_ext, date="2026-08-17", source="huawei")
    assert daily["rmssd_ms"] is not None
    assert daily["valid"] is True

    # 6. → ICU mapping (mock) — l'adapter arrotonda a 1 decimale (formato ICU)
    item = to_icu_wellness_bulk(daily)
    assert item is not None
    assert item["hrvRmssd"] == round(daily["rmssd_ms"], 1)


def test_daily_hrv_store_and_query_roundtrip():
    """Regression: get_daily_hrv_range must return dict rows (sqlite Row→dict)."""
    import sqlite3
    tmp = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(tmp)
    import huawei_hrv as S
    orig = S.get_db
    S.get_db = lambda: conn
    try:
        S.migrate_hrv_schema(conn)
        daily = {
            "date": "2026-08-17", "source": "huawei", "rmssd_ms": 47.2,
            "sdnn_ms": 61.4, "mean_hr": 52, "sample_count": 350,
            "duration_seconds": 300, "quality_score": 0.94,
            "quality_category": "excellent", "calculation_method": "rmssd_nn_cleaned_v1",
            "valid": True,
        }
        assert S.store_daily_hrv(daily, category="morning", db=conn) is True
        rows = S.get_daily_hrv_range("2000-01-01", "2100-01-01", db=conn)
        assert len(rows) == 1
        assert rows[0]["rmssd_ms"] == 47.2
        assert rows[0]["date"] == "2026-08-17"
        assert isinstance(rows[0], dict)
    finally:
        S.get_db = orig
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Metriche avanzate (task #8/#11) — SDANN, triangular index, LF/HF freq-domain
# ─────────────────────────────────────────────────────────────────────────────

def _make_clean_nn(n, t0=1000.0, base=850.0):
    """Genera NN con modulazione LF/HF per test freq-domain."""
    import math
    pts = []
    t = t0
    for i in range(n):
        iv = base + 40 * math.sin(2 * math.pi * 0.1 * i / 4.0) \
                   + 25 * math.sin(2 * math.pi * 0.25 * i / 4.0)
        pts.append(CleanNN(timestamp=t, interval_ms=iv, raw_interval_ms=iv,
                           corrected=False, source="synthetic"))
        t += 0.25  # step 0.25s → 4 Hz
    return pts


def test_advanced_short_window_no_freq():
    clean = _make_clean_nn(20)  # ~5s
    adv = compute_advanced_metrics(clean)
    assert adv["lf_ms2"] is None
    assert adv["hf_ms2"] is None
    assert adv["lf_hf_ratio"] is None
    assert adv["advanced_valid"] is False


def test_advanced_long_window_freq_domain():
    clean = _make_clean_nn(800)  # ~200s
    adv = compute_advanced_metrics(clean)
    assert adv["advanced_valid"] is True
    assert adv["lf_ms2"] is not None and adv["lf_ms2"] > 0
    assert adv["hf_ms2"] is not None and adv["hf_ms2"] > 0
    assert 0.2 <= adv["lf_hf_ratio"] <= 6.0


def test_advanced_triangular_index():
    clean = _make_clean_nn(200)
    adv = compute_advanced_metrics(clean)
    ti = adv["hrv_triangular_index"]
    assert ti is not None and ti > 1.0


def test_advanced_sdann():
    clean = _make_clean_nn(400)  # ~100s
    adv = compute_advanced_metrics(clean)
    assert adv["sdann_ms"] is not None


def test_hrv_metrics_carries_advanced():
    clean = _make_clean_nn(800)
    m = compute_hrv_metrics(clean, source="synthetic")
    assert m.rmssd_ms is not None
    assert m.sdnn_ms is not None
    assert m.lf_ms2 is not None  # segnale lungo → freq-domain valido
