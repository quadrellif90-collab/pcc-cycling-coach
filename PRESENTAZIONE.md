# PCC — Performance Cycling Coach

**Scheda principale del prodotto** · Versione **5.2.2** · Fork italiano di [Domestique](https://github.com/platypus45/domestique) (Apache-2.0)

---

## Che cos'è

PCC è un **allenatore ciclistico adattivo, locale e offline-first**: gira sul tuo computer (nessun cloud obbligatorio), importa le tue uscite `.fit` e **adatta automaticamente** la prescrizione del giorno dopo in base a ciò che hai realmente fatto. Un unico motore di pianificazione (*single source of truth*): tutte le viste — nutrizione, forza, body-composition, calendario — derivano dagli stessi numeri, senza valori divergenti.

## Per chi

Ciclisti amatoriali evoluti e agonisti che vogliono la profondità scientifica di TrainingPeaks / Intervals.icu / WKO **senza abbonamento cloud**, con i dati sul proprio disco e l'interfaccia in italiano (termini tecnici in inglese: CTL, TSS, FTP, W/kg, VO2max, DFA α1, rMSSD).

## Cosa fa (in breve)

- **Piano adattivo** che si ricalcola da TSS overshoot, DFA α1, decoupling aerobico, monotonia di Foster, drift eFTP, Hooper composite.
- **Nutrizione & integrazione**: TDEE (Mifflin-St Jeor), macro, "fuel for the work required", dosi supplementi sul peso, race-fueling.
- **Forza & mobilità** iniettate nel piano per fase (Base/Build/Peak/Taper).
- **Multi-disciplina** (bici / corsa / MTB / nuoto) e **body-composition (BIA)** importata da PDF.
- **Sync Intervals.icu** via OAuth 2.0 + push del calendario.
- **Auto-aggiornamento** dalle GitHub Releases (installer Windows silenzioso, `.dmg` macOS).

## Novità v5.2 — 12 nuove funzioni + Design System Pro

| # | Funzione | # | Funzione |
|---|----------|---|----------|
| #1 | Semaforo fatica | #7 | Grafici personalizzati |
| #2 | FTP continuo | #8 | Asimmetrie pedalata (L-R) |
| #3 | Decoder metabolico (VO2max/VLamax/FatMax) | A | Field-test FTP |
| #4 | Modelli CP multipli (Monod/Morton) | B | Export bundle (ZIP) |
| #5 | Classificazione sessione & RPE | C | Calendario `.ics` |
| #6 | Import lab test (CPET/INSCYD da PDF) | D | Infortunio → auto-riposo |

**UX 5.2 per il cliente finale:** onboarding guidato (banner setup + checklist 4 passi), scheda "Novità" in-app, gestore banner (max 2 visibili + campanella), messaggi di errore in linguaggio comprensibile, stati di caricamento sulle azioni lunghe, empty-state chiari.

## Avvio rapido

1. Scarica l'ultimo `PCC-Setup-<versione>.exe` dalle [Release](https://github.com/quadrellif90-collab/pcc-cycling-coach/releases).
2. Installa e avvia PCC (si apre sul `localhost`, porta 8080).
3. Segui la **checklist di benvenuto**: completa il profilo (peso, FTP, FC max) → importa la prima uscita `.fit` → genera il piano → (opzionale) collega Intervals.icu.

## Privacy & dati

Tutti i dati restano in locale in `~/.domestique`. Nessun dato lascia il computer se non colleghi esplicitamente Intervals.icu. Il `client_secret` OAuth è bundlato (pattern standard per app desktop installate) e `.oauth.env` è git-ignored.

---

_Fork con attribuzione a `platypus45` (vedi `NOTICE`). Licenza Apache-2.0._
