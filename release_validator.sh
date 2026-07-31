#!/usr/bin/env bash
# ==============================================================================
# PCC Pro - RELEASE VALIDATOR: Full Production Audit Suite
# ==============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCORE=100
ERRORS_COUNT=0
WARNINGS_COUNT=0
REPORT_FILE="RELEASE_CERTIFICATE.md"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS_COUNT=$((WARNINGS_COUNT+1)); SCORE=$((SCORE-5)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS_COUNT=$((ERRORS_COUNT+1)); SCORE=$((SCORE-20)); }
log_section() { echo -e "\n${BOLD}${CYAN}════════════════════════════════════════════════════════════════════${NC}\n${BOLD} $1 ${NC}\n${BOLD}${CYAN}════════════════════════════════════════════════════════════════════${NC}"; }

cleanup() { if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null || true; fi }
trap cleanup EXIT

cd "$PROJECT_DIR"

echo "# 🛡️ CERTIFICATO DI IDONEITÀ ALLA DISTRIBUZIONE" > "$REPORT_FILE"
echo "Data Validazione: $(date)" >> "$REPORT_FILE"
echo "Versione: $(cat VERSION 2>/dev/null || echo 'unknown')" >> "$REPORT_FILE"
echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')" >> "$REPORT_FILE"
echo "Commit: $(git rev-parse HEAD 2>/dev/null | cut -c1-8)" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"

# ── PHASE 1: SECURITY SCAN ──────────────────────────────────────────────
log_section "PHASE 1: SICUREZZA E SEGRETI CRITICI"

log_info "Scanning for hardcoded API keys / secrets..."
FOUND_SECRETS=false
if grep -rE "AIzaSy[0-9A-Za-z-_-]{35}|sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|postgres://[^:]+:[^@]+@|mysql://[^:]+:[^@]+@" \
  --exclude-dir='{node_modules,.git,dist,build,.next,.venv,__pycache__}' \
  --exclude='{RELEASE_CERTIFICATE.md,*.sh,*.md}' . 2>/dev/null | grep -v 'Binary\|No such' | grep -qv '^$'; then
  log_fail "Trovati potenziali SEGRETI nel sorgente!"
  FOUND_SECRETS=true
fi
if [ "$FOUND_SECRETS" = "false" ]; then
  log_success "Nessun segreto hardcoded rilevato."
fi

log_info "Verifica .env in .gitignore..."
if [ -f ".env" ] && ! grep -q '^\.env$' .gitignore 2>/dev/null; then
  log_fail ".env esiste ma NON è in .gitignore!"
else
  log_success ".env correttamente protetto in .gitignore."
fi

if [ -f ".env.example" ]; then
  log_success "Template .env.example presente."
else
  log_warn ".env.example mancante."
fi

# ── PHASE 2: DEPENDENCY AUDIT ───────────────────────────────────────────
log_section "PHASE 2: AUDIT DELLE DIPENDENZE"

if [ -f "requirements.txt" ]; then
  log_success "requirements.txt presente."
else
  log_warn "Nessun requirements.txt trovato."
fi

# ── PHASE 3: STATIC ANALYSIS ────────────────────────────────────────────
log_section "PHASE 3: ANALISI STATICA"

log_info "Controllo sintassi Python su tutti i .py..."
ALL_PYTHON_OK=true
for f in $(ls *.py 2>/dev/null | grep -v '__pycache__' | grep -v '.pyc'); do
  python -c "compile(open('$f','r').read(),'$f','exec')" 2>/dev/null || { log_fail "Errore sintassi in $f"; ALL_PYTHON_OK=false; break; }
done
if [ "$ALL_PYTHON_OK" = "true" ]; then
  log_success "Tutti i file Python sintatticamente corretti."
fi

log_info "Controllo sintassi JavaScript..."
if [ -f templates/dashboard.html ]; then
  .venv/Scripts/python.exe -c "
import re, sys
html=open('templates/dashboard.html','r',encoding='utf-8').read()
scripts=re.findall(r'<script>(.*?)</script>',html,re.DOTALL)
if not scripts: sys.exit(1)
open('/tmp/big_script.js','w',encoding='utf-8').write(max(scripts,key=len))
" 2>/dev/null
  if node --check /tmp/big_script.js 2>/dev/null; then
    log_success "Sintassi JS verificata (dashboard.html)."
  else
    log_fail "Errori di sintassi JS in dashboard.html!"
  fi
