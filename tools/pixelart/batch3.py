import os, colorsys, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw

def hx(h, s, v):
    h = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(h, max(0, min(1, s)), max(0, min(1, v)))
    return "#%02x%02x%02x" % (int(r*255), int(g*255), int(b*255))

def ramp(h, s=0.85, v=0.92):
    hi   = hx(h - 10, s*0.65, min(1, v*1.16))
    base = hx(h, s, v)
    sh   = hx(h + 12, min(1, s*1.05), v*0.68)
    ed   = hx(h + 18, s, v*0.44)
    out  = hx(h + 22, s*0.8, v*0.26)
    return [hi, base, sh, ed], out

def ferrao():  # homing sting: a curved barbed fang
    g = Grid(32, 32); r, o = ramp(38, 0.9, 0.98)
    shape = P.union(P.tri((7,24),(14,27),(27,6)), P.disc(9.5,24,3.4),
                    P.tri((20,12),(27,8),(22,17)))   # barb near tip
    g.paint(shape, r, o, light=(-1,-1.1))
    return g

def teia():  # sticky web: radial spokes + two rings
    g = Grid(32, 32); c = "#bfe9f2"; ink = "#2a4a55"
    cx, cy = 16, 16
    for a in range(0, 360, 60):
        g.line(cx, cy, cx + 14*math.cos(math.radians(a)), cy + 14*math.sin(math.radians(a)), c)
    for rr in (6, 11):
        for a in range(0, 360, 60):
            a2 = a + 60
            x0 = cx + rr*math.cos(math.radians(a)); y0 = cy + rr*math.sin(math.radians(a))
            x1 = cx + rr*math.cos(math.radians(a2)); y1 = cy + rr*math.sin(math.radians(a2))
            g.line(x0, y0, x1, y1, c)
    g.px(cx, cy, "#eaffff")
    g.outline_all(ink)
    return g

def esporos():  # spore cloud: merged blobs + lighter spore dots
    g = Grid(32, 32); r, o = ramp(140, 0.7, 0.9)
    cloud = P.union(P.disc(12,18,6.5), P.disc(20,17,7), P.disc(16,12,6), P.disc(22,21,5))
    g.paint(cloud, r, o, light=(-1,-1))
    for x, y in ((11,15),(18,13),(22,18),(15,20)):
        g.paint(P.disc(x, y, 1.6), [r[0], r[0], r[1], r[1]], o)
    return g

def feromonio():  # pheromone: purple droplet + scent waves
    g = Grid(32, 32); r, o = ramp(288, 0.75, 0.92)
    drop = P.union(P.disc(14, 19, 6.5), P.tri((7.5,19),(20.5,19),(14,6)))
    g.paint(drop, r, o, light=(-1,-1))
    wv = hx(288, 0.5, 1.0)
    for rr in (9, 12):
        g.arc(14, 19, rr, -70, 40, wv, step=8)
    g.outline_all(o)
    return g

def sopro():  # repel breath: concentric wind arcs + puff
    g = Grid(32, 32); c = hx(202, 0.55, 0.98); ink = "#1d3550"
    for rr in (8, 13, 18):
        g.arc(6, 16, rr, -58, 58, c, step=5)
    g.paint(P.disc(6, 16, 3.4),
            [hx(202,0.35,1.0), hx(202,0.5,0.95), hx(202,0.62,0.72), hx(202,0.66,0.5)], ink)
    g.outline_all(ink)
    return g

def enxame():  # swarm: cluster + orbiting bugs
    g = Grid(32, 32); r, o = ramp(52, 0.95, 1.0)
    g.paint(P.disc(16, 16, 6), r, o)
    for x, y in ((7,9),(25,12),(23,24),(9,23)):
        g.paint(P.disc(x, y, 2.6), r, o)
        g.line(x-3, y, x+3, y, "#2a2410")   # wing hint
    return g

def acido():  # acid puddle: wide pool + bubbles
    g = Grid(32, 32); r, o = ramp(98, 0.85, 0.9)
    g.paint(lambda x, y: ((x-16)/13)**2 + ((y-20)/7)**2 <= 1, r, o, light=(-1,-1.4))
    for x, y, rr in ((11,17,1.8),(19,16,2.4),(23,20,1.5)):
        g.paint(P.disc(x, y, rr), [r[0], r[0], r[1], r[2]], o)
    return g

ASSETS = [("ferrao", ferrao()), ("teia", teia()), ("esporos", esporos()),
          ("feromonio", feromonio()), ("sopro", sopro()), ("enxame", enxame()),
          ("acido", acido())]
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
sheet.save(os.path.join(P.OUT,"batch3_sheet.png"))
print("rendered:", [p[0] for p in paths])
