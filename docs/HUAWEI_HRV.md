# Huawei Health / HRV Engine — Documentazione (v5.5.0)

Estensione di PCC Pro per importare, calcolare e integrare dati HRV da
Huawei Health / Huawei Health Kit / Health Sync.

## 1. Installazione

Nessuna dipendenza nuova (solo stdlib Python). I moduli aggiunti:

- `hrv_engine.py`      — motore HRV riutilizzabile (RR→NN→RMSSD/SDNN→baseline)
- `huawei_discovery.py`— discovery + parsing export (CSV/JSON/XML/ZIP)
- `huawei_hrv.py`      — storage DB locale + adapter Intervals.icu
- `huawei_api.py`      — orchestration + endpoint `/api/huawei/*`

Il server carica gli endpoint lazy (`from huawei_api import ...`), nessun
impatto sul boot.

## 2. Configurazione

Nessuna configurazione richiesta. L'import cerca automaticamente i file
Huawei sul disco (vedi `POST /api/huawei/import`).

Per la sincronizzazione verso Intervals.icu servono le credenziali ICU
già configurate per il profilo (Settings → Intervals.icu).

## 3. Import Huawei

L'importer riconosce automaticamente (task #22, case-insensitive):

- **ZIP** esportati da Huawei Health (estrazione + dispatch per file)
- **CSV** con colonne `rr`, `rr_interval`, `nn`, `ibi`, `heart_rate`, ...
- **JSON** con chiavi `hrv_trace`, `rr`, `rmssd`, `sdnn`, ...
- **XML/TCX/GPX** (es. export Health Sync / Huawei Health Kit)

