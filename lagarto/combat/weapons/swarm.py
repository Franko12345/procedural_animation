"""Enxame -- orbital weapon: bugs circling the player."""

import math

import pygame

from ...core import config as C
from ...core import palette
from ...core.mathutil import safe_norm, vfrom_angle
from .base import Weapon, _enemies_in


class Enxame(Weapon):
    id = 'enxame'; name = 'Enxame'; hue = 55; layer = 'over'
    levels = [
        dict(count=2, dmg=8, r=74, desc='2 insetos orbitam e ferem'),
        dict(count=3, dmg=8, r=74, desc='+1 inseto'),
        dict(count=3, dmg=12, r=80, desc='+dano'),
        dict(count=4, dmg=12, r=88, desc='+1 inseto'),
        dict(count=5, dmg=16, r=96, desc='+1 inseto, +dano'),
    ]

    def new_state(self):
        return {'ang': 0.0}

    def tick(self, player, game, dt, st, level):
        lv = self.lv(level)
        st['ang'] = (st['ang'] + dt * 150) % 360
        n = lv['count'] + player.amount
        r = lv['r'] * player.area_mult
        for k in range(n):
            a = st['ang'] + k * (360 / n)
            op = player.pos + vfrom_angle(a, r)
            for e in _enemies_in(game, op, 44):
                if e.pos.distance_to(op) < 18 + e.max_r:
                    e.damage(game, lv['dmg'] * player.might * dt, safe_norm(e.pos - op))

    def draw(self, surf, cam, player, st, level):
        lv = self.lv(level)
        n = lv['count'] + player.amount
        r = lv['r'] * player.area_mult
        for k in range(n):
            a = st['ang'] + k * (360 / n)
            op = player.pos + vfrom_angle(a, r)
            sp = cam.w2s(op)
            palette.glow(surf, sp, 12 * cam.zoom, self.color, 0.6)
            # little procedural bug: body + flicking wings
            wing = math.sin(player.wobble * 12 + k) * 5
            for s in (-1, 1):
                w = cam.w2s(op + vfrom_angle(a + 90 * s, 6 + wing))
                pygame.draw.line(surf, palette.lighten(self.color, 0.4), sp, w,
                                 max(1, int(cam.zoom)))
            pygame.draw.circle(surf, self.color, sp, max(2, int(4 * cam.zoom)))
            pygame.draw.circle(surf, C.COL_INK, sp, max(2, int(4 * cam.zoom)), max(1, int(cam.zoom)))
