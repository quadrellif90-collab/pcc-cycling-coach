"""
huawei_api.py — Endpoint e orchestration per Huawei Health / HRV.

Espone (task #10/#25):
    POST /api/huawei/hrv         — accetta RR/NN, restituisce metriche calcolate
    POST /api/huawei/import      — importa un export (file/dir) dal disco
    GET  /api/huawei/hrv/daily   — DailyHRV range
    GET  /api/huawei/hrv/export  — export CSV/JSON
    GET  /api/huawei/hrv/debug   — debug trace SOURCE→FIELD→RAW→NORM→CALC→DEST

Compatibilità Health Sync (task #24): il campo 'hrv' generico di Health Sync
NON è automaticamente rMSSD (task #15). Se Health Sync fornisce 'rmssd'
esplicito → source preferenziale, ma conserviamo il raw.

Privacy (task #30): raw RR/NN restano LOCALI; verso Intervals vanno solo
metriche aggregate (hrvRmssd/hrvSdnn).
"""

from __future__ import annotations

import io
import json
import logging
import tempfile
import os
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional

log = logging.getLogger("pcc.huawei_api")

# Import del progetto
try:
    from hrv_engine import (
        extract_rr_intervals, clean_rr, compute_hrv_metrics,
        detect_morning_window, build_daily_hrv, compute_baseline,
        hrv_deviation, fingerprint, RRPoint,
    )
    from huawei_discovery import import_huawei_export
    from huawei_hrv import (
        migrate_hrv_schema, store_raw_records, store_rr_intervals,
        store_daily_hrv, store_baseline, to_icu_wellness_bulk,
        get_daily_hrv_range, export_csv, export_json, push_daily_hrv_to_icu,
    )
