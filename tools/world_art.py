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
    out["grass"] = g

    j = quantise(n2 * 0.6 + n1 * 0.4, ["#1c2a12", "#243616", "#2e441a", "#38501e", "#445c24"], 0.9)
    _blobs(j, rnd, 70, [("#4a3a1c", "#6a5428"), ("#3a4a18", "#566a22"), ("#2a2412", "#423a1c")], (1.5, 3.5), (1, 2))
    _blades(j, rnd, 160, ["#3e6a22", "#4c7e28", "#24401a"], 2, 4)
    out["jungle"] = j

    yy, xx = np.mgrid[0:TEX, 0:TEX]
    ripple = (np.sin((yy + n1 * 10) * (2 * math.pi / 8) + xx * (2 * math.pi / 64)) + 1) / 2
    s = quantise(0.45 + ripple * 0.25 + (n2 - 0.5) * 0.4, ["#b89c5c", "#c8ae6c", "#d6be7c", "#e2cc8c", "#ecd89c"], 0.8)
    _blobs(s, rnd, 14, [("#a08a5a", "#f4ecd8"), ("#8a7a5a", "#c8b898")], (0.8, 1.6), (0.6, 1.0))
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
