# Piano Parità Montis/MyCyclingTrainer → PCC Pro

## Obiettivo
Rendere la dashboard PCC indistinguibile da Montis per UX, coprendo tutte le lacune identificate.

---

## Fase 1: OAuth Intervals.icu (Fundamentale) — v5.5

### Backend (app.py)
- [ ] Registrare PCC su intervals.icu come "Developer Application" → ottenere `client_id` + `client_secret`
- [ ] Aggiungere route OAuth:
  - `GET /oauth/icu/start` — redirect a intervals.icu/oauth/authorize
  - `GET /oauth/icu/callback` — scambia code → access_token + refresh_token
  - `POST /oauth/icu/refresh` — refresh token automatico
- [ ] Salvare token criptati in `settings` (SQLite) — `intervals_access_token`, `intervals_refresh_token`, `intervals_token_expires`
- [ ] Migrare `icu_calendar_push.py` per usare token OAuth invece di `settings.icu_api_key`
- [ ] Aggiungere endpoint `GET /api/intervals/activities` (pull ultime 30 giorni)
- [ ] Aggiungere endpoint `GET /api/intervals/wellness` (HRV, sonno, RHR)
- [ ] Aggiungere endpoint `POST /api/intervals/library/save-workout` (LIBRARY:WRITE)
- [ ] Aggiungere endpoint `POST /api/intervals/chats` (CHATS:WRITE per note allenamenti)

### Frontend (dashboard.html)
- [ ] Sostituire campo "API Key" in Settings con bottone "Connetti intervals.icu" (OAuth flow)
- [ ] Mostrare stato connessione (connesso/sconnesso, ultimo sync)
- [ ] Rimuovere banner `icu-migrate-banner` (non serve più)
- [ ] Auto-sync attività all'avvio / ogni 30 min (background)

---

## Fase 2: Dashboard "Montis-style" Home — v5.5

### Layout nuovo (sostituisce sec-home attuale)
```
┌─────────────────────────────────────────────────────────────┐
│  HEADER:  PCC Pro                    [Connetti Intervals]   │
├─────────────────────────────────────────────────────────────┤
│  ROW 1:  STATO FORMA (card principale)                      │
│  ┌──────────────┬──────────────┬──────────────┬───────────┐ │
│  │     CTL      │     ATL      │     TSB      │  STATUS   │ │
│  │    87.3      │    92.1      │    -4.8      │  Fatica   │ │
│  │  Fitness     │  Fatigue     │  Form        │  (giallo) │ │
│  └──────────────┴──────────────┴──────────────┴───────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ROW 2:  OGGI + PROSSIMI 3 GIORNI (card affiancate)         │
│  ┌──────────────────────┬────────────────────────────────┐  │
│  │      OGGI            │   PROSSIMI ALLENAMENTI         │  │
│  │  🚴 2×20' Soglia     │  📅 Dom  | 3×10' VO2max | 120 TSS│  │
│  │  120 TSS · 90 min    │  📅 Lun  | Riposo                 │  │
│  │  [Esegui] [Dettagli] │  📅 Mar  | 90' Endurance | 65 TSS │  │
│  └──────────────────────┴────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ROW 3:  RECUPERO / READINESS (3 metriche)                  │
│  ┌──────────┬──────────┬──────────┐                          │
│  │   HRV    │  SONNO   │   RHR    │                          │
│  │  42 ms   │  7.5 h   │  48 bpm  │                          │
│  │  (verde) │  (giallo)│  (verde) │                          │
│  └──────────┴──────────┴──────────┘                          │
├─────────────────────────────────────────────────────────────┤
│  ROW 4:  AZIONI RAPIDE                                      │
│  [Genera Piano]  [Sync Intervals]  [Nuovo Workout]  [Calendario]│
└─────────────────────────────────────────────────────────────┘
```

### Implementazione
- [ ] Riscrivere `sec-home` con layout CSS Grid responsive
- [ ] `loadHomeDashboard()` — singolo fetch `/api/dashboard/home` (nuovo endpoint)
- [ ] Endpoint backend `/api/dashboard/home` che aggrega:
  - `/api/wellness` (ultimo HRV, sonno, RHR)
  - `/api/plan/next-sessions` (prossimi 3 allenamenti dal piano)
  - `/api/fitness/current` (CTL/ATL/TSB attuali)
  - `/api/intervals/last-sync` (timestamp ultimo sync)
- [ ] Card "Oggi" cliccabile → apre modal dettaglio allenamento
- [ ] Card "Prossimi" cliccabili → naviga a giorno in Piano
- [ ] Badge stato forma (colorato: verde/giallo/rosso) basato su TSB

---

## Fase 3: Onboarding Wizard Guidato — v5.6

### Step (modal a tutto schermo, progress bar in alto)
```
Step 1/5: PROFILO BASE
  • Peso, Altezza, Età, Sesso
  • [Avanti]

Step 2/5: METRICHE CHIAVE
  • FTP (W) — o "Non lo so → farò test dopo"
  • LTHR (bpm) — opzionale
  • FCmax — opzionale
  • [Avanti]

Step 3/5: OBIETTIVI
  • Tipo: Evento / Forma generale / FTP / VO2max / CTL
  • Se Evento: data, nome, distanza, dislivello
  • Settimane piano (4-52)
  • [Avanti]

Step 4/5: DISPONIBILITÀ
  • Ore/giorno per Lun-Ven, Sab, Dom (slider 0-4h)
  • [Avanti]

Step 5/5: CONNETTI INTERVALS.ICU
  • Bottone "Connetti intervals.icu" → OAuth flow
  • Se connesso: "Importa attività recenti (30gg)" [checkbox]
  • [Completa setup] → genera piano demo + redirect a Home
```

