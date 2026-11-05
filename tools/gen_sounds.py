#!/usr/bin/env python3
"""Synthesise DinoTrouble's audio: sound effects (with variations), music
loops and ambience loops. Pure numpy; see audiokit.py and instruments.py.

    python3 tools/gen_sounds.py            # everything
    python3 tools/gen_sounds.py sfx        # just one group: sfx | music | ambience

Outputs 16-bit mono WAV at 22.05 kHz:
    assets/sfx/<name>_<variant>.wav
    assets/music/<track>.wav        (seamless loops)
    assets/ambience/<bed>.wav       (seamless loops)
"""
import os
import shutil
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instruments as ins  # noqa: E402
from audiokit import (RATE, adsr, convolve, decay, fade, filt, formants, impulse, loop_fold, mix, n, note,  # noqa: E402
                      noise, osc, place, reverb, softclip, sweep, t_axis, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX = os.path.join(ROOT, "assets", "sfx")
MUSIC = os.path.join(ROOT, "assets", "music")
AMB = os.path.join(ROOT, "assets", "ambience")


def rng_for(name, v):
    return np.random.default_rng(zlib.crc32(f"{name}:{v}".encode()))


def jit(rng, amount):
    return 1.0 + rng.uniform(-amount, amount)


# ===========================================================================
# Sound effects
# ===========================================================================
def sfx_shot(rng, distant=False):
    crack = filt(noise(0.012, rng), "hp", 2500) * decay(0.012, 0.003)
    body = filt(noise(0.12, rng), "bp", 900 * jit(rng, 0.15), 0.8) * decay(0.12, 0.035)
    thump = osc("sine", 90 * (1 + 2 * np.exp(-t_axis(0.12) / 0.01))) * decay(0.12, 0.03)
    x = mix((crack, 0, 1.0), (body, 0.002, 0.9), (thump, 0, 0.6))
    if distant:
        x = filt(x, "lp", 2200)
    return reverb(softclip(x, 2.0), rng, mix=0.45 if distant else 0.3, decay_s=0.5, damp_hz=3500)


def sfx_burst(rng):
    out = np.zeros(n(0.9))
    for i in range(rng.integers(4, 6)):
        s = sfx_shot(rng)[:n(0.25)] * jit(rng, 0.15)
        place(out, s, i * 0.075 + rng.uniform(0, 0.01))
    return out


def sfx_spit(rng):
    sec = 0.32
    x = noise(sec, rng) * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * t_axis(sec)))
    x = sweep(x, "bp", lambda t: 2600 * (1 - t) + 500, q=2.0)
    return x * adsr(sec, 0.01, 0.05, 0.7, 0.2) * 2.2


def sfx_net(rng):
    sec = 0.4
    x = sweep(noise(sec, rng), "bp", lambda t: 400 + 1300 * np.sin(np.pi * t), q=1.5) * np.sin(np.pi * t_axis(sec) / sec)
    for k in range(3):
        click = filt(noise(0.02, rng), "bp", 1200, 2) * decay(0.02, 0.005)
        place(x, click, 0.18 + k * 0.05, 0.6)
    return x * 1.6


def sfx_impact_flesh(rng):
    thud = osc("sine", 110 * jit(rng, 0.3) * (1 + np.exp(-t_axis(0.15) / 0.01))) * decay(0.15, 0.03 * jit(rng, 0.4))
    squelch = filt(noise(0.12, rng), "bp", 700 * jit(rng, 0.35), 1.5) * decay(0.12, 0.04 * jit(rng, 0.4))
    return mix((thud, 0, jit(rng, 0.3)), (squelch, rng.uniform(0.0, 0.02), rng.uniform(0.6, 1.4)))


def sfx_impact_wood(rng):
    f = 320 * jit(rng, 0.15)
    knock = (osc("sine", f, 0.25) + 0.5 * osc("sine", f * 2.7, 0.25)) * decay(0.25, 0.05)
    splinter = filt(noise(0.2, rng), "hp", 2000) * decay(0.2, 0.05)
    return reverb(mix(knock, (splinter, 0.004, 0.5)), rng, 0.2, 0.3)


