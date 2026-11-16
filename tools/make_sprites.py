"""Draw the battle sprite sheets and backdrop in code (needs Pillow).

Usage (from the repo root):

    python tools/make_sprites.py                 # writes web/static/images/sprites/*.png
    python tools/make_sprites.py --preview DIR   # also writes 4x previews to DIR

Every character sheet has the same layout, which web/static/js/battle.js relies on:
64x48 px frames, the character facing right with its feet on row 44.

    row 0  idle    4 frames
    row 1  attack  4 frames (wind-up, swing, strike, recover)
    row 2  hurt    2 frames
    row 3  death   4 frames

A sheet from another tool (Aseprite, a bought pack) works as long as it keeps
this layout; map it in json/battle_sprites.json.
"""

import argparse
import math
import random
from pathlib import Path

from PIL import Image

FW, FH = 64, 48
GROUND = 44
ROWS = (("idle", 4), ("attack", 4), ("hurt", 2), ("death", 4))
OUT = Path(__file__).resolve().parent.parent / "web" / "static" / "images" / "sprites"
OUTLINE = (24, 18, 30, 255)


def rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


class Frame:
    """A small pixel canvas with integer drawing primitives (no anti-aliasing)."""

    def __init__(self, w=FW, h=FH):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.px = self.img.load()

    def dot(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = color

    def rect(self, x0, y0, x1, y1, color):
        for y in range(int(round(min(y0, y1))), int(round(max(y0, y1))) + 1):
            for x in range(int(round(min(x0, x1))), int(round(max(x0, x1))) + 1):
                self.dot(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / (rx + 0.35)) ** 2 + ((y - cy) / (ry + 0.35)) ** 2 <= 1:
                    self.dot(x, y, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(steps + 1):
            t = i / steps
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if width == 1:
                self.dot(x, y, color)
            else:
                half = (width - 1) / 2
                self.rect(x - half, y - half, x + half, y + half, color)

    def tri(self, a, b, c, color):
        xs, ys = (a[0], b[0], c[0]), (a[1], b[1], c[1])

        def side(p, q, r):
            return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
        for y in range(int(min(ys)), int(max(ys)) + 1):
            for x in range(int(min(xs)), int(max(xs)) + 1):
                d1, d2, d3 = side((x, y), a, b), side((x, y), b, c), side((x, y), c, a)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
                    self.dot(x, y, color)

    def outline(self, color=OUTLINE):
        """Dark 1px outline around everything drawn so far."""
        solid = [(x, y) for y in range(self.h) for x in range(self.w) if self.px[x, y][3]]
        for x, y in solid:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < self.w and 0 <= ny < self.h and not self.px[nx, ny][3]:
                    self.px[nx, ny] = color


def polar(x, y, angle_deg, length):
    """Point `length` away from (x, y); 0 degrees is right, 90 is up."""
    a = math.radians(angle_deg)
    return x + math.cos(a) * length, y - math.sin(a) * length


def fall(frame, angle_deg):
    """The frame tipped backwards around its feet, settling onto the ground."""
    if not angle_deg:
        return frame.img.copy()
    pad = 40                                     # room to rotate without clipping
    big = Image.new("RGBA", (FW + 2 * pad, FH + 2 * pad), (0, 0, 0, 0))
    big.paste(frame.img, (pad, pad))
    turned = big.rotate(angle_deg, resample=Image.NEAREST, center=(pad + 26, pad + GROUND))
    left, _, right, bottom = turned.getbbox()
    # Rest the lowest pixel on the ground and slide the body back under the frame's middle
    slide = (angle_deg / 90) * ((FW // 2 - 4) - ((left + right) / 2 - pad))
    out = Image.new("RGBA", frame.img.size, (0, 0, 0, 0))
    out.paste(turned, (int(round(slide)) - pad, GROUND + 1 - bottom), turned)
    return out


def sheet(draw, poses):
    """Assemble a sheet from a draw(pose) function and {row: [pose, ...]}."""
    img = Image.new("RGBA", (FW * 4, FH * len(ROWS)), (0, 0, 0, 0))
    for row, (name, count) in enumerate(ROWS):
        for col in range(count):
            if name == "death":
                frame = fall(draw(poses["death"]), (0, 28, 62, 90)[col])
            else:
                frame = draw(poses[name][col]).img
            img.paste(frame, (col * FW, row * FH))
    return img


# --------------------------------------------------------------------------- knight

STEEL, STEEL_L, STEEL_D = rgb("8f9bb3"), rgb("c9d3e6"), rgb("5b6680")
BLUE, BLUE_D = rgb("2f5fb3"), rgb("1f3f7a")
GOLD, GOLD_D = rgb("e0b040"), rgb("a8782a")
RED, RED_D = rgb("c8343c"), rgb("8a1f2a")
LEATHER, LEATHER_D = rgb("7a4a2a"), rgb("4f2e1a")
BLADE, BLADE_L = rgb("d8e2f0"), rgb("ffffff")
DARK = rgb("1c1626")


def draw_knight(pose):
    f = Frame()
    lean, bob = pose.get("lean", 0), pose.get("bob", 0)
    x, y = 22 + lean, bob            # body origin; legs stay planted

    # Back leg, front leg, boots
    f.rect(21, 35, 24, 41, STEEL_D)
    f.rect(27, 35, 30, 41, STEEL)
    f.rect(27, 35, 28, 41, STEEL_L)
    f.rect(21, 42, 26, 44, LEATHER_D)
    f.rect(27, 42, 32, 44, LEATHER)
    f.rect(21, 38, 24, 38, STEEL)       # knee guards
    f.rect(27, 38, 30, 38, STEEL_D)

    # Sword arm (far side, behind the torso)
    sx, sy = x + 9, 25 + y
    hx, hy = polar(sx, sy, pose["arm"], 6)
    f.line(sx, sy, hx, hy, STEEL_D, 3)
    tip = polar(hx, hy, pose["sword"], 17)
    f.line(hx, hy, *tip, BLADE, 2)
    f.line(*polar(hx, hy, pose["sword"], 3), *polar(hx, hy, pose["sword"], 15), BLADE_L, 1)
    g0, g1 = polar(hx, hy, pose["sword"] + 90, 3), polar(hx, hy, pose["sword"] - 90, 3)
    f.line(*polar(*g0, pose["sword"], 2), *polar(*g1, pose["sword"], 2), GOLD, 2)
    f.rect(hx - 1, hy - 1, hx + 1, hy + 1, LEATHER_D)

    # Torso: plate, tabard, belt
    f.rect(x - 2, 23 + y, x + 9, 34 + y, STEEL)
    f.rect(x - 2, 23 + y, x, 34 + y, STEEL_D)
    f.rect(x + 2, 23 + y, x + 9, 24 + y, STEEL_L)
    f.rect(x + 2, 25 + y, x + 6, 34 + y, BLUE)
    f.rect(x + 2, 25 + y, x + 2, 34 + y, BLUE_D)
    f.rect(x + 4, 27 + y, x + 4, 29 + y, GOLD)
    f.rect(x + 3, 28 + y, x + 5, 28 + y, GOLD)
    f.rect(x - 2, 32 + y, x + 9, 33 + y, LEATHER)
    f.rect(x + 3, 32 + y, x + 5, 33 + y, GOLD)

    # Pauldron and helmet with plume
    f.ellipse(x + 8, 24 + y, 3, 2, STEEL_L)
    f.rect(x - 1, 13 + y, x + 8, 22 + y, STEEL)
    f.rect(x - 1, 13 + y, x, 22 + y, STEEL_D)
    f.rect(x + 1, 13 + y, x + 7, 13 + y, STEEL_L)
    f.rect(x, 12 + y, x + 7, 12 + y, STEEL)
    f.rect(x + 3, 17 + y, x + 8, 18 + y, DARK)          # visor slit
    f.rect(x + 6, 19 + y, x + 6, 21 + y, STEEL_D)       # breathing holes
    f.rect(x + 8, 19 + y, x + 8, 21 + y, STEEL_D)
    f.rect(x - 4, 9 + y, x + 3, 11 + y, RED)
    f.rect(x - 6, 10 + y, x - 3, 14 + y, RED)
    f.rect(x - 6, 13 + y, x - 5, 16 + y, RED_D)
    f.rect(x - 4, 11 + y, x + 1, 11 + y, RED_D)

    # Shield on the near arm
    sh = x - 5 + pose.get("shield", 0)
    f.rect(sh, 24 + y, sh + 7, 33 + y, BLUE)
    f.tri((sh, 34 + y), (sh + 7, 34 + y), (sh + 3.5, 38 + y), BLUE)
    f.rect(sh, 24 + y, sh + 7, 24 + y, GOLD)
    f.rect(sh, 24 + y, sh, 33 + y, GOLD)
    f.rect(sh + 7, 24 + y, sh + 7, 33 + y, GOLD_D)
    f.rect(sh + 3, 26 + y, sh + 4, 35 + y, GOLD)
    f.rect(sh + 1, 29 + y, sh + 6, 30 + y, GOLD)

    f.outline()
    return f


KNIGHT_POSES = {
    "idle": [
        {"arm": -55, "sword": 72, "bob": 0},
        {"arm": -55, "sword": 74, "bob": 0},
        {"arm": -58, "sword": 76, "bob": 1},
        {"arm": -58, "sword": 74, "bob": 1},
    ],
    "attack": [
        {"arm": 75, "sword": 100, "lean": -2, "shield": 1},
        {"arm": 55, "sword": 62, "lean": 1},
        {"arm": -8, "sword": -18, "lean": 4, "bob": 1, "shield": -1},
        {"arm": -35, "sword": 15, "lean": 2},
    ],
    "hurt": [
        {"arm": -95, "sword": 30, "lean": -4, "bob": 1, "shield": 2},
        {"arm": -75, "sword": 50, "lean": -2, "bob": 1, "shield": 1},
    ],
    "death": {"arm": -90, "sword": 20, "bob": 1},
}


# --------------------------------------------------------------------------- goblin

SKIN, SKIN_L, SKIN_D = rgb("6fa83c"), rgb("9ccc5a"), rgb("476f2a")
TUNIC, TUNIC_D = rgb("8a5a34"), rgb("5c3a20")
EYE, TOOTH = rgb("ffd84a"), rgb("f4f0dc")
RUST, RUST_L = rgb("9aa0a8"), rgb("d0d4da")
WOOD = rgb("6b4526")


def draw_goblin(pose):
    f = Frame()
    lean, bob = pose.get("lean", 0), pose.get("bob", 0)
    x, y = 22 + lean, bob

    # Bandy legs and big feet
    f.rect(22, 38, 24, 42, SKIN_D)
    f.rect(27, 38, 29, 42, SKIN)
    f.rect(21, 43, 26, 44, SKIN_D)
    f.rect(27, 43, 32, 44, SKIN)

    # Weapon arm (far side): a notched cleaver
    sx, sy = x + 8, 31 + y
    hx, hy = polar(sx, sy, pose["arm"], 6)
    f.line(sx, sy, hx, hy, SKIN_D, 2)
    f.line(hx, hy, *polar(hx, hy, pose["blade"], 4), WOOD, 2)
    b0 = polar(hx, hy, pose["blade"], 4)
    b1 = polar(hx, hy, pose["blade"], 13)
    edge = pose["blade"] - 90
    f.line(*b0, *b1, RUST, 2)
    f.line(*polar(*b0, edge, 2), *polar(*b1, edge, 3), RUST, 2)
    f.line(*polar(*b0, edge, 3), *polar(*b1, edge, 4), RUST_L, 1)

    # Hunched body in a ragged tunic
    f.rect(x, 29 + y, x + 9, 38 + y, TUNIC)
    f.rect(x, 29 + y, x + 1, 38 + y, TUNIC_D)
    f.rect(x, 35 + y, x + 9, 35 + y, TUNIC_D)
    f.rect(x + 4, 35 + y, x + 5, 36 + y, EYE)
    for i in range(0, 10, 2):                       # torn hem
        f.dot(x + i, 39 + y, TUNIC)

    # Head: wide, low, with long ears and a hooked nose
    hx0, hy0 = x + 5, 22 + y
    f.tri((hx0 - 5, hy0 - 2), (hx0 - 15, hy0 - 7), (hx0 - 6, hy0 + 2), SKIN_D)   # back ear
    f.tri((hx0 - 6, hy0 - 1), (hx0 - 12, hy0 - 5), (hx0 - 6, hy0 + 1), rgb("c98a8a"))
    f.ellipse(hx0, hy0, 7, 6, SKIN)
    f.ellipse(hx0 - 1, hy0 - 3, 5, 2, SKIN_L)
    f.rect(hx0 - 7, hy0 + 2, hx0 - 4, hy0 + 5, SKIN_D)
    f.tri((hx0 + 5, hy0 - 4), (hx0 + 12, hy0 - 10), (hx0 + 7, hy0 - 1), SKIN)    # near ear
    f.tri((hx0 + 6, hy0, ), (hx0 + 11, hy0 + 2), (hx0 + 6, hy0 + 3), SKIN_D)     # nose
    f.rect(hx0 + 1, hy0 - 2, hx0 + 5, hy0 - 2, SKIN_D)                           # brow
    f.rect(hx0 + 2, hy0 - 1, hx0 + 4, hy0, EYE)
    f.dot(hx0 + 4, hy0, DARK)
    f.rect(hx0 + 1, hy0 + 3, hx0 + 6, hy0 + 3, DARK)                             # mouth
    f.dot(hx0 + 2, hy0 + 2, TOOTH)
    f.dot(hx0 + 5, hy0 + 4, TOOTH)

    # Near arm hanging forward
    ax, ay = x + 1, 31 + y
    f.line(ax, ay, *polar(ax, ay, pose.get("near_arm", -80), 7), SKIN, 2)

    f.outline()
    return f


GOBLIN_POSES = {
    "idle": [
        {"arm": -30, "blade": 60, "bob": 0},
        {"arm": -30, "blade": 64, "bob": 0},
        {"arm": -34, "blade": 68, "bob": 1},
        {"arm": -34, "blade": 64, "bob": 1},
    ],
    "attack": [
        {"arm": 80, "blade": 105, "lean": -2, "near_arm": -110},
        {"arm": 60, "blade": 70, "lean": 1},
        {"arm": -15, "blade": -30, "lean": 5, "bob": 1, "near_arm": -40},
        {"arm": -40, "blade": 10, "lean": 2},
    ],
    "hurt": [
        {"arm": -100, "blade": 20, "lean": -4, "bob": 1, "near_arm": -130},
        {"arm": -70, "blade": 40, "lean": -2, "bob": 1, "near_arm": -100},
    ],
    "death": {"arm": -90, "blade": 10, "bob": 1},
}


# --------------------------------------------------------------------------- backdrop

def backdrop_forest(w=240, h=76, seed=11):
    """Dusk forest clearing: banded sky, hills, a tree line and a dirt floor.

    240x76 matches the stage's 3.2:1 shape on desktop, so nothing is cropped there."""
    rng = random.Random(seed)
    f = Frame(w, h)
    horizon = 44
    sky = [rgb(c) for c in ("1b1f4a", "2a2a63", "433372", "6a3f78", "9a5272", "c97760")]
    for y in range(horizon):
        band = min(len(sky) - 1, y * len(sky) // horizon)
        f.rect(0, y, w - 1, y, sky[band])
    for _ in range(40):
        f.dot(rng.randrange(w), rng.randrange(20), rgb("e8e4ff"))
    f.ellipse(190, 11, 5, 5, rgb("f6e9c0"))

    for x in range(w):          # far hills
        top = int(33 + 4 * math.sin(x / 23) + 2 * math.sin(x / 7 + 1))
        f.rect(x, top, x, horizon, rgb("2d2752"))
    for _ in range(26):         # tree line
        tx, th = rng.randrange(-6, w), rng.randrange(12, 24)
        f.rect(tx + 3, horizon - 6, tx + 4, horizon, rgb("171a30"))
        for i in range(th):
            half = 1 + i * 6 // th
            f.rect(tx + 4 - half, horizon - 6 - th + i, tx + 3 + half, horizon - 6 - th + i,
                   rgb("1c2a3a") if i % 5 else rgb("243647"))

    f.rect(0, horizon, w - 1, h - 1, rgb("3a3326"))
    f.rect(0, horizon, w - 1, horizon + 1, rgb("4f6a36"))
    for _ in range(140):
        gx, gy = rng.randrange(w), rng.randrange(horizon + 2, h)
        f.dot(gx, gy, rgb(rng.choice(("4a4130", "2e281e", "55492f"))))
    for _ in range(40):
        gx, gy = rng.randrange(w), rng.randrange(horizon + 1, h - 2)
        f.rect(gx, gy - 1, gx, gy, rgb("5d8040"))
        f.dot(gx + 1, gy, rgb("3f5a2c"))
    return f.img


# --------------------------------------------------------------------------- shared rig
# One body builder for every two-legged (or floating) creature. A spec dict sets the
# build, colours, head, weapon and extras; a pose dict sets the angles for one frame.

TOOTH_C = rgb("f4f0dc")


def shades(hex_color):
    """(base, light, dark) versions of a colour."""
    r, g, b, _ = rgb(hex_color)
    light = tuple(min(255, int(c + (255 - c) * 0.38)) for c in (r, g, b)) + (255,)
    dark = tuple(int(c * 0.6) for c in (r, g, b)) + (255,)
    return (r, g, b, 255), light, dark


def draw_weapon(f, hx, hy, ang, w):
    """Weapon held at (hx, hy) pointing along `ang`."""
    kind, n = w["type"], w.get("len", 15)
    c, c_l, c_d = shades(w.get("color", "d8e2f0"))
    shaft = rgb(w.get("shaft", "6b4526"))
    back = polar(hx, hy, ang + 180, w.get("back", 0))
    tip = polar(hx, hy, ang, n)
    if kind in ("sword", "greatsword", "rapier"):
        width = {"sword": 2, "greatsword": 3, "rapier": 1}[kind]
        f.line(hx, hy, *tip, c, width)
        if width > 1:
            f.line(*polar(hx, hy, ang, 3), *polar(hx, hy, ang, n - 2), c_l, 1)
        g = 4 if kind == "greatsword" else 3
        g0, g1 = polar(hx, hy, ang + 90, g), polar(hx, hy, ang - 90, g)
        guard = rgb(w.get("guard", "e0b040"))
        f.line(*polar(*g0, ang, 2), *polar(*g1, ang, 2), guard, 2 if width > 1 else 1)
        f.line(hx, hy, *polar(hx, hy, ang + 180, 2), shaft, 2)
    elif kind == "axe":
        f.line(*back, *tip, shaft, 2)
        b0, b1 = polar(hx, hy, ang, n - 7), polar(hx, hy, ang, n - 1)
        for side in ((ang - 90,) if not w.get("double") else (ang - 90, ang + 90)):
            f.tri(b0, b1, polar(*polar(hx, hy, ang, n - 8), side, 6), c)
            f.tri(b1, polar(*polar(hx, hy, ang, n), side, 6), polar(*polar(hx, hy, ang, n - 8), side, 6), c)
            f.line(*polar(*polar(hx, hy, ang, n - 8), side, 6), *polar(*polar(hx, hy, ang, n), side, 6), c_l, 1)
    elif kind == "club":
        f.line(hx, hy, *polar(hx, hy, ang, n * 0.45), shaft, 2)
        f.line(*polar(hx, hy, ang, n * 0.45), *polar(hx, hy, ang, n - 2), shaft, 4)
        f.ellipse(*polar(hx, hy, ang, n - 2), 3, 3, shaft)
        f.dot(*polar(*polar(hx, hy, ang, n - 3), ang + 90, 3), c)
        f.dot(*polar(*polar(hx, hy, ang, n - 6), ang - 90, 3), c)
    elif kind == "mace":
        f.line(*back, *tip, shaft, 2)
        f.ellipse(*tip, 3, 3, c)
        for spike in (0, 72, 144, 216, 288):
            f.dot(*polar(*tip, ang + spike, 4.4), c_l)
        f.dot(*polar(*tip, ang + 135, 1), c_l)
    elif kind == "staff":
        f.line(*back, *tip, shaft, 2)
        f.ellipse(*tip, 3, 3, c)
        f.ellipse(tip[0] - 0.5, tip[1] - 0.5, 1, 1, c_l)
    elif kind in ("glaive", "lance"):
        f.line(*back, *tip, shaft, 2 if kind == "glaive" else 1)
        if kind == "lance":
            f.line(*back, *tip, shaft, 2)
            f.tri(polar(*tip, ang + 90, 2), polar(*tip, ang - 90, 2), polar(*tip, ang, 7), c)
            f.line(*tip, *polar(*tip, ang, 6), c_l, 1)
            f.line(*polar(*tip, ang + 180, 2), *polar(*polar(*tip, ang + 180, 2), ang - 90, 5),
                   rgb(w.get("pennant", "c8343c")), 2)
        else:
            f.tri(polar(*tip, ang + 180, 6), polar(*tip, ang, 3), polar(*polar(*tip, ang + 180, 2), ang - 90, 5), c)
            f.line(*polar(*tip, ang + 180, 6), *polar(*tip, ang, 3), c_l, 1)
    elif kind == "claws":
        for spread in (-28, 0, 28):
            f.line(hx, hy, *polar(hx, hy, ang + spread, n), c, 1)
    elif kind == "fist":
        f.ellipse(hx, hy, n, n, c)
        f.ellipse(hx - 0.5, hy - 1, max(1, n - 2), max(1, n - 2), c_l)


def draw_figure(pose, s):
    f = Frame()
    lean, bob = pose.get("lean", 0), pose.get("bob", 0)
    cx0 = s.get("cx", 24)
    cx = cx0 + lean
    tw, th = s.get("torso_w", 12), s.get("torso_h", 12)
    lh, lw = s.get("leg_h", 7), s.get("leg_w", 4)
    hw, hh = s.get("head_w", 10), s.get("head_h", 10)
    floating, robe = s.get("float"), s.get("robe")
    extras = s.get("extras", ())
    lift = 5 + pose.get("hover", 0) if floating else 0
    hip0 = GROUND - 3 - lh - lift             # last torso row before bob
    hip, top = hip0 + bob, hip0 - th + 1 + bob
    left = cx - tw // 2
    right = left + tw - 1

    skin, skin_l, skin_d = shades(s["skin"])
    body, body_l, body_d = shades(s["body"])
    legs, legs_l, legs_d = shades(s.get("legs", s["body"]))
    boot, _, boot_d = shades(s.get("boots", "4f2e1a"))
    trim = rgb(s.get("trim", "e0b040"))
    glow = rgb(s["glow"]) if s.get("glow") else None
    sway = pose.get("sway", 0)

    # --- behind the body
    if "wings" in extras:
        flap = pose.get("flap", 0)
        wing, _, wing_d = shades(s.get("wing", s["skin"]))
        for dx, dy, col in ((0, 0, wing_d), (3, 3, wing)):
            f.tri((cx - 1, top + 3), (cx - 19 + dx, top - 9 + dy - flap), (cx - 9, top + 12), col)
            f.tri((cx - 9, top + 12), (cx - 19 + dx, top - 9 + dy - flap), (cx - 17, top + 9), col)
    if "cape" in extras:
        cape, _, cape_d = shades(s.get("cape", "8a1f2a"))
        hem = min(GROUND - 1, hip + lh + 1)
        f.tri((left + 2, top + 1), (left - 6 - sway, hem), (left + 5, hem), cape_d)
        f.tri((left + 2, top + 1), (right - 2, top + 1), (left + 5, hem), cape_d)
        f.tri((left + 1, top + 2), (left - 5 - sway, hem), (left, hem), cape)
    if "tail" in extras:
        f.line(left + 2, hip - 1, left - 6, hip + 4 - sway, skin_d, 2)
        f.line(left - 6, hip + 4 - sway, left - 10, hip - 1 - sway, skin_d, 2)
        f.tri((left - 12, hip - 4 - sway), (left - 8, hip - 2 - sway), (left - 11, hip + 1 - sway), skin)
    if "hair" in extras:
        hair = rgb(s.get("hair", "1c1626"))
        hx_, hy_ = cx + s.get("hunch", 1), top - hh / 2 + 1
        f.rect(hx_ - hw / 2 - 1, hy_ - hh / 2 + 1, hx_ - hw / 2 + 2, hy_ + hh / 2 + 7, hair)

    # --- lower body
    if floating:
        wave = pose.get("wave", 0)
        f.tri((left, hip), (right, hip), (cx0 - 6 + wave, GROUND - 1), body_d)
        f.tri((left + 2, hip), (right, hip), (cx0 - 1 + wave, GROUND - 4), body)
        f.tri((left, hip), (left + 4, hip), (cx0 - 9 - wave, GROUND - 6), body_d)
    elif robe:
        for y in range(hip, GROUND):
            grow = (y - hip) // 3
            f.rect(left - grow, y, right + grow // 2, y, body)
            f.rect(left - grow, y, left - grow + 1, y, body_d)
        f.rect(left - (GROUND - hip) // 3, GROUND - 1, right + 1, GROUND - 1, body_d)
        f.rect(cx0 + 1, GROUND, cx0 + 4, GROUND, boot)
    else:
        bl = cx0 - tw // 2 + 1
        fl = cx0 + tw // 2 - lw
        f.rect(bl, hip0, bl + lw - 1, GROUND - 3, legs_d)
        f.rect(fl, hip0, fl + lw - 1, GROUND - 3, legs)
        f.rect(fl, hip0, fl, GROUND - 3, legs_l)
        f.rect(bl, GROUND - 2, bl + lw + 1, GROUND, boot_d)
        f.rect(fl, GROUND - 2, fl + lw + 1, GROUND, boot)

    # --- weapon arm (far side)
    arm_c, arm_l, arm_d = shades(s.get("arm", s["skin"]))
    aw, al = s.get("arm_w", 2), s.get("arm_len", 6)
    sx, sy = right - 1, top + 2
    hx, hy = polar(sx, sy, pose["arm"], al)
    weapon = s.get("weapon")
    if weapon:
        draw_weapon(f, hx, hy, pose.get("weapon", pose["arm"]), weapon)
    f.line(sx, sy, hx, hy, arm_d, aw)
    if not weapon or weapon["type"] not in ("fist",):
        f.rect(hx - 1, hy - 1, hx + 1, hy + 1, arm_d if weapon and weapon["type"] == "claws" else skin_d)

    # --- torso
    f.rect(left, top, right, hip, body)
    f.rect(left, top, left + 1, hip, body_d)
    f.rect(left + 2, top, right, top, body_l)
    chest = s.get("chest")
    if chest == "bare":
        f.rect(left + 2, top + 1, right, hip - 3, skin)
        f.rect(left + 2, top + 1, left + 3, hip - 3, skin_d)
        f.rect(left + 5, top + 4, right - 1, top + 4, skin_d)
    elif chest == "tabard":
        f.rect(left + 4, top + 2, right - 3, hip, trim)
        f.rect(left + 4, top + 2, left + 4, hip, body_d)
    elif chest == "ribs":
        for y in range(top + 3, hip - 1, 3):
            f.rect(left + 3, y, right - 1, y, body_d)
    if s.get("belt"):
        f.rect(left, hip - 2, right, hip - 1, rgb(s["belt"]))
        f.rect(cx, hip - 2, cx + 1, hip - 1, trim)
    if "cracks" in extras:
        f.line(left + 3, top + 2, left + 6, top + 7, body_d)
        f.line(left + 6, top + 7, left + 4, hip - 2, body_d)
        f.line(right - 3, top + 4, right - 5, hip - 4, body_d)
    if "moss" in extras:
        moss = rgb("5d8040")
        for dx in (0, 1, 2, 5, 6, tw - 3, tw - 2):
            f.dot(left + dx, top, moss)
        f.rect(left + 1, top + 1, left + 2, top + 2, moss)
    if "gem" in extras and glow:
        f.ellipse(cx + 1, top + th * 0.42, 2, 2, glow)
        f.dot(cx, top + th * 0.42 - 1, rgb("ffffff"))
    if "pauldron" in extras:
        f.ellipse(right - 1, top + 1, 3, 2, rgb(s.get("metal", "8f9bb3")))
    if "fur" in extras:
        fur, fur_l, _ = shades(s.get("fur", "8a6a48"))
        f.ellipse(cx, top, tw / 2 + 1, 2, fur)
        f.rect(left + 2, top - 1, right - 2, top - 1, fur_l)
    if "crystals" in extras:
        cr, cr_l, cr_d = shades(s.get("crystal", "8fe0ff"))
        f.tri((left, top), (left - 3, top - 8), (left + 4, top), cr_d)
        f.tri((left + 2, top), (left + 3, top - 6), (left + 6, top), cr)
        f.tri((right - 5, top), (right - 1, top - 9), (right + 1, top), cr)
        f.line(right - 2, top - 1, right - 1, top - 7, cr_l)

    # --- head
    hxc, hyc = cx + s.get("hunch", 1), top - hh / 2 + s.get("neck", 1)
    rx, ry = hw / 2, hh / 2
    head = s.get("head", "round")
    eye = rgb(s.get("eye", "1c1626"))
    if "branches" in extras:
        twig, leaf = rgb(s.get("twig", "4f3a26")), rgb(s.get("leaf", "5d8040"))
        for ang, n in ((150, 9), (118, 11), (92, 8), (62, 10), (35, 7)):
            end = polar(hxc, hyc - ry + 2, ang + sway * 2, n)
            f.line(hxc, hyc - ry + 2, *end, twig, 1)
            f.dot(end[0] + 1, end[1], leaf)
            f.dot(end[0], end[1] - 1, leaf)
            mid = polar(hxc, hyc - ry + 2, ang + sway * 2, n * 0.6)
            f.dot(mid[0] - 1, mid[1] - 1, leaf)
    if "feathers" in extras:
        for i, ang in enumerate((165, 145, 125, 105)):
            col = rgb(("e8f4ff", "7cc4f0", "e8f4ff", "c8343c")[i])
            f.line(hxc - 1, hyc - ry + 1, *polar(hxc - 1, hyc - ry + 1, ang + sway * 2, 9), col, 2)
    if "horns" in extras:
        horn = rgb(s.get("horn", "d8d0b8"))
        f.tri((hxc - rx + 1, hyc - ry + 2), (hxc - rx - 3, hyc - ry - 6), (hxc - rx + 4, hyc - ry + 1), horn)
        f.tri((hxc + 1, hyc - ry + 1), (hxc + rx + 2, hyc - ry - 6), (hxc + 4, hyc - ry + 1), horn)
    if "ears" in extras:
        f.tri((hxc - rx + 1, hyc - 2), (hxc - rx - 4, hyc - 5), (hxc - rx + 1, hyc + 1), skin_d)

    if head == "helm":
        metal, metal_l, metal_d = shades(s.get("metal", "8f9bb3"))
        f.rect(hxc - rx, hyc - ry, hxc + rx - 1, hyc + ry - 1, metal)
        f.rect(hxc - rx, hyc - ry, hxc - rx + 1, hyc + ry - 1, metal_d)
        f.rect(hxc - rx + 2, hyc - ry, hxc + rx - 2, hyc - ry, metal_l)
        f.rect(hxc - 1, hyc - 1, hxc + rx - 1, hyc, DARK)
        if glow:
            f.rect(hxc + 1, hyc - 1, hxc + 2, hyc - 1, glow)
        else:
            f.rect(hxc + rx - 3, hyc + 1, hxc + rx - 3, hyc + ry - 2, metal_d)
    elif head == "hood":
        f.ellipse(hxc, hyc, rx, ry, body_d)
        f.tri((hxc - rx, hyc - 1), (hxc - 1, hyc - ry - 3), (hxc + rx - 1, hyc - 2), body_d)
        f.ellipse(hxc - 1, hyc - 2, rx - 1, ry - 2, body)
        f.ellipse(hxc + 1.5, hyc + 0.5, rx - 2, ry - 2.5, DARK)
        if s.get("snout"):
            f.rect(hxc + 2, hyc, hxc + rx + 2, hyc + 2, skin)
            f.rect(hxc + 2, hyc + 2, hxc + rx + 2, hyc + 2, skin_d)
        f.rect(hxc + 1, hyc - 1, hxc + 2, hyc - 1, glow or eye)
        if not s.get("snout"):
            f.dot(hxc + 4, hyc - 1, glow or eye)
    elif head == "block":
        f.rect(hxc - rx, hyc - ry, hxc + rx - 1, hyc + ry - 1, skin)
        f.rect(hxc - rx, hyc - ry, hxc - rx + 1, hyc + ry - 1, skin_d)
        f.rect(hxc - rx + 2, hyc - ry, hxc + rx - 1, hyc - ry, skin_l)
        f.rect(hxc, hyc - 1, hxc + rx - 1, hyc, DARK)
        f.rect(hxc + 1, hyc - 1, hxc + 2, hyc, glow or eye)
        f.rect(hxc, hyc + ry - 2, hxc + rx - 2, hyc + ry - 2, skin_d)
    else:
        f.ellipse(hxc, hyc, rx, ry, skin)
        f.ellipse(hxc - 1, hyc - ry * 0.5, rx * 0.65, ry * 0.3, skin_l)
        f.rect(hxc - rx + 1, hyc + ry * 0.3, hxc - rx + 3, hyc + ry - 1, skin_d)
        nose = s.get("nose", 1)
        if nose:
            f.tri((hxc + rx - 1, hyc - 1), (hxc + rx + nose, hyc + 2), (hxc + rx - 1, hyc + 2), skin_d)
        ex = hxc + rx * 0.3
        if s.get("brow", True):
            f.rect(ex - 1, hyc - 2, ex + 2, hyc - 2, skin_d)
        f.rect(ex, hyc - 1, ex + 1, hyc - 1, glow or rgb("f4f0dc"))
        if not glow:
            f.dot(ex + 1, hyc - 1, eye)
        mouth_y = hyc + ry * 0.55
        f.rect(hxc + 1, mouth_y, hxc + rx - 1, mouth_y, DARK)
        if "tusks" in extras:
            f.rect(hxc + 1, mouth_y - 2, hxc + 1, mouth_y - 1, TOOTH_C)
            f.rect(hxc + rx - 1, mouth_y - 2, hxc + rx - 1, mouth_y - 1, TOOTH_C)
        if "beard" in extras:
            beard, _, beard_d = shades(s.get("beard", "e8e4dc"))
            f.tri((hxc - 1, mouth_y + 1), (hxc + rx, mouth_y + 1), (hxc + rx - 2, mouth_y + s.get("beard_len", 7)), beard)
            f.rect(hxc - 1, mouth_y, hxc, mouth_y + 1, beard_d)
            f.rect(hxc + 1, mouth_y - 1, hxc + rx - 1, mouth_y - 1, beard)
        if "hair" in extras:
            f.ellipse(hxc - 1, hyc - ry + 1, rx, 2, rgb(s.get("hair", "1c1626")))

    if "plume" in extras:
        pl, _, pl_d = shades(s.get("plume", "c8343c"))
        f.rect(hxc - rx - 3, hyc - ry - 3, hxc + 2, hyc - ry - 1, pl)
        f.rect(hxc - rx - 5, hyc - ry - 2, hxc - rx - 2, hyc - ry + 3, pl)
        f.rect(hxc - rx - 5, hyc - ry + 2, hxc - rx - 4, hyc - ry + 5, pl_d)
    if "hat" in extras:
        hat, hat_l, hat_d = shades(s.get("hat", s["body"]))
        f.tri((hxc - rx, hyc - ry + 2), (hxc + rx, hyc - ry + 2), (hxc - 3 - sway, hyc - ry - 11), hat)
        f.tri((hxc - rx, hyc - ry + 2), (hxc - 2, hyc - ry + 2), (hxc - 3 - sway, hyc - ry - 11), hat_d)
        f.rect(hxc - rx - 3, hyc - ry + 2, hxc + rx + 2, hyc - ry + 3, hat)
        f.rect(hxc - rx, hyc - ry + 1, hxc + rx - 1, hyc - ry + 1, trim)
    if "mitre" in extras:
        hat, hat_l, hat_d = shades(s.get("hat", s["body"]))
        f.rect(hxc - rx + 1, hyc - ry - 4, hxc + rx - 2, hyc - ry + 1, hat)
        f.tri((hxc - rx + 1, hyc - ry - 4), (hxc + rx - 2, hyc - ry - 4), (hxc, hyc - ry - 10), hat)
        f.rect(hxc, hyc - ry - 7, hxc, hyc - ry, trim)
        f.rect(hxc - rx + 1, hyc - ry, hxc + rx - 2, hyc - ry + 1, trim)
    if "crown" in extras:
        f.rect(hxc - rx + 1, hyc - ry, hxc + rx - 2, hyc - ry + 1, trim)
        for dx in (-rx + 1, -1, rx - 2):
            f.rect(hxc + dx, hyc - ry - 3 + (2 if dx == -1 and s.get("broken") else 0), hxc + dx, hyc - ry, trim)
        if glow:
            f.dot(hxc - 1, hyc - ry + 1, glow)
    if "flame" in extras:
        flick = pose.get("flick", 0)
        for i, dx in enumerate((-3, 0, 3)):
            tall = 5 + ((i + flick) % 2) * 3
            f.tri((hxc + dx - 2, hyc - ry + 1), (hxc + dx + 2, hyc - ry + 1), (hxc + dx - 1, hyc - ry - tall), rgb("ff7a2a"))
            f.tri((hxc + dx - 1, hyc - ry + 1), (hxc + dx + 1, hyc - ry + 1), (hxc + dx, hyc - ry - tall + 3), rgb("ffd84a"))
    if "head_crystals" in extras:
        cr, cr_l, _ = shades(s.get("crystal", "8fe0ff"))
        f.tri((hxc - 3, hyc - ry + 1), (hxc - 2, hyc - ry - 6), (hxc + 1, hyc - ry + 1), cr)
        f.tri((hxc + 1, hyc - ry + 1), (hxc + 4, hyc - ry - 4), (hxc + 4, hyc - ry + 1), cr_l)

    # --- near arm (and shield)
    ax, ay = left + 2, top + 3
    near = pose.get("near_arm", -80)
    nx, ny = polar(ax, ay, near, al)
    f.line(ax, ay, nx, ny, arm_c, aw)
    if s.get("near_fist"):
        nf = s["near_fist"]
        f.ellipse(nx, ny, nf, nf, arm_c)
        f.ellipse(nx - 0.5, ny - 1, max(1, nf - 2), max(1, nf - 2), arm_l)
    elif weapon and weapon["type"] == "claws":
        for spread in (-28, 0, 28):
            f.line(nx, ny, *polar(nx, ny, near + spread, weapon.get("len", 4)), shades(weapon.get("color", "d8e2f0"))[0])
    else:
        f.rect(nx - 1, ny - 1, nx, ny, skin_d)
    if s.get("shield"):
        sc, _, sc_d = shades(s["shield"])
        sh = left - 3 + pose.get("shield", 0)
        f.rect(sh, top + 1, sh + 7, top + 10, sc)
        f.tri((sh, top + 11), (sh + 7, top + 11), (sh + 3.5, top + 15), sc)
        f.rect(sh, top + 1, sh + 7, top + 1, trim)
        f.rect(sh, top + 1, sh, top + 10, trim)
        f.rect(sh + 7, top + 1, sh + 7, top + 10, sc_d)
        f.ellipse(sh + 3.5, top + 6, 1, 1, glow or trim)

    f.outline()
    if "wisps" in extras:                      # drawn after the outline so they stay soft
        wisp = rgb(s.get("wisp", "e8f4ff"))
        phase = pose.get("wave", 0)
        for i, (dx, dy) in enumerate(((-9, 6), (-12, 14), (12, 10), (-6, 22), (10, 20))):
            f.dot(cx + dx + (phase if i % 2 else -phase), top + dy, wisp)
            f.dot(cx + dx + (phase if i % 2 else -phase) + 1, top + dy, wisp)
    return f


def _idle(arm, weapon, near=-80, extra=None):
    frames = []
    for i, (da, bob) in enumerate(((0, 0), (2, 0), (4, 1), (2, 1))):
        pose = {"arm": arm - da // 2, "weapon": weapon + da, "bob": bob, "near_arm": near,
                "hover": (0, 1, 2, 1)[i], "wave": (0, 1, 2, 1)[i], "sway": (0, 0, 1, 1)[i],
                "flick": i, "flap": (0, 1, 2, 1)[i]}
        pose.update(extra or {})
        frames.append(pose)
    return frames


POSES = {
    "swing": {
        "idle": _idle(-55, 72),
        "attack": [
            {"arm": 75, "weapon": 100, "lean": -2, "shield": 1, "near_arm": -100},
            {"arm": 55, "weapon": 62, "lean": 1, "flap": 2},
            {"arm": -8, "weapon": -18, "lean": 4, "bob": 1, "shield": -1, "near_arm": -50, "sway": 2},
            {"arm": -35, "weapon": 15, "lean": 2, "sway": 1},
        ],
        "hurt": [
            {"arm": -95, "weapon": 30, "lean": -4, "bob": 1, "shield": 2, "near_arm": -120},
            {"arm": -75, "weapon": 50, "lean": -2, "bob": 1, "shield": 1, "near_arm": -100},
        ],
        "death": {"arm": -90, "weapon": 20, "bob": 1},
    },
    "thrust": {
        "idle": _idle(-65, 38),
        "attack": [
            {"arm": -150, "weapon": 12, "lean": -3, "near_arm": -40},
            {"arm": -110, "weapon": 6, "lean": 0, "near_arm": -60},
            {"arm": 0, "weapon": 0, "lean": 5, "bob": 1, "near_arm": -120, "sway": 2},
            {"arm": -30, "weapon": 14, "lean": 2, "sway": 1},
        ],
        "hurt": [
            {"arm": -100, "weapon": 60, "lean": -4, "bob": 1, "near_arm": -120},
            {"arm": -80, "weapon": 50, "lean": -2, "bob": 1, "near_arm": -100},
        ],
        "death": {"arm": -90, "weapon": 30, "bob": 1},
    },
    "cast": {
        "idle": _idle(-40, 86),
        "attack": [
            {"arm": 50, "weapon": 105, "lean": -2, "near_arm": -110},
            {"arm": 65, "weapon": 84, "lean": 0, "near_arm": 30, "flick": 1},
            {"arm": 12, "weapon": 38, "lean": 3, "bob": 1, "near_arm": 10, "sway": 2},
            {"arm": -20, "weapon": 66, "lean": 1, "near_arm": -40, "sway": 1},
        ],
        "hurt": [
            {"arm": -80, "weapon": 120, "lean": -4, "bob": 1, "near_arm": -120},
            {"arm": -60, "weapon": 100, "lean": -2, "bob": 1, "near_arm": -100},
        ],
        "death": {"arm": -80, "weapon": 110, "bob": 1},
    },
    "punch": {
        "idle": _idle(-70, -60, near=-95),
        "attack": [
            {"arm": 150, "weapon": 120, "lean": -3, "near_arm": -30},
            {"arm": 95, "weapon": 60, "lean": 0, "near_arm": -60, "flap": 3},
            {"arm": 0, "weapon": -10, "lean": 6, "bob": 1, "near_arm": -130, "sway": 2},
            {"arm": -40, "weapon": -40, "lean": 2, "near_arm": -100, "sway": 1},
        ],
        "hurt": [
            {"arm": -120, "weapon": -100, "lean": -4, "bob": 1, "near_arm": -140},
            {"arm": -95, "weapon": -80, "lean": -2, "bob": 1, "near_arm": -115},
        ],
        "death": {"arm": -90, "weapon": -80, "bob": 1},
    },
}

GOLEM = {"torso_w": 18, "torso_h": 15, "leg_h": 7, "leg_w": 6, "head_w": 9, "head_h": 8, "head": "block",
         "arm_w": 4, "arm_len": 9, "cx": 23, "neck": 2, "hunch": 2}
ROBED = {"robe": True, "torso_w": 10, "torso_h": 11, "leg_h": 9}

FIGURES = {
    # ---- players
    "berserker": ("swing", {
        "skin": "d9a070", "body": "6b4a32", "legs": "5c3a20", "chest": "bare", "belt": "3a2416",
        "torso_w": 13, "torso_h": 12, "arm_w": 3, "extras": ("fur", "beard", "hair"),
        "beard": "b8502a", "hair": "b8502a", "beard_len": 6,
        "weapon": {"type": "axe", "len": 17, "back": 3, "double": True, "color": "c9d3e6"}}),
    "wizard": ("cast", dict(ROBED, **{
        "skin": "e0b088", "body": "3a4fa8", "trim": "e0b040", "belt": "2a2a63",
        "extras": ("hat", "beard"), "beard": "e8e4dc", "beard_len": 9, "hat": "3a4fa8",
        "weapon": {"type": "staff", "len": 13, "back": 12, "color": "6fe0ff"}})),
    # ---- monsters
    "orc": ("swing", {
        "skin": "6f8a4f", "body": "5c4630", "legs": "4a3a2a", "belt": "2e2218", "nose": 1,
        "torso_w": 14, "torso_h": 13, "head_w": 11, "head_h": 10, "arm_w": 3, "hunch": 2,
        "extras": ("tusks", "ears", "pauldron"), "metal": "6a6f78", "eye": "c8343c",
        "weapon": {"type": "axe", "len": 15, "back": 3, "color": "9aa0a8"}}),
    "troll": ("swing", {
        "skin": "5f8f78", "body": "5f8f78", "legs": "4f7a66", "boots": "4f7a66", "chest": "bare",
        "belt": "6b4526", "torso_w": 13, "torso_h": 14, "leg_h": 9, "head_w": 11, "head_h": 10,
        "arm_w": 3, "arm_len": 9, "hunch": 4, "neck": 3, "nose": 4, "extras": ("ears", "tusks", "hair"),
        "hair": "2e4a3a", "eye": "ffd84a",
        "weapon": {"type": "club", "len": 16, "color": "d8d0b8", "shaft": "6b4526"}}),
    "dryad": ("punch", dict(ROBED, **{
        "skin": "7a5c3c", "body": "4f3a26", "glow": "d04ad0", "nose": 0, "brow": False,
        "extras": ("branches",), "leaf": "7a3f8a", "twig": "3a2a1c", "arm_len": 8,
        "weapon": {"type": "claws", "len": 6, "color": "7a3f8a"}})),
    "wraith": ("punch", {
        "float": True, "skin": "2a2440", "body": "3a3058", "glow": "c060ff", "head": "hood",
        "torso_w": 11, "torso_h": 13, "leg_h": 6, "arm": "3a3058", "arm_len": 8,
        "weapon": {"type": "claws", "len": 5, "color": "b8a8e0"}}),
    "specter": ("punch", {
        "float": True, "skin": "cfe8f4", "body": "9fc8e0", "glow": "ffffff", "nose": 0, "brow": False,
        "torso_w": 11, "torso_h": 12, "leg_h": 6, "arm": "cfe8f4", "arm_len": 8,
        "extras": ("wisps",), "weapon": {"type": "claws", "len": 5, "color": "ffffff"}}),
    "stone_golem": ("punch", dict(GOLEM, **{
        "skin": "8a8478", "body": "8a8478", "legs": "6f6a60", "boots": "5a564e", "arm": "8a8478",
        "glow": "ffb040", "extras": ("cracks", "moss"), "near_fist": 4,
        "weapon": {"type": "fist", "len": 4, "color": "8a8478"}})),
    "crystal_golem": ("punch", dict(GOLEM, **{
        "skin": "5fa8d0", "body": "5fa8d0", "legs": "4a88b0", "boots": "3a6a90", "arm": "5fa8d0",
        "glow": "ffffff", "extras": ("crystals", "head_crystals", "cracks"), "crystal": "b8f0ff",
        "near_fist": 4, "weapon": {"type": "fist", "len": 4, "color": "8fd8f4"}})),
    "shadow_knight": ("swing", {
        "skin": "2a2a3a", "body": "34344a", "legs": "2a2a3a", "boots": "1c1626", "arm": "34344a",
        "head": "helm", "metal": "3a3a52", "glow": "ff4a4a", "chest": "tabard", "trim": "6a2a8a",
        "arm_w": 3, "extras": ("plume", "cape", "pauldron"), "plume": "6a2a8a", "cape": "3a1a4a",
        "shield": "2a2a3a", "weapon": {"type": "sword", "len": 17, "color": "7a6aa8", "guard": "6a2a8a"}}),
    "void_fiend": ("punch", {
        "skin": "4a2a6a", "body": "4a2a6a", "legs": "3a1f5a", "boots": "2a1640", "chest": "bare",
        "glow": "ff4ad0", "torso_w": 13, "torso_h": 13, "arm_w": 3, "arm_len": 8, "nose": 0,
        "extras": ("horns", "wings", "tail"), "horn": "1c1626", "wing": "2a1640",
        "weapon": {"type": "claws", "len": 5, "color": "ff8ae0"}}),
    # ---- bosses
    "boss_shard_guardian": ("punch", {
        "skin": "5c4630", "body": "4a3826", "legs": "3a2a1c", "boots": "2e2218", "arm": "5c4630",
        "glow": "5fffe0", "torso_w": 16, "torso_h": 15, "leg_h": 8, "leg_w": 5, "head_w": 10, "head_h": 9,
        "head": "block", "arm_w": 3, "arm_len": 10, "cx": 23, "neck": 2,
        "extras": ("branches", "moss", "gem", "cracks"), "leaf": "3fd0b0",
        "weapon": {"type": "claws", "len": 7, "color": "3fd0b0"}}),
    "boss_captain": ("swing", {
        "skin": "6a7a5a", "body": "6a5a4a", "legs": "4a4038", "boots": "2e2218", "arm": "6a5a4a",
        "head": "helm", "metal": "7a6a58", "glow": "6fff6a", "arm_w": 3, "torso_w": 13, "torso_h": 13,
        "belt": "3a2416", "extras": ("cape", "pauldron", "plume"), "cape": "3a4a3a", "plume": "4a5a4a",
        "weapon": {"type": "greatsword", "len": 19, "color": "9a8a6a", "guard": "6a5a3a"}}),
    "boss_vex": ("thrust", dict(ROBED, **{
        "skin": "d8c8d8", "body": "3a1f4a", "trim": "c060ff", "torso_w": 9, "eye": "c060ff",
        "extras": ("hair", "cape"), "hair": "1c1626", "cape": "2a1640", "nose": 0,
        "weapon": {"type": "rapier", "len": 16, "color": "b8a8e0", "guard": "c060ff"}})),
    "boss_vex_unbound": ("thrust", dict(ROBED, **{
        "skin": "d8c8d8", "body": "5a2a8a", "trim": "ff8ae0", "torso_w": 9, "glow": "ff8ae0",
        "extras": ("hair", "cape", "crown", "wings", "wisps"), "hair": "e8e4ff", "cape": "2a1640",
        "wing": "3a1f5a", "wisp": "ff8ae0", "nose": 0,
        "weapon": {"type": "rapier", "len": 17, "color": "ffd0f0", "guard": "ff8ae0"}})),
    "boss_ssarak": ("thrust", dict(ROBED, **{
        "skin": "e0702a", "body": "8a1f2a", "trim": "ffd84a", "head": "hood", "snout": True,
        "glow": "ffd84a", "extras": ("flame", "tail"), "belt": "ffd84a",
        "weapon": {"type": "glaive", "len": 14, "back": 12, "color": "ff9a3a", "shaft": "3a2416"}})),
    "boss_oren": ("swing", dict(ROBED, **{
        "skin": "8fb8a8", "body": "1f5a5a", "trim": "e89aa8", "glow": "6fffe0", "chest": "tabard",
        "extras": ("mitre", "beard"), "beard": "5a8a7a", "hat": "1f5a5a", "nose": 0,
        "weapon": {"type": "mace", "len": 13, "back": 3, "color": "e89aa8", "shaft": "d8d0b8"}})),
    "boss_toruun": ("thrust", {
        "float": True, "skin": "b8d8e8", "body": "5a8ab8", "glow": "ffffff", "nose": 0, "brow": False,
        "torso_w": 12, "torso_h": 13, "leg_h": 7, "arm": "b8d8e8", "arm_w": 3,
        "extras": ("feathers", "cape", "wisps", "pauldron"), "cape": "3a5a8a", "metal": "e8f4ff",
        "weapon": {"type": "lance", "len": 13, "back": 12, "color": "e8f4ff", "shaft": "d8d0b8",
                   "pennant": "7cc4f0"}}),
    "boss_ghorrum": ("punch", dict(GOLEM, **{
        "skin": "7a6248", "body": "6a5540", "legs": "5a4634", "boots": "4a3a2a", "arm": "7a6248",
        "glow": "ffd84a", "torso_w": 22, "torso_h": 17, "leg_h": 6, "leg_w": 7, "head_w": 10, "head_h": 8,
        "arm_w": 5, "arm_len": 10, "cx": 22, "near_fist": 5,
        "extras": ("cracks", "moss", "crystals", "gem"), "crystal": "ffb040",
        "weapon": {"type": "fist", "len": 5, "color": "7a6248"}})),
    "boss_malachar": ("cast", dict(ROBED, **{
        "skin": "c8c0d8", "body": "241a3a", "trim": "c060ff", "glow": "c060ff", "belt": "6a2a8a",
        "torso_w": 11, "extras": ("crown", "cape", "beard", "wisps"), "broken": True, "cape": "4a1f6a",
        "beard": "1c1626", "beard_len": 6, "wisp": "c060ff",
        "weapon": {"type": "staff", "len": 14, "back": 12, "color": "c060ff", "shaft": "1c1626"}})),
}


def figure_sheet(name):
    style, spec = FIGURES[name]
    return sheet(lambda pose: draw_figure(pose, spec), POSES[style])


# --------------------------------------------------------------------------- beasts

def _blob_path(f, points, radii, color):
    """Thick curve through `points` (quadratic segments), radius easing along `radii`."""
    n = 60
    for i in range(n + 1):
        t = i / n * (len(points) - 1)
        k = min(int(t), len(points) - 2)
        u = t - k
        x = points[k][0] + (points[k + 1][0] - points[k][0]) * u
        y = points[k][1] + (points[k + 1][1] - points[k][1]) * u
        r = radii[0] + (radii[1] - radii[0]) * i / n
        f.ellipse(x, y, r, r, color)


def _smooth(points, rounds=2):
    for _ in range(rounds):
        out = [points[0]]
        for a, b in zip(points, points[1:]):
            out += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25),
                    (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        points = out + [points[-1]]
    return points


def draw_serpent(pose):
    f = Frame()
    teal, teal_l, teal_d = shades("2f8f9a")
    belly = rgb("c8e8c0")
    hx, hy = pose["head"]
    sway = pose.get("sway", 0)
    # Coils on the ground and the tail
    f.ellipse(22, 40, 11, 3, teal_d)
    f.ellipse(24, 41, 9, 3, teal)
    f.rect(17, 43, 31, 43, belly)
    _blob_path(f, _smooth([(13, 41), (7, 38 - sway), (4, 32 - sway)]), (2.5, 0.6), teal_d)
    # Neck rising to the head
    neck = _smooth([(27, 40), (15 - sway, 31), (19, 21), (hx - 6, hy + 5), (hx - 2, hy + 1)])
    _blob_path(f, neck, (4.2, 3.0), teal)
    _blob_path(f, [(p[0] + 1.6, p[1] + 0.6) for p in neck[len(neck) // 3:]], (1.6, 1.4), belly)
    for i in range(3, len(neck) - 2, 3):                 # back fins
        px, py = neck[i]
        f.tri((px - 3, py - 1), (px - 7, py - 4), (px - 3, py + 2), teal_d)
    # Head and jaw
    gape = pose.get("gape", 0)
    f.ellipse(hx, hy, 6, 3.4, teal)
    f.ellipse(hx - 1, hy - 2, 4, 1, teal_l)
    f.tri((hx - 5, hy - 2), (hx - 10, hy - 7), (hx - 2, hy - 3), teal_d)   # crest
    f.rect(hx + 1, hy + 2 + gape, hx + 6, hy + 3 + gape, belly)
    if gape:
        f.rect(hx + 1, hy + 2, hx + 5, hy + 1 + gape, rgb("8a1f2a"))
        f.dot(hx + 5, hy + 2, TOOTH_C)
        f.dot(hx + 3, hy + 2, TOOTH_C)
        f.dot(hx + 4, hy + 1 + gape, TOOTH_C)
    f.rect(hx + 1, hy - 1, hx + 2, hy - 1, rgb("ffd84a"))
    f.dot(hx + 2, hy - 1, DARK)
    f.outline()
    return f


SERPENT_POSES = {
    "idle": [{"head": (32, 15)}, {"head": (33, 15), "sway": 1}, {"head": (33, 16), "sway": 2},
             {"head": (32, 16), "sway": 1}],
    "attack": [{"head": (26, 11), "gape": 1}, {"head": (30, 12), "gape": 3},
               {"head": (46, 26), "gape": 4, "sway": 2}, {"head": (38, 19), "gape": 1, "sway": 1}],
    "hurt": [{"head": (25, 14), "gape": 2, "sway": 2}, {"head": (28, 15), "gape": 1, "sway": 1}],
    "death": {"head": (30, 17), "gape": 2},
}


def draw_salamander(pose):
    f = Frame()
    sc, sc_l, sc_d = shades("d8502a")
    belly = rgb("ffb86a")
    lean, bob, flick = pose.get("lean", 0), pose.get("bob", 0), pose.get("flick", 0)
    cx, cy = 25 + lean, 35 + bob
    # Tail curling up behind, tipped with fire
    tail = _smooth([(cx - 9, cy + 1), (cx - 17, cy + 3), (cx - 21, cy - 3 - flick % 2), (cx - 18, cy - 9)])
    _blob_path(f, tail, (3.2, 1.2), sc_d)
    tx, ty = tail[-1]
    f.tri((tx - 3, ty + 1), (tx + 3, ty + 1), (tx - 1 + flick % 2, ty - 8), rgb("ff7a2a"))
    f.tri((tx - 1, ty + 1), (tx + 2, ty + 1), (tx, ty - 4), rgb("ffd84a"))
    # Far legs, body, near legs
    step = pose.get("step", 0)
    for lx in (cx - 7 - step, cx + 7 + step):
        f.line(lx, cy + 2, lx + 1, 43, sc_d, 2)
        f.rect(lx, 43, lx + 4, 44, sc_d)
    f.ellipse(cx, cy, 12, 5, sc)
    f.ellipse(cx - 1, cy - 2, 9, 2, sc_l)
    f.rect(cx - 8, cy + 4, cx + 9, cy + 4, belly)
    for dx in (-6, -1, 4):                                  # dark bands
        f.rect(cx + dx, cy - 4, cx + dx + 1, cy + 1, sc_d)
    for lx in (cx - 10 + step, cx + 4 - step):
        f.line(lx, cy + 3, lx + 2, 43, sc, 2)
        f.rect(lx + 1, 43, lx + 5, 44, sc)
    # Flames along the spine
    for i, dx in enumerate((-8, -4, 0, 4)):
        tall = 4 + ((i + flick) % 2) * 3
        f.tri((cx + dx - 2, cy - 4), (cx + dx + 2, cy - 4), (cx + dx - 1, cy - 4 - tall), rgb("ff7a2a"))
        f.tri((cx + dx - 1, cy - 4), (cx + dx + 1, cy - 4), (cx + dx, cy - 2 - tall), rgb("ffd84a"))
    # Head
    hx, hy = cx + 14 + pose.get("reach", 0), cy - 3 + pose.get("dip", 0)
    gape = pose.get("gape", 0)
    f.line(cx + 9, cy - 1, hx - 3, hy, sc, 5)
    f.ellipse(hx, hy, 6, 3.6, sc)
    f.ellipse(hx - 1, hy - 2, 4, 1, sc_l)
    f.rect(hx, hy + 2 + gape, hx + 6, hy + 3 + gape, belly)
    if gape:
        f.rect(hx, hy + 2, hx + 5, hy + 1 + gape, rgb("ffd84a"))
        f.dot(hx + 5, hy + 2, TOOTH_C)
    f.rect(hx + 1, hy - 1, hx + 2, hy - 1, rgb("ffe27a"))
    f.dot(hx + 2, hy - 1, DARK)
    f.outline()
    return f


SALAMANDER_POSES = {
    "idle": [{"flick": 0}, {"flick": 1}, {"flick": 2, "bob": 1}, {"flick": 3, "bob": 1}],
    "attack": [{"lean": -3, "reach": -2, "dip": -3, "gape": 1, "flick": 1},
               {"lean": 0, "reach": 0, "dip": -4, "gape": 3, "flick": 2, "step": 1},
               {"lean": 6, "reach": 5, "dip": 2, "gape": 4, "flick": 3, "step": 2},
               {"lean": 3, "reach": 2, "gape": 1, "flick": 0, "step": 1}],
    "hurt": [{"lean": -4, "dip": -3, "gape": 2, "bob": 1, "flick": 1}, {"lean": -2, "dip": -1, "gape": 1, "bob": 1}],
    "death": {"gape": 2, "bob": 1},
}


def all_sheets():
    """name -> sheet image, for every character."""
    sheets = {
        "knight": sheet(draw_knight, KNIGHT_POSES),
        "goblin": sheet(draw_goblin, GOBLIN_POSES),
        "serpent": sheet(draw_serpent, SERPENT_POSES),
        "salamander": sheet(draw_salamander, SALAMANDER_POSES),
    }
    for name in FIGURES:
        sheets[name] = figure_sheet(name)
    return sheets


def overview(sheets, scale=3):
    """One image with each character's idle and strike frame, labelled by position (row-major)."""
    names = sorted(sheets)
    cols = 6
    rows = -(-len(names) // cols)
    img = Image.new("RGBA", (cols * FW * 2, rows * FH), (58, 51, 38, 255))
    for i, name in enumerate(names):
        x, y = (i % cols) * FW * 2, (i // cols) * FH
        idle = sheets[name].crop((0, 0, FW, FH))
        strike = sheets[name].crop((2 * FW, FH, 3 * FW, 2 * FH))
        img.paste(idle, (x, y), idle)
        img.paste(strike, (x + FW, y), strike)
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST), names


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--preview", type=Path, help="also write 4x previews and overview.png to this directory")
    p.add_argument("--only", default="", help="comma-separated sheet names (default: all)")
    args = p.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    sheets = all_sheets()
    images = dict(sheets, backdrop_forest=backdrop_forest())
    only = {n.strip() for n in args.only.split(",") if n.strip()}
    for name, img in images.items():
        if only and name not in only:
            continue
        img.save(OUT / f"{name}.png")
        print(f"{name}.png {img.width}x{img.height}")
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            big = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
            bg = Image.new("RGBA", big.size, (58, 51, 38, 255))
            bg.paste(big, (0, 0), big)
            bg.save(args.preview / f"{name}_4x.png")
    if args.preview:
        img, names = overview(sheets)
        img.save(args.preview / "overview.png")
        print("overview.png (idle + strike, row-major): " + ", ".join(names))


if __name__ == "__main__":
    main()
