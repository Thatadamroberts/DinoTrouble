"""Unit sprite rigs (dinosaurs, humans, vehicles) for gen_sprites.py.

Every unit is a small parametric rig drawn with pixelkit primitives. A sheet
has FRAMES columns, all facing right:
    0-1  idle (breathing)   2-7  walk cycle   8-10  attack   11-12  death
"""
import math

import numpy as np

from pixelkit import Canvas, Mat, ScaledCanvas, combine, ik2, scales, speckle, stripes, wrinkles

FRAMES = 13
CLAW = "#ece6d0"


def draw_eye(c, ex, ey, col, dead, brow):
    """Eye with pupil, a catch-light and a darker brow ridge above it."""
    if dead == 2:
        c.pixel(ex, ey, "#2a1a10")
        c.pixel(ex + 1, ey, "#2a1a10")
        return
    c.pixel(ex - 1, ey - 1, brow)
    c.pixel(ex, ey - 1, brow)
    c.pixel(ex + 1, ey - 1, brow)
    c.pixel(ex, ey, col)
    c.pixel(ex + 1, ey, "#120c06")
    c.pixel(ex + 0.2, ey - 0.2, "#fffbe8")
IDLE = (0, 1)
WALK = tuple(range(2, 8))
ATTACK = (8, 9, 10)
DEATH = (11, 12)


def pose(frame):
    """Common animation parameters for a frame."""
    p = {"phase": 0.0, "walk": False, "breath": 0.0, "attack": -1, "dead": 0}
    if frame in IDLE:
        p["breath"] = 0.5 if frame == 1 else 0.0
    elif frame in WALK:
        p["walk"] = True
        p["phase"] = (frame - WALK[0]) / len(WALK) * math.tau
    elif frame in ATTACK:
        p["attack"] = frame - ATTACK[0]
    else:
        p["dead"] = frame - DEATH[0] + 1
    return p


def leg_target(hip_x, ground, phase, stride, lift, offset=0.0):
    ph = phase + offset
    fx = hip_x + stride * math.sin(ph)
    up = max(0.0, math.cos(ph))
    return fx, ground - lift * up


