# MEMORY.md — Mappa Architettura & Logica di Business

> Generato: 2026-08-05 · Branch `pro` · v5.4.7 · Repo: quadrellif90-collab/pcc-cycling-coach (Domestique fork)

## Stack & Avvio

- **Backend**: FastAPI + SQLite + uvicorn, Python 3.11 (venv `.venv/Scripts/` su Windows)
- **Frontend**: vaniglia JS + HTML in `templates/dashboard.html` (file unico ~23k righe), Chart.js locale (`static/vendor`), PWA manifest in `static/manifest.json`
- **Avvio**: `PORT=8092 .venv/Scripts/python.exe run_web.py` (web mode). `launcher.py` = app desktop
- **Nessuno stack node**: non esistono package.json / docker-compose / Makefile
- **Regola QA**: dopo ogni modifica backend → riavviare uvicorn; dopo patch a `dashboard.html` → `git diff` per verificare che il patch tool non abbia strippato DOM/attributi

## Moduli principali (62 moduli .py)

| Modulo | Ruolo |
|--------|-------|
| `app.py` | Routing FastAPI + business logic + UI layer (~23k righe) |
| `training_planner.py` | Motore di pianificazione: generazione piano, fasi, settimane, adattamento |
| `training.py` | Integrazioni (Intervals.icu sync, wellness, fit upload) |
| `db.py` | SQLite: accesso dati, `post_sync_callback`, query wellness/activities |
| `profile_manager.py` | Profili utente, retarget `PLAN_DIR` per profilo, `.env` per-profilo, `_persist_env()` |
| `icu_calendar_push.py` | Push piano → calendario Intervals.icu (reconcile/sweep, horizon derivato dal piano) |
| `config.py` | Credenziali da `.oauth.env` (ICU/Terra), token |
| `diet.py` / `nutrition.py` / `diet_parser.py` | Piano alimentare |
| `bia_parser.py` / `bia_vision.py` / `ocr_pdf.py` | BIA ibrido (cloud + Tesseract OCR) |
| `continuous_policy.py` / `plan_options.py` | Pianificazione continua / opzioni piano |
| `readiness.py` / `readiness_composite.py` / `sleep.py` | Readiness composita |
| `fit_activity.py` / `ride_storage.py` / `power_curve.py` | Attività, salvataggio uscite, curve potenza |
| `calendar_ics.py` / `plan_export.py` / `data_export.py` | Export |
| `release_validator.sh` | Audit 10-fasi pre-release (già esistente, v5.3.16+) |

## Endpoint API principali

- `/api/version` — versione da `VERSION` (fonte unica)
- `/api/plan` / `/api/plan/update` — piano attivo, aggiornamento
- `/api/activities` / `/api/wellness` — uscite e wellness (Intervals/Terra → SQLite → API)
- `/api/icu/push` (GET status / POST push) — push piano su Intervals.icu; toggle sync
- `/api/calendar/push-workout` — push singolo workout (planner/library)
- `/oauth/icu/*`, `/api/icu/status|sync|disconnect` — pattern integrazioni OAuth per-profilo
- `/api/terragroup/*` — Terra API (Huawei Health)
- `/api/settings` — profilo: weight/FTP/LTHR/FCmax

## Logica di business chiave

- **Piano calendario Intervals.icu** (v5.4.7): orizzonte push derivato dal PIANO (`_plan_horizon_days`), non fisso 14g — un piano event-target che inizia in futuro viene caricato interamente; auto-update giornaliero via `_icu_push_daily_from_sync` (post_sync_callback) + debounce post-write; toggle OFF → `sweep_all()` con orizzonte derivato → elimina TUTTO il piano caricato
- **external_id** = `domestique:<profile_id>:<day_iso>:<n>`; manual = `domestique-manual:` (mai cancellato dal sweep)
- **Workout classification** content-based da `workouts/.content_classification.json` (non filename-based, v4.1.2)
- **Card "Come stai"** (v5.4.6): stress/mood/soreness/HRV-SDNN/SpO₂/sonno da wellness ICU, sparkline 7g + semaforo
- **Attività**: NP/IF/VI/decoupling/max_power nel payload (top-level o `raw_json` fallback)
- **Trainer hardware**: RIMOSSO da v4.0.0 — niente bleak/pycycling/FTMS
- **Piano**: `~/.domestique/profiles/<name>/plans/current_plan.json` (il file root `~/.domestique/plans/` è artefatto stantio)

## UI / UX

- Italiano, tema racing, sidebar #d5ede8, toggle dark/light (dark default), Montis-style shadows/hover
- Pattern: `apiJson()` con AbortController 10s, toast per errori (mai `catch(_){}` muto), `pccConfirm` al posto di confirm(), skeleton shimmer, micro-copy IT
- Checkbox card: `card-*` sincronizzate con `po-*` via `syncCardFlags()` (v5.4.4)

## QA / Test

- `pytest` (core: ~100+ test; alcuni test live/network vanno esclusi con `-k "not live and not network"` o timeout)
- `tests/e2e/` — test end-to-end su server live (ambientali)
- NOTA: `tests/test_331_hotfix.py::test_spec_bundles_classifier` legge `velarco.spec` → FAIL preesistente (rebrand a `pcc.spec`, commit 204fbd24) — da sistemare o ignorare
- NOTA: riga ~23268 di app.py chiama `reconcile(days_back=30, push_future=False)` — firma inesistente, bug latente (setup wizard)
- Playwright disponibile nel venv per E2E browser

## Release

- `VERSION` file → commit → push `pro` → tag `vX.Y.Z` → workflow GitHub `release.yml` (EXE + NSIS + smoke test) → `gh release create` con `PCC-Setup-X.Y.Z.exe`
- Verificare SEMPRE `gh run list` dopo il tag (v5.4.5 non triggerò; fallback `gh workflow run`)
- CI auto-release su tag; asset: `PCC-Setup-<ver>.exe` (~108MB)
