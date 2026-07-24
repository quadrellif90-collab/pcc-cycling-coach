# PPC 5.x — Roadmap: app di pianificazione potenziata

Sintesi di due ricerche (competitiva 2025-2026 + scientifica aggiornata) in un
piano d'azione per portare PPC da "planner valido" a "app competitiva 2026".

**Principio guida (dal fallimento di Today's Plan):** la profondità analitica da
sola non salva. Serve *adattività automatica* + *semplicità* + 1-2 differenziatori
realmente unici. PPC è local-first/no-subscription: questo è già un positioning
vincente (come Intervals.icu $4 o Garmin gratis) — rafforzarlo.

---

## GAP ANALISI — dove PPC è oggi

| Area | Stato PPC 4.4 | Gap vs mercato 2026 |
|---|---|---|
| PMC CTL/ATL/TSB | ✅ c'è | OK (baseline) |
| Periodizzazione base/build/peak/taper + date evento | ✅ c'è (v4.4) | Manca A/B/C races + multi-evento |
| Start_date utente / runway-aware | ✅ nuovo in v4.4 | OK |
| Ricalibro automatico del piano | ❌ manuale | **GAP #1 — il più importante** |
| FTP auto / eFTP | ⚠️ parziale | Serve eFTP da sforzi (standard 2025) |
| Alert overtraining/fatica | ⚠️ solo warning runway | Serve RLGL-style su load |
| HRV / readiness adattamento | ❌ | **GAP #2 — differenziatore** |
| Forza periodizzata | ⚠️ iniettore presente, non periodizzato | **GAP #3 — differenziatore** |
| Mobilità / core | ❌ | GAP #3 (stesso layer) |
| Nutrizione/fueling per workout | ⚠️ NutriCoach separato | Link fueling→sessione nel planner |
| Notifiche smart (email/push) | ❌ | **GAP #4 — il tuo "avvisi/notifiche"** |
| Durability / W' / CP | ⚠️ decoupling base | Metriche avanzate accessibili |
| AI coach conversazionale | ❌ | Differenziatore interessante |

---

## PIANO — PPC 5.x in 4 fasi (MVP→potenziato)

### FASE 1 — Auto-adattamento + notifiche (il core del 2026)
**Obiettivo:** il piano si aggiusta da solo e ti avvisa. Chiude GAP #1 e #4.

1. **Ricalibro automatico (continuous re-planning).**
   - Trigger: workout saltato / modificato RPE / disponibilità cambiata / nuova data evento.
   - Algoritmo: ri-ancora le fasi al remaining runway (usa la logica già esistente
     `_anchor_for_weeks` + split base→recall di v4.4), ricalcola TSS rimanenti,
     ri-distribuisce le sessioni mancanti nei giorni liberi. **Single source of truth:**
     un solo `replan(target_date, sessions_done, availability)` che le viste consumano.
   - Regola carico (da ricerca): incremento ≤8%/sett; se ATL>>CTL → inserisci recovery.
2. **Alert di fatica (RLGL-style, senza HRV).**
   - Calcola TSB giornaliero; giorni TSB<-25 → "Red" (riposo/recupero), -10..0 →
     "Yellow" (LIT), >0 → "Green" (tutto ok). Mostra nel calendario + toast.
   - Se 2+ giorni Red previsti → propone auto spostamento sessioni intense.
3. **Notifiche smart (il tuo "avvisi email/push").**
   - **Desktop toast** già nel planner (v4.4) → estendere a: reminder pre-workout
     (giorno prima + 2h prima), avviso overtraining, piano pronto post-rialibro.
   - **Email (locale, via SMTP OS client o config account):** riepilogo settimanale
     (pianificato vs fatto, TSB, suggerimenti), avviso evento imminente, alert fatica.
     Nessun cloud: l'utente configura il proprio SMTP/account.
   - **Push (opzionale):** via Intervals.icu calendar push già esistente + futuro
     webhook locale. No server esterno.

### FASE 2 — HRV / readiness + eFTP (individualizzazione)
**Gap #2 + FTP auto.** Chiude GAP #2.

4. **Layer HRV/readiness.**
   - Import HRV (rMSSD) + sonno da Intervals.icu wellness fields (API già aperta) o
     file/export Oura/Whoop/Garmin.
   - Regola (Javaloyes 2019, evidenza B): rMSSD oggi < media7d − 0.75×SD → declassa
     HIT→LIT; ≥2 giorni fuori banda → recovery day. Integra nel ricalibro Fase 1.
   - UI: riga HRV nel calendario + "giorno verde/giallo/rosso" coerente con RLGL.
5. **eFTP automatico.** Da power-duration (Monod-Scherrer / Morton 3-param) su sforzi
   recenti → FTP stimato senza test. Intervals.icu ha già eFTP; PPC può calcolarlo
   localmente sugli import FIT.

### FASE 3 — Forza + mobilità periodizzate (il differenziatore forte)
**Gap #3.** Solo FasCat/Wahoo/SYSTM lo fanno seriamente → quick win ad alto valore.

6. **Motore forza periodizzato (regole da ricerca, evidenza A):**
   - off-season/base: 2×/sett (anatomical 2-3×15@55% → max 3-4×4-8@80-90%).
   - pre-comp: 1-2×/sett conversione potenza (3-4×3-5 esplosivi@70-85%).
   - in-season: mantenimento 1×/sett (2-3×3-5@85-90% 1RM).
   - Esercizi: squat/half-squat, leg press, RDL, hip thrust, calf, core.
   - Interferenza: mai HIT bici ≤24h dopo heavy strength; separa ≥6h, giorni diversi.
7. **Mobilità / core:** 2-3×/sett, plank 30-60s + anti-rotation + bird-dog (Sports
   Med Open 2026). Nel calendario come sessioni non-bici.
8. **Integrazione calendario:** forza+mobilità appaiono nel planner affianco alle
   sessioni bici, con i dovuti spacing (interferenza). Ricalibro Fase 1 le considera.

### FASE 4 — Metriche avanzate accessibili + nutrizione linkata + AI coach
**Differenziatori "premium" resi semplici.**

9. **Durability / fatigue resistance:** ri-test soglia dopo 2-3h (o kJ cumulati)
   → % decadimento (Maunder 2021, Van Erp 2021). Mostra come grafico leggibile.
10. **W' / Critical Power (Morton-Monod):** modello CP/W' dagli sforzi → prescrizione
    intervalli e detection "breakthrough" (stile Xert MPA, semplificato).
11. **Nutrizione/fueling per sessione (link a NutriCoach):** per ogni workout calcola
    CHO/h (Burke/IOC: 30-60g/h <2.5h, 90g/h >2.5-3h), train-low sulle LIT base,
    train-high su HIT/gara. Integra consigli integratori (caffeina 3-6mg/kg, nitrati,
    creatina, beta-alanina — dosaggi IOC/ISSN) come flag pre-sessione.
12. **AI coach conversazionale (local, modello opzionale):** spiega il piano e lo
    modifica in chat (stile AI Endurance/CoachCat) — usa un LLM locale o API utente,
    mai dati fuori dal PC. Fase esplorativa.

---

## TABELLA PRIORITÀ (MUST vs DIFFERENZIATORE)

**MUST-HAVE (per competere — senza queste sei fuori mercato 2026):**
1. Ricalibro automatico del piano (Fase 1)
2. Alert fatica RLGL-style su load (Fase 1)
3. Notifiche: reminder + email riepilogo (Fase 1) — *la tua richiesta esplicita*
4. eFTP automatico (Fase 2)
5. A/B/C races + multi-evento (estensione Fase 1)
6. PMC CTL/ATL/TSB — *già presente, mantenere*
7. Integrazione Intervals.icu — *già presente, mantenere*

**DIFFERENZIATORI (dove PPC vince — pochi li hanno insieme):**
1. HRV/readiness adattamento (Fase 2) — solo AI Endurance (DFA a1) lo fa davvero
2. Forza + mobilità periodizzate nel calendario bici (Fase 3) — solo FasCat/Wahoo
3. Nutrizione/fueling linkato ai workout (Fase 4) — quasi nessuno lo lega
4. Metriche avanzate accessibili (durability, W'/CP) (Fase 4)
5. Local-first / no-subscription / data ownership (positioning)
6. AI coach conversazionale locale (Fase 4)

---

## ARCHITETTURA (per non rompere la single source of truth)
- Un solo motore `replan()` + `daily_adapt()`; dashboard/calendar/email/ICU sono VISTE.
- HRV/wellness/forza/mobilità/nutrizione sono *layer* che alimentano gli stessi
  input del motore (availability, readiness, load) — non motori separati.
- Tutto locale: notifiche via SMTP configurato dall'utente, nessun server PPC.

## EVIDENZA (riferimenti chiave)
- Rønnestad & Mujika 2014 (forza endurance, evidenza A)
- Mølmen/Rønnestad 2019 meta BP (VO2max ES 0.40, A)
- Javaloyes 2019/2020 HRV-guided (B)
- Maunder 2021 / Van Erp 2021 / Jones 2023 durability (B/C)
- Impellizzeri 2020 critica ACWR (A) — NON usare soglie ACWR come regola causale
- Mujika taper (volume -40/60%, intensità invariata, A)
- Impey 2018 / Burke periodized nutrition (A)
- IOC 2018 / ISSN integratori (A)
