# OCR in PPC 5.0 — PDF scansionati (BIA / ematochimica / dieta)

PPC 5.0 legge automaticamente i **PDF scansionati** (immagini, non testo)
grazie a un layer OCR locale. Niente cloud: tutto resta sul tuo computer.

## Come funziona
1. `bia_parser.py` / `diet_parser.py` provano a estrarre il testo dal PDF.
2. Se il PDF è una scansione (nessun testo estraibile), `ocr_pdf.py`:
   - rasterizza ogni pagina con **PyMuPDF** (fitz) a 300 DPI;
   - la passa a **Tesseract** (motore OCR open-source) in modalità EN+IT.
3. Il testo riconosciuto viene parsato come un export testuale normale.

## Tesseract è opzionale
- **Se Tesseract è installato** → i PDF scansionati vengono letti in automatico.
- **Se NON è installato** → PPC non crasha e non invia nulla a internet:
  mostra semplicemente "PDF scansionato, incolla i valori" come nelle versioni
  precedenti. L'OCR è solo un bonus quando il motore è presente.

## Dove trova Tesseract
`ocr_pdf.py` cerca (in ordine):
1. `tesseract` nel PATH di sistema;
2. `C:\Program Files\Tesseract-OCR\tesseract.exe` (installazione choco/standard);
3. `tesseract.exe` / `tesseract_bin\tesseract.exe` **accanto all'EXE di PPC**
   (questo è il caso dell'installer Windows, che lo include).

## Installazione manuale (solo se usi il sorgente, non l'EXE)
- Windows: `choco install tesseract` (o scarica da https://github.com/tesseract-ocr/tesseract)
- macOS: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

I modelli linguistici (tessdata) per `eng` e `ita` devono essere presenti
nella cartella `tessdata` accanto al binary. L'installer Windows li include.

## Note per lo sviluppo
- `requirements.txt`: `pytesseract` + `PyMuPDF` (già usato dai parser).
- `ppc.spec`: hidden imports `pytesseract`, `fitz`.
- `release.yml`: il CI installa Tesseract via `choco install tesseract` e lo
  copia in `dist\PPC\` così l'EXE bundlato funziona out-of-the-box.
- Test: `tests/test_ocr_pdf.py` verifica il graceful degrade (nessun Tesseract
  sull'host di test → nessun crash, nessun invio dati).
