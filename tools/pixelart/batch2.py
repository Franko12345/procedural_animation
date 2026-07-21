import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw

INK = "#241a30"

def coin():
    g = Grid(32, 32)
    g.paint(P.disc(16, 16, 13),
            ["#ffe27a", "#f2b81f", "#c07f12", "#8a5410"], "#3a2408", light=(-1, -1.1))
    g.paint(P.disc(11.5, 10.5, 2.4),                       # bright spec
            ["#fffbe0", "#fff0b0", "#ffe27a", "#ffe27a"], "#c07f12")
    # embossed pollen mote
    for x, y in ((16,16),(15,16),(17,16),(16,15),(16,17)):
        g.px(x, y, "#a86e10")
    return g

def heart():
    g = Grid(32, 32)
    shape = P.union(P.disc(10.5, 11, 6.8), P.disc(21.5, 11, 6.8),
                    P.tri((3.6,13),(28.4,13),(16,28.4)))
    g.paint(shape, ["#ff8f9c", "#e23b4e", "#b31f31", "#7a1220"], "#360810", light=(-1,-1.2))
    return g

def venom():
    g = Grid(32, 32)
    shape = P.union(P.disc(16, 20, 8), P.tri((8.2,20),(23.8,20),(16,4.5)))
    g.paint(shape, ["#c2ff8f", "#6fd94a", "#3f9c2e", "#226016"], "#0f3208", light=(-1,-1))
    g.paint(P.disc(9, 27.5, 2.1),
            ["#c2ff8f", "#6fd94a", "#3f9c2e", "#3f9c2e"], "#0f3208")
    return g

def tent():
    g = Grid(80, 80)
    RED, CREAM = "#d6484e", "#f3e6cf"
    WOOD, WOOD_D, WOOD_H = "#7a4f2e", "#4d2f18", "#a06a3a"
    # posts
    g.flat(P.rect(11,32,15,64), WOOD); g.flat(P.rect(65,32,69,64), WOOD)
    g.flat(P.rect(11,32,11,64), WOOD_D); g.flat(P.rect(69,32,69,64), WOOD_D)
    # rounded striped awning (triangle with a domed peak), vertical stripes
    peak_y, base_y = 10, 32
    roof = P.union(P.tri((40,peak_y),(6,base_y),(74,base_y)), P.disc(40, peak_y+4, 5))
    for (x,y),v in g.coverage(roof).items():
        if v >= 0.5:
            g.px(x, y, CREAM if (x//7) % 2 else RED)
    g._outline_from(g.coverage(roof), INK)
    # scalloped valance
    for k, xc in enumerate(range(8, 73, 9)):
        g.flat(P.tri((xc-5,base_y),(xc+5,base_y),(xc,base_y+7)), CREAM if k%2 else RED)
    # counter with volume
    g.flat(P.rect(7,50,73,63), WOOD)
    g.flat(P.rect(7,50,73,51), WOOD_H)
    g.flat(P.rect(7,62,73,63), WOOD_D)
    for x in range(7,74,6):
        g.flat(P.rect(x,52,x,61), WOOD_D)
    g._outline_from(g.coverage(P.rect(7,50,73,63)), INK)
    # pollen sign on the peak
    g.paint(P.disc(40, 6, 3.4), ["#fffbe0","#ffd94a","#f2b81f","#c07f12"], INK)
    # lantern
    g.paint(P.disc(62, 42, 3), ["#fff3b0","#ffd45a","#e0a020","#a06a10"], INK)
    # beetle merchant (volume sphere body + head)
    BUG = ["#b0a0d0","#7a68a0","#584878","#38284f"]
    g.paint(P.disc(25, 47, 6.5), BUG, INK, light=(-1,-1))
    g.paint(P.disc(25, 41, 3.6), BUG, INK, light=(-1,-1))
    g.px(27,40,"#fff"); g.px(26,40,INK)          # eye
    for dx in (-4,4):                            # antennae
        g.px(25+dx//2,37,INK); g.px(25+dx,34,"#ffe79a")
        g.px(25+dx//2,36,INK); g.px(25+dx-(1 if dx<0 else -1),35,INK)
    return g

ASSETS = [("coin_pollen", coin(), 12), ("health", heart(), 12),
          ("cuspe", venom(), 12), ("tent_beetle", tent(), 8)]
paths = [(n, g.render(n, ps), g.w) for n, g, ps in ASSETS]

TILE, PAD = 200, 16
sheet = Image.new("RGBA", (TILE*2+PAD*3, (TILE+PAD)*len(paths)+PAD), (28,30,38,255))
d = ImageDraw.Draw(sheet)
for i,(name,pp,w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE-48,TILE-48), Image.NEAREST)
    y = PAD + i*(TILE+PAD)
    for j,bg in enumerate([(24,26,34,255),(46,92,66,255)]):
        x = PAD + j*(TILE+PAD)
        tile = Image.new("RGBA",(TILE,TILE),bg); tile.alpha_composite(img,(24,24))
        sheet.alpha_composite(tile,(x,y))
    d.text((PAD,y+2), f"{name} {w}x{w}", fill=(230,230,240))
sheet.save(os.path.join(P.OUT,"batch2_sheet.png"))
print("rendered:", [p[0] for p in paths], "sheet 800x")
