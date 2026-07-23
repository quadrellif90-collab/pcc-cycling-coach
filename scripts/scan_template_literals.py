#!/usr/bin/env python3
"""Scan template literals for VISIBLE English phrases (>=2 words w/ space).
Masks ${...} so only static text is examined. Ignores single code-ish
identifiers. Flags English phrase-runs not already in Italian/technical."""
import re, collections

TECH = {
    "sweet","spot","over","under","pyramidal","polarized","endurance","tempo",
    "threshold","anaerobic","sprint","recovery","ftp","ctl","atl","tsb","tss",
    "w/kg","vo2max","zwo","fit","hrv","rmssd","mae","np","if","hr","cat","hc",
    "gran","fondo","century","crit","sportive","dfa","domestique","garmin",
    "strava","zwift","trainerroad","mywhoosh","wahoo","hammerhead","chart.js",
    "json","csv","png","pdf","crs","rest","kg","km","min","bpm","kj","gold",
    "good","med","low","ultra","foster","coggan","allen","beta","alpha","sql",
    "api","icu","gpx","xss","utf","icon","svg","html","px","ms","xml","var",
    "ok","http","monotony","strain","robustness","citations","window","rides",
    "weight","score","chronic","acute",
}

TL = re.compile(r"`(?:\\.|[^`\\])*?`")

def phrases(lit):
    masked = re.sub(r"\$\{[^}]*\}", " ‹V› ", lit)
    out = []
    # phrase = sequence of >=2 latin words separated by single spaces
    for run in re.findall(r"(?:[A-Za-z][A-Za-z'’]+(?:\s+[A-Za-z][A-Za-z'’]+)+)", masked):
        words = re.findall(r"[A-Za-z][A-Za-z'’]*", run)
        if all(w.lower() in TECH for w in words):
            continue
        if re.search(r"[àèéìòù]", run):
            continue
        out.append(run.strip())
    return out

allf = {}
for p in ["templates/dashboard.html", "templates/profile_picker.html",
          "templates/profile_setup.html", "templates/setup.html"]:
    src = open(p, encoding="utf-8").read()
    blocks = re.findall(r"<script>(.*?)</script>", src, re.S)
    found = []
    for b in blocks:
        for m in TL.finditer(b):
            found += phrases(m.group(0)[1:-1])
    if found:
        allf[p] = found

cnt = collections.Counter()
for lst in allf.values():
    for r in lst:
        cnt[r] += 1

print("=== Visible English PHRASES in template literals ===")
for r, c in cnt.most_common(60):
    print(f"  {c:3d}  {r!r}")
