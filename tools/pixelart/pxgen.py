"""Authoring layer for the pixel-art skill.

Shapes are defined as coverage masks (super-sampled predicates), then painted with
a 4-stop colour ramp: manual anti-aliasing on the curved edge, a selective (dark
fill, not pure black) outline, a top-left highlight and a bottom-right shade -- the
recipe the game's own parts.py/icons.py use, rasterised to pixels."""
import json
import math
import os
import subprocess

SKILL = "/home/franko/prog/procedural_animation/.claude/skills/pixel-art-gen/scripts/render_pixel_art.py"
OUT = os.path.dirname(__file__)


# ---- shape predicates (float coords) -------------------------------------- #
def disc(cx, cy, r):
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r

def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1

def tri(p0, p1, p2):
    def a(u, v, w):
        return (v[0]-u[0])*(w[1]-u[1]) - (v[1]-u[1])*(w[0]-u[0])
    A = a(p0, p1, p2)
    s = 1 if A > 0 else -1
    def f(x, y):
        q = (x, y)
        return (a(p0, p1, q)*s >= 0) and (a(p1, p2, q)*s >= 0) and (a(p2, p0, q)*s >= 0)
    return f

def union(*preds):
    return lambda x, y: any(p(x, y) for p in preds)

def diff(a, b):
    return lambda x, y: a(x, y) and not b(x, y)


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.c = {}

    def px(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h and col:
            self.c[(int(x), int(y))] = col

    def coverage(self, pred, ss=4):
        cov = {}
        for y in range(self.h):
            for x in range(self.w):
                n = 0
                for sy in range(ss):
                    for sx in range(ss):
                        if pred(x + (sx + 0.5) / ss, y + (sy + 0.5) / ss):
                            n += 1
                if n:
                    cov[(x, y)] = n / (ss * ss)
        return cov

    def paint(self, pred, ramp, outline, light=(-1, -1), ss=4):
        """ramp = [highlight, base, shade, edge] light->dark. Volume + AA + sel-out."""
        hi, base, shade, edge = ramp
        cov = self.coverage(pred, ss)
        inside = {k for k, v in cov.items() if v >= 0.5}
        if not inside:
            return cov
        def isin(x, y):
            return (x, y) in inside
        xs = [k[0] for k in inside]; ys = [k[1] for k in inside]
        cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
        R = max(1.0, max(math.hypot(x - cx, y - cy) for x, y in inside))
        lx, ly = light
        for (x, y), v in cov.items():
            if v < 0.5:                              # anti-aliased fringe
                if v >= 0.16:
                    self.px(x, y, edge)
                continue
            if not (isin(x-1, y) and isin(x+1, y) and isin(x, y-1) and isin(x, y+1)):
                self.px(x, y, shade)                 # inner rim
                continue
            nx, ny = (x - cx) / R, (y - cy) / R
            d = nx * lx + ny * ly                    # >0 toward the light (top-left)
            self.px(x, y, hi if d > 0.42 else (shade if d < -0.62 else base))
        self._outline_from(cov, outline)
        return cov

    def _outline_from(self, cov, col):
        filled = set(self.c.keys())
        add = {}
        for (x, y) in cov:
            if cov[(x, y)] < 0.16:
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = (x + dx, y + dy)
                    if p not in filled and 0 <= p[0] < self.w and 0 <= p[1] < self.h:
                        add[p] = col
        self.c.update(add)

    def flat(self, pred, col, ss=4):
        for (x, y), v in self.coverage(pred, ss).items():
            if v >= 0.5:
                self.px(x, y, col)

    def line(self, x0, y0, x1, y1, col, wide=0):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for ox in range(-wide, wide + 1):
                for oy in range(-wide, wide + 1):
                    self.px(x0 + ox, y0 + oy, col)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    def arc(self, cx, cy, r, a0, a1, col, step=6):
        a = a0
        while a <= a1:
            self.px(round(cx + r * math.cos(math.radians(a))),
                    round(cy + r * math.sin(math.radians(a))), col)
            a += step

    def outline_all(self, col):
        filled = set(self.c)
        add = {}
        for (x, y) in filled:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    p = (x + dx, y + dy)
                    if p not in filled and 0 <= p[0] < self.w and 0 <= p[1] < self.h:
                        add[p] = col
        self.c.update(add)

    def json(self, pixel_size, bg="transparent"):
        return dict(width=self.w, height=self.h, background=bg, grid_lines=False,
                    pixel_size=pixel_size,
                    pixels=[{"x": x, "y": y, "color": c} for (x, y), c in sorted(self.c.items())])

    def render(self, name, pixel_size=12):
        jp = os.path.join(OUT, name + ".json")
        pp = os.path.join(OUT, name + ".png")
        with open(jp, "w") as f:
            json.dump(self.json(pixel_size), f)
        subprocess.run(["python3", SKILL, jp, "-o", pp, "-p", str(pixel_size)],
                       check=True, stdout=subprocess.DEVNULL)
        return pp