def creature(rng, sec, f0_curve, wave="saw", formant_set=(700, 1800, 3000), rasp=0.3, vib_rate=6.0, vib_depth=0.02,
             env=(0.05, 0.1, 0.8, 0.25), trill=0.0, trill_rate=30.0):
    t = t_axis(sec)
    f0 = np.array([f0_curve(x) for x in t / sec])
    f0 = f0 * (1 + vib_depth * np.sin(2 * np.pi * vib_rate * t)) * (1 + 0.01 * rng.standard_normal(len(t)).cumsum() / 200)
    src = osc(wave, f0)
    if trill > 0:
        src *= 1 - trill * (0.5 + 0.5 * np.sin(2 * np.pi * trill_rate * t))
    voiced = formants(src, list(formant_set), q=4.0, gains=[1.0, 0.6, 0.35])
    breath = filt(noise(sec, rng), "bp", formant_set[1], 1.0) * np.abs(src)
    x = voiced + rasp * breath
    return softclip(x * adsr(sec, *env) * 3.0, 1.5)


def sfx_raptor_call(rng):
    peak = 1300 * jit(rng, 0.12)
    sec = 0.55 * jit(rng, 0.15)
    x = creature(rng, sec, lambda u: 700 + (peak - 700) * np.sin(np.pi * min(1, u * 1.3)) ** 0.7 - 250 * u,
                 formant_set=(900, 2200, 3400), rasp=0.5, vib_rate=28, vib_depth=0.03, trill=0.35, trill_rate=34,
                 env=(0.02, 0.05, 0.8, 0.2))
    return reverb(x, rng, 0.22, 0.5)


def sfx_dilo_call(rng):
    sec = 0.7
    hiss = filt(noise(sec, rng), "bp", 4200 * jit(rng, 0.1), 1.2) * adsr(sec, 0.04, 0.1, 0.8, 0.3)
    rattle = hiss * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 26 * t_axis(sec))))
    hoot = creature(rng, 0.35, lambda u: 520 * jit(rng, 0.05) + 140 * np.sin(np.pi * u), wave="tri",
                    formant_set=(600, 1300, 2600), rasp=0.2)
    return reverb(mix((rattle, 0, 0.9), (hoot, 0.25, 0.7)), rng, 0.2, 0.5)


def sfx_trike_call(rng):
    sec = 1.3 * jit(rng, 0.1)
    base = 72 * jit(rng, 0.08)
    x = creature(rng, sec, lambda u: base * (1 + 0.3 * np.sin(np.pi * u)), formant_set=(320, 760, 1900), rasp=0.35,
                 vib_rate=4.5, vib_depth=0.015, env=(0.15, 0.2, 0.85, 0.4))
    breath = filt(noise(sec, rng, "brown"), "lp", 500) * adsr(sec, 0.2, 0.2, 0.7, 0.4) * 0.5
    return reverb(x + breath, rng, 0.3, 0.9)


def sfx_trex_roar(rng):
    sec = 1.9 * jit(rng, 0.1)
    t = t_axis(sec)
    swell = adsr(sec, 0.25, 0.3, 0.9, 0.6)
    sub = osc("saw", 48 * jit(rng, 0.1) * (1 + 0.25 * np.sin(np.pi * t / sec)) * (1 + 0.04 * np.sin(2 * np.pi * 9 * t)))
    sub = filt(sub, "lp", 260, order=2)
    mid_f = 140 * jit(rng, 0.1) * (1 + 0.35 * np.sin(np.pi * t / sec))
    mid = osc("saw", mid_f * (1 + 0.02 * np.sin(2 * np.pi * 7 * t)))
    mid = sweep(mid, "bp", lambda u: 450 + 500 * np.sin(np.pi * u), q=1.6)
    rasp = filt(noise(sec, rng), "bp", 1100, 0.8) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 23 * t)))
    x = softclip((sub * 1.2 + mid * 0.9 + rasp * 0.6) * swell * 2.2, 2.2)
    return reverb(x, rng, 0.35, 1.2, 3000)


