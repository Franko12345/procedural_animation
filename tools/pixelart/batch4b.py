import os
import pxgen as P
from pxgen import Grid
from PIL import Image
from batch3 import hx, ramp

def vigor():  # might: a clear fist -- rounded knuckle row + palm block + thumb notch
    g = Grid(32, 32)
    r, o = ramp(2, 0.7, 0.82)
    knuckles = P.union(*[P.disc(9+i*4.4, 11, 3.4) for i in range(4)])
    palm = P.rect(7, 13, 25, 24)
    thumb = P.union(P.disc(6, 17, 3.4), P.rect(5, 17, 9, 21))
    shape = P.union(knuckles, palm, thumb)
    g.paint(shape, r, o, light=(-1,-1.2))
    # knuckle creases (dark grooves between fingers)
    for x in (11, 15.5, 20):
        g.line(x, 9, x, 14, hx(2, 0.7, 0.5))
    return g

def arranco():  # dash: a paw print (pad + 3 toes) + motion lines -- reads as a STEP
    g = Grid(32, 32)
    r, o = ramp(178, 0.7, 0.88)
    pad = P.disc(13, 21, 5.0)
    toes = P.union(P.disc(8,13,2.6), P.disc(13,10,2.8), P.disc(18,13,2.6))
    g.paint(P.union(pad, toes), r, o, light=(-1,-1))
    for i, yy in enumerate((15, 21, 27)):
        length = 7 - abs(yy-21)
        g.line(20, yy, 20+length, yy, hx(178,0.45,0.95))
    return g

for name, g in (("might", vigor()), ("dash", arranco())):
    g.render(name, 12)

# quick 2-up check tile
imgs = [Image.open(os.path.join(P.OUT, n+".png")).convert("RGBA") for n in ("might","dash")]
sheet = Image.new("RGBA", (200*2+30, 220), (44,88,64,255))
for i, img in enumerate(imgs):
    disp = img.resize((180,180), Image.NEAREST)
    sheet.alpha_composite(disp, (10+i*205, 20))
sheet.save(os.path.join(P.OUT, "batch4b_check.png"))
print("re-rendered: might, dash")
