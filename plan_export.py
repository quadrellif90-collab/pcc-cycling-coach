# Copyright 2024-2026 PCC — Performance Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""BETA Fase 7c — Compositore piano integrato + export HTML/PDF.

Raccoglie da un unico piano: ciclismo (training_planner / goal), Forza (7a),
Mobilità (7a), Nutrizione (7b) e produce un documento HTML autonomo e
stampabile (CSS @media print) → esportabile in PDF dal browser.

Nessuna dipendenza esterna: l'HTML è self-contained e si apre ovunque.
Il coach (verticale coach) usa lo stesso documento per consegnarlo all'atleta.
"""

from __future__ import annotations
from typing import Optional


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build_plan_html(athlete_name: str = "Atleta", goal_name: str = "",
                    cycling_weeks: list = None,
                    strength_plan: list = None, strength_summary: dict = None,
                    mobility_plan: list = None,
                    nutrition_day: dict = None, supplements: list = None,
                    race_fueling: dict = None) -> str:
    """Ritorna una stringa HTML completa del piano integrato."""
    cycling_weeks = cycling_weeks or []
    strength_plan = strength_plan or []
    mobility_plan = mobility_plan or []
    supplements = supplements or []

    # ── Ciclismo ──
    cy_rows = ""
    for w in cycling_weeks:
        sess = w.get("sessions") or w.get("sessions_info") or []
        sess_txt = ", ".join(
            (s.get("session_type") or s.get("type") or "session")
            for s in sess[:12]
        ) or "—"
        cy_rows += (f"<tr><td>Sett. {_esc(w.get('week_num', w.get('week', '')))}</td>"
                    f"<td>{_esc(w.get('phase', ''))}</td>"
                    f"<td>{_esc(round(w.get('tss_target', 0) or 0))} TSS</td>"
                    f"<td>{_esc(sess_txt)}</td></tr>")

    # ── Forza ──
    st_rows = ""
    for w in strength_plan:
        if not w.get("sessions"):
            st_rows += f"<tr><td>Sett. {_esc(w.get('week',''))}</td><td colspan='3'>Scarico / nessuna seduta</td></tr>"
            continue
        for s in w["sessions"]:
            st_rows += (f"<tr><td>Sett. {_esc(w.get('week',''))}</td>"
                        f"<td>{_esc(s.get('exercise',''))}</td>"
                        f"<td>{_esc(s.get('sets',''))}×{_esc(s.get('reps',''))}</td>"
                        f"<td>{_esc(s.get('pct_1rm',''))}% 1RM</td></tr>")

    # ── Mobilità ──
    mob_items = ""
    if mobility_plan:
        seq = mobility_plan[0].get("sequence", [])
        mob_items = "".join(f"<li>{_esc(x.get('exercise',''))} ({_esc(x.get('duration_s',0))} s)</li>" for x in seq)
    mob_block = f"<p>Routine {_esc(mobility_plan[0].get('minutes',15))} min/giorno: <ul>{mob_items}</ul></p>" if mob_items else ""

    # ── Nutrizione ──
    nut_block = ""
    if nutrition_day:
        nut_block = (f"<p><b>{_esc(nutrition_day.get('label',''))}</b><br>"
                     f"Carboidrati: {_esc(nutrition_day.get('daily_g',''))} "
                     f"({_esc(nutrition_day.get('daily_g_per_kg',''))})<br>"
                     f"Durante sforzo: {_esc(nutrition_day.get('during_g',0))} g "
                     f"({_esc(nutrition_day.get('during_range_g_per_h',''))})<br>"
                     f"<span style='font-size:11px;color:#666;'>{_esc(nutrition_day.get('note',''))}</span></p>")
    sup_block = ""
    if supplements:
        sup_block = "<p><b>Supplement (Gruppo A, evidence-based):</b></p><ul>" + "".join(
            f"<li><b>{_esc(s.get('name',''))}</b> [{_esc(s.get('evidence',''))}] — "
            f"{_esc(s.get('protocol',''))}. {_esc(s.get('caution',''))}</li>"
            for s in supplements) + "</ul>"

    race_block = ""
    if race_fueling:
        race_block = (f"<p><b>Piano di gara ({_esc(race_fueling.get('duration_h',''))} h):</b> "
                      f"{_esc(race_fueling.get('carb_per_h_g',''))} g/h carboidrati "
                      f"(tot {_esc(race_fueling.get('carb_total_g',''))} g, "
                      f"{_esc(race_fueling.get('carb_total_g_per_kg',''))} g/kg), "
                      f"caffeina {_esc(race_fueling.get('caffeine_mg',''))} mg pre-gara.<br>"
                      f"<span style='font-size:11px;color:#666;'>{_esc(race_fueling.get('source',''))}</span></p>")

    html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Piano integrato — {_esc(athlete_name)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; color:#1a1a1a; max-width:820px; margin:24px auto; padding:0 16px; }}
  h1 {{ font-size:22px; border-bottom:3px solid #2d7d46; padding-bottom:6px; }}
  h2 {{ font-size:16px; color:#2d7d46; margin-top:22px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:6px; }}
  th, td {{ border:1px solid #ccc; padding:5px 8px; text-align:left; }}
  th {{ background:#f0f0f0; }}
  ul {{ margin:4px 0; padding-left:18px; font-size:12px; }}
  .meta {{ color:#666; font-size:12px; }}
  .footer {{ margin-top:24px; font-size:10px; color:#999; border-top:1px solid #eee; padding-top:8px; }}
  @media print {{ body {{ margin:0; }} h2 {{ page-break-after:avoid; }} }}
</style></head>
<body>
  <h1>Piano di preparazione integrato</h1>
  <p class="meta">Atleta: <b>{_esc(athlete_name)}</b> · Obiettivo: {_esc(goal_name)}</p>

  <h2>1. Ciclismo</h2>
  <table><thead><tr><th>Settimana</th><th>Fase</th><th>Carico</th><th>Sessioni</th></tr></thead>
  <tbody>{cy_rows or "<tr><td colspan='4'>Piano non disponibile</td></tr>"}</tbody></table>

  <h2>2. Forza in palestra</h2>
  {f"<p class='meta'>{_esc(strength_summary.get('sessions_per_week',''))}×/sett, {_esc(strength_summary.get('sets',''))}×{_esc(strength_summary.get('reps',''))} al {_esc(strength_summary.get('pct_1rm',''))}% 1RM — {_esc(strength_summary.get('source',''))}</p>" if strength_summary else ""}
  <table><thead><tr><th>Settimana</th><th>Esercizio</th><th>Serie×Rip</th><th>%1RM</th></tr></thead>
  <tbody>{st_rows or "<tr><td colspan='4'>—</td></tr>"}</tbody></table>

  <h2>3. Mobilità</h2>
  {mob_block or "<p>—</p>"}

  <h2>4. Nutrizione &amp; Integrazione</h2>
  {nut_block or ""}
  {race_block}
  {sup_block or ""}

  <div class="footer">Generato da PCC — Performance Cycling Coach · Fonti: Llanos-Lagos 2025, Warneke 2025,
  GSSI SSE 231, Jeukendrup/UCI Sports Nutrition Project 2026, PMC12239112.</div>
</body></html>"""
    return html
