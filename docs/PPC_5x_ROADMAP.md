# PPC 5.x — Piano operativo (con selettore di accorgimenti)

Sintesi delle 4 ricerche (competitiva + scientifica 2022-2024 + notifiche
2024-2026 + scientifica 2025-2026) tradotta in **lavoro implementabile**, con
al centro la richiesta utente: *l'utente sceglie se usare il pianificatore
normale, oppure attivare uno o più accorgimenti tra quelli implementati
(nutrizione, integrazione, heat, fueling, forza, mobilità, DFA a1…)*.

Principio non negoziale (regola utente): **un solo motore `generate_plan`**.
Gli accorgimenti sono LAYER che arricchiscono lo stesso piano, non motori
regola degli
accorgimenti OFF) resti identico al baseline, e che ogni accorgimento ON
modifichi solo la parte di propria competenza (le altre sessioni invariante).

---

## STATO IMPLEMENTAZIONE (aggiornato 2026-07-25)

**Fatto e verificato (31 test):**
- `plan_options.py` — dataclass `PlanOptions` con 8 flag + `mode` normal/accorgimenti.
- `training_planner.generate_plan(plan_options=...)` — normalizza e applica i layer.
- 5 layer puri implementati: integrators, heat (3 sett. pre-evento), strength (VBT),
  mobility, dfa_durability. Ciascuno no-op se OFF.
- `app.py` — endpoint `/api/plan/generate` legge `plan_options` dal body e lo passa;
  serializzazione JSON delle sessioni include i 6 campi note.
- `dashboard.html` — pannello "Accorgimenti del piano (PPC 5.x)" con 8 toggle;
  `_readPlanOptions()` invia `{mode:"normal"}` se tutti spenti (piano = 4.4.0).
- **Contratto di non-regressione verificato**: normal mode → nessuna nota (byte-identico).

**Da fare (prossimi step, non bloccati):**
- Persistenza `plan_options` nel profilo (salvarlo in `current_plan.json` / user_prefs).
- Layer "notifiche" e "ricalibro auto" sono viste/engine esterni: già esistenti
  (`notifications.py`, `continuous_policy.py` + `app.py` auto-apply) — il toggle li
  attiva/disattiva ma va collegato al pannello UI (al momento il flag è trasmesso
  ma l'azione viene sempre eseguita se il codice lo prevede).
- UI: mostrare le note dei layer nel calendario/piano (tooltip o riga "Note").
- Heat/strength/mobility: oggi sono NOTE testuali; step successivo = inserire
  sessioni reali (forza 2x/sett, mobilità post-ride) nel piano quando ON.

## 1. Il selettore di accorgimenti (cuore del 5.x)

Nuovo oggetto `PlanOptions` passato a `generate_plan`:

```
PlanOptions
 ├─ mode: "normal"            # tutti gli accorgimenti OFF → piano classico
 ├─ enable_nutrition: bool    # note fueling per sessione (GIA' parziale: _nutrition_note)
 ├─ enable_integrators: bool  # caffeina/nitrati/creatina/beta-alanina (IOC/ISSN)
 ├─ enable_heat: bool         # heat/acclimatazione pre-gara (Rønnestad 2025)
 ├─ enable_strength: bool     # forza periodizzata + VBT (gia' iniettore, da periodizzare)
 ├─ enable_mobility: bool     # mobilità hip-flexor + core + aero (Roadman 2025)
 ├─ enable_dfa_durability: bool  # DFA a1 come marker durability (Van Hooren 2025)
 ├─ enable_auto_replan: bool  # ricalibro continuo (continuous_policy gia' presente)
 └─ enable_notifications: bool   # layer notifiche (email/toast) — vedi §3
```

**Comportamento:**
- `mode="normal"` ⇒ tutti i flag forzati a False ⇒ piano identico al 4.4.0.
- Ogni flag ON attiva SOLO il suo layer. L'utente vede nel pannello quali
  accorgimenti sono attivi e l'impatto stimato (es. "+2 sessioni forza/sett",
  "+note fueling su 14 sessioni", "heat-block 3 sett pre-evento").
- Il piano è sempre **una sola vista**: dashboard / calendario / notifiche /
  report sono letture dello stesso `current_plan.json`.

**UI:** pannello "Accorgimenti" in `dashboard.html` — toggle per ciascuno,
con tooltip che cita la fonte (es. "Heat: Rønnestad MSSE 2025, +4.1% Hb-mass").
Salvato nel profilo (`~/.domestique/profiles/<id>/plan_options.json`).

---

## 2. Cosa fa ogni accorgimento (regole implementabili)

