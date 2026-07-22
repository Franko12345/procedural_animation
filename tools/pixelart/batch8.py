import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp


def boss_aranha_rei():  # pale albino spider over a web -- long thin legs
    g = Grid(32, 32)
    # web strands behind (faint)
    web = hx(220, 0.1, 0.55)
    for a in range(0, 360, 45):
        g.line(16, 16, 16 + 15 * math.cos(math.radians(a)), 16 + 15 * math.sin(math.radians(a)), web)
    for rr in (6, 11, 15):
        g.arc(16, 16, rr, 0, 360, web, step=10)
    # long spindly legs (pale)
    leg = hx(255, 0.05, 0.85)
    for s in (-1, 1):
        for k, (a, b) in enumerate(((0.8, 0.2), (0.4, 0.6), (-0.2, 0.9), (-0.7, 0.7))):
            kx = 16 + s * 4
            g.line(kx, 16, kx + s * 9 * a, 16 - 9 * b + 4, leg)
            g.line(kx + s * 9 * a, 16 - 9 * b + 4, kx + s * 14 * a, 16 - 14 * b + 8, leg)
    # body: cephalothorax + abdomen
    r, o = ramp(255, 0.06, 0.9)
    g.paint(P.disc(16, 20, 6), r, o, light=(-1, -1))     # abdomen
    g.paint(P.disc(16, 13, 4.2), r, o, light=(-1, -1))   # head
    for ex in (-1.5, 1.5):                               # a few tiny black eyes
        g.px(int(16 + ex), 12, "#1a1a20")
        g.px(int(16 + ex), 14, "#1a1a20")
    return g


def boss_serpente_cristal():  # faceted rainbow crystal prism
    g = Grid(32, 32)
    # a diamond built from 4 triangular facets, each a different prism hue
    facets = [
        (P.tri((16, 3), (16, 16), (8, 12)), 300),   # left-upper (magenta)
        (P.tri((16, 3), (24, 12), (16, 16)), 55),    # right-upper (yellow)
        (P.tri((8, 12), (16, 16), (16, 29)), 190),   # left-lower (cyan)
        (P.tri((24, 12), (16, 29), (16, 16)), 130),  # right-lower (green)
    ]
    for shape, hue in facets:
        r, o = ramp(hue, 0.5, 1.0)
        g.paint(shape, r, "#20304a", light=(-1, -1))
    # bright central seam + top glint
    g.line(16, 3, 16, 29, "#eef6ff")
    g.paint(P.disc(14, 8, 1.4), ["#ffffff"] * 4, "#20304a")
    g.outline_all("#182238")
    return g


ASSETS = [("boss_aranha_rei", boss_aranha_rei()),
          ("boss_serpente_cristal", boss_serpente_cristal())]
paths = [(n, g.render(n, 12), 32) for n, g in ASSETS]

TILE, PAD, COLS = 150, 12, 2
rows = (len(paths) + COLS - 1) // COLS
sheet = Image.new("RGBA", (TILE * COLS + PAD * (COLS + 1), (TILE + PAD) * rows + PAD), (28, 30, 38, 255))
d = ImageDraw.Draw(sheet)
for i, (name, pp, w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE - 40, TILE - 40), Image.NEAREST)
    cx = PAD + (i % COLS) * (TILE + PAD); cy = PAD + (i // COLS) * (TILE + PAD)
    tile = Image.new("RGBA", (TILE, TILE), (44, 40, 56, 255)); tile.alpha_composite(img, (20, 26))
    sheet.alpha_composite(tile, (cx, cy)); d.text((cx + 4, cy + 4), name, fill=(235, 235, 245))
sheet.save(os.path.join(P.OUT, "batch8_sheet.png"))
print("rendered:", [p[0] for p in paths])