except Exception as e:  # pragma: no cover
    log.error("Import hrv module fallito: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/huawei/hrv  (task #25)
# ─────────────────────────────────────────────────────────────────────────────

def api_huawei_hrv_calculate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accetta:
        { "timestamp": "...", "rr_intervals": [812, 804, ...], "source": "..." }
    o:
        { "rr_points": [ {timestamp, interval_ms, ...}, ... ] }

    Restituisce metriche HRV calcolate localmente.
    """
    source = payload.get("source", "api")
    # normalizza input
    if "rr_intervals" in payload:
        ts0 = _parse_ts(payload.get("timestamp")) or datetime.now(timezone.utc).timestamp()
        step = payload.get("step_ms", 1000)  # default 1 battito/s
        pts = [RRPoint(ts0 + i * step / 1000.0, v, source=source)
               for i, v in enumerate(payload["rr_intervals"])]
    elif "rr_points" in payload:
        pts = extract_rr_intervals(payload["rr_points"], source=source)
    else:
        return {"error": "Serve 'rr_intervals' o 'rr_points'"}

    if len(pts) < 2:
        return {"error": "Servono almeno 2 intervalli RR"}

    clean = clean_rr(pts)
    raw = [RRPoint(p.timestamp, p.interval_ms) for p in pts]
    m = compute_hrv_metrics(clean, raw=raw, source=source)
    return {
        "rmssd_ms": m.rmssd_ms,
        "sdnn_ms": m.sdnn_ms,
        "mean_hr": m.mean_hr,
        "min_hr": m.min_hr,
        "max_hr": m.max_hr,
        "pnn50_pct": m.pnn50_pct,
        "cvnn_pct": m.cvnn_pct,
        "sample_count": m.sample_count,
        "duration_seconds": m.duration_seconds,
        "quality_score": m.quality_score,
        "quality_category": m.quality_category,
        "calculation_method": m.calculation_method,
        "valid": m.valid,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/huawei/import  (task #3/#34)
# ─────────────────────────────────────────────────────────────────────────────

def api_huawei_import(path: str, source: str = "huawei_health",
                       sync_to_icu: bool = False,
                       athlete_id: Optional[str] = None,
                       api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Importa un export Huawei dal disco, calcola DailyHRV e (opzionale) push ICU.

    Flusso (task #38):
        RAW → extract RR → clean → RMSSD → DailyHRV → store → (ICU)
    """
    migrate_hrv_schema()
    data = import_huawei_export(path, source=source)

    # RAW → RR
    pts = extract_rr_intervals(data.rr_points, source=source)
    if not pts:
        return {"ok": False, "error": "Nessun RR/NN trovato nell'export",
                "warnings": data.warnings}

    # store raw (tracciabilità)
    store_raw_records([
        {"source_file": r.get("source_file", path), "record_type": "rr",
         "timestamp_utc": r.get("timestamp"), "raw_value": r.get("interval_ms"),
         "raw_dict": r, "tz_hint": r.get("tz_hint")}
        for r in data.rr_points
    ])

    # CLEAN
    clean = clean_rr(pts)
    store_rr_intervals([
        {"source": source, "timestamp": c.timestamp,
         "raw_interval_ms": c.raw_interval_ms, "clean_interval_ms": c.interval_ms,
         "corrected": c.corrected, "session_id": c.session_id}
        for c in clean
    ])

    # Morning window + DailyHRV
    raw_rr = [RRPoint(c.timestamp, c.raw_interval_ms) for c in clean]
    win = detect_morning_window(clean)
    if not win:
        # fallback: intera serie se >= minima
        win = clean if len(clean) >= 8 else None
    if not win:
        return {"ok": False, "error": "Dati insufficienti per DailyHRV",
                "rr_count": len(clean), "warnings": data.warnings}

    d = date.fromtimestamp(win[0].timestamp).isoformat()
    daily = build_daily_hrv(win, raw_rr, date=d, source=source)
    store_daily_hrv(daily, category="morning")

    # Baseline
    existing = get_daily_hrv_range("2000-01-01", d)
    for w in (7, 14, 30):
        b = compute_baseline(existing + [daily], window_days=w)
        store_baseline(b)

    result = {
        "ok": True,
        "rr_count": len(clean),
        "daily_hrv": daily,
        "warnings": data.warnings,
    }

    # Sync ICU (task #8) — solo se valido e richiesto
    if sync_to_icu and daily.get("valid"):
        if athlete_id and api_key:
            push = push_daily_hrv_to_icu(daily, athlete_id, api_key)
            result["icu_sync"] = push
        else:
            result["icu_sync"] = {"ok": False, "error": "Credenziali ICU mancanti"}

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/huawei/hrv/daily + export (task #19)
# ─────────────────────────────────────────────────────────────────────────────

def api_huawei_daily(start: str, end: str) -> List[Dict[str, Any]]:
    migrate_hrv_schema()
    return get_daily_hrv_range(start, end)


def api_huawei_export(format: str = "csv", start: str = "2000-01-01",
                      end: str = "2100-01-01") -> bytes:
    rows = get_daily_hrv_range(start, end)
    if format == "json":
        return json.dumps(rows, indent=2, default=str).encode("utf-8")
    buf = io.StringIO()
    # usa export_csv di huawei_hrv
    tmp = os.path.join(tempfile.gettempdir(), "hrv_export_tmp.csv")
    export_csv(rows, tmp)
    with open(tmp, "r", encoding="utf-8") as f:
        data = f.read()
    os.unlink(tmp)
    return data.encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/huawei/hrv/debug  (task #21)
# ─────────────────────────────────────────────────────────────────────────────

def api_huawei_debug(path: str) -> Dict[str, Any]:
    """Trace SOURCE FILE → FIELD → RAW → NORM → CALC → DEST."""
    data = import_huawei_export(path)
    trace = []
    for r in data.rr_points[:10]:  # primo campione per file
        ts = r.get("timestamp")
        iv = r.get("interval_ms")
        clean = clean_rr(extract_rr_intervals([r], source="debug"))
        calc = compute_hrv_metrics(clean, raw=[RRPoint(ts, iv)], source="debug")
        trace.append({
            "source_file": r.get("source_file"),
            "field": "rr_interval (detected)",
            "raw_value": iv,
            "normalized_ms": iv,
            "calculated_rmssd_ms": calc.rmssd_ms,
            "destination": "huawei_rr_interval (local DB)",
        })
    return {"trace": trace, "warnings": data.warnings,
            "rr_total": len(data.rr_points)}


# ─────────────────────────────────────────────────────────────────────────────
# Health Sync compatibility (task #24)
# ─────────────────────────────────────────────────────────────────────────────

def health_sync_to_hrv(health_sync_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizza un record esportato da Health Sync.

    Health Sync mappa Huawei → Intervals con campi tipo:
        hrv / rmssd / sdnn / resting_hr / sleep / spo2 ...

    Regola (task #15/#24): se il campo è 'hrv' generico → NON è rMSSD
    automaticamente. Se è 'rmssd' esplicito → source preferenziale.
    Conserviamo sempre il raw.
    """
    out = {"raw": health_sync_record, "mapped": {}, "notes": []}
    metric = health_sync_record.get("metric", "").lower()
    value = health_sync_record.get("value")
    if metric in ("rmssd", "hrvrmssd"):
        out["mapped"]["rmssd_ms"] = value
    elif metric == "hrv":
        out["notes"].append("Campo 'hrv' generico di Health Sync: NON mappato a rMSSD senza prova")
    elif metric == "sdnn":
        out["mapped"]["sdnn_ms"] = value
    elif metric == "resting_hr":
        out["mapped"]["rhr"] = value
    return out


def _parse_ts(v: Any) -> Optional[float]:
    from hrv_engine import _to_epoch
    return _to_epoch(v) if v is not None else None


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/huawei/hrv/manual  (task #25/#31) — Scrittura manuale dati HRV
# ─────────────────────────────────────────────────────────────────────────────
def api_huawei_manual_hrv(payload: dict) -> dict:
    """
    Scrive dati manuali su Intervals.icu wellness-bulk (task #25/#31).
    
    Corpo richiesto (chi tutti opzionali tranne rmssd_ms):
    {
        "rmssd_ms": 19.1,                  # CALCOLATO localmente - OBBLIGATORIO
        "sdnn_ms": 10.3,                 # Oppure valore da Intervals
        "resting_hr": 48,                # FC a riposo in bpm
        "weight_kg": 71.4,               # Peso in kg
        "sport_info": "scalatore",       # Tipo atleta
        "notes": "RMSSD da Huawei Watch via PCC"  # Note libere
    }
    
    Regola #15/#31: Il campo 'hrv' generico NON viene mai scritto automatico.
    Solo rmssd_ms calcolato localmente da RR/NN o valore esplicito da Intervals.
    
    Restituisce:
    {
        "ok": True,
        "written_fields": ["hrvRmssd", "hrvSdnn", "restingHeartRate", ...],
        "icu_response": {"ok": True, "synced": 1}
    }
    """
    import httpx
    import json
    from hrv_engine import MIN_QUALITY_FOR_SYNC
    from datetime import datetime
    
    # Estrai campi dal body
    rmssd_ms = payload.get("rmssd_ms")
    sdnn_ms = payload.get("sdnn_ms")
    resting_hr = payload.get("resting_hr")
    weight_kg = payload.get("weight_kg")
    sport_info = payload.get("sport_info")
    notes = payload.get("notes")
    athlete_id = payload.get("athlete_id")
    api_key = payload.get("api_key")
    
    # Regola #15: rmssd_ms è obbligatorio per la sync, altrimenti fallisce
    if rmssd_ms is None:
        return {"ok": False, "error": "Serve rmssd_ms calcolato localmente"}
    
    # Quality gate
    quality = payload.get("quality_score")
    if quality is not None and quality < MIN_QUALITY_FOR_SYNC:
        return {"ok": False, "error": f"Qualità {quality} < soglia {MIN_QUALITY_FOR_SYNC}, sync impedito"}
    
    # Costruisci payload per Intervals - solo campi valorizzati
    item = {"id": datetime.utcnow().strftime("%Y-%m-%d")}
    
    if rmssd_ms is not None:
        item["hrvRmssd"] = round(rmssd_ms, 1)
    if sdnn_ms is not None:
        item["hrvSdnn"] = round(sdnn_ms, 1)
    if resting_hr is not None:
        item["restingHeartRate"] = resting_hr
    if weight_kg is not None:
        item["weight"] = weight_kg
    if sport_info is not None:
        item["sportInfo"] = sport_info
    if notes is not None:
        item["notes"] = notes
    
    # Il payload deve avere almeno hrvRmssd o hrvSdnn per essere valido
    if "hrvRmssd" not in item and "hrvSdnn" not in item:
        return {"ok": False, "error": "Nessun campo scrivibile presente"}
    
    # Costruisci URL e headers
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness-bulk" if athlete_id else ""
    
    written_fields = []
    if "hrvRmssd" in item:
        written_fields.append("hrvRmssd")
    if "hrvSdnn" in item:
        written_fields.append("hrvSdnn")
    if "restingHeartRate" in item:
        written_fields.append("restingHeartRate")
    if "weight" in item:
        written_fields.append("weight")
    if "sportInfo" in item:
        written_fields.append("sportInfo")
    if "notes" in item:
        written_fields.append("notes")
    
    if not url:
        return {"ok": True, "written_fields": written_fields, "icu_response": None, "note": "Nessun athlete_id specificato"}
    
    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Basic {api_key}"
        
        payload_data = [item] if item else []
        resp = httpx.put(url, headers=headers, json=payload_data, timeout=20)
        
        if resp.status_code in (200, 210):
            written = {}
            if "hrvRmssd" in item: written["hrvRmssd"] = round(rmssd_ms, 1)
            if "hrvSdnn" in item: written["hrvSdnn"] = round(sdnn_ms, 1) if sdnn_ms is not None else None
            if "restingHeartRate" in item: written["restingHeartRate"] = resting_hr
            if "weight" in item: written["weight"] = weight_kg
            if "sportInfo" in item: written["sportInfo"] = sport_info
            if "notes" in item: written["notes"] = notes
            
            # Aggiorna eventualmente il DB locale
            if athlete_id:
                try:
                    from huawei_hrv import get_db
                    conn = get_db()
                    conn.execute(
                        "UPDATE daily_hrv SET synced_to_icu=1 WHERE date=?",
                        (datetime.utcnow().strftime("%Y-%m-%d"),)
                    )
                    conn.commit()
                except Exception:
                    pass
            
            return {
                "ok": True,
                "written_fields": written_fields,
                "icu_response": {"ok": True, "synced": 1, "payload": written}
            }
        else:
            return {
                "ok": False, 
                "error": f"ICU {resp.status_code}: {resp.text[:200]}",
                "written_fields": written_fields
            }
    except Exception as e:
        return {"ok": False, "error": f"Network ICU: {e}", "written_fields": written_fields}


# ─────────────────────────────────────────────────────────────────────────────
# Route Flask per l'endpoint manuale
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/huawei/hrv/manual")
def api_huawei_manual_hrv_endpoint(body: dict = Body(default={})):
    """POST scrittura manuale dati HRV su Intervals.icu (task #25/#31).
    
    Vedere api_huawei_manual_hrv() per la documentazione completa del payload.
    """
    try:
        from huawei_api import api_huawei_manual_hrv
        return api_huawei_manual_hrv(body)
    except Exception as e:
        _log.exception("huawei manual hrv failed")
        return {"error": f"internal:{type(e).__name__}"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/huawei/hrv/manual  (task #25/#31) — Scrittura manuale dati HRV
# ─────────────────────────────────────────────────────────────────────────────
def api_huawei_manual_hrv(body: dict = Body(default={})) -> dict:
    """
    Scrive dati manuali su Intervals.icu wellness-bulk.
    
    Body atteso (chi tutti opzionali tranne rmssd_ms che è obbligatorio per sync):
    {
        "rmssd_ms": 19.1,                    # CALCOLATO localmente - OBBLIGATORIO per sync
        "sdnn_ms": 10.3,                 # CALCOLATO localmente o da Intervals
        "resting_hr": 48,                # MANUALE: FC a riposo in bpm
        "weight_kg": 71.4,               # MANUALE: peso in kg
        "sport_info": "scalatore",       # MANUALE: tipo atleta
        "notes": "RMSSD da Huawei Watch via PCC"  # MANUALE: note libere
    }
    
    Regola #15/#31: Il campo 'hrv' generico NON viene mai scritto automatico.
    Solo rmssd_ms calcolato localmente o valore esplicito da Intervals.
    
    Restituisce:
    {
        "ok": True,
        "written_fields": ["hrvRmssd", "hrvSdnn", "restingHeartRate", ...],
        "icu_response": {"ok": True, "synced": 1}
    }
    """
    import httpx
    from hrv_engine import MIN_QUALITY_FOR_SYNC
    
    # Estrai campi dal body
    rmssd_ms = body.get("rmssd_ms")
    sdnn_ms = body.get("sdnn_ms")
    resting_hr = body.get("resting_hr")
    weight_kg = body.get("weight_kg")
    sport_info = body.get("sport_info")
    notes = body.get("notes")
    
    # Regola #15: rmssd_ms è obbligatorio per la sync, altrimenti fallisce
    if rmssd_ms is None:
        return {"ok": False, "error": "Serve rmssd_ms calcolato localmente"}
    
    # Quality gate
    quality = body.get("quality_score")
    if quality is not None and quality < MIN_QUALITY_FOR_SYNC:
        return {"ok": False, "error": f"Qualità {quality} < soglia {MIN_QUALITY_FOR_SYNC}, sync impedito"}
    
    # Costruisci payload per Intervals - solo campi valorizzati
    item = {"id": datetime.utcnow().strftime("%Y-%m-%d")}
    
    if rmssd_ms is not None:
        item["hrvRmssd"] = round(rmssd_ms, 1)
    if sdnn_ms is not None:
        item["hrvSdnn"] = round(sdnn_ms, 1)
    if resting_hr is not None:
        item["restingHeartRate"] = resting_hr
    if weight_kg is not None:
        item["weight"] = weight_kg
    if sport_info is not None:
        item["sportInfo"] = sport_info
    if notes is not None:
        item["notes"] = notes
    
    # Il payload deve avere almeno hrvRmssd o hrvSdnn per essere valido
    if "hrvRmssd" not in item and "hrvSdnn" not in item:
        return {"ok": False, "error": "Nessun campo scrivibile presente"}
    
    # Esegui PUT su Intervals
    athlete_id = body.get("athlete_id")  # opzionale, se noto
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness-bulk" if athlete_id else ""
    
    written_fields = []
    if "hrvRmssd" in item:
        written_fields.append("hrvRmssd")
    if "hrvSdnn" in item:
        written_fields.append("hrvSdnn")
    if "restingHeartRate" in item:
        written_fields.append("restingHeartRate")
    if "weight" in item:
        written_fields.append("weight")
    if "sportInfo" in item:
        written_fields.append("sportInfo")
    if "notes" in item:
        written_fields.append("notes")
    
    if not url:
        return {"ok": True, "written_fields": written_fields, "icu_response": None, "note": "Nessun athlete_id specificato, scrittura locale solo"}
    
    try:
        headers = {}
        if body.get("api_key"):
            headers["Authorization"] = f"Basic {body['api_key']}"
        
        payload = [item] if item else []
        resp = httpx.put(url, headers=headers, json=payload, timeout=20)
        
        if resp.status_code in (200, 210):
            written = {}
            if "hrvRmssd" in item: written["hrvRmssd"] = round(rmssd_ms, 1)
            if "hrvSdnn" in item: written["hrvSdnn"] = round(sdnn_ms, 1) if sdnn_ms is not None else None
            if "restingHeartRate" in item: written["restingHeartRate"] = resting_hr
            if "weight" in item: written["weight"] = weight_kg
            if "sportInfo" in item: written["sportInfo"] = sport_info
            if "notes" in item: written["notes"] = notes
            
            return {
                "ok": True,
                "written_fields": written_fields,
                "icu_response": {"ok": True, "synced": 1, "payload": written}
            }
        else:
            return {
                "ok": False, 
                "error": f"ICU {resp.status_code}: {resp.text[:200]}",
                "written_fields": written_fields
            }
    except Exception as e:
        return {"ok": False, "error": f"Network ICU: {e}", "written_fields": written_fields}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/huawei/hrv/summary  (task #10/#11) — baselines + deviazione + trend
# ─────────────────────────────────────────────────────────────────────────────
def api_huawei_summary(end: str = "2100-01-01") -> Dict[str, Any]:
    """Riepilogo HRV per la UI: ultimo valore + baseline 7/14/30 + deviazione + trend."""
    from hrv_engine import compute_baseline, hrv_deviation, rolling_average
    migrate_hrv_schema()
    rows = get_daily_hrv_range("2000-01-01", end)
    if not rows:
        return {"ok": True, "has_data": False,
                "message": "Nessun dato HRV. Importa un export Huawei."}
    # ordina per data
    rows_sorted = sorted(rows, key=lambda r: r.get("date", ""))
    latest = rows_sorted[-1]
    today_rmssd = latest.get("rmssd_ms")
    baselines = {}
    for w in (7, 14, 30):
        b = compute_baseline(rows_sorted, window_days=w)
        baselines[f"{w}d"] = {
            "mean_rmssd": b.get("mean_rmssd"),
            "median_rmssd": b.get("median_rmssd"),
            "std_rmssd": b.get("std_rmssd"),
            "cv_pct": b.get("cv_pct"),
            "count": b.get("count"),
        }
    # deviazione vs baseline 7d e 30d
    dev = {}
    if today_rmssd is not None:
        if baselines["7d"]["mean_rmssd"]:
            dev["vs_7d"] = hrv_deviation(today_rmssd, baselines["7d"]["mean_rmssd"])
        if baselines["30d"]["mean_rmssd"]:
            dev["vs_30d"] = hrv_deviation(today_rmssd, baselines["30d"]["mean_rmssd"])
    # trend rolling 7d
    trend = rolling_average(rows_sorted, days=7)
    return {
        "ok": True,
        "has_data": True,
        "latest": {
            "date": latest.get("date"),
            "rmssd_ms": today_rmssd,
            "sdnn_ms": latest.get("sdnn_ms"),
            "mean_hr": latest.get("mean_hr"),
            "sample_count": latest.get("sample_count"),
            "duration_seconds": latest.get("duration_seconds"),
            "quality_score": latest.get("quality_score"),
            "quality_category": latest.get("quality_category"),
            "source": latest.get("source"),
            "calculation_method": latest.get("calculation_method"),
        },
        "baselines": baselines,
        "deviation": dev,
        "trend_7d": trend[-14:] if trend else [],
        "total_days": len(rows_sorted),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/huawei/hrv/summary  (task #10/#11) — baselines + deviazione + trend
# ─────────────────────────────────────────────────────────────────────────────

def api_huawei_summary(end: str = "2100-01-01") -> Dict[str, Any]:
    """Riepilogo HRV per la UI: ultimo DailyHRV + baseline 7/14/30 + deviazione + trend."""
    from hrv_engine import compute_baseline, hrv_deviation, rolling_average
    migrate_hrv_schema()
    rows = get_daily_hrv_range("2000-01-01", end)
    if not rows:
        return {"ok": True, "has_data": False,
                "message": "Nessun dato HRV. Importa un export Huawei."}
    # ordina per data
    rows_sorted = sorted(rows, key=lambda r: r.get("date", ""))
    latest = rows_sorted[-1]
    today_rmssd = latest.get("rmssd_ms")
    baselines = {}
    for w in (7, 14, 30):
        b = compute_baseline(rows_sorted, window_days=w)
        baselines[f"{w}d"] = {
            "mean_rmssd": b.get("mean_rmssd"),
            "median_rmssd": b.get("median_rmssd"),
            "std_rmssd": b.get("std_rmssd"),
            "cv_pct": b.get("cv_pct"),
            "count": b.get("count"),
        }
    # deviazione vs baseline 7d e 30d
    dev = {}
    if today_rmssd is not None:
        if baselines["7d"]["mean_rmssd"]:
            dev["vs_7d"] = hrv_deviation(today_rmssd, baselines["7d"]["mean_rmssd"])
        if baselines["30d"]["mean_rmssd"]:
            dev["vs_30d"] = hrv_deviation(today_rmssd, baselines["30d"]["mean_rmssd"])
    # trend rolling 7d
    trend = rolling_average(rows_sorted, days=7)
    return {
        "ok": True,
        "has_data": True,
        "latest": {
            "date": latest.get("date"),
            "rmssd_ms": today_rmssd,
            "sdnn_ms": latest.get("sdnn_ms"),
            "mean_hr": latest.get("mean_hr"),
            "sample_count": latest.get("sample_count"),
            "duration_seconds": latest.get("duration_seconds"),
            "quality_score": latest.get("quality_score"),
            "quality_category": latest.get("quality_category"),
            "source": latest.get("source"),
            "calculation_method": latest.get("calculation_method"),
        },
        "baselines": baselines,
        "deviation": dev,
        "trend_7d": trend[-14:] if trend else [],
        "total_days": len(rows_sorted),
    }
