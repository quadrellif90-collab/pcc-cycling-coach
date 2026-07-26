# Copyright 2024-2026 PCC — Performance Cycling Coach
# Licensed under the Apache License, Version 2.0 (LICENSE / NOTICE).
"""PCC — avvio come web app (HTML nel browser), senza involucro desktop EXE.

Questo è il punto d'ingresso "versione HTML": parte il backend FastAPI e apre
il browser sull'interfaccia. Nessun PyWebView / nessun .exe richiesto — basta
Python. Utile per:
  - usare PCC come app web locale invece di desktop,
  - esporre la UI su un altro dispositivo della rete (es. cellulare) puntando
    al proprio PC:  http://<IP-PC>:8080
  - deploy su un server (Render/Fly) per la versione mobile (vedi README).

Uso:
  python run_web.py                 # localhost:8080 + apri browser
  python run_web.py --host 0.0.0.0  # accessibile dalla rete locale (cellulare)
  PORT=8081 python run_web.py       # porta personalizzata
"""
import os
import sys
import webbrowser
import threading
import uvicorn


def main():
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "127.0.0.1")
    # allow --host override
    for a in sys.argv[1:]:
        if a.startswith("--host"):
            host = a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1]

    url = f"http://{host}:{port}/"

    # Apri il browser dopo un breve delay (il server impiega un attimo a partire)
    if host in ("127.0.0.1", "localhost"):
        def _open():
            import time
            time.sleep(2.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    print(f"\nPCC — Performance Cycling Coach (web mode)")
    print(f"Interfaccia: {url}\n")
    if host == "0.0.0.0":
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"Dalla rete locale (es. cellulare): http://{ip}:{port}/\n")
        except Exception:
            pass

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
