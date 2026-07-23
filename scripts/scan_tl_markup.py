#!/usr/bin/env python3
"""Scan template literals that contain HTML tags for visible English text.
Only template literals with '<' (markup) are examined — those carry UI text.
${...} masked. Reports multi-word English phrase-runs not in TECH/Italian."""
import re, collections

TECH = {
    "sweet","spot","over","under","pyramidal","polarized","endurance","tempo",
    "threshold","anaerobic","sprint","recovery","ftp","ctl","atl","tsb","tss",
    "w/kg","vo2max","zwo","fit","hrv","rmssd","mae","np","if","hr","cat","hc",
    "gran","fondo","century","crit","sportive","dfa","domestique","garmin",
    "strava","zwift","trainerroad","mywhoosh","wahoo","hammerhead","rest",
    "kg","km","min","bpm","kj","gold","good","med","low","ultra","foster",
    "coggan","allen","beta","alpha","sql","api","icu","gpx","xss","utf","icon",
    "svg","html","px","ms","xml","monotony","strain","robustness","citations",
    "window","rides","weight","score","chronic","acute","session","planned",
    "actual","weekly","variety","v8","w","kj",
}
TL = re.compile(r"`(?:\\.|[^`\\])*?`")
WORD = re.compile(r"[A-Za-z][A-Za-z'’]+")
RUN = re.compile(r"[A-Za-z][A-Za-z'’]+(?:\s+[A-Za-z][A-Za-z'’]+)+")

cnt = collections.Counter()
examples = {}
for p in ["templates/dashboard.html", "templates/profile_picker.html",
          "templates/profile_setup.html", "templates/setup.html"]:
    src = open(p, encoding="utf-8").read()
    blocks = re.findall(r"<script>(.*?)</script>", src, re.S)
    for b in blocks:
        for m in TL.finditer(b):
            lit = m.group(0)[1:-1]
            if "<" not in lit:
                continue
            masked = re.sub(r"\$\{[^}]*\}", " V ", lit)
            txt = " ".join(re.findall(r">([^<>]+)<", masked))
            for run in RUN.findall(txt):
                words = WORD.findall(run)
                if all(w.lower() in TECH for w in words):
                    continue
                if re.search(r"[àèéìòù]", run):
                    continue
                # skip pure-attribute/style fragments
                if "style" in run.lower() or "class" in run.lower():
                    continue
                r = run.strip()
                cnt[r] += 1
                examples.setdefault(r, p)

print("=== Visible EN phrases inside HTML-bearing template literals ===")
for r, c in cnt.most_common(60):
    print(f"  {c:3d}  {r!r}   [{examples[r]}]")
