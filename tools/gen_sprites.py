#!/usr/bin/env python3
"""Generate DinoTrouble's placeholder isometric pixel art.

Everything is drawn at half resolution, outlined, then upscaled 2x with
nearest-neighbour sampling for a chunky retro look. Swap any PNG in
assets/sprites for hand-made art of the same size and the game picks it up.

Run from the repo root:
    python3 tools/gen_sprites.py
"""
import math
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sprites")
SCALE = 2
FRAMES = 7  # 0 idle, 1-4 walk, 5-6 attack


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def save(img, rel, scale=SCALE):
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
    """Add a 1px dark outline around opaque pixels (coloured from the neighbour)."""
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


def sheet(draw_fn, w, h, **kw):
    """Build a horizontal sprite sheet of FRAMES frames."""
    img = Image.new("RGBA", (w * FRAMES, h), (0, 0, 0, 0))
    for f in range(FRAMES):
        fr = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(fr), f, w, h, **kw)
        img.paste(outline(fr), (f * w, 0))
    return img


def walk(frame):
    """(front foot dx, back foot dx, body bob) for the walk cycle."""
    if 1 <= frame <= 4:
        p = frame - 1
        fx = [-2, 0, 2, 0][p]
        return fx, -fx, [0, -1, 0, -1][p]
    return 0, 0, 0


# --------------------------------------------------------------------------
# terrain tiles (32x16 half-res -> 64x32)
# --------------------------------------------------------------------------
TW, TH = 32, 16


