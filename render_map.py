"""Render the treasure map for the Charm the Cartographers entry.

Draws "The Isle of Borrowed Winds" with PIL at 2x supersample and saves the
downscaled result as ``entry.png`` next to this file. The shipped entrypoint
(``main.py``) never runs this: it only copies the committed ``entry.png``.
Fonts are vendored under ``fonts/`` so the render is reproducible.

v2: a denser chart — twelve labeled places (the Widow's Lantern lighthouse,
the Hungry Maw whirlpool, Wrecker's Cove, the Ruined Abbey, Cinderfall and
the market town of Bramblewick join the original six), dashed sailing roads,
and deeper sea/ink tones so every feature pops harder than in v1.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
S = 2  # supersample factor; final image is 1024x1024
W = 1024 * S

INK = (56, 40, 22)
INK_DARK = (42, 30, 15)
SEA = (144, 170, 148)
SEA_DEEP = (122, 152, 132)
SEA_PALE = (168, 192, 164)
LAND = (238, 217, 158)
LAND_LIGHT = (247, 232, 186)
SHOAL = (202, 220, 188)
PARCH = (233, 216, 170)
MOUNTAIN = (110, 78, 48)
PINE = (56, 82, 48)
PINE_DARK = (44, 68, 38)
RIVER = (104, 148, 166)
LAGOON = (143, 188, 188)
ROOF = (148, 82, 50)
RED = (172, 48, 36)
PATH_INK = (120, 72, 32)
STONE = (156, 146, 128)
STONE_DARK = (140, 130, 112)
ROUTE_INK = (52, 78, 78)


def F(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size * S))


SERIF = "NotoSerif-Regular.ttf"
SERIF_B = "NotoSerif-Bold.ttf"
SERIF_I = "NotoSerif-Italic.ttf"
DISPLAY_B = "NotoSerifDisplay-Bold.ttf"


def pt(x, y):
    return (x * S, y * S)


def gauss(a, c, w):
    d = (a - c + 180) % 360 - 180
    return math.exp(-(d * d) / (2 * w * w))


CX, CY, BASE_R = 505, 508, 300


def radius(theta_deg):
    t = math.radians(theta_deg)
    r = BASE_R * (
        1
        + 0.15 * math.sin(3 * t + 0.7)
        + 0.10 * math.sin(5 * t + 2.1)
        + 0.06 * math.sin(8 * t + 0.3)
        + 0.045 * math.sin(13 * t + 1.7)
    )
    r += 58 * gauss(theta_deg, 55, 13)  # Cape of Gulls headland (south-east)
    r -= 80 * gauss(theta_deg, 128, 13)  # lagoon bay (south-west)
    r -= 34 * gauss(theta_deg, 288, 10)  # small north bay
    r += 26 * gauss(theta_deg, 175, 16)  # west bulge
    return r


def coast_point(theta_deg, frac=1.0):
    r = radius(theta_deg) * frac
    t = math.radians(theta_deg)
    return (CX + r * math.cos(t), CY + r * math.sin(t))


def island_polygon(scale=1.0):
    pts = []
    for i in range(360):
        x, y = coast_point(i, scale)
        pts.append((x, y))
    for _ in range(2):  # smooth
        pts = [
            (
                (pts[i - 1][0] + 2 * pts[i][0] + pts[(i + 1) % 360][0]) / 4,
                (pts[i - 1][1] + 2 * pts[i][1] + pts[(i + 1) % 360][1]) / 4,
            )
            for i in range(360)
        ]
    return [pt(x, y) for x, y in pts]


def shifted_polygon(scale, dx, dy):
    return [(x + dx * S, y + dy * S) for x, y in island_polygon(scale)]


def catmull_rom(points, samples_per_seg=14):
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(samples_per_seg):
            t = j / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(
                (
                    0.5
                    * (
                        2 * p1[0]
                        + (-p0[0] + p2[0]) * t
                        + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                        + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                    ),
                    0.5
                    * (
                        2 * p1[1]
                        + (-p0[1] + p2[1]) * t
                        + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                        + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                    ),
                )
            )
    out.append(points[-1])
    return out


def dashed_route(draw, points, color=ROUTE_INK, width=2.2, dash=11, gap=8):
    """A dashed sailing road along a Catmull-Rom curve through points."""
    curve = catmull_rom(points, samples_per_seg=16)
    seg = []
    acc = 0.0
    drawing = True
    left = dash
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        d = math.hypot(x1 - x0, y1 - y0)
        acc += d
        if drawing:
            seg.append((x0, y0))
            if acc >= left:
                seg.append((x1, y1))
                if len(seg) > 1:
                    draw.line([pt(x, y) for x, y in seg], fill=color + (150,), width=int(width * S))
                seg = []
                drawing = False
                acc = 0.0
                left = gap
        else:
            if acc >= left:
                drawing = True
                acc = 0.0
                left = dash
                seg = [(x1, y1)]


def depth_dots(draw, cx, cy, r, n=16, a0=0, a1=360, squash=1.0):
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * k / max(n - 1, 1))
        x0, y0 = cx + r * math.cos(a), cy + r * squash * math.sin(a)
        draw.ellipse([pt(x0 - 1.8, y0 - 1.8), pt(x0 + 1.8, y0 + 1.8)], fill=(70, 96, 96))


def label(draw, xy, text, font_name=SERIF_B, size=29, fill=INK_DARK, sub=None):
    f = F(font_name, size)
    draw.text(
        pt(*xy),
        text,
        font=f,
        fill=fill,
        anchor="mm",
        stroke_width=int(3.4 * S),
        stroke_fill=LAND_LIGHT,
    )
    if sub:
        draw.text(
            pt(xy[0], xy[1] + size * 0.95),
            sub,
            font=F(SERIF_I, 16),
            fill=(90, 66, 38),
            anchor="mm",
            stroke_width=int(3 * S),
            stroke_fill=LAND_LIGHT,
        )


def draw_peak(draw, x, y, h, w, crater=False):
    """A hatched mountain peak sitting on baseline y."""
    apex = (x, y - h)
    left = (x - w / 2, y)
    right = (x + w / 2, y)
    draw.polygon([pt(*apex), pt(*left), pt(*right)], fill=(224, 196, 140))
    draw.line([pt(*apex), pt(*left)], fill=INK, width=int(2.2 * S))
    draw.line([pt(*apex), pt(*right)], fill=INK, width=int(2.2 * S))
    # jagged shoulder lines
    draw.line([pt(x - w * 0.18, y - h * 0.55), pt(*apex)], fill=INK, width=int(1.4 * S))
    draw.line([pt(x + w * 0.22, y - h * 0.5), pt(*apex)], fill=INK, width=int(1.4 * S))
    # hatching on the shaded (right) side
    for i in range(4):
        t = 0.25 + i * 0.17
        hx = x + (w / 2) * t * 0.82
        hy = y - h * (1 - t)
        draw.line(
            [pt(hx, hy), pt(hx - w * 0.1, hy + h * 0.13)],
            fill=MOUNTAIN,
            width=int(1.3 * S),
        )
    if crater:
        draw.ellipse(
            [pt(x - w * 0.12, y - h - 5), pt(x + w * 0.12, y - h + 6)],
            fill=(146, 74, 48),
            outline=INK_DARK,
            width=int(1.8 * S),
        )
        # smoke curls
        for k in range(2):
            sx, sy = x + 10 + k * 15, y - h - 22 - k * 13
            draw.arc(
                [pt(sx - 11, sy - 9), pt(sx + 11, sy + 9)],
                start=300,
                end=140,
                fill=(105, 88, 66),
                width=int(2 * S),
            )


def draw_pine(draw, x, y, s, tone=PINE):
    draw.line([pt(x, y), pt(x, y - s * 0.25)], fill=(92, 64, 36), width=int(1.6 * S))
    for i, (ww, yy) in enumerate([(0.62, 0.52), (0.48, 0.78), (0.32, 1.0)]):
        top = (x, y - s * yy)
        bl = (x - s * ww / 2, y - s * (yy - 0.3))
        br = (x + s * ww / 2, y - s * (yy - 0.3))
        draw.polygon([pt(*top), pt(*bl), pt(*br)], fill=tone if i % 2 == 0 else PINE_DARK)


def draw_house(draw, x, y, s):
    draw.rectangle(
        [pt(x - s / 2, y - s * 0.55), pt(x + s / 2, y)],
        fill=(243, 232, 198),
        outline=INK,
        width=int(1.5 * S),
    )
    draw.polygon(
        [pt(x - s * 0.68, y - s * 0.55), pt(x + s * 0.68, y - s * 0.55), pt(x, y - s * 1.05)],
        fill=ROOF,
        outline=INK_DARK,
        width=int(1.2 * S),
    )
    draw.rectangle(
        [pt(x - s * 0.12, y - s * 0.3), pt(x + s * 0.12, y)],
        fill=(110, 76, 44),
    )


def draw_anchor(draw, x, y, s):
    draw.ellipse(
        [pt(x - s * 0.16, y - s), pt(x + s * 0.16, y - s * 0.68)],
        outline=INK_DARK,
        width=int(2 * S),
    )
    draw.line([pt(x, y - s * 0.68), pt(x, y + s * 0.55)], fill=INK_DARK, width=int(2.4 * S))
    draw.line(
        [pt(x - s * 0.34, y - s * 0.3), pt(x + s * 0.34, y - s * 0.3)],
        fill=INK_DARK,
        width=int(2.2 * S),
    )
    draw.arc(
        [pt(x - s * 0.52, y - s * 0.1), pt(x + s * 0.52, y + s * 0.75)],
        start=20,
        end=160,
        fill=INK_DARK,
        width=int(2.4 * S),
    )
    for sx in (-1, 1):
        draw.polygon(
            [
                pt(x + sx * s * 0.52, y + s * 0.42),
                pt(x + sx * s * 0.3, y + s * 0.34),
                pt(x + sx * s * 0.52, y + s * 0.16),
            ],
            fill=INK_DARK,
        )


def draw_compass(draw, cx, cy, r):
    # rhumb star: long cardinal points, short diagonals
    for k in range(8):
        ang = math.radians(k * 45)
        ln = r if k % 2 == 0 else r * 0.55
        wdt = r * (0.16 if k % 2 == 0 else 0.12)
        tip = (cx + ln * math.cos(ang), cy + ln * math.sin(ang))
        perp = ang + math.pi / 2
        b1 = (cx + wdt * math.cos(perp), cy + wdt * math.sin(perp))
        b2 = (cx - wdt * math.cos(perp), cy - wdt * math.sin(perp))
        draw.polygon([pt(*tip), pt(*b1), pt(cx, cy)], fill=(196, 160, 96), outline=INK)
        draw.polygon([pt(*tip), pt(*b2), pt(cx, cy)], fill=(120, 88, 48), outline=INK)
    draw.ellipse(
        [pt(cx - r * 1.12, cy - r * 1.12), pt(cx + r * 1.12, cy + r * 1.12)],
        outline=INK,
        width=int(1.6 * S),
    )
    draw.ellipse(
        [pt(cx - r * 0.14, cy - r * 0.14), pt(cx + r * 0.14, cy + r * 0.14)],
        fill=INK_DARK,
    )
    for txt, dx, dy in [("N", 0, -r - 17), ("S", 0, r + 17), ("E", r + 17, 0), ("W", -r - 17, 0)]:
        draw.text(
            pt(cx + dx, cy + dy),
            txt,
            font=F(SERIF_B, 21),
            fill=INK_DARK,
            anchor="mm",
            stroke_width=int(2.6 * S),
            stroke_fill=SEA_PALE,
        )


def draw_serpent(draw, x, y):
    # three filled humps breaking the surface, waterline at y
    for hx in (0, 42, 84):
        draw.pieslice(
            [pt(x + hx - 25, y - 17), pt(x + hx + 25, y + 17)],
            180,
            360,
            fill=(96, 126, 100),
            outline=INK_DARK,
            width=int(2.2 * S),
        )
        draw.line([pt(x + hx - 25, y), pt(x + hx + 25, y)], fill=(62, 92, 100), width=int(1.6 * S))
    # neck rising at the right end, with a small head and snout
    draw.arc([pt(x + 92, y - 40), pt(x + 132, y + 14)], 272, 82, fill=INK_DARK, width=int(4.4 * S))
    draw.ellipse([pt(x + 110, y - 46), pt(x + 142, y - 28)], fill=(96, 126, 100), outline=INK_DARK, width=int(1.8 * S))
    draw.polygon([pt(x + 138, y - 40), pt(x + 152, y - 34), pt(x + 138, y - 29)], fill=(96, 126, 100), outline=INK_DARK, width=int(1.4 * S))
    draw.ellipse([pt(x + 124, y - 41), pt(x + 130, y - 35)], fill=(250, 248, 238))
    draw.ellipse([pt(x + 126, y - 39.4), pt(x + 129.4, y - 36)], fill=INK_DARK)
    draw.line([pt(x + 150, y - 33), pt(x + 160, y - 30)], fill=RED, width=int(1.6 * S))


def draw_ship(draw, x, y, s=1.0):
    hull = [(x - 34 * s, y), (x + 34 * s, y), (x + 22 * s, y + 13 * s), (x - 22 * s, y + 13 * s)]
    draw.polygon([pt(*p) for p in hull], fill=(120, 82, 48), outline=INK_DARK, width=int(1.6 * S))
    for mx, hh in [(x - 8 * s, 44 * s), (x + 14 * s, 34 * s)]:
        draw.line([pt(mx, y), pt(mx, y - hh)], fill=INK_DARK, width=int(2 * S))
    draw.polygon(
        [pt(x - 8 * s, y - 44 * s), pt(x - 8 * s, y - 6 * s), pt(x + 12 * s, y - 6 * s)],
        fill=(246, 238, 214),
        outline=INK,
        width=int(1.3 * S),
    )
    draw.polygon(
        [pt(x + 14 * s, y - 34 * s), pt(x + 14 * s, y - 5 * s), pt(x + 30 * s, y - 5 * s)],
        fill=(246, 238, 214),
        outline=INK,
        width=int(1.3 * S),
    )
    draw.polygon(
        [pt(x - 8 * s, y - 44 * s), pt(x + 2 * s, y - 40 * s), pt(x - 8 * s, y - 36 * s)],
        fill=RED,
    )
    draw.arc([pt(x - 26 * s, y + 14 * s), pt(x - 4 * s, y + 24 * s)], 180, 350, fill=(70, 100, 110), width=int(1.8 * S))
    draw.arc([pt(x + 2 * s, y + 14 * s), pt(x + 24 * s, y + 24 * s)], 180, 350, fill=(70, 100, 110), width=int(1.8 * S))


def draw_lighthouse(draw, x, y):
    """The Widow's Lantern: a banded tower on the rocks, base at (x, y)."""
    # light rays first, so the tower sits over their root
    draw.polygon(
        [pt(x + 4, y - 56), pt(x + 86, y - 84), pt(x + 86, y - 34)],
        fill=(255, 226, 140, 52),
    )
    draw.polygon(
        [pt(x - 4, y - 56), pt(x - 78, y - 80), pt(x - 74, y - 30)],
        fill=(255, 226, 140, 36),
    )
    # rocks
    draw.ellipse([pt(x - 24, y - 6), pt(x + 4, y + 9)], fill=(118, 112, 100), outline=INK_DARK, width=int(1.4 * S))
    draw.ellipse([pt(x - 2, y - 8), pt(x + 26, y + 8)], fill=(130, 124, 110), outline=INK_DARK, width=int(1.4 * S))
    # tower in three bands (half-width shrinks 11 -> 7 up the 46px shaft)
    bands = [(0, -15, (244, 238, 222)), (-15, -30, RED), (-30, -46, (244, 238, 222))]
    for y0, y1, tone in bands:
        hw0 = 11 + (7 - 11) * (-y0 / 46)
        hw1 = 11 + (7 - 11) * (-y1 / 46)
        draw.polygon(
            [pt(x - hw0, y + y0), pt(x + hw0, y + y0), pt(x + hw1, y + y1), pt(x - hw1, y + y1)],
            fill=tone,
            outline=INK_DARK,
            width=int(1.4 * S),
        )
    draw.rectangle([pt(x - 3, y - 13), pt(x + 3, y)], fill=(90, 60, 30))  # door
    draw.rectangle([pt(x - 10, y - 52), pt(x + 10, y - 46)], fill=(110, 78, 44), outline=INK_DARK, width=int(1.2 * S))  # gallery
    draw.rectangle([pt(x - 6, y - 60), pt(x + 6, y - 52)], fill=(255, 216, 120), outline=INK_DARK, width=int(1.4 * S))  # lamp
    draw.polygon([pt(x - 9, y - 60), pt(x + 9, y - 60), pt(x, y - 70)], fill=INK_DARK)  # cap


