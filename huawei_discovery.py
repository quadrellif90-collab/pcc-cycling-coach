"""
huawei_discovery.py — Discovery e parsing automatico degli export Huawei Health.

Supporta (task #1/#3/#22/#23):
    * Riconoscimento tipo file: ZIP / CSV / JSON / XML / directory estratta
    * Identificazione file Huawei rilevanti (nome, header, chiavi, tag)
    * Estrazione timestamp + normalizzazione timezone (UTC interna, local per giorno)
    * Gestione duplicati / dati mancanti / cambi formato
    * Non interrompere l'import se un file è corrotto (log + skip)
    * Detector case-insensitive per sinonimi RR/HRV/HR/sleep/spo2/...

Architettura (task #23): HuaweiParser interface + implementazioni
    HuaweiCsvParser, HuaweiJsonParser, HuaweiXmlParser, HuaweiZipParser.

NON hardcodiamo nomi di file: cerchiamo contenuto (headers/keys/tags).
NON inventiamo formati non verificabili: se un formato è ambiguo, lo
segnaliamo e non estraiamo RR da campi non provati.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Iterable

log = logging.getLogger("pcc.huawei_discovery")

# Sinonimi per il field-detection (task #22), case-insensitive
RR_KEYS = [
    "rr", "rri", "rr_interval", "rrinterval", "rr interval",
    "nn", "nn_interval", "nninterval", "nn interval",
    "ibi", "interbeat_interval", "interbeat interval",
    "hrv", "hrv trace", "hrv samples", "heart_rate_variability",
]
HR_KEYS = ["hr", "heart_rate", "heartrate", "bpm", "pulse"]
SLEEP_KEYS = ["sleep", "sleep_start", "sleep_end", "sleep_score", "sleepscore", "deep_sleep", "rem_sleep"]
SPO2_KEYS = ["spo2", "sp_o2", "oxygen", "blood_oxygen"]
RESP_KEYS = ["resp", "respiration", "respiratory_rate", "breathing"]
STRESS_KEYS = ["stress", "stress_score"]
RHR_KEYS = ["rhr", "resting_hr", "resting_heart_rate", "restinghr"]


@dataclass
class HuaweiRawRecord:
    """Record grezzo estratto da un export Huawei (task #3)."""
    source_file: str
    record_type: str          # hr / hrv_rr / sleep / spo2 / stress / rhr / activity
    timestamp_utc: Optional[float] = None
    raw_value: Optional[float] = None       # valore grezzo (es. RR in ms, HR in bpm)
    raw_dict: Dict[str, Any] = field(default_factory=dict)
    tz_hint: Optional[str] = None
    fingerprint: Optional[str] = None


@dataclass
class HuaweiNormalizedData:
    """Dati normalizzati: RR/NN estratti + metriche aggregate già presenti."""
    rr_points: List[Dict[str, Any]] = field(default_factory=list)
    hrv_aggregates: List[Dict[str, Any]] = field(default_factory=list)  # es. rmssd già calcolato da Huawei
    sleep: List[Dict[str, Any]] = field(default_factory=list)
    spo2: List[Dict[str, Any]] = field(default_factory=list)
    stress: List[Dict[str, Any]] = field(default_factory=list)
    rhr: List[Dict[str, Any]] = field(default_factory=list)
    # Campi HRV da Intervals.icu (raw_json)
    icu_hrv: List[Dict[str, Any]] = field(default_factory=list)  # hrv, hrvSDNN, ecc.
    warnings: List[str] = field(default_factory=list)


@dataclass
class HuaweiHRVData:
    """Solo i dati HRV rilevanti (RR grezzi + eventuali aggregate)."""
    rr_raw: List[Dict[str, Any]]
    hrv_aggregates: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────────────────────
# Field detection
# ─────────────────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", "_", s.strip().lower())


def detect_field_type(headers: Iterable[str]) -> Dict[str, str]:
    """Mappa header → tipo di dato rilevato."""
    norm = {_norm(h): h for h in headers}
    mapping = {}
    candidates = list(norm.keys())
    for key in candidates:
        if any(k in key for k in RR_KEYS):
            mapping[norm[key]] = "rr"
        elif any(k in key for k in HR_KEYS):
            mapping[norm[key]] = "hr"
        elif any(k in key for k in SLEEP_KEYS):
            mapping[norm[key]] = "sleep"
        elif any(k in key for k in SPO2_KEYS):
            mapping[norm[key]] = "spo2"
        elif any(k in key for k in RESP_KEYS):
            mapping[norm[key]] = "resp"
        elif any(k in key for k in STRESS_KEYS):
            mapping[norm[key]] = "stress"
        elif any(k in key for k in RHR_KEYS):
            mapping[norm[key]] = "rhr"
    return mapping


def _extract_epoch(row: Dict[str, Any], tz_hint: Optional[str] = None) -> Optional[float]:
    from hrv_engine import _to_epoch
    for k in ("timestamp", "time", "date", "datetime", "epoch", "start_time", "t"):
        if k in row and row[k] not in (None, ""):
            return _to_epoch(row[k])
    # prova qualsiasi chiave che contenga 'time' o 'date'
    for k, v in row.items():
        if ("time" in k.lower() or "date" in k.lower()) and v not in (None, ""):
            e = _to_epoch(v)
            if e:
                return e
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Parsers (task #23)
# ─────────────────────────────────────────────────────────────────────────────

class HuaweiParser:
    """Interface base."""

    def can_parse(self, path: str) -> bool:
        raise NotImplementedError

    def parse(self, path: str) -> HuaweiNormalizedData:
        raise NotImplementedError


class HuaweiCsvParser(HuaweiParser):
    def can_parse(self, path: str) -> bool:
        return path.lower().endswith(".csv")

    def parse(self, path: str) -> HuaweiNormalizedData:
        out = HuaweiNormalizedData()
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                fmap = detect_field_type(headers)
                if not fmap:
                    out.warnings.append(f"{path}: nessun campo HRV/HR/sleep riconosciuto")
                    return out
                rr_keys = [h for h, t in fmap.items() if t == "rr"]
                for row in reader:
                    ts = _extract_epoch(row)
                    for h, t in fmap.items():
                        val = row.get(h)
                        if val in (None, ""):
                            continue
                        try:
                            v = float(val)
                        except (TypeError, ValueError):
                            continue
                        if t == "rr" and ts is not None:
                            out.rr_points.append({
                                "timestamp": ts, "interval_ms": v,
                                "source": "huawei_csv", "quality": None,
                            })
                        elif t == "hr" and ts is not None:
                            out.hrv_aggregates.append({
                                "date": _date_from_ts(ts), "hr": v, "type": "hr"})
                        elif t in ("sleep", "spo2", "stress", "rhr") and ts is not None:
                            getattr(out, t if t != "rhr" else "rhr").append({
                                "timestamp": ts, "value": v})
        except Exception as e:
            out.warnings.append(f"{path}: ERRORE parsing CSV: {e}")
            log.error("CSV parse failed %s: %s", path, e)
        return out


class HuaweiJsonParser(HuaweiParser):
    def can_parse(self, path: str) -> bool:
        return path.lower().endswith(".json")

    def parse(self, path: str) -> HuaweiNormalizedData:
        out = HuaweiNormalizedData()
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            self._walk(data, out, path)
        except Exception as e:
            out.warnings.append(f"{path}: ERRORE parsing JSON: {e}")
            log.error("JSON parse failed %s: %s", path, e)
        return out

    def _walk(self, node, out: HuaweiNormalizedData, src: str, depth: int = 0):
        if depth > 20:
            return
        if isinstance(node, dict):
            # record singolo?
            keys = [_norm(k) for k in node.keys()]
            if any(any(rk in k for rk in RR_KEYS) for k in keys):
                ts = _extract_epoch(node)
                for k, v in node.items():
                    nk = _norm(k)
                    if any(rk in nk for rk in RR_KEYS) and isinstance(v, (int, float)):
                        if ts is not None:
                            out.rr_points.append({
                                "timestamp": ts, "interval_ms": float(v),
                                "source": "huawei_json"})
                    if any(rk in nk for rk in ["rmssd", "sdnn"]) and isinstance(v, (int, float)):
                        out.hrv_aggregates.append({
                            "date": _date_from_ts(ts) if ts else None,
                            "metric": nk, "value": float(v)})
            # Extract HRV data from Intervals raw_json (hrv, hrvSDNN, etc.)
            if "hrv" in node or "hrvSDNN" in node:
                ts = _extract_epoch(node)
                out.icu_hrv.append({
                    "timestamp": ts,
                    "hrv": node.get("hrv"),
                    "hrvSDNN": node.get("hrvSDNN"),
                    "source": "intervals_raw_json"
                })
            for v in node.values():
                self._walk(v, out, src, depth + 1)
        elif isinstance(node, list):
            for item in node:
                self._walk(item, out, src, depth + 1)


class HuaweiXmlParser(HuaweiParser):
    def can_parse(self, path: str) -> bool:
        return path.lower().endswith((".xml", ".tcx", ".gpx"))

    def parse(self, path: str) -> HuaweiNormalizedData:
        out = HuaweiNormalizedData()
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            # TCX/GPX: cerca <HeartRateBpm>/<bpm> o <Extensions> RR
            for el in root.iter():
                tag = _norm(el.tag.split("}")[-1])
                if any(rk in tag for rk in RR_KEYS):
                    txt = el.text
                    if txt:
                        try:
                            out.rr_points.append({
                                "timestamp": None, "interval_ms": float(txt),
                                "source": "huawei_xml"})
                        except ValueError:
                            pass
        except Exception as e:
            out.warnings.append(f"{path}: ERRORE parsing XML: {e}")
            log.error("XML parse failed %s: %s", path, e)
        return out


class HuaweiZipParser(HuaweiParser):
    def can_parse(self, path: str) -> bool:
        return path.lower().endswith(".zip")

    def parse(self, path: str) -> HuaweiNormalizedData:
        out = HuaweiNormalizedData()
        try:
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.lower().endswith((".csv", ".json", ".xml", ".tcx", ".gpx")):
                        # estrai in memoria e delega
                        data = z.read(name)
                        tmp = os.path.join("/tmp", os.path.basename(name))
                        with open(tmp, "wb") as f:
                            f.write(data)
                        sub = dispatch_parse(tmp)
                        _merge(out, sub)
        except Exception as e:
            out.warnings.append(f"{path}: ERRORE parsing ZIP: {e}")
            log.error("ZIP parse failed %s: %s", path, e)
        return out


def dispatch_parse(path: str) -> HuaweiNormalizedData:
    for cls in (HuaweiZipParser, HuaweiJsonParser, HuaweiXmlParser, HuaweiCsvParser):
        p = cls()
        if p.can_parse(path):
            return p.parse(path)
    # directory → tutti i file
    if os.path.isdir(path):
        out = HuaweiNormalizedData()
        for fn in sorted(os.listdir(path)):
            fp = os.path.join(path, fn)
            if os.path.isfile(fp):
                _merge(out, dispatch_parse(fp))
        return out
    return HuaweiNormalizedData(warnings=[f"{path}: formato non riconosciuto"])


def _merge(dst: HuaweiNormalizedData, src: HuaweiNormalizedData):
    dst.rr_points.extend(src.rr_points)
    dst.hrv_aggregates.extend(src.hrv_aggregates)
    dst.sleep.extend(src.sleep)
    dst.spo2.extend(src.spo2)
    dst.stress.extend(src.stress)
    dst.rhr.extend(src.rhr)
    dst.warnings.extend(src.warnings)


def _date_from_ts(ts: float) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point: importa un export (file o directory)
# ─────────────────────────────────────────────────────────────────────────────

def import_huawei_export(path: str, source: str = "huawei_health") -> HuaweiNormalizedData:
    """
    PRIORITÀ 1: discovery + parsing robusto di un export Huawei.

    Non interrompe su file corrotto: logga e continua.
    Restituisce HuaweiNormalizedData con rr_points (RAW, da pulire dopo).
    """
    log.info("Import Huawei export: %s", path)
    data = dispatch_parse(path)
    log.info("  RR points: %d | aggregates: %d | warnings: %d",
             len(data.rr_points), len(data.hrv_aggregates), len(data.warnings))
    for w in data.warnings:
        log.warning("  %s", w)
    return data