def diamond_pixels():
    pts = []
    for y in range(TH):
        r = y if y < TH // 2 else TH - 1 - y
        half = 2 * (r + 1) + 1  # +1 overlaps neighbours slightly to hide seams
        for x in range(TW // 2 - half, TW // 2 + half):
            if 0 <= x < TW:
                pts.append((x, y))
    return pts


DIAMOND = diamond_pixels()


def tile(base, specks, prob, seed, feature=None):
    rnd = random.Random(seed)
    img = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    px = img.load()
    for x, y in DIAMOND:
        px[x, y] = rnd.choice(specks) if rnd.random() < prob else base
    if feature:
        feature(px, rnd)
    return img


def inside(x, y):
    return (x, y) in DIAMOND_SET


DIAMOND_SET = set(DIAMOND)


def tufts(col):
    def f(px, rnd):
        for _ in range(5):
            x, y = rnd.randrange(4, 28), rnd.randrange(3, 13)
            if inside(x, y) and inside(x, y - 1):
                px[x, y] = col
                px[x, y - 1] = col
    return f


def waves(col):
    def f(px, rnd):
        for _ in range(3):
            x, y = rnd.randrange(6, 24), rnd.randrange(4, 12)
            for i in range(3):
                if inside(x + i, y):
                    px[x + i, y] = col
    return f


def pebbles(col):
    def f(px, rnd):
        for _ in range(4):
            x, y = rnd.randrange(4, 28), rnd.randrange(3, 13)
            if inside(x, y):
                px[x, y] = col
    return f


def gen_tiles():
    specs = {
        "water": (C("2a5f8f"), [C("2f6a9c"), C("245580")], 0.25, waves(C("6fa6c9"))),
        "sand": (C("d8c27a"), [C("cdb46a"), C("e3d08c")], 0.3, pebbles(C("b89c58"))),
        "grass": (C("4f8a2f"), [C("5f9c37"), C("437a28"), C("6aa63e")], 0.3, tufts(C("7ab846"))),
        "jungle": (C("3a6626"), [C("2f5720"), C("47752c"), C("5a4a2a")], 0.35, tufts(C("2a4a1a"))),
        "dirt": (C("8a6a3e"), [C("7a5c34"), C("9a7a4a")], 0.35, pebbles(C("6a6a60"))),
        "rock": (C("7a7a6e"), [C("6a6a60"), C("8a8a7e")], 0.35, pebbles(C("9c9c90"))),
    }
    for name, (base, sp, prob, feat) in specs.items():
        for v in range(3):
            save(tile(base, sp, prob, sum(map(ord, name)) * 31 + v * 101, feat), f"tiles/{name}_{v}.png")


# --------------------------------------------------------------------------
# decoration
# --------------------------------------------------------------------------
def gen_decor():
    # Jungle tree
    for v in range(3):
        rnd = random.Random(100 + v)
        img = Image.new("RGBA", (28, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.polygon([(11, 38), (13, 22), (15, 22), (17, 38)], fill=C("6a4628"))
        d.line([(14, 24), (14, 37)], fill=C("7f5632"))
        greens = [C("1f4a1a"), C("2c5e22"), C("3b7a2c"), C("4f9136")]
        for layer, col in enumerate(greens):
            for _ in range(4):
                r = rnd.randint(5, 8) - layer
                cx = rnd.randint(7, 21)
                cy = rnd.randint(7, 18) - layer
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        for _ in range(8):
            x, y = rnd.randint(6, 22), rnd.randint(3, 16)
            if img.getpixel((x, y))[3]:
                img.putpixel((x, y), C("6aae48"))
        save(outline(img, 0.4), f"decor/tree_{v}.png")

    # Palm
    for v in range(2):
        rnd = random.Random(200 + v)
        img = Image.new("RGBA", (28, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bend = 3 if v == 0 else -3
        pts = [(14 + int(bend * math.sin(t / 10 * math.pi / 2)), 38 - t * 2.4) for t in range(11)]
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=C("8a6a3e") if i % 2 else C("745832"), width=3)
        top = pts[-1]
        for ang in range(0, 360, 50):
            a = math.radians(ang + rnd.randint(-10, 10))
            ex = top[0] + math.cos(a) * 11
            ey = top[1] + math.sin(a) * 5 + 4
            mx = top[0] + math.cos(a) * 6
            my = top[1] + math.sin(a) * 3 - 2
            d.line([top, (mx, my), (ex, ey)], fill=C("3f8a2e"), width=2)
        d.ellipse([top[0] - 2, top[1], top[0] + 1, top[1] + 3], fill=C("6a4a20"))
        save(outline(img, 0.4), f"decor/palm_{v}.png")

    # Fern bush (walkable decoration)
    for v in range(2):
        rnd = random.Random(300 + v)
        img = Image.new("RGBA", (16, 10), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for _ in range(6):
            x = rnd.randint(2, 13)
            d.line([(8, 9), (x, rnd.randint(1, 5))], fill=rnd.choice([C("3b7a2c"), C("4f9136"), C("2c5e22")]))
        save(outline(img, 0.45), f"decor/bush_{v}.png")

    # Boulder
    for v in range(2):
        rnd = random.Random(400 + v)
        img = Image.new("RGBA", (18, 13), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([1, 2, 16, 12], fill=C("6e6c64"))
        d.ellipse([3, 2, 12, 8], fill=C("8a887e"))
        d.point([(5, 4), (6, 4), (9, 5)], fill=C("a8a69a"))
        save(outline(img, 0.4), f"decor/boulder_{v}.png")


# --------------------------------------------------------------------------
# humans & vehicles
# --------------------------------------------------------------------------
SKIN = C("e0a878")


def human(d, f, w, h, hat, shirt, pants, gear):
    lf, rf, bob = walk(f)
    cx = 6
    # legs
    d.line([(cx + 1, 15 + bob), (cx + 1 + rf, 20)], fill=shade(pants, 0.75), width=2)
    d.line([(cx - 1, 15 + bob), (cx - 1 + lf, 20)], fill=pants, width=2)
    d.point([(cx - 1 + lf, 21), (cx + lf, 21), (cx + 1 + rf, 21), (cx + 2 + rf, 21)], fill=C("2a2018"))
    # torso + head
    d.rectangle([cx - 2, 9 + bob, cx + 2, 15 + bob], fill=shirt)
    d.line([(cx - 2, 9 + bob), (cx - 2, 15 + bob)], fill=shade(shirt, 0.8))
    d.ellipse([cx - 2, 4 + bob, cx + 2, 8 + bob], fill=SKIN)
    d.point([(cx + 1, 6 + bob)], fill=C("2a2018"))
    gear(d, f, cx, bob)
    hat(d, cx, bob)


def hat_brim(col):
    def f(d, cx, bob):
        d.rectangle([cx - 3, 4 + bob, cx + 3, 4 + bob], fill=shade(col, 0.85))
        d.rectangle([cx - 2, 2 + bob, cx + 2, 3 + bob], fill=col)
    return f


def hat_hard(d, cx, bob):
    d.pieslice([cx - 3, 2 + bob, cx + 3, 7 + bob], 180, 360, fill=C("e8c02a"))
    d.point([(cx + 3, 4 + bob)], fill=C("e8c02a"))


def hat_cap(d, cx, bob):
    d.rectangle([cx - 2, 3 + bob, cx + 2, 4 + bob], fill=C("2a2a2a"))
    d.rectangle([cx + 2, 4 + bob, cx + 4, 4 + bob], fill=C("2a2a2a"))


def gear_rifle(stock):
    def f(d, fr, cx, bob):
        if fr >= 5:
            d.line([(cx - 1, 10 + bob), (cx + 8, 10 + bob)], fill=C("4a4a4a"))
            d.line([(cx - 1, 11 + bob), (cx + 2, 11 + bob)], fill=stock)
            d.line([(cx + 1, 10 + bob), (cx + 4, 11 + bob)], fill=SKIN)
            if fr == 5:
                d.point([(cx + 9, 10 + bob), (cx + 10, 9 + bob), (cx + 10, 11 + bob), (cx + 11, 10 + bob)], fill=C("ffd84a"))
        else:
            d.line([(cx - 2, 14 + bob), (cx + 5, 8 + bob)], fill=C("4a4a4a"))
            d.line([(cx - 2, 14 + bob), (cx, 12 + bob)], fill=stock)
            d.line([(cx + 1, 10 + bob), (cx + 2, 12 + bob)], fill=SKIN)
    return f


def gear_wrench(d, fr, cx, bob):
    # toolbox / wrench
    if fr >= 5:
        y = 6 if fr == 5 else 11
        d.line([(cx + 1, 10 + bob), (cx + 4, y + bob)], fill=SKIN)
        d.line([(cx + 4, y + bob), (cx + 7, y - 2 + bob)], fill=C("b0b0b8"))
    else:
        d.line([(cx + 1, 10 + bob), (cx + 3, 13 + bob)], fill=SKIN)
        d.rectangle([cx + 2, 13 + bob, cx + 5, 15 + bob], fill=C("c0392b"))
    # hi-vis stripe
    d.line([(cx - 2, 12 + bob), (cx + 2, 12 + bob)], fill=C("f0e060"))


def gear_net(d, fr, cx, bob):
    if fr >= 5:
        d.line([(cx + 1, 10 + bob), (cx + 5, 8 + bob)], fill=SKIN)
        r = 3 if fr == 5 else 4
        d.ellipse([cx + 5 - r, 6 - r + bob, cx + 5 + r, 6 + r + bob], outline=C("d0d0c0"))
        d.line([(cx + 5 - r, 6 + bob), (cx + 5 + r, 6 + bob)], fill=C("d0d0c0"))
    else:
        d.ellipse([cx - 5, 9 + bob, cx - 1, 14 + bob], fill=C("8a8a78"))
        d.point([(cx - 4, 10 + bob), (cx - 2, 12 + bob)], fill=C("d0d0c0"))
        d.line([(cx + 1, 10 + bob), (cx + 2, 13 + bob)], fill=SKIN)
    d.line([(cx - 2, 9 + bob), (cx + 2, 9 + bob)], fill=C("c0392b"))  # bandana


def gen_humans():
    defs = {
        "ranger": (hat_brim(C("6b7b3a")), C("8a9a52"), C("5a4a32"), gear_rifle(C("8a5a32"))),
        "engineer": (hat_hard, C("d8742a"), C("3a4f7a"), gear_wrench),
        "hunter": (hat_cap, C("8a2a22"), C("3a3a3a"), gear_rifle(C("3a2a1a"))),
        "trapper": (hat_brim(C("5a3a1e")), C("a07a48"), C("4a3a2a"), gear_net),
    }
    for name, (hat, shirt, pants, gear) in defs.items():
        save(sheet(human, 14, 23, hat=hat, shirt=shirt, pants=pants, gear=gear), f"units/{name}.png")


def jeep(d, f, w, h):
    _, _, bob = walk(f)
    bob = -bob if f else 0
    body, dark = C("6a2a24"), C("3a1a18")
    d.polygon([(2, 9 + bob), (6, 6 + bob), (20, 6 + bob), (23, 9 + bob), (29, 10 + bob), (29, 15 + bob), (2, 15 + bob)], fill=body)
    d.line([(2, 12 + bob), (29, 12 + bob)], fill=C("c8b060"))
    d.polygon([(14, 6 + bob), (17, 1 + bob), (19, 1 + bob), (18, 6 + bob)], fill=C("8ab0c0"))
    d.line([(6, 6 + bob), (8, 1 + bob), (13, 1 + bob)], fill=dark)  # roll bar
    # mounted gun
    d.rectangle([8, 3 + bob, 10, 6 + bob], fill=C("3a3a3a"))
    if f >= 5:
        d.line([(10, 3 + bob), (17, 3 + bob)], fill=C("3a3a3a"))
        if f == 5:
            d.point([(18, 3 + bob), (19, 2 + bob), (19, 4 + bob)], fill=C("ffd84a"))
    else:
        d.line([(10, 3 + bob), (15, 2 + bob)], fill=C("3a3a3a"))
    for wx in (7, 23):
        d.ellipse([wx - 4, 12, wx + 3, 19], fill=C("1e1e1e"))
        d.ellipse([wx - 2, 14, wx + 1, 17], fill=C("8a8a8a"))
        a = (f % 4) * math.pi / 4
        d.line([(wx - 0.5 + math.cos(a) * 2, 15.5 + math.sin(a) * 2), (wx - 0.5 - math.cos(a) * 2, 15.5 - math.sin(a) * 2)], fill=C("3a3a3a"))


# --------------------------------------------------------------------------
# dinosaurs (side view, facing right)
# --------------------------------------------------------------------------
def leg(d, hip, foot, col, width=2):
    d.line([hip, foot], fill=col, width=width)
    d.line([foot, (foot[0] + 2, foot[1])], fill=shade(col, 0.7))


def raptor(d, f, w, h):
    lf, rf, bob = walk(f)
    body, belly, stripe = C("b08a4a"), C("d8c08a"), C("6a4a2a")
    wag = [0, 1, 0, -1][(f - 1) % 4] if 1 <= f <= 4 else 0
    lunge = 2 if f == 6 else 0
    leg(d, (13, 11 + bob), (12 + rf, 17), shade(body, 0.7))
    d.polygon([(10, 7 + bob), (0, 6 + bob + wag), (1, 8 + bob + wag), (10, 11 + bob)], fill=body)
    d.ellipse([8, 6 + bob, 19, 12 + bob], fill=body)
    d.ellipse([10, 9 + bob, 18, 12 + bob], fill=belly)
    for sx in (10, 12, 14, 16):
        d.line([(sx, 6 + bob), (sx - 1, 8 + bob)], fill=stripe)
    d.polygon([(16, 8 + bob), (19 + lunge, 3 + bob), (21 + lunge, 4 + bob), (19, 9 + bob)], fill=body)
    hx = 19 + lunge
    d.ellipse([hx, 1 + bob, hx + 6, 5 + bob], fill=body)
    d.rectangle([hx + 4, 3 + bob, hx + 8, 4 + bob], fill=body)
    if f == 5:
        d.polygon([(hx + 4, 5 + bob), (hx + 8, 7 + bob), (hx + 3, 6 + bob)], fill=body)
        d.point([(hx + 6, 5 + bob)], fill=C("ffffff"))
    d.point([(hx + 3, 2 + bob)], fill=C("1a1a1a"))
    d.line([(18, 9 + bob), (21, 11 + bob)], fill=shade(body, 0.8))
    leg(d, (15, 11 + bob), (15 + lf, 17), body)
    d.point([(16 + lf, 16)], fill=C("eeeeee"))  # sickle claw


def dilophosaurus(d, f, w, h):
    lf, rf, bob = walk(f)
    body, belly, stripe, crest = C("6f9a3a"), C("d8d07a"), C("3a5a22"), C("c8402a")
    wag = [0, 1, 0, -1][(f - 1) % 4] if 1 <= f <= 4 else 0
    leg(d, (13, 14 + bob), (12 + rf, 21), shade(body, 0.7))
    d.polygon([(10, 10 + bob), (0, 9 + bob + wag), (1, 11 + bob + wag), (10, 14 + bob)], fill=body)
    d.ellipse([8, 9 + bob, 20, 16 + bob], fill=body)
    d.ellipse([10, 12 + bob, 19, 16 + bob], fill=belly)
    for sx in (11, 14, 17):
        d.point([(sx, 10 + bob), (sx, 11 + bob)], fill=stripe)
    d.polygon([(17, 11 + bob), (21, 4 + bob), (23, 5 + bob), (20, 12 + bob)], fill=body)
    if f >= 5:  # frill flares when spitting
        d.pieslice([16, -1 + bob, 28, 11 + bob], 180, 360, fill=C("e8b030"))
        d.arc([16, -1 + bob, 28, 11 + bob], 180, 360, fill=crest)
    d.ellipse([21, 3 + bob, 27, 7 + bob], fill=body)
    d.rectangle([25, 5 + bob, 29, 6 + bob], fill=body)
    d.line([(22, 3 + bob), (25, 0 + bob)], fill=crest)
    d.line([(23, 3 + bob), (26, 1 + bob)], fill=crest)
    d.point([(24, 4 + bob)], fill=C("1a1a1a"))
    if f == 6:
        d.point([(30, 5 + bob), (31, 5 + bob), (30, 4 + bob)], fill=C("8aff4a"))
    leg(d, (15, 14 + bob), (15 + lf, 21), body)


def triceratops(d, f, w, h):
    lf, rf, bob = walk(f)
    body, belly, frill, horn = C("7a8a5a"), C("a8b080"), C("c8a050"), C("eee2c0")
    dip = 2 if f >= 5 else 0
    push = 2 if f == 6 else 0
    for x, dx, col in ((10, rf, shade(body, 0.7)), (24, lf, shade(body, 0.7))):
        d.rectangle([x + dx, 16, x + dx + 2, 22], fill=col)
    d.polygon([(6, 11 + bob), (0, 14 + bob), (6, 16 + bob)], fill=body)
    d.ellipse([4, 6 + bob, 29, 20 + bob], fill=body)
    d.ellipse([8, 13 + bob, 27, 20 + bob], fill=belly)
    for sx in range(9, 26, 4):
        d.point([(sx, 7 + bob), (sx + 1, 7 + bob)], fill=shade(body, 0.75))
    for x, dx in ((7, lf), (21, rf)):
        d.rectangle([x + dx, 16, x + dx + 3, 23], fill=body)
    hx = 25 + push
    hy = 3 + bob + dip
    d.ellipse([hx - 2, hy, hx + 9, hy + 13], fill=frill)
    d.arc([hx - 2, hy, hx + 9, hy + 13], 120, 300, fill=C("8a5a2a"))
    d.polygon([(hx + 3, hy + 6), (hx + 10, hy + 7), (hx + 11, hy + 11), (hx + 4, hy + 12)], fill=body)
    d.line([(hx + 6, hy + 6), (hx + 11, hy + 1)], fill=horn)
    d.line([(hx + 7, hy + 7), (hx + 11, hy + 3)], fill=horn)
    d.point([(hx + 10, hy + 8), (hx + 11, hy + 7)], fill=horn)
    d.point([(hx + 6, hy + 8)], fill=C("1a1a1a"))


def trex(d, f, w, h):
    lf, rf, bob = walk(f)
    body, belly, stripe = C("5a6a3a"), C("a8a070"), C("3a4626")
    wag = [0, 1, 0, -1][(f - 1) % 4] if 1 <= f <= 4 else 0
    lunge = 3 if f == 6 else (1 if f == 5 else 0)
    leg(d, (18, 22 + bob), (16 + rf, 34), shade(body, 0.7), 4)
    d.polygon([(14, 14 + bob), (0, 15 + bob + wag), (1, 18 + bob + wag), (14, 22 + bob)], fill=body)
    d.ellipse([11, 11 + bob, 31, 26 + bob], fill=body)
    d.ellipse([15, 18 + bob, 30, 26 + bob], fill=belly)
    for sx in (14, 18, 22, 26):
        d.line([(sx, 12 + bob), (sx - 1, 16 + bob)], fill=stripe)
    d.polygon([(25, 15 + bob), (29 + lunge, 7 + bob), (33 + lunge, 8 + bob), (30, 18 + bob)], fill=body)
    hx = 28 + lunge
    hy = 2 + bob + (1 if f >= 5 else 0)
    d.polygon([(hx, hy + 2), (hx + 4, hy), (hx + 14, hy + 2), (hx + 15, hy + 7), (hx + 3, hy + 9)], fill=body)
    jaw = 5 if f == 5 else (2 if f == 6 else 0)
    d.polygon([(hx + 3, hy + 8), (hx + 14, hy + 7 + jaw), (hx + 13, hy + 10 + jaw), (hx + 4, hy + 11)], fill=shade(body, 0.85))
    if jaw:
        for tx in range(hx + 6, hx + 14, 2):
            d.point([(tx, hy + 7), (tx, hy + 7 + jaw)], fill=C("f0f0e0"))
        d.polygon([(hx + 5, hy + 8), (hx + 13, hy + 7), (hx + 13, hy + 7 + jaw)], fill=C("8a2a2a"))
    d.point([(hx + 6, hy + 3), (hx + 7, hy + 3)], fill=C("e8c020"))
    d.line([(28, 19 + bob), (31, 21 + bob)], fill=shade(body, 0.8))  # tiny arm
    leg(d, (21, 22 + bob), (21 + lf, 34), body, 4)


# --------------------------------------------------------------------------
# buildings
# --------------------------------------------------------------------------
def iso_box(d, cx, cy, hw, hh, height, top, left, right):
    L, B, R, T = (cx - hw, cy), (cx, cy + hh), (cx + hw, cy), (cx, cy - hh)
    up = lambda p: (p[0], p[1] - height)
    d.polygon([L, B, up(B), up(L)], fill=left)
    d.polygon([B, R, up(R), up(B)], fill=right)
    d.polygon([up(T), up(R), up(B), up(L)], fill=top)
    return up(L), up(B), up(R), up(T)


def canvas(size, extra):
    w, dh = size * 32, size * 16
    img = Image.new("RGBA", (w, dh + extra), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), w // 2, dh + extra - dh // 2


def pad(d, cx, cy, size, col, inset=0):
    hw, hh = size * 16 - inset * 2, size * 8 - inset
    d.polygon([(cx - hw, cy), (cx, cy + hh), (cx + hw, cy), (cx, cy - hh)], fill=col)


def mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def roof(d, L, B, R, T, rise, front, back, gable):
    A = (mid(L, T)[0], mid(L, T)[1] - rise)
    Cc = (mid(B, R)[0], mid(B, R)[1] - rise)
    d.polygon([A, Cc, R, T], fill=back)
    d.polygon([L, B, Cc, A], fill=front)
    d.polygon([B, R, Cc], fill=gable)
    d.line([A, Cc], fill=shade(front, 1.25))


def ranger_station():
    img, d, cx, cy = canvas(3, 44)
    pad(d, cx, cy, 3, C("8a8670"))
    L, B, R, T = iso_box(d, cx, cy, 38, 19, 16, C("7a5030"), C("8a5a32"), C("6a4424"))
    for i in range(3, 16, 4):  # plank lines
        d.line([(cx - 38, cy - i), (cx, cy + 19 - i)], fill=C("6a4424"))
        d.line([(cx, cy + 19 - i), (cx + 38, cy - i)], fill=C("5a3a1e"))
    d.polygon([(cx - 22, cy + 8), (cx - 16, cy + 11), (cx - 16, cy + 1), (cx - 22, cy - 2)], fill=C("3a2614"))
    for wx in (cx - 32, cx + 10, cx + 24):
        d.rectangle([wx, cy + (2 if wx < cx else 4), wx + 4, cy + (6 if wx < cx else 8)], fill=C("e8d890"))
    roof(d, L, B, R, T, 14, C("3f6a2e"), C("4f7f38"), C("6a4424"))
    # flag
    d.line([(cx - 4, cy - 30), (cx - 4, cy - 52)], fill=C("cccccc"))
    d.polygon([(cx - 3, cy - 52), (cx + 7, cy - 49), (cx - 3, cy - 46)], fill=C("3aa04a"))
    return img


def hatchery():
    img, d, cx, cy = canvas(3, 40)
    pad(d, cx, cy, 3, C("9a9a90"))
    for i in range(-40, 41, 8):
        d.point([(cx + i, cy + 19 - abs(i) // 2)], fill=C("e8c020"))
    iso_box(d, cx, cy, 38, 19, 6, C("b0b0a8"), C("8a8a84"), C("707068"))
    # eggs inside
    for ex, ey in ((cx - 14, cy - 12), (cx - 2, cy - 15), (cx + 10, cy - 12), (cx + 2, cy - 8), (cx - 8, cy - 7)):
        d.ellipse([ex - 3, ey - 4, ex + 3, ey + 4], fill=C("efe6c8"))
        d.point([(ex - 1, ey - 1), (ex + 1, ey + 2)], fill=C("8a7a50"))
    dome = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(dome)
    dd.chord([cx - 30, cy - 40, cx + 30, cy + 4], 180, 360, fill=C("8ad0d8", 150))
    dd.arc([cx - 30, cy - 40, cx + 30, cy + 4], 180, 360, fill=C("d8e8e8"))
    dd.arc([cx - 22, cy - 36, cx + 6, cy - 8], 200, 260, fill=C("ffffff", 220))
    for rx in (-15, 0, 15):
        dd.line([(cx + rx, cy - 18 - (24 - abs(rx)) + (abs(rx) // 2)), (cx + rx * 1.6, cy - 18)], fill=C("c0d0d0", 200))
    img = Image.alpha_composite(img, dome)
    d = ImageDraw.Draw(img)
    d.rectangle([cx + 32, cy - 22, cx + 36, cy - 4], fill=C("707068"))  # vent
    d.rectangle([cx + 31, cy - 24, cx + 37, cy - 22], fill=C("505048"))
    return img


def watchtower(dark=False):
    img, d, cx, cy = canvas(2, 58)
    pad(d, cx, cy, 2, C("7a6448") if not dark else C("5a5048"), 1)
    wood = C("7a5030") if not dark else C("4a4a4a")
    for px, py in ((cx - 18, cy), (cx, cy + 9), (cx + 18, cy), (cx, cy - 9)):
        d.line([(px, py), (px * 0.85 + cx * 0.15, py - 36)], fill=wood, width=2)
    d.line([(cx - 18, cy - 4), (cx, cy - 27)], fill=shade(wood, 0.8))
    d.line([(cx + 18, cy - 4), (cx, cy - 27)], fill=shade(wood, 0.8))
    L, B, R, T = iso_box(d, cx, cy - 36, 22, 11, 3, shade(wood, 1.2), wood, shade(wood, 0.75))
    hut = C("6a7a3a") if not dark else C("8a2a24")
    L, B, R, T = iso_box(d, cx, cy - 40, 12, 6, 9, hut, shade(hut, 0.9), shade(hut, 0.7))
    d.polygon([L, B, R, (cx, cy - 64)], fill=C("3f6a2e") if not dark else C("3a3a3a"))
    d.polygon([B, R, (cx, cy - 64)], fill=C("2f5a22") if not dark else C("2a2a2a"))
    d.ellipse([cx + 8, cy - 47, cx + 11, cy - 44], fill=C("fff080") if not dark else C("ff3030"))
    return img


def supply_depot():
    img, d, cx, cy = canvas(2, 28)
    pad(d, cx, cy, 2, C("8a7a5a"), 1)
    L, B, R, T = iso_box(d, cx - 2, cy - 2, 20, 10, 11, C("8a6a40"), C("8a6a40"), C("6a4a2a"))
    roof(d, L, B, R, T, 8, C("2f6a6a"), C("3a7a7a"), C("6a4a2a"))
    for bx, by in ((cx + 10, cy + 6), (cx + 16, cy + 3), (cx + 13, cy)):
        iso_box(d, bx, by, 4, 2, 4, C("c89a5a"), C("a07a40"), C("805a30"))
    return img


def poacher_camp():
    img, d, cx, cy = canvas(3, 40)
    pad(d, cx, cy, 3, C("7a6448"))
    # fence posts
    for i in range(-44, 45, 8):
        y = cy + 22 - abs(i) // 2
        d.line([(cx + i, y), (cx + i, y - 4)], fill=C("4a3420"))

    def tent(tx, ty, w, hgt, col):
        d.polygon([(tx - w, ty), (tx, ty - hgt), (tx + w, ty)], fill=col)
        d.polygon([(tx, ty - hgt), (tx + w, ty), (tx + w + 6, ty - 3), (tx + 6, ty - hgt - 3)], fill=shade(col, 0.75))
        d.polygon([(tx - 2, ty), (tx, ty - hgt // 2), (tx + 2, ty)], fill=C("2a2018"))

    tent(cx - 4, cy - 6, 14, 18, C("6a6a3a"))
    tent(cx - 26, cy + 2, 9, 11, C("b8a070"))
    tent(cx + 18, cy + 4, 9, 11, C("b8a070"))
    for bx, by in ((cx - 10, cy + 12), (cx - 4, cy + 14)):
        iso_box(d, bx, by, 4, 2, 4, C("c89a5a"), C("a07a40"), C("805a30"))
    d.line([(cx + 30, cy - 4), (cx + 30, cy - 34)], fill=C("cccccc"))
    d.polygon([(cx + 31, cy - 34), (cx + 42, cy - 31), (cx + 31, cy - 27)], fill=C("c0302a"))
    d.ellipse([cx + 4, cy + 8, cx + 10, cy + 11], fill=C("4a3420"))
    d.point([(cx + 6, cy + 7), (cx + 7, cy + 6), (cx + 8, cy + 7)], fill=C("ff9030"))
    return img


def resource_amber():
    img = Image.new("RGBA", (24, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 10, 22, 19], fill=C("6e6c64"))
    d.ellipse([4, 10, 16, 15], fill=C("8a887e"))
    for x0, top, x1 in ((5, 5, 11), (10, 1, 17), (15, 7, 21)):
        xm = (x0 + x1) // 2
        d.polygon([(x0, 15), (x0, top + 3), (xm, top), (xm, 15)], fill=C("f0a838"))
        d.polygon([(xm, 15), (xm, top), (x1, top + 3), (x1, 15)], fill=C("b8661a"))
        d.line([(x0 + 1, top + 4), (x0 + 1, 13)], fill=C("ffe090"))
    d.point([(13, 6), (14, 8)], fill=C("fff0a0"))
    return outline(img, 0.35)


def resource_crates():
    img = Image.new("RGBA", (26, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    iso_box(d, 8, 14, 6, 3, 6, C("c89a5a"), C("a07a40"), C("805a30"))
    iso_box(d, 17, 15, 6, 3, 6, C("c89a5a"), C("a07a40"), C("805a30"))
    iso_box(d, 12, 9, 6, 3, 6, C("d8aa6a"), C("a07a40"), C("805a30"))
    d.line([(12, 3), (12, 9)], fill=C("5a3a1e"))
    d.polygon([(19, 9), (24, 11), (24, 17), (21, 18)], fill=C("4f7f38"))
    return outline(img, 0.35)


def gen_buildings():
    save(ranger_station(), "buildings/ranger_station.png")
    save(hatchery(), "buildings/hatchery.png")
    save(watchtower(), "buildings/watchtower.png")
    save(watchtower(dark=True), "buildings/poacher_tower.png")
    save(supply_depot(), "buildings/supply_depot.png")
    save(poacher_camp(), "buildings/poacher_camp.png")
    save(resource_amber(), "resources/amber.png")
    save(resource_crates(), "resources/crates.png")


# --------------------------------------------------------------------------
# UI art
# --------------------------------------------------------------------------
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
    save(outline(img, 0.4), "../../icon.png")


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
    fr = Image.new("RGBA", (44, 36), (0, 0, 0, 0))
    trex(ImageDraw.Draw(fr), 5, 44, 36)
    sil = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    sil.paste(C("0a140c"), (0, 0), fr)
    sil = sil.resize((88, 72), Image.NEAREST)
    img.alpha_composite(sil, (30, 70))
    save(img, "ui/menu_bg.png", scale=4)


def main():
    gen_tiles()
    gen_decor()
    gen_humans()
    save(sheet(jeep, 31, 20), "units/jeep.png")
    save(sheet(raptor, 28, 18), "units/raptor.png")
    save(sheet(dilophosaurus, 32, 22), "units/dilophosaurus.png")
    save(sheet(triceratops, 37, 24), "units/triceratops.png")
    save(sheet(trex, 44, 36), "units/trex.png")
    gen_buildings()
    gen_icon()
    gen_menu_bg()
    print("sprites written to", OUT)


if __name__ == "__main__":
    main()
