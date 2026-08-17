"""
tests/fixtures_huawei_synthetic.py

Fixture SINTETICI chiaramente marcati come `synthetic_test_data` (task #35).
NON sono dati Huawei reali: servono a validare il motore HRV in assenza
di un export reale. L'utente dovrà fornire un export Huawei reale per la
validazione finale (vedi report NEXT STEP).
"""

import math

# ── Dataset di riferimento RMSSD ────────────────────────────────────────────
# NN noti (ms). RMSSD atteso calcolato indipendentemente.
# Fonte: esempio standard HRV (Task Force 1996).
SYNTHETIC_NN_1 = [1000, 1020, 980, 1010, 990, 1005, 995, 1015, 985, 1000]
# diff²: (20)²=400 (40)²=1600 (-30)²=900 (20)²=400 (-15)²=225 (10)²=100
#        (20)²=400 (-30)²=900 (15)²=225 → somma=5150, /9 = 572.2, sqrt ≈ 23.92
SYNTHETIC_RMSSD_1_EXPECTED = round(math.sqrt(5150 / 9), 2)  # 23.92

# Secondo dataset: RR con artifact (salto grande) per test cleaning
SYNTHETIC_NN_WITH_ARTIFACT = [
    1000, 1010, 990, 1500,  # 1500 = ectopic/artifact
    1005, 995, 1015, 985, 1000, 990,
]

# RR impossibili (fuori range fisiologico) per test rimozione
SYNTHETIC_NN_IMPOSSIBLE = [1000, 50, 3000, 990, 1010, 980, 1005, 995]

# Duplicati (stesso timestamp) per test idempotenza
SYNTHETIC_NN_DUPLICATES = [
    (1000.0, 800), (1001.0, 810), (1001.0, 810),  # dup
    (1002.0, 820), (1003.0, 790), (1004.0, 805),
]

# Gap grande tra due battiti (test gestione gap)
SYNTHETIC_NN_GAP = [(1000.0, 800), (1001.0, 810), (1050.0, 800), (1051.0, 790)]

# HRV aggregata già calcolata da Huawei (formato "HRV" generico ambiguo)
SYNTHETIC_HUAWEI_HRV_AGGREGATE = {
    "date": "2026-08-17",
    "hrv": 47.2,          # generico — NON è rMSSD provato
    "rmssd": 46.8,        # esplicito — ok
    "sdnn": 61.4,
}

# Export CSV Huawei simulato (header + righe RR in ms)
SYNTHETIC_CSV = """timestamp,rr_interval,heart_rate
2026-08-17T06:30:00,823,54
2026-08-17T06:30:01,815,55
2026-08-17T06:30:02,831,54
2026-08-17T06:30:03,809,55
2026-08-17T06:30:04,820,54
2026-08-17T06:30:05,826,55
2026-08-17T06:30:06,812,54
2026-08-17T06:30:07,818,55
"""

# Export JSON Huawei simulato (HRV trace)
SYNTHETIC_JSON = {
    "device": "Huawei Watch Fit 5 Pro",
    "hrv_trace": [
        {"timestamp": "2026-08-17T06:30:00", "rr": 823},
        {"timestamp": "2026-08-17T06:30:01", "rr": 815},
        {"timestamp": "2026-08-17T06:30:02", "rr": 831},
        {"timestamp": "2026-08-17T06:30:03", "rr": 809},
    ],
    "aggregates": {"rmssd": 46.8, "sdnn": 61.4},
}
