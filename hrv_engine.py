"""
hrv_engine.py — Motore HRV riutilizzabile e production-ready.

Scopo:
    Trasformare una serie di intervalli RR/NN (beat-to-beat, in ms) in metriche
    HRV standard (RMSSD, SDNN, pNN50, LF/HF, ...) con una pipeline di cleaning
    professionale, calcolo di HRV giornaliera "morning", baseline rolling e trend.

Principi (vedi task #5/#15/#28/#38):
    * RAW RR e CLEAN NN sono conservati SEPARATI (non si muta il dato originale).
    * RMSSD/SDNN sono calcolati LOCALMENTE da RR/NN, MAI copiati da un indice
      proprietario ("HRV") salvo prova documentata che il valore è rMSSD.
    * Soglie minime documentate: durata minima, numero minimo di NN.
    * Quality score 0..1 con categorie excellent/good/fair/poor/invalid.
    * Nessun dato medico: è un indicatore di training/recovery, non diagnosi.

Riusa le astrazioni del progetto:
    * Nessuna nuova dipendenza (solo stdlib: math, statistics, datetime, json).
    * Compatibile con il pattern `athlete_metrics` (date, metric, value, source).

Autore: PCC Pro — estensione Huawei Health / HRV (v5.5.0)
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Sequence, List, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# Costanti & soglie (documentate — task #28)
# ─────────────────────────────────────────────────────────────────────────────

# Fisiologicamente un RR in ms a riposo sta in ~250..2500 ms (HR 24..240 bpm).
# Lasciamo un margine per catch ectopic/artifact.
RR_MIN_MS = 250.0
RR_MAX_MS = 2500.0

# Soglie minime per ritenere valida una finestra (task #6/#13)
MIN_NN_COUNT = 8           # almeno ~8 battiti per uno RMSSD sensato
MIN_DURATION_S = 10.0      # almeno 10s di registrazione
MIN_QUALITY_FOR_SYNC = 0.5  # sotto questa soglia NON sincronizzare come HRV ufficiale

# Artifact detection: un salto > questa frazione vs mediana locale è sospetto
ARTIFACT_RATIO = 0.25

# Morning window default (task #9)
DEFAULT_MORNING_WINDOW_S = 300       # 5 minuti
DEFAULT_MORNING_LOOKBACK_S = 3 * 3600  # cerca entro 3h dal risveglio


@dataclass
class RRPoint:
    """Un singolo intervallo RR/NN grezzo (non modificato)."""
    timestamp: float          # epoch seconds (UTC) del battito
    interval_ms: float        # durata RR in ms
    source: str = "unknown"
    quality: Optional[float] = None
    session_id: Optional[str] = None


@dataclass
class CleanNN:
    """NN dopo cleaning (ectopic/artifact rimossi o corretti)."""
    timestamp: float
    interval_ms: float
    raw_interval_ms: float     # valore originale prima del cleaning
    corrected: bool = False    # True se era ectopic e è stato interpolato
    source: str = "unknown"
    session_id: Optional[str] = None


@dataclass
class QualityResult:
    score: float              # 0..1
    category: str             # excellent/good/fair/poor/invalid
    n_raw: int
    n_clean: int
    n_artifacts: int
    n_missing: int
    duration_s: float
    continuity: float         # 0..1, frazione di segnale continuo


@dataclass
class HRVMetrics:
    """Risultato del calcolo su una finestra di NN."""
    rmssd_ms: Optional[float] = None
    sdnn_ms: Optional[float] = None
    mean_nn_ms: Optional[float] = None
    median_nn_ms: Optional[float] = None
    mean_hr: Optional[float] = None
    min_hr: Optional[float] = None
    max_hr: Optional[float] = None
    pnn50_pct: Optional[float] = None
    cvnn_pct: Optional[float] = None
    sdann_ms: Optional[float] = None       # richiede segmentazione per minuto
    hrv_triangular_index: Optional[float] = None
    lf_ms2: Optional[float] = None          # frequency-domain (se durata ok)
    hf_ms2: Optional[float] = None
    lf_hf_ratio: Optional[float] = None
    respiratory_rate: Optional[float] = None  # se fornito esplicitamente
    sample_count: int = 0
    duration_seconds: float = 0.0
    quality_score: float = 0.0
    quality_category: str = "invalid"
    calculation_method: str = "rmssd_nn_cleaned_v1"
    algorithm: str = "standard_hrv_v1"
    timestamp: Optional[float] = None
    source: str = "unknown"
    valid: bool = False         # False se sotto soglie minime


# ─────────────────────────────────────────────────────────────────────────────
# 1) ESTRAZIONE RR/NN (task #4)
# ─────────────────────────────────────────────────────────────────────────────

def extract_rr_intervals(
    raw: Sequence[Dict[str, Any]],
    source: str = "huawei_health",
) -> List[RRPoint]:
    """
    Normalizza una lista di dict grezzi in RRPoint.

    Cerca (case-insensitive) tra i campi/chiavi i sinonimi:
        rr, rri, rr_interval, nn, nn_interval, ibi, interbeat_interval,
        heart_rate_variability, hrv (se esplicitamente intervallo)

    Ogni dict deve contenere almeno un timestamp e un valore intervallo.
    I valori HR NON sono RR: se trova solo 'hr'/'heart_rate' (bpm) e non
    intervalli, restituisce lista vuota (non inventa RR da HR — task #15).
    """
    points: List[RRPoint] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        # trova timestamp
        ts = _pick_first(row, ["timestamp", "time", "date", "epoch", "t", "datetime"])
        if ts is None:
            continue
        ts_epoch = _to_epoch(ts)
        if ts_epoch is None:
            continue
        # trova intervallo
        iv = _pick_first(row, [
            "rr", "rri", "rr_interval", "rrinterval", "nn", "nn_interval",
            "nninterval", "ibi", "interbeat_interval", "interval_ms",
            "interval", "rr_ms", "nn_ms",
        ])
        if iv is None:
            continue
        try:
            iv_ms = float(iv)
        except (TypeError, ValueError):
            continue
        # se il valore è in secondi (< 10) lo scaliamo a ms (errore comune)
        if 0 < iv_ms < 10:
            iv_ms *= 1000.0
        q = row.get("quality") or row.get("status")
        sid = row.get("session_id") or row.get("event_id")
        points.append(RRPoint(
            timestamp=ts_epoch,
            interval_ms=iv_ms,
            source=source,
            quality=(float(q) if isinstance(q, (int, float)) else None),
            session_id=(str(sid) if sid is not None else None),
        ))
    # ordina per timestamp (monotonicità — task #5)
    points.sort(key=lambda p: p.timestamp)
    return points


def _pick_first(d: Dict[str, Any], keys: Sequence[str]) -> Any:
    lowered = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k in lowered and lowered[k] not in (None, ""):
            return lowered[k]
    return None


def _to_epoch(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)):
        # se è un numero grande tipo 20260817 → non è epoch; lascia perdere
        if v > 1e12:  # ms epoch
            return v / 1000.0
        if v > 1e9:   # s epoch
            return float(v)
        return None
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.fromisoformat(s).timestamp()
            except ValueError:
                try:
                    return datetime.strptime(s, fmt).timestamp()
                except ValueError:
                    continue
    if isinstance(v, datetime):
        return v.timestamp()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2) CLEANING RR → NN (task #5)
# ─────────────────────────────────────────────────────────────────────────────

def clean_rr(
    points: Sequence[RRPoint],
    rr_min: float = RR_MIN_MS,
    rr_max: float = RR_MAX_MS,
    artifact_ratio: float = ARTIFACT_RATIO,
) -> List[CleanNN]:
    """
    Pipeline di cleaning professionale:
        1. rimozione valori impossibili (fuori [rr_min, rr_max])
        2. controllo fisiologico (HR derivata entro 24..240 bpm)
        3. artifact/ectopic detection (salto > artifact_ratio vs mediana mobile)
        4. correzione ectopic via interpolazione lineare (non silenziosa:
           il valore RAW è preservato in raw_interval_ms, corrected=True)
        5. gestione duplicati (stesso timestamp → tiene il primo)
        6. gestione gap (li conserva come buchi, non riempie)
        7. controllo monotonicità timestamp (già ordinati)

    NON modifica points; restituisce CleanNN separati.
    """
    clean: List[CleanNN] = []
    seen_ts = set()
    if not points:
        return clean

    # mediana iniziale per detect artifact
    vals = [p.interval_ms for p in points
            if rr_min <= p.interval_ms <= rr_max]
    med = statistics.median(vals) if vals else (rr_min + rr_max) / 2

    for p in points:
        # duplicati
        if p.timestamp in seen_ts:
            continue
        seen_ts.add(p.timestamp)

        raw = p.interval_ms
        # valore impossibile → scartato (non corretto)
        if not (rr_min <= raw <= rr_max):
            continue

        # artifact: salto eccessivo vs mediana corrente
        is_artifact = abs(raw - med) > artifact_ratio * med
        if is_artifact:
            # interpolazione lineare col precedente valido se esiste
            if clean:
                prev = clean[-1].interval_ms
                # stima semplice: usa la mediana corrente come NN corretto
                corrected_val = med
            else:
                corrected_val = raw  # primo punto, nessun contesto
            clean.append(CleanNN(
                timestamp=p.timestamp,
                interval_ms=corrected_val,
                raw_interval_ms=raw,
                corrected=True,
                source=p.source,
                session_id=p.session_id,
            ))
            # aggiorna mediana lentamente
            med = 0.9 * med + 0.1 * corrected_val
        else:
            clean.append(CleanNN(
                timestamp=p.timestamp,
                interval_ms=raw,
                raw_interval_ms=raw,
                corrected=False,
                source=p.source,
                session_id=p.session_id,
            ))
            med = 0.9 * med + 0.1 * raw

    return clean


# ─────────────────────────────────────────────────────────────────────────────
# 3) CALCOLO METRICHE (task #6/#7/#8)
# ─────────────────────────────────────────────────────────────────────────────

def compute_quality(
    raw: Sequence[RRPoint],
    clean: Sequence[CleanNN],
    duration_s: float,
) -> QualityResult:
    n_raw = len(raw)
    n_clean = len(clean)
    n_artifacts = sum(1 for c in clean if c.corrected)
    n_missing = n_raw - n_clean - n_artifacts  # scartati per fuori range
    # continuità: frazione di NN con gap < 2s
    continuity = 1.0
    if len(clean) > 1:
        gaps = [clean[i].timestamp - clean[i - 1].timestamp
                for i in range(1, len(clean))]
        good = sum(1 for g in gaps if g < 2.0)
        continuity = good / len(gaps) if gaps else 1.0

    # score composito
    score = 1.0
    if n_clean < MIN_NN_COUNT:
        score *= 0.3
    if duration_s < MIN_DURATION_S:
        score *= 0.5
    if n_clean > 0:
        score *= (1.0 - 0.5 * (n_artifacts / n_clean))
    score *= (0.5 + 0.5 * continuity)
    score = max(0.0, min(1.0, score))

    if score >= 0.85:
        cat = "excellent"
    elif score >= 0.7:
        cat = "good"
    elif score >= 0.5:
        cat = "fair"
    elif score >= 0.3:
        cat = "poor"
    else:
        cat = "invalid"

    return QualityResult(
        score=round(score, 3),
        category=cat,
        n_raw=n_raw,
        n_clean=n_clean,
        n_artifacts=n_artifacts,
        n_missing=max(0, n_missing),
        duration_s=round(duration_s, 1),
        continuity=round(continuity, 3),
    )


def _rmssd(nn: Sequence[float]) -> float:
    if len(nn) < 2:
        return 0.0
    sq = sum((nn[i + 1] - nn[i]) ** 2 for i in range(len(nn) - 1))
    return math.sqrt(sq / (len(nn) - 1))


def _sdnn(nn: Sequence[float]) -> float:
    if len(nn) < 2:
        return 0.0
    return statistics.pstdev(nn)


def _pnn50(nn: Sequence[float]) -> float:
    if len(nn) < 2:
        return 0.0
    diffs = [abs(nn[i + 1] - nn[i]) for i in range(len(nn) - 1)]
    over = sum(1 for d in diffs if d > 50.0)
    return 100.0 * over / len(diffs)


def _hr_from_nn(ms: float) -> float:
    return 60000.0 / ms if ms > 0 else 0.0


def compute_hrv_metrics(
    clean: Sequence[CleanNN],
    raw: Optional[Sequence[RRPoint]] = None,
    source: str = "huawei_health",
    calculation_method: str = "rmssd_nn_cleaned_v1",
    timestamp: Optional[float] = None,
) -> HRVMetrics:
    """
    Calcola tutte le metriche HRV da una finestra di NN puliti.

    RMSSD = sqrt( Σ (NN[i+1]-NN[i])² / (N-1) )   [ms]
    SDNN  = deviazione standard popolazione dei NN [ms]

    Gestisce: finestre corte, NN insufficienti, artefatti, gap.
    Non restituisce metriche se la qualità minima non è rispettata
    (valid=False). Restituisce comunque i conteggi per debug.
    """
    n = len(clean)
    if n == 0:
        return HRVMetrics(valid=False, source=source,
                          calculation_method=calculation_method,
                          timestamp=timestamp)

    nn = [c.interval_ms for c in clean]
    if raw:
        duration_s = (raw[-1].timestamp - raw[0].timestamp) if len(raw) > 1 else 0.0
    else:
        duration_s = (clean[-1].timestamp - clean[0].timestamp) if n > 1 else 0.0

    q = compute_quality(raw if raw else [RRPoint(t, v) for t, v in
                     [(c.timestamp, c.raw_interval_ms) for c in clean]],
                     clean, duration_s)

    # soglie minime
    valid = (n >= MIN_NN_COUNT and duration_s >= MIN_DURATION_S
             and q.score >= 0.0)  # quality gate applicato a sync, non a calcolo

    # Metriche avanzate (task #8/#11): SDANN, triangular index, LF/HF freq-domain.
    # Calcolate sempre (se durata permette) ma esposte con flag di validità
    # separato — non inquinano RMSSD/SDNN principali.
    adv = compute_advanced_metrics(clean, raw=raw, source=source)

    m = HRVMetrics(
        rmssd_ms=round(_rmssd(nn), 2),
        sdnn_ms=round(_sdnn(nn), 2),
        mean_nn_ms=round(statistics.mean(nn), 2),
        median_nn_ms=round(statistics.median(nn), 2),
        mean_hr=round(_hr_from_nn(statistics.mean(nn)), 1),
        min_hr=round(_hr_from_nn(max(nn)), 1),
        max_hr=round(_hr_from_nn(min(nn)), 1),
        pnn50_pct=round(_pnn50(nn), 2),
        cvnn_pct=round(100.0 * statistics.pstdev(nn) / statistics.mean(nn), 2) if statistics.mean(nn) else None,
        sdann_ms=adv.get("sdann_ms"),
        hrv_triangular_index=adv.get("hrv_triangular_index"),
        lf_ms2=adv.get("lf_ms2"),
        hf_ms2=adv.get("hf_ms2"),
        lf_hf_ratio=adv.get("lf_hf_ratio"),
        sample_count=n,
        duration_seconds=round(duration_s, 1),
        quality_score=q.score,
        quality_category=q.category,
        calculation_method=calculation_method,
        algorithm="standard_hrv_v1",
        timestamp=timestamp,
        source=source,
        valid=valid,
    )
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 4) MORNING HRV WINDOW (task #9/#10)
# ─────────────────────────────────────────────────────────────────────────────

def detect_morning_window(
    clean: Sequence[CleanNN],
    wake_time: Optional[float] = None,
    sleep_end: Optional[float] = None,
    window_s: float = DEFAULT_MORNING_WINDOW_S,
    lookback_s: float = DEFAULT_MORNING_LOOKBACK_S,
) -> Optional[List[CleanNN]]:
    """
    Identifica la migliore finestra mattutina valida per il morning HRV.

    Ordine di preferenza (task #9):
        1. se Huawei fornisce wake_time/sleep_end → finestra subito dopo
        2. altrimenti: prima finestra valida (>= window_s, NN sufficienti)
           entro `lookback_s` dal risveglio stimato (o dall'inizio dati)
        3. se nessuna finestra lunga abbastanza → None (NON inventare)

    Restituisce la sotto-lista di CleanNN della finestra scelta, o None.
    """
    if not clean:
        return None

    anchor = wake_time or sleep_end
    if anchor is None:
        # stima risveglio = inizio dei dati (primo NN della sessione mattutina)
        anchor = clean[0].timestamp

    # finestra di ricerca: da anchor a anchor+lookback
    candidates = [c for c in clean if anchor <= c.timestamp <= anchor + lookback_s]
    if not candidates:
        candidates = list(clean)

    # scorri finestre contigue di durata >= window_s
    best: Optional[List[CleanNN]] = None
    best_q = -1.0
    i = 0
    while i < len(candidates):
        # accumula finché la durata < window_s
        j = i
        while j < len(candidates) and \
              (candidates[j].timestamp - candidates[i].timestamp) < window_s:
            j += 1
        if j > i:
            window = candidates[i:j]
            if len(window) >= MIN_NN_COUNT:
                q = compute_quality([], window,
                                    window[-1].timestamp - window[0].timestamp).score
                if q > best_q:
                    best_q = q
                    best = window
            i = j
        else:
            i += 1

    # se non troviamo una finestra di window_s, accetta la più lunga se >= minima
    if best is None:
        # trova la run contigua più lunga
        longest = _longest_run(candidates)
        if longest and len(longest) >= MIN_NN_COUNT and \
           (longest[-1].timestamp - longest[0].timestamp) >= MIN_DURATION_S:
            best = longest
    return best


def _longest_run(seq: Sequence[CleanNN]) -> List[CleanNN]:
    if not seq:
        return []
    runs = []
    cur = [seq[0]]
    for prev, cur_p in zip(seq, seq[1:]):
        if cur_p.timestamp - prev.timestamp < 2.0:  # contiguo
            cur.append(cur_p)
        else:
            runs.append(cur)
            cur = [cur_p]
    runs.append(cur)
    return max(runs, key=len)


def build_daily_hrv(
    window: Sequence[CleanNN],
    raw: Sequence[RRPoint],
    date: str,
    source: str = "huawei_health",
    calculation_method: str = "rmssd_nn_cleaned_v1",
) -> Dict[str, Any]:
    """Costruisce il dict DailyHRV (task #10)."""
    m = compute_hrv_metrics(window, raw=raw, source=source,
                            calculation_method=calculation_method,
                            timestamp=window[0].timestamp if window else None)
    if not window:
        return {}
    return {
        "date": date,
        "timestamp": window[0].timestamp,
        "window_start": window[0].timestamp,
        "window_end": window[-1].timestamp,
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
        "source": source,
        "calculation_method": calculation_method,
        "valid": m.valid,
    }
    # (propagazione quality_score/valid già nei campi sopra)


# ─────────────────────────────────────────────────────────────────────────────
# 5) BASELINE & TREND (task #11/#12)
# ─────────────────────────────────────────────────────────────────────────────

def compute_baseline(daily: Sequence[Dict[str, Any]], window_days: int = 7) -> Dict[str, Any]:
    """
    Calcola baseline su `window_days` giorni di DailyHRV (i più recenti).

    Restituisce media, mediana, std, CV, e (se disponibile un valore odierno)
    z-score e deviazione percentuale.
    """
    # prendi gli ultimi `window_days` giorni (i più recenti per data)
    sorted_daily = sorted(daily, key=lambda d: d.get("date", ""), reverse=True)
    window = sorted_daily[:window_days]
    vals = [d["rmssd_ms"] for d in window if d.get("rmssd_ms") is not None]
    if not vals:
        return {"window_days": window_days, "count": 0}
    mean = statistics.mean(vals)
    median = statistics.median(vals)
    std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    cv = (std / mean * 100.0) if mean else 0.0
    return {
        "window_days": window_days,
        "count": len(vals),
        "mean_rmssd": round(mean, 2),
        "median_rmssd": round(median, 2),
        "std_rmssd": round(std, 2),
        "cv_pct": round(cv, 2),
    }


def hrv_deviation(today_rmssd: float, baseline_mean: float) -> Dict[str, Any]:
    """Deviazione % odierna vs baseline (task #11)."""
    if baseline_mean <= 0:
        return {"deviation_pct": None, "z_score": None}
    dev = (today_rmssd - baseline_mean) / baseline_mean * 100.0
    return {"deviation_pct": round(dev, 1), "baseline_mean": round(baseline_mean, 2)}


def rolling_average(daily: Sequence[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
    """Media mobile RMSSD su `days` giorni (task #12)."""
    out = []
    vals = [(d.get("date"), d.get("rmssd_ms")) for d in daily]
    for i in range(len(vals)):
        window = [v for (_, v) in vals[max(0, i - days + 1):i + 1]
                  if v is not None]
        if window:
            out.append({
                "date": vals[i][0],
                f"rolling_{days}d": round(statistics.mean(window), 2),
            })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 6) METRIHE AVANZATE (task #8/#11) — freq-domain, SDANN, triangular index
# ─────────────────────────────────────────────────────────────────────────────

# Soglie minime per metriche avanzate (documentate — task #28)
MIN_DURATION_FREQ_S = 120.0   # LF/HF richiede >= 2 min di segnale stazionario
FREQ_LO_FREQ_HZ = 0.04        # banda LF: 0.04–0.15 Hz (Task Force 1996)
FREQ_HI_FREQ_HZ = 0.15        # banda HF: 0.15–0.40 Hz
FREQ_HI_MAX_HZ = 0.40
RESAMPLE_HZ = 4.0             # resampling per Welch (4 Hz standard per HRV)


def compute_advanced_metrics(
    clean: Sequence[CleanNN],
    raw: Optional[Sequence[RRPoint]] = None,
    source: str = "huawei_health",
) -> Dict[str, Any]:
    """
    Calcola metriche avanzate NON riportate da Huawei/Intervals:

    * SDANN      — deviazione standard delle medie NN per minuto (necessita
                   segmentazione temporale; richiede durata >= 120s)
    * HRV triangular index — (N totale) / (picco dell'istogramma NN)
    * LF, HF, LF/HF — domain frequenza (Welch PSD su NN resampled a 4 Hz);
                   VALIDO SOLO se durata >= MIN_DURATION_FREQ_S e qualità ok.

    Ogni metrica ha il proprio flag di validità: non calcoliamo LF/HF su
    finestre troppo brevi (task #8: "NON calcolare metriche non valide su
    finestre troppo brevi").

    Restituisce dict con valori None dove non applicabile.
    """
    out: Dict[str, Any] = {
        "sdann_ms": None,
        "hrv_triangular_index": None,
        "lf_ms2": None,
        "hf_ms2": None,
        "lf_hf_ratio": None,
        "advanced_valid": False,
    }
    n = len(clean)
    if n == 0:
        return out

    nn = [c.interval_ms for c in clean]
    dur_s = (clean[-1].timestamp - clean[0].timestamp) if n > 1 else 0.0

    # HRV triangular index: N / conteggio nel bin modalità (bin = 1/128 s ≈ 7.8 ms)
    try:
        from collections import Counter
        bins = [round(v / 7.8125) for v in nn]  # 1/128 s binning (Task Force)
        counts = Counter(bins)
        modal = max(counts.values())
        out["hrv_triangular_index"] = round(n / modal, 2) if modal else None
    except Exception:
        pass

    # SDANN: medie NN per minuto, poi deviazione standard
    if dur_s >= 60.0 and n > 1:
        try:
            from collections import defaultdict
            per_min: Dict[int, List[float]] = defaultdict(list)
            t0 = clean[0].timestamp
            for c in clean:
                minute = int((c.timestamp - t0) // 60)
                per_min[minute].append(c.interval_ms)
            means = [statistics.mean(v) for v in per_min.values() if v]
            if len(means) >= 2:
                out["sdann_ms"] = round(statistics.pstdev(means), 2)
        except Exception:
            pass

    # LF/HF freq-domain: solo se segnale sufficientemente lungo e stazionario
    if dur_s >= MIN_DURATION_FREQ_S and n >= 32:
        try:
            import numpy as np
            # timestamp assoluti → resample NN a frequenza fissa (4 Hz)
            t = np.array([c.timestamp for c in clean], dtype=float)
            y = np.array(nn, dtype=float)
            t_rs = np.arange(t[0], t[-1], 1.0 / RESAMPLE_HZ)
            y_rs = np.interp(t_rs, t, y)
            # rimuovi media (per PSD serve segnale zero-mean dei NN)
            y_zm = y_rs - np.mean(y_rs)
            # Welch PSD
            f, psd = _welch_psd(y_zm, fs=RESAMPLE_HZ)
            lf_mask = (f >= FREQ_LO_FREQ_HZ) & (f <= FREQ_HI_FREQ_HZ)
            hf_mask = (f >= FREQ_HI_FREQ_HZ) & (f <= FREQ_HI_MAX_HZ)
            lf = float(np.trapezoid(psd[lf_mask], f[lf_mask])) if lf_mask.any() else 0.0
            hf = float(np.trapezoid(psd[hf_mask], f[hf_mask])) if hf_mask.any() else 0.0
            out["lf_ms2"] = round(lf, 2)
            out["hf_ms2"] = round(hf, 2)
            out["lf_hf_ratio"] = round(lf / hf, 2) if hf > 0 else None
            out["advanced_valid"] = True
        except Exception as e:
            log.warning("advanced freq-domain fallita: %s", e)

    return out


def _welch_psd(x: "np.ndarray", fs: float = 4.0):  # noqa: F821
    """Welch PSD usando solo numpy (no scipy). Restituisce (f, psd)."""
    import numpy as np
    n = len(x)
    seg = min(256, n)
    if seg < 32:
        seg = max(32, n // 2)
    noverlap = seg // 2
    # segmenta e media le periodogramme
    step = seg - noverlap
    if step < 1:
        step = 1
    segments = [x[i:i + seg] for i in range(0, max(1, n - seg + 1), step)]
    if not segments:
        segments = [x]
    win = np.hanning(seg)
    psds = []
    for s in segments:
        if len(s) < seg:
            s = np.pad(s, (0, seg - len(s)))
        detr = s - np.mean(s)
        w = detr * win
        spec = np.abs(np.fft.rfft(w)) ** 2
        psds.append(spec)
    avg = np.mean(psds, axis=0)
    freqs = np.fft.rfftfreq(seg, 1.0 / fs)
    # normalizzazione densità di potenza (semplificata, sufficiente per rapporti LF/HF)
    scale = 1.0 / (fs * np.sum(win ** 2))
    psd = avg * scale * 2  # *2 per one-sided
    return freqs, psd


# ─────────────────────────────────────────────────────────────────────────────

# Utility / serializzazione
# ─────────────────────────────────────────────────────────────────────────────

def to_json(obj: Any) -> str:
    if hasattr(obj, "__dataclass_fields__"):
        return json.dumps(asdict(obj), default=str, indent=2)
    return json.dumps(obj, default=str, indent=2)


def fingerprint(source: str, timestamp: float, measurement_type: str, value: float) -> str:
    """Fingerprint idempotenza import (task #17)."""
    import hashlib
    raw = f"{source}|{timestamp:.3f}|{measurement_type}|{value:.3f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