# ---------------------------------------------------------------------------
# Biped dinosaur rig (raptor, dilophosaurus, T. rex)
# ---------------------------------------------------------------------------
def biped(w, h, frame, spec):
    p = pose(frame)
    s = spec["scale"]
    c = ScaledCanvas(w, h, spec.get("k", 1.0))
    skin, far_skin = spec["skin"], spec["skin"]
    ground = h - 3
    bob = 0.0
    if p["walk"]:
        bob = -abs(math.sin(p["phase"])) * 1.2 * s
    bob += p["breath"] * 0.6
    dead = p["dead"]
    drop = ground - spec["hip"][1] * s - spec["thigh_r"] * s * 0.8
    lean = {0: 0.0, 1: 0.5, 2: 1.0}.get(dead, 0) * drop / 1.4

    hip = (spec["hip"][0] * s, spec["hip"][1] * s + bob + lean * 1.4)
    body_c = (hip[0] + 6 * s, hip[1] - 1 * s)
    body_rot = spec.get("body_rot", -8) + (8 if dead else 0) + (4 if p["attack"] == 1 else 0)
    pat = spec.get("pattern")

    # tail
    sway = math.sin(p["phase"] * 1.0 + 1.0) * 1.5 * s if p["walk"] else math.sin(p["breath"] * 3) * 0.5
    tail = [hip, (hip[0] - 9 * s, hip[1] - 1 * s + sway * 0.4 + lean * 0.3),
            (hip[0] - 18 * s, hip[1] - 1.5 * s + sway + lean * 0.6), (hip[0] - 27 * s, hip[1] - 1 * s + sway * 1.6 + lean)]
    tr = spec["tail_r"]
    tr = [tr[0] * s, tr[1] * s, tr[2] * s, 0.8]

    # legs
    L1, L2 = spec["thigh"] * s, spec["shin"] * s
    stride, lift = spec["stride"] * s, 3.0 * s

    def leg(offset, shade, group):
        if dead:
            ankle = (hip[0] + (6 + offset * 2) * s, ground - 2 - (0 if dead == 2 else 3 * s))
            knee = (hip[0] + 5 * s, hip[1] + 3 * s)
        elif p["walk"]:
            fx, fy = leg_target(hip[0] + 1 * s, ground, p["phase"], stride, lift, offset)
            ankle = (fx - 2 * s, fy - 4 * s)
            knee = ik2((hip[0], hip[1] + 2 * s), ankle, L1, L2, bend=1)
        else:
            spread = 3 * s if offset else -2 * s
            ankle = (hip[0] + spread, ground - 4 * s)
            knee = ik2((hip[0], hip[1] + 2 * s), ankle, L1, L2, bend=1)
        toe = (ankle[0] + 4.5 * s, min(ground, ankle[1] + 4 * s))
        if spec.get("drumstick"):
            mx, my = (hip[0] + knee[0]) / 2, (hip[1] + knee[1]) / 2
            ang = math.degrees(math.atan2(knee[1] - hip[1], knee[0] - hip[0]))
            tg = 2 if group == 6 else group  # near thigh blends into the body outline
            c.ellipse(mx, my - 1 * s, L1 * 0.62, spec["thigh_r"] * s, skin, rot=ang, group=tg, shade=shade, pattern=pat)
        else:
            c.capsule((hip[0], hip[1] + 1 * s), knee, spec["thigh_r"] * s, spec["thigh_r"] * 0.6 * s, skin, group, shade)
        sr = spec.get("shin_r", (0.5, 1.3, 0.9))
        c.capsule(knee, ankle, spec["thigh_r"] * sr[0] * s, sr[1] * s, skin, group, shade, pattern=pat)
        c.capsule(ankle, toe, sr[1] * s, sr[2] * s, skin, group, shade)
        c.pixel(toe[0] + 1.0, toe[1] - 0.3, CLAW)
        c.pixel(toe[0] + 0.3, toe[1] + 0.2, CLAW if shade > 0.9 else "#a8a28c")
        if spec.get("sickle"):
            c.pixel(ankle[0] + 2 * s, ankle[1] + 1, CLAW)
            c.pixel(ankle[0] + 2.6 * s, ankle[1] + 0.3, CLAW)

    leg(math.pi, 0.72, 1)  # far leg

    c.chain(tail, tr, skin, 2, pattern=pat)
    c.ellipse(body_c[0], body_c[1], spec["body"][0] * s, spec["body"][1] * s, skin, rot=body_rot, group=2, pattern=pat)

    # neck & head
    ha = spec.get("head_up", 0)
    atk = p["attack"]
    lunge = {0: 1.5, 1: 4.0, 2: 2.0}.get(atk, 0.0) * s
    nb = (body_c[0] + spec["body"][0] * 0.7 * s, body_c[1] - spec["body"][1] * 0.3 * s)
    neck_top = (nb[0] + spec["neck"][0] * s + lunge, nb[1] - spec["neck"][1] * s + (lunge * 0.4) + p["breath"] * 0.4)
    if dead:
        neck_top = (nb[0] + spec["neck"][0] * s, ground - spec["head"][1] * s - 1 - (2 * s if dead == 1 else 0))
    c.capsule(nb, neck_top, spec["neck_r"][0] * s, spec["neck_r"][1] * s, skin, 2, pattern=pat)
    p["nb"], p["neck_top"] = nb, neck_top

    hx, hy = neck_top[0] + spec["head"][0] * 0.6 * s, neck_top[1] - 0.5 * s
    head_rot = spec.get("head_rot", 8) + (10 if atk == 1 else 0) - ha
    jaw = {0: 0.25, 1: 1.0, 2: 0.4}.get(atk, 0.0) * spec["jaw"] * s
    if dead:
        head_rot = 12
        jaw = 0.6 * spec["jaw"] * s
    # lower jaw first so the upper skull overlaps it
    jr = math.radians(head_rot + 18 * (jaw / max(0.1, spec["jaw"] * s)))
    jl = spec["head"][0] * 1.7 * s
    jaw_end = (hx + math.cos(jr) * jl * 0.95, hy + 1.5 * s + math.sin(jr) * jl * 0.95)
    c.capsule((hx - 1 * s, hy + 1.2 * s), jaw_end, spec["jaw_r"] * s, spec["jaw_r"] * 0.55 * s, skin, 3, shade=0.85)
    if jaw > 0.5 * s:
        mouth = spec.get("mouth", "#7a2a2a")
        c.capsule((hx, hy + 0.8 * s), (jaw_end[0] - 1, jaw_end[1] - 1.2 * s), 0.9 * s, 0.6 * s, Mat([mouth, mouth]), 4)
    c.ellipse(hx, hy, spec["head"][0] * s, spec["head"][1] * s, skin, rot=head_rot, group=3, belly_t=0.6)
    hr = math.radians(head_rot)
    snout_end = (hx + math.cos(hr) * spec["snout"] * s, hy + math.sin(hr) * spec["snout"] * s + 0.3 * s)
    c.capsule((hx, hy), snout_end, spec["head"][1] * 0.85 * s, spec["head"][1] * 0.5 * s, skin, 3, belly_t=0.6)
    lip = spec["head"][1] * 0.5 * s + 0.5
    if jaw > 0.5 * s:
        for i in range(1, 7):
            t = i / 7
            tx = hx + (snout_end[0] - hx) * t
            c.pixel(tx, hy + (snout_end[1] - hy) * t + lip, "#f2eedc")
            c.pixel(tx + 0.5, hy + (jaw_end[1] - hy) * t + 0.4, "#e4dcc4")
    elif spec.get("teeth"):
        for i in range(2, 7):
            t = i / 7
            tx = hx + (snout_end[0] - hx) * t
            c.pixel(tx, hy + (snout_end[1] - hy) * t + lip + 0.6, "#ece4cc")
    c.line((hx - 1 * s, hy + lip), (snout_end[0] - 0.5 * s, snout_end[1] + lip * 0.6), spec["skin"].ramp[0])
    # eye
    ex, ey = hx + spec["eye"][0] * s, hy + spec["eye"][1] * s
    draw_eye(c, ex, ey, spec.get("eye_col", "#f0c020"), dead, spec["skin"].ramp[1])
    c.pixel(snout_end[0] - 1 * s, snout_end[1] - spec["head"][1] * 0.4 * s, spec["skin"].ramp[0])  # nostril

    p["jaw_end"], p["snout_end"] = jaw_end, snout_end
    if "head_extra" in spec:
        spec["head_extra"](c, hx, hy, head_rot, s, p)

    # arms
    sh = (body_c[0] + spec["body"][0] * 0.55 * s, body_c[1] + spec["body"][1] * 0.35 * s)
    ar = spec["arm"] * s
    swing = math.sin(p["phase"]) * 1.0 if p["walk"] else (1.5 if atk == 1 else 0.0)
    elbow = (sh[0] + ar * 0.5, sh[1] + ar * 0.6 + swing * 0.3)
    hand = (elbow[0] + ar * 0.5 + swing * 0.3, elbow[1] - ar * 0.1)
    c.capsule(sh, elbow, 1.3 * s, 1.0 * s, skin, 5, shade=0.9)
    c.capsule(elbow, hand, 1.0 * s, 0.7 * s, skin, 5, shade=0.9)
    c.pixel(hand[0] + 1, hand[1] + 1, CLAW)
    c.pixel(hand[0] + 1.6, hand[1] + 0.2, CLAW)
    p["hand"], p["elbow"], p["sh"] = hand, elbow, sh

    leg(0.0, 1.0, 6)  # near leg
    if "body_extra" in spec:
        spec["body_extra"](c, hip, body_c, s, p)
    return c.finish()


