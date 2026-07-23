"""Sopro -- knockback aura that pushes and chips enemies around the player."""

import math

import pygame

from ...core import palette
from ...core.mathutil import safe_norm
from .base import Weapon, _enemies_in


class Sopro(Weapon):
    id = 'sopro'; name = 'Sopro Repelente'; hue = 200
    levels = [
        dict(push=260, dps=2, r=95, desc='empurra e fere inimigos ao redor'),
        dict(push=340, dps=2, r=95, desc='+empurrao'),
        dict(push=340, dps=3, r=125, desc='+area'),
        dict(push=430, dps=5, r=140, desc='+empurrao, +dano'),
    ]

    def tick(self, player, game, dt, st, level):
        lv = self.lv(level)
        r = lv['r'] * player.area_mult
        for e in _enemies_in(game, player.pos, r):
            d = safe_norm(e.pos - player.pos)
            e.vel += d * lv['push'] * dt
            e.damage(game, lv['dps'] * player.might * dt)

    def draw(self, surf, cam, player, st, level):
        r = self.lv(level)['r'] * player.area_mult
        st['ang'] = (st.get('ang', 0) + 90) % 360           # rotating shimmer
        sp = cam.w2s(player.pos)
        f = 0.6 + 0.4 * math.sin(player.wobble * 3)
        palette.glow(surf, sp, r * cam.zoom * (0.7 + 0.3 * f), self.color, 0.35)
        pygame.draw.circle(surf, palette.lighten(self.color, 0.3), sp,
                           int(r * cam.zoom * (0.9 + 0.1 * f)), max(1, int(2 * cam.zoom)))
