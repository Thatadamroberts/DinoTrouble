#!/usr/bin/env python3
"""Synthesise DinoTrouble's placeholder sound effects as 16-bit mono WAVs.

Run from the repo root:
    python3 tools/gen_sounds.py
"""
import math
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sfx")
RATE = 22050


def write(name, samples):
    os.makedirs(OUT, exist_ok=True)
    peak = max(1e-6, max(abs(s) for s in samples))
    gain = 0.8 / peak
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * gain)) * 32767)) for s in samples))


def n(sec):
    return int(sec * RATE)


def lowpass(samples, k):
    out, acc = [], 0.0
    for s in samples:
        acc += (s - acc) * k
        out.append(acc)
    return out


def noise(sec, rnd):
    return [rnd.uniform(-1, 1) for _ in range(n(sec))]


def env(samples, attack, decay_pow=2.0):
    total = len(samples)
    a = max(1, n(attack))
    out = []
    for i, s in enumerate(samples):
        e = i / a if i < a else (1 - (i - a) / max(1, total - a)) ** decay_pow
        out.append(s * e)
    return out


def tone(freq_fn, sec, shape="sine"):
    out, ph = [], 0.0
    for i in range(n(sec)):
        t = i / RATE
        ph += freq_fn(t) / RATE
        if shape == "sine":
            out.append(math.sin(2 * math.pi * ph))
        elif shape == "square":
            out.append(1.0 if (ph % 1) < 0.5 else -1.0)
        else:  # saw
            out.append(2 * (ph % 1) - 1)
    return out


def mix(*tracks):
    length = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(length)]


def main():
    rnd = random.Random(3)
    # rifle shot: noise crack plus low thump
    write("shot", mix(env(lowpass(noise(0.18, rnd), 0.6), 0.002, 3),
                      [x * 0.6 for x in env(tone(lambda t: 120 - t * 300, 0.12), 0.002, 2)]))
    # venom spit: hissy filtered noise
    write("spit", env(lowpass(noise(0.16, rnd), 0.25), 0.03, 1.5))
    # bite / melee: two snaps plus a short growl
    snap = env(lowpass(noise(0.05, rnd), 0.7), 0.001, 4)
    growl = env([s * 0.5 for s in lowpass(tone(lambda t: 90 + 20 * math.sin(t * 60), 0.2, "saw"), 0.2)], 0.01, 1.5)
    write("bite", mix(snap, [0] * n(0.06) + snap, growl))
    # roar: detuned low saws with vibrato plus breathy noise
    roar = mix(tone(lambda t: 85 + 25 * math.sin(t * 9) - t * 20, 1.3, "saw"),
               tone(lambda t: 128 + 30 * math.sin(t * 7), 1.3, "saw"),
               [s * 0.8 for s in noise(1.3, rnd)])
    write("roar", env(lowpass(roar, 0.08), 0.15, 1.2))
    # net throw: whoosh
    write("net", env([s * math.sin(i / n(0.25) * math.pi) for i, s in enumerate(lowpass(noise(0.25, rnd), 0.12))], 0.01, 1))
    # hatch: three cracks then a rising chirp
    crack = env(lowpass(noise(0.03, rnd), 0.8), 0.001, 3)
    chirp = [s * 0.5 for s in env(tone(lambda t: 700 + t * 2400, 0.22), 0.01, 1.5)]
    write("hatch", crack + [0] * n(0.07) + crack + [0] * n(0.05) + crack + [0] * n(0.05) + chirp)
    # UI select blip
    write("select", env(tone(lambda t: 880, 0.06, "square"), 0.002, 2))
    # build/hammer knocks
    knock = env(mix(lowpass(noise(0.05, rnd), 0.5), tone(lambda t: 220, 0.05)), 0.001, 3)
    write("build", knock + [0] * n(0.1) + knock)
    # alert: two-tone beep
    write("alert", env(tone(lambda t: 660, 0.12, "square"), 0.005, 0.5) + env(tone(lambda t: 520, 0.16, "square"), 0.005, 0.8))
    # building collapse / big death
    write("collapse", env(lowpass(noise(0.9, rnd), 0.05), 0.01, 1.8))
    # victory / defeat jingles
    def arp(notes, dur):
        out = []
        for f in notes:
            out += env(tone(lambda t, f=f: f, dur, "square"), 0.005, 1.2)
        return out
    write("victory", arp([523, 659, 784, 1046, 784, 1046], 0.14))
    write("defeat", arp([392, 330, 262, 196], 0.25))
    print("sounds written to", OUT)


if __name__ == "__main__":
    main()
