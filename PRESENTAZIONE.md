# PCC Pro — Performance Cycling Coach

**Scheda prodotto** · Versione **5.3.4** · Fork italiano di [Domestique](https://github.com/platypus45/domestique) (Apache-2.0)

---

## Che cos'è

PCC Pro è un **allenatore ciclistico adattivo, locale e offline-first**: gira sul tuo computer (nessun cloud obbligatorio), importa le tue uscite `.fit` e **adatta automaticamente** la prescrizione del giorno dopo in base a ciò che hai realmente fatto. Un unico motore di pianificazione (*single source of truth*): tutte le viste — nutrizione, forza, body-composition, calendario — derivano dagli stessi numeri, senza valori divergenti.

**PCC Pro** (v5.3.x) aggiunge la **Pro Experience**: dashboard interattiva, radar metabolico animato, grafici Chart.js locali, PWA — tutto verificato end-to-end con 0 errori JS.

---

## Per chi

Ciclisti amatoriali evoluti e agonisti che vogliono la profondità scientifica di TrainingPeaks / Intervals.icu / WKO **senza abbonamento cloud**, con i dati sul proprio disco e l'interfaccia in italiano (termini tecnici in inglese: CTL, TSS, FTP, W/kg, VO2max, DFA α1, rMSSD).

---

## Cosa fa (in breve)

- **Piano adattivo** che si ricalcola da TSS overshoot, DFA α1, decoupling aerobico, monotonia di Foster, drift eFTP, Hooper composite.
- **Nutrizione & integrazione**: TDEE (Mifflin-St Jeor), macro, "fuel for the work required", dosi supplementi sul peso, race-fueling.
- **Forza & mobilità** iniettate nel piano per fase (Base/Build/Peak/Taper).
- **Multi-disciplina** (bici / corsa / MTB / nuoto) e **body-composition (BIA)** importata da PDF.
- **Sync Intervals.icu** via OAuth 2.0 + push del calendario.
- **Auto-aggiornamento** dalle GitHub Releases (installer Windows silenzioso, `.dmg` macOS).

---

## PCC Pro — Dashboard & Pro Experience (v5.3.x)

| Funzione | Dettaglio |
|---|---|
| **Griglia dashboard ridimensionabile** | Ogni widget si **ridimensiona** (`resize:both`) e si **riordina via drag-and-drop**, con persistenza in `localStorage`. |
| **Card KPI animate** | Forma/fatica, TSB, CTL/ATL, carico settimanale — con micro-animazioni e hover-lift. |
| **Grafici Chart.js locali** | Power Curve con zoom interattivo, Fitness/TSS interattivi, TSS settimanale. **Nessun CDN** (offline). |
| **Radar metabolico animato** | 5 assi (VO₂max, VLamax, FatMax, W/kg, FTP, CTL) con score 0–100, disegno pixel-by-pixel verificato. |
| **Badge tipo atleta** | Scalatore / Sprinter / All-rounder / Cronoman / Intermedio / Amatoriale + raccomandazioni IA di focus. |
| **Timeline stagione drag-and-drop** | Riordina eventi/blocchi trascinandoli. |
| **Tema racing** | Palette teal→amber, sidebar tab a sinistra, header sticky frosted-glass. |
| **PWA** | Manifest + service worker → installabile e usabile offline dal browser. |

**Verificato end-to-end** (smoke test Playwright, 0 JS errors): pro-dashboard-grid, season-timeline drag-and-drop, pro-tss-weekly-chart (Chart.js), profile-radar + pixel disegnati, input PDF BIA, PWA manifest.

---

## Body Composition (BIA) — Parser ibrido

Import misurazioni da **PDF di bioimpedenziometria** (AKERN Biavector, InBody, Tanita, BODYGRAM):

1. **PDF testuale** → parsing regex diretto.
2. **PDF scansionato + chiave cloud** (`.env`) → modello vision (z.ai / OpenAI-compatible) ritorna **JSON strutturato** con tutti i campi (qualità = OCR z.ai: virgole decimali preservate, colonne non confuse).
3. **PDF scansionato senza chiave** → **OCR Tesseract** + parser regex (fallback offline).

**Parser regex robusto** (ereditato da NutriCoach): normalizzazione virgola→punto *prima* della punteggiatura (risolve `13,1→131`), pattern *unit-aware* (non confonde FM kg con FM %), e **sanity-check post-estrazione** per rumore OCR AKERN (`ECW>TBW → ECW=TBW-ICW`, `PhA` fuori 1–20° scartato, litri/CHI ÷10 se la virgola decimale è persa).

Tipicamente **12–22 campi** da un singolo PDF (peso, altezza, BMI, massa grassa/magra, TBW, ECW/ICW, idratazione, BCM, SMM, ASMM, PhA, CHI).

---

## Novità v5.2 — 12 nuove funzioni + Design System Pro

| # | Funzione | # | Funzione |
|---|----------|---|----------|
| #1 | Semaforo fatica | #7 | Grafici personalizzati |
| #2 | FTP continuo | #8 | Asimmetrie pedalata (L-R) |
| #3 | Decoder metabolico (VO2max/VLamax/FatMax) | A | Field-test FTP |
| #4 | Modelli CP multipli (Monod/Morton) | B | Export bundle (ZIP) |
| #5 | Classificazione sessione & RPE | C | Calendario `.ics` |
| #6 | Import lab test (CPET/INSCYD da PDF) | D | Infortunio → auto-riposo |

---

## Avvio rapido

1. Scarica l'ultimo `PCC-Setup-<versione>.exe` (o `PCC.dmg`) dalle [Release](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases).
2. Installa e avvia PCC (si apre sul `localhost`, porta 8080).
3. Segui la **checklist di benvenuto**: completa il profilo (peso, FTP, FC max) → importa la prima uscita `.fit` → genera il piano → (opzionale) collega Intervals.icu.

---

## Privacy & dati

Tutti i dati restano in locale in `~/.domestique`. Nessun dato lascia il computer se non colleghi esplicitamente Intervals.icu. Il `client_secret` OAuth è bundlato (pattern standard per app desktop installate) e `.oauth.env` è git-ignored.

---

_Fork con attribuzione a `platypus45` (vedi `NOTICE`). Licenza Apache-2.0._