def draw_whirlpool(draw, x, y, r=34):
    """The Hungry Maw: a perspective-squashed spiral with foam and debris."""
    pts = []
    turns = 4.6 * math.pi
    for i in range(220):
        th = turns * i / 219
        rr = 3 + (r - 3) * th / turns
        pts.append((x + rr * math.cos(th), y + 0.8 * rr * math.sin(th)))
    draw.line([pt(px, py) for px, py in pts], fill=(44, 72, 82), width=int(2.6 * S))
    for rr, a0 in [(r + 7, 20), (r + 7, 150), (r + 7, 265)]:
        draw.arc(
            [pt(x - rr, y - 0.8 * rr), pt(x + rr, y + 0.8 * rr)],
            start=a0,
            end=a0 + 55,
            fill=(44, 72, 82),
            width=int(2 * S),
        )
    for dx, dy in [(-r - 4, -6), (r - 2, -14), (-8, 0.8 * r + 4), (16, 0.8 * r + 8)]:
        draw.ellipse([pt(x + dx - 2.2, y + dy - 2.2), pt(x + dx + 2.2, y + dy + 2.2)], fill=(238, 246, 242))
    # a doomed spar, tilted at the rim
    draw.line([pt(x - 20, y - 12), pt(x - 10, y + 8)], fill=(104, 72, 44), width=int(3 * S))
    draw.polygon([pt(x - 19, y - 12), pt(x - 11, y - 4), pt(x - 20, y - 2)], fill=(238, 228, 200), outline=INK_DARK, width=int(1 * S))


