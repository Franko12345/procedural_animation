"""Esporos -- damage aura pulsing around the player."""

import math
import random

import pygame

from ...core import palette
from ...core.mathutil import random_dir
from .base import Weapon, _enemies_in


class Esporos(Weapon):
    id = 'esporos'; name = 'Nuvem de Esporos'; hue = 135
    levels = [
        dict(dps=7, r=95,  desc='nuvem que fere quem chega perto'),
        dict(dps=10, r=95, desc='+dano'),
        dict(dps=10, r=125, desc='+area'),
        dict(dps=14, r=125, desc='+dano'),
        dict(dps=18, r=160, desc='+area, +dano'),
    ]

    def tick(self, player, game, dt, st, level):
        lv = self.lv(level)
        r = lv['r'] * player.area_mult
        for e in _enemies_in(game, player.pos, r):
            e.damage(game, lv['dps'] * player.might * dt)
        if random.random() < dt * 14:
            p = player.pos + random_dir(random.uniform(0, r))
            game.fx.burst(p, self.color, 1, 40)

    def draw(self, surf, cam, player, st, level):
        r = self.lv(level)['r'] * player.area_mult
        sp = cam.w2s(player.pos)
        pulse = 0.85 + 0.15 * math.sin(player.wobble * 2)
        palette.glow(surf, sp, r * cam.zoom * pulse, palette.darken(self.color, 0.3), 0.5)
        pygame.draw.circle(surf, self.color, sp, int(r * cam.zoom * pulse),
                           max(1, int(2 * cam.zoom)))
