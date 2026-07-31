![PCC](assets/ppc_logo.png)

# PCC Pro — Adaptive Cycling Intelligence

**Pianificatore di allenamento ciclistico adattivo, locale, che chiude il loop tra ciò che hai programmato e ciò che hai realmente fatto — con nutrizione, forza, mobilità e body-composition integrati.**

> **PCC** (Power Curve Coach): il nome evoca la *power-duration curve*, il cuore scientifico del pianificatore — la curva che descrive quanto riesci a produrre per quanto tempo. Il logo unisce quell'arco ascendente a una ruota, con il gradiente teal→amber della palette.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-green) ![Version](https://img.shields.io/badge/Version-v5.4.2-brightgreen) ![License](https://img.shields.io/badge/License-Apache--2.0-blue) ![Tests](https://img.shields.io/badge/Tests-2974%2B-passing-green)

> Latest: **[v5.4.2 — Accorgimenti persistiti: forza/mobilità/nutrizione sopravvivono agli auto-update**](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.4.2)

> ⚠️ **Fork italiano di PCC** (Apache-2.0, `platypus45`). Questa è una versione derivata: stessa architettura di pianificazione adattiva, ma con motore nutrizione/integrazione riscritto, import BIA da PDF, sync estensibile verso Intervals.icu e altre app, UI in italiano e auto-aggiornamento. Il credito all'autore originale è in [`NOTICE`](NOTICE).

---

## Novità v5.4.2 — Accorgimenti persistiti

| Feature | Descrizione |
|---------|-------------|
| 🔧 **Accorgimenti che sopravvivono** | Forza, mobilità, nutrizione e integratori NON vengono più azzerati da auto-update, ricalcoli e reforecast (`_apply_plan_options_future` su tutti i path + round-trip completo delle note) |
| 💾 **Flag persistiti** | I `plan_options` vengono salvati nel piano → ogni rigenerazione rilegge gli stessi flag |
| 🎨 **UI coerente** | Card "Forza & Mobilità" con ID univoci + `syncCardFlags()`; Nutrizione/Integrazione chiuse di default; forza/mobilità OFF di default |
| 📤 **Push completo** | `load_plan_weeks()` include le sessioni → il push su intervals.icu non invia più 0 eventi |

**Verificato E2E:** genera piano con flag → 4 forza + 4 mobilità + 18 note nutrizione + 7 integratori → update tier `rebalanced` → tutti preservati → push `/api/icu/push` → `pushed=4 updated=9 deleted=2`.

---

## Novità v5.4.0 — ICU push per-sessione + Forza/Mobilità opt-in

| Feature | Descrizione |
|---------|-------------|
| 📅 **Push piano su intervals.icu** | `/api/icu/push` usa il motore `reconcile()`: pusha ogni singola seduta (ciclismo, forza, mobilità, running, MTB) con file ZWO verbatim (potenza) o FIT HR-target (HR), upsert bulk idempotente, orphan sweep |
| ⚙️ **Forza & Mobilità opt-in** | Checkbox nella card Home rispettate da `loadStrength()`/`injectMultidiscipline()` e dal backend |
| 🔗 **Vedi su intervals.icu** | Bottone nel calendario "Il mio calendario" → `https://intervals.icu/athlete/<id>/calendar` |

---

## Novità v5.3.9 — Setup auto-sync da Intervals.icu

| Feature | Descrizione |
|---------|-------------|
| 🏷️ **Day label esplicito** | Ogni giorno nel calendario mostra "OGGI — SWEET SPOT" oppure "Sat 18 Jul — TEMPO · in 2 days" — mai confusione su quale giorno stai guardando |
| 🔄 **Home card fresh** | Dopo un re-fit del piano, la home card si aggiorna automaticamente — niente più sessione stale |
| 🔔 **Upstream Domestique check** | Badge nella toolbar che controlla automaticamente se Domestique (upstream) ha rilasciato nuove versioni, classifica il rischio (safe/review/break) e cliccando apre la release su GitHub |
| 🌱 **Fresh legs FTP test** | Backport pulito da Domestique v3.7.0: il giorno prima di un FTP test viene forzato a Recovery (se non già easy) |
| ✅ **Jump-to-today** | Già presente: "Vai a oggi" scrolla il calendario alla settimana corrente |
| 💡 **Explainer bottoni** | Già presenti: ogni azione nel calendario ha tooltip descrittivo |

