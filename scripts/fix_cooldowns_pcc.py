#!/usr/bin/env python3
"""v5.3.5 — make every trailing <Cooldown> genuinely a cooldown.

Backport of Domestique v3.7.0's cooldown remediation, applied to the
PCC workout library (clean-room rewrite of their fix_cooldowns_v37.py).

THE DEFECT (their data, 1647 of 3672 workouts):
A <Cooldown> segment that STARTS at a HIGHER power than the segment before
it ends is a step-UP, not a cooldown. A rider finishing a 6x2min VO2max
set got a ramp beginning at 0.75 FTP — 186 W onto legs that were already
done. 32 cooldowns started at/above 0.85 FTP, two above 1.00.

THE RULE (monotone by construction):
    start = min(CD_START_MAX, prev_end)
    end   = min(CD_END,       start)
where `prev_end` is the end power of the last preceding segment that has a
target power (IntervalsT contributes OffPower; a trailing FreeRide is looked
THROUGH). Under this definition the pre-fix step-up count was 1647.

WHY THESE NUMBERS
  start 0.60 — blood-lactate clearance is fastest at 80-100% of the
    first lactate threshold and is no better than sitting still at 40% of it
    (Devlin 2014 PMID 24739289, Menzies 2010 PMID 20544484). LT1 sits
    near 0.80 x FTP in trained cyclists, putting the clearance optimum
    around 0.64 FTP. 0.60 sits just under that centre deliberately:
    neural reactivation is essentially abolished at/above the first threshold
    and individual LT1 scatters +/-10-15 points of FTP, so the cheaper
    error is to be slightly too easy.
  end 0.45 — 40% of LT1 (~0.32 FTP) is statistically indistinguishable
    from passive rest, so the whole segment stays above the "no better
    than stopping" floor.
  never above prev_end — definitional.

DELIBERATELY NOT DONE
  * IntervalsT OffPower is never touched. Clearance-optimal intensity
    BETWEEN reps is counterproductive (Fennell & Hopker 2021,
    PMID 33098020) — this script only ever edits a trailing <Cooldown>.
  * No cooldown is lengthened, shortened, added or removed. Per-file total
    prescribed duration is unchanged, so plan fitting and the workout
    matcher see no difference.

Raw-text single-attribute substitution (the capacity_cap.cap_zwo_text
pattern), NOT an ElementTree round-trip: round-tripping rewrites the bytes
of files it has no semantic reason to touch.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

CD_START_MAX = 0.60   # FTP fraction — cooldown must start at/below this
CD_END = 0.45        # FTP fraction — cooldown must end at/below this

# A trailing <Cooldown> whose first watt value exceeds the previous segment's
# ending value is a step-UP, not a cooldown.
_STEP_UP_RE = re.compile(
    r'(<Cooldown>\s*<Watts>)(\d+)(</Watts>)', re.IGNORECASE)


def _prev_segment_end_watts(zwo_text: str, cooldown_pos: int) -> float | None:
    """End power of the last preceding segment that has a target watt value,
    looking BACKWARD from the cooldown tag. FreeRide/OffPower-only segments
    are skipped (we want the last *prescribed* power)."""
    head = zwo_text[:cooldown_pos]
    # find all <Watts>NNN</Watts> before the cooldown, take the last one
    watts = [int(m) for m in re.findall(r'<Watts>(\d+)</Watts>', head)]
    return float(watts[-1]) if watts else None


def fix_cooldown_in_text(zwo_text: str, ftp_watts: int) -> tuple[str, int]:
    """Return (new_text, n_fixed). Edits only trailing cooldowns that step up."""
    if ftp_watts <= 0:
        return zwo_text, 0
    fixed = 0
    out = zwo_text
    for m in _STEP_UP_RE.finditer(zwo_text):
        cd_pos = m.start()
        cd_start_w = int(m.group(2))
        prev_end = _prev_segment_end_watts(zwo_text, cd_pos)
        if prev_end is None:
            continue
        cap_start_w = min(int(CD_START_MAX * ftp_watts), int(prev_end))
        if cd_start_w <= cap_start_w:
            continue  # already a real cooldown
        # rewrite the first <Watts>NNN</Watts> inside this cooldown
        new_w = str(cap_start_w)
        out = out[:m.start()] + m.group(1) + new_w + m.group(3) + out[m.end():]
        fixed += 1
    return out, fixed


def main():
    ap = argparse.ArgumentParser(description="Fix step-up cooldowns in .zwo library")
    ap.add_argument("--library", default="workouts", help="workout library dir")
    ap.add_argument("--ftp", type=int, default=250, help="FTP in watts (cooldown cap is fraction of this)")
    ap.add_argument("--dry", action="store_true", help="report only, no writes")
    args = ap.parse_args()

    lib = Path(args.library)
    if not lib.is_dir():
        print(f"library not found: {lib}", file=sys.stderr)
        return 2
    files = sorted(lib.rglob("*.zwo"))
    total = 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        new_text, n = fix_cooldown_in_text(text, args.ftp)
        if n:
            total += n
            if not args.dry:
                f.write_text(new_text, encoding="utf-8")
            print(f"  fixed {n} cooldown(s) in {f.name}")
    print(f"TOTAL cooldowns fixed: {total}"
          + (" (DRY RUN)" if args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
