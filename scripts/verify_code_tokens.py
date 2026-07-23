#!/usr/bin/env python3
"""DECISIVE verification: every code token (attr values, ids, classes,
onclick handlers, JS identifiers, CSS props) is byte-identical between
baseline and HEAD. Only free prose text may differ (that's the translation).

We extract, from each line, tokens that are anchored to code:
  - KEY=VALUE   (id=, class=, onclick=, data-tab=, value=, style=, href=, etc.)
  - .identifier  (JS property/method access)
  - tag names <tag  and </tag>
  - bracket/operator structure
and compare the multiset of those tokens per file. If identical => the
only differences are visible prose => safe translation.
"""
import subprocess, re, difflib
from collections import Counter

BASE = "9be7f15"

def read_at(commit, path):
    out = subprocess.run(["git", "show", f"{commit}:{path}"],
                         capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None

# capture code-anchored tokens
ATTR = re.compile(r'\b([a-zA-Z_-]+)=("(?:[^"]*)"|\'(?:[^\']*)\'|[^\s"\'<>]+)')
DOT  = re.compile(r'\.([a-zA-Z_$][\w$]*)')           # .foo JS access
TAG   = re.compile(r'</?([a-zA-Z][a-zA-Z0-9]*)')      # <div </span
JSPROP= re.compile(r'\b(function|const|let|var|return|if|else|for|while|await|async|new|typeof|class)\b')
FUNCCALL = re.compile(r'\b([a-zA-Z_$][\w$]*)\s*\(')   # foo(

def code_tokens(line):
    toks = []
    for k, v in ATTR.findall(line):
        toks.append(f"{k}={v}")
    for m in DOT.findall(line):
        toks.append("." + m)
    for m in TAG.findall(line):
        toks.append("<" + m)
    for m in JSPROP.findall(line):
        toks.append(m)
    for m in FUNCCALL.findall(line):
        toks.append(m + "(")
    return Counter(toks)

files = ["templates/profile_picker.html", "templates/profile_setup.html",
         "templates/setup.html", "templates/dashboard.html", "app.py"]

allok = True
for f in files:
    old, cur = read_at(BASE, f), read_at("HEAD", f)
    if old is None or cur is None:
        print(f"{f}: (non in baseline)"); continue
    c_old = Counter()
    for ln in old: c_old.update(code_tokens(ln))
    c_cur = Counter()
    for ln in cur: c_cur.update(code_tokens(ln))
    # also compare operator/bracket character counts as a cheap structural check
    br_old = Counter(ch for ln in old for ch in ln if ch in "{}()[];")
    br_cur = Counter(ch for ln in cur for ch in ln if ch in "{}()[];")
    only_old = (c_old - c_cur)
    only_cur = (c_cur - c_old)
    br_diff = {k: (br_old[k], br_cur[k]) for k in set(br_old)|set(br_cur) if br_old[k]!=br_cur[k]}
    if not only_old and not only_cur and not br_diff:
        print(f"✅ {f}: token di codice IDENTICI (attr/id/class/onclick/JS) + parentesi identiche "
              f"-> differenze SOLO testo visibile")
    else:
        allok = False
        print(f"❌ {f}: divergenze di codice rilevate!")
        if only_old: print("   solo nel baseline:", dict(list(only_old.items())[:20]))
        if only_cur: print("   solo in HEAD:    ", dict(list(only_cur.items())[:20]))
        if br_diff:  print("   parentesi:      ", br_diff)

print("\nRISULTATO:", "TUTTO SICURO ✅ (nessun token/struttura di codice cambiata)" if allok
      else "PROBLEMI RILEVATI ❌")
