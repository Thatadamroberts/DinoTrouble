#!/usr/bin/env python3
"""Objective checks for the generated audio (it can't be auditioned here).

Fails (exit 1) on clipping, silence, bad durations, clicky loop seams or
variations that are identical. Run after gen_sounds.py.
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiokit import RATE, read  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOPS = ("music", "ambience", "fire_loop")


def db(x):
    return 20 * np.log10(max(x, 1e-9))


def main():
    problems = []
    rows = []
    files = sorted(glob.glob(os.path.join(ROOT, "assets", "*", "*.wav")))
    variants = {}
    for f in files:
        x = read(f)
        rel = os.path.relpath(f, ROOT)
        dur = len(x) / RATE
        peak = np.max(np.abs(x))
        rms = np.sqrt(np.mean(x ** 2))
        clipped = int(np.sum(np.abs(x) > 0.995))
        rows.append(f"{rel:44s} {dur:6.2f}s peak {db(peak):6.1f} dB  rms {db(rms):6.1f} dB")
        if clipped > 2:
            problems.append(f"{rel}: {clipped} clipped samples")
        if rms < 10 ** (-45 / 20):
            problems.append(f"{rel}: nearly silent")
        if dur < 0.03 or dur > 70:
            problems.append(f"{rel}: odd duration {dur:.2f}s")
        if any(k in rel for k in LOOPS):
            seam = abs(x[0] - x[-1])
            head = np.sqrt(np.mean(x[:int(0.05 * RATE)] ** 2))
            tail = np.sqrt(np.mean(x[-int(0.05 * RATE):] ** 2))
            # music restarts on a downbeat, so only beds must match in level
            level_jump = abs(db(head) - db(tail)) > 6 and "music" not in rel
            if seam > 0.08 or level_jump:
                problems.append(f"{rel}: loop seam (step {seam:.3f}, level {db(head):.1f} vs {db(tail):.1f} dB)")
        base = os.path.basename(f).rsplit("_", 1)[0]
        if "sfx" in rel:
            variants.setdefault(base, []).append(x)
    for name, xs in variants.items():
        if len(xs) > 1:
            a, b = xs[0], xs[1]
            k = min(len(a), len(b))
            c = np.corrcoef(a[:k], b[:k])[0, 1]
            if c > 0.98:
                problems.append(f"sfx {name}: variations are near-identical (r={c:.3f})")
    print("\n".join(rows))
    total = sum(os.path.getsize(f) for f in files) / 1e6
    print(f"\n{len(files)} files, {total:.1f} MB")
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("all audio checks passed")


if __name__ == "__main__":
    main()
