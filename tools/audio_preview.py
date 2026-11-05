#!/usr/bin/env python3
"""Waveform + spectrogram sheet for generated audio (for visual review).

    python3 tools/audio_preview.py out.png assets/sfx/trex_roar_0.wav ...
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiokit import RATE, read  # noqa: E402

W, H_WAVE, H_SPEC = 900, 60, 140


def spectrogram(x, width, height, max_s=None):
    if max_s:
        x = x[:int(max_s * RATE)]
    win = 1024
    hop = max(1, (len(x) - win) // width) if len(x) > win else 1
    cols = []
    for i in range(width):
        s = i * hop
        seg = x[s:s + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * np.hanning(win)))
        cols.append(20 * np.log10(mag + 1e-6))
    spec = np.array(cols).T  # freq x time
    # log-frequency rows up to 11 kHz
    freqs = np.fft.rfftfreq(win, 1 / RATE)
    rows = np.geomspace(40, RATE / 2, height)[::-1]
    idx = np.clip(np.searchsorted(freqs, rows), 0, len(freqs) - 1)
    img = spec[idx]
    img = np.clip((img - (img.max() - 70)) / 70, 0, 1)
    rgb = np.stack([img ** 0.6, img ** 1.2, 0.35 + 0.65 * img ** 2.5], -1)
    return Image.fromarray((rgb * 255).astype(np.uint8))


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    sheet = Image.new("RGB", (W, len(paths) * (H_WAVE + H_SPEC + 18)), (12, 12, 16))
    d = ImageDraw.Draw(sheet)
    y = 0
    for p in paths:
        x = read(p)
        max_s = 12.0 if len(x) / RATE > 12 else None
        xs = x[:int(max_s * RATE)] if max_s else x
        d.text((4, y + 2), f"{os.path.basename(p)}  {len(x) / RATE:.2f}s", fill=(230, 220, 180))
        y += 16
        step = max(1, len(xs) // W)
        for i in range(W):
            seg = xs[i * step:(i + 1) * step]
            if len(seg) == 0:
                break
            a, b = seg.min(), seg.max()
            d.line([(i, y + H_WAVE / 2 - b * H_WAVE / 2), (i, y + H_WAVE / 2 - a * H_WAVE / 2)], fill=(120, 200, 140))
        y += H_WAVE
        sheet.paste(spectrogram(x, W, H_SPEC, max_s), (0, y))
        y += H_SPEC + 2
    sheet.save(out)


if __name__ == "__main__":
    main()
