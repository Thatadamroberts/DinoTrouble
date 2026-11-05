"""Buildings, resources, foliage and terrain textures for gen_sprites.py."""
import math

import numpy as np
from PIL import Image

from pixelkit import BAYER, Canvas, Mat, ShadowLayer, drop_shadow, hexrgb, quantise, speckle, tile_noise

# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
LOG = Mat(["#2a160a", "#4a2a14", "#6e4220", "#94602e", "#b8803e", "#d8a256"])
PLANK = Mat(["#2e1c0e", "#523218", "#7a4e26", "#a06a36", "#c48a4a"])
STONE = Mat(["#2a2a2a", "#464642", "#66645c", "#888478", "#aaa698", "#cac6b6"])
SHINGLE = Mat(["#14240e", "#223a16", "#34541e", "#4a7028", "#628a34", "#80a844"])
CONCRETE = Mat(["#3a3a38", "#5a5a56", "#7c7c76", "#9e9e96", "#bebeb4", "#dadace"])
METAL = Mat(["#16181c", "#2c3036", "#464c54", "#666e78", "#8a929c", "#b4bcc4"], spec=0.6)
RUST = Mat(["#2a1208", "#4a2010", "#6e3418", "#924a22", "#b4642e"])
CANVAS_TAN = Mat(["#4a3a22", "#6e5834", "#94784a", "#b89a62", "#d8bc82", "#eedaa4"])
CANVAS_OLIVE = Mat(["#1e2210", "#343a1c", "#4c5428", "#666e36", "#828a48"])
GLASS_WARM = Mat(["#6a3a08", "#c07010", "#f0b030", "#ffe08a"])
RED_CLOTH = Mat(["#3a0806", "#6a120c", "#9a2018", "#c83428", "#e85a44"])
GREEN_CLOTH = Mat(["#0e2a10", "#1a4a1c", "#28702a", "#3a9a3a", "#5ac050"])
EGG = Mat(["#6a6048", "#a89c7c", "#d8ceae", "#f4ecd6", "#fffaf0"], spec=0.4)
STRAW = Mat(["#4a3410", "#7a5a1c", "#a8822e", "#d0aa48", "#ecd070"])
SAND_BAG = Mat(["#4a4028", "#726440", "#9a8a5c", "#bcae7c"])
DIRT_PAD = Mat(["#3a2a18", "#56402a", "#745a3c", "#927652", "#ae9468"])
HAZARD_Y = Mat(["#6a5008", "#b08a10", "#e8c020", "#fff060"])
BARK = Mat(["#1e120a", "#3a2414", "#5a3a20", "#7a5230", "#9a6c40"])
LEAF = Mat(["#0a1a0a", "#143014", "#1e4a1a", "#2c6420", "#3e8228", "#56a034", "#78bc46"])
LEAF_LIGHT = Mat(["#12280e", "#1e4216", "#2e5e1e", "#447e28", "#5c9c32", "#7cba44", "#a0d860"])
PALM_LEAF = Mat(["#10260c", "#1c4014", "#2c5e1c", "#407e26", "#5a9e32", "#7cbc44"])
ROCK = Mat(["#1e1e1c", "#383834", "#56544c", "#76736a", "#98948a", "#bab6aa"])
MOSS = Mat(["#1a2a0e", "#2c4416", "#42601e", "#5a7e28"])
AMBER = Mat(["#4a1e04", "#8a3e08", "#c8680e", "#ec9620", "#ffc450", "#fff0a0"], spec=1.0)

FACE_L, FACE_R, FACE_T = 0.86, 0.55, 1.0


# ---------------------------------------------------------------------------
# Textures for faces (brightness multipliers)
# ---------------------------------------------------------------------------
def tex_logs(u, v):
    k = (v % 5) / 5.0
    val = 0.72 + 0.42 * np.sin(k * math.pi)
    val = np.where(v % 5 < 0.8, 0.45, val)
    grain = (np.sin(u * 0.9 + np.floor(v / 5) * 7.3) > 0.85) * -0.12
    return val + grain


def tex_planks_v(u, v):
    val = np.where(u % 6 < 0.9, 0.55, 0.95 + 0.08 * np.sin(np.floor(u / 6) * 4.1))
    return val + (np.sin(v * 0.7 + np.floor(u / 6) * 3.0) > 0.9) * -0.1


def tex_planks_h(u, v):
    val = np.where(v % 4 < 0.8, 0.55, 0.95 + 0.08 * np.sin(np.floor(v / 4) * 4.1))
    return val + (np.sin(u * 0.7 + np.floor(v / 4) * 3.0) > 0.9) * -0.1


def tex_shingles(u, v):
    row = np.floor(v / 4)
    col = np.floor((u + row * 3) / 6)
    val = 0.95 + 0.1 * np.sin(col * 2.7 + row * 1.3)
    val = np.where(v % 4 > 3.0, 0.62, val)
    val = np.where((u + row * 3) % 6 < 0.8, val * 0.8, val)
    return val


def tex_stone(u, v):
    row = np.floor(v / 5)
    off = (row % 2) * 4
    val = 0.92 + 0.1 * np.sin(np.floor((u + off) / 8) * 3.3 + row * 1.7)
    val = np.where((v % 5 < 0.9) | ((u + off) % 8 < 0.9), 0.5, val)
    return val


def tex_concrete(u, v):
    val = 0.95 + 0.06 * np.sin(u * 3.1 + v * 1.7) * np.sin(u * 0.7 - v * 2.3)
    val = np.where((u % 16 < 0.8) | (v % 12 < 0.8), 0.7, val)
    return val


def tex_corrugated(u, v):
    return 0.82 + 0.22 * np.sin(u * 1.4)


def tex_canvas(u, v):
    return 0.88 + 0.12 * np.sin(u * 0.45) + (np.sin(u * 2.3 + v * 1.1) > 0.92) * -0.08


def tex_flat(u, v):
    return np.ones_like(u)


# ---------------------------------------------------------------------------
# Building helpers
# ---------------------------------------------------------------------------
class Lot:
    """A building canvas: footprint of `size` tiles, extra height above it and
    side margins for shadows. The footprint diamond sits at the bottom and is
    horizontally centred (the game relies on this)."""

    def __init__(self, size, extra, margin=24):
        self.size = size
        self.w = size * 64 + margin * 2
        self.dh = size * 32
        self.h = self.dh + extra
        self.cx = self.w / 2
        self.cy = self.h - self.dh / 2
        self.c = Canvas(self.w, self.h)
        self.sh = ShadowLayer(self.w, self.h)

    def g(self, gx, gy, z=0.0):
        """Ground grid offset (tiles, from centre) + height (px) -> canvas."""
        return (self.cx + (gx - gy) * 32, self.cy + (gx + gy) * 16 - z)

    def diamond(self, hx, hy=None, z=0.0, ox=0.0, oy=0.0):
        hy = hx if hy is None else hy
        return [self.g(ox - hx, oy - hy, z), self.g(ox + hx, oy - hy, z), self.g(ox + hx, oy + hy, z), self.g(ox - hx, oy + hy, z)]

    def ground(self, mat, half, tex=None, pattern=None):
        T, R, B, L = self.diamond(half)
        self.c.face(L, (T[0] - L[0], T[1] - L[1]), (B[0] - L[0], B[1] - L[1]), mat, 0.9, tex, group=0, pattern=pattern)

    def box(self, hx, hy, z0, height, side_mat, top_mat, ltex=None, rtex=None, ttex=None, ox=0.0, oy=0.0, group=None, shadow=True, top=True):
        """Axis-aligned box on the grid. Returns the top corners (T, R, B, L)."""
        T0, R0, B0, L0 = self.diamond(hx, hy, z0, ox, oy)
        T1, R1, B1, L1 = self.diamond(hx, hy, z0 + height, ox, oy)
        if shadow:
            self.sh.prism([T0, R0, B0, L0], height + z0)
        g = group if group is not None else self.c.n
        # left face (L-B edge), right face (B-R edge)
        self.c.face(L1, (B1[0] - L1[0], B1[1] - L1[1]), (0, height), side_mat, FACE_L, ltex, g)
        self.c.face(B1, (R1[0] - B1[0], R1[1] - B1[1]), (0, height), side_mat, FACE_R, rtex, g)
        if top:
            self.c.face(L1, (T1[0] - L1[0], T1[1] - L1[1]), (B1[0] - L1[0], B1[1] - L1[1]), top_mat, FACE_T, ttex, g)
        return T1, R1, B1, L1

    def gable_roof(self, top, rise, mat, wall_mat, overhang=4, group=None):
        """Pitched roof whose ridge runs parallel to the left (L-B) face."""
        T, R, B, L = top
        ext = lambda p, q, k: (p[0] + (p[0] - q[0]) * k, p[1] + (p[1] - q[1]) * k)
        k = overhang / 40.0
        T, R, B, L = ext(T, B, k), ext(R, L, k), ext(B, T, k), ext(L, R, k)
        A = ((L[0] + T[0]) / 2, (L[1] + T[1]) / 2 - rise)
        C = ((B[0] + R[0]) / 2, (B[1] + R[1]) / 2 - rise)
        g = group if group is not None else self.c.n
        self.sh.prism([L, B, R, T], rise + (self.cy - min(L[1], B[1])) * 0.5)
        # back slope
        self.c.face(A, (C[0] - A[0], C[1] - A[1]), (T[0] - A[0], T[1] - A[1]), mat, 0.62, tex_shingles, g)
        # gable end (right face)
        self.c.polygon([B, R, C], wall_mat, normal=(0.7, 0.1, 0.5), group=g, flat=FACE_R * 0.95)
        # front slope
        self.c.face(A, (C[0] - A[0], C[1] - A[1]), (L[0] - A[0], L[1] - A[1]), mat, 0.98, tex_shingles, g)
        self.c.line((int(A[0]), int(A[1])), (int(C[0]), int(C[1])), shade_hex(mat, 4))
        return A, C

    def window(self, p, w=5, h=6, lit=True):
        x, y = p
        self.c.polygon([(x, y), (x + w, y + w / 2), (x + w, y + w / 2 + h), (x, y + h)],
                       GLASS_WARM if lit else Mat(["#101820", "#203040", "#406070"]), normal=(0, 0, 1), flat=0.85)
        self.c.line((x, y + h + 0.5), (x + w, y + w / 2 + h + 0.5), "#2a1a0a")

    def barrel(self, x, y, mat=None, h=9, r=4):
        mat = mat or RUST
        self.sh.blob(x + 4, y, r + 1, r * 0.5 + 1)
        self.c.capsule((x, y - 2), (x, y - h + 2), r, r, mat)
        self.c.ellipse(x, y - h + 2, r, r * 0.5, mat, group=self.c.n - 1, round_=0.3)

    def crate(self, gx, gy, s=0.18, h=8):
        self.box(s, s, 0, h, PLANK, PLANK, tex_planks_h, tex_planks_h, tex_planks_v, ox=gx, oy=gy)

    def render(self, shadow_alpha=105):
        img = self.sh.image(shadow_alpha)
        img.alpha_composite(self.c.finish())
        return img


