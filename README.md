# PPC — Programming Cycling Coach

Pianificatore di allenamento ciclistico locale: piano integrato (ciclismo +
forza + mobilità + nutrizione), lettura dati da intervals.icu, export PDF/HTML.

> Evoluzione di **Domestique** (Apache-2.0). Il nome prodotto è ora **PPC**;
> la directory dati resta `~/.domestique/` per preservare piani e connessioni
> agli aggiornamenti (vedi `NOTICE`).

## Licenza
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