def sfx_bite(rng, big=False):
    out = np.zeros(n(0.7 if big else 0.4))
    for k in range(2):
        snap = filt(noise(0.05, rng), "bp", (1500 if big else 2800) * jit(rng, 0.15), 1.2) * decay(0.05, 0.012)
        place(out, snap, k * (0.07 if big else 0.05), 1.0)
    crunch = filt(noise(0.25, rng), "lp", 1800 if big else 3200) * decay(0.25, 0.06)
    place(out, crunch, 0.03, 0.8)
    if big:
        thump = osc("sine", 70 * (1 + np.exp(-t_axis(0.3) / 0.02))) * decay(0.3, 0.08)
        place(out, thump, 0.0, 1.0)
        growl = creature(rng, 0.4, lambda u: 85 * (1 - 0.3 * u), formant_set=(400, 900, 2000), rasp=0.4)
        place(out, growl, 0.1, 0.5)
    return reverb(out, rng, 0.15, 0.35)


def sfx_stomp(rng):
    sec = 0.6
    t = t_axis(sec)
    thud = osc("sine", 46 * jit(rng, 0.1) * (1 + 1.2 * np.exp(-t / 0.02))) * decay(sec, 0.12)
    rumble = filt(noise(sec, rng, "brown"), "lp", 220) * decay(sec, 0.2)
    debris = filt(noise(0.2, rng), "hp", 2500) * decay(0.2, 0.05) * 0.15
    return softclip(mix(thud, (rumble, 0, 0.8), (debris, 0.02, 1.0)) * 1.5, 1.5)


def sfx_dino_death(rng):
    sec = 1.4
    return reverb(creature(rng, sec, lambda u: 180 * jit(rng, 0.15) * (1 - 0.55 * u), formant_set=(500, 1100, 2400),
                           rasp=0.5, vib_rate=5, vib_depth=0.03, env=(0.05, 0.3, 0.7, 0.6)), rng, 0.3, 0.8)


def sfx_human_down(rng):
    thud = osc("sine", 90 * (1 + np.exp(-t_axis(0.3) / 0.02))) * decay(0.3, 0.06)
    out = mix(thud, (filt(noise(0.15, rng, "pink"), "lp", 900) * decay(0.15, 0.05), 0, 0.7))
    for k in range(3):  # gear rattle
        f = rng.uniform(2500, 4200)
        clink = (osc("sine", f, 0.08) + 0.5 * osc("sine", f * 1.48, 0.08)) * decay(0.08, 0.015)
        place(out, clink, 0.06 + k * 0.045, 0.25)
    return out


def sfx_hatch(rng):
    out = np.zeros(n(1.0))
    for k in range(3):
        crack = filt(noise(0.03, rng), "hp", 1800) * decay(0.03, 0.006)
        place(out, crack, k * rng.uniform(0.07, 0.11), 0.9)
    sec = 0.3
    t = t_axis(sec)
    f = 1300 * jit(rng, 0.1) * (1 + 0.6 * t / sec) * (1 + 0.03 * np.sin(2 * np.pi * 30 * t))
    chirp = osc("sine", f) * adsr(sec, 0.01, 0.05, 0.7, 0.12)
    place(out, chirp, 0.36, 0.7)
    place(out, chirp[::-1] * 0.6, 0.62, 0.5)
    return reverb(out, rng, 0.2, 0.4)


def sfx_build(rng):
    out = np.zeros(n(0.9))
    for k in range(2):
        f = 260 * jit(rng, 0.1)
        knock = (osc("sine", f, 0.2) + 0.4 * osc("sine", f * 3.1, 0.2)) * decay(0.2, 0.04)
        click = filt(noise(0.01, rng), "hp", 3000) * decay(0.01, 0.002)
        place(out, knock, k * 0.17, 0.9)
        place(out, click, k * 0.17, 0.6)
    saw_t = 0.35
    stroke = filt(noise(saw_t, rng), "bp", 2400, 1.0) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t_axis(saw_t))) * adsr(saw_t, 0.03, 0.05, 0.8, 0.1)
    place(out, stroke, 0.45, 0.35)
    return reverb(out, rng, 0.15, 0.3)


def sfx_gather_rock(rng):
    f = rng.uniform(2000, 2600)
    clink = sum(osc("sine", f * r, 0.4) * g for r, g in ((1, 1), (1.53, 0.6), (2.3, 0.4))) * decay(0.4, 0.06)
    crumble = filt(noise(0.3, rng), "lp", 2500) * decay(0.3, 0.08) * 0.5
    return reverb(mix(clink, (crumble, 0.01, 1.0)), rng, 0.15, 0.3)


