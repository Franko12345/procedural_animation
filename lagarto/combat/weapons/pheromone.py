"""Feromonio -- slow aura pulsing around the player."""

import math

import pygame

from ...core import palette
from ...core.mathutil import vfrom_angle
from .base import Weapon, _enemies_in


class Feromonio(Weapon):
    id = 'feromonio'; name = 'Feromônio'; hue = 285
    levels = [
        dict(slow=0.66, r=105, desc='inimigos por perto ficam lentos'),
        dict(slow=0.52, r=105, desc='+lentidao'),
        dict(slow=0.52, r=145, desc='+area'),
        dict(slow=0.40, r=170, desc='muito mais lentos, +area'),
    ]

    def tick(self, player, game, dt, st, level):
        lv = self.lv(level)
        r = lv['r'] * player.area_mult
        for e in _enemies_in(game, player.pos, r):
            e.apply_slow(lv['slow'], 0.25)

    def draw(self, surf, cam, player, st, level):
        r = self.lv(level)['r'] * player.area_mult
        sp = cam.w2s(player.pos)
        wob = 0.9 + 0.1 * math.sin(player.wobble * 1.5)
        pygame.draw.circle(surf, palette.lighten(self.color, 0.1), sp,
                           int(r * cam.zoom * wob), max(1, int(2 * cam.zoom)))
        for k in range(3):
            a = player.wobble * 40 + k * 120
            pp = cam.w2s(player.pos + vfrom_angle(a, r * 0.7))
            pygame.draw.circle(surf, self.color, pp, max(1, int(3 * cam.zoom)))
