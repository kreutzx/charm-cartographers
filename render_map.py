"""Render the treasure map for the Charm the Cartographers entry.

Draws "The Isle of Borrowed Winds" with PIL at 2x supersample and saves the
downscaled result as ``entry.png`` next to this file. The shipped entrypoint
(``main.py``) never runs this: it only copies the committed ``entry.png``.
Fonts are vendored under ``fonts/`` so the render is reproducible.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
S = 2  # supersample factor; final image is 1024x1024
W = 1024 * S

INK = (64, 46, 26)
INK_DARK = (48, 34, 18)
SEA = (156, 180, 158)
SEA_DEEP = (138, 166, 148)
SEA_PALE = (176, 198, 172)
LAND = (236, 216, 166)
LAND_LIGHT = (245, 231, 188)
SHOAL = (208, 224, 194)
PARCH = (233, 216, 170)
MOUNTAIN = (110, 78, 48)
PINE = (56, 82, 48)
PINE_DARK = (44, 68, 38)
RIVER = (104, 148, 166)
LAGOON = (143, 188, 188)
ROOF = (148, 82, 50)
RED = (172, 48, 36)
PATH_INK = (120, 72, 32)


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
    draw.polygon([pt(*apex), pt(*left), pt(*right)], fill=(226, 200, 148))
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
        tone = random.choice([SEA_PALE, SEA_DEEP, (168, 190, 164)])
        draw.ellipse([pt(bx - br, by - br * 0.6), pt(bx + br, by + br * 0.6)], fill=tone + (36,))

    # rhumb lines from the compass point, under everything else
    ccx, ccy = 150, 150
    for k in range(16):
        ang = math.radians(k * 22.5)
        ex, ey = ccx + 1200 * math.cos(ang), ccy + 1200 * math.sin(ang)
        draw.line([pt(ccx, ccy), pt(ex, ey)], fill=(64, 46, 26, 30), width=int(1.1 * S))

    # island: shoal ring, land, double-line coast
    draw.polygon(island_polygon(1.055), fill=SHOAL)
    draw.polygon(island_polygon(1.028), outline=(120, 140, 110), width=int(2 * S))
    draw.polygon(island_polygon(1.0), fill=LAND)
    inner = island_polygon(0.965)
    draw.polygon(inner, fill=None)
    draw.line(inner + [inner[0]], fill=(196, 164, 104), width=int(1.6 * S))
    coast = island_polygon(1.0)
    draw.line(coast + [coast[0]], fill=INK, width=int(2.6 * S))
    # interior lift: a soft lighter wash in the middle of the island
    draw.ellipse([pt(300, 290), pt(720, 730)], fill=LAND_LIGHT + (52,))

    # --- the river, from the volcano's shoulder down to the lagoon ---
    river_pts = catmull_rom([(498, 408), (466, 466), (478, 524), (428, 574), (386, 622), (362, 668)])
    draw.line([pt(x, y) for x, y in river_pts], fill=RIVER, width=int(8 * S), joint="curve")
    draw.line([pt(x, y) for x, y in river_pts], fill=(172, 204, 208), width=int(3 * S), joint="curve")

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

    # --- Cape of Gulls: a small flock over the water east of the cape ---
    for gx, gy in [(820, 700), (858, 678), (792, 724), (884, 716)]:
        draw.arc([pt(gx - 14, gy - 8), pt(gx, gy + 8)], 200, 340, fill=INK_DARK, width=int(2.6 * S))
        draw.arc([pt(gx, gy - 8), pt(gx + 14, gy + 8)], 200, 340, fill=INK_DARK, width=int(2.6 * S))

    # --- the Sunken Bell, in the north-east shallows ---
    bx, by = 818, 262
    for rr in (30, 40):
        for a0 in range(0, 360, 26):
            a = math.radians(a0)
            x0, y0 = bx + rr * math.cos(a), by + rr * math.sin(a)
            draw.ellipse([pt(x0 - 1.8, y0 - 1.8), pt(x0 + 1.8, y0 + 1.8)], fill=(70, 96, 96))
    draw.polygon([pt(bx - 13, by + 8), pt(bx - 7, by - 12), pt(bx + 7, by - 12), pt(bx + 13, by + 8)], outline=INK_DARK, width=int(2.2 * S))
    draw.rectangle([pt(bx - 15, by + 8), pt(bx + 15, by + 13)], outline=INK_DARK, width=int(2 * S))
    draw.ellipse([pt(bx - 3.4, by + 15), pt(bx + 3.4, by + 22)], fill=INK_DARK)
    wave(draw, bx - 30, by - 30, 1.1)
    wave(draw, bx + 22, by - 36, 0.9)

    # --- sea life and traffic ---
    draw_serpent(draw, 108, 322)
    draw_ship(draw, 905, 585, 0.95)
    for wx, wy, ws in [(300, 180, 1.0), (700, 130, 0.9), (930, 300, 1.0), (150, 700, 1.0),
                       (880, 700, 1.0), (960, 880, 0.9), (420, 120, 0.85),
                       (620, 920, 0.95), (950, 120, 0.8), (330, 560, 0.8)]:
        wave(draw, wx, wy, ws)

    draw_compass(draw, ccx, ccy, 56)

    # --- sea name, lettered down the west edge ---
    sea_layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sea_layer)
    sd.text(pt(512, 46), "T H E   B O R R O W E D   S E A", font=F(SERIF_I, 25), fill=(52, 74, 74, 150), anchor="mm")
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

    # --- title cartouche ---
    draw.rounded_rectangle([pt(218, 32), pt(806, 122)], radius=int(10 * S), fill=(240, 224, 178), outline=INK, width=int(2.6 * S))
    draw.rounded_rectangle([pt(226, 40), pt(798, 114)], radius=int(8 * S), outline=(150, 116, 64), width=int(1.2 * S))
    draw.text(pt(512, 70), "The Isle of Borrowed Winds", font=F(DISPLAY_B, 38), fill=INK_DARK, anchor="mm")
    draw.text(pt(512, 102), "— charted in the Year of the Low Tide —", font=F(SERIF_I, 17), fill=(96, 70, 40), anchor="mm")
    for fx in (244, 780):
        draw.line([pt(fx - 8, 70), pt(fx + 8, 70)], fill=(150, 116, 64), width=int(2 * S))
        draw.line([pt(fx, 62), pt(fx, 78)], fill=(150, 116, 64), width=int(2 * S))

    # --- legend cartouche ---
    draw.rounded_rectangle([pt(46, 836), pt(340, 974)], radius=int(8 * S), fill=(240, 224, 178, 238), outline=INK, width=int(2.2 * S))
    draw.text(pt(64, 862), "A Mariner's Key", font=F(SERIF_B, 21), fill=INK_DARK, anchor="lm")
    for dx in (0, 11, 22):
        draw.ellipse([pt(256 + dx - 2.8, 892 - 2.8), pt(256 + dx + 2.8, 892 + 2.8)], fill=PATH_INK)
    draw.text(pt(64, 892), "the Smuggler's Path", font=F(SERIF, 18), fill=INK_DARK, anchor="lm")
    draw.line([pt(56, 918), pt(66, 928)], fill=RED, width=int(3.4 * S))
    draw.line([pt(56, 928), pt(66, 918)], fill=RED, width=int(3.4 * S))
    draw.text(pt(84, 923), "Treasure, buried deep", font=F(SERIF, 18), fill=INK_DARK, anchor="lm")
    draw_anchor(draw, 62, 936, 15)
    draw.text(pt(84, 950), "Safe anchorage", font=F(SERIF, 18), fill=INK_DARK, anchor="lm")

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
    img.save(out, optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    render()