**Backend:** `upstream_check.py` + `UPSTREAM_BASE` + endpoint `/api/upstream/check` — confronto automatico tra la versione fork (v3.5.2) e l'ultima release upstream.

---

## Novità v5.3.7 — Home UI fix

| Fix | Descrizione |
|-----|-------------|
| 🔧 **Tab switch** | Rimosso `}catch(_){}` orfano che bloccava TUTTI i listener JS — ora i tab funzionano |
| 📊 **Dati home a cold start** | `loadProDashboard()` richiamato all'avvio (bootstrap della tab attiva) — le card si popolano all'apertura |
| 🧩 **Card dentro `sec-home`** | `</div>` spurio spostava le card fuori dalla sezione home rendendole persistenti su tutte le tab |
| 🔗 **Mappatura API** | `/api/wellness` (lista) e `/api/readiness` (campi nidificati) letti correttamente |

## Novità v5.3.8 — Card layout + plan push fix

| Fix | Descrizione |
|-----|-------------|
| 📐 **Card responsive** | Rimosso `resize:both`/`min-width:280px` — le card home si accostano automaticamente, niente resize manuale bloccato |
| 🔄 **TSS chart** | Grafico settimanale non riempie più lo schermo (aspect-ratio fisso + cap asse Y) |
| ⬆️ **Push piano ICU** | `load_plan_weeks()` leggeva `current_plan.json` (prima chiamava una funzione senza argomenti e falliva sempre) — il piano viene ora pushato su Intervals.icu |

## Novità v5.3.9 — Setup auto-sync da Intervals.icu

| Fix | Descrizione |
|-----|-------------|
| 🔗 **Setup intelligente** | Se Intervals.icu è collegato, il setup estrapola le attività automaticamente (`POST /api/sync`) invece di chiedere import FIT manuale |
| 📥 **Fallback manuale** | Se ICU non è collegato, resta l'import manuale del FIT |
| 🏷️ **Gap dinamico** | Il gap "activities" mostra "Sincronizza attività da Intervals.icu" quando linked |

---

## Novità v5.3.5 — Fresh Legs before FTP Test

| Fix | Descrizione |
|-----|-------------|
| 🦵 **Fresh legs prima FTP test** | La funzione `_ensure_fresh_legs_before_ftp_tests` forza un giorno di Recovery prima dei test FTP a metà ciclo (backport clean-room da Domestique v3.7.0) |
| 🧊 **Cooldown verificato** | Script `fix_cooldowns_pcc.py` (dry-run su 4200+ workout: 0 fix — la libreria PCC era già corretta) |

**Test:** 38/38 passati.

---

## Novità v5.3.x — Pro Experience

La versione **Pro** (v5.3.x) eleva l'interfaccia a standard da software professionale (TrainingPeaks / Intervals.icu / WKO), mantenendo il motore di pianificazione adattiva identico.

**Dashboard interattiva**
- **Griglia dashboard ridimensionabile** (`pro-dashboard-grid`): ogni widget si può **ridimensionare** e **riordinare via drag-and-drop**, con persistenza in `localStorage`.
- **Card KPI animate**: forma/fatica, TSB, CTL/ATL, carico settimanale — con micro-animazioni e hover-lift.
- **Grafici Chart.js locali** (offline, nessun CDN): Power Curve con zoom interattivo, Fitness/TSS interattivi, TSS settimanale.
- **Badge tipo atleta** (Scalatore / Sprinter / All-rounder / Cronoman / Intermedio / Amatoriale) + **raccomandazioni IA** di focus allenamento.
- **Timeline stagione drag-and-drop**: riordina eventi/blocchi trascinandoli.
- **Tema racing** (palette teal→amber, sidebar tab a sinistra, header sticky frosted-glass).
- **PWA**: manifest + service worker → installabile e usabile offline dal browser.
- **Radar metabolico animato** a 5 assi con score normalizzato 0–100.

**Parser BIA ibrido (v5.3.4):**
Il flusso `parse_bia_pdf` gestisce ogni tipo di PDF futuro:
1. **PDF testuale** → parsing regex diretto
2. **PDF scansionato + chiave cloud** → modello vision (z.ai/OpenAI) → **JSON strutturato**
3. **PDF scansionato senza chiave** → OCR Tesseract offline