def crest(c, hx, hy, rot, s, p):
    red = Mat(["#5a1410", "#8a2418", "#c03a22", "#e86a3a", "#ff9a60"])
    nt = p.get("neck_top")
    if nt:  # throat pouch
        c.ellipse(nt[0] + 1.5 * s, nt[1] + 2.5 * s, 2.6 * s, 2.0 * s, Mat(["#5a4a20", "#9a8a40", "#d0c060", "#ece08a"]), group=6, belly_t=0.9)
    for k, dx in enumerate((-1.0, 1.0)):
        base = (hx - 1 * s + dx * 0.8, hy - 2 * s)
        c.polygon([base, (base[0] + 2 * s, base[1] - 5 * s), (base[0] + 6 * s, base[1] - 3.5 * s), (base[0] + 5 * s, base[1])],
                  red, normal=(-0.3 + k * 0.4, -0.5, 0.8), group=7 + k,
                  pattern=lambda xx, yy, nx, ny: np.where((xx * 1.3 + yy * 0.6).astype(int) % 3 == 0, -1, 0))
    if p["attack"] >= 0:  # neck frill flares open when spitting
        frill = Mat(["#6a3a10", "#b0601a", "#e8a020", "#f8d050"])
        cx, cy = hx - 3 * s, hy + 1 * s
        pts = [(cx + math.cos(a) * 7 * s, cy + math.sin(a) * 6 * s) for a in [math.radians(d) for d in range(100, 271, 15)]]
        c.polygon([(cx, cy)] + pts, frill, normal=(0.1, -0.2, 1), group=9,
                  pattern=lambda xx, yy, nx, ny: ((xx - cx) * 2.1 + (yy - cy) * 0.3).astype(int) % 3 == 0)


def raptor_quills(c, hip, body_c, s, p):
    q = Mat(["#2a180a", "#4e3216", "#7a5226", "#a07034"])
    for i in range(6):
        x = body_c[0] - 8 * s + i * 2.8 * s
        y = body_c[1] - 5.5 * s + abs(i - 2.5) * 0.5
        c.capsule((x, y), (x - 2.8 * s, y - 2.4 * s), 0.8, 0.35, q, 11)
    nb, nt = p.get("nb"), p.get("neck_top")
    if nb and nt:
        for t in (0.2, 0.45, 0.7):
            x, y = nb[0] + (nt[0] - nb[0]) * t, nb[1] + (nt[1] - nb[1]) * t - 2.2 * s
            c.capsule((x, y), (x - 2.4 * s, y - 1.6 * s), 0.7, 0.3, q, 12)
    el, hd = p.get("elbow"), p.get("hand")
    if el and hd:
        for t in (0.3, 0.7):
            x, y = el[0] + (hd[0] - el[0]) * t, el[1] + (hd[1] - el[1]) * t
            c.capsule((x, y), (x - 2.0 * s, y + 2.2 * s), 0.6, 0.3, q, 13)


RAPTOR = {
    "scale": 1.0, "hip": (24, 22), "body": (11, 6.5), "body_rot": -10,
    "tail_r": (4.5, 3.0, 1.6), "thigh": 7, "shin": 7, "thigh_r": 4.6, "stride": 6, "drumstick": True,
    "neck": (6, 7), "neck_r": (3.6, 2.6), "head": (5, 3.2), "head_rot": 6, "snout": 7, "jaw": 1.6, "jaw_r": 1.4,
    "eye": (1.5, -1.5), "arm": 5, "sickle": True,
    "skin": Mat(["#3e2814", "#6a4a24", "#9a7038", "#c49a58", "#e2c488"], belly=["#6a5a40", "#a89470", "#d8c8a0", "#f0e4c0", "#fff6dc"]),
    "pattern": combine(stripes(0.9, width=0.22, shift=-1), speckle(3, 0.05), scales(1, -1, 0.6)),
    "body_extra": raptor_quills, "k": 1.3, "teeth": True,
}

DILO = {
    "scale": 1.0, "hip": (24, 28), "body": (11, 7), "body_rot": -12,
    "tail_r": (4.5, 3.0, 1.6), "thigh": 8, "shin": 8, "thigh_r": 4.8, "stride": 6, "drumstick": True,
    "neck": (7, 10), "neck_r": (3.6, 2.4), "head": (5, 3.0), "head_rot": 4, "snout": 7, "jaw": 1.4, "jaw_r": 1.3,
    "eye": (1.5, -1.2), "arm": 5, "mouth": "#3a6a1a",
    "skin": Mat(["#1e3414", "#365a22", "#58862e", "#84b23e", "#b8d868"], belly=["#5a5a28", "#9a9a48", "#d0c870", "#ece4a0", "#fff8cc"]),
    "pattern": combine(speckle(7, 0.12, -1), stripes(0.7, 1.0, 0.18, shift=-1)),
    "head_extra": crest, "k": 1.3,
}


TREX_SKIN = Mat(["#16160e", "#2a2a18", "#443f24", "#625a32", "#847744", "#a8985a"],
                belly=["#3e3626", "#6a5e44", "#968866", "#bcae88", "#dcd0a8", "#f0e6c4"])


