import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp


def boss_rei_lagarto():  # crown: jagged 5-point band, golden, a few gem studs
    g = Grid(32, 32)
    r, o = ramp(42, 0.82, 0.9)
    band = P.rect(6, 20, 26, 25)
    pts = []
    xs = [6, 10, 14, 18, 22, 26]
    for i in range(5):
        x0, x1 = xs[i], xs[i + 1]
        mx = (x0 + x1) / 2
        top = 4 if i % 2 == 0 else 11
        pts.append(P.tri((x0, 20), (x1, 20), (mx, top)))
    crown = P.union(band, *pts)
    g.paint(crown, r, o, light=(-1, -1))
    for cx, hcol in ((10, 350), (16, 205), (22, 350)):
        g.paint(P.disc(cx, 22.5, 1.6), [hx(hcol, 0.75, 0.95)] * 4, o)
    return g


def boss_centopeiadeira():  # rusted gear: dark orange-brown, pitted teeth
    g = Grid(32, 32)
    r, o = ramp(22, 0.55, 0.55)
    body = P.disc(16, 16, 10)
    teeth = [P.tri((16 + 9 * math.cos(math.radians(a - 12)), 16 + 9 * math.sin(math.radians(a - 12))),
                   (16 + 9 * math.cos(math.radians(a + 12)), 16 + 9 * math.sin(math.radians(a + 12))),
                   (16 + 13 * math.cos(math.radians(a)), 16 + 13 * math.sin(math.radians(a))))
             for a in range(0, 360, 45)]
    g.paint(P.union(body, *teeth), r, o, light=(-1, -1))
    g.paint(P.disc(16, 16, 4.2), [hx(24, 0.4, 0.32)] * 4, o)
    # rust pitting -- a few dark speckles scattered on the body
    for px, py in ((12, 12), (20, 13), (13, 20), (21, 20), (16, 9)):
        g.px(px, py, hx(18, 0.6, 0.28))
    return g


def boss_kraken_mor():  # wide violet eye + 2 curling tentacles beneath
    g = Grid(32, 32)
    g.paint(P.disc(16, 14, 9.5), ["#efe6ff", "#d8c8f2", "#a98adf", "#5a3f7a"], "#241633",
           light=(-1, -1))
    g.paint(lambda x, y: abs(x - 16) <= 2.2 and 7 <= y <= 21, [hx(280, 0.7, 0.25)] * 4, "#241633")
    g.paint(P.disc(19, 11, 1.6), ["#bfe8ea"] * 4, "#241633")  # bioluminescent glint
    for s in (-1, 1):
        x, y = 16 + s * 6, 22
        for i in range(5):
            nx = x + s * (2.5 + i * 0.4) * math.sin(i * 0.9)
            ny = y + i * 1.8
            g.paint(P.disc(nx, ny, 2.0 - i * 0.28), [hx(275, 0.65, 0.55)] * 4, "#241633")
    return g


def boss_mae_escaravelho():  # cluster of overlapping eggs, one glowing
    g = Grid(32, 32)
    r, o = ramp(32, 0.55, 0.6)
    eggs = [(11, 15, 5.6), (21, 15, 5.6), (16, 10, 4.8), (10, 23, 4.6), (22, 23, 4.6)]
    for i, (cx, cy, rr) in enumerate(eggs):
        shape = lambda x, y, cx=cx, cy=cy, rr=rr: ((x - cx) / rr) ** 2 + ((y - cy) / (rr * 1.2)) ** 2 <= 1
        if i == 2:                      # the middle egg glows -- something's alive in there
            g.paint(shape, [hx(48, 0.7, 1.0), hx(45, 0.6, 0.92), hx(35, 0.55, 0.65), o],
                   o, light=(-1, -1))
        else:
            g.paint(shape, r, o, light=(-1, -1))
    return g


def boss_primordial():  # ancient flame/rune, magma red-orange with white-hot core
    g = Grid(32, 32)
    r, o = ramp(14, 0.85, 0.85)
    flame = P.union(
        P.tri((16, 3), (23, 15), (16, 12)), P.tri((16, 3), (9, 15), (16, 12)),
        P.tri((9, 15), (23, 15), (16, 27)),
        P.tri((16, 12), (21, 20), (16, 24)), P.tri((16, 12), (11, 20), (16, 24)),
    )
    g.paint(flame, r, o, light=(-1, -1))
    g.paint(P.disc(16, 19, 3.2), [hx(48, 0.55, 1.0)] * 4, o)
    for px, py in ((13, 9), (20, 11), (16, 17)):
        g.px(px, py, hx(20, 0.7, 0.35))       # cracks/embers
    return g


ASSETS = [("boss_rei_lagarto", boss_rei_lagarto()), ("boss_centopeiadeira", boss_centopeiadeira()),
          ("boss_kraken_mor", boss_kraken_mor()), ("boss_mae_escaravelho", boss_mae_escaravelho()),
          ("boss_primordial", boss_primordial())]
paths = [(n, g.render(n, 12), 32) for n, g in ASSETS]

TILE, PAD, COLS = 150, 12, 3
rows = (len(paths) + COLS - 1) // COLS
sheet = Image.new("RGBA", (TILE * COLS + PAD * (COLS + 1), (TILE + PAD) * rows + PAD), (28, 30, 38, 255))
d = ImageDraw.Draw(sheet)
for i, (name, pp, w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE - 40, TILE - 40), Image.NEAREST)
    cx = PAD + (i % COLS) * (TILE + PAD); cy = PAD + (i // COLS) * (TILE + PAD)
    tile = Image.new("RGBA", (TILE, TILE), (44, 40, 56, 255)); tile.alpha_composite(img, (20, 26))
    sheet.alpha_composite(tile, (cx, cy)); d.text((cx + 4, cy + 4), name, fill=(235, 235, 245))
sheet.save(os.path.join(P.OUT, "batch7_sheet.png"))
print("rendered:", [p[0] for p in paths])
