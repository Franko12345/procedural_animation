"""Camera: follows one player, or frames both in co-op (lerped pos + zoom).

Also owns screen shake. ``w2s`` / ``s2w`` convert between world and screen space.
"""

import math
import random
from pygame import Vector2

from ..core import config as C
from ..core.mathutil import clamp, lerp, random_dir


class Camera:
    def __init__(self, center=None):
        self.pos = Vector2(C.WORLD_W / 2, C.WORLD_H / 2)
        self.zoom = 1.0
        self.shake_mag = 0.0
        self.shake_off = Vector2()
        # where world-space `pos` lands on screen; menus use this to render a
        # live creature inside a panel instead of the middle of the screen.
        self.center = center or (C.WIDTH / 2, C.HEIGHT / 2)

    def follow(self, players, dt):
        alive = [p for p in players if not p.dead]
        if not alive:
            return
        center = Vector2()
        for p in alive:
            center += p.pos
        center /= len(alive)

        target_zoom = 1.0
        if len(alive) > 1:
            span = max(alive[0].pos.distance_to(alive[1].pos), 1)
            target_zoom = clamp(min(C.WIDTH, C.HEIGHT) / (span + 380), 0.55, 1.05)

        self.pos = self.pos.lerp(center, clamp(6 * dt, 0, 1))
        self.zoom = lerp(self.zoom, target_zoom, clamp(4 * dt, 0, 1))

        if self.shake_mag > 0.2:
            self.shake_off = random_dir(self.shake_mag)
            self.shake_mag *= math.exp(-9 * dt)
        else:
            self.shake_off = Vector2()

    def add_shake(self, m):
        self.shake_mag = min(self.shake_mag + m, 26)

    def w2s(self, world):
        cx, cy = self.center
        x = (world[0] - self.pos.x) * self.zoom + cx + self.shake_off.x
        y = (world[1] - self.pos.y) * self.zoom + cy + self.shake_off.y
        return (int(x), int(y))

    def s2w(self, screen):
        cx, cy = self.center
        x = (screen[0] - cx - self.shake_off.x) / self.zoom + self.pos.x
        y = (screen[1] - cy - self.shake_off.y) / self.zoom + self.pos.y
        return Vector2(x, y)

    def visible(self, pos, margin=80):
        s = self.w2s(pos)
        return -margin < s[0] < C.WIDTH + margin and -margin < s[1] < C.HEIGHT + margin
