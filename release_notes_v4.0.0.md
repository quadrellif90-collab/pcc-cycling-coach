# PPC — Programming Cycling Coach v4.0.0

**Fork italiano di Domestique (Apache-2.0, `platypus45`).** Questa release è una versione derivata: stessa architettura di pianificazione adattiva dell'originale, estesa con motore nutrizione/integrazione riscritto, forza/mobilità iniettabili, import BIA da PDF, sync estensibile verso Intervals.icu e altre app, UI in italiano e auto-aggiornamento.

> Omaggio all'autore originale in `NOTICE`. Credit & homage to `platypus45`.

---

## Cosa è cambiato rispetto a Domestique 3.5.2

| Area | Domestique 3.5.2 | PPC 4.0.0 |
|---|---|---|
| Lingua UI | Inglese | Italiano (termini dominio in EN: CTL, TSS, FTP, W/kg, VO2max, ZWO, FIT, rMSSD, DFA α1) |
| Motore nutrizione | Note generiche per fase | Motore completo: TDEE Mifflin-St Jeor, macro obiettivo, compensazione carico, race-fueling, pasti con grammi |
| Integrazione | — | Protocolli Gruppo A evidence-based con **dosi calcolate sul peso** (Jeukendrup/UCI 2026, PMC12239112) |
| Forza & Mobilità | — | Modulo dedicato + endpoint che **iniettano** sedute nel piano per fase |
| Body Composition | — | Import **BIA da PDF** (anche scansionati) + storico + sync su Intervals.icu |
| Sync | Intervals.icu (attività/calendario) | ICU + **layer estensibile** (plugin per TrainingPeaks, Google Fit, Strava, export JSON) |
| Multi-disciplina | Ciclismo centrale | Campo `disciplines` (cycling/running/mtb/swim/strength/mobility) + cross-sport TSS |
| Auto-aggiornamento | Banner "update disponibile" | Install reale da GitHub Releases |
| Palette / Dashboard | Blu originale | Teal/amber, sidebar tab a sinistra, card ridimensionabili/riordinabili |
| Brand | Domestique | PPC — Programming Cycling Coach |
| Build | `domestique.spec` | `ppc.spec`, installer NSIS `PPC-Setup.exe`, CI macOS `.dmg` |

**Non rimosso:** la logica di pianificazione adattiva di Domestique (guardrail G1–G7, ricalibrazione FTP a metà ciclo, micro-intervalli 30/15 Rønnestad, 4×8 Seiler, polarizzazione, ACWR Gabbett). PPC la estende.

---

## Funzionalità principali

- **Planner adattivo**: muta la prescrizione da ogni segnale reale (TSS overshoot, DFA α1, decoupling, Hooper, ACWR). Micro-intervalli 30/15 Rønnestad, 4×8 Seiler, polarizzazione 80/5/15.
- **Motore Nutrizione & Integrazione** (`nutrition.py`, `diet.py`): TDEE, macro per obiettivo (cut/maintain/gain), compensazione al carico ("fuel for the work required"), dosi integrazione per kg, race-fueling, dieta con grammi per alimento (import PDF).
- **Forza & Mobilità** (`strength_mobility.py`): piani per fase (Llanos-Lagos 2025) e routine mobilità (Warneke 2025), iniettabili nel piano.
- **Body Composition (BIA)**: import da PDF (anche scansionati via OCR incolla-testo), storico e sync su Intervals.icu (`PUT /wellness-bulk`).
- **Sync estensibile** (`sync_targets.py`): plugin per ICU e altre app.
- **Multi-disciplina**: cycling/running/mtb/swim con TSS cross-sport coerente.
- **Auto-aggiornamento**: `POST /api/self-update` — Windows installer silenzioso, macOS `.dmg`.
- **4.200+ workout ZWO** e **622 route virtuali** (libreria ereditata).

---

## Installazione

### Windows
Scarica `PPC-Setup-4.0.0.exe` e installa. L'app si auto-aggiorna dalle future release.

### macOS
Scarica `PPC.dmg`, trascina PPC in Applicazioni.
> Nota: il `.dmg` non è notarizzato Apple. Al primo avvio, se serve: tasto destro → Apri, oppure `xattr -d com.apple.quarantine /Applications/PPC.app`.

### Sviluppo / Web
```bash
pip install -r requirements.txt
python run_web.py   # http://localhost:8080
```

I dati utente restano in `~/.domestique/` (intenzionalmente non rinominato).

---

## La scienza (riferimenti)

Rønnestad 2014/2020 (30/15s), Seiler (4×8), Gabbett 2016 (ACWR), Hulin 2014, Rogers 2021 (DFA α1), Hooper & Mackinnon 1995 / Cheung 2003, Mujika 2010, Mifflin & St Jeor 1995, Burke 2018 / Mountjoy 2018 IOC / GSSI SSE 231, Jeukendrup/UCI 2026 / PMC12239112, Llanos-Lagos 2025, Warneke 2025. Tabella completa in `docs/SCIENCE.md`.

---

## Licenza

Apache-2.0. PPC è un fork di Domestique (`platypus45`). Vedi `LICENSE` e `NOTICE`.