**Auto-aggiornamento quotidiano (v5.2.5 → v5.3.x):**
Il piano si adatta automaticamente dopo ogni sync, con semaforo fatica, FTP continuo, decoder metabolico INSCYD-style, modelli CP multipli, field-test FTP e export bundle.

---

## Sicurezza & OAuth (Intervals.icu)

L'integrazione Intervals.icu usa il flusso **OAuth 2.0 installed-app** (public client, senza PKCE): il `client_id` è pubblico e il `client_secret` è bundlato nel eseguibile (`pcc.spec` include `.oauth.env`). Questo è il pattern standard per le app desktop installate presso un provider che non emette segreti per-utente; il secret non garantisce accesso a dati altrui e può essere revocato dal pannello Intervals.icu in qualsiasi momento. Il file `.oauth.env` è git-ignored (mai nel repository).

**Indice:** [TL;DR](#tldr) · [Perché esiste](#perché-esiste) · [Cosa è cambiato rispetto a PCC](#cosa-è-cambiato-rispetto-a-domestique) · [Avvio rapido](#avvio-rapido) · [Motore Nutrizione & Integrazione](#motore-nutrizione--integrazione) · [Body Composition (BIA)](#body-composition-bia) · [Sync & Altre app](#sync--altre-app) · [Planner adattivo](#planner-adattivo) · [Auto-aggiornamento](#auto-aggiornamento) · [Architettura](#architettura) · [La scienza](#la-scienza) · [Release](#release) · [Licenza](#licenza--attribuzione)

> Approfondimento: la logica completa del planner, le formule e la tabella delle referenze citate sono in [**docs/SCIENCE.md**](docs/SCIENCE.md).

---

## TL;DR

PCC è un planner ciclistico **localhost-only** che:

- Include **4.200+ workout ZWO strutturati** e **622 route virtuali** (ereditati dalla libreria PCC);
- Importa i tuoi **FIT post-uscita** e **muta la prescrizione del giorno successivo** da ogni segnale che la pedalata ha esposto (TSS overshoot, breach di polarizzazione, DFA α1, decoupling aerobico, monotonia Foster, drift eFTP, composite Hooper, overload glicolitico);
- Aggiunge un **motore nutrizione & integrazione** completo: TDEE (Mifflin-St Jeor), macro su base scientifica, compensazione al carico, dosi supplementi calcolate sul peso e race-fueling;
- Inietta **forza e mobilità** direttamente nel piano (protocolli per fase);
- Supporta **multi-disciplina** (ciclismo / running / MTB / swim) — TSS cross-sport coerente;
- Importa **BIA da PDF** (anche scansionati) e sincronizza peso/% grassa su Intervals.icu;
- Si collega a **Intervals.icu** e ad **altre app** tramite layer di sync estensibile;
- Si **auto-aggiorna** dalla release GitHub (Windows `/S` silenzioso, macOS `.dmg`);
- **Controlla upstream Domestique** per nuove release e valuta il rischio di merge.

Hardware-agnostic: genera ZWO, pedali in MyWhoosh / Tacx / Zwift / Hammerhead / outdoor, re-importi il FIT. Nessun power meter? Modalità a frequenza cardiaca. Un atleta, nessun cloud, nessun telemetry.

---

## Perché esiste

La maggior parte delle app di allenamento cade in due modalità:

- **Solo display**: widget HRV, curve di fitness Banister, anelli di polarizzazione — grafici bellissimi, zero feedback comportamentale.
- **Solo calendario**: un piano fisso di 12 settimane che non sa cosa hai realmente fatto ieri.

PCC (come PCC da cui deriva) è diverso: ogni segnale che tocca la dashboard ha anche un code-path che muta una sessione futura. Aggiunge, rispetto all'originale, un motore nutrizione/integrazione e forza/mobilità **integrati nel piano** invece di essere fogli di calcolo separati.

Sette guardrail scientifici (G1–G7) ereditati, ciascuno con citazione, più una fase di consolidamento di 1 settimana alla fine di ogni ciclo non-evento (Mujika 2010).

---

## Cosa è cambiato rispetto a PCC

PCC parte da PCC 3.5.2 e aggiunge/riscrive:

| Area | Domestique 3.5.2 | PCC Pro |
|------|------------------|---------|
| **Lingua UI** | Inglese | Italiano (termini di dominio in EN: CTL, TSS, FTP, W/kg, VO2max, ZWO, FIT, rMSSD, DFA α1) |
| **Motore nutrizione** | Note generiche per fase | Motore completo: `nutrition.py` (TDEE Mifflin-St Jeor, macro obiettivo, compensazione carico, race-fueling, `diet.py` pasti/grammi) |
| **Integrazione** | — | Protocolli Gruppo A evidence-based con **dosi calcolate sul peso** (Jeukendrup/UCI 2026, PMC12239112) |
| **Forza & Mobilità** | — | Modulo `strength_mobility.py` + endpoint che **iniettano** sedute nel piano per fase |
| **Body Composition** | — | Import **BIA da PDF** (ibrido cloud vision + OCR Tesseract), storico + sync ICU |
| **Sync** | Intervals.icu (solo attività) | ICU + **layer estensibile** `sync_targets.py` (plugin per altre app) |
| **Multi-disciplina** | Ciclismo centrale | Campo `disciplines` profilo (cycling/running/mtb/swim/strength/mobility) |
| **Upstream check** | — | `upstream_check.py` + badge UI: controlla release upstream e classifica rischio merge |
| **Auto-aggiornamento** | Banner "update disponibile" | **Install reale** da GitHub Releases (`/api/self-update`) |
| **Palette / Dashboard** | Blu originale | Teal/amber, dashboard ridimensionabile, card riordinabili, radar metabolico |
| **Brand** | Domestique | PCC — Power Curve Coach (omaggio in NOTICE + header) |
| **Build** | `domestique.spec` | `pcc.spec`, installer NSIS `PCC-Setup.exe`, CI macOS `.dmg` |

**Non abbiamo rimosso** la logica di pianificazione adattiva di Domestique (guardrail G1–G7, ricalibrazione FTP a metà ciclo, micro-intervalli 30/15 Rønnestad, 4×8 Seiler, polarizzazione, ACWR Gabbett). PCC la estende.

---

## Avvio rapido

```bash
# Sviluppo / web app
pip install -r requirements.txt
python run_web.py                 # apre http://localhost:8080 nel browser

# Build desktop (EXE Windows)
pyinstaller pcc.spec --clean --noconfirm
# → dist/PCC/PCC.exe  (poi: makensis installer.nsi → PCC-Setup-<ver>.exe)

# Build desktop (macOS .dmg) — richiede macOS
bash build_mac.sh                # → dist/PCC.app + PCC.dmg
```

I dati utente restano in `~/.domestique/` (intenzionalmente non rinominato, così piani e connessioni ICU sopravvivono agli aggiornamenti).

---

## Motore Nutrizione & Integrazione

Modulo [`nutrition.py`](nutrition.py) + [`diet.py`](diet.py). **Single source of truth**: un solo motore calcola, gli altri moduli sono viste.

- **TDEE** via Mifflin-St Jeor (1995) × fattore attività (1.2–1.9).
- **Obiettivi**: `cut` (deficit 300–500 kcal, Mountjoy 2018 IOC), `maintain`, `gain` (surplus).
- **Compensazione al carico**: macro che tengono conto di TSS di oggi + ieri.
- **Dosi integrazione calcolate sul peso**: caffeina 3–6 mg/kg, beta-alanina, nitrato, bicarbonato, creatina, glicerolo (Gruppo A, Jeukendrup/UCI 2026).
- **Race fueling**: carboidrati durante sforzo in base a durata e peso.

Tutte le funzioni hanno test: `tests/test_fase1_nutrition_strength.py`, `tests/test_diet_parser.py`.

---

## Body Composition (BIA)

Modulo [`bia_parser.py`](bia_parser.py) + layer cloud vision opzionale [`bia_vision.py`](bia_vision.py). Import di misurazioni da **PDF di bioimpedenziometria** (AKERN Biavector, InBody, Tanita, BODYGRAM):

- **Flusso ibrido** (massima affidabilità su tutti i PDF futuri):
  1. **PDF testuale** → parsing regex diretto;
  2. **PDF scansionato + chiave cloud** → modello vision (z.ai/OpenAI) → **JSON strutturato**;
  3. **PDF scansionato senza chiave** → OCR Tesseract (fallback offline).
- **Parser regex robusto**: normalizzazione virgola→punto, pattern unit-aware, sanity-check post-estrazione.
- **12–22 campi** da un singolo PDF: peso, altezza, BMI, massa grassa/magra, TBW, ECW/ICW, idratazione, BCM, SMM, ASMM, PhA, CHI.
- **Storico** salvato e **sync su Intervals.icu** (peso + % grassa).

Config cloud vision (`.env`):
```bash
BIA_VISION_API_KEY=sk-...
BIA_VISION_BASE_URL=https://api.z.ai/v1
BIA_VISION_MODEL=glm-4v-flash
```
Test: `tests/test_bia_parser.py` — 7 passed.

---

## Sync & Altre app

Modulo [`sync_targets.py`](sync_targets.py) — astrazione a **plugin** (`SyncTarget`) con registry. Intervals.icu è il primo target registrato; aggiungere TrainingPeaks, Google Fit, Strava o un export JSON locale significa solo registrare una nuova destinazione. Sync bidirezionale ICU: attività, calendario (push sessioni pianificate), e BIA.

---

## Domestique Upstream Check

Modulo [`upstream_check.py`](upstream_check.py) + `UPSTREAM_BASE` (v3.5.2). A ogni avvio, PCC controlla l'ultima release di **platypus45/domestique** su GitHub e la confronta con la versione base:

- ✅ **Safe** — fix isolati (cooldown, fresh legs) → merge pulito
- ⚠️ **Review** — modifiche a `training_planner.py` → valutare manualmente
- 🔴 **Break** — riscrittura massiva → review approfondita

Un **badge UI** nella toolbar del calendario mostra l'esito. Cliccando si apre la release su GitHub. Endpoint: `/api/upstream/check`.

---

## Planner adattivo

Il planner legge ogni mattina HRV (vs baseline), forma e deficit di zona, e muta la prescrizione:

- **Soreness ≥ 6/7** → VO2max diventa recupero (Hooper & Mackinnon 1995).
- **TSS reale > 1.5× pianificata** → budget -15% (Gabbett 2016, ACWR 0.8–1.3).
- **Z5+ rolling 48h ≥ 25 min** → oggi forzato Z2 (Hulin et al. 2014).
- **DFA α1 medio < 0.5 su 3 uscite** → soglia swap a Z2 (Rogers et al. 2021).
- **Ricalibrazione FTP a metà ciclo** con fresh legs (Allen & Coggan).
- **Micro-intervalli 30/15 Rønnestad**, **4×8 Seiler**, polarizzazione 80/5/15.

Fasi: BASE / BUILD1 / BUILD2 / PEAK / TAPER o CONSOLIDATION (Mujika 2010).

---

## Auto-aggiornamento

L'app controlla `releases/latest` a ogni avvio (cache 6h). Se c'è una versione più nuova:
- **Windows**: download `PCC-Setup-<ver>.exe` → installer NSIS silenzioso (`/S`).
- **macOS**: monta `PCC.dmg` (trascina in Applicazioni).

Endpoint: `POST /api/self-update` (verificato, test `tests/test_self_update.py`).

---

## Architettura

- `app.py` — backend FastAPI (endpoint pianificazione, nutrizione, BIA, sync, self-update, upstream check)
- `training_planner.py` — motore piano (CTL/TSB, fasi, blocchi, guardrail G1–G7)
- `nutrition.py` / `diet.py` — nutrizione & integrazione
- `upstream_check.py` — controllo upstream Domestique
- `strength_mobility.py` — forza/mobilità
- `bia_parser.py` / `bia_vision.py` — import BIA ibrido
- `diet_parser.py` — import dieta da PDF
- `sync_targets.py` — layer sync estensibile (plugin)
- `plan_export.py` — export PDF/HTML
- `templates/dashboard.html` — UI (italiano, palette teal/amber)
- `.github/workflows/build-macos.yml` — CI build `.dmg`
- `UPSTREAM_BASE` — versione fork Domestique tracciata

Dati in `~/.domestique/`; nessun cloud.

---

## La scienza

Ogni regola del planner cita uno studio. Tabella completa e formule in [**docs/SCIENCE.md**](docs/SCIENCE.md). Riferimenti chiave:

- **Rønnestad 2014/2020** — micro-intervalli 30/15 (+12% FTP).
- **Seiler** — 4×8 min (top FTP/VO2max builder).
- **Gabbett 2016** — ACWR 0.8–1.3.
- **Hulin et al. 2014** — fatica neuromuscolare.
- **Rogers et al. 2021** — DFA α1 < 0.5.
- **Hooper & Mackinnon 1995 / Cheung 2003** — sorezza periferica.
- **Mujika 2010** — consolidazione post-ciclo.
- **Mifflin & St Jeor 1995** — TDEE.
- **Burke 2018 / Mountjoy 2018 (IOC)** — nutrizione, deficit.
- **Jeukendrup / UCI 2026 / PMC12239112** — integrazione Gruppo A.

---

## Release

Tutte le release: [github.com/quadrellif90-collab/pcc-cycling-coach/releases](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases)

| Versione | Piattaforma | Note |
|----------|-------------|------|
| **v5.3.9** (Latest) | Win / macOS | [Setup auto-sync da Intervals.icu](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.9) |
| v5.3.8 | Win / macOS | [Card layout + plan push fix](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.8) |
| v5.3.7 | Win / macOS | [Home UI fix](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.7) |
| v5.3.6 | Win / macOS | [UI fixes + upstream Domestique check](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.6) |
| v5.3.5 | Win / macOS | [Fresh legs FTP test](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.5) |
| v5.3.4 | Win / macOS | [Parser BIA ibrido (cloud vision + Tesseract)](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.4) |
| v5.3.3 | Win / macOS | [Fix BIA AKERN + virgola decimale](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.3) |
| v5.3.2 | Win / macOS | [BIA OCR su PDF scansionati](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.2) |
| v5.3.1 | Win / macOS | [Fix auto-update + layout](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.1) |
| v5.3.0 | Win / macOS | [PCC Pro: radar animato, Chart.js, drag-drop](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.3.0) |
| v5.2.5 | Win / macOS | [Daily-sync, INSCYD, profilo metabolico](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.5) |
| v5.2.4 | Win / macOS | [Fix self-update + i18n](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.4) |
| v5.2.3 | Win / macOS | [Release notes + design system](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.3) |
| v5.2.2 | Win / macOS | [Fix planner + nutrizione](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.2) |
| v5.2.1 | Win / macOS | [Fix sync ICU](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.1) |
| v5.2.0 | Win / macOS | [12 nuove funzioni + Design System Pro](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.0) |
| v5.1.0 | Win / macOS | [Rebrand + ricerca WorldTour + auto-update](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.1.0) |
| v5.0.0 | Win / macOS | [Selettore di accomodamenti + OCR](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.0.0) |
| v4.4.0 | Win / macOS | [OAuth persistente, profili, motore runway-aware](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v4.4.0) |
| v4.0.0 | Win / macOS | [Fork italiano di Domestique + auto-update](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v4.0.0) |

Auto-update: Windows (`PCC-Setup*.exe /S`), macOS (monta `.dmg`).

---

## Licenza & attribuzione

Apache-2.0 — vedi [`LICENSE`](LICENSE) e [`NOTICE`](NOTICE).

PCC è un **fork di PCC** (`platypus45`, Apache-2.0). Tutto il merito per il codebase originale, il build system e buona parte del motore di scienza dell'allenamento va agli autori originali di PCC. PCC aggiunge: motore nutrizione/integrazione, forza/mobilità, BIA, sync estensibile, upstream check, UI italiana, auto-update.

Tacx, Wahoo, Garmin, Polar, MyWhoosh, Zwift, Golden Cheetah, Rouvy, Intervals.icu sono marchi dei rispettivi proprietari.

---

## Abbreviazioni

| Sigla | Significato |
|-------|-------------|
| **TSS** | Training Stress Score |
| **CTL / ATL / TSB** | Chronic / Acute Training Load / Stress Balance |
| **FTP** | Functional Threshold Power |
| **W/kg** | Watt per kg di peso corporeo |
| **VO2max** | Massimo consumo di ossigeno |
| **BIA** | Bioelectrical Impedance Analysis |
| **DFA α1** | Detrended Fluctuation Analysis alpha1 |
| **ACWR** | Acute:Chronic Workload Ratio |
| **ICU** | intervals.icu |

---

*Costruito con ricerca PubMed, 4.200+ workout e profondo amore per il ciclismo — fork italiano di Domestique.*

Copyright (c) 2026 PCC contributors (fork of Domestique, Apache-2.0).