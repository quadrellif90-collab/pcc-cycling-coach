#!/usr/bin/env python3
"""Extract CLEAN visible strings from dashboard.html for localization.

We keep only strings that are very likely user-visible text (not JS code /
HTML markup / template fragments):
  - HTML element text content (tag bodies)
  - JS .textContent / .innerText assignments (literal strings, no ${})
  - alert/confirm/prompt string literals
  - placeholder= / title= / alt= attribute literals
  - <option> text
We REJECT strings containing < > $ { } ; + \n or that look like code,
and limit length to 1..90 chars.
"""
import re, json, collections, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "templates/dashboard.html"
html = open(SRC, encoding="utf-8").read()
strings = []

def clean(t):
    t = t.strip()
    if not t:
        return None
    # reject code/markup signals
    if any(ch in t for ch in "<>$}{;+\n\t"):
        return None
    if t.startswith(("@", "{", "$", "#", "%")):
        return None
    # must contain at least 2 latin letters and a space or common word
    if not re.search(r"[A-Za-z]{2,}", t):
        return None
    return t

# tag text
for m in re.finditer(r">([^<>{}]{1,90})<", html):
    t = clean(m.group(1))
    if t:
        strings.append(("tag", t))
# textContent / innerText
for m in re.finditer(r"\.(?:textContent|innerText)\s*=\s*(['\"])((?:\\\1|(?!\1).)*?)\1", html):
    t = clean(m.group(2))
    if t:
        strings.append(("prop", t))
# alert/confirm/prompt
for kw in ("alert", "confirm", "prompt"):
    for m in re.finditer(kw + r"\s*\(\s*(['\"])((?:\\\1|(?!\1).)*?)\1", html):
        t = clean(m.group(2))
        if t:
            strings.append((kw, t))
# attributes
for attr in ("placeholder", "title", "alt"):
    for m in re.finditer(attr + r"\s*=\s*(['\"])((?:\\\1|(?!\1).)*?)\1", html):
        t = clean(m.group(2))
        if t:
            strings.append((attr, t))
# options
for m in re.finditer(r"<option[^>]*>([^<]{1,90})</option>", html):
    t = clean(m.group(1))
    if t:
        strings.append(("option", t))

cnt = collections.Counter(s[1] for s in strings)
print(f"Total candidates: {len(strings)}  unique: {len(cnt)}")
# save sorted by frequency
out = {s: c for s, c in cnt.most_common()}
with open("scripts/_clean_strings.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Saved scripts/_clean_strings.json")
print("\nTop 40:")
for s, c in cnt.most_common(40):
    print(f"  {c:3d}  {s}")