def trex_head(c, hx, hy, rot, s, p):
    # heavy jaw muscles and a brow ridge give the skull its boxy look
    c.ellipse(hx - 3 * s, hy + 1.5 * s, 6.5 * s, 6 * s, TREX_SKIN, rot=rot, group=3, belly_t=0.55,
              pattern=wrinkles(1.6, -1, axis_x=False))
    c.capsule((hx - 2 * s, hy - 5 * s), (hx + 5 * s, hy - 4.2 * s), 1.6 * s, 1.2 * s, TREX_SKIN, 3, shade=1.1)
    c.capsule((hx - 5 * s, hy + 6 * s), (hx + 1 * s, hy + 7.5 * s), 2.2 * s, 1.4 * s, TREX_SKIN, 3, shade=0.8,
              pattern=wrinkles(2.0, -1))  # throat wattle
    for i in range(4):  # old scar across the snout
        c.pixel(hx + (5 + i * 1.2) * s, hy - (1.8 - i * 0.7) * s, "#c8a888")


TREX = {
    "scale": 1.0, "hip": (42, 40), "body": (17, 12), "body_rot": -14, "drumstick": True,
    "tail_r": (10, 6.5, 3.2), "thigh": 13, "shin": 12, "thigh_r": 8.5, "stride": 8,
    "neck": (9, 11), "neck_r": (8.0, 6.5), "head": (11, 7.0), "head_rot": 8, "snout": 13, "jaw": 4.5, "jaw_r": 4.0,
    "eye": (0.0, -2.5), "arm": 6, "eye_col": "#f0a010",
    "skin": TREX_SKIN,
    "pattern": combine(stripes(0.5, 0.5, 0.26, shift=-2), speckle(11, 0.10, -1), scales(4, -1, 0.7)),
    "head_extra": trex_head, "k": 1.3, "teeth": True, "shin_r": (0.62, 2.6, 1.6),
}


def raptor(frame):
    return biped(66, 42, frame, RAPTOR)


def dilophosaurus(frame):
    return biped(70, 50, frame, DILO)


def trex(frame):
    return biped(118, 78, frame, TREX)


# ---------------------------------------------------------------------------
# Triceratops (quadruped)
# ---------------------------------------------------------------------------
TRIKE_SKIN = Mat(["#2a2c22", "#464a36", "#646a4c", "#848a62", "#a6aa7c", "#c8c89a"],
                 belly=["#4a4636", "#78705a", "#a49a7c", "#c8bea0", "#e4dcc0", "#f4ecd8"])
FRILL = Mat(["#4a2a14", "#7a4a20", "#b0702c", "#d89a40", "#f0c868"])
BONE = Mat(["#6a6450", "#a8a088", "#d8d0b4", "#f4eedc"], spec=0.5)


def triceratops(frame):
    w, h = 88, 56
    p = pose(frame)
    c = ScaledCanvas(w, h, 1.3)
    ground = h - 3
    dead = p["dead"]
    bob = -abs(math.sin(p["phase"])) * 1.0 if p["walk"] else p["breath"] * 0.5
    sink = {0: 0, 1: 5, 2: 9}[dead]
    bx, by = 38, 31 + bob + sink
    pat = combine(speckle(5, 0.08, -1), stripes(0.45, 0.0, 0.12, shift=-1), scales(7, -1, 0.75), wrinkles(1.1, -1))
    atk = p["attack"]
    push = {0: 1, 1: 4, 2: 2}.get(atk, 0)

    def legs(far):
        shade = 0.7 if far else 1.0
        g = 1 if far else 8
        for i, (lx, off) in enumerate(((24, 0.0), (52, math.pi))):
            ph_off = off + (math.pi if far else 0)
            if dead:
                foot = (lx + 6 + (3 if far else 0), ground - 1)
                top = (lx, by + 4)
            else:
                dx = math.sin(p["phase"] + ph_off) * 4 if p["walk"] else 0
                lift = max(0, math.cos(p["phase"] + ph_off)) * 3 if p["walk"] else 0
                top = (lx + (2 if far else 0), by + 6)
                foot = (lx + dx + (2 if far else 0), ground - 2 - lift)
            c.capsule(top, foot, 6.0, 4.6, TRIKE_SKIN, g, shade, pattern=wrinkles(1.7, -1, axis_x=False))
            c.ellipse(foot[0] + 1, foot[1] + 0.5, 4.5, 2.2, TRIKE_SKIN, group=g, shade=shade * 0.85)
            for t in (-1.5, 1.0, 3.5):  # toenails
                c.pixel(foot[0] + t, foot[1] + 1.8, CLAW if not far else "#a8a28c")

    legs(True)
    # tail
    c.chain([(bx - 18, by - 1), (bx - 28, by + 2), (bx - 36, by + 6)], [6.5, 4.0, 1.2], TRIKE_SKIN, 2, pattern=pat)
    c.ellipse(bx, by, 22, 13, TRIKE_SKIN, rot=-4, group=2, pattern=pat)
    # back ridge scutes
    for i in range(7):
        x = bx - 15 + i * 5
        y = by - 12.5 + abs(i - 3) * 0.9
        c.ellipse(x, y, 2.2, 1.4, TRIKE_SKIN, group=2, shade=1.1)
    legs(False)

    # head: frill behind, then skull, beak, horns
    hx, hy = bx + 24 + push, by - 3 + (atk == 1) * 3 + (6 if dead else 0)
    c.ellipse(hx - 2, hy - 4, 10, 12, FRILL, rot=-20, group=10, round_=0.6,
              pattern=lambda xx, yy, nx, ny: (((xx - hx) ** 2 + (yy - hy) ** 2) ** 0.5 % 4 < 1) * -1)
    for k in range(7):  # frill rim knobs
        a = math.radians(-160 + k * 30)
        c.ellipse(hx - 2 + math.cos(a) * 10, hy - 4 + math.sin(a) * 11.5, 1.6, 1.6, BONE, group=11)
    c.ellipse(hx + 4, hy + 2, 8, 6.5, TRIKE_SKIN, rot=12, group=12, belly_t=0.5, pattern=scales(9, -1, 0.8))
    c.capsule((hx + 1, hy + 6), (hx - 2, hy + 9), 1.3, 0.4, BONE, 12)  # cheek horn
    c.polygon([(hx + 9, hy - 1), (hx + 15, hy + 3), (hx + 13, hy + 8), (hx + 8, hy + 7)], BONE, normal=(0.4, -0.2, 0.9), group=13)
    c.capsule((hx + 4, hy - 1), (hx + 16, hy - 11), 1.8, 0.5, BONE, 14)  # brow horns
    c.capsule((hx + 1, hy - 2), (hx + 11, hy - 12), 1.6, 0.5, BONE, 15, shade=0.8)
    c.capsule((hx + 11, hy + 1), (hx + 14, hy - 3), 1.4, 0.5, BONE, 16)  # nose horn
    c.line((hx + 13, hy + 5), (hx + 15, hy + 3.5), "#3a3428")  # beak edge
    c.pixel(hx + 10, hy + 2, "#2a2418")  # nostril
    draw_eye(c, hx + 5, hy, "#f0c020", dead, "#3a3c2a")
    return c.finish()


