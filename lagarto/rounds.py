"""Round manager: themed waves that DRIP in from destructible nests, with telegraphs.

Instead of dumping every enemy at once, each round picks a **theme** (composition),
places 1-2 **Nests** (organic POIs) near the players, and the nests emit enemies one
at a time through a growing **SpawnMark** telegraph (so nothing spawns on top of you).
Destroying a nest cuts its flow -> agency. The round clears when the budget is spent
(or every nest is destroyed) and no enemies remain. Between rounds sits a short
intermission which Phase 3 turns into the camp (route + shop).
"""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import palette
from . import species
from .mathutil import vfrom_angle, clamp

# theme -> (banner, enemy pool, budget multiplier, max alive at once)
THEMES = {
    'enxame':     dict(banner='ENXAME', pool=['runner', 'runner', 'spiky', 'snake'],
                       budget=1.7, cap=11),
    'cuspidores': dict(banner='CHUVA DE CUSPIDORES', pool=['spitter', 'spitter', 'runner'],
                       budget=1.0, cap=7),
    'tanques':    dict(banner='MARCHA DOS TANQUES', pool=['tank', 'horned', 'tank'],
                       budget=0.7, cap=5),
    'aranhas':    dict(banner='NOITE DAS ARANHAS', pool=['spider', 'spider', 'scorpion'],
                       budget=1.0, cap=7),
    'invasao':    dict(banner='INVASAO', pool=list(species.ENEMY_SPECIES),
                       budget=1.05, cap=8),
}
THEME_KEYS = list(THEMES.keys())


class SpawnMark:
    """A growing ground marker; when it fills, the enemy erupts from it."""
    def __init__(self, pos, species_key, hp_bonus, speed_mul, delay=0.85):
        self.pos = Vector2(pos)
        self.species_key = species_key
        self.hp_bonus = hp_bonus
        self.speed_mul = speed_mul
        self.t = 0.0
        self.delay = delay
        self.done = False

    def update(self, dt, game):
        self.t += dt
        if self.t >= self.delay:
            e = species.make(self.species_key, self.pos)
            e.hp += self.hp_bonus
            e.max_speed *= self.speed_mul
            game.enemies.append(e)
            game.fx.ring(self.pos, e.color)
            game.fx.burst(self.pos, e.color, 10, 160)
            self.done = True

    def draw(self, surf, cam):
        f = clamp(self.t / self.delay, 0, 1)
        sp = cam.w2s(self.pos)
        r = int((14 + 26 * f) * cam.zoom)
        col = (255, 80, 90)
        pygame.draw.circle(surf, col, sp, r, max(1, int(2 * cam.zoom)))
        pygame.draw.circle(surf, col, sp, max(1, int(r * f * 0.7)))
        palette.glow(surf, sp, r * 1.3, col, 0.4 + 0.4 * f)


class Nest:
    """A pulsing organic mound that emits enemies; destroy it to stop the flow."""
    def __init__(self, pos, hp, pool):
        self.pos = Vector2(pos)
        self.hp = hp
        self.maxhp = hp
        self.pool = pool
        self.dead = False
        self.max_r = 34
        self.emit_cd = random.uniform(1.2, 2.6)
        self.pulse = random.uniform(0, C.TAU)
        self.hit_flash = 0.0

    def update(self, dt):
        self.pulse += dt * 3
        self.hit_flash = max(0.0, self.hit_flash - dt * 3)
        self.emit_cd -= dt
        return self.emit_cd <= 0        # ready to emit?

    def reset_emit(self, faster):
        self.emit_cd = random.uniform(*( (0.7, 1.6) if faster else (1.4, 2.8) ))

    def take_hit(self, game, dmg):
        self.hp -= dmg
        self.hit_flash = 1.0
        game.fx.burst(self.pos, (170, 120, 90), 6, 150)
        if self.hp <= 0 and not self.dead:
            self.dead = True
            game.fx.burst(self.pos, (200, 150, 110), 30, 300)
            game.fx.spark_burst(self.pos, (255, 220, 160), 20, 360)
            game.fx.ring(self.pos, (220, 170, 120))
            game.shake(8)
            game.spawn_fruit(self.pos)
            if random.random() < 0.22:              # rare: nests can drop a charm
                from . import charms as CH
                p = game.nearest_player(self.pos) or (game.players[0] if game.players else None)
                if p and not p.dead:
                    avail = [c for c in CH.CHARMS if c not in p.charms_owned]
                    if avail:
                        cid = random.choice(avail)
                        p.gain_charm(cid, game)
                        game.fx.popup(self.pos, f"CHARM: {CH.CHARMS[cid].name}", CH.CHARMS[cid].color)

    def draw(self, surf, cam):
        sp = cam.w2s(self.pos)
        breathe = 1.0 + 0.06 * math.sin(self.pulse)
        r = int(self.max_r * cam.zoom * breathe)
        base = (96, 66, 52)
        if self.hit_flash > 0:
            base = tuple(int(b + (255 - b) * self.hit_flash) for b in base)
        # lumpy mound
        for dx, dy, rr in ((-0.5, 0.1, 0.9), (0.5, 0.1, 0.9), (0, -0.4, 0.8), (0, 0.3, 1.0)):
            p = (sp[0] + int(dx * r), sp[1] + int(dy * r))
            pygame.draw.circle(surf, base, p, max(2, int(rr * r)))
        # glowing maw that brightens as it's about to emit
        heat = clamp(1.0 - self.emit_cd / 2.6, 0, 1)
        palette.glow(surf, sp, r * 1.1, (255, 120, 80), 0.3 + 0.5 * heat)
        pygame.draw.circle(surf, (30, 16, 14), sp, max(2, int(r * 0.42)))
        pygame.draw.circle(surf, palette.mix((60, 30, 24), (255, 140, 90), heat),
                           sp, max(1, int(r * 0.42 * (0.4 + 0.5 * heat))))
        # hp pip ring
        if self.hp < self.maxhp:
            f = clamp(self.hp / self.maxhp, 0, 1)
            pygame.draw.arc(surf, (120, 240, 120),
                            (sp[0] - r - 6, sp[1] - r - 6, 2 * (r + 6), 2 * (r + 6)),
                            -math.pi / 2, -math.pi / 2 + f * C.TAU, max(2, int(3 * cam.zoom)))


