# Analisi Competitiva 2026 — App per Coach, Biomeccanica e Sport di Resistenza

**Scopo:** confrontare PCC (Performance Cycling Coach, app local-first PyWebView+FastAPI) con il mercato 2025‑2026 di software di coaching/analisi, strumenti di biomeccanica/bike‑fitting, test di laboratorio e le feature AI/ML emergenti. Per ogni categoria: cosa fanno, come sono sviluppati, workflow d'uso, e cosa PCC può realisticamente aggiungere restando **offline/local‑first**.

**Metodo:** 3 ricerche web parallele (fonti ufficiali, support docs, paper peer‑reviewed, recensioni 2024‑2026). Ogni affermazione ha il suo link. Dove un dato non è pubblico si segnala `[NON VERIFICATO]`.

**Stato attuale di PCC (riferimento per il confronto):** motore unico (single source of truth) `generate_plan`; CTL/ATL/TSB; TSS, FTP, W/kg, VO2max stimato; DFA α1 (durability); distribuzioni Polarizzato/Piramidale/Soglia; block periodization; sync intervals.icu; import `.fit`; export ZWO; layer strategia (nutrizione, heat, integrazione, mobilità, forza, altitude); auto‑replan; calcolo nutrizione/integrazione dal profilo atleta.

---

## 1. Software di Coaching & Analisi (cycling / endurance)

| Prodotto | Modello fisiologico | Punti di forza | Workflow | Pricing | Architettura | Cosa PCC NON ha |
|---|---|---|---|---|---|---|
| **TrainingPeaks** + **WKO5** | CTL/ATL/TSB, TSS, FTP, power‑duration, hrTSS/rTSS/sTSS; WKO5: Power‑Duration Model V2, mFTP, FRC≈W′, TTE, Stamina, iLevels (zone individuali) | Calendario+workout builder, Plan Store, messaging coach↔atleta, PMC, roster coach, comparison atleti | Coach costruisce piano su calendario (o template/Store) → assegna workout → atleta completa → sync → coach rivede PMC e commenta | Athlete free/$~20 mo; Coach a tier; WKO5 licenza ~$149 una tantum | Cloud web + iOS/Android + desktop uploader; **WKO5 = app desktop nativa (Windows/Mac)** che sincronizza da TP cloud | iLevels zone individuali, FRC/W′, Stamina, roster multi‑atleta, Plan Store, messaging |
| **TrainerRoad** (Adaptive Training / **Red Light Green Light**) | FTP (**AI FTP Detection** senza test), TSS, CTL/ATL/TSB, Progression Levels per zona, survey RPE | ML adattivo ("centinaia di simulazioni"), **RLGL** (semaforo verde/giallo/rosso fatica), ERG, libreria enorme | Self‑coached: goal+giorni → Plan Builder → Adaptive Training+RLGL aggiustano da completati e RPE | $21,99/mo o $209,99/anno (tutto incluso) | Cloud AI + app native Mac/Win/iOS/Android | **AI FTP Detection**, RLGL semaforo fatica, Progression Levels per zona |
| **Today's Plan** | CTL/ATL/TSB‑style, power curve | (storico) calendario+workout builder, slicing dati flessibile | — | — | Cloud (defunto) | ⚠️ **Chiuso fine 2023** — non più prodotto attivo |
| **Xert** | **Fitness Signature** (TP, HIE≈W′, PP), **MPA** (potenza max disponibile real‑time), XSS (low/high/peak) | "Senza test FTP", MPA real‑time, Adaptive Training Advisor, breakthrough detection | Self‑coached: goal+rate → programma adattivo → Advisor suggerisce sessione giornaliera | ~$10‑15/mo (da confermare) | Cloud + app mobile + data fields Garmin/Wahoo | MPA real‑time, Fitness Signature continua, no‑FTP‑test |
| **intervals.icu** | CTL/ATL/TSB con costanti regolabili, **eFTP** automatico, Morton 3P & Monod‑Scherrer CP, MAP, HR drift, HRV | **140+ metriche**, grafici custom, open API, auto‑interval detection, multisport, wellness/HRV | Atleta‑centric + coach via organizzazioni (aggiunge atleti, assegna workout, rivede PMC) | **Free**; Supporter piccolo abbonamento/anno | **Cloud web (Astro) + open API**; sviluppatore solo (David Tinker); 160k+ atleti | Open API, 140+ metriche custom, eFTP, modelli CP multipli |
| **GoldenCheetah** | CP/W′ balance, power‑duration, TSS/BikeScore/TRIMP, PMC (LTS/STS), Aerobic Decoupling, W′bal, VO2, Banister/PD; metriche custom (Python/R) | **Open source desktop**, UI/charts custom, dataset aperto (GCD) | **Single‑user desktop**, no assignment/messaging; analisi locale | **Gratis (GPL)**, v3.7 SP1 | **Nativa desktop C++/Qt6**, dati 100% locali | ⭐ **Il gemello architetturale di PCC** (locale, estensibile) |
| **Athletica.ai** | Carico adattivo (metodologia HIIT Science / Paul Laursen); metriche interne proprietarie | **Coach conversazionale AI** (chat), piani adattivi auto‑rigenerati, HRV readiness | Self‑coached+AI: onboarding → AI piano → sync → adatta; coach risponde a domande | $19,90/mo; $99/6mo; $189/anno (prova 2 sett) | Cloud web + app mobile native; LLM coach | Coach LLM conversazionale, HRV readiness gating |
| **JOIN Cycling** | Bilanciamento carico + adattamento **RPE**; profilo punti di forza/debolezza | Rileva attività non pianificate (es. giro in gruppo) e **ri‑pianifica**; protezione overtraining | Self‑coached/AI: giorni+ore+goal → piano → adatta da completati/RPE | Subscription (mobile) | Cloud + app iOS/Android | Classificazione attività + ri‑pianificazione da RPE |
| **HumanGO** (Humango) | Analisi fitness+metabolica+wearable+schedule insieme (GenAI/LLM) | **"Hugo"** coach AI multilingua, generazione piano real‑time, smart scheduling, coach mode | Goal+disponibilità → AI piano/adatta real‑time → Hugo feedback | Essential $16,99/mo; Premium $28,99/mo; Coach $20/mo | Cloud‑native + mobile, LLM | Piano real‑time LLM, coach mode per coach |
| **Hammerhead Karoo** | Registra TSS/potenza/HR; **non** ha motore CTL/ATL (usa piattaforme sync) | Esecuzione workout strutturati su device, ERG FE‑C, import ZWO/FIT | **Endpoint di esecuzione**: pianifica altrove → sync Dashboard → esegui → upload | Hardware ~$399‑475; sync gratis | Android (Karoo OS) + Dashboard cloud | (non è un planner — solo esecuzione) |

