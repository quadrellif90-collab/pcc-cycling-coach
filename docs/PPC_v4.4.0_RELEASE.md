# PCC v4.4.0 — Presentazione di rilascio

**Performance Cycling Coach** · Build del 2026-07-25 · Installer Windows + DMG macOS

---

## In sintesi

PCC 4.4.0 risolve tre irritazioni vecchie di mesi e rende il motore di
pianificazione **consapevole del tempo che hai davvero**. Niente più "mi chiede
sempre di ridare il login", niente più profili che non si cancellano, e un
pianificatore che ragiona sul *runway* (settimane che ti restano fino alla gara)
invece di partire ciecamente da oggi.

Tutto **local-first**: i tuoi dati restano sul tuo PC, nessun abbonamento,
nessun server PCC. L'integrazione con intervals.icu è un *optional* che colleghi
tu.

---

## Cosa c'è di nuovo

### 1. Login intervals.icu che resta (OAuth one-click)
- **Collega** con un clic: premi *Collega intervals.icu*, autorizzi sul sito,
  torni connesso. Niente più copia-incolla di API key.
- Il token **sopravvive ai riavvii** → apri PCC e sei già connesso.
- **Disconnetti** ora pulisce *entrambi* i metodi (token OAuth + eventuale API
  key). Prima una API key residua dava l'illusione di "restare sempre connesso".
- Se le credenziali OAuth mancano nel build, l'app mostra un avviso chiaro
  invece di rimandarti in loop alla pagina di login.

### 2. Gestione profili completa
Tre controlli nel pannello profilo, tutti funzionanti anche sull'ultimo/attivo:
- **Disconnetti ICU** — azzera le credenziali intervals.icu.
- **Reset profilo** — svuota rides/piani/wellness, mantiene il profilo.
- **Elimina profilo** — ora possibile anche se è l'attivo (hot-swap a un altro
  profilo, oppure riavvio del wizard se è l'unico).

### 3. Motore di pianificazione *runway-aware*
- **Data di partenza scelta da te.** Il piano può partire dalla data che decidi
  (anche futura, fino a 1 anno avanti). Le fasi vengono ancorate da lì.
- **Date impossibili bloccate con chiarezza.** Partenza ≥ giorno della gara →
  il selettore la impedisce e spiega perché, in italiano. Niente più errore
  criptico *"no runway left"*.
- **Avvisi intelligenti sul runway:**
  - `< 2 settimane` → avviso *piano da settimana-gara* (consiglio: obiettivo
    intermedio o sposta la partenza);
  - `2–5 settimane` → avviso *piano compresso* (consiglio: anticipa la
    partenza);
  - `~12+ settimane` → nessun avviso.
- **Periodizzazione a blocchi sui piani lunghi.** Una base lunga non è più una
  fila di blocchi identici: ogni 3 blocchi aerobici viene inserito un **richiamo
  VO2max/soglia** (*block periodization*, Rønnestad 2019) per mantenere il
  top-end durante la base, senza compromettere l'aerobico.

### 4. Sotto il cofano
- Iniettore forza **idempotente**: niente sessioni duplicate lo stesso giorno;
  la forza è distribuita su giorni distinti (~48h).
- Build EXE/installer allineati (scipy 1.18, percorsi `dist/PCC`).
- **Installer Windows** incluso: `PCC-Setup-4.4.0.exe` installa con scorciatoia
  nel menu Start e disinstallatore pulito.

---

## Come si installa

| Piattaforma | File | Note |
|---|---|---|
| Windows | `PCC-Setup-4.4.0.exe` | Installer NSIS — doppio clic, Next/Next. Dati utente in `%USERPROFILE%\.domestique\` (non toccati da installazione/aggiornamento). |
| macOS | `PCC.dmg` | Trascina in Applicazioni. |

I dati (piani, connessioni intervals.icu, profili) vivono fuori dalla cartella
di installazione → un aggiornamento futuro non li cancella.

---

## Cosa NON c'è ancora (e arriva nel 5.x)

Questa release consolida la *base*. La prossima major (PCC 5.x) porterà, sulla
scia delle ricerche 2025-2026 appena chiuse:

- **Notifiche smart** (il pezzo mancante): avvisi/email/toast proattivi —
  Morning Readiness, Red/Yellow/Green day, Workout of the Day, Weekly Review,
  reminder fueling, allarmi HRV/monotony. Local-first, via SMTP tuo + toast.
- **Selettore di "accorgimenti"**: nel pianificatore potrai attivare/disattivare
  singoli moduli — nutrizione/fueling, integrazione (caffeina/nitrati/creatina),
  strategie heat/acclimatazione, forza e mobilità periodizzate, DFA a1 /
  durability — e vedere subito come cambia il piano. Oppure tenere il
  **pianificatore "normale"** pulito.
- **Ricalibro automatico** continuo (già in parte presente come *continuous
  policy*) esposto esplicitamente all'utente.

→ Vedi `docs/PCC_5x_ROADMAP.md` per il piano d'azione completo.

---

## Verifiche

- ✅ Installer NSIS compilato e allegato alla release
- ✅ Secret OAuth bundle-ato nell'EXE (login one-click funzionante)
- ✅ EXE smoke-test: serve `/api/version` = 4.4.0
- ✅ Suite pytest: 2933 test passati (nessuna regressione sulle mie modifiche)