fi

# ── PHASE 4: UNIT TESTS ─────────────────────────────────────────────────
log_section "PHASE 4: UNIT & INTEGRATION TEST"

log_info "Esecuzione PyTest (core suite 38 test)..."
PYTEST_OUT=$(PYTHONPATH=. .venv/Scripts/python.exe -m pytest tests/test_bia_parser.py tests/test_plan_api.py tests/test_plan_auto_update.py tests/test_self_update.py -q --tb=short 2>&1)
TEST_EXIT=$?
echo "$PYTEST_OUT" | tail -5
if [ $TEST_EXIT -eq 0 ]; then
  PASSED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= passed)' | head -1)
  log_success "${PASSED:-38} test superati."
else
  FAILED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= failed)' | head -1)
  log_fail "${FAILED:-0} test FALLITI."
fi

# ── PHASE 5: BUILD VERIFICATION ─────────────────────────────────────────
log_section "PHASE 5: BUILD E ASSET"

if [ -f "dist/PCC/PCC.exe" ]; then
  log_success "EXE compilato: dist/PCC/PCC.exe"
else
  log_warn "EXE non trovato in dist/PCC/PCC.exe"
fi

LATEST_INSTALLER=$(ls -t PCC-Setup-*.exe 2>/dev/null | head -1 || true)
if [ -n "$LATEST_INSTALLER" ]; then
  SIZE=$(du -h "$LATEST_INSTALLER" | cut -f1)
  log_success "Installer presente: $LATEST_INSTALLER ($SIZE)"
else
  log_warn "Nessun PCC-Setup-*.exe trovato."
fi

# ── PHASE 6: LIVE SERVER HEALTH CHECK ───────────────────────────────────
log_section "PHASE 6: LIVE SERVER HEALTH CHECK"

PORT=8092
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/ 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
  log_success "Server su :$PORT operativo (HTTP $HTTP_STATUS)."

  LATENCY=$(curl -s -w "%{time_total}" -o /dev/null http://127.0.0.1:$PORT/ 2>/dev/null || echo "999")
  log_info "Latenza risposta: ${LATENCY}s"

  LATENCY_MS=$(python3 -c "print(int(float('${LATENCY}') * 1000))" 2>/dev/null || echo "0")
  if [ "$LATENCY_MS" -lt 1000 ] 2>/dev/null; then
    log_success "Latenza ottimale (${LATENCY_MS}ms)."
  elif [ "$LATENCY_MS" -lt 3000 ] 2>/dev/null; then
    log_warn "Latenza nella norma (${LATENCY_MS}ms)."
  else
    log_fail "Latenza eccessiva: ${LATENCY_MS}ms."
  fi

  HTML_CHECK=$(curl -s http://127.0.0.1:$PORT/ 2>/dev/null | grep -c 'PCC\|dashboard\|skeleton' || echo "0")
  if [ "$HTML_CHECK" -gt 0 ]; then
    log_success "HTML served correttamente (trovati marker PCC)."
  else
    log_warn "HTML servito ma marker attesi non trovati."
  fi
else
  log_warn "Server non raggiungibile su :$PORT (HTTP $HTTP_STATUS). Saltati test E2E live."
fi

# ── PHASE 7: PWA AND STATIC ASSETS ──────────────────────────────────────
log_section "PHASE 7: PWA E STATIC ASSET"

if [ -f "templates/dashboard.html" ]; then
  HAS_MANIFEST=$(grep -c 'rel="manifest"' templates/dashboard.html 2>/dev/null || echo "0")
  if [ "$HAS_MANIFEST" -gt 0 ]; then
    log_success "Manifest PWA presente nel template."
  else
    log_warn "Manifest PWA non trovato nel template."
  fi
fi

if [ -f "static/manifest.json" ]; then
  log_success "static/manifest.json presente."
else
  log_warn "static/manifest.json mancante."
fi

# ── PHASE 8: GIT INTEGRITY ──────────────────────────────────────────────
log_section "PHASE 8: GIT INTEGRITY"

UNCOMMITTED=$(git status --porcelain 2>/dev/null | grep -vE 'RELEASE_CERTIFICATE.md|release_notes.*\.md' | wc -l)
if [ "$UNCOMMITTED" -eq 0 ]; then
  log_success "Working tree pulito (escluse release notes)."
else
  log_warn "$UNCOMMITTED file non committati."
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
log_info "Branch attivo: $CURRENT_BRANCH"

LATEST_COMMIT=$(git log --oneline -1 2>/dev/null || echo "N/A")
log_info "Ultimo commit: $LATEST_COMMIT"

VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]' || echo "unknown")
TAG_EXISTS=$(git tag -l "v$VERSION" 2>/dev/null | head -1 || true)
if [ "$TAG_EXISTS" = "v$VERSION" ]; then
  log_success "Tag v$VERSION presente e allineato."
else
  log_warn "Tag v$VERSION non trovato o non allineato."
fi

# ── PHASE 9: VERSION CONSISTENCY ─────────────────────────────────────────
log_section "PHASE 9: CONSISTENZA VERSIONE"

if [ -n "$VERSION" ] && [ "$VERSION" != "unknown" ]; then
  COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null | head -1 || echo "")
  if echo "$COMMIT_MSG" | grep -qi "v$VERSION\|VERSION\|bump"; then
    log_success "Ultimo commit coerente con versione $VERSION."
  else
    log_warn "Ultimo commit non reference versione $VERSION."
  fi