**Fonti:** TrainingPeaks athlete/coach features, WKO5 PD Model V2; TrainerRoad adaptive + RLGL (Bicycle Retailer 2024); Xert glossary/MPA; intervals.icu features + power‑curve; GoldenCheetah; Athletica; JOIN; Humango FAQ; Hammerhead workouts. (Link completi nei report sorgente in `cache/delegation/`.)

### Spunti concreti per PCC (local‑first fattibili)
- **Semaforo fatica** Green/Yellow/Red (tipo TrainerRoad RLGL) sopra il tuo DFA α1 + TSB esistente.
- **FTP/CP/W′ continui senza test** (tipo Xert / intervals.icu eFTP) — hai già W′ e power‑duration di base.
- **Progression Levels per zona** (TrainerRoad) per scegliere il prossimo workout.
- **Più modelli Critical Power** (Morton 3P, Monod‑Scherrer) per arricchire il motore power‑duration.
- **RPE‑driven adaptation + classificazione attività** (JOIN) — rileva giri non pianificati e re‑pianifica.
- **Metriche/charts custom definibili** (GoldenCheetah/WKO5) — il precedente locale più vicino a PCC.

---

## 2. Biomeccanica, Bike‑Fitting & Lab Fisiologico

> **Nota onesta:** alcuni sistemi del brief sono stati corretti dalla ricerca — **STAC** è un trainer (STAC Zero) + servizio aero Virtual Wind Tunnel, **NON** motion‑capture; **Cyclus2** è un ergometro, non mocap.