def sfx_gather_wood(rng):
    thump = osc("sine", 150 * jit(rng, 0.1), 0.25) * decay(0.25, 0.05)
    rustle = filt(noise(0.35, rng, "pink"), "bp", 1600, 0.8) * adsr(0.35, 0.05, 0.1, 0.6, 0.15) * 0.6
    return mix(thump, (rustle, 0.03, 1.0))


def sfx_collapse(rng):
    sec = 1.6
    crunch = sweep(noise(sec, rng), "lp", lambda u: 3500 * (1 - u) + 250) * decay(sec, 0.5)
    rumble = filt(noise(sec, rng, "brown"), "lp", 160) * decay(sec, 0.6)
    out = mix(crunch, (rumble, 0, 1.2))
    for k in range(5):
        crack = filt(noise(0.05, rng), "bp", rng.uniform(600, 1800), 1.5) * decay(0.05, 0.015)
        place(out, crack, rng.uniform(0, 0.8), 0.8)
    return reverb(out, rng, 0.3, 0.9)


def sfx_explosion(rng):
    sec = 1.8
    t = t_axis(sec)
    boom = osc("sine", 55 * (1 + 2.5 * np.exp(-t / 0.04))) * decay(sec, 0.35)
    blast = sweep(noise(sec, rng), "lp", lambda u: 5000 * (1 - u) ** 2 + 200) * decay(sec, 0.4)
    out = softclip(mix(boom, (blast, 0, 1.3)) * 2.0, 2.0)
    for k in range(8):
        place(out, filt(noise(0.02, rng), "hp", 2000) * decay(0.02, 0.005), 0.3 + rng.uniform(0, 1.2), 0.3)
    return reverb(out, rng, 0.35, 1.2)


def sfx_fire_loop(rng):
    L = n(4.0)
    buf = filt(noise(5.0, rng, "brown"), "lp", 400)[:L] * 0.5
    for k in range(70):
        crack = filt(noise(0.015, rng), "bp", rng.uniform(1500, 5000), 1.5) * decay(0.015, 0.004)
        place(buf, crack, rng.uniform(0, 4.0), rng.uniform(0.2, 0.8))
    return crossfade_loop(np.concatenate([buf, buf[:n(0.5)]]), L, n(0.5))


def sfx_splash(rng):
    sec = 0.35
    t = t_axis(sec)
    plop = osc("sine", 650 * jit(rng, 0.2) * np.exp(-t / 0.05) + 180) * decay(sec, 0.06)
    spray = filt(noise(sec, rng), "hp", 2500) * decay(sec, 0.08) * 0.5
    return reverb(mix(plop, (spray, 0.01, 1.0)), rng, 0.2, 0.4)


D_MINOR = {"D3": note("D3"), "F3": note("F3"), "A3": note("A3"), "D4": note("D4"), "F4": note("F4"), "A4": note("A4"),
           "D5": note("D5"), "C5": note("C5"), "Bb4": note("Bb4"), "G4": note("G4"), "E4": note("E4"), "F#4": note("F#4")}


def sfx_ui_click(rng):
    sec = 0.05
    tick = osc("sine", 1900 * jit(rng, 0.05), sec) * decay(sec, 0.012)
    return tick + filt(noise(sec, rng), "hp", 4000) * decay(sec, 0.004) * 0.4


def sfx_ui_confirm(rng):
    return reverb(ins.chime([note("A4"), note("D5")], rng, 0.07, 0.8), rng, 0.2, 0.5)


def sfx_objective(rng):
    return reverb(ins.chime([note("D4"), note("F4"), note("A4"), note("D5")], rng, 0.09), rng, 0.3, 0.8)


def sfx_alert(rng):
    a = ins.horn(note("D4"), 0.35) * 0.9
    b = ins.horn(note("A3"), 0.5) * 0.9
    return reverb(mix(a, (b, 0.32, 1.0)), rng, 0.25, 0.7)


def sfx_wave_drums(rng):
    out = np.zeros(n(2.6))
    for i, (tt, v) in enumerate(((0.0, 1.0), (0.42, 0.8), (0.63, 0.8), (0.84, 1.0))):
        place(out, ins.taiko(rng, v, 58 if i % 3 == 0 else 64), tt, 1.0)
    for k in range(6):
        place(out, ins.tom(rng, 0.5 + k * 0.08, 150 - k * 6), 1.15 + k * 0.07, 0.8)
    place(out, ins.taiko(rng, 1.1, 54), 1.6, 1.0)
    return reverb(out, rng, 0.3, 1.0)