# ---------------------------------------------------------------------------
# Humans
# ---------------------------------------------------------------------------
SKIN = Mat(["#6a3a22", "#a0623a", "#d08a5a", "#f0b888"])
BOOT = Mat(["#1a120c", "#3a2a1c", "#5a4430"])
METAL = Mat(["#1a1a1e", "#3a3a40", "#62646c", "#9a9ca4"], spec=0.8)
WOOD = Mat(["#2a1808", "#5a3418", "#8a5428", "#b47a40"])


def human(frame, look):
    w, h = 28, 44
    p = pose(frame)
    c = ScaledCanvas(w, h, 1.25)
    ground = h - 3
    cx = 12
    dead = p["dead"]
    if dead:
        return human_dead(frame, look, dead)
    bob = -abs(math.sin(p["phase"])) * 1.0 if p["walk"] else p["breath"] * 0.5
    hip = (cx, 27 + bob)
    shirt, pants, hat = look["shirt"], look["pants"], look["hat"]

    def leg(off, shade, g):
        if p["walk"]:
            fx = hip[0] + math.sin(p["phase"] + off) * 3.5
            fy = ground - 1 - max(0, math.cos(p["phase"] + off)) * 2
        else:
            fx, fy = hip[0] + (1 if off else -1), ground - 1
        knee = ik2(hip, (fx, fy - 1), 6.5, 6.5, bend=1)
        c.capsule(hip, knee, 2.3, 2.0, pants, g, shade)
        c.capsule(knee, (fx, fy - 1), 2.0, 1.8, pants, g, shade)
        c.capsule((fx - 0.5, fy), (fx + 2.5, fy), 1.6, 1.4, BOOT, g + 20, shade)

    def arm(off, shade, g, aim=False):
        sh = (cx + (1 if not off else -1) * 0.5, 17 + bob)
        if aim:
            el = (sh[0] + 4, sh[1] + 2)
            hand = (sh[0] + 7.5, sh[1] + 0.5)
        else:
            sw = math.sin(p["phase"] + off) * 3 if p["walk"] else 0
            el = (sh[0] + sw * 0.5, sh[1] + 5)
            hand = (sh[0] + sw, sh[1] + 9)
        c.capsule(sh, el, 1.9, 1.6, shirt, g, shade)
        c.capsule(el, hand, 1.6, 1.4, shirt, g, shade)
        c.ellipse(hand[0], hand[1], 1.5, 1.5, SKIN, group=g + 30, shade=shade)
        return hand

    leg(math.pi, 0.72, 1)
    far_hand = arm(math.pi, 0.72, 2, aim=p["attack"] >= 0 and look["gear"] in ("rifle",))
    if "back" in look:
        look["back"](c, cx, bob, p)
    # torso
    c.capsule((cx, 19 + bob), (cx, 26 + bob), 4.2, 3.8, shirt, 3)
    c.line((cx + 0.5, 18 + bob), (cx + 0.5, 25 + bob), shirt.ramp[1])  # placket
    if look.get("vest"):
        c.polygon([(cx - 3, 18 + bob), (cx + 3, 18 + bob), (cx + 3.5, 26 + bob), (cx - 3.5, 26 + bob)], look["vest"], normal=(-0.2, -0.2, 1), group=3)
    c.capsule((cx - 3.5, 26.5 + bob), (cx + 3.5, 26.5 + bob), 1.0, 1.0, BOOT, 3)  # belt
    if "front" in look:
        look["front"](c, cx, bob, p)
    leg(0.0, 1.0, 4)
    # head & face
    hy = 11 + bob
    c.capsule((cx + 0.5, hy + 2), (cx + 0.5, hy + 5), 1.4, 1.4, SKIN, 5, shade=0.8)  # neck
    c.ellipse(cx + 0.5, hy, 3.4, 3.8, SKIN, group=5)
    c.pixel(cx + 2.4, hy - 0.4, "#1a1208")  # eye
    c.pixel(cx + 2.4, hy - 1.3, "#4a2a18")  # brow
    c.pixel(cx + 3.6, hy + 0.6, SKIN.ramp[1])  # nose
    c.pixel(cx + 2.6, hy + 2.0, "#7a3a2a")  # mouth
    c.pixel(cx - 0.6, hy + 0.2, SKIN.ramp[1])  # ear
    if look.get("stubble"):
        c.pixel(cx + 1.6, hy + 2.4, "#5a3a2a")
        c.pixel(cx + 0.6, hy + 2.2, "#5a3a2a")
    look["hat_fn"](c, cx, hy, hat)
    gear = look["gear"]
    atk = p["attack"]
    if gear == "rifle":
        if atk >= 0:
            y = 17.5 + bob
            c.capsule((cx - 2, y + 1), (cx + 4, y), 1.4, 1.2, WOOD, 9)
            c.capsule((cx + 4, y), (cx + 14, y - 0.5), 0.9, 0.7, METAL, 9)
            if look.get("scope"):
                c.capsule((cx + 5, y - 1.8), (cx + 9, y - 1.9), 0.8, 0.8, METAL, 9)
            if atk == 0:
                for d in ((15, -1), (16, 0), (15, 1), (17, -0.5), (16, -2), (16, 1.5)):
                    c.pixel(cx + d[0], y + d[1], "#fff2a0" if d[0] < 17 else "#ffb030")
        else:
            c.capsule((cx - 3, 26 + bob), (cx + 6, 15 + bob), 1.2, 0.8, WOOD, 9)
            c.capsule((cx + 2, 20 + bob), (cx + 8, 12 + bob), 0.8, 0.6, METAL, 9)
            if look.get("scope"):
                c.capsule((cx + 3.5, 17 + bob), (cx + 5.5, 14.5 + bob), 0.8, 0.8, METAL, 9)
    elif gear == "wrench":
        if atk >= 0:
            ang = {0: -60, 1: 20, 2: -10}[atk]
            a = math.radians(ang)
            base = (cx + 4, 19 + bob)
            c.capsule(base, (base[0] + math.cos(a) * 9, base[1] + math.sin(a) * 9), 1.0, 1.0, METAL, 9)
            c.ellipse(base[0] + math.cos(a) * 9, base[1] + math.sin(a) * 9, 2, 1.6, METAL, group=9)
        else:
            c.polygon([(cx + 2, 27 + bob), (cx + 8, 27 + bob), (cx + 8, 31 + bob), (cx + 2, 31 + bob)], Mat(["#5a1410", "#9a2a1a", "#d04a2a"]), group=9)
            c.capsule((cx + 4, 26 + bob), (cx + 6, 26 + bob), 0.6, 0.6, METAL, 9)
    elif gear == "net":
        net = Mat(["#4a4a3a", "#7a7a64", "#b0b098", "#dcdcc8"])
        if atk >= 0:
            r = (3, 5, 4)[atk]
            nx, ny = cx + 6 + atk * 2, 12 + bob - atk
            for k in range(-r, r + 1, 2):
                c.line((nx - r, ny + k), (nx + r, ny + k), "#d4d4c0")
                c.line((nx + k, ny - r), (nx + k, ny + r), "#b4b4a0")
        else:
            c.ellipse(cx - 4.5, 21 + bob, 3.5, 4.5, net, group=9, pattern=lambda xx, yy, a, b: ((xx + yy).astype(int) % 2) * -1)
    return c.finish()


