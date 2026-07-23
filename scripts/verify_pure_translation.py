#!/usr/bin/env python3
"""Verify i18n edits are PURE string translations vs baseline — robust v2.

Strips from each line everything that is NOT code structure:
  1. HTML comments  <!-- ... -->
  2. quoted strings (", ', `)
  3. any letter-run NOT immediately adjacent to a code anchor
     ( = ( ) { } ; < > / [ ] ' " ` . @ )
  -> only code tokens (tag names, attr names, ids, JS identifiers,
     operators) survive. Two lines that differ ONLY in visible prose
  will then have identical skeletons.
"""
import subprocess, re, difflib

BASE = "9be7f15"
ANCHOR = r"=(){};<>/\[\]'\"`\.@"
PROSE = re.compile(r"(?<![" + ANCHOR + r"])[A-Za-z]+(?![" + ANCHOR + r"])")

def read_at(commit, path):
    out = subprocess.run(["git", "show", f"{commit}:{path}"],
                         capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None

def skeleton(line):
    line = re.sub(r"<!--.*?-->", "", line, flags=re.S)   # HTML comments
    line = re.sub(r'"[^"]*"', '""', line)
    line = re.sub(r"'[^']*'", "''", line)
    line = re.sub(r"`[^`]*`", "``", line)
    line = PROSE.sub("", line)                            # free prose words
    line = re.sub(r"\s+", " ", line).strip()
    return line

files = ["templates/profile_picker.html", "templates/profile_setup.html",
         "templates/setup.html", "templates/dashboard.html", "app.py"]

allok = True
for f in files:
    old, cur = read_at(BASE, f), read_at("HEAD", f)
    if old is None or cur is None:
        print(f"{f}: (non in baseline)"); continue
    matcher = difflib.SequenceMatcher(None, old, cur, autojunk=False)
    problems = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        ob, nb = old[i1:i2], cur[j1:j2]
        n = max(len(ob), len(nb))
        for k in range(n):
            o = ob[k] if k < len(ob) else ""
            nn = nb[k] if k < len(nb) else ""
            if skeleton(o) != skeleton(nn):
                problems.append((o, nn))
    if not problems:
        nb_blocks = sum(1 for t,*_ in matcher.get_opcodes() if t != "equal")
        print(f"✅ {f}: {nb_blocks} blocchi cambiati — TUTTI pure traduzioni")
    else:
        allok = False
        print(f"❌ {f}: {len(problems)} righe con skeleton DIVERSO:")
        for o, nn in problems[:25]:
            print("   OLD:", o[:130]); print("   NEW:", nn[:130]); print()

print("\nRISULTATO:", "TUTTO SICURO ✅" if allok else "PROBLEMI RILEVATI ❌")
