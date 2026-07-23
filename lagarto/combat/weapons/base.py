"""Shared pieces every auto-weapon builds on: the ``Weapon`` base class, the
``_enemies_in`` body-overlap query the auras use, and ``Puddle``.

``Puddle`` lives here rather than in `acid` because enemy venom and the boss's
sky-slam spawn puddles too -- they must not have to import a weapon module.

For what a weapon *is*, see `lagarto/combat/weapons/__init__.py`.
"""

import math
import random
from pygame import Vector2
import pygame

from ...core import config as C
from ...core import palette
from ...core.mathutil import safe_norm, clamp


def _enemies_in(game, pos, r):
    """Enemies whose BODY (not just the head) is within `r` of `pos`."""
    out = []
    for e in game.enemies:
        if e.dead:
            continue
        if e.hit_test(pos, r):
            out.append(e)
    return out


class Weapon:
    id = ''
    name = ''
    hue = 0
    layer = 'under'                   # 'under' = behind body (auras), 'over' = in front
    levels = []                       # per-level dicts (index = level-1)

    @property
    def color(self):
        return palette.vibrant(self.hue, 0.85, 1.0)

    def maxlevel(self):
        return len(self.levels)

    def lv(self, level):
        return self.levels[min(level, len(self.levels)) - 1]

    def level_desc(self, level):
        if level <= 0 or level > len(self.levels):
            return ''
        return self.levels[level - 1].get('desc', '')

    def new_state(self):
        return {'t': 0.0, 'ang': random.uniform(0, 360)}

    def tick(self, player, game, dt, st, level):
        raise NotImplementedError

    def draw(self, surf, cam, player, st, level):
        pass


class Puddle:
    """A patch of ground that hurts whatever stands in it.

    ``hostile`` flips who it hurts, and **the meaning of `dmg` flips with it**:
      hostile=False (player's acid) -- `dmg` is damage per SECOND; update()
          multiplies by dt and feeds AILizard.damage()'s fractional accumulator.
      hostile=True (enemy venom)    -- `dmg` is damage per TICK, paced by this
          puddle's own `tick` timer. Player i-frames are NOT the rate limiter:
          they reopen every ~0.17s, which measured out at 42 damage a second.
    Mixing those up is the "60x damage" footgun this codebase has hit before, so
    the two paths are kept visibly apart below.

    Callers must also keep `life` shorter than the spawner's cooldown, or the
    puddles overlap and stack -- the exact bug already fixed once in `Acido`.
    """

    def __init__(self, pos, r, dmg, life, hue, hostile=False, tick=0.5, slow=None):
        self.pos = Vector2(pos)
        self.r = r
        self.dmg = dmg
        self.life = life
        self.maxlife = life
        self.hue = hue
        self.hostile = hostile
        self.tick = tick
        self.tick_t = 0.0
        self.slow = slow            # optional (mul, dur) applied alongside a landed hostile hit
        self.dead = False
        self.bubbles = [(random.uniform(-r * 0.6, r * 0.6), random.uniform(-r * 0.6, r * 0.6),
                         random.uniform(0.2, 1.0)) for _ in range(6)]
        self.t = random.uniform(0, C.TAU)

    def update(self, dt, game):
        self.life -= dt
        self.t += dt * 4
        if self.life <= 0:
            self.dead = True
            return
        if self.hostile:
            self.tick_t -= dt                 # own cadence: i-frames are far too fast
            if self.tick_t <= 0:
                self.tick_t = self.tick
                for p in game.players:
                    if p.dead or p.down:
                        continue
                    if p.pos.distance_to(self.pos) < self.r + p.max_r * 0.4:
                        landed = p.hurt(game, safe_norm(p.pos - self.pos), self.dmg)
                        if landed and self.slow:
                            p.apply_slow(*self.slow)
        else:
            for e in _enemies_in(game, self.pos, self.r + 8):
                e.damage(game, self.dmg * dt)     # `dmg` is dps -> must scale by dt

    def draw(self, surf, cam):
        f = clamp(self.life / self.maxlife, 0, 1)
        sp = cam.w2s(self.pos)
        rr = int(self.r * cam.zoom * (0.6 + 0.4 * f))
        col = palette.vibrant(self.hue, 0.8, 0.9)
        palette.glow(surf, sp, rr * 1.4, palette.darken(col, 0.2), 0.4 * f)
        pygame.draw.circle(surf, palette.darken(col, 0.35), sp, rr)
        pygame.draw.circle(surf, col, sp, rr, max(1, int(2 * cam.zoom)))
        for bx, by, bs in self.bubbles:
            wob = math.sin(self.t + bx) * 3
            bp = cam.w2s(self.pos + Vector2(bx, by + wob))
            pygame.draw.circle(surf, palette.lighten(col, 0.3), bp,
                               max(1, int(bs * 4 * cam.zoom * f)))
