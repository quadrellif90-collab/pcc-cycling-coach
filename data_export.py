"""PCC 5.x — Export bundle (portabilità / backup, principio "tutto incorporato").

Genera un archivio ZIP locale-first contenente:
  * profile.json        — atleta + impostazioni (da ProfileManager)
  * metrics.csv         — tutte le metriche storiche (da db.query_metric_history)
  * field_tests.json    — risultati field test (se presenti)
  * cpep_history.json   — test lab CPET/INSCYD (se presenti)
  * pedal_asymmetry.json— asimmetrie pedala (se presenti)
  * custom_charts.json  — grafici definiti (se presenti)
  * plan/current_plan.json — piano corrente (se presente)
  * .domestique/        — copia integrale della cartella profilo (backup grezzo)

Tutto offline, solo stdlib (zipfile). Nessun upload cloud. Il file viene
salvato in una cartella export del profilo e restituito come download.

Single source of truth: legge dagli stessi store del resto dell'app
(ProfileManager, db, file JSON già scritti dalle altre viste).
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional


def _profile_dir() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        return Path.home() / ".domestique" / "profiles" / aid
    except Exception:
        return None


def build_metrics_csv() -> str:
    """Return CSV of all tracked metrics (metric,date,value,source,notes)."""
    try:
        import db
        rows = db.get_db().execute(
            "SELECT metric, date, value, source, notes FROM athlete_metrics ORDER BY metric, date"
        ).fetchall()
        lines = ["metric,date,value,source,notes"]
        for r in rows:
            notes = (r.get("notes") or "").replace('"', '""')
            lines.append(f'{r["metric"]},{r["date"]},{r["value"]},{r.get("source","")},"{notes}"')
        return "\n".join(lines)
    except Exception:
        return "metric,date,value,source,notes\n"


def build_bundle() -> tuple[bytes, str]:
    """Build the export ZIP in memory. Returns (zip_bytes, filename)."""
    pdir = _profile_dir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # profile
        try:
            from profile_manager import ProfileManager
            prof = ProfileManager.get().to_dict() if hasattr(ProfileManager.get(), "to_dict") else {}
            if not prof:
                import os
                aj = pdir / "athlete.json"
                if aj.exists():
                    prof = json.loads(aj.read_text(encoding="utf-8"))
            z.writestr("profile.json", json.dumps(prof, indent=2, ensure_ascii=False))
        except Exception:
            z.writestr("profile.json", "{}")
        # metrics csv
        z.writestr("metrics.csv", build_metrics_csv())
        # json sidecars already written by other views
        for name in ["field_tests.json", "cpep_history.json",
                     "pedal_asymmetry_history.json", "custom_charts.json"]:
            fp = pdir / name
            if fp.exists():
                z.writestr(name, fp.read_text(encoding="utf-8"))
        # current plan
        cp = pdir / "plan" / "current_plan.json"
        if cp.exists():
            z.writestr("plan/current_plan.json", cp.read_text(encoding="utf-8"))
        # raw backup of full profile dir (exclude the zip itself)
        if pdir and pdir.exists():
            written = set(z.namelist())
            sidecars = {"field_tests.json", "cpep_history.json",
                        "pedal_asymmetry_history.json", "custom_charts.json",
                        "injury_blocks.json"}
            for f in pdir.rglob("*"):
                if f.is_file():
                    rel = str(f.relative_to(pdir))
                    if rel in written or rel in sidecars:
                        continue
                    try:
                        z.writestr(rel, f.read_bytes())
                    except Exception:
                        pass
    stamp = _stamp()
    return buf.getvalue(), f"pcc_export_{stamp}.zip"


def _stamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