| Sistema | Cosa misura | Hardware | Report | Workflow pro | Come alimenta il training |
|---|---|---|---|---|---|
| **Retül** (Specialized) | Cinematica 3D articolare (ginocchio, anca, spalla, gomito) dinamica per ogni pedalata | Retül Vantage (LED infrarossi, 8 marker), Zin tool (mappa digitale setup) | Report fit completo | Valutazione pre‑fit → 8 marker → capture 3D live → Zin mappa → report | Comfort/prevenzione infortuni, trasferimento di potenza |
| **gebioMized** (pressione) | Pressione sella (64 sensori), piede (suole 32 sensori, 200 Hz), mani; L/R | Film sottile su sella + solette wireless | Mappe pressione colorate/3D, L/R | Statico+dinamico su rulli → fitter aggiusta e vede mappa live → report | Scelta sella/scarpa/plantare/cleat; simmetria L/R |
| **LEOMO Type‑S** (IMU) | **MPI**: Dead Spot Score (DSS), Leg/FOOT Angular Range, Pelvic/Torso Angle, L/R | 5 sensori IMU indossabili (no telecamere) → **funziona su strada** | Display MPI live, baseline per atleta, validato (Plaza‑Bravo 2022, Thompson 2024) | Sensori → giro → leggi MPI live/post → intervieni (cleat, sella, cueing) | Tecnica = target allenabile (lisciare DSS, bilanciare L/R) |
| **STAC** | (trainer magnetico silenzioso + **VWT** CdA da scan 3D) | STAC Zero trainer; VWT = CFD browser | CdA per posizione/equip | Fit su STAC Zero; VWT per aero | Solo aero/equip — **non** carico |
| **Cyclus2** (ergometro) | Potenza, coppia, isocinetico; test incrementale/Wingate/lattate; sync CPET/ECG/lattate/VO2 | Montaggio elastico bici propria, adattatori, WiFi | PDF/CSV/FIT export | Bici montata → protocollo → CPET/lattate → report | Soglie, profilo potenza → zone e intervalli |
| **Shimano Bikefitting** | Statico (2D Body Analyzer, 100k geometrie) + dinamico (camera 3D, pedaling analyzer forza) | Fit Bike, camera 3D, Bike Adjuster laser | Report angoli + mappa laser setup | Body scan → 3D camera live → aggiusta → Bike Adjuster replica | Posizione/equip per comfort/efficienza |
| **Notio / Aerosensor / AeroLab** (aero CdA) | CdA real‑time da potenza/velocità/pressione (metodo Chung virtual‑elevation) | Sensore ANT+ su bici + power meter + Garmin Edge (Aerosensor); Notio iOS | CdA live + analisi post‑ride (Aerotune) | Monta sensore → giro → CdA live → cambi posizione/equip → confronta | Solo aero (posizione/elmo) → "free speed" TT |
| **INSCYD** (metabolico) | **VO2max, VLamax, MLSS/LT1, FatMax, CarbMax, lattate accumulo/recupero, economia, contrib. aer/anaer** | **Nessun lab**: power meter o GPS + breve test PPD (Power Performance Decoder) | Profilo metabolico, zone, proiezioni, report auto | Test PPD remoto → upload → decode → coach legge limitazione | ⭐ **Il pipeline "lab→training" più forte**: VLamax guida focus, lattate→report/work‑rest, FatMax→fueling |
| **Cortex / COSMED** (CPET) | VO2max, soglie ventilatorie, ECG, spiroergometria breath‑by‑breath | METALYZER/K5 (wearable field), OMNIA, Quark CPET | OMNIA/MetaSoft: soglie, VO2max, slope VE/VCO2 | Calibrazione → maschera → CPET → soglie | Gold‑standard zone/pace |
| **Assioma / Garmin Rally** (pedali potenza) | L/R balance, PCO, Power Phase, Torque Effectiveness, Pedal Smoothness | Pedali strain‑gauge BLE/ANT+ | App dinamiche live | Pedali → giro → leggi L/R,PCO → regola cleat → re‑test | L/R imbalance/tecnica → rehab/cleat |

