## Novità v5.4.0

### 🔄 Push Piano su intervals.icu (Reconcile Completo)
- **Endpoint /api/icu/push** ora usa il motore `reconcile()` di `icu_calendar_push.py`
- Pusha **ogni singola seduta** (ciclismo, forza, mobilità, running, MTB) con dettagli completi
- File ZWO verbatim per modalità potenza, FIT HR-target per modalità HR
- Upsert bulk idempotente (external_id `domestique:<profile>:<day>:<n>`)
- Orphan sweep: rimuove eventi non più nel piano, preserva eventi manuali (`domestique-manual:`)

### ⚙️ Forza & Mobilità — Opt-in
- **Checkbox** "Forza" / "Mobilità" nella card Home "Forza & Mobilità"
- `loadStrength()` rispetta i flag: disabilitati → non chiama API, UI mostra "disabilitata"
- `injectMultidiscipline()` invia `include_strength` / `include_mobility` al backend
- Backend `/api/plan/inject-multidiscipline` rispetta i flag

### 🔗 Link "Vedi su intervals.icu"
- Bottone nel calendario "Il mio calendario" per ogni settimana
- Apre `https://intervals.icu/athlete/<id>/calendar` in nuova scheda
- Legge athlete ID dal profilo

### 🧪 Test & Qualità
- 38/38 pytest passati
- JS syntax OK (node --check)
- Release validator 95/100