fi

# ── FINAL REPORT ─────────────────────────────────────────────────────────
log_section "PHASE 10: REPORT FINALE E GIUDIZIO"

echo "" >> "$REPORT_FILE"
echo "## Risultato Audit" >> "$REPORT_FILE"
echo "* **Punteggio Totale**: **$SCORE / 100**" >> "$REPORT_FILE"
echo "* **Errori (FAIL)**: $ERRORS_COUNT" >> "$REPORT_FILE"
echo "* **Avvisi (WARN)**: $WARNINGS_COUNT" >> "$REPORT_FILE"
echo "* **Versione**: v$VERSION" >> "$REPORT_FILE"
echo "* **Branch**: $CURRENT_BRANCH" >> "$REPORT_FILE"
echo "* **Commit**: $(git rev-parse HEAD 2>/dev/null | cut -c1-8)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ $SCORE -lt 0 ]; then SCORE=0; fi

if [ $ERRORS_COUNT -eq 0 ] && [ $SCORE -ge 85 ]; then
  STATUS_MSG="✅ APPROVATO PER LA DISTRIBUZIONE — READY FOR PRODUCTION"
  echo "### STATO: $STATUS_MSG" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
  echo -e "\n${BOLD}${GREEN}====================================================================${NC}"
  echo -e "${BOLD}${GREEN}  🚀 $STATUS_MSG  ${NC}"
  echo -e "${BOLD}${GREEN}  Punteggio Qualità Prodotto: $SCORE / 100${NC}"
  echo -e "${BOLD}${GREEN}  Errori: $ERRORS_COUNT | Avvisi: $WARNINGS_COUNT${NC}"
  echo -e "${BOLD}${GREEN}====================================================================${NC}\n"
  echo "[INFO] Certificato rilasciato con successo. Pronto per la distribuzione."
  exit 0
else
  STATUS_MSG="❌ NON IDONEO ALLA DISTRIBUZIONE — CORREGGERE GLI ERRORI"
  echo "### STATO: $STATUS_MSG" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
  echo -e "\n${BOLD}${RED}====================================================================${NC}"
  echo -e "${BOLD}${RED}  ❌ $STATUS_MSG  ${NC}"
  echo -e "${BOLD}${RED}  Punteggio: $SCORE / 100 | Errori: $ERRORS_COUNT | Avvisi: $WARNINGS_COUNT${NC}"
  echo -e "${BOLD}${RED}====================================================================${NC}\n"
  echo "[INFO] Audit fallito con score $SCORE. Rivedi RELEASE_CERTIFICATE.md."
  exit 1
fi
SCRIPT