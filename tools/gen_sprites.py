#!/usr/bin/env python3
"""Generate all of DinoTrouble's pixel art.

Sprites are drawn by small parametric rigs (tools/units_art.py and
tools/world_art.py) using a pixel-art shading kit (tools/pixelkit.py):
volumes are lit by a single sun, quantised onto colour ramps with ordered
dithering, and given coloured outlines. Replace any PNG with hand-made art of
the same size and layout and the game will use it.

Run from the repo root (needs Pillow and numpy):
    python3 tools/gen_sprites.py
"""
import math
import os
import random
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import units_art  # noqa: E402
import world_art  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sprites")


def save(img, rel, scale=1):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)


def C(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + (c[3],)


def outline(img, factor=0.3):
    src = img.load()
    w, h = img.size
    out = img.copy()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] != 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] > 0:
                    dst[x, y] = shade(src[nx, ny], factor)[:3] + (255,)
                    break
    return out


def gen_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 61, 61], fill=C("2f5a22"))
    d.ellipse([6, 6, 57, 57], fill=C("4f8a2f"))
    d.ellipse([18, 10, 46, 54], fill=C("efe6c8"))
    d.ellipse([22, 14, 34, 30], fill=C("fffaf0"))
    for x, y in ((28, 40), (36, 26), (24, 32)):
        d.ellipse([x, y, x + 4, y + 3], fill=C("8a7a50"))
    d.line([(20, 30), (26, 34), (30, 28), (36, 34), (42, 30), (45, 32)], fill=C("3a2a1a"), width=2)
    save(outline(img, 0.4), "../../icon.png", scale=2)


def gen_menu_bg():
    W, H = 320, 180
    img = Image.new("RGBA", (W, H), C("000000"))
    d = ImageDraw.Draw(img)
    bands = ["2a1a3a", "3a1f44", "5a2848", "7a3448", "a04a44", "c8603a", "e07a3a", "f0a050"]
    for i, b in enumerate(bands):
        d.rectangle([0, i * 14, W, i * 14 + 14], fill=C(b))
    for i in range(9):  # sun
        y = 96 + i * 3
        d.ellipse([214, 70, 262, 118], fill=C("ffd27a"))
    for i in range(4):
        d.line([(210, 100 + i * 5), (266, 100 + i * 5)], fill=C("f0a050"), width=1 + i // 2)
    d.polygon([(0, 112), (40, 96), (80, 106), (130, 92), (170, 104), (320, 98), (320, 120), (0, 120)], fill=C("4a2a44"))
    d.polygon([(110, 118), (160, 48), (170, 46), (178, 50), (236, 118)], fill=C("2e1e30"))
    d.polygon([(160, 48), (170, 46), (178, 50), (172, 56), (166, 52)], fill=C("e85020"))
    for i, (sx, sy, r) in enumerate(((168, 38, 6), (174, 28, 8), (166, 16, 10), (178, 6, 12))):
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=C("5a4a5a"))
    d.rectangle([0, 118, W, H], fill=C("24405a"))
    rnd = random.Random(7)
    for _ in range(40):
        x, y = rnd.randrange(0, W), rnd.randrange(122, H)
        d.line([(x, y), (x + rnd.randint(3, 8), y)], fill=C("4a7aa0"))
    d.polygon([(0, 130), (30, 120), (70, 124), (120, 132), (150, 140), (150, H), (0, H)], fill=C("12301a"))
    d.polygon([(220, 150), (260, 136), (320, 132), (320, H), (210, H)], fill=C("12301a"))
    for px, py, s in ((20, 124, 1), (60, 122, -1), (100, 130, 1), (250, 136, -1), (290, 132, 1)):
        d.line([(px, py), (px + 3 * s, py - 22)], fill=C("0a1a0e"), width=2)
        for a in range(0, 360, 60):
            ex = px + 3 * s + math.cos(math.radians(a)) * 9
            ey = py - 22 + math.sin(math.radians(a)) * 4 + 3
            d.line([(px + 3 * s, py - 22), (ex, ey)], fill=C("0a1a0e"), width=2)
    for bx, by in ((60, 40), (80, 30), (250, 30)):  # flying reptiles
        d.line([(bx - 6, by - 2), (bx, by + 1), (bx + 6, by - 2)], fill=C("2a1a2a"))
    # big predator silhouette on the cliff
    fr = units_art.trex(9)
    sil = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    sil.paste(C("0a140c"), (0, 0), fr)
    sil = sil.crop(sil.getbbox()).resize((100, 64), Image.NEAREST)
    img.alpha_composite(sil, (24, 78))
    save(img, "ui/menu_bg.png", scale=4)


def gen_units():
    for name, fn in (("raptor", units_art.raptor), ("dilophosaurus", units_art.dilophosaurus),
                     ("triceratops", units_art.triceratops), ("trex", units_art.trex), ("jeep", units_art.jeep)):
        save(units_art.make_sheet(fn), f"units/{name}.png")
    for name, look in units_art.LOOKS.items():
        save(units_art.make_sheet(units_art.human, look), f"units/{name}.png")


def gen_world():
    save(world_art.ranger_station(), "buildings/ranger_station.png")
    save(world_art.hatchery(), "buildings/hatchery.png")
    save(world_art.watchtower(), "buildings/watchtower.png")
    save(world_art.watchtower(dark=True), "buildings/poacher_tower.png")
    save(world_art.supply_depot(), "buildings/supply_depot.png")
    save(world_art.poacher_camp(), "buildings/poacher_camp.png")
    save(world_art.amber(), "resources/amber.png")
    save(world_art.crates(), "resources/crates.png")
    for v in range(3):
        save(world_art.tree(10 + v), f"decor/tree_{v}.png")
        save(world_art.tuft(30 + v), f"decor/tuft_{v}.png")
    for v in range(2):
        save(world_art.palm(20 + v), f"decor/palm_{v}.png")
        save(world_art.bush(40 + v), f"decor/bush_{v}.png")
        save(world_art.boulder(50 + v), f"decor/boulder_{v}.png")
    for v in range(4):
        save(world_art.flowers(v), f"decor/flowers_{v}.png")
    textures, noise = world_art.ground_textures()
    for name, img in textures.items():
        save(img, f"terrain/{name}.png")
    save(noise, "terrain/noise.png")


def main():
    old_tiles = os.path.join(OUT, "tiles")
    if os.path.isdir(old_tiles):
        shutil.rmtree(old_tiles)
    gen_units()
    gen_world()
    gen_icon()
    gen_menu_bg()
    print("sprites written to", OUT)


if __name__ == "__main__":
    main()
