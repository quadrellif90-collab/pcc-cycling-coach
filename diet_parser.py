"""PCC — Parser intelligente diete PDF (nutrizionista) + DB nutrizionale.

Il PDF del nutrizionista (es. "Filippo estate.pdf") ha struttura:
  - intestazione "10/04/2026 pagina N"
  - nomi giorno: Lunedì / Martedì / ... / Domenica
  - pasti: Colazione Salata | Colazione | Pranzo | Spuntino Pomeriggio |
           Spuntino | Cena | Alternativa
  - righe "Alimento 123 g" oppure "o Alimento 45 g" (alternativa inline)
  - "frutta secca (...)" e' un raggruppamento, grammi subito dopo.

Questo modulo:
  1. estrae il testo (PyPDF2)
  2. lo parse in {day, meal, alternatives:[{food, grams}]}
  3. calcola macro reali (kcal/carb/prot/fat) via DB nutrizionale per 100g
  4. lascia ALL'alternativa esplicita cosi l'atleta sceglie nella UI

Nessun dato viene perso: il testo grezzo e' preservato in `raw_text`.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ── DB nutrizionale (valori per 100 g, fonte: tavole INRAN/USDA approssimate)
#    Copre gli alimenti del PDF "Filippo estate" + comuni. Se un alimento
#    manca, il parser lo segnala (kcal=0) invece di inventare numeri.
NUTRITION_PER_100G = {
    # Cereali / pane
    "pane comune": (265, 49, 9, 3.2),
    "pane di segale": (250, 48, 8.5, 2.6),
    "pane integrale": (247, 41, 8.8, 4.2),
    "cracker di segale": (340, 65, 9, 6),
    "cracker \"zero grano\" galbusera": (380, 55, 8, 14),
    "fette biscottate": (380, 72, 11, 6),
    "biscotti frollini": (450, 68, 6, 18),
    "piadina": (290, 48, 9, 7),
    "miele": (304, 82, 0.3, 0),
    "marmellata hero light fragola": (160, 38, 0.5, 0),
    "marmellata di frutta (normali e tipo frutta viva)": (180, 44, 0.4, 0),
    "marmellata": (250, 62, 0.5, 0),
    "burro": (717, 0.1, 0.9, 81),
    "cioccolato fondente": (546, 46, 4.9, 39),
    "cous cous medio": (360, 75, 12, 1),
    # Riso / pasta
    "riso basmati": (350, 78, 7, 0.9),
    "riso brillato": (360, 79, 7, 0.4),
    "riso venere": (355, 75, 8, 3),
    "pasta di semola": (359, 71, 12, 1.5),
    "pasta di semola integrale": (355, 70, 13, 2.5),
    "pasta di grano saraceno": (340, 70, 12, 2),
    "pasta all'uovo secca": (370, 71, 13, 4),
    "pasta all'uovo fresca": (330, 60, 13, 5),
    "pasta di lenticchie": (330, 52, 22, 2.5),
    "pasta di piselli": (335, 55, 21, 2),
    "polenta": (350, 75, 7, 1),
    "sugo al pomodoro": (40, 7, 1.5, 0.5),
    "sugo di verdure": (35, 6, 1.2, 0.4),
    "ragù alla bolognese": (120, 5, 8, 8),
    "pesto alla genovese": (450, 6, 4, 46),
    # Latticini / uova
    "latte di vacca parzialmente scremato": (47, 4.8, 3.3, 1.5),
    "latte di soia": (33, 1.8, 3, 1.8),
    "latte di avena": (45, 7, 1, 1.5),
    "latte di mandorle": (17, 0.3, 0.5, 1.2),
    "yogurt greco bianco total 2% - fage": (59, 3.5, 9.5, 2),
    "yogurt greco (0% lipidi)": (57, 3.6, 10, 0.2),
    "yogurt greco 0%": (57, 3.6, 10, 0.2),
    "ricotta di vacca": (174, 3, 11, 13),
    "ricotta di vacca e pecora": (180, 3, 11, 14),
    "ricotta di pecora": (178, 3, 11, 13),
    "ricotta salata": (170, 2, 12, 13),
    "grana padano": (392, 0, 33, 28),
    "parmigiano reggiano": (392, 0, 33, 28),
    "yogurt intero": (61, 4.7, 3.2, 3.3),
    "kefir": (50, 4, 3, 2),
    "philadelphia light": (170, 5, 9, 12),
    "mozzarella light": (190, 3, 18, 12),
    "feta light": (210, 2, 14, 16),
    "fiocchi di latte - naturella": (80, 2, 15, 1),
    "formaggio a pasta molle": (280, 2, 16, 23),
    "sottilette light": (230, 4, 18, 15),
    "primo sale": (300, 1, 20, 24),
    "ricotta cuor di malga": (175, 3, 11, 13),
    "uova di gallina": (155, 1.1, 13, 11),
    "uova di gallina (albume)": (52, 0.7, 11, 0.2),
    # Proteine animali
    "avocado": (160, 9, 2, 15),
    "salmone fresco crudo": (208, 0, 20, 13),
    "salmone affumicato": (180, 0, 21, 10),
    "salmone d'allevamento": (208, 0, 20, 13),
    "pesce spada": (130, 0, 20, 5),
    "merluzzo": (82, 0, 18, 1),
    "spigola o branzino": (97, 0, 18, 2),
    "sogliola": (90, 0, 19, 1),
    "orata d'allevamento": (115, 0, 20, 4),
    "rana pescatrice": (85, 0, 18, 1),
    "tonno in scatola (sott'olio)": (190, 0, 26, 9),
    "tonno": (130, 0, 28, 1),
    "vitello, filetto, crudo": (115, 0, 22, 3),
    "vitellone (filetto)": (120, 0, 22, 4),
    "vitellone (hamburger)": (200, 0, 20, 13),
    "vitello, macinato, crudo": (140, 0, 21, 6),
    "maiale (filetto)": (145, 0, 21, 6),
    "manzo, sminuzzato, crudo": (160, 0, 21, 8),
    "pollo (petto)": (120, 0, 23, 2),
    "pollo (coscia)": (180, 0, 18, 11),
    "pollo (sovracoscio)": (175, 0, 18, 10),
    "tacchino, fesa (petto)": (110, 0, 22, 2),
    "tacchino (petto)": (110, 0, 22, 2),
    "hamburger tacchino": (150, 0, 21, 7),
    "prosciutto cotto magro": (105, 1, 16, 4),
    "prosciutto crudo di parma sgrassato": (130, 0, 22, 5),
    "pancetta affumicata o bacon": (450, 1, 10, 45),
    # Vegetali / legumi / frutta
    "verdure miste": (25, 4, 2, 0.3),
    "insalata mista": (15, 2, 1, 0.2),
    "pomodori": (18, 3.5, 1, 0.2),
    "carote": (41, 9, 1, 0.2),
    "cipolle": (40, 9, 1, 0.1),
    "finocchi": (31, 6, 1, 0.2),
    "olive nere": (115, 6, 1, 10),
    "olive verdi": (145, 3, 1, 15),
    "patate": (77, 17, 2, 0.1),
    "frutta fresca": (50, 12, 0.5, 0.3),
    "frutta secca (anacardi, arachidi, mandorle, nocciole, noci, noci del brasile, noci pecan, pinoli e pistacchi)": (580, 20, 18, 50),
    "semi di lino": (534, 29, 18, 42),
    "semi di chia - naturasì": (486, 42, 17, 31),
    "ceci in scatola": (120, 20, 7, 2),
    "fagioli in scatola": (110, 19, 7, 0.5),
    "polpette bio vegetali con verdure miste (granarolo)": (180, 12, 12, 8),
    "preparato per polpette vegane": (200, 15, 14, 8),
    "hamburger vegetali taranis": (190, 10, 18, 9),
    "budino di chia": (120, 10, 4, 7),
    "melone d'estate": (34, 8, 0.8, 0.2),
    "succo di limone": (25, 8, 0.4, 0),
    "senape": (100, 10, 5, 4),
    "salsa per insalate con yogurt (senza olio)": (70, 8, 2, 3),
    # Grassi
    "olio di oliva extra vergine": (884, 0, 0, 100),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().replace('"', "").replace("'", ""))


_NUTRITION_LOOKUP = {_norm(k): v for k, v in NUTRITION_PER_100G.items()}


def nutrition_for(food: str):
    """Ritorna (kcal, carb, prot, fat) per 100g per un alimento (lookup fuzzy)."""
    key = _norm(food)
    if key in _NUTRITION_LOOKUP:
        return _NUTRITION_LOOKUP[key]
    for k, v in _NUTRITION_LOOKUP.items():
        if k in key or key in k:
            return v
    return (0, 0, 0, 0)  # sconosciuto -> segnalato, non inventato


@dataclass
class FoodItem:
    name: str
    grams: float
    is_alternative: bool = False
    group_with: Optional[str] = None
    kcal: float = 0.0
    carb_g: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    known: bool = True

    def compute(self):
        kc, c, p, f = nutrition_for(self.name)
        self.kcal = round(self.grams * kc / 100, 1)
        self.carb_g = round(self.grams * c / 100, 1)
        self.protein_g = round(self.grams * p / 100, 1)
        self.fat_g = round(self.grams * f / 100, 1)
        self.known = (kc > 0)


@dataclass
class Meal:
    name: str
    items: list = field(default_factory=list)

    def totals(self, primary_only: bool = True):
        """Macro del pasto. Se primary_only, conta SOLO la prima opzione di
        ogni gruppo di alternative (non le alternative stesse)."""
        items = self.items
        if primary_only:
            seen_groups = set()
            keep = []
            for i in items:
                if i.is_alternative:
                    continue  # le alternative non si sommano
                keep.append(i)
            items = keep
        return {
            "kcal": round(sum(i.kcal for i in items), 1),
            "carb_g": round(sum(i.carb_g for i in items), 1),
            "protein_g": round(sum(i.protein_g for i in items), 1),
            "fat_g": round(sum(i.fat_g for i in items), 1),
            "unknown": [i.name for i in items if not i.known],
        }


@dataclass
class DayPlan:
    day: str
    meals: list = field(default_factory=list)

    def totals(self, primary_only: bool = True):
        t = {"kcal": 0, "carb_g": 0, "protein_g": 0, "fat_g": 0, "unknown": []}
        for m in self.meals:
            mt = m.totals(primary_only=primary_only)
            t["kcal"] += mt["kcal"]
            t["carb_g"] += mt["carb_g"]
            t["protein_g"] += mt["protein_g"]
            t["fat_g"] += mt["fat_g"]
            t["unknown"].extend(mt["unknown"])
        return t


_DAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
_MEALS = ["colazione salata", "colazione", "pranzo", "spuntino pomeriggio",
          "spuntino", "cena", "alternativa"]


def _parse_grams_line(line: str):
    """Da 'Avocado 30 g' o 'o Pane comune 50 g' -> (food, grams, is_alt)."""
    m = re.match(r"^(o\s+)?(.+?)\s+(\d+(?:\.\d+)?)\s*g\s*$", line.strip(), re.IGNORECASE)
    if not m:
        return None
    is_alt = bool(m.group(1))
    food = m.group(2).strip().rstrip(":").strip()
    grams = float(m.group(3))
    return food, grams, is_alt


def _day_from_line(low: str):
    """Rileva un nome giorno anche se attaccato ad altro (es. 'pagina 5Giovedì')."""
    import unicodedata
    low_n = unicodedata.normalize("NFKC", low)
    for d in _DAYS:
        dn = unicodedata.normalize("NFKC", d)
        idx = low_n.find(dn)
        if idx >= 0:
            return d, idx
    return None, -1


def parse_diet_text(text: str) -> dict:
    """Parse il testo grezzo del PDF in struttura giorni/pasti/alimenti.

    Logica alternative: ogni riga 'o X 50 g' è alternativa alla riga
    precedente NON-alternativa. Nel calcolo dei macro giornalieri si conta
    SOLO la prima opzione (non-alt) di ogni gruppo; le alternative restano
    disponibili nell'UI per la scelta dell'atleta.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    days: list[DayPlan] = []
    cur_day = None
    cur_meal = None
    unknown_foods = []
    last_primary: Optional[FoodItem] = None

    for raw in lines:
        low = raw.lower().replace("quantità", "").strip()
        import unicodedata
        low = unicodedata.normalize("NFKC", low)
        # giorno ha priorita sull'intestazione (es. "pagina 5Giovedì")
        day_hit, day_idx = _day_from_line(low)
        if day_hit:
            cur_day = DayPlan(day=day_hit.capitalize())
            days.append(cur_day)
            cur_meal = None
            last_primary = None
            rest = low[day_idx + len(day_hit):].strip()
            meal_hit = next((m for m in _MEALS if rest.startswith(m)), None)
            if meal_hit and cur_day is not None:
                cur_meal = Meal(name=meal_hit.capitalize())
                cur_day.meals.append(cur_meal)
                last_primary = None
            continue
        if re.match(r"^\d{2}/\d{2}/\d{4}\s+pagina", low):
            continue
        meal_hit = next((m for m in _MEALS if low.startswith(m)), None)
        if meal_hit and cur_day is not None:
            cur_meal = Meal(name=meal_hit.capitalize())
            cur_day.meals.append(cur_meal)
            last_primary = None
            continue
        parsed = _parse_grams_line(raw)
        if parsed and cur_meal is not None:
            food, grams, is_alt = parsed
            item = FoodItem(name=food, grams=grams, is_alternative=is_alt)
            item.compute()
            if not item.known:
                unknown_foods.append(food)
            cur_meal.items.append(item)
            if not is_alt:
                last_primary = item
            else:
                item.group_with = last_primary.name if last_primary else None

    return {
        "days": days,
        "unknown_foods": sorted(set(unknown_foods)),
        "day_count": len(days),
    }


