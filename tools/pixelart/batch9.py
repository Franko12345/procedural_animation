import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp


def boss_terror_alado():  # wasp: black-yellow body + 2 translucent wings + venom stinger
    g = Grid(32, 32)
    # wings behind (pale, translucent-ish)
    wr, wo = ramp(52, 0.25, 1.0)
    for s in (-1, 1):
        wing = P.union(P.tri((16, 14), (16 + s * 12, 6), (16 + s * 11, 15)),
                       P.disc(16 + s * 10, 10, 3.2))
        g.paint(wing, [hx(52, 0.15, 1.0)] * 4, hx(52, 0.3, 0.6), light=(-s, -1))
    # body: striped abdomen (yellow with black bands)
    r, o = ramp(48, 0.95, 1.0)
    g.paint(P.union(P.disc(16, 18, 5.5), P.disc(16, 12, 3.6)), r, o, light=(-1, -1))
    for yy in (15, 19, 22):                 # black stripes
        g.line(11, yy, 21, yy, "#221a08")
    # stinger down
    st = P.tri((16, 30), (13.5, 22), (18.5, 22))
    g.paint(st, [hx(48, 0.8, 0.9)] * 4, o)
    g.px(16, 29, "#7cff8c")                 # venom drip
    # 2 tiny black eyes
    g.px(14, 11, "#1a1a20"); g.px(18, 11, "#1a1a20")
    return g


ASSETS = [("boss_terror_alado", boss_terror_alado())]
paths = [(n, g.render(n, 12), 32) for n, g in ASSETS]

TILE = 200
sheet = Image.new("RGBA", (TILE + 24, TILE + 24), (28, 30, 38, 255))
d = ImageDraw.Draw(sheet)
for i, (name, pp, w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE - 40, TILE - 40), Image.NEAREST)
    tile = Image.new("RGBA", (TILE, TILE), (44, 48, 40, 255)); tile.alpha_composite(img, (20, 26))
    sheet.alpha_composite(tile, (12, 12)); d.text((16, 16), name, fill=(235, 235, 245))
sheet.save(os.path.join(P.OUT, "batch9_sheet.png"))
print("rendered:", [p[0] for p in paths])
