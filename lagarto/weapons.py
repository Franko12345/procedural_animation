"""Survivor-like auto-weapons: they fire/act on their own so the player just moves.

Each weapon is a small object with a **per-level table** (VS-style: each level does
something specific, shown on the card) and its own **animation**. Weapons scale with
the player's global stats: ``might`` (damage), ``cooldown_mult`` (rate), ``area_mult``
(size/range) and ``amount`` (+projectiles/orbitals). Archetypes: projectile, homing,
slow-projectile, damage-aura, slow-aura, knockback-aura, orbital and ground puddles.
"""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import audio
from . import palette
from .mathutil import safe_norm, vfrom_angle, clamp, random_dir
from .projectile import spit as mk_spit, web as mk_web, Projectile


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


# --------------------------------------------------------------------------- #
#  Projectile weapons                                                          #
# --------------------------------------------------------------------------- #

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


class Ferrao(Weapon):
    id = 'ferrao'; name = 'Ferrão Teleguiado'; hue = 40
    levels = [
        dict(dmg=1, count=1, cd=1.5, desc='ferrao que persegue inimigos'),
        dict(dmg=1, count=2, cd=1.5, desc='+1 ferrao'),
        dict(dmg=2, count=2, cd=1.3, desc='+dano, -recarga'),
        dict(dmg=2, count=3, cd=1.2, desc='+1 ferrao'),
        dict(dmg=3, count=4, cd=1.0, desc='+1 ferrao, +dano'),
    ]

    def tick(self, player, game, dt, st, level):
        st['t'] -= dt
        if st['t'] > 0 or not any(not e.dead for e in game.enemies):
            return
        lv = self.lv(level)
        st['t'] = lv['cd'] * player.cooldown_mult
        mouth = player.spine.joints[0] + player.spine.head_dir() * player.max_r
        n = lv['count'] + player.amount
        for k in range(n):
            v = random_dir(240)
            pr = Projectile(mouth, v, self.color,
                            dmg=int(round(lv['dmg'] * player.might)),
                            radius=6, hostile=False, life=3.0)
            pr.homing = True
            game.spawn_projectile(pr)
        game.fx.spark_burst(mouth, self.color, 3, 150)
        audio.play('w_homing', 0.28)


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


# --------------------------------------------------------------------------- #
#  Aura weapons (pulsing fields around the player)                             #
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
#  Orbital weapon                                                              #
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
#  Ground puddle weapon                                                        #
# --------------------------------------------------------------------------- #

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


WEAPONS = {w.id: w for w in [Cuspe(), Ferrao(), Teia(), Esporos(),
                             Feromonio(), Sopro(), Enxame(), Acido()]}
