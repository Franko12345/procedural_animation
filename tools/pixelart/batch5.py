import os
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp

def fruta():  # round orange fruit + a green stem/leaf
    g = Grid(24, 24)
    r, o = ramp(18, 0.88, 1.0)
    g.paint(P.disc(12, 14, 8), r, o, light=(-1,-1))
    leaf_r, leaf_o = ramp(120, 0.7, 0.85)
    g.paint(P.tri((12,6),(17,7),(12,11)), leaf_r, leaf_o, light=(-1,-1))
    g.line(12, 3, 12, 7, "#5a3a1c")             # stem
    return g

def ovo():  # cream egg with a small friend-purple rune mark
    g = Grid(24, 24)
    shape = lambda x, y: ((x-12)/6.2)**2 + ((y-13)/8.6)**2 <= 1
    r = ["#fffef2", "#f5f2dc", "#c9c0a0", "#8f866c"]
    o = "#4a4636"
    g.paint(shape, r, o, light=(-1,-1.3))
    g.paint(P.disc(12, 13, 2.0), ["#c9a8ff","#a878ff","#7048c8","#4a2c90"], "#2c1a5c")
    return g

def inseto():  # a small scarab: rounded body + 6 tiny legs + head
    g = Grid(24, 24)
    r, o = ramp(315, 0.85, 1.0)
    g.paint(P.disc(12, 13, 6.4), r, o, light=(-1,-1))
    g.paint(P.disc(12, 7, 2.6), r, o, light=(-1,-1))
    for s in (-1, 1):
        for ly in (10, 13, 16):
            g.line(12+s*6, ly, 12+s*9, ly+ (2 if s>0 else -2), o)
    g.line(12, 8, 12, 15, hx(315,0.9,0.6))       # wing seam
    return g

ASSETS = [("pickup_fruit", fruta()), ("pickup_egg", ovo()), ("pickup_bug", inseto())]
paths = [(n, g.render(n, 14), 24) for n, g in ASSETS]

TILE, PAD = 170, 14
sheet = Image.new("RGBA", (TILE*3+PAD*4, TILE+PAD*2), (44,88,64,255))
d = ImageDraw.Draw(sheet)
for i,(name,pp,w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE-40,TILE-40), Image.NEAREST)
    x = PAD + i*(TILE+PAD)
    sheet.alpha_composite(img,(x+20,PAD+20)); d.text((x+4,PAD+2), name, fill=(235,235,245))
sheet.save(os.path.join(P.OUT,"batch5_sheet.png"))
print("rendered:", [p[0] for p in paths])
