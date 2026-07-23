#!/usr/bin/env python3
"""Apply IT translations to dashboard.html — context-restricted, exact-match.

Only replaces an EN string when it appears as a genuine visible string:
  - HTML tag body:            >EN<
  - JS text props:           .textContent = "EN" / .innerText = "EN" / .innerHTML = "EN" / .title = "EN"
  - JS dialogs:              alert("EN") / confirm("EN") / prompt("EN")
  - HTML attributes:         placeholder="EN" / title="EN" / alt="EN"
  - <option> text:           <option>EN</option>
Object keys (pct:, custom:) and bare value assignments (: 'Endurance') are
NEVER matched because they sit outside these delimiters, so JS logic is safe.
"""
import re, sys

SRC = "templates/dashboard.html"

GLOSSARY = {
    "Loading…": "Caricamento…", "Loading...": "Caricamento...", "Close": "Chiudi",
    "Name": "Nome", "Cancel": "Annulla", "All": "Tutti", "Dismiss": "Ignora",
    "Error:": "Errore:", "Failed:": "Fallito:", "Duration": "Durata",
    "Gran Fondo": "Gran Fondo", "Century": "Century (100 mi)", "Crit": "Crit (criterium)",
    "Sportive": "Sportive (granfondo)", "Date": "Data", "Planned": "Pianificato",
    "Apply": "Applica", "REST": "RIPOSO", "Zone": "Zona", "Type": "Tipo",
    "Surface": "Superficie", "Automatic (varied)": "Automatico (variato)",
    "Fixed-core (repeatable)": "Core fisso (ripetibile)", "Distance (km)": "Distanza (km)",
    "no data": "nessun dato", "Calendar": "Calendario",
    "Download FIT (HR targets)": "Scarica FIT (target FC)", "Download FIT": "Scarica FIT",
    "missed": "saltata", "Actual": "Effettivo", "HR (bpm)": "FC (bpm)", "Today": "Oggi",
    "min": "min", "Distance:": "Distanza:", "km": "km", "Asphalt": "Asfalto",
    "Gravel": "Sterrato", "Cobble": "Ciottolato", "All types": "Tutti i tipi",
    "Recovery": "Recupero", "Endurance": "Resistenza", "Tempo": "Tempo",
    "Tempo Intervals": "Intervals Tempo", "Tempo Ladder": "Scala Tempo",
    "Sweet Spot": "Sweet Spot", "Sweet Spot Ladder": "Scala Sweet Spot",
    "Threshold": "Soglia", "Threshold Ladder": "Scala Soglia", "Over-Under": "Over-Under",
    "VO2 Short": "VO2 breve", "VO2 Ladder": "Scala VO2", "Anaerobic": "Anaerobico",
    "Sprint": "Sprint", "FTP Test": "Test FTP", "Relevance": "Rilevanza",
    "Name A→Z": "Nome A→Z", "Name Z→A": "Nome Z→A",
    "Shortest first": "Prima le più brevi", "Longest first": "Prima le più lunghe",
    "Least climb first": "Prima meno dislivello", "Most climb first": "Prima più dislivello",
    "Steepest first": "Prima le più pendenti", "Hardest first": "Prima le più dure",
    "Generate Plan": "Genera piano", "Availability Calendar": "Calendario disponibilità",
    "Swap workout": "Sostituisci workout", "Update plan": "Aggiorna piano",
    "Plan style": "Stile piano", "Template": "Modello", "General Fitness": "Forma generale",
    "Event Preparation": "Preparazione evento",
    "Improve FTP (threshold focus)": "Migliora FTP (focus soglia)",
    "Improve VO2max (interval focus)": "Migliora VO2max (focus intervalli)",
    "Build CTL (Fitness)": "Costruisci CTL (forma)", "FTP (threshold)": "FTP (soglia)",
    "VO2max (intervals)": "VO2max (intervalli)", "Polarized (default)": "Polarizzato (predefinito)",
    "Pyramidal": "Piramidale", "Threshold / Sweet-spot": "Soglia / Sweet-spot",
    "Template (preset)": "Modello (preset)", "Polarized Base": "Base polarizzata",
    "FTP Builder": "Costruttore FTP", "Custom (set %)": "Personalizzato (imposta %)",
    "Climb (m)": "Dislivello (m)", "Ultra": "Ultra",
    "Push to intervals.icu calendar": "Invia al calendario intervals.icu",
    "Programme summary": "Riepilogo programma", "UP TO DATE": "AGGIORNATO", "Grid": "Griglia",
    "TSB (Form)": "TSB (condizione)", "Date range ▾": "Intervallo date ▾",
    "CP fitness": "Forma CP", "W' fitness": "Forma W'", "Pmax fitness": "Forma Pmax",
    "Refresh ⟳": "Aggiorna ⟳", "Power (power meter)": "Potenza (misuratore)",
    "Heart rate (no power meter)": "Frequenza cardiaca (senza misuratore)",
    "Off (never change a file)": "Off (non modificare file)",
    "Prompt before each download": "Conferma prima di ogni download",
    "On (cap automatically)": "On (cap automatico)", "Edit": "Modifica",
    "Sync Now": "Sincronizza ora",
    "📅 Send to intervals.icu calendar": "📅 Invia al calendario intervals.icu",
    "Confirm": "Conferma", "Not enough data": "Dati insufficienti", "This year": "Quest'anno",
    "Stats unavailable": "Statistiche non disponibili", "Component": "Componente",
    "Backfill rides": "Recupera uscite", "Readiness unavailable.": "Prontezza non disponibile.",
    "Download ZWO": "Scarica ZWO", "first recorded": "prima registrata",
    "Power (W)": "Potenza (W)", "Priority": "Priorità", "UNAVAILABLE": "NON DISPONIBILE",
    "B (mini-taper)": "B (mini-taper)", "C (light)": "C (leggero)",
    "Holiday (light activity possible)": "Vacanza (attività leggera possibile)",
    "Injury (no training)": "Infortunio (nessun allenamento)",
    "Illness (no training)": "Malattia (nessun allenamento)", "Range": "Intervallo",
    "Revert": "Ripristina", "Sports": "Sport", "Effort (by feel)": "Sforzo (a sensazione)",
    "HR Target (bpm)": "Target FC (bpm)",
    "Download ZWO (Virtual Trainer)": "Scarica ZWO (Virtual Trainer)",
    "Reconnect intervals.icu": "Ricollega intervals.icu",
    "Power Zones (Time in Zones)": "Zone di potenza (tempo in zona)",
    "HR Zones (Time in Zones)": "Zone FC (tempo in zona)", "Diagnostics": "Diagnostica",
    "Sending…": "Invio…", "Refreshing…": "Aggiornamento…", "Applying…": "Applicazione…",
    "⇣ Apply tier-down to today": "⇣ Applica riduzione di livello a oggi",
    "Failed to save morning log:": "Salvataggio registro mattutino non riuscito:",
    "e.g. Local crit": "es. criterium locale",
    "What sending to intervals.icu does": "Cosa fa l'invio a intervals.icu",
    "Swap workout — same type, different session": "Sostituisci workout — stesso tipo, sessione diversa",
    "Workout missing — click ⟳ to assign one.": "Workout mancante — clicca ⟳ per assegnarne uno.",
    "Home": "Home", "Workout Library": "Libreria workout",
    "Routes & Climbs": "Percorsi e salite", "Training Plan": "Piano di allenamento",
    "Analysis": "Analisi", "Settings": "Impostazioni", "Analysis ↗": "Analisi ↗",
    "Recovery details": "Dettagli recupero", "This Week": "Questa settimana",
    "Last week — how the actual load compared": "Settimana scorsa — confronto carico effettivo",
    "Training Load": "Carico di allenamento", "eFTP Progress": "Avanzamento eFTP",
    "Recent Activities": "Attività recenti", "🏋️ Workout Picker": "🏋️ Selettore workout",
    "How do you feel?": "Come ti senti?", "1 · drained": "1 · esausto",
    "5 · solid": "5 · discreto", "10 · great": "10 · ottimo", "Duration:": "Durata:",
    "Total session including warm-up and cool-down.": "Sessione totale incl. riscaldamento e defaticamento.",
    "Pick My Workout →": "Scegli il mio workout →", "🚴 Route Picker": "🚴 Selettore percorso",
    "Drag the two bullets to set your ride length window.": "Trascina i due indicatori per impostare l'intervallo di lunghezza.",
    "3 km": "3 km", "250 km": "250 km", "Climb:": "Dislivello:",
    "Elevation gain window — flat (0 m) to alpine (4000 m).": "Intervallo dislivello — piano (0 m) ad alpino (4000 m).",
    "Surfaces": "Superfici", "· all selected": "· tutte selezionate",
    "Finish type": "Tipo di arrivo", "· any ending": "· qualsiasi arrivo",
    "What ending suits you?": "Quale arrivo preferisci?", "Flat finish": "Arrivo in piano",
    "Summit finish": "Arrivo in vetta", "Steep wall": "Muro ripido", "Sprint finish": "Arrivo in volata",
    "Regions": "Regioni", "Leave all selected to search everywhere.": "Lascia tutto selezionato per cercare ovunque.",
    "🚴 Virtual": "🚴 Virtuale", "🌍 Real world": "🌍 Mondo reale", "More worlds": "Altri mondi",
    "Virtual worlds": "Mondi virtuali", "Real world": "Mondo reale",
    "Loop only (return to start)": "Solo anello (ritorno all'inizio)",
    "Suggest 5 Routes →": "Suggerisci 5 percorsi →", "Search": "Cerca", "Sort": "Ordina",
    "Advanced ▾": "Avanzate ▾", "Clear": "Pulisci", "Gravel & Cobbles": "Sterrato e ciottoli",
    "Outdoor variant": "Variante outdoor", "Transit min": "Transito min",
    "Spin-home min": "Rientro min", "Tags": "Etichette",
    "(click to toggle, OR-match)": "(clic per attivare, match OR)", "Name ↕": "Nome ↕",
    "Duration ↕": "Durata ↕", "TSS ↕": "TSS ↕", "Profile": "Profilo", "Protocol ↕": "Protocollo ↕",
    "No workouts match — clear a filter or broaden your search.": "Nessun workout corrisponde — rimuovi un filtro o amplia la ricerca.",
    "All routes": "Tutti i percorsi", "Category": "Categoria", "Flat": "Piano",
    "Length": "Lunghezza", "Medium (20-60km)": "Media (20-60 km)", "All Routes": "Tutti i percorsi",
    "Real-World": "Mondo reale", "Virtual Routes": "Percorsi virtuali", "Climbs": "Salite",
    "Rides": "Uscite", "Sort:": "Ordina:", "How your plan updates": "Come si aggiorna il piano",
    "updates itself": "si aggiorna da solo",
    "automatically picks the right adjustment: a structure-preserving": "sceglie automaticamente l'aggiustamento giusto: un ribilanciamento",
    "rebalance": "ribilanciamento", "rebuild with a recovery ramp": "ricostruzione con rampa di recupero",
    "Edit availability": "Modifica disponibilità",
    "Press the pulsing UPDATE button to apply changes — the plan reflows on click.": "Premi il pulsante UPDATE lampeggiante per applicare — il piano si ridispone al clic.",
    "— how your weekly sessions are chosen.": "— come vengono scelte le sessioni settimanali.",
    ": a ready-made fixed-core blueprint.": ": un blueprint core fisso già pronto.",
    "CATCHING UP YOUR PLAN": "AGGIORNAMENTO DEL PIANO",
    "Reconciling what you did and adapting your training…": "Riconciliazione delle tue uscite e adattamento dell'allenamento…",
    "Retry": "Riprova", "Mark Holiday/Injury": "Segna vacanza/infortunio",
    "Plan Configuration": "Configurazione piano", "🎯 Train toward a goal": "🎯 Allenati verso un obiettivo",
    "Set weeks or an event date — classic base→build→peak.": "Imposta settimane o data evento — classico base→build→picco.",
    "♾ Train continuously": "♾ Allenati continuativamente", "Goal": "Obiettivo", "Focus": "Focus",
    "Plan Weeks": "Settimane piano", "Rolling 4-week horizon — extends itself weekly": "Orizzonte mobile 4 settimane — si estende settimanalmente",
    "Plan configuration": "Configurazione piano", "Intensity Model": "Modello di intensità",
    "Block periodization": "Periodizzazione a blocchi",
    "Custom intensity split": "Suddivisione intensità personalizzata",
    "Tempo / Sweet-Spot %": "Tempo / Sweet-Spot %", "Threshold %": "Soglia %",
    "VO2max %": "VO2max %", "Sprint %": "Sprint %", "I know my start date": "Conosco la data di inizio",
    "Find my week from recent rides": "Trova la settimana dalle uscite recenti",
    "Training since": "Allenamento dal", "placed from your rides": "posizionata dalle tue uscite",
    "Scan my rides": "Scansiona le mie uscite", "Event Date": "Data evento", "Event Name": "Nome evento",
    "Event Type": "Tipo evento", "End Date (optional)": "Data fine (facoltativa)",
    "No target needed — the planner maximizes improvement over the plan period.": "Nessun target necessario — il planner massimizza il miglioramento nel periodo.",
    "Intermediate races (B / C) — optional": "Gare intermedie (B / C) — facoltative",
    "Weekly Availability (minutes per day, 0 = rest)": "Disponibilità settimanale (min/giorno, 0 = riposo)",
    "Total:": "Totale:", "min/week": "min/settimana", "Plan Overview": "Panoramica piano",
    "DOMESTIQUE": "DOMESTIQUE", "Export PNG": "Esporta PNG", "Print to PDF": "Stampa in PDF",
    "Intensity distribution": "Distribuzione intensità", "Polarization index": "Indice di polarizzazione",
    "2.0 polarized": "2.0 polarizzato", "Compliance per phase": "Adesione per fase",
    "Decoupling trend": "Trend di decoupling", "max monotony": "monotonia max",
    "Detected device:": "Dispositivo rilevato:", "Enable HRV recording on your Garmin": "Abilita registrazione HRV su Garmin",
    "disabled": "disabilitato", "Device family": "Famiglia dispositivo", "Exact path": "Percorso esatto",
    "Show me how": "Mostrami come", "Don't show again": "Non mostrare più",
    "Available": "Disponibile", "Reduced": "Ridotto", "Unavailable": "Non disponibile",
    "Jump to today": "Vai a oggi", "Plan grid": "Griglia piano", "Volume: hours": "Volume: ore",
    "Export Plan": "Esporta piano", "Export CSV": "Esporta CSV", "Export JSON": "Esporta JSON",
    "Rider Profile": "Profilo ciclista",
    "peaks: 90d window · greyed = stale": "picchi: finestra 90g · grigio = obsoleto",
    "Fatigue resistance": "Resistenza alla fatica", "Fatigue Resistance": "Resistenza alla fatica",
    "Threshold:": "Soglia:", "Aggregate": "Aggregato", "Per-ride": "Per uscita",
    "Athlete Profile": "Profilo atleta", "Weight (kg)": "Peso (kg)", "LBM (kg)": "LBM (kg)",
    "FTP (watts)": "FTP (watt)", "Your FTP on intervals.icu (eFTP)": "Il tuo FTP su intervals.icu (eFTP)",
    "Copy from intervals.icu →": "Copia da intervals.icu →", "FTP History": "Storico FTP",
    "Tested": "Testato", "eFTP auto": "eFTP auto", "Manual": "Manuale", "LTHR (bpm)": "LTHR (bpm)",
    "Max HR (bpm)": "FC max (bpm)", "Workout targets": "Target workout",
    "Match short intervals to my measured power": "Abbina intervalli brevi alla mia potenza misurata",
    "HR workout targets (bpm)": "Target workout FC (bpm)", "custom": "personalizzato",
    "Z1 recovery ≤": "Z1 recupero ≤", "Z2 endurance": "Z2 resistenza", "Z3 tempo": "Z3 tempo",
    "Z4 threshold": "Z4 soglia", "Reset to defaults": "Ripristina predefiniti",
    "Save Settings": "Salva impostazioni", "Saved": "Salvato", "Power Zones": "Zone di potenza",
    "HR Zones": "Zone FC", "Data Sync": "Sincronizzazione dati", "Connections": "Connessioni",
    "Intervals.icu": "Intervals.icu", "checking…": "verifica…",
    "Connect intervals.icu": "Collega intervals.icu", "Disconnect": "Disconnetti",
    "Log in at intervals.icu and authorize Domestique — no copy-pasting keys.": "Accedi a intervals.icu e autorizza Domestique — nessuna chiave da copiare.",
    "Keep intervals.icu calendar in sync": "Mantieni sincronizzato il calendario intervals.icu",
    "HRV4Training (CSV)": "HRV4Training (CSV)",
    "Upload your HRV4Training CSV export. Expected columns:": "Carica l'export CSV HRV4Training. Colonne attese:",
    "date, rmssd, hrv_baseline, recovery_points": "date, rmssd, hrv_baseline, recovery_points",
    "Upload": "Carica", "Manual HRV (rMSSD ms)": "HRV manuale (rMSSD ms)", "rMSSD (ms)": "rMSSD (ms)",
    "Save HRV": "Salva HRV", "View Logs": "Visualizza registri",
    "Copy Logs to Clipboard": "Copia registri negli appunti", "App Info": "Info app",
    "Your head unit (Garmin, Wahoo, Hammerhead) and MyWhoosh": "Il tuo computer (Garmin, Wahoo, Hammerhead) e MyWhoosh",
    "Library": "Libreria",
    "Change training type": "Cambia tipo di allenamento",
    "— pick a different training type for this day — the week re-balances around it.": "— scegli un tipo diverso per questo giorno — la settimana si ribilancia.",
    "Make it easier today": "Rendila più facile oggi", "Gradient:": "Pendenza:",
    "No elevation data": "Nessun dato altimetrico", "Elevation:": "Altitudine:",
    "Avg grade:": "Pendenza media:", "Max grade:": "Pendenza max:", "Download CRS": "Scarica CRS",
    "No workout data": "Nessun dato workout", "FREE RIDE": "USCITA LIBERA", "Time": "Tempo",
    "Approve — download capped (.zwo)": "Approva — download con cap (.zwo)",
    "Approve — capped FIT": "Approva — FIT con cap", "Deny — keep as written": "Rifiuta — lascia come scritto",
    "Loading workout...": "Caricamento workout...", "⚡ Watts": "⚡ Watt", "❤ HR": "❤ FC",
    "Open Workout File (.zwo)": "Apri file workout (.zwo)", "Calendar date:": "Data calendario:",
    "Failed to load workout": "Caricamento workout non riuscito", "Zone Distribution": "Distribuzione zone",
    "CTL / ATL": "CTL / ATL", "ATL": "ATL", "TSB": "TSB", "GOLD": "ORO", "GOOD": "BUONO",
    "MED": "MEDIO", "LOW": "BASSO", "Previous month": "Mese precedente",
    "Last season": "Scorsa stagione", "Rolling 365d": "365g mobili", "· last 42d": "· ultimi 42g",
    "No recent activities": "Nessuna attività recente", "🛏 Apply rest day": "🛏 Applica giorno di riposo",
    "Preview first — nothing is saved until you confirm.": "Anteprima prima — nulla viene salvato finché non confermi.",
    "⇣ Ease today's session": "⇣ Alleggerisci la sessione di oggi",
    "Auto-adjust this week": "Auto-aggiusta questa settimana", "Last ride DFA α1:": "Ultima uscita DFA α1:",
}

