import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp

def speed():  # motion streak: three chevrons trailing off, not a bolt
    g = Grid(32, 32)
    body = P.union(P.tri((6,16),(18,9),(14,16)), P.tri((6,16),(18,23),(14,16)))
    r, o = ramp(198, 0.75, 0.95)
    g.paint(body, r, o, light=(-1,-1))
    for i, dx in enumerate((0, 8, 15)):
        a = 0.85 - i*0.24
        c = hx(198, 0.4, min(1, 0.95+a*0.1))
        g.line(20+dx, 12+i*0, 27+dx*0.4, 16, c, wide=0)
    # simpler: three parallel speed-lines behind the chevron
    for i, yy in enumerate((10, 16, 22)):
        length = 9 - abs(yy-16)//2
        c = hx(198, 0.5, 0.95)
        g.line(19, yy, 19+length, yy, c)
    return g

def energia():  # a spark/battery cell: rounded cell with a bolt inside
    g = Grid(32, 32)
    cell = P.rect(9, 6, 23, 25)
    r, o = ramp(48, 0.85, 1.0)
    g.paint(cell, r, o, light=(-1,-1))
    g.flat(P.rect(13, 3, 19, 6), o)          # battery nub
    bolt = P.union(P.tri((18,9),(13,17),(17,17)), P.tri((14,16),(19,16),(15,24)))
    g.flat(bolt, "#fff6d0")
    g.outline_all("#3a2408")
    return g

def vigor():  # might: a clenched claw/fist knuckle print
    g = Grid(32, 32)
    r, o = ramp(0, 0.75, 0.85)
    palm = P.disc(16, 19, 8)
    knuckles = P.union(*[P.disc(9+i*4.6, 9, 3.2) for i in range(4)])
    g.paint(P.union(palm, knuckles), r, o, light=(-1,-1))
    return g

def metabolismo():  # xp: a bright multi-point star with a shine streak
    g = Grid(32, 32)
    pts = []
    cx, cy, R, r = 16, 16, 13, 5.2
    for i in range(10):
        ang = -90 + i*36
        rr = R if i % 2 == 0 else r
        pts.append((cx + rr*math.cos(math.radians(ang)), cy + rr*math.sin(math.radians(ang))))
    shape = lambda x, y: _pt_in_poly(x, y, pts)
    r_, o = ramp(50, 0.9, 1.0)
    g.paint(shape, r_, o, light=(-1,-1))
    g.line(11, 11, 14, 14, "#fff8d8")
    return g

def _pt_in_poly(x, y, poly):
    n = len(poly); inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-9) + xi):
            inside = not inside
        j = i
    return inside

def amplitude():  # area: expanding concentric rings from a center dot
    g = Grid(32, 32)
    c = hx(150, 0.6, 0.95); ink = "#123a0c"
    g.paint(P.disc(16, 16, 2.6), ramp(150,0.9,0.95)[0], ink)
    for rr in (7, 11, 15):
        g.arc(16, 16, rr, 0, 359, c, step=7)
    g.outline_all(ink)
    return g

def frenesi():  # haste: hourglass with sand mid-fall (motion, not a static clock)
    g = Grid(32, 32)
    top = P.tri((8,6),(24,6),(16,15))
    bot = P.tri((8,26),(24,26),(16,17))
    r, o = ramp(15, 0.75, 0.95)
    g.paint(P.union(top, bot), r, o, light=(-1,-1))
    g.flat(P.rect(7,5,25,7), o); g.flat(P.rect(7,25,25,27), o)
    g.line(16, 15, 16, 18, "#fff3d0")
    g.outline_all("#3a1c08")
    return g

def fecundidade():  # amount: three dots in a growing triangle (+1 stacking)
    g = Grid(32, 32)
    r, o = ramp(320, 0.7, 0.95)
    g.paint(P.disc(16, 8, 3.6), r, o, light=(-1,-1))
    g.paint(P.disc(9, 22, 4.6), r, o, light=(-1,-1))
    g.paint(P.disc(23, 22, 4.6), r, o, light=(-1,-1))
    return g

def arranco():  # dash: a footprint + burst step, distinct from ferrao's arrow
    g = Grid(32, 32)
    r, o = ramp(178, 0.7, 0.9)
    foot = P.union(P.disc(13,20,4.4), P.tri((9,15),(17,15),(13,9)))
    g.paint(foot, r, o, light=(-1,-1))
    for i, yy in enumerate((14, 20, 26)):
        length = 8 - abs(yy-20)
        g.line(19, yy, 19+length, yy, hx(178,0.4,0.95))
    return g

ASSETS = [("speed", speed()), ("energy", energia()), ("might", vigor()),
          ("xp", metabolismo()), ("area", amplitude()), ("haste", frenesi()),
          ("amount", fecundidade()), ("dash", arranco())]
paths = [(n, g.render(n, 12), 32) for n, g in ASSETS]

TILE, PAD, COLS = 150, 12, 4
rows = (len(paths)+COLS-1)//COLS
sheet = Image.new("RGBA", (TILE*COLS+PAD*(COLS+1), (TILE+PAD)*rows+PAD), (28,30,38,255))
d = ImageDraw.Draw(sheet)
for i,(name,pp,w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE-40,TILE-40), Image.NEAREST)
    cx = PAD + (i%COLS)*(TILE+PAD); cy = PAD + (i//COLS)*(TILE+PAD)
    tile = Image.new("RGBA",(TILE,TILE),(44,88,64,255)); tile.alpha_composite(img,(20,26))
    sheet.alpha_composite(tile,(cx,cy)); d.text((cx+4,cy+4), name, fill=(235,235,245))
sheet.save(os.path.join(P.OUT,"batch4_sheet.png"))
print("rendered:", [p[0] for p in paths])
