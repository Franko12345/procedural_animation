import os, math
import pxgen as P
from pxgen import Grid
from PIL import Image, ImageDraw
from batch3 import hx, ramp

def antenas():  # head charm: a pair of curved antennae over a small skull dot
    g = Grid(32, 32)
    col = hx(190, 0.55, 0.7)
    for s in (-1, 1):
        g.line(16, 18, 16+s*3, 12, col)
        g.line(16+s*3, 12, 16+s*8, 6, col)
        g.paint(P.disc(16+s*8, 5, 1.8), [hx(190,0.5,1.0)]*4, col)
    r, o = ramp(190, 0.5, 0.75)
    g.paint(P.disc(16, 20, 5.4), r, o, light=(-1,-1))
    return g

def presas():  # head charm: two curved venom fangs over a purple drop
    g = Grid(32, 32)
    r, o = ramp(300, 0.7, 0.9)
    g.paint(P.union(P.disc(16,20,6), P.tri((10,20),(22,20),(16,8))), r, o, light=(-1,-1))
    for s in (-1, 1):
        g.flat(P.tri((16+s*1.5,17),(16+s*4.5,17),(16+s*2,24)), "#f5f2f8")
    return g

def olhos():  # head charm: a cluster of three watching eyes
    g = Grid(32, 32)
    for cx, cy, rr in ((10,18,4.6),(22,18,4.6),(16,10,3.8)):
        g.paint(P.disc(cx, cy, rr), ["#fff","#eee","#ccc","#999"], "#1c1c22")
        g.paint(P.disc(cx, cy, rr*0.42), [hx(50,0.9,0.9)]*4, "#1c1c22")
    return g

def carapaca():  # back charm: an armored shell segment, chevron scales
    g = Grid(32, 32)
    r, o = ramp(255, 0.55, 0.7)
    g.paint(lambda x,y: ((x-16)/11)**2 + ((y-18)/8)**2 <= 1, r, o, light=(-1,-1))
    for i, yy in enumerate((13, 17, 21)):
        w = 9 - i
        g.line(16-w, yy, 16, yy-3, hx(255,0.4,0.9))
        g.line(16, yy-3, 16+w, yy, hx(255,0.4,0.9))
    return g

def espinhos():  # back charm: three sharp dorsal spikes fanning up
    g = Grid(32, 32)
    r, o = ramp(330, 0.75, 0.9)
    for i, ang in enumerate((-28, 0, 28)):
        bx = 16 + 7*math.sin(math.radians(ang))
        tx = 16 + 15*math.sin(math.radians(ang))
        ty = 26 - 20*math.cos(math.radians(ang))
        g.paint(P.tri((bx-2.6,26),(bx+2.6,26),(tx,ty)), r, o, light=(-1,-1))
    return g

def asas():  # back charm: a pair of beetle wings, glossy
    g = Grid(32, 32)
    r, o = ramp(175, 0.55, 0.8)
    for s in (-1, 1):
        wing = P.union(P.tri((16,18),(16+s*13,10),(16+s*10,22)),
                       P.disc(16+s*10, 15, 3))
        g.paint(wing, r, o, light=(-s,-1))
    return g

def glandula():  # back charm: a spore-sac cluster (green, bubbly) -- distinct from nectar
    g = Grid(32, 32)
    r, o = ramp(135, 0.7, 0.88)
    for cx, cy, rr in ((12,18,4.6),(20,16,5.2),(16,23,4.0)):
        g.paint(P.disc(cx, cy, rr), r, o, light=(-1,-1))
    return g

def nectar():  # tail charm: a single glossy amber droplet (distinct from glandula)
    g = Grid(32, 32)
    r, o = ramp(42, 0.85, 0.98)
    drop = P.union(P.disc(16, 20, 6.4), P.tri((10,20),(22,20),(16,7)))
    g.paint(drop, r, o, light=(-1,-1))
    return g

def clava():  # tail charm: a heavy spiked mace ball on a short handle
    g = Grid(32, 32)
    r, o = ramp(28, 0.6, 0.65)
    g.flat(P.rect(14, 22, 18, 28), o)                # handle
    g.paint(P.disc(16, 15, 7.2), r, o, light=(-1,-1))
    for ang in range(0, 360, 45):
        tx = 16 + 10*math.cos(math.radians(ang)); ty = 15 + 10*math.sin(math.radians(ang))
        g.paint(P.disc(tx, ty, 1.6), [hx(28,0.4,0.8)]*4, o)
    return g

ASSETS = [("antenas", antenas()), ("presas", presas()), ("olhos", olhos()),
          ("carapaca", carapaca()), ("espinhos", espinhos()), ("asas", asas()),
          ("glandula", glandula()), ("nectar", nectar()), ("clava", clava())]
paths = [(n, g.render(n, 12), 32) for n, g in ASSETS]

TILE, PAD, COLS = 150, 12, 3
rows = (len(paths)+COLS-1)//COLS
sheet = Image.new("RGBA", (TILE*COLS+PAD*(COLS+1), (TILE+PAD)*rows+PAD), (28,30,38,255))
d = ImageDraw.Draw(sheet)
for i,(name,pp,w) in enumerate(paths):
    img = Image.open(pp).convert("RGBA").resize((TILE-40,TILE-40), Image.NEAREST)
    cx = PAD + (i%COLS)*(TILE+PAD); cy = PAD + (i//COLS)*(TILE+PAD)
    tile = Image.new("RGBA",(TILE,TILE),(44,88,64,255)); tile.alpha_composite(img,(20,26))
    sheet.alpha_composite(tile,(cx,cy)); d.text((cx+4,cy+4), name, fill=(235,235,245))
sheet.save(os.path.join(P.OUT,"batch6_sheet.png"))
print("rendered:", [p[0] for p in paths])