class RoundManager:
    def __init__(self, game):
        self.game = game
        self.wave = 0
        self.state = 'intermission'     # intermission | combat | cleared
        self.timer = 2.5                # short delay before round 1
        self.theme = 'invasao'
        self._next_theme = None
        self.banner_t = 0.0
        self.budget = 0
        self.nests = []
        self.marks = []

    # ---- lifecycle ------------------------------------------------------ #
    def start_round(self, theme=None):
        self.wave += 1
        g = self.game
        self.theme = theme or self._next_theme or self._pick_theme()
        self._next_theme = None
        spec = THEMES[self.theme]
        self.budget = int((4 + self.wave * 1.6) * spec['budget'])
        self.state = 'combat'
        self.banner_t = 2.2
        self.marks = []
        # place nests near the players
        center = g.alive_players()[0].pos if g.alive_players() \
            else Vector2(C.WORLD_W / 2, C.WORLD_H / 2)
        n_nests = 1 + (self.wave // 3)
        self.nests = []
        for _ in range(min(n_nests, 3)):
            pos = center + vfrom_angle(random.uniform(0, 360), random.uniform(360, 620))
            pos.x = clamp(pos.x, 80, C.WORLD_W - 80)
            pos.y = clamp(pos.y, 80, C.WORLD_H - 80)
            self.nests.append(Nest(pos, 6 + self.wave * 2, spec['pool']))
        g.wave = self.wave

    def _pick_theme(self):
        if self.wave <= 1:
            return 'invasao'
        return random.choice(THEME_KEYS)

    def _alive_enemies(self):
        return sum(1 for e in self.game.enemies if not e.dead)

    def cleared(self):
        return (self.budget <= 0 and self._alive_enemies() == 0
                and not self.marks) or \
               (all(n.dead for n in self.nests) and self._alive_enemies() == 0
                and not self.marks)

    # ---- per-frame ------------------------------------------------------ #
    def update(self, dt):
        g = self.game
        self.banner_t = max(0.0, self.banner_t - dt)
        self.nests = [n for n in self.nests if not n.dead]

        if self.state == 'intermission':
            self.timer -= dt
            if self.timer <= 0:
                self.start_round()
            return

        if self.state == 'cleared':
            # wait here; the game opens the camp (route + shop) and calls request_next.
            return

        if self.state == 'combat':
            spec = THEMES[self.theme]
            for m in self.marks:
                m.update(dt, g)
            self.marks = [m for m in self.marks if not m.done]
            # emit from nests up to the alive cap and remaining budget
            if self.budget > 0 and self._alive_enemies() + len(self.marks) < spec['cap']:
                live = [n for n in self.nests if not n.dead]
                for n in live:
                    if n.update(dt) and self.budget > 0 and \
                            self._alive_enemies() + len(self.marks) < spec['cap']:
                        key = random.choice(spec['pool'])
                        pos = n.pos + vfrom_angle(random.uniform(0, 360), random.uniform(20, 70))
                        self.marks.append(SpawnMark(pos, key, self.wave // 3,
                                                    1.0 + min(self.wave * 0.02, 0.4)))
                        self.budget -= 1
                        n.reset_emit(self.wave > 4)
            else:
                for n in self.nests:
                    n.update(dt)         # keep pulse/flash advancing

            if self.cleared():
                self.state = 'cleared'
                self.timer = 3.0
                if g.alive_players():
                    g.fx.popup(g.alive_players()[0].pos + Vector2(0, -140),
                               "ONDA LIMPA!", C.COL_WHITE)

    def request_next(self, theme=None):
        """Called after the camp to begin the next round (optionally a chosen theme)."""
        self._next_theme = theme
        self.state = 'intermission'
        self.timer = 0.6

    # ---- draw ----------------------------------------------------------- #
    def draw_world(self, surf, cam):
        for n in self.nests:
            if not n.dead and cam.visible(n.pos, 80):
                n.draw(surf, cam)
        for m in self.marks:
            if cam.visible(m.pos, 60):
                m.draw(surf, cam)

    def draw_banner(self, surf, font, bigfont):
        if self.banner_t > 0 and self.state == 'combat':
            a = clamp(self.banner_t / 2.2, 0, 1)
            txt = bigfont.render(THEMES[self.theme]['banner'], True, C.COL_ENEMY)
            sub = font.render(f"Onda {self.wave}", True, (220, 220, 235))
            y = 110
            surf.blit(txt, (C.WIDTH // 2 - txt.get_width() // 2, y))
            surf.blit(sub, (C.WIDTH // 2 - sub.get_width() // 2, y + txt.get_height()))
