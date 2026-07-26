"""Test PCC — parser PDF dieta + endpoint nutrizione/dieta."""
import os
from fastapi.testclient import TestClient
import app as app_mod

# diet_parser
from diet_parser import parse_diet_pdf, parse_diet_text, nutrition_for

# Il PDF di test e' fuori da PCC (in .hermes). Risali da PCC -> Desktop/PCC/.hermes
_HERE = os.path.dirname(__file__)
_PCC = os.path.dirname(_HERE)
_DESKTOP = os.path.dirname(_PCC)
PDF_PATH = os.path.join(_DESKTOP, ".hermes", "desktop-attachments", "Filippo estate.pdf")

client = TestClient(app_mod.app)


def test_nutrition_for_known():
    kc, c, p, f = nutrition_for("pane comune")
    assert kc == 265
    # sconosciuto -> tutti zero (non inventa)
    assert nutrition_for("alimento_inesistente_xyz") == (0, 0, 0, 0)


def test_parser_counts_7_days():
    if not os.path.exists(PDF_PATH):
        return
    data = open(PDF_PATH, "rb").read()
    s = parse_diet_pdf(data)
    assert s["day_count"] == 7, f"attesi 7 giorni, ho {s['day_count']}"
    assert s["pages"] == 9
    assert s["unknown_foods"] == [], s["unknown_foods"]


def test_parser_alternatives_marked():
    text = "Lunedì\nColazione\nPane comune 50 g\no Pane integrale 59 g\nUova 100 g\n"
    s = parse_diet_text(text)
    d = s["days"][0]
    items = d.meals[0].items
    primaries = [i for i in items if not i.is_alternative]
    alts = [i for i in items if i.is_alternative]
    assert len(primaries) == 2  # pane comune + uova
    assert len(alts) == 1       # pane integrale
    assert alts[0].name == "Pane integrale"


def test_parser_macros_primary_only():
    text = "Lunedì\nColazione\nPane comune 100 g\no Pane integrale 120 g\n"
    s = parse_diet_text(text)
    d = s["days"][0]
    t = d.totals(primary_only=True)
    # solo pane comune 100g -> 265 kcal/100g * 1 = 265
    assert abs(t["kcal"] - 265) < 1, t
    t2 = d.totals(primary_only=False)
    assert t2["kcal"] > t["kcal"]


def test_endpoint_diet_pdf_import():
    if not os.path.exists(PDF_PATH):
        return
    data = open(PDF_PATH, "rb").read()
    r = client.post("/api/diet-pdf-import",
                    files={"file": ("diet.pdf", data, "application/pdf")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["day_count"] == 7
    assert "summary" in j
    assert len(j["summary"]) == 7
    assert "kcal" in j["summary"][0]


def test_endpoint_nutrition_auto():
    r = client.get("/api/nutrition-auto?goal_type=cut")
    assert r.status_code == 200, r.text
    j = r.json()
    assert "macros" in j
    assert "auto" in j
    assert j["macros"]["carb_g"] > 0


def test_endpoint_inject_multidiscipline():
    client.post("/api/profile",
                 json={"disciplines": ["cycling", "running", "mtb", "strength", "mobility"]})
    r = client.post("/api/plan/inject-multidiscipline", data={"phase": "base"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["disciplines"], "discipline lette dal profilo"