def draw_tentacles(draw, x, y):
    """Three kraken arms curling out of the water."""
    for dx, h in [(0, 30), (17, 21), (34, 36)]:
        draw.arc(
            [pt(x + dx - 7, y - h), pt(x + dx + 7, y + 6)],
            start=195,
            end=345,
            fill=(104, 84, 114),
            width=int(4.4 * S),
        )
        draw.ellipse([pt(x + dx - 3, y - h - 3), pt(x + dx + 3, y - h + 3)], fill=(104, 84, 114))


def draw_wreck(draw, x, y):
    """The wreck at Wrecker's Cove: a hull stove in and listing hard."""
    hull = [(x - 31, y + 11), (x + 29, y - 13), (x + 17, y + 3), (x - 17, y + 17)]
    draw.polygon([pt(*p) for p in hull], fill=(94, 64, 38), outline=INK_DARK, width=int(1.6 * S))
    for dx in (-14, 0, 13):  # ribs
        draw.line([pt(x + dx, y + 9 - dx * 0.35), pt(x + dx, y - 3 - dx * 0.35)], fill=INK_DARK, width=int(1.2 * S))
    # the crack that sank her: a jagged split across the hull
    crack = [(x - 2, y - 6), (x + 2, y - 1), (x - 3, y + 4), (x + 1, y + 10)]
    draw.line([pt(*p) for p in crack], fill=(30, 20, 10), width=int(2.2 * S))
    # main mast snapped in two: stump on deck, top half hanging by the rigging
    draw.line([pt(x - 4, y + 1), pt(x - 9, y - 13)], fill=INK_DARK, width=int(3 * S))
    draw.line([pt(x - 16, y - 30), pt(x - 11, y - 17)], fill=INK_DARK, width=int(2.6 * S))
    draw.line([pt(x - 9, y - 13), pt(x - 14, y - 26)], fill=INK_DARK, width=int(1 * S))  # rigging
    draw.polygon(
        [pt(x - 16, y - 30), pt(x - 15, y - 15), pt(x - 8, y - 19), pt(x - 5, y - 13), pt(x - 2, y - 21)],
        fill=(206, 196, 176),
        outline=INK,
        width=int(1.1 * S),
    )  # torn, limp sail
    draw.line([pt(x + 14, y - 4), pt(x + 21, y - 18)], fill=INK_DARK, width=int(2.4 * S))  # fore stump
    # debris: a barrel and a loose plank drifting off the stern
    draw.ellipse([pt(x + 36, y + 6), pt(x + 46, y + 14)], fill=(120, 82, 48), outline=INK_DARK, width=int(1.1 * S))
    draw.line([pt(x - 46, y + 16), pt(x - 34, y + 12)], fill=(104, 72, 44), width=int(2.6 * S))
    wave(draw, x - 26, y + 20, 0.9)
    wave(draw, x + 10, y + 22, 0.8)