**Fonti principali:** retul.com/tts; gebiomized.us saddle/foot‑pressure; manual.leomo.io + PMC9322640 + doi 10.1080/02640414.2024.2324604; cyclus2.com; bikefitting.com; notio.ai / aerosensor.tech / dcrainmaker AeroLab; inscyd.com; cortex‑medical.com / cosmed.com; favero.com / garmin.com.

### Spunti per PCC (import contesto atleta, non carico)
- **INSCYD‑style decoder** da un test field con power meter → VLamax/FatMax/zone. ⭐ Il modello più adatto da replicare offline (solo power meter + FIT).
- **LEOMO MPI** (DSS L/R) come metrica di tecnica importabile da FIT/IMU.
- **Pedali potenza** (Assioma/Rally): import L/R balance, PCO → contesto asimmetrie.
- **Aero CdA** (Notio/Aerosensor): divergenziatore per TT/road (ma serve sensore su bici).
- **Import layer FIT + PDF CPET/INSCYD** per coprire la maggior parte degli studi.

---

## 3. AI/ML 2025‑2026 & Architetture di Sviluppo

### 3.1 Feature AI già sul mercato
- **Motori adattivi** (rigenerano il piano dai completati): TrainerRoad (simulazioni), Humango/Hugo, Athletica, Runna (acq. Strava 2025), TriDot/2Peak/Maxiom/AI Endurance (confronto triathlete.com marzo 2026), Xert (MPA).
- **Coach LLM conversazionali**: WHOOP Coach (GPT‑4, descrittivo), Strava Athlete Intelligence (solo descrittivo — NON prescrittivo), Maxiom "MAX", Humango "Hugo", Athletica coach chat.
- **Computer‑vision gait/form**: Ochy (video smartphone → angoli articolari, adidas partnership gen 2025), Runeasi (gait 3D per fisio/coach).
- **Injury‑risk ML**: revisioni accademiche 2025 (Br.J.Sports Med., Martins JCM 2025, WCE Zumeta‑Olaskoaga 2025) — **ancora NON feature di testa nei consumer app** (white space 2026).
- **Fueling AI**: Fuelin (carb periodization + logging, perlopiù rule‑based, non generativo).
- ⚠️ **"Vituro"** e **"TrainedByAI"** non verificati → omessi (non inventati).

### 3.2 Modelli fisiologici stato‑dell'arte
| Metrica | Cosa cattura | Fonte |
|---|---|---|
| **Durability** | Resistenza alla fatica (drift potenza/HR più stabile) | Intervals.icu RPS, WKO5 |
| **DFA α1 / HRV threshold** | α1>0.75 = sforzo veramente facile; drift scende con intensità | PMC10875128 (2024), marcoaltini.com |
| **Critical Power / W′** | CP = asintoto potenza sostenibile; W′ = capacità anaerobica | Xert MPA, Athletica Workout Reserve |
| **Glycogen / carb** | 60‑90+ g/h fueling; periodizzazione carb | Fuelin |
| **Heat & altitude** | Garmin: acclimazione >22°C o >800 m corregge VO2max | garmin.com |
| **Sleep / HRV readiness** | Garmin Training Readiness, WHOOP recovery, Athletica HRV gating | support docs |
| **Banister / impulse‑response** | Fitness‑fatigue = backbone dei piani adattivi | Athletica/Humango/Intervals |

### 3.3 Architettura tipica dei competitor
- **Frontend:** Web SPA (Intervals.icu = **Vue.js + Vuetify + D3.js**); mobile React Native/Flutter o nativo.
- **Backend:** Cloud API (Java/Spring Boot comune); ingestion `.fit` (Garmin FIT SDK C/portabile, `fitparse` Python, ~0,45s parse); API device (Garmin/Strava/Whoop).
- **Dove girano gli analytics:** cloud/batch per piano + LLM (OpenAI per WHOOP); CV gait server‑side; on‑device solo widget Garmin.
- **Pattern opposto di PCC:** analytics **locali** (FastAPI + motore single‑source‑of‑truth). Replicabili offline: FIT parse, CP/W′/CTL‑ATL (NumPy), DFA α1 (DSP locale), Banister. **Solo cloud:** LLM chat e CV gait.

