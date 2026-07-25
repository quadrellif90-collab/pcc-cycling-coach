# Ricerca scientifica WorldTour / Pro — Fitness, ciclismo, preparazione (2025-2026)

Sintesi di studi e pratiche aggiornate nel mondo del ciclismo professionistico
(WorldTour, Grand Tour) e sport pro, con fonti citate. Base per decidere cosa
implementare in PPC oltre al selettore accorgimenti già presente.

> Tutte le fonti sono verificate via web (PMC, Frontiers, Outside/Velo, NPR,
> studi peer-reviewed 2025-2026). I claim senza studio sono marcati.

---

## 1. Nutrizione / Fueling in corsa (il "carb revolution")

- **Tour de France 2025**: i vincenti (es. Ben Healy, tappa 6) hanno consumato
  **~140 g carboidrati/ora** in volata da lontano; media peloton ormai
  **>120 g/h** (NPR, lug 2025). Fonte: NPR "A carbohydrate revolution is fueling
  cyclists in the Tour de France" (2025-07-23); roadmancycling Ben Healy 140g/h.
- **Evidence di base**: sforzi >2.5h → 80-100 g/h ottimali per gli amateur;
  i pro spingono a 100-120 g/h con **ratio glucosio:fructose 2:1** per assorbimento.
  Fonte: EF Pro Cycling "gut training" tips; roadmancycling "How Grand Tour riders
  fuel 5000+ calories".
- **Gut training**: si può allenare l'intestino a tollerare >100 g/h con
  progressione (EF Pro Cycling).

**Implicazione per PPC:** il layer "fueling" oggi suggerisce ~60-90 g/h.
Evidenza 2025 → portare a **90-120 g/h in gare >2.5h**, con mix 2:1 e nota
"gut-training progression". Già parzialmente nel motore nutrizione.

---

## 2. Heat acclimation / pre-cooling

