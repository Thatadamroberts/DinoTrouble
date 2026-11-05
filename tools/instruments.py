"""Synth instruments for DinoTrouble's music and stingers."""
import numpy as np

from audiokit import RATE, adsr, decay, filt, n, noise, osc, softclip, t_axis


def taiko(rng, vel=1.0, pitch=62.0):
    """Big low drum: falling sine body + skin slap."""
    sec = 1.1
    t = t_axis(sec)
    f = pitch * (1 + 1.6 * np.exp(-t / 0.03))
    body = osc("sine", f) * decay(sec, 0.32)
    slap = filt(noise(0.06, rng), "bp", 900, 1.2) * decay(0.06, 0.012)
    out = np.zeros(n(sec))
    out[:len(slap)] += slap * 0.55
    return softclip(body + out, 1.4) * vel


def tom(rng, vel=1.0, pitch=140.0):
    sec = 0.5
    t = t_axis(sec)
    f = pitch * (1 + 0.6 * np.exp(-t / 0.02))
    body = osc("sine", f) * decay(sec, 0.14)
    hit = filt(noise(0.03, rng), "bp", 1800, 1.0) * decay(0.03, 0.008)
    body[:len(hit)] += hit * 0.4
    return body * vel


def shaker(rng, vel=1.0):
    sec = 0.09
    x = filt(noise(sec, rng), "hp", 6000, order=2) * adsr(sec, 0.012, 0.03, 0.3, 0.04)
    return x * vel * 1.4


def rim(rng, vel=1.0):
    sec = 0.06
    x = filt(noise(sec, rng), "bp", 2600, 3.0) * decay(sec, 0.01)
    x += osc("sine", 1700.0, sec) * decay(sec, 0.012) * 0.4
    return x * vel


def marimba(freq, vel=1.0, sec=0.9):
    """Wooden bar: fundamental + the characteristic 4x partial, quick decay."""
    t = t_axis(sec)
    x = osc("sine", freq, sec) * np.exp(-t / 0.35)
    x += 0.35 * osc("sine", freq * 3.93, sec) * np.exp(-t / 0.06)
    x += 0.12 * osc("sine", freq * 9.2, sec) * np.exp(-t / 0.02)
    x[:n(0.003)] *= np.linspace(0, 1, n(0.003))
    return x * vel


def pad(freqs, sec, rng, bright=1400.0, vel=1.0):
    """Warm detuned-saw chord with slow attack and release."""
    out = np.zeros(n(sec))
    for f in freqs:
        for det in (-0.006, 0.0, 0.0065):
            out += osc("saw", f * (1 + det), sec, phase0=rng.random())
    out = filt(out, "lp", bright, 0.8, order=2)
    return out * adsr(sec, sec * 0.3, 0.2, 0.85, sec * 0.35) * vel / (len(freqs) * 3)


def horn(freq, sec, vel=1.0, rng=None):
    """Brassy lead: saw through horn-like formants, swell attack, gentle vibrato."""
    t = t_axis(sec)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    x = osc("saw", freq * vib)
    x = filt(x, "lp", 2200, 0.7, order=2)
    x = x + 0.7 * filt(x, "bp", 950, 2.5) + 0.4 * filt(x, "bp", 2400, 3.0)
    env = adsr(sec, 0.09, 0.15, 0.82, 0.18)
    return softclip(x * env * 0.6, 1.2) * vel


def strings_ostinato(freq, sec, vel=1.0):
    """Short, urgent low string note (spiccato-ish)."""
    x = osc("saw", freq, sec) + osc("saw", freq * 1.004, sec)
    x = filt(x, "lp", 1100, 0.9, order=2)
    return x * adsr(sec, 0.01, 0.08, 0.55, 0.06) * vel * 0.5


def bass(freq, sec, vel=1.0):
    x = osc("tri", freq, sec) + 0.4 * osc("sine", freq / 2, sec)
    return x * adsr(sec, 0.005, 0.15, 0.6, 0.08) * vel


def chime(freqs, rng, spacing=0.09, vel=1.0):
    """Arpeggiated marimba chime (UI / objective)."""
    out = np.zeros(n(spacing * len(freqs) + 1.0))
    for i, f in enumerate(freqs):
        s = marimba(f, vel, 0.9)
        i0 = n(spacing * i)
        out[i0:i0 + len(s)] += s
    return out
