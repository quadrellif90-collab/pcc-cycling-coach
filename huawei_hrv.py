"""
huawei_hrv.py — Storage locale + adapter Intervals.icu per i dati Huawei HRV.

DB (task #16, migrazioni additive — NON rompe il DB esistente):
    huawei_raw_record    — ogni record grezzo da export (tracciabilità)
    huawei_rr_interval   — serie temporale RR/NN (RAW e CLEAN separati)
    hrv_measurement      — ogni metrica calcolata (rmssd, sdnn, pnn50, ...)
    daily_hrv            — HRV giornaliera (morning/overnight/spot)
    hrv_baseline         — baseline 7/14/30gg

Intervalli (task #14/#8): adapter `IntervalsIcuHrvTarget` che pusha
    hrvRmssd / hrvSdnn via wellness-bulk (campi ufficiali Intervals).
    Se Intervals NON accetta una metrica → resta LOCAL ONLY (task #17/#30).

Pattern riusati:
    * db.py già espone get_db() + _maybe_add_column() per migrazioni sicure.
    * sync_targets.SyncTarget è la base per gli adapter (estendiamo qui).
    * bia_parser.to_icu_wellness() è il modello di mappatura wellness→ICU.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

log = logging.getLogger("pcc.huawei_hrv")

# Import del modello DB esistente del progetto
try:
    from db import get_db, _maybe_add_column
except Exception:  # pragma: no cover
    get_db = None
    _maybe_add_column = None


# ─────────────────────────────────────────────────────────────────────────────
# Schema / migrazioni (task #16)
# ─────────────────────────────────────────────────────────────────────────────

MIGRATION_SQL = """
CREATE TABLE IF NOT EXISTS huawei_raw_record (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file   TEXT,
    record_type   TEXT,
    timestamp_utc REAL,
    raw_value     REAL,
    raw_json      TEXT,
    tz_hint       TEXT,
    fingerprint   TEXT UNIQUE,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS huawei_rr_interval (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source         TEXT,
    timestamp_utc  REAL,
    raw_interval_ms REAL,
    clean_interval_ms REAL,
    corrected      INTEGER DEFAULT 0,
    session_id    TEXT,
    fingerprint    TEXT UNIQUE,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hrv_measurement (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source             TEXT,
    metric             TEXT,        -- rmssd_ms, sdnn_ms, pnn50_pct, ...
    value              REAL,
    unit               TEXT,
    timestamp_utc      REAL,
    window_start       REAL,
    window_end         REAL,
    duration_seconds   REAL,
    sample_count       INTEGER,
    quality_score      REAL,
    quality_category   TEXT,
    calculation_method TEXT,
    algorithm          TEXT,
    synced_to_icu      INTEGER DEFAULT 0,
    created_at         TEXT DEFAULT (datetime('now')),
    UNIQUE(source, metric, timestamp_utc)
);

CREATE TABLE IF NOT EXISTS daily_hrv (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date               TEXT,
    source             TEXT,
    category           TEXT DEFAULT 'morning',  -- morning/overnight/spot/workout
    timestamp_utc      REAL,
    window_start       REAL,
    window_end         REAL,
    rmssd_ms           REAL,
    sdnn_ms            REAL,
    mean_hr            REAL,
    min_hr             REAL,
    max_hr             REAL,
    pnn50_pct          REAL,
    cvnn_pct           REAL,
    sample_count       INTEGER,
    duration_seconds   REAL,
    quality_score      REAL,
    quality_category   TEXT,
    calculation_method TEXT,
    valid              INTEGER DEFAULT 1,
    synced_to_icu      INTEGER DEFAULT 0,
    created_at         TEXT DEFAULT (datetime('now')),
    UNIQUE(date, source, category)
);

CREATE TABLE IF NOT EXISTS hrv_baseline (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_on   TEXT,
    window_days   INTEGER,
    mean_rmssd    REAL,
    median_rmssd  REAL,
    std_rmssd     REAL,
    cv_pct        REAL,
    count         INTEGER,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- Aggiunge colonna hrv_sdnn alla tabella wellness se non esiste
-- (eseguito separatamente in migrate_hrv_schema per evitare errori)
"""


def migrate_hrv_schema(db=None) -> None:
    """Crea/aggiorna lo schema HRV. Idempotente (IF NOT EXISTS)."""
    if get_db is None:
        log.error("db.py non importabile — migrazione HRV saltata")
        return
    conn = db or get_db()
    conn.executescript(MIGRATION_SQL)
    # Aggiunge colonna hrv_sdnn se non esiste
    try:
        conn.execute("ALTER TABLE wellness ADD COLUMN hrv_sdnn REAL")
        conn.commit()
        log.info("Colonna hrv_sdnn aggiunta alla tabella wellness")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            log.warning(f"Impossibile aggiungere colonna hrv_sdnn: {e}")
    conn.commit()
    log.info("Schema HRV migrato (tabelle huawei_*, hrv_*, daily_hrv, hrv_baseline)")


# ─────────────────────────────────────────────────────────────────────────────
# Storage: salvataggio idempotente (task #17)
# ─────────────────────────────────────────────────────────────────────────────

def store_raw_records(records: List[Dict[str, Any]], db=None) -> int:
    """Inserisce record grezzi con fingerprint per idempotenza."""
    if get_db is None or not records:
        return 0
    conn = db or get_db()
    n = 0
    for r in records:
        fp = r.get("fingerprint") or _fp("raw", r)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO huawei_raw_record
                   (source_file, record_type, timestamp_utc, raw_value, raw_json, tz_hint, fingerprint)
                   VALUES (?,?,?,?,?,?,?)""",
                (r.get("source_file"), r.get("record_type"), r.get("timestamp_utc"),
                 r.get("raw_value"), json.dumps(r.get("raw_dict", {})),
                 r.get("tz_hint"), fp),
            )
            n += 1
        except sqlite3.Error as e:
            log.warning("skip raw record: %s", e)
    conn.commit()
    return n


def store_rr_intervals(points: List[Dict[str, Any]], db=None) -> int:
    """Salva RR/NN (raw + clean separati). Idempotente via fingerprint."""
    if get_db is None or not points:
        return 0
    conn = db or get_db()
    n = 0
    for p in points:
        fp = p.get("fingerprint") or _fp("rr", p)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO huawei_rr_interval
                   (source, timestamp_utc, raw_interval_ms, clean_interval_ms, corrected, session_id, fingerprint)
                   VALUES (?,?,?,?,?,?,?)""",
                (p.get("source", "huawei"), p.get("timestamp"),
                 p.get("raw_interval_ms", p.get("interval_ms")),
                 p.get("clean_interval_ms", p.get("interval_ms")),
                 1 if p.get("corrected") else 0,
                 p.get("session_id"), fp),
            )
            n += 1
        except sqlite3.Error:
            pass
    conn.commit()
    return n


def store_daily_hrv(daily: Dict[str, Any], category: str = "morning", db=None) -> bool:
    """Salva/aggiorna DailyHRV. Idempotente via (date, source, category)."""
    if get_db is None or not daily:
        return False
    conn = db or get_db()
    conn.execute(
        """INSERT OR REPLACE INTO daily_hrv
           (date, source, category, timestamp_utc, window_start, window_end,
            rmssd_ms, sdnn_ms, mean_hr, min_hr, max_hr, pnn50_pct, cvnn_pct,
            sample_count, duration_seconds, quality_score, quality_category,
            calculation_method, valid, synced_to_icu)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
        (daily.get("date"), daily.get("source", "huawei"),
         category, daily.get("timestamp"), daily.get("window_start"),
         daily.get("window_end"), daily.get("rmssd_ms"), daily.get("sdnn_ms"),
         daily.get("mean_hr"), daily.get("min_hr"), daily.get("max_hr"),
         daily.get("pnn50_pct"), daily.get("cvnn_pct"), daily.get("sample_count"),
         daily.get("duration_seconds"), daily.get("quality_score"),
         daily.get("quality_category"), daily.get("calculation_method"),
         1 if daily.get("valid", True) else 0),
    )
    conn.commit()
    return True


def store_baseline(b: Dict[str, Any], db=None) -> None:
    if get_db is None:
        return
    conn = db or get_db()
    conn.execute(
        """INSERT INTO hrv_baseline
           (computed_on, window_days, mean_rmssd, median_rmssd, std_rmssd, cv_pct, count)
           VALUES (?,?,?,?,?,?,?)""",
        (datetime.now(timezone.utc).isoformat(), b.get("window_days"),
         b.get("mean_rmssd"), b.get("median_rmssd"), b.get("std_rmssd"),
         b.get("cv_pct"), b.get("count", 0)),
    )
    conn.commit()


def _fp(prefix: str, d: Dict[str, Any]) -> str:
    import hashlib
    key = f"{prefix}|{d.get('timestamp_utc') or d.get('timestamp')}|{d.get('raw_value', d.get('interval_ms'))}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# Adapter Intervals.icu (task #8/#14) — estende il pattern SyncTarget
# ─────────────────────────────────────────────────────────────────────────────

def to_icu_wellness_bulk(daily: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Mappa DailyHRV → campo wellness-bulk di Intervals.icu.

    Intervals ACCETTA (documentato):
        hrvRmssd  — rMSSD in ms
        hrvSdnn   — SDNN in ms  (campo ufficiale, se presente nel piano wellness)

    Se la qualità è < MIN_QUALITY_FOR_SYNC → None (NON sincronizzare,
    task #13/#15: un valore invalid non diventa HRV ufficiale).

    NOTA (task #15): se Huawei fornisce un generico "HRV" senza prove che sia
    rMSSD, NON lo mappiamo qui. Solo rmssd_ms calcolato localmente da RR/NN.
    """
    from hrv_engine import MIN_QUALITY_FOR_SYNC
    if not daily or not daily.get("valid"):
        return None
    if (daily.get("quality_score") or 0) < MIN_QUALITY_FOR_SYNC:
        log.info("DailyHRV %s qualità %s < soglia — NON sincronizzato",
                 daily.get("date"), daily.get("quality_score"))
        return None

    item = {"id": daily.get("date")}
    if daily.get("rmssd_ms") is not None:
        item["hrvRmssd"] = round(daily["rmssd_ms"], 1)
    if daily.get("sdnn_ms") is not None:
        item["hrvSdnn"] = round(daily["sdnn_ms"], 1)
    # Intervals NON accetta pNN50/LF-HF/raw → restano local only (task #17)
    return item if len(item) > 1 else None


def push_daily_hrv_to_icu(daily: Dict[str, Any], athlete_id: str, api_key: str,
                          db=None) -> Dict[str, Any]:
    """
    Pusha un DailyHRV su Intervals.icu via wellness-bulk PUT.

    Restituisce {ok, synced, error}. Se Intervals rifiuta → errore loggato,
    il dato resta nel DB locale (task #30: privacy — solo metriche aggregate).
    """
    import httpx
    payload = to_icu_wellness_bulk(daily)
    if not payload:
        return {"ok": False, "error": "DailyHRV non idoneo al sync (qualità/invalid)"}
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness-bulk"
    try:
        resp = httpx.put(url, headers={"Authorization": f"Basic {api_key}"},
                         json=[payload], timeout=20)
        if resp.status_code in (200, 201):
            if get_db is not None:
                conn = db or get_db()
                conn.execute(
                    "UPDATE daily_hrv SET synced_to_icu=1 WHERE date=? AND source=?",
                    (daily.get("date"), daily.get("source", "huawei")))
                conn.commit()
            return {"ok": True, "synced": 1, "payload": payload}
        return {"ok": False, "error": f"ICU {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": f"Network ICU: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# Query / export (task #19)
# ─────────────────────────────────────────────────────────────────────────────

def get_daily_hrv_range(start: str, end: str, db=None) -> List[Dict[str, Any]]:
    if get_db is None:
        return []
    conn = db or get_db()
    cur = conn.execute(
        "SELECT * FROM daily_hrv WHERE date BETWEEN ? AND ? ORDER BY date",
        (start, end))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def import_icu_hrv(db=None) -> Dict[str, Any]:
    """
    Legge i dati HRV da Intervals.icu (già sincronizzati nel DB locale wellness)
    e li normalizza rispettando la regola #15/#31:

      * Intervals espone `hrv` (aggregato, AMBIGUO) → NON è rMSSD automatico.
        Viene registrato come 'icu_hrv' (baseline di riferimento), mai come
        rmssd_ms calcolato.
      * Intervals espone `hrvSDNN` nel raw_json (quando il device lo misura) →
        campo esplicito, utilizzabile come sdnn di confronto.
      * RR/NN grezzi NON sono disponibili da Intervals → non possiamo calcolare
        RMSSD/SDNN da zero; la metrica primaria resta quella calcolata da Huawei.

    Popola i campi `hrv` e `hrvSDNN` nella tabella `wellness` se presenti nei dati importati.
    
    Restituisce un riepilogo dei giorni importati e il conteggio di quali campi
    erano presenti. Utile per popolare hrv_baseline come confronto.
    """
    if get_db is None:
        return {"ok": False, "error": "db non disponibile"}
    conn = db or get_db()
    try:
        rows = conn.execute(
            "SELECT date, hrv, raw_json FROM wellness ORDER BY date"
        ).fetchall()
    except sqlite3.Error as e:
        return {"ok": False, "error": f"query wellness: {e}"}

    imported = 0
    hrv_present = 0
    sdnn_present = 0
    updated = 0
    for date_s, hrv_val, raw_json in rows:
        if not date_s:
            continue
        sdnn = None
        new_hrv = hrv_val
        if raw_json:
            try:
                rj = json.loads(raw_json)
                # Estrae hrv e hrvSDNN dal raw_json se presenti
                if rj.get("hrv") is not None:
                    new_hrv = rj.get("hrv")
                sdnn = rj.get("hrvSDNN")
            except (json.JSONDecodeError, TypeError):
                pass
        # Registra solo se c'è almeno un dato HRV da Intervals
        if new_hrv is None and sdnn is None:
            continue
        if new_hrv is not None:
            hrv_present += 1
        if sdnn is not None:
            sdnn_present += 1
        # Aggiorna la tabella wellness con i dati HRV estratti
        if new_hrv != hrv_val or sdnn is not None:
            try:
                conn.execute(
                    "UPDATE wellness SET hrv = ?, hrv_sdnn = ? WHERE date = ?",
                    (float(new_hrv) if new_hrv is not None else None,
                     float(sdnn) if sdnn is not None else None,
                     date_s)
                )
                updated += 1
            except sqlite3.Error:
                pass
        # NON inseriamo in daily_hrv (quello è per RMSSD calcolato localmente).
        # Memorizziamo il riferimento Intervals in hrv_baseline come fonte esterna.
        try:
            conn.execute(
                """INSERT OR REPLACE INTO hrv_baseline
                   (computed_on, window_days, mean_rmssd, median_rmssd, std_rmssd, cv_pct, count)
                   VALUES (?,?,?,?,?,?,?)""",
                (f"icu:{date_s}", 1,
                 float(new_hrv) if new_hrv is not None else None,
                 None, None, None, 1),
            )
            imported += 1
        except sqlite3.Error:
            pass
    conn.commit()
    return {
        "ok": True,
        "days_with_icu_hrv": imported,
        "icu_hrv_aggregated_present": hrv_present,
        "icu_hrv_sdnn_present": sdnn_present,
        "wellness_rows_updated": updated,
        "note": "Campo 'hrv' Intervals NON è rMSSD calcolato; usato solo come riferimento. Popolato hrv e hrv_sdnn in wellness.",
    }


def export_csv(daily_list: List[Dict[str, Any]], path: str) -> None:
    """Esporta DailyHRV in CSV (task #19)."""
    import csv
    cols = ["date", "timestamp", "rmssd_ms", "sdnn_ms", "mean_hr",
            "sample_count", "duration_seconds", "quality_score",
            "quality_category", "source", "calculation_method"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for d in daily_list:
            w.writerow(d)


def export_json(daily_list: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(daily_list, f, indent=2, default=str)
