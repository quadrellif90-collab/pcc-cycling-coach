![PCC](assets/ppc_logo.png)

# PCC — Adaptive Cycling Intelligence

**Pianificatore di allenamento ciclistico adattivo, locale, che chiude il loop tra ciò che hai programmato e ciò che hai realmente fatto — con nutrizione, forza, mobilità e body-composition integrati.**

> **PCC** (VELocità + ARCO di potenza): il nome evoca la *power-duration curve*, il cuore scientifico del pianificatore — la curva che descrive quanto riesci a produrre per quanto tempo. Il logo unisce quell'arco ascendente a una ruota, con il gradiente teal→amber della palette.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-green) ![Version](https://img.shields.io/badge/Version-v5.2.0-brightgreen) ![License](https://img.shields.io/badge/License-Apache--2.0-blue) ![Fork](https://img.shields.io/badge/Fork%20of-PCC-orange)

Latest: **[v5.2.0 — Design System Pro + 12 nuove funzioni](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases/tag/v5.2.0)**

> ⚠️ **Fork italiano di PCC** (Apache-2.0, `platypus45`). Questa è una versione derivata: stessa architettura di pianificazione adattiva, ma con motore nutrizione/integrazione riscritto, import BIA da PDF, sync estensibile verso Intervals.icu e altre app, UI in italiano e auto-aggiornamento. Il credito all'autore originale è in [`NOTICE`](NOTICE).

---


### Sicurezza & OAuth (Intervals.icu)

L'integrazione Intervals.icu usa il flusso **OAuth 2.0 installed-app** (public client, senza PKCE): il `client_id` è pubblico e il `client_secret` è bundlato nel eseguibile (`pcc.spec` include `.oauth.env`). Questo è il pattern standard per le app desktop installate presso un provider che non emette segreti per-utente; il secret non grantisce accesso a dati altrui e può essere revocato dal pannello Intervals.icu in qualsiasi momento. Il file `.oauth.env` è git-ignored (mai nel repository). Non è un segreto a elevata sensibilità (non è una password utente, non è una API key cloud privata).

