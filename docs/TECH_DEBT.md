# Tech Debt — VELARCO (fork VELARCO)

Audit del 2026-07-25 (deep-scan + verifica incrociata con un altro LLM).
I bug **funzionali** (crash/valori sballati) sono stati fixati in `training_planner.py`,
`app.py`, `plan_options.py`, `release.yml`, `installer.nsi` — vedi commit di fix.
Qui sotto il **debito strutturale** (non blocca il rilascio, ma va affrontato prima
di scaleggiare il codebase).

---

## 1. `except … pass` silenziosi (83 in `app.py` + 10 in `training_planner.py`)

**Rischio:** errori reali nascosti (es. fallimenti di sync ICU, parse JSON, write file).
**Stato:** molti sono legittimi (daily_log mancante → ritorna 0; tipo sconosciuto →
fallback). Alcuni nascondono bug.

**Top pericolosi da auditare (candidati a `_log.warning` invece di `pass`):**
- handler API che swallowano `Exception` senza log → crash silenziosi nell'UI
- percorsi di save/load piano (un piano non salvato non deve passare inosservato)
- sync ICU (un 401 deve essere visibile, non `pass`)

**Piano:** grep `except[^:]*:\s*pass`, per ognuno decidere:
- suppressor legittimo → lascia + commento `# noqa`
- nasconde errore → sostituisci `pass` con `_log.warning(...)` o rilancia

**Non fare:** rimuovere tutti i `pass` a calci — romperebbe la suite (101 fail pre-esistenti
già monitorati). Intervenire per classe di errore, con test.

---

## 2. `config.__getattr__` magic proxy (`config.py:95`)

**Rischio:** spelling error su `config.NOME` → `AttributeError` generico, debug più lento.
**Stato:** design intenzionale (risolve valori per-profile da `ProfileManager` lazy).
Non è un bug — è documentato. Lasciare com'è; non refattorizzare (romperebbe tutti i
`config.ATHLETE_*` esistenti senza beneficio funzionale).

---

## 3. 217 `fetch()` inline in `dashboard.html`

**Rischio:** nessun client API centralizzato → URL硬编码, gestione errori duplicata,
impossibile intercettare 401/gateway.
**Piano (future, richiede suite front-end verde):**
- estrarre `api.get(path)`, `api.post(path, body)` in `static/js/api.js`
- un solo `catch` che gestisce 401 (re-auth ICU) e 500 (banner)
- sostituire i 217 `fetch` gradualmente per feature, non in un colpo solo

---

## 4. File monolitici

`app.py` 22.137 righe · `training_planner.py` 13.604 · `dashboard.html` 21.623
(totale 57.364 delle ~80K del repo).

**Rischio:** merge conflict, build lento, diff illeggibili.
**Piano (future):** split `app.py` per dominio (auth, plan, ride, nutrition, ocr)
in package `api/`, mantenendo gli stessi endpoint. Richiede la suite verde PRIMA
(oggi 101 fail noti da risolvere prima di splittare).

---

## Priorità

| # | Item | Impatto | Sforzo | Quando |
|---|------|---------|--------|--------|
| 1 | `except…pass` pericolosi | medio | medio | dopo aver azzerato i 101 fail noti |
| 2 | `config.__getattr__` | basso | n/a | non toccare |
| 3 | fetch centralizzati | medio | alto | con suite FE verde |
| 4 | split monoliti | alto | alto | dopo 1+3 |

---

## Risolti in questa sessione (debito documentato → fixato)

- ✅ `docs/SYSTEM.md` drift (Flask/WebSocket/ANT+/ERG → FastAPI, file inesistenti rimossi)
- ✅ `requirements.txt` upper bounds troppo stretti (`<0.140` escludeva FastAPI 0.140.0,
  `<0.40` escludeva uvicorn 0.51.0) → allargati a `<1.0`
- ✅ OAuth secret: documentato il rischio + confermato `.oauth.env` git-ignored
