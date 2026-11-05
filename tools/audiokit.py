"""Small numpy synthesis kit used by gen_sounds.py.

Everything is mono float64 at RATE Hz. Filters work in the frequency domain
(FFT, or STFT for time-varying sweeps) so long music renders stay fast.
"""
import math
import os
import struct
import wave

import numpy as np

RATE = 22050


# ---------------------------------------------------------------------------
# basics
# ---------------------------------------------------------------------------
def n(sec):
    return max(1, int(round(sec * RATE)))


def t_axis(sec):
    return np.arange(n(sec)) / RATE


def silence(sec):
    return np.zeros(n(sec))


def note(name_or_midi):
    """'A4' / 'C#3' / midi int -> Hz."""
    if isinstance(name_or_midi, (int, float)):
        m = name_or_midi
    else:
        names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        s = name_or_midi
        m = names[s[0]]
        i = 1
        while i < len(s) and s[i] in "#b":
            m += 1 if s[i] == "#" else -1
            i += 1
        m += (int(s[i:]) + 1) * 12
    return 440.0 * 2 ** ((m - 69) / 12)


def phase_from_freq(freq):
    """Integrate an instantaneous-frequency array (Hz) into phase (cycles)."""
    return np.cumsum(freq) / RATE


def osc(kind, freq, sec=None, phase0=0.0):
    """freq: scalar or array. kind: sine, saw, square, tri."""
    if np.isscalar(freq):
        ph = phase0 + np.arange(n(sec)) * freq / RATE
    else:
        ph = phase0 + phase_from_freq(freq)
    if kind == "sine":
        return np.sin(2 * np.pi * ph)
    if kind == "saw":
        return 2.0 * (ph % 1.0) - 1.0
    if kind == "square":
        return np.where((ph % 1.0) < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4.0 * np.abs((ph % 1.0) - 0.5) - 1.0
    raise ValueError(kind)


def noise(sec, rng, color="white"):
    x = rng.standard_normal(n(sec))
    if color == "white":
        return x / 3.0
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    f[0] = 1.0
    if color == "pink":
        spec /= np.sqrt(f)
    elif color == "brown":
        spec /= f
    y = np.fft.irfft(spec, len(x))
    return y / (np.max(np.abs(y)) + 1e-9) * 0.8


# ---------------------------------------------------------------------------
# envelopes
# ---------------------------------------------------------------------------
def adsr(sec, a=0.01, d=0.1, s=0.7, r=0.2):
    total = n(sec)
    na, nd, nr = n(a), n(d), n(r)
    ns = max(0, total - na - nd - nr)
    env = np.concatenate([
        np.linspace(0, 1, na, endpoint=False),
        np.linspace(1, s, nd, endpoint=False),
        np.full(ns, s),
        np.linspace(s, 0, nr),
    ])
    return np.pad(env, (0, max(0, total - len(env))))[:total]


def decay(sec, tau, attack=0.002):
    t = t_axis(sec)
    env = np.exp(-t / tau)
    na = n(attack)
    env[:na] *= np.linspace(0, 1, na)
    return env


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin > 0:
        k = min(len(x), n(fin))
        x[:k] *= np.linspace(0, 1, k)
    if fout > 0:
        k = min(len(x), n(fout))
        x[-k:] *= np.linspace(1, 0, k)
    return x


# ---------------------------------------------------------------------------
# filters (frequency domain)
# ---------------------------------------------------------------------------
def _resp(kind, f, fc, q=0.707, gain_db=0.0):
    f = np.maximum(f, 1e-6)
    r = f / fc
    if kind == "lp":  # 2nd-order-ish magnitude
        return 1.0 / np.sqrt((1 - r ** 2) ** 2 + (r / q) ** 2)
    if kind == "hp":
        return r ** 2 / np.sqrt((1 - r ** 2) ** 2 + (r / q) ** 2)
    if kind == "bp":
        return (r / q) / np.sqrt((1 - r ** 2) ** 2 + (r / q) ** 2)
    if kind == "peak":
        g = 10 ** (gain_db / 20)
        bw = (r / q) / np.sqrt((1 - r ** 2) ** 2 + (r / q) ** 2)
        return 1 + (g - 1) * bw
    raise ValueError(kind)


def filt(x, kind, fc, q=0.707, gain_db=0.0, order=1):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    h = _resp(kind, f, fc, q, gain_db) ** order
    return np.fft.irfft(spec * h, len(x))


def sweep(x, kind, fc_curve, q=0.707, order=1, win=1024):
    """Time-varying filter. fc_curve: function t(0..1) -> cutoff Hz."""
    hop = win // 4
    w = np.hanning(win)
    pad = np.pad(x, (win, win))
    out = np.zeros_like(pad)
    norm = np.zeros_like(pad)
    f = np.fft.rfftfreq(win, 1 / RATE)
    total = len(x)
    for start in range(0, len(pad) - win, hop):
        seg = pad[start:start + win] * w
        center = (start + win / 2 - win) / max(1, total)
        fc = fc_curve(min(1.0, max(0.0, center)))
        h = _resp(kind, f, fc, q) ** order
        y = np.fft.irfft(np.fft.rfft(seg) * h, win) * w
        out[start:start + win] += y
        norm[start:start + win] += w * w
    out /= np.maximum(norm, 1e-6)
    return out[win:win + total]


def formants(x, freqs, q=8.0, gains=None):
    """Sum of band-passes (vocal-tract-like colouring)."""
    gains = gains or [1.0] * len(freqs)
    return sum(g * filt(x, "bp", fc, q) for fc, g in zip(freqs, gains))


# ---------------------------------------------------------------------------
# dynamics / space
# ---------------------------------------------------------------------------
def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def normalize(x, peak_db=-1.0):
    p = np.max(np.abs(x)) + 1e-12
    return x * (10 ** (peak_db / 20) / p)


def impulse(sec, rng, decay_s, damp_hz=4000.0, predelay=0.0):
    ir = noise(sec, rng) * np.exp(-t_axis(sec) / decay_s)
    ir = filt(ir, "lp", damp_hz)
    ir = np.concatenate([np.zeros(n(predelay)), ir]) if predelay else ir
    ir[0] = 0.0
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-12)