def shade_hex(mat, i):
    r, g, b = mat.ramp[min(i, len(mat.ramp) - 1)]
    return (r, g, b)


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------
def ranger_station():
    lot = Lot(3, 120)
    c = lot.c
    lot.ground(DIRT_PAD, 1.45, pattern=speckle(21, 0.15, -1))
    lot.box(1.25, 1.2, 0, 6, STONE, STONE, tex_stone, tex_stone, tex_stone)
    top = lot.box(1.15, 1.1, 6, 30, LOG, LOG, tex_logs, tex_logs, top=False)
    # door & windows on the left face, windows on the right face
    L = lot.g(-1.15, 1.1, 6)
    c.polygon([lot.g(-0.25, 1.1, 6), lot.g(0.15, 1.1, 6), lot.g(0.15, 1.1, 26), lot.g(-0.25, 1.1, 26)], PLANK, normal=(0, 0, 1), flat=0.55)
    c.pixel(*lot.g(0.08, 1.1, 15), "#e0c060")
    for gx in (-0.85, 0.55):
        lot.window(lot.g(gx, 1.1, 24), 8, 9)
    for gy in (0.6, -0.2):
        p = lot.g(1.15, gy, 24)
        lot.window((p[0] - 8, p[1] - 4), 8, 9)
    lot.gable_roof(top, 26, SHINGLE, LOG)
    # chimney
    lot.box(0.12, 0.12, 52, 18, STONE, STONE, tex_stone, tex_stone, ox=0.5, oy=-0.75, shadow=False)
    # porch posts & bench
    for gx in (-0.95, 0.95):
        b = lot.g(gx, 1.35, 0)
        c.capsule(b, (b[0], b[1] - 30), 1.4, 1.4, LOG)
    # flag
    fb = lot.g(-1.35, -1.25, 0)
    c.capsule(fb, (fb[0], fb[1] - 78), 1.0, 0.8, METAL)
    c.polygon([(fb[0] + 1, fb[1] - 78), (fb[0] + 20, fb[1] - 74), (fb[0] + 18, fb[1] - 66), (fb[0] + 1, fb[1] - 68)], GREEN_CLOTH,
              normal=(-0.2, -0.2, 1), pattern=lambda xx, yy, nx, ny: (np.sin(xx * 0.8) > 0.3) * -1)
    lot.sh.prism([fb], 78, 0.6, -0.1)
    # props
    lot.crate(1.25, 1.45)
    lot.crate(1.5, 1.2, h=7)
    lot.barrel(*lot.g(-1.45, 1.35, 0), mat=PLANK)
    return lot.render()