| Accorgimento | Cosa modifica nel piano | Fonte | Stato oggi |
|---|---|---|---|
| **Nutrition/Fueling** | note CHO/h per sessione (>90min→60-90g/h; >3h→gut-training 90-120); train-low su LIT | Impey 2018, IOC | `_nutrition_note` esiste → elevare a toggle + gut-training |
| **Integrators** | note supplemento per blocchi: caffeina 3-6mg/kg (HIT/gara), nitrati (3-4gg pre-gara), creatina (forza), beta-alanina (≥4sett) | IOC/ISSN | NUOVO |
| **Heat** | 3 sett pre-evento: sessioni con heat-block (tuta termica 40-60min×5/sett) per preservare Hb-mass post-altura | Rønnestad 2025 | NUOVO |
| **Strength** | forza 2×/sett base → 1×/sett in-season; VBT stop VL20%; spacing ≥6h | Han 2025, Rønnestad 2014 | iniettore esiste → periodizzare + VBT |
| **Mobility** | hip-flexor 3-4×/sett (30-45s) + core 2-3×/sett + aero progressiva 8-12sett | Roadman 2025 | NUOVO |
| **DFA a1 durability** | se DFA a1 LIT a fresco <0.75 → declassa; long ride caduta <0.75 ≥30min→flag | Van Hooren 2025 | `readiness.check_dfa_stress_cap` esiste → collegare al planner |
| **Auto-replan** | ri-ancora fasi su runway rimanente se sessione saltata/RPE cambiata | continuous_policy | `suggest_today_family`/`_auto_apply_missed_moves` esistono → esporre |

Tutti questi layer sono **funzioni pure** che prendono il piano e restituiscono
il piano arricchito → testabili singolarmente (contratto: piano base invariato
se layer OFF).

---

## 3. Notifiche smart (il focus utente — layer a sé)

Modulo `notifications.py` (gia' creato, da completare): consuma gli stati che
il planner/engine calcola gia' (readiness, TSB, HRV band, calendario) e li
spedisce via **toast desktop + email SMTP utente + colore calendario**. 12
tipi (da `ricerca_notifiche_smart_2024-2026.md`): Morning Readiness, RLGL Day
Flag, Workout of the Day, Swap advisory, PR detect, eFTP drift, HRV trend,
Missed workout, Weekly Review, Pre-race countdown, Fueling reminder, Monotony
alert. Scheduler locale (thread) innesca agli orari configurati. Endpoint
`/api/notifications/*` per settings/test. Nessun cloud PPC.

**Attivabile dal selettore** (`enable_notifications`) — ma funziona anche da
solo sul piano "normale" (legge solo readiness/TSB, non richiede altri layer).

---

## 4. Ordine di implementazione (verificabile per step)

1. **`PlanOptions` + selettore UI** — il pianificatore "normale" resta identico
   (contratto: piano base invariato). *Verifica: test che `mode=normal` produce
   output bit-identico al 4.4.0.*
2. **Nutrition/Fueling toggle** — eleva `_nutrition_note` a layer attivabile +
   gut-training. *Verifica: con OFF nessuna nota; con ON le note appaiono solo
   sulle sessioni, altro invariato.*
3. **Integrators + Heat** — note di supplemento e heat-block pre-evento.
4. **Strength periodizzato + VBT**, **Mobility** — sessioni nel calendario con
   spacing interferenza.
5. **DFA a1 durability** — collega `readiness.check_dfa_stress_cap` al planner.
6. **Notifications** — completa `notifications.py` + scheduler + endpoint + UI.
7. **Auto-replan esposto** — toggle che attiva il ricalibro continuo già presente.

Ogni step: pytest sul layer puro + curl end-to-end sul server locale + controllo
che il piano base non cambi (contract test).

---

## 5. Gap di mercato (perché PPC vince)

Nessun competitor **local-first/no-subscription** offre email+toast proattivi
combinando HRV intervals + carico, e nessuno lascia all'utente il **controllo
granulare** su quali accorgimenti scientifici applicare al proprio piano.
TrainingPeaks/Xert/AI Endurance sono cloud e opachi; FasCat/Wahoo fanno forza
ma non il selettore modulare. PPC: scienza 2025-2026, dati tuoi, piano uno,
viste molteplici, accorgimenti a scelta.

---

## 6. Evidenza (fonti)

- Rønnestad MSSE 2025 (heat-suit Hb-mass +4.1%) · Han Front Physiol 2025 (VBT)
- Huiberts Sports Med 2024 (interferenza sesso-specifica) · Roadman 2025 (aero 12-sett)
- Van Hooren J Sports Sci 2025 (DFA a1) · Impey 2018 / IOC / ISSN (nutrizione)
- Sédiri/Kyriaki 2025 (digital twin) · Javaloyes 2019/2020 (HRV-guided)
- TrainerRoad RLGL 2024 (benchmark notifiche) · Intervals.icu wellness API