def sfx_victory(rng):
    out = np.zeros(n(4.0))
    melody = [("D4", 0.0, 0.3), ("F#4", 0.3, 0.3), ("A4", 0.6, 0.3), ("D5", 0.9, 1.6)]
    for nm, at, dur in melody:
        place(out, ins.horn(note(nm), dur + 0.2), at, 0.8)
        place(out, ins.horn(note(nm) / 2, dur + 0.2), at, 0.35)
    place(out, ins.pad([note("D3"), note("F#3"), note("A3")], 2.6, rng, 1800), 0.9, 0.9)
    for at in (0.0, 0.6, 0.9):
        place(out, ins.taiko(rng, 0.9), at, 0.8)
    return reverb(out, rng, 0.35, 1.4)


def sfx_defeat(rng):
    out = np.zeros(n(4.5))
    for i, nm in enumerate(["D4", "C4", "Bb3", "A3"]):
        place(out, ins.horn(note(nm), 0.9 if i < 3 else 2.0), i * 0.55, 0.75)
    place(out, ins.pad([note("D3"), note("F3"), note("A3")], 3.0, rng, 900), 1.5, 0.9)
    place(out, ins.taiko(rng, 1.0, 50), 1.65, 1.0)
    return reverb(out, rng, 0.4, 1.6)


SFX_DEFS = {
    "shot": (sfx_shot, 4), "tower_shot": (lambda r: sfx_shot(r, distant=True), 3), "burst": (sfx_burst, 3),
    "spit": (sfx_spit, 3), "net": (sfx_net, 3), "impact_flesh": (sfx_impact_flesh, 4), "impact_wood": (sfx_impact_wood, 4),
    "raptor_call": (sfx_raptor_call, 4), "dilo_call": (sfx_dilo_call, 3), "trike_call": (sfx_trike_call, 3),
    "trex_roar": (sfx_trex_roar, 3), "bite_small": (sfx_bite, 4), "bite_large": (lambda r: sfx_bite(r, big=True), 3),
    "stomp": (sfx_stomp, 4), "dino_death": (sfx_dino_death, 3), "human_down": (sfx_human_down, 3),
    "hatch": (sfx_hatch, 3), "build": (sfx_build, 3), "gather_rock": (sfx_gather_rock, 4), "gather_wood": (sfx_gather_wood, 3),
    "collapse": (sfx_collapse, 3), "explosion": (sfx_explosion, 2), "fire_loop": (sfx_fire_loop, 1), "splash": (sfx_splash, 3),
    "ui_click": (sfx_ui_click, 3), "ui_confirm": (sfx_ui_confirm, 1), "objective": (sfx_objective, 1), "alert": (sfx_alert, 1),
    "wave_drums": (sfx_wave_drums, 1), "victory": (sfx_victory, 1), "defeat": (sfx_defeat, 1),
}

# Peak levels per sound (dBFS) set the mix balance between effects.
SFX_LEVELS = {"ui_click": -9, "stomp": -4, "shot": -3, "tower_shot": -6, "burst": -3, "gather_rock": -9, "gather_wood": -9,
              "build": -8, "splash": -10, "fire_loop": -10, "impact_flesh": -8, "impact_wood": -7, "spit": -6, "net": -7,
              "trex_roar": -1, "explosion": -1}


def gen_sfx():
    if os.path.isdir(SFX):
        shutil.rmtree(SFX)
    for name, (fn, count) in SFX_DEFS.items():
        for v in range(count):
            x = fn(rng_for(name, v))
            write(os.path.join(SFX, f"{name}_{v}.wav"), x, SFX_LEVELS.get(name, -2), trim=(name != "fire_loop"))
    print("sfx:", sum(c for _, c in SFX_DEFS.values()), "files")


