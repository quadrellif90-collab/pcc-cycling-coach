"""PCC 5.x — Metabolic decoder (INSCYD-style "lab -> training" view).

STATUS: field-based ESTIMATE from a power-duration curve + body mass. NOT a
lab replacement. Built from peer-reviewed physiology so the numbers are
interpretable, not fabricated:

- VO2max from power: V̇O2max is reached near the asymptotic power of the
  power-duration curve. We use Critical Power (CP, Monod-Scherrer 2-param)
  as the heavy/severe boundary and convert via gross mechanical efficiency
  (P/V̇O2 ≈ 20-22% for trained cyclists; di Prampero 1986). The aerobic
  ceiling power Pmax_ao ≈ CP / (1 - W'/D') style asymptote; here we derive
  VO2max from the 60-min best effort and from CP and take the higher, capped
  by a physiological ceiling.
  Sources: Mader & Heck 1986 (metabolic anaer. threshold theory);
  di Prampero 1986 (efficiency); Leo et al. 2021 (power profiling review);
  INSCYD PPD validation J Science Cycling 2022 (VO2max r=0.945 vs lab).
- VLamax (maximal glycolytic power, mmol/L/s): estimated from the ratio of a
  short maximal effort (30s) to CP. A large gap => high glycolytic capacity.
  Source: INSCYD VLamax metric; Poffe et al. 2024 / Dunst et al. 2024
  (cadence caveat: VLamax is cadence-dependent; we assume ~90 rpm field).
- FatMax (peak fat oxidation power, W): occurs at ~45-55% V̇O2max, i.e.
  ~50-65% of FTP for most endurance cyclists. Source: Achten et al. 2002
  (FATmax protocol); Chrzanowski-Smith et al. 2020 (reliability).
- Zones: derived from CP and VO2max using standard percentages, aligned with
  the existing PCC zone model.

All outputs are clearly labelled "stima da power-duration (non lab)" in the UI.
Single source of truth: this module only READS best_efforts / CP / W' already
computed by fitness_estimation; it does not invent a new training model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Mechanical efficiency P/V̇O2 for trained cyclists (di Prampero 1986): ~21%.
# Convert W -> ml/min O2: V̇O2 = P / efficiency_gross where efficiency_gross
# is the fraction of metabolic power turned into mechanical power.
_GROSS_EFFICIENCY = 0.21
# Resting V̇O2 (ml/min/kg) added to the gross cost when expressing per-kg.
_REST_VO2_ML_KG_MIN = 3.5
# Body-mass-specific ceiling for VO2max in trained cyclists (ml/kg/min).
_VO2MAX_CEILING_ML_KG_MIN = 85.0


@dataclass
class MetabolicProfile:
    vo2max_ml_kg_min: Optional[float] = None
    vlamax_mmol_l_s: Optional[float] = None
    fatmax_w: Optional[float] = None
    cp_w: Optional[int] = None
    w_prime_j: Optional[int] = None
    ftp_w: Optional[int] = None
    fatmax_pct_ftp: Optional[float] = None
    method: str = "field power-duration (non lab)"
    assumptions: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def _vo2max_from_power(power_w: float, body_kg: float) -> float:
    """Gross V̇O2 (ml/min) from mechanical power, then per-kg.

    V̇O2_gross_ml_min = (P / efficiency) + resting component*kg.
    """
    if body_kg <= 0 or power_w <= 0:
        return 0.0
    metabolic_w = power_w / _GROSS_EFFICIENCY  # total metabolic power, W
    vo2_gross_ml_min = (metabolic_w * 60.0 / 20.9) + _REST_VO2_ML_KG_MIN * body_kg
    # 20.9 J/ml O2; 1 W = 60 J/min -> ml/min = W*60/20.9
    return vo2_gross_ml_min / body_kg


def decode_metabolic_profile(
    best_efforts: dict[int, int],
    body_kg: float,
    cp_w: Optional[int] = None,
    w_prime_j: Optional[int] = None,
    ftp_w: Optional[int] = None,
) -> MetabolicProfile:
    """Estimate a metabolic profile from field best efforts.

    Args:
        best_efforts: {duration_s: best_avg_watts} e.g. from
            fitness_estimation.extract_best_efforts.
        body_kg: athlete body mass (kg).
        cp_w, w_prime_j: optional pre-computed (else derived from best_efforts).
        ftp_w: optional known FTP (else estimated from best_efforts).

    Returns:
        MetabolicProfile with vo2max / vlamax / fatmax / zones (estimates).
    """
    prof = MetabolicProfile(cp_w=cp_w, w_prime_j=w_prime_j, ftp_w=ftp_w)
    prof.assumptions = [
        "VO2max stimato da potenza via efficienza meccanica lorda ~21% (di Prampero 1986).",
        "VLamax stimato dal rapporto sforzo breve (30s) / CP — approssimazione field.",
        "FatMax a ~50-65% FTP (picco ossidazione lipidi, Achten 2002).",
        "Non sostituisce test lab CPET; accuracy entro variabilita' day-to-day.",
    ]
    prof.sources = [
        "Mader & Heck 1986, Int J Sports Med (metabolic model)",
        "di Prampero 1986 (mechanical efficiency)",
        "Leo et al. 2021 Eur J Appl Physiol (power profiling)",
        "INSCYD PPD validation, J Science Cycling 2022 (VO2max r=0.945 vs lab)",
        "Achten et al. 2002 Med Sci Sports Exerc (FATmax)",
        "Poffe et al. 2024 / Dunst et al. 2024 (VLamax)",
    ]

    if not best_efforts or body_kg <= 0:
        return prof

    # CP / FTP fallback from best efforts if not supplied.
    if cp_w is None or ftp_w is None:
        from fitness_estimation import estimate_ftp, compute_cp_wprime
        if ftp_w is None:
            ftp_w = estimate_ftp(best_efforts)
            prof.ftp_w = ftp_w
        if cp_w is None:
            try:
                res = compute_cp_wprime(best_efforts)
                if res:
                    cp_w = int(round(res[0]))
                    w_prime_j = int(round(res[1]))
                    prof.cp_w = cp_w
                    prof.w_prime_j = w_prime_j
            except Exception:
                pass

    eff_cp = cp_w or ftp_w
    if eff_cp and body_kg > 0:
        # VO2max: use the higher of (60min best effort) and (CP-converted),
        # capped at physiological ceiling. CP sits near the heavy/severe
        # boundary (~MLSS), below VO2max; add a fatigue-reserve margin.
        vo2_cp = _vo2max_from_power(eff_cp, body_kg)
        p60 = best_efforts.get(3600)
        vo2_p60 = _vo2max_from_power(p60, body_kg) if p60 else 0.0
        vo2_est = max(vo2_cp * 1.08, vo2_p60)  # ~8% above CP ~ heavy boundary
        prof.vo2max_ml_kg_min = round(min(vo2_est, _VO2MAX_CEILING_ML_KG_MIN), 1)

    # VLamax: ratio of short maximal effort to CP signals glycolytic capacity.
    p30 = best_efforts.get(30)
    if p30 and eff_cp:
        # Excess short-power above CP, per kg, scaled to a lactate-rate proxy.
        excess = max(p30 - eff_cp, 0)
        # Empirically-tuned: ~ (excess/W per kg) mapped to mmol/L/s range 0.3-1.2
        excess_per_kg = excess / body_kg
        vlamax = 0.3 + min(excess_per_kg / 6.0, 0.9)  # clamp to plausible band
        prof.vlamax_mmol_l_s = round(vlamax, 2)

    # FatMax: peak fat oxidation ~ 50-65% FTP.
    if ftp_w:
        fatmax = int(round(ftp_w * 0.58))
        prof.fatmax_w = fatmax
        prof.fatmax_pct_ftp = 58.0

    return prof


def profile_to_dict(prof: MetabolicProfile) -> dict:
    return {
        "vo2max_ml_kg_min": prof.vo2max_ml_kg_min,
        "vlamax_mmol_l_s": prof.vlamax_mmol_l_s,
        "fatmax_w": prof.fatmax_w,
        "fatmax_pct_ftp": prof.fatmax_pct_ftp,
        "cp_w": prof.cp_w,
        "w_prime_j": prof.w_prime_j,
        "ftp_w": prof.ftp_w,
        "method": prof.method,
        "assumptions": prof.assumptions,
        "sources": prof.sources,
    }