def human_dead(frame, look, dead):
    w, h = 28, 44
    c = ScaledCanvas(w, h, 1.25)
    ground = h - 4
    if dead == 1:
        c.capsule((8, ground - 6), (16, ground - 12), 3.8, 3.5, look["shirt"], 1)
        c.ellipse(19, ground - 15, 3.3, 3.5, SKIN, group=2)
        c.capsule((7, ground - 5), (2, ground), 2.0, 1.8, look["pants"], 3)
    else:
        c.capsule((6, ground - 2), (17, ground - 3), 2.2, 2.0, look["pants"], 1)
        c.capsule((13, ground - 3), (21, ground - 3), 3.8, 3.5, look["shirt"], 2)
        c.ellipse(24, ground - 3, 3.3, 3.0, SKIN, group=3)
    return c.finish()


def hat_bush(col):
    m = Mat(col)

    def f(c, cx, hy, _):
        c.ellipse(cx + 0.5, hy - 2.5, 6, 1.6, m, group=6, round_=0.5)
        c.ellipse(cx + 0.5, hy - 3.8, 3.4, 2.4, m, group=6)
    return f


def hat_hard(c, cx, hy, _):
    m = Mat(["#7a5a08", "#c09010", "#e8c020", "#fff070"], spec=0.6)
    c.ellipse(cx + 0.5, hy - 2.5, 4.4, 3.6, m, group=6, clip=lambda xx, yy: yy < hy - 1.2)
    c.capsule((cx - 3.5, hy - 1.6), (cx + 6, hy - 1.6), 0.7, 0.7, m, 6)
    c.capsule((cx - 1, hy - 3.6), (cx + 3.5, hy - 3.6), 0.8, 0.8, Mat(["#0a1420", "#1a3450", "#3a6a90", "#8ac0e0"], spec=1), 7)  # goggles


def hat_cap(c, cx, hy, _):
    m = Mat(["#0e0e10", "#22222a", "#3a3a44", "#56566a"])
    c.ellipse(cx + 0.5, hy - 2.8, 3.6, 2.6, m, group=6, clip=lambda xx, yy: yy < hy - 1.0)
    c.capsule((cx + 2, hy - 1.6), (cx + 6.5, hy - 1.4), 0.8, 0.6, m, 6)


CANVAS_BAG = Mat(["#2a2a14", "#46462a", "#646440", "#84845a"])
LEATHER = Mat(["#2a140a", "#4a2a14", "#6e4222", "#925a30"])
BRASS = "#e0b040"


def ranger_back(c, cx, bob, p):
    c.capsule((cx - 4.5, 18 + bob), (cx - 4.5, 25 + bob), 3.0, 3.2, CANVAS_BAG, 40)  # backpack
    c.capsule((cx - 7, 17 + bob), (cx - 2, 17 + bob), 1.6, 1.6, Mat(["#3a1a10", "#6a3020", "#9a4a30", "#c06a48"]), 41)  # bedroll


