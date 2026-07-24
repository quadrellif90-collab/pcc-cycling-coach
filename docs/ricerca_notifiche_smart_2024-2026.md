# Ricerca tattica — Notifiche/avvisi smart in app endurance (2024–2026)

## Benchmark overtraining = TrainerRoad RLGL
- Semaforo Red/Yellow/Green su fatica (non solo TSS); auto-adatta il piano
  (interval→Endurance su yellow, →Rest su red). Nessun competitor local-first
  fa email+toast proattivi combinando HRV Intervals + carico.

## 12 NOTIFICHE SMART per PPC (local-first: SMTP utente + toast desktop + HRV/wellness da Intervals.icu API)
1. **Morning Readiness Report** (email ~7:00 + toast): HRV vs baseline 7/42gg, restingHR, sleep, Form (TSB) → 🟢🟡🔴.
2. **RLGL Day Flag**: ramp rate CTL >5–7/sett o TSB < −25 o HRV sotto baseline−1SD per 2+ gg → "Red Day: rest/recovery" (toast + colore calendario).
3. **Workout of the Day email** (stile TrainingPeaks): sessione, target W/zone, meteo.
4. **Alert adattamento workout**: readiness bassa + sessione intensa → toast "Suggested swap: VO2 → Endurance Z2".
5. **Breakthrough/PR detect** (stile Xert): nuovo best power curve (5s/1m/5m/20m) → toast "🏆 New 20min PR".
6. **eFTP/zone drift alert**: eFTP cambia >2% → email proposta aggiornamento zone.
7. **HRV trend warning**: HRV in calo 3+ gg sotto baseline → email "possible overreaching/illness".
8. **Missed workout re-plan** (stile CoachCat): non eseguita entro sera → toast + ricollocazione.
9. **Weekly Review email** (domenica, stile Coach Watts): carico, compliance, best efforts, trend HRV, focus prox sett.
10. **Pre-race Form countdown**: a X gg evento, email con TSB proiettato + checklist taper.
11. **Fueling reminder**: sessione >90min o >1500kJ domani → toast "prepara 60–90 g/h carbs".
12. **Monotony/Strain alert** (Foster): monotony >2.0 o strain anomalo → email "varia intensità".

**Implementazione:** scheduler locale (cron/task Python) → GET wellness/activities da
Intervals.icu API, regole soglia, `smtplib` per email, `win10toast`/`plyer` per toast.

## Tabella gap (sintesi)
- Nessun concorrente self-hosted/local-first manda email+toast proattivi combinando
  HRV Intervals + carico. Intervals.icu stesso NON ha daily reminder (feature request aperta).
- PPC può vincere qui: local-first, privacy, nessun abbonamento, notifiche proattive.