def draw_abbey(draw, x, y):
    """The Ruined Abbey: a broken tower, a roofless wall, fallen stone."""
    # roofless wall to the right of the tower
    wall = [(x + 10, y - 24), (x + 20, y - 30), (x + 27, y - 22), (x + 38, y - 27), (x + 38, y), (x + 10, y)]
    draw.polygon([pt(*p) for p in wall], fill=STONE_DARK, outline=INK, width=int(1.4 * S))
    # tower with a jagged broken top
    tower = [(x - 16, y), (x - 16, y - 46), (x - 8, y - 38), (x - 1, y - 52), (x + 6, y - 42), (x + 10, y - 48), (x + 10, y)]
    draw.polygon([pt(*p) for p in tower], fill=STONE, outline=INK, width=int(1.5 * S))
    draw.pieslice([pt(x - 8, y - 40), pt(x + 2, y - 24)], 180, 360, fill=INK_DARK)  # arched window
    draw.rectangle([pt(x - 8, y - 32), pt(x + 2, y - 18)], fill=INK_DARK)
    draw.rectangle([pt(x - 5, y - 12), pt(x + 1, y)], fill=(70, 54, 36))  # doorway
    # fallen column and rubble
    draw.rectangle([pt(x - 26, y + 5), pt(x - 2, y + 11)], fill=STONE_DARK, outline=INK, width=int(1.1 * S))
    for dx, dy, rr in [(16, 4, 3.4), (26, 7, 2.6), (6, 8, 2.4)]:
        draw.ellipse([pt(x + dx - rr, y + dy - rr * 0.6), pt(x + dx + rr, y + dy + rr * 0.6)], fill=STONE, outline=INK, width=int(1 * S))
    # a bare dead tree keeping watch
    draw.line([pt(x + 50, y + 2), pt(x + 52, y - 24)], fill=(92, 64, 36), width=int(2.2 * S))
    draw.line([pt(x + 52, y - 18), pt(x + 42, y - 28)], fill=(92, 64, 36), width=int(1.6 * S))
    draw.line([pt(x + 52, y - 14), pt(x + 62, y - 24)], fill=(92, 64, 36), width=int(1.6 * S))