def ranger_front(c, cx, bob, p):
    c.line((cx - 2.5, 18 + bob), (cx + 2.5, 25 + bob), LEATHER.ramp[1])  # strap
    for k in range(3):
        c.pixel(cx - 1.5 + k * 1.6, 19.5 + bob + k * 2.2, BRASS)
    c.ellipse(cx + 3.5, 28 + bob, 1.6, 2.0, Mat(["#1a2a1a", "#2e4a2e", "#4a6a4a", "#7a9a7a"], spec=0.4), group=42)  # canteen


def engineer_front(c, cx, bob, p):
    for y in (21, 24):  # reflective stripes
        c.line((cx - 3, y + bob), (cx + 3, y + bob), "#f0f0d8")
    for k, col in enumerate(("#9a9ca4", "#e8c020", "#9a9ca4")):  # tool belt
        c.pixel(cx - 2 + k * 2, 27.5 + bob, col)


def hunter_front(c, cx, bob, p):
    c.line((cx + 2.5, 18 + bob), (cx - 2.5, 25.5 + bob), LEATHER.ramp[1])  # bandolier
    for k in range(4):
        c.pixel(cx + 1.8 - k * 1.4, 19 + bob + k * 2.0, BRASS)


def trapper_back(c, cx, bob, p):
    c.line((cx - 5, 16 + bob), (cx - 1, 25 + bob), "#b0b0b8")  # machete on the back
    c.pixel(cx - 5, 15.5 + bob, LEATHER.ramp[2])


def trapper_front(c, cx, bob, p):
    rope = Mat(["#5a4a28", "#8a7440", "#b49c60", "#d8c488"])
    c.ellipse(cx + 3.5, 28.5 + bob, 2.4, 1.8, rope, group=43,
              pattern=lambda xx, yy, nx, ny: np.where(((xx + yy) * 1.5).astype(int) % 2 == 0, -1, 0))


LOOKS = {
    "ranger": {"shirt": Mat(["#2a3418", "#46562a", "#68803e", "#90a858"]), "pants": Mat(["#2a2014", "#4a3a26", "#6a5638", "#8a7450"]),
               "hat": None, "hat_fn": hat_bush(["#3a3a1a", "#5e5e2c", "#848442", "#a8a860"]), "gear": "rifle",
               "back": ranger_back, "front": ranger_front},
    "engineer": {"shirt": Mat(["#1a2440", "#2a3a62", "#3e5488", "#5a74aa"]), "pants": Mat(["#141c30", "#22304e", "#34466e", "#4a5e8a"]),
                 "vest": Mat(["#8a3a08", "#d0641a", "#f08a2a", "#ffb050"]), "hat": None, "hat_fn": hat_hard, "gear": "wrench",
                 "front": engineer_front},
    "hunter": {"shirt": Mat(["#2a0c0a", "#5a1a14", "#8a2a20", "#b04232"]), "pants": Mat(["#141414", "#26262a", "#3a3a40", "#54545c"]),
               "hat": None, "hat_fn": hat_cap, "gear": "rifle", "scope": True, "stubble": True, "front": hunter_front},
    "trapper": {"shirt": Mat(["#3a2a14", "#6a5030", "#9a7a4c", "#c4a270"]), "pants": Mat(["#20180e", "#3a2c1a", "#56442a", "#74603e"]),
                "hat": None, "hat_fn": hat_bush(["#2a1a0a", "#4a3018", "#6a4828", "#8a6438"]), "gear": "net",
                "stubble": True, "back": trapper_back, "front": trapper_front},
}


# ---------------------------------------------------------------------------
# Poacher jeep
# ---------------------------------------------------------------------------
PAINT = Mat(["#2a0a08", "#4a1410", "#7a2218", "#a8362a", "#cc5040"], spec=0.4)
TYRE = Mat(["#0a0a0a", "#1c1c1c", "#2e2e30", "#444448"])
GLASS = Mat(["#1a3040", "#2e5a6e", "#5a94a8", "#a8dce8"], spec=1.0)