def convolve(x, ir):
    size = len(x) + len(ir) - 1
    nfft = 1 << (size - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:size]
    return y


def reverb(x, rng, mix=0.25, decay_s=0.6, damp_hz=4500.0, tail=True):
    ir = impulse(decay_s * 3.0, rng, decay_s, damp_hz, 0.012)
    wet = convolve(x, ir)
    dry = np.pad(x, (0, len(wet) - len(x)))
    y = dry * (1 - mix) + wet * mix * 1.2
    return y if tail else y[:len(x)]


def mix(*parts, length=None):
    """Sum signals of different lengths; each part is (signal, offset_s, gain) or signal."""
    items = []
    for p in parts:
        if isinstance(p, tuple):
            items.append(p)
        else:
            items.append((p, 0.0, 1.0))
    total = length if length is not None else max(n(o) + len(s) for s, o, g in items)
    out = np.zeros(total)
    for s, o, g in items:
        i = n(o) if o > 0 else 0
        if i >= total:
            continue
        k = min(len(s), total - i)
        out[i:i + k] += s[:k] * g
    return out


def place(buf, sig, at_s, gain=1.0):
    """Add sig into buf at time at_s (wrapping around for loops)."""
    i = int(round(at_s * RATE)) % len(buf)
    k = min(len(sig), len(buf))
    end = i + k
    if end <= len(buf):
        buf[i:end] += sig[:k] * gain
    else:
        first = len(buf) - i
        buf[i:] += sig[:first] * gain
        buf[:k - first] += sig[first:k] * gain


def loop_fold(x, loop_len):
    """Make a seamless loop: anything past loop_len (tails) wraps to the start."""
    out = x[:loop_len].copy()
    rest = x[loop_len:]
    while len(rest):
        k = min(len(rest), loop_len)
        out[:k] += rest[:k]
        rest = rest[k:]
    return out


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------
def trim_tail(x, floor_db=-54.0, fade_s=0.03):
    """Drop the inaudible end of a one-shot (long reverb tails) with a short fade."""
    thr = np.max(np.abs(x)) * 10 ** (floor_db / 20)
    idx = np.nonzero(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    end = min(len(x), idx[-1] + n(fade_s))
    y = x[:end].copy()
    k = min(len(y), n(fade_s))
    y[-k:] *= np.linspace(1, 0, k)
    return y


def write(path, x, peak_db=-1.0, trim=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    if trim:
        x = trim_tail(x)
    y = normalize(x, peak_db)
    data = np.clip(y * 32767, -32768, 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def read(path):
    with wave.open(path, "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return data.astype(np.float64) / 32768.0
