"""PCC 5.x — CP models & Progression Levels (views over the power engine).

Single source of truth: the athlete's best-effort power-duration curve already
computed by fitness_estimation.extract_best_efforts / power_curve. This module
NEVER invents a new training model; it fits known published models to the
curve and derives TrainerRoad-style progression levels from it.

1) Morton 3-parameter CP model (Morton 1996; "3P").
   The classic 2P Monod-Scherrer fit already lives in
   fitness_estimation.compute_cp_wprime. The 3P adds a time constant tau
   (the W' reconstitution delay), giving:
       t = W' / (P - CP) - tau
   Linear in 1/(P-CP); we grid-search CP and tau jointly (least squares on t)
   and report CP, W', tau, plus R^2. This is the "richer power-duration"
   variant intervals.icu / WKO5 expose. Source: Morton R, "The critical power
   and related whole-body bioenergetic models", Eur J Appl Physiol 2006;
   also Jones et al. 2019 (front. physiol) on 3P validity.

2) Progression Levels per zone (TrainerRoad-style).
   Each training zone maps to a representative effort duration; the athlete's
   best-effort W/kg at that duration is normalised against an elite-male
   benchmark W/kg (power-profiling literature, Leo et al. 2021 Eur J Appl
   Physiol) and mapped to a 1-10 level. Higher level = more developed system.
   Sources: Leo et al. 2021 (power profiling); TrainerRoad "Progression
   Levels" concept (zone-based, duration-anchored).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Representative zone -> anchor duration (seconds) used for the level.
ZONE_ANCHORS: list[tuple[str, str, int]] = [
    ("Endurance (Z2)", "endurance", 1200),      # 20 min
    ("Tempo (Z3)", "tempo", 600),               # 10 min
    ("Soglia (Z4)", "threshold", 480),          # 8 min
    ("VO2max (Z5)", "vo2max", 180),             # 3 min
    ("Anaerobico (Z6)", "anaerobic", 60),        # 1 min
    ("Sprint (Z7)", "sprint", 30),              # 30 s
]

# Elite-male benchmark W/kg at each anchor duration (approx, from
# power-profiling literature / ProCyclingStats-style career bests). Used only
# to normalise the athlete's level (level = 10 at ~elite, ~1 near untrained).
ELITE_WKG: dict[str, float] = {
    "endurance": 5.6,    # ~20 min
    "tempo": 6.0,        # ~10 min
    "threshold": 6.6,    # ~8 min
    "vo2max": 7.4,       # ~3 min
    "anaerobic": 9.2,    # ~1 min
    "sprint": 16.0,      # ~30 s
}


@dataclass
class CpModels:
    monod_cp_w: Optional[float] = None
    monod_wprime_j: Optional[float] = None
    morton_cp_w: Optional[float] = None
    morton_wprime_j: Optional[float] = None
    morton_tau_s: Optional[float] = None
    morton_r2: Optional[float] = None
    progression_levels: list[dict] = field(default_factory=list)


def _ols_t_on_inv(resid_pairs: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Fit t = slope*(1/(P-CP)) + intercept  -> slope=W', intercept=-tau.

    resid_pairs: list of (1/(P-CP), t). Returns (W', -intercept=tau, r2).
    """
    n = len(resid_pairs)
    sx = sum(p[0] for p in resid_pairs)
    sy = sum(p[1] for p in resid_pairs)
    sxx = sum(p[0] * p[0] for p in resid_pairs)
    sxy = sum(p[0] * p[1] for p in resid_pairs)
    denom = n * sxx - sx * sx
    if denom <= 1e-12:
        return (0.0, 0.0, 0.0)
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    y_mean = sy / n
    ss_tot = sum((p[1] - y_mean) ** 2 for p in resid_pairs) or 1e-12
    ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in resid_pairs)
    r2 = max(0.0, 1.0 - ss_res / ss_tot)
    return (slope, -intercept, r2)


