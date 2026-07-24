# PPC 5.x — Roadmap: app di pianificazione potenziata (massimo del massimo)

Sintesi di 4 ricerche (competitiva 2025-2026 + scientifica 2022-2024 + scientifica
2025-2026 + notifiche tattiche) in un piano d'azione. Dettagli in:
- `docs/PPC_5x_ROADMAP.md` (questo file, sintesi)
- `docs/ricerca_competitiva_2025-2026.md`
- `docs/ricerca_scientifica_2022-2024.md`
- `docs/ricerca_scientifica_2025-2026.md`
- `docs/ricerca_notifiche_smart_2024-2026.md`

**Principio guida:** profondità analitica da sola non salva (Today's Plan è morta
nonostante fosse valida). Serve *adattività automatica* + *semplicità* + 1-2
differenziatori unici. PPC è local-first/no-subscription: positioning vincente.

---

## GAP ANALISI — dove PPC è oggi (v4.4)

| Area | Stato PPC 4.4 | Gap vs mercato 2026 |
|---|---|---|
| PMC CTL/ATL/TSB | ✅ c'è | OK baseline |
| Periodizzazione + date evento | ✅ runway-aware (v4.4) | Manca A/B/C races + multi-evento |
| Start_date utente | ✅ nuovo | OK |
| Ricalibro automatico | ❌ manuale | **GAP #1** |
| FTP auto / eFTP | ⚠️ parziale | Serve eFTP da sforzi |
| Alert overtraining/fatica | ⚠️ solo runway | Serve RLGL-style + notifiche |
| HRV / readiness adattamento | ❌ | **GAP #2** |
| Forza periodizzata | ⚠️ iniettore non periodizzato | **GAP #3** |
| Mobilità / core | ❌ | GAP #3 |
| Nutrizione/fueling per workout | ⚠️ NutriCoach separato | Link fueling→sessione |
| Notifiche smart (email/push/toast) | ❌ | **GAP #4 (il tuo focus)** |
| Durability / W' / CP | ⚠️ decoupling base | Metriche accessibili |
| AI coach conversazionale | ❌ | Differenziatore |
| Digital twin ML | ❌ | Frontiera (Fase 4) |

---

## PIANO — PPC 5.x in 4 fasi

### FASE 1 — Auto-adattamento + notifiche smart (il core del 2026)
**Chiude GAP #1 e #4 (il tuo focus: avvisi/notifiche/email).**

1. **Ricalibro automatico (continuous re-planning).**
   - Trigger: workout saltato / RPE modificato / disponibilità cambiata / nuova data.
   - Algoritmo: ri-ancora fasi al remaining runway (logica `_anchor_for_weeks` +
     split base→recall di v4.4), ricalcola TSS rimanenti, ridistribuisce.
   - Single source of truth: un solo `replan()` che le viste consumano.
   - Regola carico: incremento ≤8%/sett; se ATL>>CTL → recovery.

2. **Alert fatica RLGL-style (senza HRV).**
   - TSB giornaliero: <−25 → Red (riposo), −10..0 → Yellow (LIT), >0 → Green.
   - 2+ giorni Red previsti → propone auto-spostamento sessioni intense.
   - Mostra nel calendario + toast.

3. **NOTIFICHE SMART (12 tipi, local-first).** — il tuo "avvisi/notifiche via mail":
   - **Canali:** toast desktop (win10toast/plyer) + **email via SMTP utente**
     (smtplib, nessun cloud) + colore calendario. Scheduler locale (cron/task Python).
   - **Dati:** GET wellness/activities da Intervals.icu API (HRV, sonno, Form).
   - **Le 12 notifiche** (dettaglio in `ricerca_notifiche_smart_2024-2026.md`):
     1. Morning Readiness Report (email+toast, 🟢🟡🔴)
     2. RLGL Day Flag (TSB<−25 / HRV−1SD → Red Day)
     3. Workout of the Day email (stile TrainingPeaks)
     4. Alert adattamento workout (readiness bassa → swap VO2→Endurance)
     5. Breakthrough/PR detect (best power curve → toast 🏆)
     6. eFTP/zone drift alert (eFTP >2% → email aggiorna zone)
     7. HRV trend warning (3+ gg calo → email overreaching/illness)
     8. Missed workout re-plan (non eseguita → toast + ricolloca)
     9. Weekly Review email (domenica: carico/compliance/HRV/focus)
     10. Pre-race Form countdown (TSB proiettato + checklist taper)
     11. Fueling reminder (sessione >90min → toast "60–90 g/h carbs")
     12. Monotony/Strain alert (Foster monotony >2.0 → email "varia")
   - **Gap di mercato:** nessun competitor local-first fa email+toast proattivi
     combinando HRV Intervals + carico. PPC vince qui.

### FASE 2 — HRV / readiness + eFTP + DFA a1 (individualizzazione)
**Gap #2 + digital twin base.**

4. **Layer HRV/readiness:** import rMSSD + sonno da Intervals.icu wellness (API aperta).
   - Regola (Javaloyes 2019): rMSSD < media7d − 0.75×SD → declassa HIT→LIT;
     ≥2 gg fuori banda → recovery. Integra nel ricalibro Fase 1.

5. **eFTP automatico:** da power-duration (Monod-Scherrer/Morton 3-param) su sforzi
   recenti → FTP stimato senza test.