# ===========================================================================
# Music
# ===========================================================================
CHORDS = {  # D minor family
    "Dm": ["D3", "F3", "A3"], "Bb": ["Bb2", "D3", "F3"], "F": ["F3", "A3", "C4"], "C": ["C3", "E3", "G3"],
    "Gm": ["G2", "Bb2", "D3"], "A": ["A2", "C#3", "E3"], "Am": ["A2", "C3", "E3"],
}


def crossfade_loop(x, loop_len, xf):
    """Seamless loop for unpitched beds: blend the overrun into the start."""
    out = x[:loop_len].copy()
    tail = x[loop_len:loop_len + xf]
    k = len(tail)
    w = np.linspace(0, 1, k)
    out[:k] = out[:k] * np.sqrt(w) + tail * np.sqrt(1 - w)
    return out


def render_track(bpm, bars, build, rng, rev_decay=1.4, rev_mix=0.28, tail_s=4.0):
    beat = 60.0 / bpm
    loop_s = bars * 4 * beat
    buf = np.zeros(n(loop_s + tail_s))
    build(buf, beat, rng)
    wet = convolve(buf, impulse(rev_decay * 3, rng, rev_decay, 3800, 0.02))[:len(buf) + n(rev_decay * 3)]
    dry = np.pad(buf, (0, len(wet) - len(buf)))
    full = dry * (1 - rev_mix) + wet * rev_mix * 1.3
    return loop_fold(full, n(loop_s))


def at(buf, sig, t, gain=1.0):
    i = n(t) if t > 0 else 0
    k = min(len(sig), len(buf) - i)
    if k > 0:
        buf[i:i + k] += sig[:k] * gain


def build_explore(buf, beat, rng):
    prog = ["Dm", "Bb", "F", "C"] * 4  # 16 bars
    arp = [0, 1, 2, 1, 0, 2, 1, 2]
    for bar, ch in enumerate(prog):
        t0 = bar * 4 * beat
        freqs = [note(x) for x in CHORDS[ch]]
        at(buf, ins.pad(freqs, 4 * beat + 1.0, rng, 1300), t0, 0.55)
        at(buf, ins.bass(freqs[0] / 2, 1.5 * beat), t0, 0.5)
        at(buf, ins.bass(freqs[0] / 2, 1.5 * beat), t0 + 2 * beat, 0.35)
        for k in range(8):  # marimba ostinato, eighth notes
            f = freqs[arp[k]] * (2 if k % 4 else 4)
            v = 0.5 + 0.2 * (k % 2 == 0) + rng.uniform(-0.05, 0.05)
            at(buf, ins.marimba(f, v, 0.7), t0 + k * beat / 2 + rng.uniform(0, 0.008), 0.55)
        for k in range(16):  # shaker sixteenths
            at(buf, ins.shaker(rng, 0.35 + 0.35 * (k % 4 == 2)), t0 + k * beat / 4, 0.4)
        if bar % 2 == 0:
            at(buf, ins.taiko(rng, 0.45), t0, 0.7)
    melody = [("A4", 0, 2), ("D5", 2, 2), ("C5", 4, 3), ("A4", 7, 1), ("Bb4", 8, 2), ("A4", 10, 1), ("G4", 11, 1),
              ("A4", 12, 4), ("F4", 16, 2), ("G4", 18, 1), ("A4", 19, 1), ("C5", 20, 3), ("A4", 23, 1), ("D5", 24, 6)]
    t_mel = 8 * 4 * beat  # horn enters in the second half
    for nm, start, dur in melody:
        at(buf, ins.horn(note(nm), dur * beat), t_mel + start * beat, 0.32)