### Implementazione
- [ ] Nuovo endpoint `/api/onboarding/complete` — salva tutto + genera piano
- [ ] Modal wizard in `dashboard.html` (riutilizza `pccConfirm` pattern)
- [ ] Progress bar visuale + step indicator
- [ ] Validazione per step (non si avanza se campi obbligatori vuoti)
- [ ] Skip opzionale per step 2 e 5 (con hint "potrai farlo dopo")

---

## Fase 4: Calendar View Drag-Drop Stile Montis — v5.6

### Requisiti
- [ ] Vista calendario mensile (griglia 7 colonne × 5-6 righe)
- [ ] Allenamenti come card trascinabili (drag-drop nativo HTML5)
- [ ] Drop su giorno → sposta allenamento, ricalcola piano
- [ ] Click su giorno vuoto → "Aggiungi allenamento" (modal picker)
- [ ] Click su allenamento → modal dettaglio (sostituisci, elimina, sposta)
- [ ] Legenda colori per tipo (Z2, Soglia, VO2, Forza, Mobilità, Riposo)
- [ ] Sync bidirezionale: modifiche → push Intervals automatico

### Implementazione
- [ ] Nuova sezione `sec-calendar` (o estendere `sec-plan`)
- [ ] CSS Grid per calendario mensile
- [ ] HTML5 Drag & Drop API (native, no librerie)
- [ ] Endpoint `POST /api/plan/move-session` — sposta sessione, ricalcola
- [ ] Endpoint `POST /api/plan/add-session` — aggiungi sessione custom
- [ ] Integrazione `reconcile()` dopo ogni modifica

---

## Fase 5: Workout Library + Templates (LIBRARY:WRITE) — v5.7

### Funzionalità
- [ ] Tab "Libreria Workout" → mostra workout salvati localmente + su Intervals
- [ ] "Salva su Intervals" per ogni workout (usa `/api/intervals/library/save-workout`)
- [ ] "Importa da Intervals" — scarica library remota
- [ ] Template riutilizzabili: "2×20' Soglia", "5×5' VO2max", "30' Recupero", ecc.
- [ ] Drag template su giorno calendario → crea sessione istanza

### Implementazione
- [ ] Estendere `sec-library` con vista "I miei template"
- [ ] Backend: tabella `workout_templates` (name, description, zwo_json, source_intervals_id)
- [ ] OAuth scope `LIBRARY:WRITE` + `LIBRARY:READ`

---

## Fase 6: Nutrizione Integrata nel Piano — v5.7

### Cambio UX
- [ ] Rimuovere tab `nutrition` separata
- [ ] In `sec-plan`: ogni giorno mostra **macro target** (kcal, CHO, PRO, FAT) sotto allenamento
- [ ] "Piano nutrizionale settimanale" — card espandibile per settimana
- [ ] Generazione automatica basata su TSS/giorno + peso + obiettivo composizione
- [ ] Sync con Intervals? (solo se hanno API nutrition — verificare)

---

## Fase 7: PWA / Service Worker / Mobile — v5.8

- [ ] `manifest.json` completo (name, short_name, icons, start_url, display: standalone)
- [ ] Service worker (`sw.js`) — cache static assets + API GET per offline-read
- [ ] `offline.html` fallback
- [ ] "Installa app" banner su mobile
- [ ] Responsive: sidebar collassabile in hamburger menu < 768px

---

## Mapping Endpoint Backend Necessari

| Endpoint | Metodo | Descrizione | Fase |
|----------|--------|-------------|------|
| `/oauth/icu/start` | GET | Inizia OAuth flow | 1 |
| `/oauth/icu/callback` | GET | Callback OAuth | 1 |
| `/oauth/icu/refresh` | POST | Refresh token | 1 |
| `/api/dashboard/home` | GET | Aggregato per Home Montis-style | 2 |
| `/api/plan/next-sessions` | GET | Prossimi N allenamenti piano | 2 |
| `/api/fitness/current` | GET | CTL/ATL/TSB attuali | 2 |
| `/api/intervals/activities` | GET | Pull attività recenti (30gg) | 1 |
| `/api/intervals/wellness` | GET | HRV, sonno, RHR da Intervals | 1 |
| `/api/intervals/library/save-workout` | POST | Salva workout su Intervals | 5 |
| `/api/intervals/library/list` | GET | Lista library Intervals | 5 |
| `/api/onboarding/complete` | POST | Completa wizard + genera piano | 3 |
| `/api/plan/move-session` | POST | Sposta sessione (drag-drop) | 4 |
| `/api/plan/add-session` | POST | Aggiungi sessione custom | 4 |
| `/api/plan/week-nutrition` | GET | Macro target settimana | 6 |

---

## Priorità Immediata (questa sessione)

1. ✅ **OAuth Intervals.icu** — fondamentale per tutto il resto
2. ✅ **Dashboard Home Montis-style** — impatto UX immediato
3. ✅ **Onboarding Wizard** — prima esperienza utente

---

## Note Tecniche

- **Crittografia token**: usare `cryptography.fernet` con chiave derivata da `SECRET_KEY` + `user_id` (single user → `SECRET_KEY` basta)
- **Auto-sync**: `setInterval` 30 min in frontend + `onfocus` window event
- **Error handling**: ogni `catch` → `showToast(errore, 8000, 'error')` — mai silent fail
- **Loading states**: skeleton shimmer (già presente) per ogni card
- **i18n**: tutti i testi in italiano, micro-copy caldo/tecnico