def hatchery():
    lot = Lot(3, 96)
    c = lot.c
    lot.ground(CONCRETE, 1.5, tex_concrete)
    # hazard stripes around the pad edge
    T, R, B, L = lot.diamond(1.5)
    T2, R2, B2, L2 = lot.diamond(1.36)
    c.polygon([L, B, B2, L2], HAZARD_Y, normal=(0, 0, 1), flat=0.85,
              pattern=lambda xx, yy, nx, ny: np.where(((xx - yy * 2) // 6) % 2 == 0, -3, 0))
    c.polygon([B, R, R2, B2], HAZARD_Y, normal=(0, 0, 1), flat=0.7,
              pattern=lambda xx, yy, nx, ny: np.where(((xx + yy * 2) // 6) % 2 == 0, -3, 0))
    top = lot.box(1.2, 1.2, 0, 8, CONCRETE, CONCRETE, tex_concrete, tex_concrete, tex_concrete)
    # nest & eggs
    cx, cy = lot.g(0, 0, 8)
    c.ellipse(cx, cy, 52, 24, STRAW, round_=0.4, pattern=speckle(33, 0.3, -1))
    for ex, ey, r in ((-22, -6, 7), (-6, -10, 8), (12, -7, 7), (26, 0, 6), (2, 4, 8), (-16, 6, 7)):
        c.ellipse(cx + ex, cy + ey - r * 0.6, r * 0.8, r, EGG, pattern=speckle(int(ex * 3 + 100), 0.07, -2))
    # glass dome: tint what is under it, then ribs and highlights
    xx, yy = c.xx, c.yy
    dcx, dcy, rx, ry = cx, cy + 2, 58, 64
    u = (xx - dcx) / rx
    v = (yy - dcy) / ry
    dome = (u * u + v * v <= 1) & (yy <= dcy)
    under = c.a > 0
    tint = np.array([140, 210, 220], np.float32)
    base = np.where(under[..., None], c.rgb.astype(np.float32), np.array([90, 150, 160], np.float32))
    nz = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
    fres = (1 - nz) ** 2
    col = base * (0.55 - 0.15 * fres[..., None]) + tint * (0.35 + 0.5 * fres[..., None])
    c.rgb[dome] = np.clip(col[dome], 0, 255).astype(np.uint8)
    c.a[dome] = 255
    c.part[dome] = c.n
    c.group[dome] = c.n
    c.outline_col[dome] = (30, 50, 56)
    c.n += 1
    for k in (-0.8, -0.45, 0.0, 0.45, 0.8):  # meridian ribs
        for th in np.linspace(0, math.pi / 2, 70):
            c.pixel(dcx + rx * math.cos(th) * k, dcy - ry * math.sin(th), (196, 216, 218))
    for t in np.linspace(0, 1, 120):  # base ring and rim
        ang = math.pi * (1 + t)
        c.pixel(dcx + math.cos(ang) * rx, dcy + math.sin(ang) * ry, (210, 228, 230))
    for t in np.linspace(0.15, 0.4, 40):  # highlight streak
        ang = math.pi * (1 + t)
        c.pixel(dcx + math.cos(ang) * rx * 0.78, dcy + math.sin(ang) * ry * 0.82, (255, 255, 255))
        c.pixel(dcx + math.cos(ang) * rx * 0.74, dcy + math.sin(ang) * ry * 0.78, (230, 250, 252))
    lot.sh.blob(dcx + 30, dcy - 4, 60, 22)
    # side tank & pipes
    tx, ty = lot.g(1.15, -0.55, 0)
    lot.sh.prism([(tx - 8, ty), (tx + 8, ty)], 34)
    c.capsule((tx, ty - 4), (tx, ty - 30), 8, 8, METAL)
    c.ellipse(tx, ty - 30, 8, 3.5, METAL, group=c.n - 1, round_=0.3)
    c.capsule((tx - 6, ty - 20), (tx - 22, ty - 12), 1.8, 1.8, METAL)
    c.ellipse(tx, ty - 36, 2, 2, Mat(["#600000", "#c01010", "#ff4040", "#ffc0c0"], spec=1))
    # control box
    bx, by = lot.g(-1.2, 0.9, 8)
    c.polygon([(bx, by - 2), (bx + 10, by + 3), (bx + 10, by - 9), (bx, by - 14)], METAL, normal=(-0.5, 0, 1), flat=0.6)
    c.polygon([(bx + 2, by - 10), (bx + 8, by - 7), (bx + 8, by - 3), (bx + 2, by - 6)], Mat(["#0a3010", "#20a040", "#80ff90"]), normal=(0, 0, 1), flat=0.8)
    return lot.render()


def watchtower(dark=False):
    lot = Lot(2, 150, margin=30)
    c = lot.c
    wood = METAL if dark else LOG
    lot.ground(DIRT_PAD, 0.95, pattern=speckle(5, 0.2, -1))
    legs = [(-0.7, -0.7), (0.7, -0.7), (0.7, 0.7), (-0.7, 0.7)]
    H = 70
    for gx, gy in legs:
        b = lot.g(gx, gy, 0)
        t = lot.g(gx * 0.75, gy * 0.75, H)
        lot.sh.prism([(b[0] - 2, b[1]), (b[0] + 2, b[1])], H, 0.75, -0.12)
        if (gx, gy) == (-0.7, -0.7):
            c.capsule(b, t, 2.2, 1.8, wood, shade=0.7)
    for (a, b2) in (((-0.7, 0.7), (0.7, 0.7)), ((0.7, -0.7), (0.7, 0.7))):
        for z0, z1 in ((8, 38), (38, 8), (40, 66), (66, 40)):
            p0 = lot.g(a[0] * (1 - z0 / H * 0.25), a[1] * (1 - z0 / H * 0.25), z0)
            p1 = lot.g(b2[0] * (1 - z1 / H * 0.25), b2[1] * (1 - z1 / H * 0.25), z1)
            c.capsule(p0, p1, 0.9, 0.9, wood, shade=0.85)
    for gx, gy in legs[1:]:
        b = lot.g(gx, gy, 0)
        t = lot.g(gx * 0.75, gy * 0.75, H)
        c.capsule(b, t, 2.2, 1.8, wood)
    # ladder
    l0 = lot.g(-0.2, 0.75, 0)
    for k in range(0, H, 6):
        c.line((l0[0] - 3, l0[1] - k), (l0[0] + 3, l0[1] - k), shade_hex(PLANK, 3))
    c.line((l0[0] - 3, l0[1]), (l0[0] - 3, l0[1] - H), shade_hex(PLANK, 1))
    c.line((l0[0] + 3, l0[1]), (l0[0] + 3, l0[1] - H), shade_hex(PLANK, 1))
    # platform
    lot.box(0.82, 0.82, H, 4, PLANK, PLANK, tex_planks_h, tex_planks_h, tex_planks_v, shadow=False)
    hut_mat = RUST if dark else PLANK
    top = lot.box(0.5, 0.5, H + 4, 18, hut_mat, hut_mat, tex_corrugated if dark else tex_planks_v,
                  tex_corrugated if dark else tex_planks_v, top=False, shadow=False)
    T, R, B, L = top
    roof_m = METAL if dark else SHINGLE
    apex = lot.g(0, 0, H + 40)
    c.polygon([T, R, apex], roof_m, flat=0.6)
    c.polygon([L, B, apex], roof_m, flat=0.95, pattern=lambda xx, yy, nx, ny: ((yy % 4) < 1) * -1)
    c.polygon([B, R, apex], roof_m, flat=0.72, pattern=lambda xx, yy, nx, ny: ((yy % 4) < 1) * -1)
    lot.window(lot.g(-0.15, 0.5, H + 18), 7, 6, lit=not dark)
    # railing posts
    for gx, gy in ((-0.82, 0.82), (0.82, 0.82), (0.82, -0.82), (0, 0.82), (0.82, 0)):
        p = lot.g(gx, gy, H + 4)
        c.capsule(p, (p[0], p[1] - 8), 0.8, 0.8, PLANK)
    p1, p2, p3 = lot.g(-0.82, 0.82, H + 11), lot.g(0.82, 0.82, H + 11), lot.g(0.82, -0.82, H + 11)
    c.capsule(p1, p2, 0.8, 0.8, PLANK)
    c.capsule(p2, p3, 0.8, 0.8, PLANK)
    light = lot.g(0.6, 0.3, H + 14)
    c.ellipse(light[0], light[1], 3, 3, Mat(["#600000", "#c01010", "#ff4040", "#ffd0d0"], spec=1) if dark
              else Mat(["#806020", "#f0d060", "#fffbd0", "#ffffff"], spec=1))
    if dark:
        for gx in (-0.5, 0.3):
            p = lot.g(gx, 0.82, H + 4)
            c.ellipse(p[0], p[1] - 2, 5, 3, SAND_BAG)
    return lot.render()


def supply_depot():
    lot = Lot(2, 64)
    c = lot.c
    lot.ground(DIRT_PAD, 0.95, pattern=speckle(9, 0.2, -1))
    top = lot.box(0.7, 0.55, 0, 22, METAL, METAL, tex_corrugated, tex_corrugated, top=False, ox=-0.1, oy=-0.2)
    lot.gable_roof(top, 12, Mat(["#0e2a2a", "#164040", "#205a5a", "#2c7474", "#3a9090", "#4cacac"]), METAL, overhang=3)
    door = [lot.g(-0.45, 0.35, 0), lot.g(0.15, 0.35, 0), lot.g(0.15, 0.35, 16), lot.g(-0.45, 0.35, 16)]
    c.polygon(door, Mat(["#0a0a0c", "#16181c", "#22262c"]), flat=0.6)
    lot.crate(0.55, 0.65)
    lot.crate(0.75, 0.35, h=7)
    lot.barrel(*lot.g(-0.75, 0.75, 0), mat=Mat(["#0a2a0a", "#164a14", "#24701e", "#38922c"]))
    lot.barrel(*lot.g(-0.55, 0.85, 0), mat=Mat(["#0a2a0a", "#164a14", "#24701e", "#38922c"]))
    for k, (gx, gy) in enumerate(((0.2, 0.85), (0.35, 0.8))):
        p = lot.g(gx, gy, 0)
        lot.sh.blob(p[0] + 4, p[1], 6, 3)
        c.ellipse(p[0], p[1] - 3, 5, 3.5, SAND_BAG)
    return lot.render()


def tent(lot, gx, gy, hx, hy, h, mat):
    c = lot.c
    T, R, B, L = lot.diamond(hx, hy, 0, gx, gy)
    A = ((L[0] + T[0]) / 2, (L[1] + T[1]) / 2 - h)
    Cc = ((B[0] + R[0]) / 2, (B[1] + R[1]) / 2 - h)
    lot.sh.prism([L, B, R, T], h * 0.7)
    g = c.n
    c.face(A, (Cc[0] - A[0], Cc[1] - A[1]), (T[0] - A[0], T[1] - A[1]), mat, 0.6, tex_canvas, g)
    c.polygon([B, R, Cc], mat, flat=0.5, group=g)
    c.face(A, (Cc[0] - A[0], Cc[1] - A[1]), (L[0] - A[0], L[1] - A[1]), mat, 0.95, tex_canvas, g)
    # door flap on the gable end
    m = ((B[0] + R[0]) / 2, (B[1] + R[1]) / 2)
    c.polygon([(m[0] - 4, m[1] - 2), (m[0] + 1, m[1] - 2), ((m[0] + Cc[0]) / 2, (m[1] + Cc[1]) / 2 + 3)],
              Mat(["#0a0806", "#1a140e", "#2a2018"]), flat=0.4)
    c.line((int(A[0]), int(A[1])), (int(Cc[0]), int(Cc[1])), shade_hex(mat, 4))


def poacher_camp():
    lot = Lot(3, 90)
    c = lot.c
    lot.ground(DIRT_PAD, 1.45, pattern=speckle(13, 0.22, -1))
    lot.crate(-1.25, -0.9)
    lot.crate(-1.3, -0.55, h=7)
    tent(lot, -0.25, -0.35, 0.75, 0.55, 40, CANVAS_OLIVE)
    tent(lot, -0.9, 0.55, 0.45, 0.4, 26, CANVAS_TAN)
    tent(lot, 0.75, 0.6, 0.45, 0.4, 26, CANVAS_TAN)
    # cage
    cx0, cy0 = lot.g(0.85, -0.6, 0)
    lot.box(0.35, 0.35, 0, 3, PLANK, PLANK, tex_planks_h, tex_planks_h, tex_planks_v, ox=0.85, oy=-0.6)
    egg = lot.g(0.85, -0.6, 3)
    c.ellipse(egg[0], egg[1] - 7, 6, 8, EGG, pattern=speckle(5, 0.08, -2))
    T, R, B, L = lot.diamond(0.35, 0.35, 3, 0.85, -0.6)
    for p0, p1 in ((L, B), (B, R)):
        for t in np.linspace(0, 1, 7):
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            c.line((x, y), (x, y - 20), shade_hex(METAL, 3))
    lot.sh.prism([L, B, R, T], 22)
    # campfire
    fx, fy = lot.g(0.15, 0.95, 0)
    for k in range(8):
        a = k / 8 * math.tau
        c.ellipse(fx + math.cos(a) * 7, fy + math.sin(a) * 3.5, 2, 1.5, STONE)
    c.capsule((fx - 5, fy), (fx + 5, fy - 1), 1.2, 1.2, LOG)
    for (dx, dy, col) in ((0, -3, "#ff9020"), (-1, -5, "#ffc040"), (1, -6, "#ffe080"), (0, -8, "#fff4c0"), (2, -4, "#ff7010"), (-2, -3, "#ff6010")):
        c.pixel(fx + dx, fy + dy, col)
    # banner
    fb = lot.g(1.3, -1.25, 0)
    c.capsule(fb, (fb[0], fb[1] - 64), 1.0, 0.8, METAL)
    c.polygon([(fb[0] + 1, fb[1] - 64), (fb[0] + 18, fb[1] - 60), (fb[0] + 16, fb[1] - 52), (fb[0] + 1, fb[1] - 54)], RED_CLOTH,
              normal=(-0.2, -0.2, 1), pattern=lambda xx, yy, nx, ny: (np.sin(xx * 0.8) > 0.3) * -1)
    lot.sh.prism([fb], 64, 0.6, -0.1)
    # fuel drums
    lot.barrel(*lot.g(1.4, 0.2, 0), mat=RED_CLOTH)
    lot.barrel(*lot.g(1.3, 0.45, 0), mat=RED_CLOTH)
    # fence posts along the front edges
    for t in np.linspace(-1.45, 1.45, 9):
        for p in (lot.g(t, 1.5, 0), lot.g(1.5, t, 0)):
            c.capsule(p, (p[0], p[1] - 9), 1.3, 1.1, LOG)
    return lot.render()


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
def rock_pile(c, sh, specs, moss=True):
    for x, y, rx, ry in specs:
        sh.blob(x + rx * 0.5, y + ry * 0.6, rx, ry * 0.5)
    for x, y, rx, ry in specs:
        c.ellipse(x, y, rx, ry, ROCK, round_=0.85, pattern=speckle(int(x * 7 + y), 0.08, -1))
        if moss:
            c.ellipse(x - rx * 0.2, y - ry * 0.55, rx * 0.6, ry * 0.35, MOSS, round_=0.6,
                      pattern=speckle(int(x + y * 3), 0.3, -1))


def amber():
    c = Canvas(64, 52)
    sh = ShadowLayer(64, 52)
    rock_pile(c, sh, [(22, 40, 14, 9), (40, 41, 12, 8)])
    for x0, top, w, h in ((14, 18, 9, 22), (26, 8, 11, 32), (39, 20, 9, 20), (46, 30, 6, 12)):
        xm = x0 + w * 0.45
        base = 44
        pts_l = [(x0, base), (x0, top + 5), (xm, top), (xm, base)]
        pts_r = [(xm, base), (xm, top), (x0 + w, top + 5), (x0 + w, base)]
        g = c.n
        c.polygon(pts_l, AMBER, flat=0.92, group=g, pattern=lambda xx, yy, nx, ny, t=top: np.where((yy - t) % 7 < 1, 1, 0))
        c.polygon(pts_r, AMBER, flat=0.55, group=g)
        c.line((x0 + 1, top + 6), (x0 + 1, base - 3), "#fff4b0")
        c.pixel(xm - 1, top + 3, "#ffffff")
        sh.prism([(x0, base), (x0 + w, base)], base - top, 0.5, -0.05)
    rock_pile(c, sh, [(12, 44, 7, 5), (50, 45, 8, 5)], moss=False)
    img = sh.image(100)
    img.alpha_composite(c.finish())
    return img


def crates():
    lot = Lot(1, 40, margin=4)
    lot.c = Canvas(lot.w, lot.h)
    lot.sh = ShadowLayer(lot.w, lot.h)
    lot.crate(-0.18, 0.05, s=0.2, h=11)
    lot.crate(0.2, 0.15, s=0.2, h=11)
    lot.box(0.2, 0.2, 11, 11, PLANK, PLANK, tex_planks_h, tex_planks_h, tex_planks_v, ox=0.0, oy=0.05)
    p = lot.g(0.3, -0.25, 0)
    lot.barrel(p[0], p[1], mat=Mat(["#0a2a0a", "#164a14", "#24701e", "#38922c"]))
    t = lot.g(-0.3, -0.3, 0)
    lot.c.polygon([(t[0] - 10, t[1]), (t[0] - 4, t[1] - 10), (t[0] + 6, t[1] - 8), (t[0] + 8, t[1] + 2)], GREEN_CLOTH, flat=0.8,
                  pattern=lambda xx, yy, nx, ny: (np.sin(xx * 1.1 + yy) > 0.5) * -1)
    return lot.render(100)


# ---------------------------------------------------------------------------
# Foliage & rocks
# ---------------------------------------------------------------------------
def tree(seed):
    rnd = np.random.default_rng(seed)
    w, h = 96, 112
    c = Canvas(w, h)
    base = (44, 106)
    lean = rnd.uniform(-4, 4)
    top = (44 + lean, 70)
    c.ellipse(base[0], base[1] - 1, 7, 2.5, BARK, round_=0.5)  # root flare
    for dx in (-6, 6):
        c.capsule((base[0], base[1] - 3), (base[0] + dx, base[1]), 2.4, 1.2, BARK, 1)
    c.capsule(base, top, 6.5, 4.2, BARK, 1, pattern=lambda xx, yy, nx, ny: (np.sin(xx * 2.2 + yy * 0.3) > 0.6) * -1)
    c.capsule((top[0], top[1] + 10), (top[0] + 12, top[1] - 4), 2.2, 1.4, BARK, 1)
    c.capsule((top[0], top[1] + 14), (top[0] - 13, top[1] - 2), 2.2, 1.4, BARK, 1)
    blobs = []
    for _ in range(18):
        a = rnd.uniform(0, math.tau)
        r = rnd.uniform(0, 1) ** 0.6
        bx = top[0] + math.cos(a) * 28 * r
        by = top[1] - 24 + math.sin(a) * 20 * r
        blobs.append((by, bx, rnd.uniform(10, 15)))
    blobs.sort()
    for by, bx, br in blobs:
        shade = 0.78 + 0.3 * (1 - (by - (top[1] - 44)) / 44)
        c.ellipse(bx, by, br, br * 0.85, LEAF if seed % 2 else LEAF_LIGHT, group=5, shade=shade,
                  pattern=speckle(int(bx * 13 + by), 0.12, -1), round_=0.9)
    img = c.finish(inner=True)
    return drop_shadow(img, dx=8, dy=0, squash=0.3, alpha=95)


def palm(seed):
    rnd = np.random.default_rng(seed)
    w, h = 96, 112
    c = Canvas(w, h)
    bend = rnd.uniform(-10, 10)
    pts = []
    for i in range(9):
        t = i / 8
        pts.append((44 + bend * t * t, 106 - t * 62))
    radii = [4.0 - i * 0.18 for i in range(9)]
    c.chain(pts, radii, BARK, 1, pattern=lambda xx, yy, nx, ny: ((yy.astype(int) % 4) == 0) * -1)
    top = pts[-1]
    for k in range(3):  # coconuts
        c.ellipse(top[0] - 3 + k * 3, top[1] + 4 + (k % 2), 2.6, 2.6, Mat(["#2a1a08", "#5a3a14", "#8a5a22", "#b07a34"]))
    for k in range(10):
        a = math.radians(k * 36 + rnd.uniform(-10, 10))
        length = rnd.uniform(26, 34)
        back = math.sin(a) < -0.2
        fpts = []
        for j in range(8):
            t = j / 7
            fpts.append((top[0] + math.cos(a) * length * t,
                         top[1] + math.sin(a) * length * 0.4 * t - math.sin(t * math.pi * 0.8) * 10 + t * t * 12))
        mat_shade = 0.62 if back else 1.0
        for j in range(1, 8):  # broad leaflets on both sides of the rib
            px, py = fpts[j]
            dx, dy = fpts[j][0] - fpts[j - 1][0], fpts[j][1] - fpts[j - 1][1]
            n = math.hypot(dx, dy) + 1e-6
            ox, oy = -dy / n, dx / n
            L = 7.5 * math.sin((j / 8) * math.pi) + 2
            for side, sh_ in ((1, 1.0), (-1, 0.78)):
                tip = (px + ox * L * side + dx / n * 3, py + oy * L * side + 4)
                c.capsule((px, py), tip, 1.3, 0.5, PALM_LEAF, 3 + k, shade=mat_shade * sh_)
        c.chain(fpts, [1.4, 1.3, 1.2, 1.1, 1.0, 0.8, 0.6, 0.4], PALM_LEAF, 3 + k, shade=mat_shade * 1.1)
    img = c.finish()
    return drop_shadow(img, dx=8, dy=0, squash=0.3, alpha=90)


def bush(seed):
    rnd = np.random.default_rng(seed)
    w, h = 48, 32
    c = Canvas(w, h)
    for k in range(11):
        a = math.radians(180 + k * 18 + rnd.uniform(-8, 8))
        L = rnd.uniform(12, 18)
        pts = [(24 + math.cos(a) * L * t, 29 + math.sin(a) * L * 0.9 * t + t * t * 8) for t in (0, 0.35, 0.7, 1.0)]
        c.chain(pts, [1.6, 1.4, 1.0, 0.5], LEAF_LIGHT if k % 3 else LEAF, k, shade=0.8 + 0.2 * (k % 2))
        for t in (0.35, 0.7):
            px, py = 24 + math.cos(a) * L * t, 29 + math.sin(a) * L * 0.9 * t + t * t * 8
            c.pixel(px - 2, py + 1, shade_hex(LEAF_LIGHT, 5))
            c.pixel(px + 2, py + 1, shade_hex(LEAF_LIGHT, 3))
    return drop_shadow(c.finish(), dx=4, dy=0, squash=0.25, alpha=80)


def boulder(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(52, 40)
    sh = ShadowLayer(52, 40)
    specs = [(22, 26, 14, 11), (34, 30, 9, 7)] if seed % 2 else [(24, 27, 16, 10), (12, 32, 6, 5)]
    rock_pile(c, sh, specs)
    img = sh.image(95)
    img.alpha_composite(c.finish())
    return img


def tuft(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(20, 16)
    greens = ["#2c5e1c", "#407e26", "#5a9e32", "#7cbc44", "#a0d860"]
    for k in range(9):
        x0 = 10 + rnd.uniform(-5, 5)
        lean = rnd.uniform(-4, 4)
        hgt = rnd.uniform(6, 12)
        col = hexrgb(greens[rnd.integers(0, len(greens))])
        c.line((x0, 14), (x0 + lean, 14 - hgt), col)
    return c.finish(outline=False)


def flowers(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(22, 16)
    petal = [["#e84a6a", "#ff90a8"], ["#f0d040", "#fff4a0"], ["#e8e8f0", "#ffffff"], ["#a060e0", "#d0a0ff"]][seed % 4]
    for k in range(5):
        x = 11 + rnd.uniform(-7, 7)
        y = 14 - rnd.uniform(3, 8)
        c.line((x, 14), (x + rnd.uniform(-1, 1), y), "#3e7e24")
        c.pixel(x - 1, y, petal[0])
        c.pixel(x + 1, y, petal[0])
        c.pixel(x, y - 1, petal[0])
        c.pixel(x, y + 1, petal[0])
        c.pixel(x, y, petal[1])
    return c.finish(outline=False)


# ---------------------------------------------------------------------------
# Seamless ground textures (world space, used by the ground shader)
# ---------------------------------------------------------------------------
TEX = 128


def _blades(img, rnd, count, cols, hmin, hmax):
    for _ in range(count):
        x, y = rnd.integers(0, TEX), rnd.integers(0, TEX)
        hgt = rnd.integers(hmin, hmax + 1)
        col = np.array(hexrgb(cols[rnd.integers(0, len(cols))]))
        lean = rnd.choice([-1, 0, 0, 1])
        for k in range(hgt):
            img[(y - k) % TEX, (x + (k * lean) // 3) % TEX] = col


def _blobs(img, rnd, count, cols, rx, ry):
    yy, xx = np.mgrid[0:TEX, 0:TEX]
    for _ in range(count):
        cx, cy = rnd.uniform(0, TEX), rnd.uniform(0, TEX)
        r1, r2 = rnd.uniform(*rx), rnd.uniform(*ry)
        dx = (xx - cx + TEX / 2) % TEX - TEX / 2
        dy = (yy - cy + TEX / 2) % TEX - TEX / 2
        m = (dx / r1) ** 2 + (dy / r2) ** 2 <= 1
        lit = (dx / r1 + dy / r2) < -0.3
        col = cols[rnd.integers(0, len(cols))]
        img[m] = np.array(hexrgb(col[0]))
        img[m & lit] = np.array(hexrgb(col[1]))


def ground_textures():
    out = {}
    n1 = tile_noise(TEX, 4, 1, 4)
    n2 = tile_noise(TEX, 8, 2, 3)
    rnd = np.random.default_rng(42)

    g = quantise(n1 * 0.7 + n2 * 0.3, ["#34501c", "#3e5e20", "#486c26", "#547a2c", "#608632"], 0.9)
    _blades(g, rnd, 380, ["#6a9638", "#76a240", "#36561c", "#82ac48"], 2, 4)
    _blades(g, rnd, 40, ["#a2c45c", "#b8d070"], 2, 3)
    _blobs(g, rnd, 10, [("#4a7a2a", "#68983a")], (2.5, 4.0), (1.4, 2.2))  # clover patches
    _blobs(g, rnd, 8, [("#5e5a50", "#9a968a")], (0.8, 1.4), (0.6, 0.9))  # stones
    for _ in range(6):  # tiny white flowers
        x, y = rnd.integers(0, TEX), rnd.integers(0, TEX)
        g[y, x] = hexrgb("#f4f0e0")
    out["grass"] = g

    j = quantise(n2 * 0.6 + n1 * 0.4, ["#1c2a12", "#243616", "#2e441a", "#38501e", "#445c24"], 0.9)
    _blobs(j, rnd, 70, [("#4a3a1c", "#6a5428"), ("#3a4a18", "#566a22"), ("#2a2412", "#423a1c")], (1.5, 3.5), (1, 2))
    _blades(j, rnd, 160, ["#3e6a22", "#4c7e28", "#24401a"], 2, 4)
    _blobs(j, rnd, 16, [("#5a3a1a", "#8a5a2a")], (0.8, 1.2), (0.6, 0.9))  # seeds
    for _ in range(6):  # surface roots
        x, y = rnd.uniform(0, TEX), rnd.uniform(0, TEX)
        a = rnd.uniform(0, math.pi)
        for t in range(10):
            j[int(y + math.sin(a) * t * 0.5) % TEX, int(x + math.cos(a) * t) % TEX] = hexrgb("#3a2a14")
    out["jungle"] = j

    yy, xx = np.mgrid[0:TEX, 0:TEX]
    ripple = (np.sin((yy + n1 * 10) * (2 * math.pi / 8) + xx * (2 * math.pi / 64)) + 1) / 2
    s = quantise(0.45 + ripple * 0.25 + (n2 - 0.5) * 0.4, ["#b89c5c", "#c8ae6c", "#d6be7c", "#e2cc8c", "#ecd89c"], 0.8)
    _blobs(s, rnd, 14, [("#a08a5a", "#f4ecd8"), ("#8a7a5a", "#c8b898")], (0.8, 1.6), (0.6, 1.0))
    _blobs(s, rnd, 3, [("#7a6248", "#a88a66")], (3.0, 4.5), (0.7, 1.0))  # driftwood
    out["sand"] = s

    d = quantise(n1 * 0.6 + n2 * 0.4, ["#4e3a22", "#5e482a", "#6e5634", "#7e643c", "#8e7246"], 0.9)
    _blobs(d, rnd, 60, [("#5a5248", "#9a9284"), ("#4a3a2a", "#7a6448"), ("#6a5a48", "#a89a84")], (1.0, 2.4), (0.7, 1.4))
    out["dirt"] = d

    # rock: voronoi slabs with dark seams (wrapped distances keep it seamless)
    pts = rnd.uniform(0, TEX, (26, 2))
    best = np.full((TEX, TEX), 1e9)
    second = np.full((TEX, TEX), 1e9)
    cell = np.zeros((TEX, TEX), int)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px)
        dx = np.minimum(dx, TEX - dx)
        dy = np.abs(yy - py)
        dy = np.minimum(dy, TEX - dy) * 2.0
        dist = np.sqrt(dx * dx + dy * dy)
        closer = dist < best
        second = np.where(closer, best, np.minimum(second, dist))
        cell = np.where(closer, i, cell)
        best = np.where(closer, dist, best)
    shade_cell = (np.sin(cell * 12.9898) * 43758.5453) % 1.0
    val = 0.45 + shade_cell * 0.25 + (n2 - 0.5) * 0.3
    val = np.where(second - best < 1.4, 0.2, val)
    out["rock"] = quantise(val, ["#4a4740", "#57544c", "#646058", "#716d64", "#7e7a70", "#8a867c"], 0.7)

    noise = (tile_noise(TEX, 4, 9, 4) * 255).astype(np.uint8)
    return {k: Image.fromarray(v, "RGB") for k, v in out.items()}, Image.fromarray(noise, "L")


# ---------------------------------------------------------------------------
# More jungle: plants, clutter, shoreline and water decor
# ---------------------------------------------------------------------------
FROND = Mat(["#0e2a10", "#1a4418", "#286022", "#3a7e2c", "#509c38", "#6eb848"])
FERN = Mat(["#10300e", "#1c4c16", "#2c6a20", "#40882a", "#58a636", "#7ac44a"])
NEEDLE = Mat(["#081a10", "#0e2a18", "#163c20", "#20502a", "#2e6634", "#407e40"])
WOOD_CUT = Mat(["#4a3018", "#7a5228", "#a8783c", "#cca058", "#e4c27a"])
BONE_M = Mat(["#6a6450", "#a8a088", "#d4ccb2", "#eee8d6", "#fffcf0"])
CAP_RED = Mat(["#4a0a08", "#8a1a10", "#c02a1a", "#e8503a"])
CAP_TAN = Mat(["#4a3018", "#7a5430", "#a87a48", "#d0a466"])
STEM = Mat(["#8a8270", "#c8c0a8", "#ece6d4"])
LILY = Mat(["#0e3018", "#1a4a22", "#2a6a2e", "#3e8a3a", "#58a84c"])
REED = Mat(["#2a3a14", "#46601e", "#66842a", "#88a43a"])
CATTAIL = Mat(["#2a160a", "#4a2a14", "#6e4222"])


def _frond(c, base, ang, length, droop, mat, group, shade=1.0, leaflet=4.0, lift=8.0):
    pts = []
    for j in range(8):
        t = j / 7
        pts.append((base[0] + math.cos(ang) * length * t,
                    base[1] + math.sin(ang) * length * 0.45 * t - math.sin(t * math.pi * 0.85) * lift + t * t * droop))
    for j in range(1, 8):
        px, py = pts[j]
        dx, dy = pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]
        n = math.hypot(dx, dy) + 1e-6
        ox, oy = -dy / n, dx / n
        L = leaflet * math.sin((j / 8) * math.pi) + 1.0
        for side, sh in ((1, 1.0), (-1, 0.8)):
            c.capsule((px, py), (px + ox * L * side + dx / n * 2, py + oy * L * side + 2.5), 0.9, 0.4, mat, group, shade * sh)
    c.chain(pts, [1.2, 1.1, 1.0, 0.9, 0.8, 0.6, 0.5, 0.3], mat, group, shade * 1.1)


def cycad(seed):
    rnd = np.random.default_rng(seed)
    w, h = 80, 80
    c = Canvas(w, h)
    bx = w // 2 - 4
    top = (bx, h - 26)
    c.capsule((bx, h - 7), top, 6.5, 5.5, BARK, 1,
              pattern=lambda xx, yy, nx, ny: np.where(((xx + yy * 1.5).astype(int) % 4 == 0) | ((xx - yy * 1.5).astype(int) % 4 == 0), -1, 0))
    fronds = sorted(range(12), key=lambda k: math.sin(math.radians(k * 30)))
    for k in fronds:
        a = math.radians(k * 30 + rnd.uniform(-8, 8))
        back = math.sin(a) < -0.2
        _frond(c, top, a, rnd.uniform(18, 24), 4, FROND, 2 + k, 0.65 if back else 1.0, leaflet=3.5, lift=12)
    c.ellipse(top[0], top[1] - 2, 3.5, 4.5, Mat(["#4a2a08", "#8a5418", "#c08030", "#e8b050"]), group=20,
              pattern=lambda xx, yy, nx, ny: np.where((yy.astype(int) % 2) == 0, -1, 0))
    return drop_shadow(c.finish(), dx=6, dy=0, squash=0.3, alpha=90)


def giant_fern(seed):
    rnd = np.random.default_rng(seed)
    w, h = 96, 116
    c = Canvas(w, h)
    bx = w // 2 - 4
    lean = rnd.uniform(-5, 5)
    pts = [(bx + lean * (t / 6) ** 2, h - 6 - t * 9) for t in range(7)]
    c.chain(pts, [3.8, 3.5, 3.3, 3.1, 2.9, 2.8, 2.8], BARK, 1,
            pattern=lambda xx, yy, nx, ny: np.where((yy.astype(int) % 3 == 0) & (xx.astype(int) % 2 == 0), -1, 0))
    top = pts[-1]
    order = sorted(range(11), key=lambda k: math.sin(math.radians(k * 33)))
    for k in order:
        a = math.radians(k * 33 + rnd.uniform(-10, 10))
        back = math.sin(a) < -0.2
        _frond(c, top, a, rnd.uniform(30, 38), 16, FERN, 2 + k, 0.62 if back else 1.0, leaflet=5.0, lift=9)
    for k in range(3):  # unfurling fiddleheads
        fx, fy = top[0] - 3 + k * 3, top[1] - 5
        c.ellipse(fx, fy, 1.6, 1.6, FERN, group=30)
    return drop_shadow(c.finish(), dx=8, dy=0, squash=0.3, alpha=90)


def conifer(seed):
    rnd = np.random.default_rng(seed)
    w, h = 84, 128
    c = Canvas(w, h)
    bx = w // 2 - 4
    c.capsule((bx, h - 6), (bx, 14), 3.6, 1.6, BARK, 1)
    tiers = 7
    for i in range(tiers):
        y = h - 34 - i * 12
        span = 24 - i * 2.6 + rnd.uniform(-2, 2)
        for side in (-1, 1):
            tip = (bx + side * span, y + 3)
            c.capsule((bx, y - 1), tip, 1.0, 0.6, BARK, 2 + i, shade=0.8)
            for t in np.linspace(0.15, 1.0, 6):  # needle tufts along each branch
                px, py = bx + side * span * t, y - 1 + 4 * t
                c.ellipse(px, py, 4.5 - t * 1.5, 2.8, NEEDLE, group=2 + i, shade=0.85 + 0.25 * (i / tiers),
                          pattern=speckle(int(px * 7 + py), 0.25, -1))
    c.ellipse(bx, 14, 4, 6, NEEDLE, group=20, pattern=speckle(seed, 0.25, -1))
    return drop_shadow(c.finish(), dx=8, dy=0, squash=0.28, alpha=90)


def vine_tree(seed):
    rnd = np.random.default_rng(seed + 500)
    base = tree(seed)  # already has its shadow
    w, h = base.size
    c = Canvas(w, h)
    flower = ["#e84a8a", "#ff9ac0", "#f0d040"]
    for k in range(5):
        x0 = rnd.uniform(20, 70)
        y0 = rnd.uniform(52, 62)
        length = rnd.uniform(18, 34)
        pts = [(x0 + math.sin(t * 2.2 + k) * 2.5, y0 + t * length) for t in np.linspace(0, 1, 6)]
        c.chain(pts, [0.9, 0.9, 0.8, 0.7, 0.6, 0.5], Mat(["#14280e", "#24421a", "#386026"]), 1 + k)
        for j, (px, py) in enumerate(pts[1:]):
            c.pixel(px + (1.5 if j % 2 else -1.5), py, "#4e8a32")
            if rnd.random() < 0.3:
                c.pixel(px, py + 1, flower[rnd.integers(0, 3)])
    out = base.copy()
    out.alpha_composite(c.finish(outline=False))
    return out


def stump(seed):
    c = Canvas(40, 32)
    sh = ShadowLayer(40, 32)
    sh.blob(23, 26, 12, 4)
    for dx in (-7, 7):
        c.capsule((18, 24), (18 + dx, 28), 2.6, 1.2, BARK, 1)
    c.capsule((18, 27), (18, 16), 7.5, 7.0, BARK, 1, pattern=lambda xx, yy, nx, ny: np.where(np.sin(xx * 2.0) > 0.6, -1, 0))
    c.ellipse(18, 15, 7.5, 3.4, WOOD_CUT, group=1, round_=0.2,
              pattern=lambda xx, yy, nx, ny: np.where(np.hypot(xx - 18, (yy - 15) * 2.2).astype(int) % 2 == 0, -1, 0))
    c.ellipse(13, 21, 3, 2, MOSS, round_=0.6)
    img = sh.image(90)
    img.alpha_composite(c.finish())
    return img


def log(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(72, 40)
    sh = ShadowLayer(72, 40)
    a, b = (12, 14), (58, 28)
    sh.prism([(a[0], a[1] + 6), (b[0], b[1] + 6)], 8, 0.6, -0.1)
    c.capsule(a, b, 6.5, 6.0, BARK, 1, pattern=lambda xx, yy, nx, ny: np.where(np.sin((xx * 0.3 - yy) * 1.8) > 0.7, -1, 0))
    c.ellipse(b[0] + 1, b[1] + 0.5, 3.5, 6.0, WOOD_CUT, rot=-15, group=2, round_=0.2,
              pattern=lambda xx, yy, nx, ny: np.where(np.hypot((xx - b[0]) * 1.7, yy - b[1]).astype(int) % 2 == 0, -1, 0))
    for k in range(3):
        t = rnd.uniform(0.15, 0.8)
        c.ellipse(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - 5, 4, 2, MOSS, group=3, round_=0.6)
    for k in range(2):  # shelf fungus
        t = rnd.uniform(0.3, 0.7)
        c.ellipse(a[0] + (b[0] - a[0]) * t + 2, a[1] + (b[1] - a[1]) * t + 3, 2.5, 1.2, CAP_TAN, group=4)
    img = sh.image(90)
    img.alpha_composite(c.finish())
    return img


def mushrooms(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(24, 18)
    cap = CAP_RED if seed % 3 == 0 else CAP_TAN
    for k in range(rnd.integers(3, 5)):
        x = 12 + rnd.uniform(-7, 7)
        hgt = rnd.uniform(4, 8)
        c.capsule((x, 15), (x, 15 - hgt), 0.9, 0.8, STEM, k)
        r = rnd.uniform(2.0, 3.2)
        c.ellipse(x, 15 - hgt, r, r * 0.65, cap, group=k, belly_t=0.9)
        if cap is CAP_RED:
            c.pixel(x - 1, 15 - hgt - 0.6, "#fff4e8")
            c.pixel(x + 1, 15 - hgt - 0.2, "#fff4e8")
    return c.finish()


def bones(seed):
    c = Canvas(44, 26)
    sh = ShadowLayer(44, 26)
    sh.blob(24, 20, 16, 4)
    for k in range(5):  # ribs
        x = 10 + k * 5
        c.chain([(x, 20), (x + 2, 12 - abs(k - 2)), (x + 5, 9 - abs(k - 2))], [1.1, 1.0, 0.7], BONE_M, 1 + k)
    c.capsule((8, 20), (36, 20), 1.4, 1.2, BONE_M, 10)  # spine
    c.ellipse(38, 18, 4.5, 3.2, BONE_M, group=11)  # skull
    c.pixel(39, 17.5, "#3a3428")
    c.capsule((39, 20), (44, 21), 1.0, 0.6, BONE_M, 11)
    img = sh.image(80)
    img.alpha_composite(c.finish())
    return img


def pebbles(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(24, 14)
    for k in range(rnd.integers(3, 6)):
        r = rnd.uniform(1.2, 2.6)
        c.ellipse(12 + rnd.uniform(-8, 8), 9 + rnd.uniform(-3, 3), r * 1.3, r, ROCK, round_=0.8)
    return c.finish()


def fern_small(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(40, 28)
    for k in range(7):
        a = math.radians(190 + k * 26 + rnd.uniform(-8, 8))
        _frond(c, (20, 24), a, rnd.uniform(10, 14), 6, FERN, k, 0.85 + 0.15 * (k % 2), leaflet=2.4, lift=6)
    return drop_shadow(c.finish(), dx=3, dy=0, squash=0.25, alpha=70)


def reeds(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(28, 38)
    for k in range(9):
        x0 = 14 + rnd.uniform(-8, 8)
        hgt = rnd.uniform(16, 30)
        lean = rnd.uniform(-4, 4)
        top = (x0 + lean, 35 - hgt)
        c.capsule((x0, 35), top, 0.7, 0.4, REED, k, shade=0.8 + 0.2 * (k % 2))
        if rnd.random() < 0.45:
            c.capsule((top[0] - lean * 0.08, top[1] + 2), (top[0] - lean * 0.15, top[1] + 6), 1.3, 1.3, CATTAIL, k)
    return c.finish()


def water_rock(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(44, 30)
    specs = [(20, 18, 11, 8), (30, 21, 6, 4.5)] if seed % 2 else [(22, 18, 12, 7), (12, 22, 5, 3.5)]
    for x, y, rx, ry in specs:
        c.ellipse(x, y, rx, ry, ROCK, round_=0.85, pattern=speckle(int(x * 3 + y), 0.08, -1),
                  clip=lambda xx, yy, y=y, ry=ry: yy < y + ry * 0.45)
        c.ellipse(x - rx * 0.2, y - ry * 0.5, rx * 0.55, ry * 0.3, MOSS, round_=0.6)
    img = c.finish()
    # foam ring at the waterline
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for x, y, rx, ry in specs:
        d.arc([x - rx - 2, y + ry * 0.45 - 3, x + rx + 2, y + ry * 0.45 + 3], 0, 180, fill=(232, 244, 240, 255))
    return img


def lily(seed):
    rnd = np.random.default_rng(seed)
    c = Canvas(48, 22)
    for k in range(rnd.integers(3, 6)):
        x, y = 24 + rnd.uniform(-14, 14), 12 + rnd.uniform(-4, 4)
        r = rnd.uniform(4.5, 7.0)
        notch = rnd.uniform(0, math.tau)
        c.ellipse(x, y, r, r * 0.5, LILY, group=k, round_=0.3,
                  clip=lambda xx, yy, x=x, y=y, n=notch: np.abs(((np.arctan2((yy - y) * 2, xx - x) - n + math.pi) % math.tau) - math.pi) > 0.35)
    if seed % 2 == 0:
        fx, fy = 24 + rnd.uniform(-8, 8), 10
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 0)):
            c.pixel(fx + dx, fy + dy, "#ff9ac0" if (dx, dy) != (0, 0) else "#ffe080")
    return c.finish()


# ---------------------------------------------------------------------------
# Base props & rubble
# ---------------------------------------------------------------------------
def fence(direction):
    """Log-rail fence segment spanning one tile edge. direction 'a' runs
    down-right (along grid x), 'b' runs up-right (along grid y)."""
    c = Canvas(72, 44)
    sh = ShadowLayer(72, 44)
    if direction == "a":
        p0, p1 = (6, 18), (62, 40)
    else:
        p0, p1 = (6, 40), (62, 18)
    for t in (0.0, 0.5, 1.0):
        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        sh.prism([(x - 1, y), (x + 1, y)], 14, 0.6, -0.1)
    for z in (5, 11):
        sh.prism([p0, p1], 2, 0.6, -0.1)
    for t in (0.0, 0.5, 1.0):
        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        c.capsule((x, y), (x, y - 15), 1.6, 1.4, LOG, 1)
    for z in (5, 11):
        c.capsule((p0[0], p0[1] - z), (p1[0], p1[1] - z), 1.2, 1.2, LOG, 2)
    img = sh.image(80)
    img.alpha_composite(c.finish())
    return img


def lamp():
    c = Canvas(28, 56)
    sh = ShadowLayer(28, 56)
    sh.prism([(12, 52), (15, 52)], 46, 0.5, -0.08)
    c.capsule((13, 52), (13, 12), 1.4, 1.1, METAL, 1)
    c.capsule((13, 13), (19, 12), 0.9, 0.9, METAL, 1)
    c.polygon([(16, 13), (22, 13), (21, 19), (17, 19)], METAL, flat=0.6, group=2)
    c.ellipse(19, 17, 2.2, 2.2, Mat(["#806020", "#f0c040", "#fff0a0", "#ffffff"], spec=1), group=3)
    c.ellipse(13, 52, 3.5, 1.5, STONE, group=4)
    img = sh.image(80)
    img.alpha_composite(c.finish())
    return img


def generator():
    lot = Lot(1, 34, margin=6)
    lot.c = Canvas(lot.w, lot.h)
    lot.sh = ShadowLayer(lot.w, lot.h)
    green = Mat(["#0e2410", "#1a3e1c", "#2a5a2a", "#3e7a3a", "#5a9a50"], spec=0.3)
    lot.box(0.32, 0.22, 0, 12, green, green, tex_corrugated, tex_flat, tex_flat)
    p = lot.g(0.15, -0.1, 12)
    lot.c.capsule(p, (p[0], p[1] - 12), 1.6, 1.4, METAL)  # exhaust stack
    lot.c.ellipse(p[0], p[1] - 12, 1.8, 0.9, METAL, group=lot.c.n - 1)
    q = lot.g(-0.32, 0.0, 6)
    lot.c.polygon([(q[0] + 2, q[1] - 2), (q[0] + 8, q[1] + 1), (q[0] + 8, q[1] + 5), (q[0] + 2, q[1] + 2)], METAL, flat=0.55)
    lot.c.pixel(q[0] + 4, q[1] + 1, "#40ff60")
    lot.c.pixel(q[0] + 6, q[1] + 2, "#ff4040")
    return lot.render(90)


def power_pole():
    c = Canvas(30, 76)
    sh = ShadowLayer(30, 76)
    sh.prism([(13, 72), (16, 72)], 66, 0.45, -0.07)
    c.capsule((14, 72), (14, 8), 1.8, 1.4, LOG, 1)
    c.capsule((5, 12), (23, 12), 1.0, 1.0, LOG, 2)
    for x in (6, 14, 22):
        c.ellipse(x, 10, 1.2, 1.4, Mat(["#606060", "#a0a8b0", "#e0e8f0"], spec=1), group=3)
    img = sh.image(80)
    img.alpha_composite(c.finish())
    return img


def sandbags():
    c = Canvas(48, 26)
    sh = ShadowLayer(48, 26)
    sh.blob(28, 20, 18, 4)
    for row, (y, n) in enumerate(((20, 5), (15, 4), (10, 3))):
        for i in range(n):
            x = 10 + i * 7 + row * 3.5
            c.ellipse(x, y, 4.2, 2.8, SAND_BAG, group=row * 10 + i, pattern=speckle(row * 10 + i, 0.15, -1))
    img = sh.image(85)
    img.alpha_composite(c.finish())
    return img


def fuel_drums():
    lot = Lot(1, 30, margin=6)
    lot.c = Canvas(lot.w, lot.h)
    lot.sh = ShadowLayer(lot.w, lot.h)
    for gx, gy in ((-0.15, -0.1), (0.15, -0.1), (0.0, 0.15)):
        p = lot.g(gx, gy, 0)
        lot.barrel(p[0], p[1], mat=RED_CLOTH, h=11, r=4.5)
    return lot.render(90)


def sign():
    c = Canvas(40, 40)
    sh = ShadowLayer(40, 40)
    sh.prism([(10, 36), (30, 36)], 20, 0.5, -0.08)
    for x in (12, 28):
        c.capsule((x, 36), (x, 16), 1.3, 1.2, LOG, 1)
    c.polygon([(6, 8), (34, 8), (34, 22), (6, 22)], PLANK, flat=0.85, group=2,
              pattern=lambda xx, yy, nx, ny: np.where(yy.astype(int) % 5 == 0, -1, 0))
    # stylised dinosaur footprint emblem (three toes) on the board
    for dx, dy in ((-3, -2), (0, -3), (3, -2)):
        c.pixel(20 + dx, 14 + dy, "#2a5a20")
        c.pixel(20 + dx, 15 + dy, "#2a5a20")
    for dx in (-1, 0, 1):
        c.pixel(20 + dx, 16, "#2a5a20")
        c.pixel(20 + dx, 17, "#2a5a20")
    img = sh.image(80)
    img.alpha_composite(c.finish())
    return img


def rubble(size, dark=False):
    """Collapsed building footprint: scorched ground, debris, broken beams."""
    lot = Lot(size, 26, margin=8)
    c = lot.c
    rnd = np.random.default_rng(size * 13 + (7 if dark else 0))
    scorch = Mat(["#141210", "#221e1a", "#322c24", "#463e32", "#5a5040"])
    lot.ground(scorch, size * 0.48, pattern=speckle(size + 3, 0.3, -1))
    debris_mats = [STONE, PLANK, METAL if dark else LOG, CONCRETE if not dark else RUST]
    for _ in range(14 * size):
        gx, gy = rnd.uniform(-0.42, 0.42, 2) * size
        x, y = lot.g(gx, gy, 0)
        m = debris_mats[rnd.integers(0, len(debris_mats))]
        if rnd.random() < 0.55:
            c.ellipse(x, y - 2, rnd.uniform(2.5, 5.0), rnd.uniform(1.6, 3.0), m, group=c.n, round_=0.8)
        else:
            L = rnd.uniform(6, 14)
            a = rnd.uniform(0, math.tau)
            c.capsule((x, y - 2), (x + math.cos(a) * L, y - 2 + math.sin(a) * L * 0.5 - rnd.uniform(0, 6)), 1.4, 1.1, m)
    for _ in range(2 + size):  # a few beams still standing at an angle
        gx, gy = rnd.uniform(-0.3, 0.3, 2) * size
        x, y = lot.g(gx, gy, 0)
        c.capsule((x, y), (x + rnd.uniform(-8, 8), y - rnd.uniform(10, 18)), 1.8, 1.4, LOG if not dark else METAL)
    return lot.render(70)


def egg_cage():
    """A poacher cage of stolen eggs on a straw bed."""
    lot = Lot(2, 52)
    c = lot.c
    lot.ground(DIRT_PAD, 0.95, pattern=speckle(17, 0.2, -1))
    lot.box(0.72, 0.72, 0, 4, PLANK, PLANK, tex_planks_h, tex_planks_h, tex_planks_v)
    cx, cy = lot.g(0, 0, 4)
    c.ellipse(cx, cy, 30, 13, STRAW, round_=0.4, pattern=speckle(41, 0.3, -1))
    for ex, ey, r in ((-12, -3, 7), (2, -6, 8), (14, -1, 7), (-3, 4, 7)):
        c.ellipse(cx + ex, cy + ey - r * 0.6, r * 0.8, r, EGG, pattern=speckle(int(ex * 5 + 300), 0.07, -2))
    T, R, B, L = lot.diamond(0.72, 0.72, 4)
    top = [(x, y - 34) for x, y in (T, R, B, L)]
    for p0, p1 in ((L, B), (B, R), (T, R), (L, T)):
        for t in np.linspace(0, 1, 8):
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            c.line((x, y), (x, y - 34), shade_hex(METAL, 3 if (p0, p1) in ((L, B), (B, R)) else 1))
    for a, b in ((top[3], top[2]), (top[2], top[1]), (top[0], top[1]), (top[3], top[0])):
        c.capsule(a, b, 1.0, 1.0, METAL)
    lot.sh.prism([L, B, R, T], 36)
    # padlock and a red warning tag
    lx, ly = (L[0] + B[0]) / 2, (L[1] + B[1]) / 2 - 16
    c.ellipse(lx, ly, 2.4, 2.0, Mat(["#5a4a10", "#a88a20", "#e8c040", "#fff080"], spec=1))
    c.polygon([(lx + 4, ly - 6), (lx + 10, ly - 3), (lx + 10, ly + 1), (lx + 4, ly - 2)], RED_CLOTH, flat=0.8)
    return lot.render()