def fit_morton_3p(best_efforts: dict[int, int]) -> Optional[tuple[float, float, float, float]]:
    """Grid-search Morton 3P (CP, W', tau, R^2) from best efforts.

    Uses the standard durations {120, 180, 300, 480, 600, 1200} s. Returns
    (cp_w, wprime_j, tau_s, r2) or None if insufficient data / non-physical.
    """
    durs = [120, 180, 300, 480, 600, 1200]
    pts = [(d, best_efforts[d]) for d in durs if d in best_efforts and best_efforts[d] > 0]
    if len(pts) < 3:
        return None
    powers = sorted(p for _, p in pts)
    p_min, p_max = powers[0], powers[-1]
    best: Optional[tuple[float, float, float, float]] = None
    # Grid over candidate CP (must be below the shortest effort, above a floor)
    # and tau (>= 0, bounded). Keep physiological bounds.
    cp_lo = max(80.0, 0.55 * p_min)
    cp_hi = 0.98 * p_min
    if cp_hi <= cp_lo:
        return None
    for cp in [cp_lo + (cp_hi - cp_lo) * i / 40 for i in range(41)]:
        for tau in [j * 3.0 for j in range(0, 21)]:  # 0..60 s
            pairs = []
            ok = True
            for d, p in pts:
                denom = p - cp
                if denom <= 1.0:
                    ok = False
                    break
                pairs.append((1.0 / denom, d + tau))
            if not ok:
                continue
            w_prime, tau_est, r2 = _ols_t_on_inv(pairs)
            if w_prime <= 0 or tau_est < -1.0:
                continue
            if r2 < 0.90:
                continue
            # Joint cost: prefer higher R^2 then lower CP error vs 2P-style.
            score = r2 - 0.0  # primary: fit quality
            if best is None or score > best[3]:
                best = (cp, w_prime, max(tau_est, 0.0), r2)
    return best


def compute_progression_levels(
    best_efforts: dict[int, int],
    body_kg: float,
) -> list[dict]:
    """TrainerRoad-style 1-10 level per zone from the athlete's curve."""
    levels: list[dict] = []
    if body_kg <= 0:
        return levels
    for label, key, dur in ZONE_ANCHORS:
        watts = best_efforts.get(dur)
        if not watts:
            levels.append({
                "zone": label, "key": key, "duration_s": dur,
                "level": None, "wkg": None,
                "elite_wkg": ELITE_WKG[key], "note": "nessun dato a questa durata",
            })
            continue
        wkg = watts / body_kg
        level = max(1, min(10, round(10.0 * wkg / ELITE_WKG[key])))
        levels.append({
            "zone": label, "key": key, "duration_s": dur,
            "level": level, "wkg": round(wkg, 2),
            "elite_wkg": ELITE_WKG[key],
            "note": "",
        })
    return levels


def compute_cp_models(best_efforts: dict[int, int], body_kg: float) -> CpModels:
    """Fit Monod 2P (delegated) + Morton 3P, and progression levels."""
    out = CpModels()
    # Monod 2P already in fitness_estimation.
    try:
        from fitness_estimation import compute_cp_wprime
        res = compute_cp_wprime(best_efforts)
        if res:
            out.monod_cp_w = round(res[0], 1)
            out.monod_wprime_j = round(res[1])
    except Exception:
        pass
    # Morton 3P.
    m3 = fit_morton_3p(best_efforts)
    if m3:
        out.morton_cp_w = round(m3[0], 1)
        out.morton_wprime_j = round(m3[1])
        out.morton_tau_s = round(m3[2], 1)
        out.morton_r2 = round(m3[3], 3)
    # Progression levels.
    out.progression_levels = compute_progression_levels(best_efforts, body_kg)
    return out


def cp_models_to_dict(m: CpModels) -> dict:
    return {
        "monod": {"cp_w": m.monod_cp_w, "wprime_j": m.monod_wprime_j},
        "morton_3p": {
            "cp_w": m.morton_cp_w,
            "wprime_j": m.morton_wprime_j,
            "tau_s": m.morton_tau_s,
            "r2": m.morton_r2,
        },
        "progression_levels": m.progression_levels,
        "method": "fit su power-duration (2P Monod + 3P Morton)",
        "sources": [
            "Monod & Scherrer 1965 (2P)",
            "Morton 2006 / Jones et al. 2019 (3P)",
            "Leo et al. 2021 Eur J Appl Physiol (power profiling)",
            "TrainerRoad Progression Levels (zone-duration anchored)",
        ],
    }