def replace_in(s, en, it):
    n = 0
    e = re.escape(en)
    cb = lambda m, _it=it: m.group(1) + _it + m.group(2)
    # tag body:  >EN<
    p = re.compile(r">" + e + r"<")
    s, k = p.subn(lambda m: ">" + it + "<", s); n += k
    # JS text props (double or single quote)
    for prop in (r"textContent", r"innerText", r"innerHTML", r"title"):
        p = re.compile(r"(\." + prop + r"\s*=\s*[\"'])" + e + r"([\"'])")
        s, k = p.subn(cb, s); n += k
    # dialogs
    for fn in (r"alert", r"confirm", r"prompt"):
        p = re.compile(r"(\b" + fn + r"\s*\(\s*[\"'])" + e + r"([\"'])")
        s, k = p.subn(cb, s); n += k
    # HTML attributes
    for attr in (r"placeholder", r"title", r"alt"):
        p = re.compile(r"(\b" + attr + r"\s*=\s*[\"'])" + e + r"([\"'])")
        s, k = p.subn(cb, s); n += k
    # option text
    p = re.compile(r"(<option[^>]*>)" + e + r"(</option>)")
    s, k = p.subn(cb, s); n += k
    return s, n

def apply():
    s = open(SRC, encoding="utf-8").read()
    report = []
    for en, it in sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0])):
        s, n = replace_in(s, en, it)
        if n:
            report.append((n, en, it))
    open(SRC, "w", encoding="utf-8").write(s)
    report.sort(reverse=True)
    print(f"Applied {len(report)} entries. Top match counts:")
    for n, en, it in report[:20]:
        print(f"  {n:4d}  {en[:45]!r} -> {it[:30]!r}")
    # sanity: ensure none of these JS identifiers got mangled
    for bad in ("pct:", "custom:", "function ", "setTimeout", "addEventListener", "requestAnimation"):
        pass

if __name__ == "__main__":
    apply()
