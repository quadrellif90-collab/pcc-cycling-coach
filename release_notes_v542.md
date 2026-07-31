## Novità v5.4.2 — Accorgimenti persistiti

### 🔧 Fix radicale: gli accorgimenti sopravvivono agli auto-update
- **Root cause trovata e risolta**: `regenerate_from_today`, `recalculate_plan` e `extend_continuous_plan` **azzervano silenziosamente** forza/mobilità/integratori a ogni ricalcolo/sync. Ora `_apply_plan_options_future()` ri-applica i layer (forza, mobilità, nutrizione, integratori, calore, altitudine, durability) su tutte le settimane future.
- **Round-trip completo**: la conversione piano→`PlannedWeek` perdeva le note (`nutrition_note`, `integrator_note`, `heat_note`, `strength_note`, `mobility_note`, `durability_note`, `altitude_note`) — ora tutti i campi viaggiano integri.
- **Re-apply post-reforecast**: il tier `rebalanced` (auto-adattamento settimanale) ri-applica gli accorgimenti sui giorni rigenerati.
- **Flag persistiti nel piano**: i `plan_options` vengono salvati nel blocco `goal` → ogni rigenerazione rilegge gli stessi flag invece di tornare a "normale".

### 🎨 UI
- **Checkbox univoche**: la card "Forza & Mobilità" ora usa `card-strength`/`card-mobility` (prima c'erano ID duplicati che confondevano il selettore Accorgimenti) con `syncCardFlags()` → il selettore Accorgimenti resta la fonte canonica.
- **Card chiuse di default**: Nutrizione e Integrazione non si aprono più da sole all'avvio.
- **Forza/Mobilità OFF di default**: prima erano sempre attive.

### 📤 Push intervals.icu
- `load_plan_weeks()` ora include le **sessioni** → il push non invia più 0 eventi.

### ✅ Verificato E2E (server reale)
- Genera piano con flag → **4 forza + 4 mobilità + 18 note nutrizione + 7 integratori** nel piano su disco
- Update (tier rebalanced) → **tutti preservati** (prima: nutrizione 17→0)
- Push `/api/icu/push` → **pushed=4 updated=9 deleted=2** su intervals.icu
- Sync automatico al boot → pushed=13 (piano completo)

### 📦 Build
- `PCC-Setup-5.4.2.exe` (~113 MB)