Detector basato su **contenuto** (header/chiavi/tag), non solo nome file.
I file corrotti vengono loggati e saltati (non interrompono l'import).

### Esempio

```bash
curl -X POST http://localhost:8092/api/huawei/import \
  -H "Content-Type: application/json" \
  -d '{"path":"/path/export.zip","source":"huawei_health","sync_to_icu":false}'
```

## 4. Formati supportati

| Formato | Campi riconosciuti | Stato |
|---------|-------------------|-------|
| CSV Huawei | `rr_interval`, `heart_rate`, `sleep`, `spo2` | ✅ |
| JSON Huawei | `hrv_trace[].rr`, `aggregates.rmssd/sdnn` | ✅ |
| ZIP Huawei | qualsiasi dei sopra | ✅ |
| XML/TCX | `HeartRateBpm`, `Extensions RR` | ⚠️ parziale |
| Health Sync | `rmssd`, `hrv` (generico → NON rMSSD) | ✅ (vedi #6) |

## 5. Algoritmo HRV (task #28)

```
RAW RR  → extract → RRPoint (grezzo, non modificato)
       → clean_rr → CleanNN (ectopic/artifact rimossi o corretti, RAW preservato)
       → compute_hrv_metrics:
           RMSSD = sqrt( Σ(NN[i+1]-NN[i])² / (N-1) )   [ms]
           SDNN  = deviazione standard popolazione dei NN [ms]
           pNN50, CVNN, mean/median NN, mean/min/max HR
```

**Soglie minime documentate** (in `hrv_engine.py`):
- `RR_MIN_MS=250`, `RR_MAX_MS=2500` (fisiologico a riposo)
- `MIN_NN_COUNT=8` (almeno 8 battiti)
- `MIN_DURATION_S=10` (almeno 10s di registrazione)
- `MIN_QUALITY_FOR_SYNC=0.5` (sotto → non sincronizzato come HRV ufficiale)

**Cleaning professionale:**
1. rimozione valori impossibili (fuori [250, 2500] ms)
2. artifact/ectopic detection (salto >25% vs mediana mobile)
3. correzione ectopic via interpolazione (RAW preservato in `raw_interval_ms`)
4. gestione duplicati (stesso timestamp → 1 solo)
5. gestione gap (conservati, non riempiti)
6. controllo monotonicità timestamp

## 6. Regola fondamentale HRV ≠ rMSSD (task #15/#24)

Se Huawei/Health Sync fornisce un valore chiamato **"HRV"** generico:
- **NON** viene mappato automaticamente a `rMSSD`.
- Solo `RR/NN` → algoritmo RMSSD, oppure `rmssd` esplicito documentato,
  producono `hrv_rmssd_ms`.
- Il campo `hrv` generico resta **local only** (non sincronizzato).

## 7. Morning HRV window (task #9)

`detect_morning_window` cerca la migliore finestra mattutina:
1. se Huawei fornisce `wake_time`/`sleep_end` → finestra subito dopo
2. altrimenti: prima finestra valida (≥5 min, NN sufficienti) entro 3h
3. se nessuna finestra lunga abbastanza → **None** (NON inventare)

## 8. Sincronizzazione Intervals.icu (task #14)

Via `wellness-bulk` PUT (stesso endpoint di BIA/peso):
- `hrvRmssd` ← `rmssd_ms` calcolato localmente
- `hrvSdnn`  ← `sdnn_ms` (se Intervals lo accetta)

**Dati NON accettati da Intervals** (restano LOCAL ONLY, task #17/#30):
- raw RR/NN (privacy: non inviati a server esterni)
- pNN50, LF/HF, CVNN, respiratory rate
- Baseline, trend, quality score

## 8b. Metriche avanzate (task #8/#11)

Oltre a RMSSD/SDNN principali, `compute_advanced_metrics` calcola metriche
che Intervals.icu **non** espone e che restano **LOCAL ONLY**:

| Metrica | Formula | Soglia minima | Sync ICU |
|---------|---------|---------------|----------|
| pNN50 | % differenze NN > 50ms | sempre | ❌ locale |
| CVNN | SDNN/mean × 100 | sempre | ❌ locale |
| SDANN | dev.stdev medie NN/min | ≥ 60s | ❌ locale |
| HRV triangular index | N / picco istogramma NN (bin 1/128s) | sempre | ❌ locale |
| LF (ms²) | Welch PSD banda 0.04–0.15 Hz | ≥ 120s + ≥ 32 NN | ❌ locale |
| HF (ms²) | Welch PSD banda 0.15–0.40 Hz | ≥ 120s + ≥ 32 NN | ❌ locale |
| LF/HF | LF ÷ HF | ≥ 120s | ❌ locale |

**Regola (task #8):** LF/HF NON viene calcolato su finestre < 120s o con
pochi NN — il campo resta `None` (non inventiamo metriche non valide).
L'analisi freq-domain usa numpy (Welch, resampling 4 Hz), nessuna dipendenza
nuova oltre numpy già presente.

## 8c. UI e endpoint riepilogo (task #10/#20)

Tab **HRV** nella sidebar (`sec-hrv`):

- KPI: RMSSD oggi, baseline 7g/30g, deviazione %, qualità + dettaglio
- Grafico `hrvChart` (Chart.js offline): RMSSD giornaliero + media mobile 7g
- Tabella metriche: RMSSD/SDNN (sync=✓) vs pNN50/SDANN/LF/HF/LF-HF (locale)
- Box import: path export → `POST /api/huawei/import` → ricalcola e aggiorna
- Export CSV: `GET /api/huawei/hrv/export?format=csv`

Endpoint `GET /api/huawei/hrv/summary` restituisce l'ultimo DailyHRV +
baseline 7/14/30 + deviazione + trend rolling 7g (usato dalla UI).

## 9. Privacy (task #30)

- Raw RR/NN → **solo DB locale**
- Verso Intervals.icu → **solo metriche aggregate** (RMSSD/SDNN)
- Nessun dato grezzo inviato a server esterni

## 10. Troubleshooting

| Sintomo | Causa | Soluzione |
|---------|-------|-----------|
| Import: "Nessun RR/NN trovato" | export senza colonne RR | verifica formato con `/api/huawei/hrv/debug` |
| DailyHRV vuoto | dati < 10s o < 8 NN | finestra troppo breve, aumentare durata |
| Sync ICU non fatto | qualità < 0.5 | migliorare segnale (riposo, no movimento) |
| "hrv" non sincronizzato | campo generico non-rMSSD | atteso per regola #15 |

## 11. Debug mode (task #21)

`GET /api/huawei/hrv/debug?path=...` restituisce la trace:
```
SOURCE FILE → FIELD → RAW → NORMALIZED → CALCULATED → DESTINATION
```
Essenziale per capire esattamente cosa Huawei sta esportando.
