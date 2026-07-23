"""Acido -- ground-puddle weapon. ``Puddle`` itself lives in `base`, because
enemy venom and boss slams spawn puddles without touching this weapon."""

import random

from ...audio import engine as audio
from ...core.mathutil import random_dir
from .base import Weapon, Puddle


class Acido(Weapon):
    id = 'acido'; name = 'Poça de Ácido'; hue = 95
    # NOTE: `dmg` here is damage *per second* (Puddle.update multiplies by dt), not
    # damage per hit. Same for Enxame. `life` is short on purpose: it used to be
    # longer than `cd`, so several puddles piled onto the same enemy at once.
    levels = [
        dict(count=1, cd=2.4, r=52, dmg=4, life=2.0, desc='solta pocas que ferem no chao'),
        dict(count=1, cd=2.4, r=52, dmg=5, life=2.0, desc='+dano'),
        dict(count=1, cd=1.9, r=60, dmg=5, life=2.2, desc='+cadencia, +area'),
        dict(count=2, cd=1.9, r=60, dmg=5, life=2.2, desc='+1 poca'),
        dict(count=2, cd=1.6, r=74, dmg=6, life=2.4, desc='+area, +dano, +cadencia'),
    ]

    def tick(self, player, game, dt, st, level):
        st['t'] -= dt
        if st['t'] > 0:
            return
        lv = self.lv(level)
        st['t'] = lv['cd'] * player.cooldown_mult
        n = lv['count'] + max(0, player.amount)
        # Spread over DISTINCT enemies. Re-querying nearest_enemy inside the loop put
        # every puddle on the SAME target (the world doesn't advance between
        # iterations) scattered within 60px while each has radius ~80 -- they
        # overlapped almost perfectly. That stacking, not the per-frame damage, is
        # what made acid ~3x the other auras.
        foes = sorted((e for e in game.enemies if not e.dead),
                      key=lambda e: e.pos.distance_squared_to(player.pos))
        foes = [e for e in foes if e.pos.distance_to(player.pos) < 420][:n]
        for i in range(n):
            if i < len(foes):
                base, spread = foes[i].pos, 60
            else:                       # more puddles than targets: scatter wide
                base, spread = player.pos, 180
            pos = base + random_dir(random.uniform(0, spread))
            game.spawn_puddle(Puddle(pos, lv['r'] * player.area_mult,
                                     lv['dmg'] * player.might, lv['life'], self.hue))
        audio.play('w_puddle', 0.26)
