"""Deep-scan riproduzione + regression test per i bug trovati il 2026-07-25.

Bug coperti:
  B1 (crash 500): api_climb_zwo chiama api_course_profile (endpoint FastAPI
      che ritorna JSONResponse) e ne usa .get() -> AttributeError.
      Fix: estrarre la logica in _course_profile_dict() che ritorna dict.
  B2 (layer morto): _apply_dfa_durability richiede duration_min>=120 ma il
      planner emette al piu' 105 min -> durability_note sempre 0.
      Fix: soglia allineata ai dati reali (es. >=75 min per sessioni lunghe)
      OPPURE rimuovere il vincolo di durata e basarsi solo sul session_type.
  B3 (flag azzerati): PlanOptions(enable_heat=True) senza mode -> is_normal
      True e tutti i flag azzerati silenziosamente.
      Fix: from_dict/tipo accettano flag espliciti anche senza mode='accorgimenti'.
"""

import sys
import pytest

sys.path.insert(0, ".")

import plan_options as PO
import training_planner as tp
from datetime import date


def test_b3_planoptions_flag_without_mode_not_cleared():
    """B3: passare flag=True senza mode non deve azzerarli."""
    opts = PO.PlanOptions(enable_heat=True, enable_altitude=True)
    # Oggi: is_normal diventa True e i flag spariscono.
    # Dopo il fix: se almeno un flag e' esplicitamente True, mode deve essere
    # trattato come 'accorgimenti' (non normal).
    assert opts.enable_heat is True, "flag enable_heat azzerato senza mode"
    assert opts.enable_altitude is True, "flag enable_altitude azzerato senza mode"
    assert opts.is_normal is False, "is_normal True nonostante flag espliciti"


def test_b2_durability_note_emitted_for_long_sessions():
    """B2: il layer durability deve produrre almeno una nota su un piano reale."""
    goal = tp.Goal(goal_type="event", target_date=date(2026, 8, 30),
                   target_ftp=243, target_weight_kg=70)
    opts = PO.PlanOptions(mode="accorgimenti", enable_dfa_durability=True)
    _, weeks = tp.generate_plan(goal=goal, plan_options=opts)
    dur = sum(1 for w in weeks for s in w.sessions if getattr(s, "durability_note", ""))
    # Il planner emette sessioni <=105min; il layer deve usare una soglia
    # coerente (es. >=75min o solo session_type) e non >=120.
    assert dur > 0, "durability_note sempre 0: soglia 120 non allineata ai dati (max 105)"


def test_b1_climb_zwo_no_attributeerror():
    """B1: api_climb_zwo non deve crashare con AttributeError su JSONResponse."""
    import app as appmod
    # Usa un corso inesistente: il layer deve gestire 404 senza .get() su Response
    try:
        resp = appmod.api_climb_zwo("nonexistent_region", "nofile.zwo")
    except AttributeError as e:
        pytest.fail(f"api_climb_zwo crash AttributeError: {e}")
    # Se il corso non esiste, deve ritornare un JSONResponse 404, non crashare.
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