- **Meta-analisi 2024**: l'acclimatamento al caldo migliora TT del **~6% in
  condizioni fresche** e **~8% al caldo** (PPR/Racinais line; velo.outsideonline
  "Heat acclimation gives big cycling performance improvements in cool
  conditions", studio 2024).
- **Pre-cooling con ghiaccio** è **equivalente** all'acclimatamento per TT nel
  caldo (studio ResearchGate "Pre-Cooling With Crushed Ice is as Effective as
  Heat Acclimation...").
- **Durata protocollo**: ~10-14 giorni di esposizione calda prima dell'evento.

**Implicazione:** il layer "heat" di PPC oggi inserisce una nota 3 sett.
pre-evento. Evidenza 2024-2025 → estendere a **10-14 giorni** + aggiungere
suggerimento **pre-cooling** (ghiaccio/bevande fredde) per giorno gara.

---

## 3. Forza / Strength training (ciclisti pro e master)

- **Vikestad et al. 2025** (PMC12244580): "Strength training among professional
  UCI road cyclists" — indaga pratiche, sfide e razionali dei pro. Conferma
  l'adozione diffusa dello strength nei WorldTour.
- **Meta-analisi 2025** (Eur J Appl Physiol, 17 studi, 262 ciclisti allenati;
  PubMed 40632222): lo strength migliora **efficienza di pedalata, potenza
  anaerobica, TT**; **NESSUN effetto negativo su VO2max**.
- **Mantenimento**: 1 sessione/settimana basta a mantenere i guadagni; i guadagni
  si perdono in 6-8 settimane di stop. **48h** tra forza e uscita chiave.
- **Over-40**: lo strength batte "più chilometri" (roadmancycling, 2026).

**Implicazione:** il layer "strength" di PPC oggi è nota testuale. Evidenza
2025 → inserire **2 sessioni/sett (30-40 min)**, distribuite a ~48h da uscite
chiave, con mantenimento 1x/sett. Già coerente con il layer ma da rendere
sessioni reali nel piano.

---

## 4. DFA α1 / Durability (HRV durante sforzo)

- **DFA α1**: indice di variabilità cardiaca (esponente di detrended fluctuation
  analysis). Soglia aerobica ≈ **0.75**; valori >0.75 = bassa intensità, <0.75 =
  alta. Usato live per durabilità/intensità (PezCycling, 2025).
- **Affidabilità**: SWC 0.06-0.07 tra sessioni (PMC10582140, 2023).
- **Relazione universale potenza-DFA α1** da workout quotidiani (aiendurance
  2025) → tracking accessibile della durabilità.
- **Frontiers 2025** (fspor.2025.1574087): HRV nel controllo del carico, recovery,
  periodizzazione.

**Implicazione:** il layer "durability" di PPC oggi è una nota. Evidenza →
calcolare DFA α1 dalle sessioni (se ci sono dati HRV/RMSSD) e flaggare sessioni
che scendono <0.75 come "alta intensità / attenzione durabilità". Già parzialmente
nel motore HRV; da collegare al layer.

---

## 5. Periodizzazione / Polarized / Block / Altitude

- **Giro d'Italia top-5** (PMC9796663): distribuzione **piramidale** + block
  periodization "race-based" (più HIT nelle settimane di gara). Rønnestad: block
  HIT superiore a distribuzione uniforme su 4-12 sett.; su 12 sett. risultati
  simili a periodizzazione tradizionale.
- **Polarized 80/20** (Seiler & Lorang 2026, roadmancycling): 80% easy / 20% hard.
- **Altitude training**: combinato con block HIT per adattamenti (PMC9796663).
  Pratica diffusa TdF 2025 (es. Seixas, 1500km/37000m in 12 giorni a quota).

**Implicazione:** PPC già usa polarizzazione + block (base_recall ogni 3
blocchi). Evidenza conferma l'approccio. Altitude: opzionale come nota layer.

---

## 6. Caffeina / Ketoni

- **Meta-analisi 2025** (PMC11155427 / Frontiers fnut.2025.1745472): caffeina
  **4-6 mg/kg, 60' prima** → **+2% TT** vs dose bassa (1-3 mg/kg). Dose assoluta
  comune 200-400 mg.
- **Ketoni**: UCI 2024 ne ha limitato l'uso (note di sicurezza); evidenza
  prestazionale mista — PPC non li raccomanda (già in sport_science.py).

**Implicazione:** il layer "integrazione" di PPC ha già caffeina dosata sul
peso. Evidenza 2025 → conferma 3-6 mg/kg a 60' pre-gara; ketoni NON inclusi.

---

## Sintesi — cosa è GIÀ implementato vs cosa migliorare

| Tema | Stato in PPC (5.x) | Evidenza 2025-26 | Azione proposta |
|---|---|---|---|
| Fueling 90-120 g/h | parziale (60-90) | 120+ TdF2025 | alza a 90-120 g/h in gara |
| Heat 10-14 gg + pre-cool | 3 sett. nota | 6-8% (2024) | estendi + pre-cooling |
| Strength 2x/sett 48h | nota | meta 2025 | sessioni reali |
| DFA α1 <0.75 flag | nota | 2025 | calcolo live |
| Polarized/block | sì | confermato | nessuna |
| Caffeina 3-6 mg/kg | sì | confermato | nessuna |
| Altitude | no | utile Pro | nota opzionale |
| Ketoni | esclusi | UCI 2024 | esclusi |

---

## Fonti
- NPR (2025-07-23) "A carbohydrate revolution is fueling cyclists in the Tour de France"
- roadmancycling.com — Ben Healy 140g/h; Grand Tour fueling; strength over 40 (2026)
- EF Pro Cycling — gut training tips
- velo.outsideonline.com — Heat acclimation cool-weather (2024 study)
- Vikestad et al. 2025, PMC12244580 — Strength training pro UCI cyclists
- Meta-analisi 2025, Eur J Appl Physiol, PubMed 40632222 (17 studi, 262 ciclisti)
- PMC10582140 — DFA α1 reliability; aiendurance 2025 — power-DFA α1 relation
- Frontiers in Sports 2025 (fspor.2025.1574087) — HRV in sport
- PMC9796663 — Giro d'Italia top-5 training (block/polarized/altitude)
- roadmancycling — Polarised Training Seiler & Lorang (2026)
- PMC11155427 / Frontiers fnut.2025.1745472 — caffeine meta-analysis 2025
- UCI 2024 — ketone restriction note
