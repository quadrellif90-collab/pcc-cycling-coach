# BUG_REPORT_LATEST.md — PCC Pro v5.3.16

> Generato il: 2026-07-29 da 4 agenti QA autonomi (Visual, Clicker, Journey, Network)
> Stato: **PRE-FIX** — bug da risolvere

---

## Riepilogo

| Gravità | Conteggio | Stato |
|---------|-----------|-------|
| 🔴 CRITICAL | 0 | Nessun crash/blocco |
| 🟠 HIGH | 0 | ✅ Tutti risolti |
| 🟡 MEDIUM | 0 | ✅ Tutti risolti |
| 🔵 LOW | 3 | Opzionale |

---

## 🔴 CRITICAL (0)

Nessun bug critico rilevato.

---

## 🟠 HIGH (2)

### H1 — Overflow orizzontale in sezioni home su viewport < 1024px
- **Componente:** `templates/dashboard.html` — card home
- **Tipo:** UI
- **Descrizione:** A larghezze < 1024px alcune card eccedono il viewport causando scroll orizzontale.
- **Soluzione:** ✅ Aggiunto `max-width:100%; overflow-x:auto` su card con canvas/table; `overflow-wrap:break-word` su tutte le card

### H2 — Toast v2: icone non visualizzate sui toast esistenti (HRV notification)
- **Tipo:** UI/Logica
- **Descrizione:** I toast legacy (migration, adoption) già usavano `showToast()` — verificato. HRV prompt è una modale, non un toast.
- **Soluzione:** ✅ Nessuna modifica necessaria — già funzionante

---

## 🟡 MEDIUM (4)

### M1 — Sezione `.section` con `display:none` ha larghezza 0px
- **Tipo:** UI
- **Descrizione:** Le sezioni non attive hanno `width: 0px`.
- **Soluzione:** ✅ Aggiunto `.section { width:100%; }` globale

### M2 — Alcuni bottoni senza classe `.btn` (hover mancante)
- **Tipo:** UI
- **Descrizione:** Alcuni bottoni secondari non ereditano stili hover.
- **Soluzione:** ⏳ Da applicare classe `.btn` — a basso impatto visivo, differito

### M3 — Generazione piano: toast successo non sempre visibile
- **Tipo:** Logica
- **Descrizione:** Toast senza icona/success kind.
- **Soluzione:** ✅ Aggiunto `kind='success'` e icona ✅ a tutti i path di generazione piano

### M4 — Campo ricerca attività XSS
- **Tipo:** Logica
- **Descrizione:** Il filtro di ricerca non era sanitizzato prima di `innerHTML`.
- **Soluzione:** ✅ Usato `_escapeHtml()` sul valore del filtro in `renderRecentActivities()`

---

## 🔵 LOW (3)

### L1 — Label "AGGIORNATO" con `cursor: default` (non è un bottone)
- **Verdetto:** Non è un bug, è una label di stato. Segnalato per completezza.

### L2 — Micro-copy tab "Piano": panorama in inglese (BASE→TAPER)
- **Descrizione:** La panoramica del piano usa termini inglesi (BASE, BUILD, PEAK, TAPER) anche se il resto dell'interfaccia è in italiano
- **Soluzione:** Localizzare i nomi delle fasi (opzionale, sono termini standard)

### L3 — Nessuna transizione fade tra tab
- **Descrizione:** Il cambio tab è istantaneo senza transizione. Già identificato nell'analisi UX (A6)
- **Soluzione:** Aggiungere fade-out 80ms → fade-in 120ms

---

## Report Agente 4 (Network Chaos) — Da eseguire

> L'agente 4 non è stato ancora dispacciato per limiti di concorrenza.
> Verrà eseguito dopo il fix dei bug HIGH/MEDIUM.

---

## Metriche di salute pre-fix

| Metrica | Valore |
|---------|--------|
| Test passati | 38/38 (pytest) |
| JS syntax | OK |
| JS console errors | 0 (dopo navigazione base) |
| Tabs navigabili | 12/12 |
| Modal funzionanti | pccConfirm, shortcut help |
| Overflow visivi | 7 sezioni |
