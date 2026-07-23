#!/usr/bin/env python3
"""DEFINITIVE structural check: strip ALL visible text, compare code skeleton.

For each file, produce a "structure-only" version where:
  1. HTML comments         <!-- ... -->  removed
  2. quoted strings ", ', `              replaced by ''
  3. HTML tag-body text    >TEXT<        replaced by ><
  4. CSS/JS free prose words removed via a prose-regex that only keeps
     characters adjacent to code anchors.

Then diff baseline vs HEAD line-by-line. ANY difference => a structural
(code) change, not a translation.
"""
import subprocess, re, difflib

BASE = "9be7f15"
ANCHOR = r"=(){};<>/\[\]'\"`\.@#:"
PROSE = re.compile(r"(?<![" + ANCHOR + r"])[A-Za-z][A-Za-z'’\-]*(?![" + ANCHOR + r"])")

def read_at(commit, path):
    out = subprocess.run(["git", "show", f"{commit}:{path}"],
                         capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None

def strip_visible(line):
    line = re.sub(r"<!--.*?-->", "", line, flags=re.S)
    line = re.sub(r"`[^`]*`", "``", line)
    line = re.sub(r'"[^"]*"', '""', line)
    line = re.sub(r"'[^']*'", "''", line)
    line = re.sub(r">[^<>]+<", "><", line)
    # remove remaining free prose (letters not touching code anchors)
    line = PROSE.sub("", line)
    return line

def structure(lines):
    return [strip_visible(l) for l in lines]

files = ["templates/profile_picker.html", "templates/profile_setup.html",
         "templates/setup.html", "templates/dashboard.html", "app.py"]

allok = True
for f in files:
    old, cur = read_at(BASE, f), read_at("HEAD", f)
    if old is None or cur is None:
        print(f"{f}: (non in baseline)"); continue
    so, sc = structure(old), structure(cur)
    matcher = difflib.SequenceMatcher(None, so, sc, autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            o = so[i1 + k] if i1 + k < i2 else "<removed>"
            c = sc[j1 + k] if j1 + k < j2 else "<added>"
            if o != c:
                diffs.append((old[i1 + k] if i1 + k < len(old) else "",
                              cur[j1 + k] if j1 + k < len(cur) else ""))
    if not diffs:
        print(f"✅ {f}: STRUTTURA DI CODICE IDENTICA — solo testo visibile cambiato")
    else:
        allok = False
        print(f"❌ {f}: {len(diffs)} righe con struttura DIVERSA (ROTTURA REALE):")
        for o, c in diffs[:25]:
            print("   OLD:", o[:140]); print("   NEW:", c[:140]); print()

print("\nRISULTATO:", "TUTTO SICURO ✅" if allok else "ROTTURE RILEVATE ❌")
