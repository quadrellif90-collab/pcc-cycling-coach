"""Test isolati per il parser BIA (ibrido: regex NutriCoach + cloud vision)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from bia_parser import parse_bia_text, parse_bia_vision_json, BIAReading, _norm


def test_norm_decimal_preservation():
    """_norm NON deve fondere la virgola decimale (75,2 -> 75.2 non 752)."""
    assert "75.2" in _norm("Peso: 75,2 kg")
    assert "13.1" in _norm("Massa Grassa 13,1 kg")


def test_akern_text_unit_aware():
    """Il parser distingue kg/% e non confonde FM kg con FM %."""
    txt = """Peso: 71.4 kg
Altezza: 168.0 cm
BMI: 25.3 kg/m2
Massa Grassa (FM) 14.6 kg 8.7 kg/m
Massa Magra (FFM) 56.8 kg 33.8 kg/m
Idratazione tissutale 73.1% (TBW/FFM)
Angolo di Fase (PhA) 7.4 °
Indice nutrizionale (CHI) 109.16"""
    res = parse_bia_text(txt)
    f = res["fields"]
    assert abs(f["weight_kg"] - 71.4) < 0.1
    assert abs(f["fat_mass_kg"] - 14.6) < 0.1
    assert abs(f["fat_free_mass_kg"] - 56.8) < 0.1
    assert abs(f["height_cm"] - 168.0) < 0.1


def test_akern_ocr_litre_comma_loss():
    """OCR perde la virgola sui litri (43.0L -> 430L): sanity-check /10."""
    txt = """Acqua Totale (TBW) 430L 25.6 l/m
Acqua Intra Cellulare (ICW) 253L 58.8%
Idratazione tissutale 731% (TBW/FFM)"""
    res = parse_bia_text(txt)
    f = res["fields"]
    # tbw 430 -> 43.0 (corretto via /10)
    assert abs(f["tbw_l"] - 43.0) < 0.5
    assert abs(f["icw_l"] - 25.3) < 0.5


def test_ecw_gt_tbw_fix():
    """Se ECW > TBW (rumore OCR 177 invece di 17.7), correggi ECW=TBW-ICW."""
    txt = """Acqua Totale (TBW) 43.0 L
Acqua Extra Cellulare (ECW) 177 L
Acqua Intra Cellulare (ICW) 25.3 L"""
    res = parse_bia_text(txt)
    f = res["fields"]
    # ECW 177 -> 43.0-25.3 = 17.7
    assert abs(f["ecw_l"] - 17.7) < 0.5


def test_chi_not_from_maschile():
    """'chi' in 'Maschile' non deve essere scambiato per l'indice CHI."""
    txt = "Sesso: Maschile\nIndice nutrizionale (CHI) 109.16"
    res = parse_bia_text(txt)
    f = res["fields"]
    # deve prendere 109.16 da (CHI), non 15 da Maschile
    assert f.get("chi") is None or abs(f["chi"] - 109.16) < 1


def test_vision_json_maps_and_fixes_decimal():
    """JSON vision: mappa campi e corregge virgola persa (1091.6 -> 109.16)."""
    data = {"weight_kg": 71.4, "fat_mass_kg": 14.6, "chi": 1091.6,
            "tbw_l": 43.0, "phase_angle": 7.4}
    res = parse_bia_vision_json(data)
    f = res["fields"]
    assert abs(f["weight_kg"] - 71.4) < 0.01
    assert abs(f["chi"] - 109.16) < 0.01
    assert abs(f["tbw_l"] - 43.0) < 0.01


def test_validated_fields_range():
    r = BIAReading(weight_kg=70.0, fat_mass_pct=186.0, hydration_pct=731.0)
    v = r.validated_fields()
    assert "weight_kg" in v
    assert "fat_mass_pct" not in v
    assert "hydration_pct" not in v