def draw_waterfall(draw, x, y):
    """Cinderfall: white water dropping over the river's rock step."""
    draw.line([pt(x - 10, y - 12), pt(x + 10, y - 12)], fill=INK, width=int(2 * S))  # rock lip
    for dx in (-6, 0, 6):
        draw.line([pt(x + dx, y - 12), pt(x + dx * 1.35, y + 9)], fill=(233, 245, 245), width=int(2.4 * S))
    for rr in (6, 11, 16):
        draw.arc([pt(x - rr, y + 2), pt(x + rr, y + 16)], 15, 165, fill=(240, 248, 248), width=int(1.8 * S))


def draw_market_town(draw):
    """Bramblewick: a second settlement with a striped market stall."""
    for hx, hy, hs in [(638, 700, 24), (666, 716, 27), (694, 698, 23), (652, 736, 21)]:
        draw_house(draw, hx, hy, hs)
    # market stall with a striped awning
    draw.rectangle([pt(694, 724), pt(722, 740)], fill=(243, 232, 198), outline=INK, width=int(1.3 * S))
    draw.polygon([pt(690, 724), pt(726, 724), pt(719, 711), pt(697, 711)], fill=ROOF, outline=INK_DARK, width=int(1.1 * S))
    for sx in (700, 708, 716):
        draw.line([pt(sx, 712.5), pt(sx - 2, 723)], fill=(246, 238, 214), width=int(2.2 * S))
    for dx in (700, 716):
        draw.line([pt(dx, 724), pt(dx, 740)], fill=(110, 78, 44), width=int(1.6 * S))


