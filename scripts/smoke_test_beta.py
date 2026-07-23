#!/usr/bin/env python3
"""Smoke test funzionale dell'EXE BETA (non-distruttivo).

Avvia l'EXE, attende il bind su 127.0.0.1, poi verifica:
  - la dashboard si serve (HTTP 200)
  - le nuove API BETA rispondono con JSON sensato
  - i nuovi elementi UI sono nel markup servito
Alla fine killa l'EXE.
"""
import subprocess, time, sys, os, urllib.request, json, signal

EXE = r"C:\Users\Siviglino\Desktop\PPC\domestique-beta\dist\Domestique\Domestique.exe"
PORTS = [8080, 8000, 5000, 8888, 12789, 1423]

def wait_port(timeout=40):
    for _ in range(timeout):
        for p in PORTS:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{p}/", timeout=2) as r:
                    if r.status == 200:
                        return p
            except Exception:
                pass
        time.sleep(1)
    return None

def get_json(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return None, str(e)

print("== Avvio EXE BETA ==")
proc = subprocess.Popen([EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)  # let it spawn
try:
    port = wait_port()
    if not port:
        print("ERRORE: nessuna porta in ascolto entro il timeout")
        proc.kill(); sys.exit(1)
    print(f"[ok] server su porta {port}")

    # dashboard served
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
        html = r.read().decode(errors="ignore")
    for marker in ["Inizio", "Distribuzione intensità settimanale", "Adattamento giornaliero"]:
        print(f"  UI '{marker}':", "OK" if marker in html else "MANCANTE")

    # nuove API BETA
    for path in ["/api/tid-weekly?weeks=8", "/api/plan-block-model?total_weeks=16",
                 "/api/daily-adapt", "/api/route-wprime?url=test"]:
        st, body = get_json(port, path)
        print(f"  {path} ->", st, (str(body)[:80] if st else body))

    print("\nSMOKE TEST: completato (vedi sopra per dettagli)")
finally:
    proc.kill()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
