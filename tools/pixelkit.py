"""Tiny pixel-art rendering kit used by gen_sprites.py.

Shapes are rasterised as shaded *volumes*: every primitive produces a surface
normal per pixel, which is lit by a single sun (upper-left, toward the viewer)
and then quantised onto a hand-picked colour ramp with ordered (Bayer)
dithering. The result looks like hand-shaded pixel art: round forms, belly
counter-shading, patterns and coloured selective outlines.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
LIGHT = np.array([-0.55, -0.75, 0.62])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
DITHER = 0.55  # width of the dithered band between two ramp colours


def hexrgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class Mat:
    """A material: a dark->light colour ramp plus optional extras."""

    def __init__(self, ramp, belly=None, spec=0.0, ambient=0.28, outline=None):
        self.ramp = [hexrgb(c) for c in ramp]
        self.belly = [hexrgb(c) for c in belly] if belly else None
        self.spec = spec
        self.ambient = ambient
        self.outline = hexrgb(outline) if outline else tuple(int(v * 0.55) for v in self.ramp[0])


def shift(arr, dy, dx, fill=0):
    """Shift an array by (dy, dx) without wrapping around the edges."""
    out = np.full_like(arr, fill)
    h, w = arr.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = arr[ys, xs]
    return out


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.rgb = np.zeros((h, w, 3), np.uint8)
        self.a = np.zeros((h, w), np.uint8)
        self.part = np.full((h, w), -1, np.int32)
        self.group = np.full((h, w), -1, np.int32)
        self.outline_col = np.zeros((h, w, 3), np.uint8)
        self.n = 0
        yy, xx = np.mgrid[0:h, 0:w]
        self.xx = xx + 0.5
        self.yy = yy + 0.5

    # ------------------------------------------------------------------
    def _commit(self, mask, nx, ny, nz, mat, group, shade=1.0, pattern=None, belly_t=0.35, flat=None):
        if not mask.any():
            return
        if flat is not None:
            v = np.broadcast_to(np.asarray(flat, np.float32), mask.shape)
        else:
            diff = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
            v = mat.ambient + (1 - mat.ambient) * diff
            # soft rim light from behind-right keeps silhouettes readable
            v += 0.12 * np.clip(nx * 0.8 - nz * 0.2, 0, 1) ** 2
        v = v * shade
        ramp = np.array(mat.ramp, np.float32)
        use_belly = None
        if mat.belly is not None:
            use_belly = ny > belly_t
        alt = np.zeros(mask.shape, np.int32)
        if pattern is not None:
            alt = pattern(self.xx, self.yy, nx, ny).astype(np.int32)
        n = len(ramp)
        t = np.clip(v, 0, 1) * (n - 1)
        base = np.floor(t)
        frac = t - base
        thr = 0.5 + (BAYER[(self.yy.astype(int) % 4), (self.xx.astype(int) % 4)] - 0.5) * DITHER
        idx = (base + (frac > thr)).astype(np.int32) + alt
        idx = np.clip(idx, 0, n - 1)
        col = ramp[idx]
        if use_belly is not None:
            bramp = np.array(mat.belly, np.float32)
            bidx = np.clip(idx, 0, len(bramp) - 1)
            bcol = bramp[bidx]
            col = np.where(use_belly[..., None], bcol, col)
        if mat.spec > 0 and flat is None:
            h = np.array([LIGHT[0], LIGHT[1], LIGHT[2] + 1.0])
            h = h / np.linalg.norm(h)
            s = np.clip(nx * h[0] + ny * h[1] + nz * h[2], 0, 1) ** 24 * mat.spec
            col = np.where((s > 0.5)[..., None], np.minimum(255, col * 0.3 + 255 * 0.7), col)
        m = mask
        self.rgb[m] = col[m].astype(np.uint8)
        self.a[m] = 255
        self.part[m] = self.n
        self.group[m] = group if group is not None else self.n
        self.outline_col[m] = mat.outline
        self.n += 1

    # ------------------------------------------------------------------
    def ellipse(self, cx, cy, rx, ry, mat, rot=0.0, group=None, shade=1.0, pattern=None, round_=1.0, belly_t=0.35, clip=None):
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        dx, dy = self.xx - cx, self.yy - cy
        u = (dx * c + dy * s) / rx
        v = (-dx * s + dy * c) / ry
        r2 = u * u + v * v
        mask = r2 <= 1.0
        if clip is not None:
            mask &= clip(self.xx, self.yy)
        nz = np.sqrt(np.clip(1 - r2, 0, 1))
        lu, lv = u * round_, v * round_
        nx = lu * c - lv * s
        ny = lu * s + lv * c
        norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
        self._commit(mask, nx / norm, ny / norm, nz / norm, mat, group, shade, pattern, belly_t)

    def capsule(self, p0, p1, r0, r1, mat, group=None, shade=1.0, pattern=None, belly_t=0.35):
        x0, y0 = p0
        x1, y1 = p1
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy + 1e-9
        t = np.clip(((self.xx - x0) * vx + (self.yy - y0) * vy) / L2, 0, 1)
        px, py = x0 + t * vx, y0 + t * vy
        ox, oy = self.xx - px, self.yy - py
        r = r0 + (r1 - r0) * t
        d = np.sqrt(ox * ox + oy * oy)
        mask = d <= r + 0.15
        nx, ny = ox / (r + 1e-6), oy / (r + 1e-6)
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
        self._commit(mask, nx, ny, nz, mat, group, shade, pattern, belly_t)

    def chain(self, pts, radii, mat, group=None, shade=1.0, pattern=None, belly_t=0.35):
        g = group if group is not None else self.n
        for i in range(len(pts) - 1):
            self.capsule(pts[i], pts[i + 1], radii[i], radii[i + 1], mat, g, shade, pattern, belly_t)

    def polygon(self, pts, mat, normal=(0.0, -0.3, 0.95), group=None, shade=1.0, pattern=None, flat=None):
        img = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(img).polygon([(float(x), float(y)) for x, y in pts], fill=255)
        mask = np.array(img) > 0
        n = np.array(normal, np.float32)
        n = n / np.linalg.norm(n)
        nx = np.full(mask.shape, n[0], np.float32)
        ny = np.full(mask.shape, n[1], np.float32)
        nz = np.full(mask.shape, n[2], np.float32)
        self._commit(mask, nx, ny, nz, mat, group, shade, pattern, flat=flat)

    def face(self, o, eu, ev, mat, light=1.0, tex=None, group=None, pattern=None, clip=None):
        """Textured parallelogram o + u*eu + v*ev (u, v in 0..1).

        tex(u_px, v_px) returns a brightness multiplier per pixel, where
        u_px/v_px are distances in pixels along the two edges."""
        pts = [o, (o[0] + eu[0], o[1] + eu[1]), (o[0] + eu[0] + ev[0], o[1] + eu[1] + ev[1]), (o[0] + ev[0], o[1] + ev[1])]
        img = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(img).polygon([(float(x), float(y)) for x, y in pts], fill=255)
        mask = np.array(img) > 0
        if clip is not None:
            mask &= clip(self.xx, self.yy)
        det = eu[0] * ev[1] - eu[1] * ev[0]
        dx, dy = self.xx - o[0], self.yy - o[1]
        u = (dx * ev[1] - dy * ev[0]) / det
        v = (eu[0] * dy - eu[1] * dx) / det
        up = u * math.hypot(*eu)
        vp = v * math.hypot(*ev)
        val = np.full(mask.shape, light, np.float32)
        if tex is not None:
            val = val * tex(up, vp)
        self._commit(mask, None, None, None, mat, group, 1.0, pattern, flat=np.clip(val, 0, 1))
        return pts

    def pixel(self, x, y, color, group=-2):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.rgb[y, x] = hexrgb(color) if isinstance(color, str) else color
            self.a[y, x] = 255
            self.part[y, x] = self.n
            self.group[y, x] = group
            self.n += 1

    def line(self, p0, p1, color):
        steps = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
        for i in range(steps + 1):
            t = i / steps
            self.pixel(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, color)

    # ------------------------------------------------------------------
    def finish(self, outline=True, inner=True):
        rgb = self.rgb.copy()
        a = self.a.copy()
        if inner:
            # Darken the edge of a part that is overlapped by a part in front
            # of it (different group), like hand-drawn contour lines.
            part, group = self.part, self.group
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nb_part = shift(part, dy, dx, -1)
                nb_group = shift(group, dy, dx, -1)
                edge = (a > 0) & (nb_part > part) & (nb_group != group) & (nb_part >= 0) & (group != -2) & (nb_group != -2)
                rgb[edge] = (rgb[edge] * 0.62).astype(np.uint8)
        if outline:
            out = np.zeros_like(a, bool)
            ocol = np.zeros_like(rgb)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nb_a = shift(self.a, dy, dx)
                nb_c = shift(self.outline_col, dy, dx)
                hit = (self.a == 0) & (nb_a > 0) & ~out
                ocol[hit] = nb_c[hit]
                out |= hit
            rgb[out] = ocol[out]
            a[out] = 255
        img = np.dstack([rgb, a])
        return Image.fromarray(img, "RGBA")


# ----------------------------------------------------------------------
# misc helpers
# ----------------------------------------------------------------------
def ik2(hip, target, l1, l2, bend=1):
    """Two-bone IK. Returns the joint position. bend=+1 puts the joint forward (+x)."""
    hx, hy = hip
    tx, ty = target
    dx, dy = tx - hx, ty - hy
    d = max(1e-3, min(math.hypot(dx, dy), l1 + l2 - 1e-3))
    a = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    base = math.atan2(dy, dx)
    j1 = (hx + l1 * math.cos(base - a), hy + l1 * math.sin(base - a))
    j2 = (hx + l1 * math.cos(base + a), hy + l1 * math.sin(base + a))
    return j1 if (j1[0] - j2[0]) * bend > 0 else j2


def stripes(freq, phase=0.0, width=0.25, only_up=True, shift=-1):
    def f(xx, yy, nx, ny):
        s = np.sin(xx * freq + phase + yy * 0.25)
        m = s > (1 - width * 2)
        if only_up:
            m &= ny < 0.15
        return np.where(m, shift, 0)
    return f


def speckle(seed, density=0.08, shift=-1):
    rnd = np.random.default_rng(seed)
    cache = {}

    def f(xx, yy, nx, ny):
        key = xx.shape
        if key not in cache:
            cache[key] = rnd.random(xx.shape)
        return np.where(cache[key] < density, shift, 0)
    return f


def combine(*fs):
    def f(xx, yy, nx, ny):
        out = 0
        for g in fs:
            out = out + g(xx, yy, nx, ny)
        return out
    return f


def drop_shadow(img, dx=6, dy=2, squash=0.35, alpha=90):
    """Bake a dithered ground shadow (cast down-right) under a sprite.

    The silhouette is squashed vertically and sheared to the right from its
    base line, then drawn as a 50% checker of translucent black behind it."""
    src = np.array(img)
    h, w = src.shape[:2]
    sil = src[..., 3] > 0
    rows = np.where(sil.any(axis=1))[0]
    if len(rows) == 0:
        return img
    base = rows.max()
    out = np.zeros_like(src)
    ys, xs = np.nonzero(sil)
    height = base - ys
    ny = (base - height * squash + dy).astype(int)
    nx = (xs + height * 0.9 * squash * 2 + dx).astype(int)
    ok = (nx >= 0) & (nx < w) & (ny >= 0) & (ny < h)
    shadow = np.zeros((h, w), bool)
    shadow[ny[ok], nx[ok]] = True
    # close small gaps
    shadow |= shift(shadow, 0, 1) & shift(shadow, 0, -1)
    shadow |= shift(shadow, 1, 0) & shift(shadow, -1, 0)
    out[shadow] = (8, 12, 6, alpha)
    res = Image.fromarray(out, "RGBA")
    res.alpha_composite(img)
    return res


# ----------------------------------------------------------------------
# shadows & noise
# ----------------------------------------------------------------------
def convex_hull(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


class ShadowLayer:
    """Accumulates soft ground shadows (dithered, translucent)."""

    def __init__(self, w, h):
        self.mask = Image.new("L", (w, h), 0)
        self.d = ImageDraw.Draw(self.mask)

    def prism(self, base_pts, height, sx=0.75, sy=-0.12):
        """Shadow cast by a vertical prism standing on base_pts."""
        off = [(x + height * sx, y + height * sy) for x, y in base_pts]
        self.d.polygon(convex_hull(list(base_pts) + off), fill=255)

    def blob(self, cx, cy, rx, ry):
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)

    def image(self, alpha=110):
        m = np.array(self.mask) > 0
        h, w = m.shape
        yy, xx = np.mgrid[0:h, 0:w]
        # soften edges with a dithered fringe
        edge = m & ~(shift(m, 1, 0) & shift(m, -1, 0) & shift(m, 0, 1) & shift(m, 0, -1))
        a = np.where(m, alpha, 0).astype(np.uint8)
        a[edge & ((xx + yy) % 2 == 0)] = 0
        out = np.zeros((h, w, 4), np.uint8)
        out[..., 0:3] = (10, 16, 8)
        out[..., 3] = a
        return Image.fromarray(out, "RGBA")


def tile_noise(n, period, seed, octaves=3):
    """Seamless value noise in [0, 1] of size n x n."""
    rnd = np.random.default_rng(seed)
    total = np.zeros((n, n), np.float32)
    amp, norm = 1.0, 0.0
    p = period
    for _ in range(octaves):
        g = rnd.random((p, p)).astype(np.float32)
        coords = np.arange(n) * p / n
        i0 = np.floor(coords).astype(int) % p
        i1 = (i0 + 1) % p
        f = coords - np.floor(coords)
        f = f * f * (3 - 2 * f)
        a = g[i0][:, i0] * (1 - f)[None, :] + g[i0][:, i1] * f[None, :]
        b = g[i1][:, i0] * (1 - f)[None, :] + g[i1][:, i1] * f[None, :]
        layer = a * (1 - f)[:, None] + b * f[:, None]
        total += layer * amp
        norm += amp
        amp *= 0.5
        p *= 2
    return total / norm


def quantise(values, ramp, dither=0.6):
    """Map a float array (0..1) onto a colour ramp with ordered dithering."""
    h, w = values.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ramp = np.array([hexrgb(c) if isinstance(c, str) else c for c in ramp], np.float32)
    n = len(ramp)
    t = np.clip(values, 0, 1) * (n - 1)
    base = np.floor(t)
    thr = 0.5 + (BAYER[yy % 4, xx % 4] - 0.5) * dither
    idx = np.clip((base + ((t - base) > thr)).astype(int), 0, n - 1)
    return ramp[idx].astype(np.uint8)