def wave(draw, x, y, s=1.0, alpha=110):
    draw.arc([pt(x - 11 * s, y - 5 * s), pt(x + 1 * s, y + 6 * s)], 180, 350, fill=(62, 92, 100), width=int(1.7 * S))
    draw.arc([pt(x - 1 * s, y - 5 * s), pt(x + 11 * s, y + 6 * s)], 180, 350, fill=(62, 92, 100), width=int(1.7 * S))


def render():
    random.seed(20261124)
    img = Image.new("RGB", (W, W), SEA)
    draw = ImageDraw.Draw(img, "RGBA")

    # mottled sea: soft blotches of lighter/deeper wash
    for _ in range(46):
        bx, by = random.uniform(0, 1024), random.uniform(0, 1024)
        br = random.uniform(60, 190)
        tone = random.choice([SEA_PALE, SEA_DEEP, (160, 184, 158)])
        draw.ellipse([pt(bx - br, by - br * 0.6), pt(bx + br, by + br * 0.6)], fill=tone + (36,))

    # rhumb lines from the compass point, under everything else
    ccx, ccy = 150, 150
    for k in range(16):
        ang = math.radians(k * 22.5)
        ex, ey = ccx + 1200 * math.cos(ang), ccy + 1200 * math.sin(ang)
        draw.line([pt(ccx, ccy), pt(ex, ey)], fill=(56, 40, 22, 30), width=int(1.1 * S))

    # island: soft shadow, shoal ring, land, double-line coast
    draw.polygon(shifted_polygon(1.05, 7, 10), fill=(104, 130, 106))
    draw.polygon(island_polygon(1.055), fill=SHOAL)
    draw.polygon(island_polygon(1.028), outline=(110, 132, 102), width=int(2 * S))
    draw.polygon(island_polygon(1.0), fill=LAND)
    inner = island_polygon(0.965)
    draw.line(inner + [inner[0]], fill=(196, 164, 104), width=int(1.6 * S))
    coast = island_polygon(1.0)
    draw.line(coast + [coast[0]], fill=INK, width=int(3 * S))
    # interior lift: a soft lighter wash in the middle of the island
    draw.ellipse([pt(300, 290), pt(720, 730)], fill=LAND_LIGHT + (52,))

    # --- dashed sailing roads, kept in open water ---
    dashed_route(draw, [(520, 848), (700, 838), (822, 762), (852, 622), (850, 472), (838, 336), (826, 292)])
    dashed_route(draw, [(438, 848), (300, 836), (210, 722), (206, 600), (250, 435), (325, 232), (378, 172)])
    dashed_route(draw, [(624, 268), (700, 250), (788, 258)])

    # --- the river, from the volcano's shoulder down to the lagoon ---
    river_pts = catmull_rom([(498, 408), (466, 466), (478, 524), (428, 574), (386, 622), (362, 668)])
    draw.line([pt(x, y) for x, y in river_pts], fill=RIVER, width=int(8 * S), joint="curve")
    draw.line([pt(x, y) for x, y in river_pts], fill=(172, 204, 208), width=int(3 * S), joint="curve")
    draw_waterfall(draw, 473, 500)

    # --- the lagoon, carved into the south-west bay (irregular blob) ---
    lag = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lag)
    blob = []
    for a in range(0, 360, 6):
        t = math.radians(a)
        rr = 1 + 0.10 * math.sin(3 * t + 1.2) + 0.07 * math.sin(6 * t + 0.4)
        blob.append(pt(360 + 104 * rr * math.cos(t), 689 + 54 * rr * math.sin(t)))
    ld.polygon(blob, fill=LAGOON + (238,), outline=INK + (255,), width=int(2 * S))
    blob2 = []
    for a in range(0, 360, 8):
        t = math.radians(a)
        rr = 1 + 0.09 * math.sin(4 * t + 2.0)
        blob2.append(pt(362 + 74 * rr * math.cos(t), 690 + 36 * rr * math.sin(t)))
    ld.polygon(blob2, outline=(228, 242, 238, 170), width=int(2 * S))
    img.paste(Image.alpha_composite(img.convert("RGBA"), lag).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    mist = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    md = ImageDraw.Draw(mist)
    md.ellipse([pt(290, 624), pt(430, 660)], fill=(250, 248, 238, 42))
    mist = mist.filter(ImageFilter.GaussianBlur(7 * S))
    img.paste(Image.alpha_composite(img.convert("RGBA"), mist).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(4):  # mist curls over the lagoon
        mx, my = 300 + i * 36, 630 - (i % 2) * 12
        draw.arc([pt(mx - 25, my - 11), pt(mx + 25, my + 13)], 180, 350, fill=(250, 248, 238, 195), width=int(3.2 * S))

    # --- mountains: Mount Cinder and its hatched range ---
    draw_peak(draw, 520, 402, 96, 118, crater=True)
    draw_peak(draw, 588, 420, 62, 84)
    draw_peak(draw, 644, 444, 48, 66)
    draw_peak(draw, 466, 428, 54, 76)
    draw_peak(draw, 420, 452, 40, 58)

    # --- the Ruined Abbey, west of the river ---
    draw_abbey(draw, 322, 470)

    # --- the Whispering Pines ---
    rng = random.Random(7)
    for _ in range(38):
        px = 690 + rng.gauss(0, 52)
        py = 478 + rng.gauss(0, 40)
        if 600 < px < 790 and 400 < py < 560:
            draw_pine(draw, px, py, rng.uniform(20, 32), tone=rng.choice([PINE, PINE_DARK, (66, 94, 54)]))
    draw_pine(draw, 640, 520, 26)
    draw_pine(draw, 742, 522, 24)

    # --- the dotted smuggler's path and the treasure ---
    path_pts = catmull_rom([(486, 762), (548, 688), (588, 592), (602, 502), (606, 442)], samples_per_seg=10)
    for i in range(0, len(path_pts), 3):
        x, y = path_pts[i]
        draw.ellipse([pt(x - 3.4, y - 3.4), pt(x + 3.4, y + 3.4)], fill=PATH_INK)
    tx, ty = 612, 408
    draw.line([pt(tx - 15, ty - 15), pt(tx + 15, ty + 15)], fill=RED, width=int(6 * S))
    draw.line([pt(tx - 15, ty + 15), pt(tx + 15, ty - 15)], fill=RED, width=int(6 * S))
    for sx, sy in [(tx - 34, ty - 26), (tx + 38, ty + 8), (tx - 6, ty + 36)]:
        draw.line([pt(sx - 5, sy), pt(sx + 5, sy)], fill=(196, 150, 60), width=int(2 * S))
        draw.line([pt(sx, sy - 5), pt(sx, sy + 5)], fill=(196, 150, 60), width=int(2 * S))

    # --- Port Meridian: harbour town on the south coast ---
    for hx, hy, hs in [(424, 796, 21), (452, 806, 25), (484, 808, 22), (512, 800, 19), (402, 786, 17)]:
        draw_house(draw, hx, hy, hs)
    draw.line([pt(436, 818), pt(516, 818)], fill=(110, 78, 44), width=int(3 * S))  # jetty
    for jx in (452, 480, 506):
        draw.line([pt(jx, 818), pt(jx, 830)], fill=(110, 78, 44), width=int(2 * S))
    draw_anchor(draw, 566, 818, 27)

    # --- Bramblewick: the market town inland from the cape ---
    draw_market_town(draw)

    # --- Cape of Gulls: a small flock over the water east of the cape ---
    for gx, gy in [(820, 700), (858, 678), (792, 724), (884, 716)]:
        draw.arc([pt(gx - 14, gy - 8), pt(gx, gy + 8)], 200, 340, fill=INK_DARK, width=int(2.6 * S))
        draw.arc([pt(gx, gy - 8), pt(gx + 14, gy + 8)], 200, 340, fill=INK_DARK, width=int(2.6 * S))

    # --- the Sunken Bell, in the north-east shallows ---
    bx, by = 818, 262
    depth_dots(draw, bx, by, 30, n=14)
    depth_dots(draw, bx, by, 40, n=18)
    draw.polygon([pt(bx - 13, by + 8), pt(bx - 7, by - 12), pt(bx + 7, by - 12), pt(bx + 13, by + 8)], outline=INK_DARK, width=int(2.2 * S))
    draw.rectangle([pt(bx - 15, by + 8), pt(bx + 15, by + 13)], outline=INK_DARK, width=int(2 * S))
    draw.ellipse([pt(bx - 3.4, by + 15), pt(bx + 3.4, by + 22)], fill=INK_DARK)
    wave(draw, bx - 30, by - 30, 1.1)
    wave(draw, bx + 22, by - 36, 0.9)

    # --- the Widow's Lantern, on the north-east bay shore ---
    draw_lighthouse(draw, 612, 276)

    # --- the wreck at Wrecker's Cove, in the north-west shallows ---
    draw_wreck(draw, 387, 158)
    depth_dots(draw, 387, 158, 34, n=12, a0=200, a1=520)
    for ang_deg, rr in [(52, 400), (58, 408), (64, 398)]:
        dx, dy = coast_point(ang_deg, rr / radius(ang_deg))
        draw.ellipse([pt(dx - 1.8, dy - 1.8), pt(dx + 1.8, dy + 1.8)], fill=(70, 96, 96))

    # --- the Hungry Maw, in the south sea, with kraken arms nearby ---
    draw_whirlpool(draw, 698, 906, 34)
    draw_tentacles(draw, 772, 892)

    # --- sea life and traffic ---
    draw_serpent(draw, 108, 322)
    draw_ship(draw, 905, 585, 0.95)
    draw_ship(draw, 922, 218, 0.7)
    for wx, wy, ws in [(700, 130, 0.9), (930, 300, 1.0), (150, 700, 1.0),
                       (880, 700, 1.0), (960, 880, 0.9), (420, 120, 0.85),
                       (950, 120, 0.8), (330, 560, 0.8), (120, 480, 0.85)]:
        wave(draw, wx, wy, ws)

    draw_compass(draw, ccx, ccy, 56)

    # --- sea name, lettered down the west edge ---
    sea_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sea_layer)
    sd.text(pt(512, 46), "T H E   B O R R O W E D   S E A", font=F(SERIF_I, 25), fill=(46, 66, 66, 150), anchor="mm")
    sea_layer = sea_layer.rotate(90, center=pt(512, 512))
    img.paste(Image.alpha_composite(img.convert("RGBA"), sea_layer).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # --- place labels (legibility is judged second, right after charm) ---
    label(draw, (390, 296), "Mount Cinder", sub="(still smoking)")
    label(draw, (692, 580), "The Whispering Pines")
    label(draw, (272, 762), "Lagoon of Mists", sub="(mind the mist)")
    label(draw, (466, 872), "Port Meridian")
    label(draw, (716, 866), "Cape of Gulls")
    label(draw, (818, 336), "The Sunken Bell")
    label(draw, (600, 166), "Widow's Lantern")
    label(draw, (390, 194), "Wrecker's Cove")
    label(draw, (328, 542), "The Ruined Abbey")
    label(draw, (372, 490), "Cinderfall")
    label(draw, (665, 784), "Bramblewick", sub="(the market town)")
    label(draw, (700, 966), "The Hungry Maw")

    # --- title cartouche ---
    draw.rounded_rectangle([pt(218, 32), pt(806, 122)], radius=int(10 * S), fill=(240, 224, 178), outline=INK, width=int(2.6 * S))
    draw.rounded_rectangle([pt(226, 40), pt(798, 114)], radius=int(8 * S), outline=(150, 116, 64), width=int(1.2 * S))
    draw.text(pt(512, 70), "The Isle of Borrowed Winds", font=F(DISPLAY_B, 38), fill=INK_DARK, anchor="mm")
    draw.text(pt(512, 102), "— charted in the Year of the Low Tide —", font=F(SERIF_I, 17), fill=(96, 70, 40), anchor="mm")
    for fx in (244, 780):
        draw.line([pt(fx - 8, 70), pt(fx + 8, 70)], fill=(150, 116, 64), width=int(2 * S))
        draw.line([pt(fx, 62), pt(fx, 78)], fill=(150, 116, 64), width=int(2 * S))

    # --- legend cartouche ---
    draw.rounded_rectangle([pt(42, 820), pt(342, 982)], radius=int(8 * S), fill=(240, 224, 178, 238), outline=INK, width=int(2.2 * S))
    draw.text(pt(60, 845), "A Mariner's Key", font=F(SERIF_B, 20), fill=INK_DARK, anchor="lm")
    rows = [
        (871, "the Smuggler's Path"),
        (894, "Treasure, buried deep"),
        (917, "Safe anchorage"),
        (940, "the Sailing Roads"),
        (963, "The Hungry Maw"),
    ]
    for ry, txt in rows:
        draw.text(pt(86, ry), txt, font=F(SERIF, 17), fill=INK_DARK, anchor="lm")
    for dx in (0, 11, 22):  # path dots
        draw.ellipse([pt(56 + dx - 2.8, 871 - 2.8), pt(56 + dx + 2.8, 871 + 2.8)], fill=PATH_INK)
    draw.line([pt(52, 889), pt(62, 899)], fill=RED, width=int(3.4 * S))  # treasure X
    draw.line([pt(52, 899), pt(62, 889)], fill=RED, width=int(3.4 * S))
    draw_anchor(draw, 58, 906, 13)  # anchorage
    draw.line([pt(50, 940), pt(60, 940)], fill=ROUTE_INK, width=int(2.2 * S))  # route dashes
    draw.line([pt(64, 940), pt(74, 940)], fill=ROUTE_INK, width=int(2.2 * S))
    # mini whirlpool spiral
    spiral = []
    for i in range(60):
        th = 4.2 * math.pi * i / 59
        rr = 1.5 + 7.5 * th / (4.2 * math.pi)
        spiral.append((62 + rr * math.cos(th), 963 + 0.8 * rr * math.sin(th)))
    draw.line([pt(x, y) for x, y in spiral], fill=(44, 72, 82), width=int(1.8 * S))

    # --- border frame ---
    draw.rectangle([pt(15, 15), pt(1009, 1009)], outline=INK_DARK, width=int(3 * S))
    draw.rectangle([pt(24, 24), pt(1000, 1000)], outline=(120, 92, 52), width=int(1.2 * S))

    # --- grain and vignette ---
    noise = Image.effect_noise((W, W), 11).convert("L")
    noise = noise.point(lambda v: 236 + int((v - 128) * 0.10))
    img = ImageChops.multiply(img, noise.convert("RGB"))
    vig = Image.new("L", (256, 256), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-70, -70, 326, 326], fill=255)
    vig = vig.resize((W, W)).filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (W, W), (96, 74, 44))
    img = Image.composite(img, ImageChops.multiply(img, dark), vig)

    img = img.resize((1024, 1024), Image.LANCZOS)
    out = os.path.join(HERE, "entry.png")
    img.save(out, optimize=True, compress_level=9)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    render()