6. **DFA a1 (HRV esercizio) come marker durability** (regole 2025-2026):
   - DFA a1 LIT a fresco <0.75 → sopra VT1 → declassa.
   - Long ride >2h: caduta DFA a1 <0.75 ≥30min prima vs baseline → durability loss.
   - CAVEAT: in fatica (TSB<−20 / HRV−1SD) NON usare DFA a1 per zonizzazione.

### FASE 3 — Forza + mobilità periodizzate (differenziatore forte)
**Gap #3. Solo FasCat/Wahoo/SYSTM lo fanno seriamente.**

7. **Motore forza periodizzato (regole A):**
   - off-season/base: 2×/sett (anatomical 2-3×15@55% → max 3-4×4-8@80-90%)
   - pre-comp: 1-2×/sett conversione potenza (3-4×3-5 @70-85%)
   - in-season: mantenimento 1×/sett (2-3×3-5@85-90% 1RM)
   - **2025 VBT:** stop set a 20% velocity loss; separa forza/endurance ≥6h.
   - **Interferenza sesso-specifica (2025):** assente femmine → rimuovi penalità;
     attenuata maschi.

8. **Mobilità / core + aero:** core 2-3×/sett (plank 30-60s + anti-rotation).
   **Aero come adattamento (2025):** 8-12 sett esposizione progressiva (+10-15%/sett)
   + hip-flexor mobility 3-4×/sett hold 30-45s.

9. **Calendario integrato:** forza+mobilità+endurance con spacing interferenza.

### FASE 4 — Metriche avanzate + nutrizione linkata + AI coach + digital twin
**Differenziatori "premium" resi semplici.**

10. **Durability / W' / CP (Morton-Monod):** ri-test soglia dopo 2-3h → % decadimento;
    modello CP/W' dagli sforzi → prescrizione intervalli + detection breakthrough.

11. **Nutrizione/fueling per sessione (link NutriCoach):** CHO/h (60-90 <2.5h, 90-120
    >3h con gut-training); train-low su LIT base; train-high su HIT/gara; flag integratori
    (caffeina 3-6mg/kg, nitrati, creatina, beta-alanina — IOC/ISSN). **Gut-training
    progressivo:** 4-6 sett +10-15 g/h/sett verso 120 g/h.

12. **Digital twin ML (frontiera):** modello ibrido physics-informed + RF/XGBoost,
    re-fit ogni 7gg su rolling 42gg, re-fit se errore P-soglia >5%. Zone dinamiche.

13. **AI coach conversazionale (locale):** spiega/modifica il piano in chat (stile
    CoachCat/AI Endurance). LLM locale o API utente, mai dati fuori dal PC.

---

## HEAT / ALTITUDE (supporto Liv I 2025, da aggiungere come raccomandazioni)
- Camp altura 3 sett → +4.1% Hb-mass; post-camp heat-suit 40-60min×5/sett×3 sett
  per preservarla. Heat acclimation autonoma: 5-10gg 60min/die.

---

## TABELLA PRIORITÀ

**MUST-HAVE (per competere 2026):**
1. Ricalibro automatico (Fase 1)
2. Alert fatica RLGL-style (Fase 1)
3. **Notifiche: reminder + email riepilogo + 12 smart (Fase 1) — la tua richiesta**
4. eFTP automatico (Fase 2)
5. A/B/C races + multi-evento (estensione Fase 1)
6. PMC CTL/ATL/TSB — già presente
7. Integrazione Intervals.icu — già presente

**DIFFERENZIATORI (dove PPC vince):**
1. HRV/readiness + DFA a1 durability (Fase 2) — solo AI Endurance lo fa davvero
2. Forza + mobilità + aero periodizzati nel calendario (Fase 3) — solo FasCat/Wahoo
3. Nutrizione/fueling linkato ai workout + gut-training (Fase 4)
4. Metriche avanzate accessibili (durability, W'/CP) (Fase 4)
5. Local-first / no-subscription / data ownership + email/toast proattivi
6. AI coach conversazionale locale (Fase 4)
7. Digital twin ML predittivo (Fase 4, frontiera)

## ARCHITETTURA (single source of truth)
- Un solo motore `replan()` + `daily_adapt()`; dashboard/calendar/email/ICU = VISTE.
- HRV/wellness/forza/mobilità/nutrizione = LAYER che alimentano gli stessi input
  (availability, readiness, load) — non motori separati.
- Tutto locale: notifiche via SMTP utente, nessun server PPC.

## EVIDENZA (fonti chiave)
- Rønnestad & Mujika 2014 (forza, A); Mølmen/Rønnestad 2019 meta BP (A)
- Javaloyes 2019/2020 HRV-guided (B); Impellizzeri 2020 critica ACWR (A)
- Mujika taper (A); Impey 2018 / Burke nutrition (A); IOC 2018 / ISSN integratori (A)
- **2025-2026:** Sédiri/Kyriaki digital twin (III); Van Hooren DFA a1 (II);
  Rønnestad heat-suit Hb-mass MSSE 2025 (I/II); Han VBT Front Physiol 2025 (I);
  Huiberts interferenza sesso-specifica Sports Med 2024 (I); King gut-training (II);
  Roadman aero 12-week (III)