**Indice:** [TL;DR](#tldr) · [Perché esiste](#perché-esiste) · [Cosa è cambiato rispetto a PCC](#cosa-è-cambiato-rispetto-a-domestique) · [Avvio rapido](#avvio-rapido) · [Motore Nutrizione & Integrazione](#motore-nutrizione--integrazione) · [Forza & Mobilità](#forza--mobilità) · [Multi-disciplina](#multi-disciplina) · [Body Composition (BIA)](#body-composition-bia) · [Sync & Altri sport/app](#sync--altre-app) · [Planner adattivo](#planner-adattivo) · [Auto-aggiornamento](#auto-aggiornamento) · [Architettura](#architettura) · [La scienza](#la-scienza) · [Release](#release) · [Licenza](#licenza--attribuzione)

> Approfondimento: la logica completa del planner, le formule e la tabella delle referenze citate sono in [**docs/SCIENCE.md**](docs/SCIENCE.md).

---

## TL;DR

PCC è un planner ciclistico **localhost-only** che:

- Include **4.200+ workout ZWO strutturati** e **622 route virtuali** (ereditati dalla libreria PCC);
- Importa i tuoi **FIT post-uscita** e **muta la prescrizione del giorno successivo** da ogni segnale che la pedalata ha esposto (TSS overshoot, breach di polarizzazione, DFA α1, decoupling aerobico, monotonia Foster, drift eFTP, composite Hooper, overload glicolitico);
- Aggiunge un **motore nutrizione & integrazione** completo: TDEE (Mifflin-St Jeor), macro su base scientifica, compensazione al carico ("fuel for the work required"), dosi supplementi calcolate sul peso e race-fueling;
- Inietta **forza e mobilità** direttamente nel piano (protocolli per fase);
- Supporta **multi-disciplina** (ciclismo / running / MTB / swim) — il TSS di una corsa dura conta come quello di una salita;
- Importa **BIA da PDF** (bioimpedenziometria, anche scansionati) e sincronizza peso/% grassa su Intervals.icu;
- Si collega a **Intervals.icu** e a **altre app** tramite un layer di sync estensibile;
- Si **auto-aggiorna** dalla release GitHub (Windows installer silenzioso, macOS `.dmg`).

Hardware-agnostic: genera ZWO, pedali in MyWhoosh / Tacx / Zwift / Hammerhead / outdoor, re-importi il FIT. Nessun power meter? Una modalità a frequenza cardiaca prescrive range bpm invece di watt. Un atleta, nessun cloud, nessun telemetry.

---

## Novità v5.2

La release **v5.2.0-beta.2** porta PCC a un livello professionale sia funzionale che visivo. Tutte le funzioni sono **viste sul motore unico di pianificazione** (single source of truth): nessun motore parallelo, nessun numero divergente.

**12 nuove funzioni (tutte verificate end-to-end):**
- **#1 Semaforo fatica** — segnale di fatica composito nel readiness.
- **#2 FTP continuo** — stima FTP ad ogni uscita (motore esistente, ora esposto).
- **#3 Decoder metabolico** — da power-duration + peso stima VO2max / VLamax / FatMax.
- **#4 Modelli CP multipli** — Monod 2-param + Morton 3-param + Progression Levels.
- **#5 Classificazione & RPE** — tipo di sessione da IF + rilevamento RPE atleta + replan guidato.
- **#6 Import lab test** — parser CPET / INSCYD da PDF (+ import FIT già presente).
- **#7 Grafici personalizzati** — metriche derivate da formula sicura (no eval) sullo store metriche.
- **#8 Asimmetrie pedala / LEOMO MPI** — L-R / torque effectiveness / pedal smoothness.
- **A — Field-test FTP** — stima FTP da 20min / ramp / 4×8min / 4×4min (chiude il loop #2).
- **B — Export bundle** — ZIP portabile (profilo + metriche + sidecar + backup `~/.domestique`).
- **C — Calendario .ics** — feed webcal per importare il piano in Google / Outlook / Apple Calendar.
- **D — Injury/illness → auto-riposo** — blocco infortunio/malattia che rimodula il piano (giorni → rest, TSS 0).

**Design System Pro (beta.2):** UI elevata al pari di TrainingPeaks / Intervals.icu — card con profondità e hover-lift, header sticky frosted-glass con KPI, tab a underline morbido, whitespace generoso, tipografia rifinita. Verificata in light e dark.

> Le versioni `v5.2.0-beta.1` / `beta.2` restano disponibili come **prerelease storiche**. La release consigliata è la **v5.2.0 stabile**.

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

| Area | PCC 3.5.2 | PCC 4.0.0 |
|---|---|---|
| **Lingua UI** | Inglese | Italiano (termini di dominio in EN: CTL, TSS, FTP, W/kg, VO2max, ZWO, FIT, rMSSD, DFA α1) |
| **Motore nutrizione** | Note generiche per fase | Motore completo: `nutrition.py` (TDEE Mifflin-St Jeor, macro obiettivo, compensazione carico, `race_fueling`, `diet.py` pasti/grammi) |
| **Integrazione** | — | Protocolli Gruppo A evidence-based con **dosi calcolate sul peso** (`supplement_doses`, mg/kg → mg assoluti) — Jeukendrup/UCI 2026, PMC12239112 |
| **Forza & Mobilità** | — | Modulo `strength_mobility.py` + endpoint che **iniettano** sedute nel piano per fase (`api_inject_strength`, `api_inject_mobility`) |
| **Body Composition** | — | Import **BIA da PDF** (`bia_parser.py`, anche scansionati via incolla-testo OCR) + storico + sync su ICU |
| **Sync** | Intervals.icu (attività/calendario) | ICU + **layer estensibile** `sync_targets.py` (plugin per altre app: TrainingPeaks, Google Fit, Strava, export JSON) |
| **Multi-disciplina** | Ciclismo centrale | Campo `disciplines` profilo (cycling/running/mtb/swim/strength/mobility) + cross-sport TSS |
| **Auto-aggiornamento** | Banner "update disponibile" | **Install reale** da GitHub Releases (`/api/self-update`) |
| **Palette / Dashboard** | Blu originale | Teal/amber, sidebar tab a sinistra, card ridimensionabili/riordinabili |
| **Brand** | PCC | PCC — Performance Cycling Coach (omaggio in NOTICE + header) |
| **Build** | `domestique.spec` | `pcc.spec`, installer NSIS `PCC-Setup.exe`, CI macOS `.dmg` |

**Non abbiamo rimosso** la logica di pianificazione adattiva di PCC (guardrail G1–G7, ricalibrazione FTP a metà ciclo, micro-intervalli 30/15 Rønnestad, 4×8 Seiler, polarizzazione, ACWR Gabbett). PCC la estende.

---

## Avvio rapido

```bash
# Sviluppo / web app
pip install -r requirements.txt
python run_web.py                 # apre http://localhost:8080 nel browser

# Build desktop (EXE Windows)
pyinstaller pcc.spec --clean --noconfirm
# → dist/PCC/PCC.exe  (poi: iscc installer.nsi → PCC-Setup-<ver>.exe silenzioso)

# Build desktop (macOS .dmg) — richiede macOS
bash build_mac.sh                # → dist/PCC.app + PCC.dmg
```

Nessun `.exe` necessario per la modalità web: il backend FastAPI gira e l'interfaccia è HTML nel browser. I dati utente restano in `~/.domestique/` (intenzionalmente non rinominato, così piani e connessioni ICU sopravvivono agli aggiornamenti).

---

## Motore Nutrizione & Integrazione

Modulo [`nutrition.py`](nutrition.py) + [`diet.py`](diet.py). **Single source of truth**: un solo motore calcola, gli altri moduli sono viste di quei numeri.

- **TDEE** via Mifflin-St Jeor (1995) × fattore attività (1.2 sedentario … 1.9 molto attivo). Per ciclisti in preparazione: 1.6–1.9.
- **Obiettivi**: `cut` (deficit 300–500 kcal, Mountjoy 2018 IOC; Burke 2018: NON <30 kcal/kg per evitare perdita FTP/massa), `maintain`, `gain` (surplus).
- **Compensazione al carico** ("fuel for the work required", GSSI SSE 231 / Burke 2018): macro che tengono conto di TSS di oggi + ieri.
- **Dosi integrazione calcolate sul peso**: caffeina 3–6 mg/kg → es. "270–540 mg" per 90 kg; beta-alanina, nitrato/barbabietola, bicarbonato, creatina, glicerolo (Gruppo A, PMC12239112; Jeukendrup/UCI 2026).
- **Race fueling**: carboidrati durante sforzo in base a durata e peso (`race_fueling`).
- **Dieta**: `diet.py` genera pasti con **grammi per alimento** (`build_daily_diet`, `build_weekly_diet`) — import da PDF con scelta sorgente (`diet_parser.py`).

Tutte le funzioni hanno test: `tests/test_fase1_nutrition_strength.py`, `tests/test_diet_parser.py`.

---

Così il piano non è solo "bici": la forza e la mobilità sono parte della settimana, con carico calcolato su 1RM.

Endpoint:
- `GET /api/strength-plan?phase=base&weeks=4&one_rm_kg=120` — piano forza per fase (Llanos-Lagos 2025)
- `GET /api/mobility-plan?days=7` — routine mobilità quotidiana (Warneke 2025, 15 min)
- `POST /api/plan/inject-strength` — inietta forza (e opzionalmente running/MTB) nel piano esistente

---

## Multi-disciplina

PCC non è solo ciclismo. Il profilo atleta accetta `disciplines` (`cycling`, `running`, `mtb`, `swim`, `strength`, `mobility`). Il planner tratta il TSS cross-sport in modo coerente: *"a hard run's TSS counts the same as a hard ride"* — una corsa dura carica quanto una salita dura, così il bilanciamento settimanale resta onesto anche per triathleti/MTB/Gravel.

---

## Body Composition (BIA)

Modulo [`bia_parser.py`](bia_parser.py). Import di misurazioni da **PDF di bioimpedenziometria**:

- PDF nativo (testo estratti) o **scansionato** (render delle pagine in immagine + incolla-testo OCR esterno, parsing regex dei campi);
- Estrazione automatica: peso, altezza, BMI, massa grassa/magra, acqua totale, fase, SMM, ecc.;
- **Storico** salvato e **sync su Intervals.icu** via `PUT /wellness-bulk` (peso + % grassa) — verificato con push reali 200 OK.

Test: `tests/test_bia.py`.

---

## Sync & Altre app

Modulo [`sync_targets.py`](sync_targets.py) — astrazione a **plugin** (`SyncTarget`) con registry. Intervals.icu è il primo target registrato; aggiungere TrainingPeaks, Google Fit, Strava o un export JSON locale significa solo registrare una nuova destinazione. L'endpoint `GET /api/sync-targets` elenca le app connesse (usato per la futura UI "Connected apps").

Sync bidirezionale ICU: attività, calendario (push delle sessioni pianificate → Garmin/MyWhoosh), e ora anche BIA.

---

## Planner adattivo

Ereditato e mantenuto da PCC, con le nostre estensioni sopra. Il planner legge ogni mattina HRV (vs baseline), forma e deficit di zona, e muta la prescrizione:

- **Soreness ≥ 6/7** sulla composite Hooper → la VO2max di oggi diventa recupero (Hooper & Mackinnon 1995; Cheung et al. 2003).
- **TSS reale settimana scorsa > 1.5× pianificata** → budget TSS settimana prossima -15% (Gabbett 2016, ACWR 0.8–1.3).
- **Z5+ rolling 48h ≥ 25 min** → oggi forzato Z2 anche con TSB positivo (Hulin et al. 2014).
- **DFA α1 medio < 0.5 su 3 uscite** → soglia di domani swap a Z2, con bottone revert (Rogers et al. 2021).
- **Ricalibrazione FTP a metà ciclo** (build1→build2) auto-testa l'FTP (Allen & Coggan, *TR&P* 3ª ed.).
- **Micro-intervalli 30/15 Rønnestad** (+12% FTP in 10 settimane), **4×8 Seiler** (top FTP builders), polarizzazione 80/5/15.

Fasi: BASE / BUILD1 / BUILD2 / PEAK / TAPER (event prep) o CONSOLIDATION (cicli non-evento, Mujika 2010). Z1…Z7+ = zone Coggan.

---

## Auto-aggiornamento

L'app controlla `releases/latest` sul fork a ogni avvio (con cache 6h). Se c'è una versione più nuova:

- **Windows**: scarica `PCC-Setup-<ver>.exe` e lancia l'installer NSIS silenzioso (`/S`) che rimpiazza l'EXE;
- **macOS**: monta `PCC.dmg` (trascini PCC in Applicazioni).

Endpoint: `POST /api/self-update` (verificato con test `tests/test_self_update.py`). Le release sono firmate... *nota*: il `.dmg` macOS non è notarizzato Apple — al primo avvio potrebbe servire "Apri" col tasto destro o `xattr -d`.

---

## Architettura

- `app.py` — backend FastAPI (endpoint pianificazione, nutrizione, BIA, sync, self-update)
- `training_planner.py` — motore piano (CTL/TSB, fasi, blocchi, guardrail G1–G7)
- `nutrition.py` / `diet.py` — nutrizione & integrazione (single source of truth)
- `strength_mobility.py` — forza/mobilità
- `bia_parser.py` / `diet_parser.py` — import PDF
- `sync_targets.py` — layer sync estensibile (plugin)
- `my_progress.py` — calendario/aderenza personale (lettura ICU self)
- `plan_export.py` — export PDF/HTML
- `templates/dashboard.html` — UI (italiano, palette teal/amber)
- `.github/workflows/build-macos.yml` — CI build `.dmg` su release

Dati in `~/.domestique/`; nessun cloud.

---

## La scienza

Ogni regola del planner cita uno studio. Tabella completa e formule in [**docs/SCIENCE.md**](docs/SCIENCE.md). Riferimenti chiave usati da PCC:

- **Rønnestad 2014 / 2020** — micro-intervalli 30/15 (+12% FTP, +12% potenza a 40 min); block periodization (+8.8% VO2max, +22% soglia).
- **Seiler** — 4×8 min (top FTP/VO2max builder).
- **Gabbett 2016** — ACWR sweet spot 0.8–1.3 (auto-cut TSS).
- **Hulin et al. 2014** — fatica neuromuscolare → forzatura Z2.
- **Rogers et al. 2021** — DFA α1 < 0.5 → swap soglia→Z2.
- **Hooper & Mackinnon 1995 / Cheung 2003** — sorezza periferica indipendente da HRV centrale.
- **Mujika 2010** — consolidazione post-ciclo.
- **Mifflin & St Jeor 1995** — TDEE.
- **Burke 2018 / Mountjoy 2018 (IOC) / GSSI SSE 231** — nutrizione, deficit, "fuel for the work required".
- **Jeukendrup / UCI 2026 / PMC12239112** — integrazione Gruppo A, dosi per kg.

---

## Release

| Piattaforma | Asset | Auto-update |
|---|---|---|
| Windows | `PCC-Setup-4.0.0.exe` (installer NSIS silenzioso) | `PCC-Setup*.exe /S` |
| macOS | `PCC.dmg` (buildato da CI su runner macOS) | monta e trascina in Applicazioni |

Vedi [**Releases**](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases) sul fork.

---

## Licenza & attribuzione

Apache-2.0 — vedi [`LICENSE`](LICENSE) e [`NOTICE`](NOTICE).

PCC è un **fork di PCC** (`platypus45`, Apache-2.0). Tutto il merito per il codebase originale, il build system e buona parte del motore di scienza dell'allenamento va agli autori originali di PCC. PCC aggiunge: motore nutrizione/integrazione, forza/mobilità, BIA, sync estensibile, UI italiana, auto-update.

Tacx, Wahoo, Garmin, Polar, MyWhoosh, Zwift, Golden Cheetah, Rouvy, Intervals.icu sono marchi dei rispettivi proprietari.

---

### Abbreviazioni

| Sigla | Significato |
|---|---|
| **TSS** | Training Stress Score |
| **CTL / ATL / TSB** | Chronic / Acute Training Load / Stress Balance (forma/carico/prontezza) |
| **FTP** | Functional Threshold Power |
| **W/kg** | Watt per kg di peso corporeo |
| **VO2max** | Massimo consumo di ossigeno |
| **ZWO** | Zwift Workout Object (file allenamento strutturato) |
| **FIT** | Flexible and Interoperable Data Transfer (formato attività Garmin) |
| **BIA** | Bioelectrical Impedance Analysis (bioimpedenziometria) |
| **DFA α1** | Detrended Fluctuation Analysis alpha1 (indice fatica autonoma) |
| **rMSSD** | Root Mean Square of Successive Differences (HRV) |
| **ACWR** | Acute:Chronic Workload Ratio |
| **ICU** | intervals.icu |
| **API** | Application Programming Interface |

---

*Costruito con ricerca PubMed, 4.200+ workout e profondo amore per il ciclismo — fork italiano di PCC.*

Copyright (c) 2026 PCC contributors (fork of PCC, Apache-2.0).