def parse_diet_pdf(pdf_bytes: bytes) -> dict:
    """Estrae testo da PDF (PyPDF2) e lo parse.

    PCC 5.0 — OCR fallback: if the PDF yields no text (scanned image), try
    Tesseract OCR before giving up. Self-contained: no cloud, degrades to a
    text-only parse (raw_text empty) if OCR is unavailable.
    """
    from PyPDF2 import PdfReader
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
    text = text.strip()
    ocr_used = False
    if not text:
        try:
            import ocr_pdf
            ocr_text = ocr_pdf.ocr_pdf_text(pdf_bytes)
            if ocr_text:
                text = ocr_text
                ocr_used = True
        except Exception:
            pass
    struct = parse_diet_text(text)
    struct["raw_text"] = text
    struct["pages"] = len(reader.pages)
    struct["ocr_used"] = ocr_used
    return struct


def day_macros_summary(struct: dict) -> list:
    """Riepilogo macro per giorno (primary_only) per UI/confronto con target PCC."""
    out = []
    for d in struct.get("days", []):
        t = d.totals(primary_only=True)
        out.append({
            "day": d.day,
            "kcal": t["kcal"],
            "carb_g": t["carb_g"],
            "protein_g": t["protein_g"],
            "fat_g": t["fat_g"],
            "unknown": t["unknown"],
            "meals": [{"name": m.name, "items": [
                {"name": i.name, "grams": i.grams, "is_alt": i.is_alternative,
                 "kcal": i.kcal, "carb_g": i.carb_g, "protein_g": i.protein_g,
                 "fat_g": i.fat_g, "known": i.known}
                for i in m.items]} for m in d.meals],
        })
    return out
