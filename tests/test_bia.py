"""Test PPC — import/sync BIA + integrazione Intervals.icu."""
import os
from fastapi.testclient import TestClient
import app as app_mod
from bia_parser import parse_bia_text, parse_bia_pdf, to_icu_wellness, BIAReading

client = TestClient(app_mod.app)

# Il PDF di test e' fuori da PPC (in .hermes). Risali da PPC -> Desktop/PPC/.hermes
_HERE = os.path.dirname(__file__)
_PPC = os.path.dirname(_HERE)
_DESKTOP = os.path.dirname(_PPC)
BIA_PDF = os.path.join(_DESKTOP, ".hermes", "desktop-attachments",
                        "Report utente - F.Q. - 18-06-2026.pdf")

# Valori reali dal report BODYGRAM/AKERN (Filippo Quadrelli, 15/06/2026)
SAMPLE_TEXT = """
Peso: 71.4 kg
Altezza: 168.0 cm
BMI: 25.3
Massa Grassa (FM): 14.6 kg
Massa Magra (FFM): 56.8 kg
Acqua Totale (TBW): 43.0 L
Acqua Extra Cellulare (ECW): 17.7 L
Acqua Intra Cellulare (ICW): 25.3 L
Idratazione tissutale: 73.1%
Massa Cellulare (BCM): 29.3 kg
Massa Muscolo-Scheletrica (SMM): 32.2 kg
Massa Muscolare Appendicolare (ASMM): 24.5 kg
Angolo di Fase (PhA): 7.4 gradi
Indice nutrizionale (CHI): 1091.6
"""


def test_parser_text_extracts_fields():
    r = parse_bia_text(SAMPLE_TEXT)
    assert r["scanned"] is False
    d = r["reading"]
    assert abs(d["weight_kg"] - 71.4) < 0.1
    assert abs(d["fat_mass_kg"] - 14.6) < 0.1
    assert abs(d["smm_kg"] - 32.2) < 0.1
    assert d["fat_mass_pct"] is not None
    assert abs(d["fat_mass_pct"] - 20.4) < 0.5


def test_parser_pdf_scanned_detected():
    if not os.path.exists(BIA_PDF):
        return
    pdf = open(BIA_PDF, "rb").read()
    r = parse_bia_pdf(pdf)
    assert r["scanned"] is True
    assert r["reading"]["source"] == "pdf_scanned"


def test_icu_payload_mapping():
    r = parse_bia_text(SAMPLE_TEXT)["reading"]
    r["date"] = "2026-06-15"
    icu = to_icu_wellness(BIAReading(**r), "2026-06-15")
    p = icu["payload"]
    # Intervals.icu /wellness-bulk accepts ONLY weight + bodyFat for this
    # athlete: pctBodyFat, muscleMass, hydration, bmi -> 422 Unprocessable.
    # Verified end-to-end with real PUT (200 OK). See bia_parser.to_icu_wellness.
    assert p["weight"] == 71.4
    assert p["bodyFat"] == 20.4
    assert "hydration" not in p
    assert "muscleMass" not in p
    assert "bmi" not in p
    assert icu["date"] == "2026-06-15"


def test_endpoint_bia_import_json():
    res = client.post("/api/bia-import", json={
        "date": "2026-06-15", "weight_kg": 71.4, "bmi": 25.3,
        "fat_mass_kg": 14.6, "smm_kg": 32.2, "hydration_pct": 73.1})
    assert res.status_code == 200, res.text
    j = res.json()
    assert j["ok"] is True
    assert j["history_count"] >= 1
    assert j["icu_payload"]["payload"]["weight"] == 71.4


def test_endpoint_bia_history():
    client.post("/api/bia-import", json={"date": "2026-06-16", "weight_kg": 70.0})
    res = client.get("/api/bia-history")
    assert res.status_code == 200
    j = res.json()
    assert j["ok"] is True
    assert j["count"] >= 1


def test_endpoint_bia_sync_no_creds():
    res = client.post("/api/bia-sync-icu", json={})
    assert res.status_code == 200
    j = res.json()
    assert "ok" in j