def build_combat(buf, beat, rng):
    prog = ["Dm", "Dm", "Bb", "C", "Dm", "Gm", "A", "A"] * 3  # 24 bars
    for bar, ch in enumerate(prog):
        t0 = bar * 4 * beat
        freqs = [note(x) for x in CHORDS[ch]]
        at(buf, ins.pad([f / 2 for f in freqs], 4 * beat + 0.6, rng, 900), t0, 0.4)
        for k in range(8):  # driving string ostinato
            f = freqs[0] / 2 if k % 2 == 0 else freqs[0]
            at(buf, ins.strings_ostinato(f, beat / 2 * 0.9, 0.8 + 0.2 * (k % 4 == 0)), t0 + k * beat / 2, 0.5)
        for b, v, p in ((0, 1.0, 58), (1.5, 0.75, 64), (2, 0.9, 58), (3, 0.6, 70), (3.5, 0.6, 70)):
            at(buf, ins.taiko(rng, v, p), t0 + b * beat, 0.75)
        for k in range(16):
            at(buf, ins.shaker(rng, 0.4 + 0.4 * (k % 2 == 1)), t0 + k * beat / 4, 0.4)
        at(buf, ins.rim(rng, 0.6), t0 + 1 * beat, 0.5)
        at(buf, ins.rim(rng, 0.6), t0 + 3 * beat, 0.5)
        if bar % 4 == 3:  # tom fill
            for k in range(6):
                at(buf, ins.tom(rng, 0.6 + k * 0.06, 170 - k * 12), t0 + 2.5 * beat + k * beat / 4, 0.7)
    motif = [("D4", 0, 1.5), ("F4", 1.5, 0.5), ("A4", 2, 2), ("G4", 4, 1), ("F4", 5, 1), ("E4", 6, 2),
             ("D4", 8, 1.5), ("F4", 9.5, 0.5), ("A4", 10, 1), ("C5", 11, 1), ("A4", 12, 4)]
    for phrase_bar in (4, 12, 20):
        for nm, start, dur in motif:
            at(buf, ins.horn(note(nm), dur * beat), phrase_bar * 4 * beat + start * beat, 0.38)


def build_menu(buf, beat, rng):
    prog = ["Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "A"] * 1 + ["Dm", "F", "C", "Dm"]  # 12 bars
    for bar, ch in enumerate(prog):
        t0 = bar * 4 * beat
        freqs = [note(x) for x in CHORDS[ch]]
        at(buf, ins.pad(freqs + [freqs[0] * 2], 4 * beat + 1.5, rng, 1600), t0, 0.6)
        at(buf, ins.bass(freqs[0] / 2, 3 * beat), t0, 0.45)
        at(buf, ins.taiko(rng, 0.55, 56), t0, 0.6)
        at(buf, ins.taiko(rng, 0.3, 64), t0 + 2.5 * beat, 0.5)
        for k in (0, 3, 6):
            at(buf, ins.marimba(freqs[k % 3] * 4, 0.35, 1.0), t0 + k * beat / 2 + 2 * beat, 0.4)
    theme = [("D4", 0, 3), ("A4", 3, 1), ("F4", 4, 2), ("G4", 6, 1), ("A4", 7, 1), ("Bb4", 8, 3), ("A4", 11, 1),
             ("G4", 12, 2), ("F4", 14, 2), ("E4", 16, 2), ("F4", 18, 1), ("G4", 19, 1), ("A4", 20, 4), ("C5", 24, 2),
             ("D5", 26, 2), ("C5", 28, 2), ("A4", 30, 2), ("Bb4", 32, 2), ("A4", 34, 2), ("F#4", 36, 4), ("D4", 40, 6)]
    for nm, start, dur in theme:
        at(buf, ins.horn(note(nm), dur * beat), start * beat, 0.4)
        at(buf, ins.horn(note(nm) / 2, dur * beat), start * beat, 0.15)


def gen_music():
    rng = np.random.default_rng(7)
    tracks = {
        "explore": (96, 16, build_explore, 1.4, 0.28),
        "combat": (128, 24, build_combat, 1.0, 0.22),
        "menu_theme": (76, 12, build_menu, 2.0, 0.35),
    }
    for name, (bpm, bars, fn, rd, rm) in tracks.items():
        x = render_track(bpm, bars, fn, rng, rd, rm)
        x = softclip(x / (np.max(np.abs(x)) + 1e-9) * 1.1, 1.1)
        write(os.path.join(MUSIC, f"{name}.wav"), x, -1.5)
        print(f"music: {name} {len(x) / RATE:.1f}s")


# ===========================================================================
# Ambience
# ===========================================================================
def bird_call(rng):
    kind = rng.integers(0, 3)
    if kind == 0:  # rising whistle
        sec = rng.uniform(0.25, 0.5)
        t = t_axis(sec)
        f = rng.uniform(1800, 2600) * (1 + 0.5 * t / sec)
        x = osc("sine", f) * np.sin(np.pi * t / sec) ** 2
    elif kind == 1:  # trill
        sec = rng.uniform(0.4, 0.8)
        t = t_axis(sec)
        f = rng.uniform(3000, 4200) * (1 + 0.05 * np.sin(2 * np.pi * 40 * t))
        x = osc("sine", f) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(14, 22) * t)) * np.sin(np.pi * t / sec)
    else:  # two-note call
        sec = 0.5
        t = t_axis(sec)
        f = np.where(t < 0.22, rng.uniform(1500, 2000), rng.uniform(1100, 1400))
        x = osc("sine", f) * (np.sin(np.pi * np.clip(t / 0.22, 0, 1)) + np.sin(np.pi * np.clip((t - 0.25) / 0.25, 0, 1)))
    return x


