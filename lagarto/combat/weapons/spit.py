"""Cuspe -- projectile weapon that spits at the nearest enemy."""

from ...audio import engine as audio
from ...core.mathutil import safe_norm
from ..projectile import spit as mk_spit
from .base import Weapon


class Cuspe(Weapon):
    id = 'cuspe'; name = 'Cuspe Ácido'; hue = 105
    levels = [
        dict(dmg=1, count=1, cd=1.05, desc='cospe no inimigo mais proximo'),
        dict(dmg=2, count=1, cd=1.05, desc='+dano'),
        dict(dmg=2, count=2, cd=1.0,  desc='+1 projetil'),
        dict(dmg=3, count=2, cd=0.9,  desc='+dano, -recarga'),
        dict(dmg=3, count=3, cd=0.85, desc='+1 projetil'),
        dict(dmg=4, count=4, cd=0.72, desc='+1 projetil, -recarga'),
    ]

    def tick(self, player, game, dt, st, level):
        st['t'] -= dt
        if st['t'] > 0:
            return
        lv = self.lv(level)
        tgt = game.nearest_enemy(player.pos, 470)
        if not tgt:
            return
        st['t'] = lv['cd'] * player.cooldown_mult
        mouth = player.spine.joints[0] + player.spine.head_dir() * player.max_r
        base = safe_norm(tgt.pos - mouth)
        n = lv['count'] + player.amount
        for k in range(n):
            off = (k - (n - 1) / 2) * 12
            aim = mouth + base.rotate(off) * 300
            game.spawn_projectile(mk_spit(
                mouth, aim, self.color, dmg=int(round(lv['dmg'] * player.might)),
                effect='poison' if player.venom else None, speed=330, radius=6,
                hostile=False))
        game.fx.spark_burst(mouth, self.color, 3, 130)
        audio.play('w_spit', 0.30)
