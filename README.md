# PPC — Programming Cycling Coach

> ⚠️ **Questa è una versione derivata (fork italiano).** Vedi sotto la sezione
> **Versione originale vs Versione italiana PPC**.

Pianificatore di allenamento ciclistico locale: piano integrato (ciclismo +
forza + mobilità + nutrizione), lettura dati da intervals.icu, export PDF/HTML.

---

## Versione originale vs Versione italiana PPC

### Versione originale (upstream)
- **Autore**: `platypus45` — [github.com/platypus45/domestique](https://github.com/platypus45/domestique)
- **Licenza**: Apache-2.0
- **Stato**: progetto da cui questo fork deriva (v3.5.2). Tutto il merito per il
  codebase originale, il build system e buona parte del motore di scienza
  dell'allenamento va agli autori originali di Domestique.

### Versione italiana PPC (questo fork)
- **Repo**: [github.com/quadrellif90-collab/ppc-cycling-coach](https://github.com/quadrellif90-collab/ppc-cycling-coach)
- **Nome prodotto**: PPC — Programming Cycling Coach
- **Lingua UI**: italiano (termini di dominio ciclistico in inglese: CTL, TSS,
  FTP, W/kg, VO2max, ZWO, FIT, rMSSD, DFA α1)
- **Cosa è stato fatto in più rispetto all'originale**:
  1. **Import BIA da PDF** (bioimpedenziometria / body composition): anche PDF
     scansionati (via incolla-testo OCR) con estrazione automatica dei campi e
     salvataggio storico.
  2. **Sync bidirezionale Intervals.icu**: oltre alle attività e al calendario,
     ora anche i dati BIA (peso, % grassa) vengono scritti su ICU via
     `PUT /wellness-bulk`.
  3. **Layer di sync estensibile** (`sync_targets.py`): astrazione a plugin per
     inviare/estrarre dati anche ad altre app oltre ICU (TrainingPeaks, Google
     Fit, Strava, export JSON locale…) — basta registrare una nuova destinazione.
  4. **Dashboard ridisegnata**: sidebar tab a sinistra, card ridimensionabili e
     riordinabili, palette teal/amber distintiva.
  5. **Auto-aggiornamento**: l'app controlla le release su GitHub e installa
     l'aggiornamento (Windows installer silenzioso, macOS .dmg).
  6. **Motore nutrizione singolo** (no valori divergenti) + grammi per alimento +
     adattamento integrazione automatico + forza/mobilità automatiche nel piano.
- **Omaggio**: il credito all'autore originale è in `NOTICE`; l'header dell'app
  riporta "fork di Domestique · credit & homage to platypus45".
- **Dati utente**: conservati in `~/.domestique/` (intenzionalmente non rinominato)
  così piani e connessioni ICU sopravvivono agli aggiornamenti.

---


Apache-2.0. Vedi `LICENSE` e `NOTICE` (attribuzioni scientifiche: Llanos-Lagos
2025, Vikmoen 2021, Warneke 2025, GSSI SSE 231, Jeukendrup/UCI 2026, ecc.).

## Avvio (sviluppo / versione web)
```bash
pip install -r requirements.txt
python run_web.py                 # apre http://localhost:8080 nel browser
python run_web.py --host 0.0.0.0  # accessibile dalla rete locale (es. cellulare)
```
Nessun `.exe`: il backend FastAPI gira e l'interfaccia è HTML nel browser.

## Build desktop (EXE)
```bash
pyinstaller domestique.spec --clean --noconfirm
# → dist/PPC/PPC.exe
```
Installer (preserva i dati utente): compila `installer.nsi` con NSIS → `PPC-Setup-<ver>.exe`.

## Deploy
| Modalità | Come | Dati/connessioni | Limite |
|---|---|---|---|
| **Desktop EXE** | PyInstaller + installer NSIS | conservati in `~/.domestique/` | richiede installazione |
| **Web app locale** | `python run_web.py` | `~/.domestique/` | richiede Python |
| **Mobile / GitHub Pages** | `mobile/index.html` pushato su `gh-pages` | lato intervals.icu (OAuth) | serve ICU Client ID; solo vista (no planner) |

### Versione mobile via GitHub Pages
GitHub Pages serve **solo file statici**: non può eseguire il backend Python.
La `mobile/index.html` è una **vista lite** che si connette a intervals.icu via
OAuth implicit flow e mostra CTL/TSB/ATL/calendario nel browser del telefono,
senza installare nulla. Per attivarla:
1. Crea un'OAuth app su intervals.icu/settings/api → Redirect URI = `https://<tuo>.github.io/PPC/`.
2. Incolla il **Client ID** in `mobile/index.html` (`ICU_CLIENT_ID`).
3. Pusha `mobile/index.html` sul branch `gh-pages` (o usa Settings → Pages).
4. Apri `https://<tuo>.github.io/PPC/` dal cellulare e collega ICU.

> Per avere il **planner completo** su mobile serve un backend deployato
> (Render/Fly/Heroku) che espone l'API di PPC; la UI `templates/dashboard.html`
> punta all'URL di quel backend. Non è possibile su GitHub Pages da soli.

## Struttura
- `app.py` — backend FastAPI
- `training_planner.py` — motore piano (CTL/TSB, fasi, blocchi)
- `strength_mobility.py` / `nutrition.py` — moduli Forza/Mobilità e Nutrizione
- `plan_export.py` — compositore export PDF/HTML
- `my_progress.py` — calendario/aderenza personale (lettura ICU self)
- `templates/dashboard.html` — UI
