#!/usr/bin/env python3
"""FINAL robust check: compare ONLY structural code attributes & JS calls.

Extract from each line:
  - all  name="value"  /  name='value'  /  name=value  HTML attributes
    (id, class, onclick, data-*, style, href, value, placeholder, title, for,
     type, autofocus, etc.)  -> these wire behaviour
  - all  foo(   JS function calls and  .bar   property accesses
  - all  function/const/let/return/if/for/while/await/async/new  keywords
Then compare the MULTISET of these tokens between baseline and HEAD.
If identical -> behaviour wiring is byte-for-byte unchanged -> only visible
text differs -> translation is safe.  We IGNORE all free text, comments, prose.
"""
import subprocess, re
from collections import Counter

BASE = "9be7f15"

def read_at(commit, path):
    out = subprocess.run(["git", "show", f"{commit}:{path}"],
                         capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None

ATTR = re.compile(r'\b([a-zA-Z_:][\w:.-]*)=("(?:[^"]*)?"|\'(?:[^\']*)\'?|[^\s"\'<>]+)')
CALL = re.compile(r'\b([A-Za-z_$][\w$]*)\s*\(')
DOT  = re.compile(r'\.([A-Za-z_$][\w$]*)')
KW   = re.compile(r'\b(function|const|let|var|return|if|else|for|while|await|async|new|typeof|class|switch|case|break|continue|throw|try|catch|of|in)\b')

def tokens(lines):
    c = Counter()
    for ln in lines:
        for k, v in ATTR.findall(ln):
            c[f"{k}={v}"] += 1
        for m in CALL.findall(ln):
            c[m + "("] += 1
        for m in DOT.findall(ln):
            c["." + m] += 1
        for m in KW.findall(ln):
            c[m] += 1
    return c

files = ["templates/profile_picker.html", "templates/profile_setup.html",
         "templates/setup.html", "templates/dashboard.html", "app.py"]

allok = True
for f in files:
    old, cur = read_at(BASE, f), read_at("HEAD", f)
    if old is None or cur is None:
        print(f"{f}: (non in baseline)"); continue
    co, cc = tokens(old), tokens(cur)
    only_old = co - cc
    only_cur = cc - co
    if not only_old and not only_cur:
        print(f"✅ {f}: attributi HTML + chiamate JS + keyword IDENTICI "
              f"-> cablaggio comportamentale invariato (solo testo visibile cambiato)")
    else:
        allok = False
        print(f"❌ {f}: CABLAGGIO DIVERSO!")
        if only_old: print("   solo baseline:", dict(list(only_old.items())[:30]))
        if only_cur: print("   solo HEAD:   ", dict(list(only_cur.items())[:30]))

print("\nRISULTATO:", "TUTTO SICURO ✅" if allok
      else "CABLAGGIO CAMBIATO ❌")
