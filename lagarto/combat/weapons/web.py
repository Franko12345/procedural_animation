"""Teia -- slow-projectile weapon that sticks enemies in place."""

from ...audio import engine as audio
from ...core.mathutil import safe_norm
from ..projectile import web as mk_web
from .base import Weapon


class Teia(Weapon):
    id = 'teia'; name = 'Teia Pegajosa'; hue = 190
    levels = [
        dict(count=1, cd=2.1, desc='teia que deixa inimigos lentos'),
        dict(count=1, cd=1.6, desc='+cadencia'),
        dict(count=2, cd=1.6, desc='+1 teia'),
        dict(count=2, cd=1.3, desc='slow mais forte, +cadencia'),
    ]

    def tick(self, player, game, dt, st, level):
        st['t'] -= dt
        if st['t'] > 0:
            return
        lv = self.lv(level)
        tgt = game.nearest_enemy(player.pos, 480)
        if not tgt:
            return
        st['t'] = lv['cd'] * player.cooldown_mult
        mouth = player.spine.joints[0] + player.spine.head_dir() * player.max_r
        n = lv['count'] + player.amount
        base = safe_norm(tgt.pos - mouth)
        for k in range(n):
            off = (k - (n - 1) / 2) * 16
            aim = mouth + base.rotate(off) * 300
            game.spawn_projectile(mk_web(mouth, aim, self.color, speed=200))
        audio.play('w_web', 0.24)