def gen_ambience():
    L_s = 20.0
    L = n(L_s)
    xf = n(1.5)
    rng = np.random.default_rng(11)
    # --- jungle day ---
    bed = filt(noise(L_s + 1.5, rng, "pink"), "lp", 1400) * 0.25
    bed *= 0.7 + 0.3 * np.sin(2 * np.pi * t_axis(L_s + 1.5) / 7.0)
    insects = filt(noise(L_s + 1.5, rng), "bp", 5200, 2.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 17 * t_axis(L_s + 1.5))) * 0.06
    day = crossfade_loop(bed + insects, L, xf)
    birds = np.zeros(L)
    for k in range(16):
        call = bird_call(rng)
        distance = rng.uniform(0.3, 1.0)
        call = filt(call, "lp", 7000 - 4000 * (1 - distance)) * distance
        for rep in range(rng.integers(1, 3)):
            place(birds, call, (k + rng.uniform(0, 1)) * L_s / 16 + rep * 0.6, 0.35)
    day += loop_fold(reverb(birds, rng, 0.4, 0.9), L)
    write(os.path.join(AMB, "jungle_day.wav"), day, -6)
    # --- jungle night ---
    wind = filt(noise(L_s + 1.5, rng, "pink"), "lp", 700) * 0.3
    night = crossfade_loop(wind, L, xf)
    for c in range(4):  # crickets
        f = rng.uniform(4200, 5200)
        period = rng.uniform(0.45, 0.8)
        chirp = osc("sine", f, 0.02) * np.sin(np.pi * t_axis(0.02) / 0.02)
        pulse = np.zeros(n(0.12))
        for p in range(3):
            place(pulse, chirp, p * 0.035, 1.0)
        tt = rng.uniform(0, period)
        gain = rng.uniform(0.05, 0.12)
        while tt < L_s:
            place(night, pulse, tt, gain)
            tt += period
    for k in range(10):  # frogs
        sec = rng.uniform(0.2, 0.35)
        t = t_axis(sec)
        croak = osc("saw", rng.uniform(170, 260) * (1 - 0.15 * t / sec))
        croak = filt(croak, "bp", 600, 1.5) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 28 * t))) * np.sin(np.pi * t / sec)
        place(night, croak, (k + rng.uniform(0, 1)) * L_s / 10, rng.uniform(0.08, 0.2))
    write(os.path.join(AMB, "jungle_night.wav"), loop_fold(reverb(night, rng, 0.3, 1.2), L), -7)
    # --- surf --- (wave envelopes are periodic over the loop, so no seam)
    sec = L_s + 1.5
    t = t_axis(sec)
    offsets = [rng.uniform(0, 1) for _ in range(4)]

    def waves(delay):
        env = np.zeros(len(t))
        for k in range(-2, 7):
            c = k * 5.0 + offsets[k % 4] + delay
            env += np.exp(-((t - c) / 1.4) ** 2) + 0.6 * np.exp(-((t - c - 1.6) / 0.9) ** 2)
        return env

    roar = filt(noise(sec, rng, "pink"), "lp", 900) * (0.2 + waves(0.0))
    hiss = filt(noise(sec, rng), "hp", 3000) * waves(1.2) * 0.3
    write(os.path.join(AMB, "surf.wav"), crossfade_loop(roar + hiss, L, xf), -7)
    print("ambience: 3 loops")


def main():
    groups = sys.argv[1:] or ["sfx", "music", "ambience"]
    if "sfx" in groups:
        gen_sfx()
    if "music" in groups:
        gen_music()
    if "ambience" in groups:
        gen_ambience()


if __name__ == "__main__":
    main()
