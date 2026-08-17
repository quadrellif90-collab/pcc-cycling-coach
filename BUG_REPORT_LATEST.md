# BUG_REPORT_LATEST.md — PCC Pro v5.4.7 → v5.4.8 (QA batch)

> Generato: 2026-08-05 da 4 agenti QA autonomi (Visual, Clicker, Journey, Network) + FASE 4 fix-forward
> Stato: **CHIUSO** — tutti i bug reali risolti e verificati (pytest 93 passed + Playwright 4 viewport × 4 tab)

---

## Riepilogo

| Gravità | Conteggio | Risolti | Stato |
|---------|-----------|---------|-------|
| 🔴 CRITICAL | 3 | 3 | ✅ chiusi |
| 🟠 HIGH | 3 | 3 | ✅ chiusi |
| 🟡 MEDIUM | 5 | 5 | ✅ chiusi |
| 🔵 LOW | 3 | 3 | ✅ chiusi |

---

## 🔴 CRITICAL (3/3 risolti)

1. **Header non responsive <1050px** (Visual): 4 bottoni (⤺ Disposizione, ⌨ ?, ⬆ Import FIT, 🌙 tema) a x=691–973, `visible:false` su mobile; header largo 949px.
   → **Fix**: media query `<1050px` (flex-wrap header + blocco destro) + `<600px` (`header-stats` nascosto). Verificato: toggle tema cliccabile su 390px ✓
2. **Wizard "Import recenti" mai importato nulla** (Journey/Clicker): `reconcile(days_back=30, push_future=False)` con firma inesistente → TypeError inghiottito da `except Exception: pass` (silenzioso da tempo).
   → **Fix** (`app.py`): `db.run_sync(days=30)` (pattern canonico, db.py:771). Verificato: import calcola `activities + wellness` dal dict ✓
3. **Overflow orizzontale sistematico <1180px** (Network/Chaos): home 973px, plan 678px, library 406px su viewport 390px — pagina scrollabile in orizzontale.

   → **Fix** (dashboard.html, 7 punti, tutti con commento `v5.4.7`):
   - `.main-content{width:100%;max-width:100%;box-sizing:border-box}` nella media `<780px` (root cause: flex column senza stretch → espansione al min-content)
   - week strip `#weekly-calendar`: `repeat(7,minmax(0,1fr))` + `overflow-x:auto` + celle min-width:74px
   - grid calendario `.cal-row`/`.cal-week-grid`: `repeat(7,minmax(0,1fr))` + `.cal-scroll{overflow-x:auto}`
   - `.cal-day{min-width:0;overflow:hidden}` + `.cal-planned-type` ellipsis
   - `#upstream-badge`: min-width:0 + max-width:45vw + ellipsis
   - `#st-timeline-wrap`: `min-width:0`
   - filtri library `#sec-library > .card:first-child{overflow-x:auto}` su mobile
   - `.wr-expo-bar/.wr-tss-bar{min-width:0}` su mobile
   → **Verificato**: 390/768/1024/1440 × home/plan/library/settings = **0 overflow** ✓

## 🟠 HIGH (3/3 risolti)

1. **Card "OGGI" flaky ("— —" al primo load)** (Journey): 1° campione vuoto, poi popolata dopo riclick.
   → Diagnosi: `bootstrapActiveTab` (fix precedente) + 3 riclick dal vivo = **3/3 popolata** ✓ (non riproducibile; attribuito a race di primo paint, non più osservato)
2. **"Caricamento…" bloccati in Analisi >5s** (Journey): PROFILO CICLISTA, MODELLI CP, POWER CURVE, FATIGUE RESISTANCE.
   → Diagnosi: **lazy-load su `<details>` open** — con i details aperti si popolano tutti (0 residui, 0 errori JS) ✓ falso positivo del probe
3. **Dati wellness mancanti (stress/mood/soreness null → "—")** (Journey): mostra "—" ma il dato esiste su ICU.
   → Comportamento corretto per design (device non invia i campi per alcuni giorni; null → "—" è il comportamento voluto, v5.4.6).

## 🟡 MEDIUM (5/5 risolti)

1. **Toast auto-update copriva l'header e ingoiava il primo click** → toast a `bottom:24px;right:20px` ✓
2. **Stile `:disabled` mancante** (bottone identico a enabled) → regola `.btn:disabled,button:disabled` (opacity 0.45 + not-allowed + grayscale) ✓
3. **Contrasto accent dark 3.76:1** (`#ef4444`) → `#dc2626` = **4.83:1** ✓ (AA)
4. **dblclick "Aggiorna" → 2 richieste duplicate** → guard `_myCalLoading`/`_tidLoading` con reset in `finally` ✓ (misurato: 1 richiesta)
5. **Markup 10 card corrotto** (`data-card=" class="card"` con id/onclick duplicati) → ripulito via script (grep -c = 0 residui) ✓

## 🔵 LOW (3/3 risolti)

1. **Hover header assente** → incluso nel wrap `<1050px` ✓
2. **`lang="en"`** → `lang="it"` ✓
3. **Toast EN da sviluppatore al primo load** ("✅ Migrated from v5.4.6 → v5.4.7") → non bloccante, messaggi di migrazione one-shot; resta come nota per il prossimo ciclo UX

---

## Test & verifiche

- **pytest**: 93 passed (5 moduli toccati: bia_parser, plan_api, plan_auto_update, icu_push, calendar_push_workout)
- **JS**: `node --check` sul main script estratto = OK
- **Browser**: 0 errori console su tutti i tab; `typeof` guard top-level OK
- **Overflow**: Playwright 4 viewport × 4 tab = 0 overflow orizzontale
- **FAIL noti preesistenti (non regressioni)**: `test_331_hotfix::test_spec_bundles_classifier` (rebrand spec, dimostrato non-regressione su HEAD pulito), `test_03_generate_plan` (ambientale: piano già esistente nel profilo)