def jeep(frame):
    w, h = 70, 48
    p = pose(frame)
    c = ScaledCanvas(w, h, 1.2)
    ground = h - 3
    dead = p["dead"]
    bob = (math.sin(p["phase"] * 2) * 0.8) if p["walk"] else 0
    tilt = 3 if dead == 2 else 0
    by = 30 + bob + tilt
    # wheels (far side first)
    for wx in (16, 52):
        c.ellipse(wx + 3, ground - 7, 7, 7, TYRE, group=1, shade=0.6)
    c.ellipse(4, by - 6, 4.5, 5.5, TYRE, group=1)  # spare tyre
    c.ellipse(4, by - 6, 2, 2.5, METAL, group=1)
    # chassis (with mud splashed along the bottom)
    rnd = np.random.default_rng(17)
    mud_noise = rnd.random((200, 200))
    c.polygon([(4, by - 6), (12, by - 12), (40, by - 12), (46, by - 7), (64, by - 6), (66, by + 2), (4, by + 2)], PAINT, normal=(0, -0.1, 1), group=2,
              pattern=lambda xx, yy, nx, ny: (yy > by - 1) * -1 + ((yy > by - 4) & (mud_noise[(yy * 3).astype(int) % 200, (xx * 3).astype(int) % 200] < 0.35)) * -2)
    c.polygon([(50, by - 6), (58, by - 6), (58, by), (50, by)], Mat(["#14240e", "#24401a", "#365c26", "#4a7a34"]), normal=(0, 0, 1), flat=0.75, group=2)  # jerry can
    c.line((52, by - 4), (56, by - 4), "#1a2a12")
    c.polygon([(12, by - 12), (40, by - 12), (42, by - 14), (14, by - 14)], PAINT, normal=(0, -1, 0.4), group=2)
    c.capsule((4, by - 2), (66, by - 2), 0.6, 0.6, Mat(["#806020", "#c8a040", "#f0d070"]), 2)  # stripe
    # crew: driver and gunner
    c.ellipse(35, by - 16, 2.2, 2.4, SKIN, group=3)
    c.ellipse(35, by - 17.6, 2.3, 1.2, Mat(["#0e0e10", "#22222a", "#3a3a44"]), group=3)
    c.ellipse(20, by - 18, 2.2, 2.4, SKIN, group=3)
    c.ellipse(20, by - 19.8, 2.3, 1.2, Mat(["#2a1a0a", "#4a3018", "#6a4828"]), group=3)
    c.capsule((20, by - 15), (20, by - 13), 2.4, 2.6, Mat(["#2a0c0a", "#5a1a14", "#8a2a20"]), 3)
    # windshield & roll bar
    c.polygon([(38, by - 12), (44, by - 24), (47, by - 24), (43, by - 12)], GLASS, normal=(0.6, -0.6, 0.6), group=3)
    c.line((41, by - 15), (44.5, by - 22), "#e8f8ff")  # glare
    c.chain([(10, by - 12), (13, by - 26), (30, by - 26), (33, by - 12)], [1.2, 1.2, 1.2, 1.2], METAL, 4)
    # mounted gun
    atk = p["attack"]
    c.capsule((22, by - 14), (22, by - 22), 1.3, 1.3, METAL, 5)
    gx = 2 if atk == 0 else 0
    c.capsule((18, by - 23), (36 - gx, by - 23 + (0 if atk < 0 else -1)), 1.6, 1.1, METAL, 5)
    if atk == 0:
        for d in ((37, -1), (38, 0), (37, 1), (39, -1), (39, 1), (40, 0)):
            c.pixel(d[0], by - 23 + d[1] - 1, "#fff2a0" if d[0] < 39 else "#ffb030")
    # bull bar, headlight
    c.chain([(66, by - 8), (69, by - 6), (69, by + 1)], [0.9, 0.9, 0.9], METAL, 6)
    c.ellipse(64, by - 3, 1.6, 1.6, Mat(["#806020", "#f0e080", "#fffff0"], spec=1), group=6)
    # near wheels
    for wx in (12, 48):
        c.ellipse(wx, ground - 6, 7, 7, TYRE, group=7,
                  pattern=lambda xx, yy, nx, ny, wx=wx: np.where((np.arctan2(yy - (ground - 6), xx - wx) * 6).astype(int) % 2 == 0, -1, 0))
        c.ellipse(wx, ground - 6, 3.2, 3.2, METAL, group=8)
        a = p["phase"] * 2
        for k in range(3):
            aa = a + k * math.tau / 3
            c.pixel(wx + math.cos(aa) * 2.2, ground - 6 + math.sin(aa) * 2.2, "#1a1a1e")
    if dead:
        for i in range(10):
            c.pixel(20 + i * 3, by - 14 - (i % 3), "#202020")
    return c.finish()


def make_sheet(fn, *args):
    from PIL import Image
    frames = [fn(f, *args) for f in range(FRAMES)]
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * FRAMES, h), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * w, 0))
    return sheet


# ---------------------------------------------------------------------------
# Ambient flying reptile (4-frame flap cycle, facing right)
# ---------------------------------------------------------------------------
PTERO_SKIN = Mat(["#2a1a14", "#4a3020", "#6e4a30", "#946a44", "#b88c5c"])
MEMBRANE = Mat(["#3a1a14", "#6a3020", "#9a4a2a", "#c46a3a", "#e08a50"])


def pteranodon(frame):
    c = ScaledCanvas(56, 34, 1.0)
    flap = [-9.0, -2.0, 7.0, -2.0][frame % 4]
    body = (26, 18)
    tip_far = (body[0] - 6, body[1] + flap * 0.8 - 2)
    tip_near = (body[0] + 2, body[1] + flap + 4)
    # far wing (behind the body), darker
    c.polygon([(body[0] - 3, body[1] - 1), (tip_far[0] - 14, tip_far[1] - 6), (tip_far[0] - 6, tip_far[1] + 2), (body[0] - 6, body[1] + 2)],
              MEMBRANE, normal=(-0.2, -0.6, 0.8), group=1, shade=0.7)
    c.capsule((body[0] + 9, body[1] - 1), (body[0] - 10, body[1] + 1), 2.6, 1.6, PTERO_SKIN, 2)
    c.capsule((body[0] - 10, body[1] + 1), (body[0] - 15, body[1] + 2), 1.0, 0.4, PTERO_SKIN, 2)
    head = (body[0] + 12, body[1] - 3)
    c.ellipse(head[0], head[1], 3.2, 2.2, PTERO_SKIN, group=3)
    c.capsule(head, (head[0] + 10, head[1] + 1.5), 1.4, 0.4, Mat(["#6a5a38", "#a8945c", "#d8c488"]), 3)  # beak
    c.capsule(head, (head[0] - 8, head[1] - 4), 1.6, 0.5, MEMBRANE, 3)  # crest
    c.pixel(head[0] + 1, head[1] - 1, "#f0d040")
    # near wing in front
    c.polygon([(body[0] + 3, body[1] - 1), (tip_near[0] + 18, tip_near[1] + 4), (tip_near[0] + 8, tip_near[1] + 7), (body[0] - 4, body[1] + 2)],
              MEMBRANE, normal=(0.1, -0.5, 0.9), group=4,
              pattern=lambda xx, yy, nx, ny: np.where((xx * 0.5 + yy).astype(int) % 5 == 0, -1, 0))
    c.line((body[0] + 3, body[1] - 1), (tip_near[0] + 18, tip_near[1] + 4), PTERO_SKIN.ramp[1])
    return c.finish()


def make_strip(fn, n):
    from PIL import Image
    frames = [fn(f) for f in range(n)]
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * w, 0))
    return sheet
