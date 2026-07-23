#!/usr/bin/env python3
"""FINAL-2: compare ONLY behaviour-bearing HTML attributes.

Behaviour in these templates is wired by:
  id=  class=  onclick=  data-*=  style=  href=  type=  for=  value=
  (NOT placeholder=/title=/alt= — those are visible text, safe to change)
We strip the visible text of placeholder/title/alt FIRST (so their prose
doesn't leak), then extract the behaviour attrs and compare multisets.
"""
import subprocess, re
from collections import Counter

BASE = "9be7f15"
BEHAV = re.compile(r'\b((?:id|class|onclick|on(?:change|input|click|submit)|data-[\w-]+|style|href|type|for|value|autofocus|rel|target|src|method|name|min|max|step|id)\s*=\s*)(?:"[^"]*"|\'[^\']*\'|[^\s"\'<>]+)')

def read_at(commit, path):
    out = subprocess.run(["git", "show", f"{commit}:{path}"],
                         capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None

# strip visible-text attributes entirely before extraction
def strip_text_attrs(line):
    return re.sub(r'\b(title|placeholder|alt)\s*=\s*(?:"[^"]*"|\'[^\']*\')', "", line)

def beh_attrs(lines):
    c = Counter()
    for ln in lines:
        ln = strip_text_attrs(ln)
        for m in BEHAV.findall(ln):
            c[m] += 1
    return c

files = ["templates/profile_picker.html", "templates/profile_setup.html",
         "templates/setup.html", "templates/dashboard.html"]

allok = True
for f in files:
    old, cur = read_at(BASE, f), read_at("HEAD", f)
    if old is None or cur is None:
        print(f"{f}: (non in baseline)"); continue
    co, cc = beh_attrs(old), beh_attrs(cur)
    only_old = co - cc
    only_cur = cc - co
    if not only_old and not only_cur:
        print(f"✅ {f}: attributi comportamentali (id/class/onclick/data/style/href/...) IDENTICI")
    else:
        allok = False
        print(f"❌ {f}: attributi comportamentali DIVERSI!")
        if only_old: print("   solo baseline:", dict(list(only_old.items())[:40]))
        if only_cur: print("   solo HEAD:   ", dict(list(only_cur.items())[:40]))

print("\nRISULTATO:", "TUTTO SICURO ✅" if allok else "ATTR COMPORTAMENTALI CAMBIATI ❌")
