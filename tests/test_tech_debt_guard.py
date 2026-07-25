"""Guard test: il debito di `except Exception: pass` senza log non deve crescere.

I 67 (app.py) + N (training_planner.py) suppressor silenziosi sono debito noto
(vedi docs/TECH_DEBT.md). Questo test congela il COUNT attuale: se qualcuno
aggiunge un nuovo `except Exception: pass` senza `_log`/`logger`, il test fallisce
e costringe a gestire l'errore (o a documentarlo con `# noqa`). Non rimuoviamo i
vecchi a calci perche' alcuni sono suppressor legittimi e la suite ha 101 fail noti.
"""

import re

MAX_SILENT_EXCEPT = 67  # app.py: count al 2026-07-25 (deve solo scendere)


def _count_silent_except(path: str) -> int:
    lines = open(path, encoding="utf-8").read().splitlines()
    n = 0
    for i, l in enumerate(lines):
        if re.search(r"except\s+(Exception|BaseException|:)\s*:", l):
            nxt = " ".join(lines[i + 1:i + 3])
            if "pass" in nxt and "_log" not in nxt and "logger" not in nxt:
                n += 1
    return n


def test_app_py_silent_except_count_frozen():
    got = _count_silent_except("app.py")
    assert got <= MAX_SILENT_EXCEPT, (
        f"app.py ha {got} except Exception:pass silenziosi "
        f"(soglia {MAX_SILENT_EXCEPT}). Se ne hai rimosso uno, abbassa la soglia; "
        f"se ne hai aggiunto uno, gestisci l'errore o documenta con # noqa."
    )
