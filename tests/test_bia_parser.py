"""Test isolati per il parser BIA (validazione range fisiologico).

Verificano che i report AKERN Biavector (dove il primo numero dopo
l'etichetta e' il valore di riferimento, non la misurazione, e la
virgola decimale italiana puo' sparire) non producano valori
impossibili salvati silenziosamente.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bia_parser import parse_bia_text, BIAReading


def test_akern_text_rejects_out_of_range():
    """Valori AKERN sbagliati (riferimento invece di misurazione) vengono scartati."""
    fake = """
Peso: 70.3 kg
Altezza: 168.0 cm
BMI: 24.9 kg/m
Massa Grassa (FM) 131 kg 78 kg/m 18 28 5.6 9.5 13.3
Massa Magra (FFM) 572 kg 34.0 kg/m
Idratazione tissutale 731% (TBW/FFM)
Angolo di Fase (PhA) 76
Indice nutrizionale (CHI) 1052.3
"""
    res = parse_bia_text(fake)
    validated = res["found_fields"]
    rejected = set(res["rejected_fields"])
    # Campi corretti mantenuti
    assert "weight_kg" in validated
    assert abs(res["reading"]["weight_kg"] - 70.3) < 0.01
    assert "height_cm" in validated
    assert "bmi" in validated
    # Campi assurdi scartati
    assert "fat_mass_kg" in rejected
    assert "fat_mass_pct" in rejected
    assert "fat_free_mass_kg" in rejected
    assert "hydration_pct" in rejected
    assert "chi" in rejected
    assert "phase_angle" in rejected
    # Nessun valore > 200 nei campi validati
    for k, v in res["reading"].items():
        if k in validated and isinstance(v, (int, float)):
            assert v <= 200, f"{k}={v} non dovrebbe essere validato"


def test_clean_text_keeps_all_fields():
    """Report con valori plausibili: tutto validato, niente scartato."""
    clean = """
Peso: 71.4 kg
Altezza: 168.0 cm
BMI: 25.3 kg/m
Massa Grassa (FM): 14.2 kg
Massa Magra (FFM): 57.2 kg
Idratazione tissutale: 73.1% (TBW/FFM)
Angolo di Fase (PhA): 6.5
Indice nutrizionale (CHI): 109.1
"""
    res = parse_bia_text(clean)
    assert res["unreliable"] is False
    assert "fat_mass_kg" in res["found_fields"]
    assert abs(res["reading"]["fat_mass_kg"] - 14.2) < 0.01
    assert abs(res["reading"]["hydration_pct"] - 73.1) < 0.01
    assert not res["rejected_fields"]


def test_validated_fields_range():
    r = BIAReading(weight_kg=70.0, fat_mass_pct=186.0, hydration_pct=731.0)
    v = r.validated_fields()
    assert "weight_kg" in v
    assert "fat_mass_pct" not in v   # 186% impossibile
    assert "hydration_pct" not in v   # 731% impossibile