### 3.4 Workflow end‑user dominante
1. **Readiness giornaliera** (HRV/sonno) → semaforo verde/amber/rosso.
2. **Prescrizione workout** già adattata a readiness+schedule.
3. **Sync al device** (Garmin/Wahoo/trainer) → registrato come FIT.
4. **Upload & analisi** → AI riassume, aggiorna CTL/ATL/CP/DFA α1.
5. **Auto‑adjust** sessioni successive (simulazioni/ri‑pianificazione).
6. **Layer conversazionale** (opzionale) WHOOP/Maxiom.

> **Strava (descrittivo) vs app dedicate (prescrittivo)** — utenti seri usano entrambi ("smart stack").

---

## 4. Confronto Sintetico vs PCC

| Capabilità | PCC oggi | Gap vs mercato | Fattibile offline? |
|---|---|---|---|
| CTL/ATL/TSB, TSS, FTP, W/kg | ✅ | — | ✅ |
| DFA α1 / durability | ✅ | arricchire con semaforo fatica | ✅ |
| Power‑duration / CP / W′ | ⚠️ base | MPA real‑time, modelli CP multipli, FRC | ✅ (math locale) |
| AI FTP / no‑test | ❌ | FTP continuo da dati | ✅ |
| Adattivo da completati/RPE | ⚠️ auto‑replan presente | classificazione attività non pianificate, RPE | ✅ |
| Coach LLM conversazionale | ❌ | layer opzionale online | 🚫 solo cloud (wrapper opzionale) |
| CV gait/form | ❌ | — | 🚫 solo cloud |
| iLevels zone individuali | ❌ | — | ✅ (da test) |
| Roster multi‑atleta / messaging | ❌ | — | ✅ (ma fuori scope single‑athlete) |
| Open API / metriche custom | ❌ | — | ✅ |
| INSCYD‑style metabolic decoder | ❌ | ⭐ alto valore, offline | ✅ (power meter + FIT) |
| Aero CdA | ❌ | divergenziatore TT | 🚫 richiede sensore |
| Import CPET/INSCYD PDF | ❌ | contesto atleta | ✅ |

---

## 5. Raccomandazioni per la Roadmap PCC (local‑first)

**Alta priorità, fattibile offline (estende il motore esistente):**
1. **Semaforo fatica** (Green/Yellow/Red) su DFA α1 + TSB.
2. **FTP/CP/W′ continui senza test** da power‑duration (tipo Xert/eFTP).
3. **INSCYD‑style metabolic decoder** da test field power‑meter → VLamax/FatMax/zone (il "lab→training" più forte, 100% offline).
4. **Progression Levels per zona** + **modelli CP multipli** (Morton 3P, Monod‑Scherrer).
5. **Classificazione attività + RPE** → ri‑pianificazione automatica (tipo JOIN).
6. **Import layer FIT + PDF CPET/INSCYD** per contesto atleta.

**Medio, divergenziatori:**
7. **Metriche/charts custom definibili** (precedente GoldenCheetah — gemello locale di PCC).
8. **LEOMO MPI / pedali potenza L/R** come contesto asimmetrie importabile.

**Fuori scope offline (solo come add‑on cloud opzionale, da spiegare all'utente):**
9. **Coach LLM conversazionale** (WHOOP/Athletica style) — richiede API/LLM.
10. **Computer‑vision gait/form** (Ochy) — richiede CV server‑side.

> Per coerenza con la filosofia PCC (local‑first, nessun cloud), le voci 9‑10 vanno offerte solo come **componenti opzionali online** che non rompono l'offline‑first; tutto il carico analitico core resta locale.

---

## 6. Limiti della ricerca (onesti)
- **Today's Plan**: chiuso fine 2023, non più prodotto attivo.
- **Xert / JOIN / Athletica / Humango**: prezzi e formule di carico interne proprietarie non documentati pubblicamente → non inventati.
- **Notio** (hardware sonda non verificato, sito bloccato), **AeroLab** (specifiche 2025‑26 non riverificate), **Retül** (campi report oltre Zin+3D non pubblicati), **Garmin Rally** (algoritmo dinamiche non verificato indipendentemente).
- **"Vituro"/"TrainedByAI"**: non verificati → omessi.

---

*Fonti complete nei report sorgente: `cache/delegation/subagent-summary-0/1/2-20260726_*.txt` e `cycling_biomech_lab_tools_2025.md`.*
