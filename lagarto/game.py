"""Game: world state, spawning, waves, collisions, HUD and the fixed-step update.

Holds the players, AI lizards and pickups, resolves eating/combat, drives the
escalating predator waves and draws everything (background, shadows, entities,
particles, HUD, game-over).
"""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from .mathutil import clamp, vfrom_angle, safe_norm
from .spine import build_radii
from .lizard import Player, AILizard
from . import species
from . import evolution
from . import audio
from . import icons
from . import ui
from . import progression
from . import palette
from . import weapons
from . import charms as charmlib
from .pickups import Bug, Fruit, Egg
from .fx import FX, shadow
from .camera import Camera
from .world import World
from .collision import separate
from .rounds import RoundManager

def _dial(surf, center, r, frac, color, font, label, t, enabled=True):
    """Radial cooldown dial: fills as the ability recharges, pulses when ready.

    ``enabled=False`` (not enough energy) greys the whole thing out.
    """
    ready = frac >= 0.999 and enabled
    if not enabled:
        color = (78, 82, 104)
    pygame.draw.circle(surf, (34, 38, 54), center, r)
    if frac > 0:
        pts = [center]
        steps = max(3, int(frac * 22))
        for i in range(steps + 1):
            pts.append(center + vfrom_angle(-90 + 360 * frac * (i / steps), r))
        if len(pts) >= 3:
            pygame.draw.polygon(surf, color, pts)
    if ready:
        pulse = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(t * 6))
        palette.glow(surf, center, r * 2.2, color, pulse)
    pygame.draw.circle(surf, (96, 102, 136) if not ready else color, center, r, 2)
    im = font.render(label, True, (206, 208, 226) if ready else (130, 134, 160))
    surf.blit(im, (center[0] + r + 6, center[1] - im.get_height() // 2))


_VIGNETTE = None


def _vignette(surf):
    """Smooth radial dark edges so the vivid centre pops (built once, then blitted)."""
    global _VIGNETTE
    if _VIGNETTE is None:
        s = 80
        small = pygame.Surface((s, s), pygame.SRCALPHA)
        cx = cy = (s - 1) / 2.0
        maxd = (cx * cx + cy * cy) ** 0.5
        for y in range(s):
            for x in range(s):
                d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / maxd
                a = 0 if d < 0.4 else int(150 * ((d - 0.4) / 0.6) ** 2)
                small.set_at((x, y), (0, 0, 0, min(150, a)))
        _VIGNETTE = pygame.transform.smoothscale(small, (C.WIDTH, C.HEIGHT))
    surf.blit(_VIGNETTE, (0, 0))


class Game:
    def __init__(self, num_players, controllers, font, bigfont, meta=None, mode='normal'):
        self.mode = mode                     # 'normal' (ends at the final boss) | 'endless'
        self.meta = meta if meta is not None else progression.load()
        self.run_banked = False
        self.font = font
        self.bigfont = bigfont
        self.cam = Camera()
        self.fx = FX()
        self.world = World()

        cx, cy = C.WORLD_W / 2, C.WORLD_H / 2
        self.cam.pos = Vector2(cx, cy)
        self.players = []
        for i in range(num_players):
            off = Vector2(-80 if i == 0 else 80, 0)
            colorset = C.COL_PLAYER if i == 0 else C.COL_PLAYER2
            pl = Player(Vector2(cx, cy) + off, controllers[i], colorset, i)
            progression.apply_to_player(self.meta, pl)     # permanent upgrades
            self.players.append(pl)

        self.enemies = []
        self.friends = []
        self.prey = []
        self.pickups = []
        self.projectiles = []
        self.puddles = []

        self.score = 0
        self.kills = 0
        self.wave = 0
        self.wave_timer = 4.0
        self.time = 0.0
        self.state = 'play'
        self.combo = 0
        self.combo_timer = 0.0
        self.combo_flash = 0.0
        self.pollen = 0
        self.hitstop = 0.0        # freeze frames on heavy impacts
        self.flash = 0.0          # brief white screen flash
        self.camp = None
        self.rounds = RoundManager(self)
        self.cards = []
        self.card_idx = 0
        self.levelup_player = None

        for _ in range(46):
            self.pickups.append(Bug(self._rand_world()))
        for _ in range(12):
            self.pickups.append(Fruit(self._rand_world()))
        for _ in range(6):
            self.pickups.append(Egg(self._rand_world()))
        for _ in range(8):
            self.prey.append(self._spawn_prey())

    # ---- helpers -------------------------------------------------------- #
    def _rand_world(self, margin=120):
        return Vector2(random.uniform(margin, C.WORLD_W - margin),
                       random.uniform(margin, C.WORLD_H - margin))

    def _rand_edge_near(self, center, dist=560):
        return center + vfrom_angle(random.uniform(0, 360), dist)

    def shake(self, m):
        self.cam.add_shake(m)

    def punch(self, freeze=0.06, shake=6, flash=0.0):
        """Impact feedback: brief freeze + shake (+ optional screen flash)."""
        self.hitstop = max(self.hitstop, freeze)
        self.cam.add_shake(shake)
        if flash:
            self.flash = max(self.flash, flash)

    def add_score(self, n):
        self.score += int(n * self.combo_mult())

    def combo_mult(self):
        return 1.0 + min(self.combo, 30) * 0.08     # up to ~3.4x

    def add_combo(self):
        self.combo += 1
        self.combo_timer = 3.2
        self.combo_flash = 1.0

    def add_pollen(self, n):
        mult = max((getattr(p, 'pollen_mult', 1.0) for p in self.players), default=1.0)
        self.pollen += int(n * self.combo_mult() * mult)

    def alive_players(self):
        return [p for p in self.players if not p.dead]

    def nearest_player(self, pos):
        best, bd = None, 1e9
        for p in self.players:
            if p.dead or p.down:
                continue
            d = p.pos.distance_to(pos)
            if d < bd:
                best, bd = p, d
        return best

    def nearest_enemy(self, pos, rng):
        best, bd = None, rng
        for e in self.enemies:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def nearest_prey(self, pos, rng):
        best, bd = None, rng
        for e in self.prey:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def nearest_threat(self, pos, rng):
        """Closest thing a prey should flee: a player or a predator."""
        best, bd = None, rng
        for p in self.players:
            if p.dead or p.down:
                continue
            d = p.pos.distance_to(pos)
            if d < bd:
                best, bd = p, d
        for e in self.enemies:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def give_xp(self, amount):
        for p in self.players:
            if not p.dead and not p.down:
                p.gain_xp(amount, self)

    def _enter_levelup(self, player):
        self.levelup_player = player
        self.cards = evolution.roll_cards(player, 3)
        self.card_idx = 0
        self.state = 'levelup'
        audio.play('levelup')
        self.fx.popup(player.pos, f"NIVEL {player.level}!", C.COL_WHITE)
        self.fx.ring(player.pos, player.colorset[0])
        self.shake(4)

    def choose_card(self, i):
        if self.state != 'levelup' or not self.cards:
            return
        i = max(0, min(len(self.cards) - 1, i))
        card = self.cards[i]
        p = self.levelup_player
        if getattr(card, 'is_weapon', False):
            card.apply(p, self)
            self.fx.burst(p.pos, card.color, 22, 250)
            self.fx.spark_burst(p.pos, palette.lighten(card.color, 0.4), 14, 320)
            self.fx.ring(p.pos, card.color)
        else:
            p.apply_mutation(card, self)
        p.pending_levelups = max(0, p.pending_levelups - 1)
        audio.play('evolve')
        self.fx.popup(p.pos, card.name, card.color)
        self.cards = []
        self.state = 'play'          # step() re-enters if more level-ups are queued

    # ---- camp (route + shop between rounds) ----------------------------- #
    def _enter_camp(self):
        from .rounds import THEMES, THEME_KEYS
        picks = random.sample(THEME_KEYS, min(3, len(THEME_KEYS)))
        bonuses = ['cura', 'polen', 'carta']
        random.shuffle(bonuses)
        routes = [dict(theme=k, bonus=bonuses[i % 3], label=THEMES[k]['banner'])
                  for i, k in enumerate(picks)]
        self.camp = dict(routes=routes, shop=self._roll_shop(), sel=0,
                         focus='route', shop_sel=0)
        self._route_rects = []
        self._shop_rects = []
        self._charm_rects = []
        self.state = 'camp'
        for p in self.players:
            if not p.dead:
                p.health = min(p.max_health, p.health + p.max_health * 0.12)

    def _roll_shop(self):
        def heal(g):
            for pl in g.players:
                pl.health = min(pl.max_health, pl.health + 40)

        def vitality(g):
            for pl in g.players:
                pl.max_health += 20; pl.health += 20

        def might(g):
            for pl in g.players:
                pl.might *= 1.15

        def haste(g):
            for pl in g.players:
                pl.cooldown_mult *= 0.9

        def egg(g):
            for pl in g.players:
                if pl.dead:
                    continue
                f = AILizard(pl.pos, 'friend', 0.9, C.COL_FRIEND)
                f.hp = 3
                g.friends.append(f)

        def charm(g):
            for pl in g.players:
                if pl.dead:
                    continue
                avail = [c for c in charmlib.CHARMS if c not in pl.charms_owned
                         and progression.unlocked(self.meta, 'charm', c)]
                if avail:
                    pl.gain_charm(random.choice(avail), g)
        return [
            dict(name='Nectar de Cura', desc='+40 vida', cost=12, hue=140, icon='health', fn=heal),
            dict(name='Vitalidade', desc='+20 vida maxima', cost=28, hue=5, icon='health', fn=vitality),
            dict(name='Vigor', desc='+15% dano das armas', cost=32, hue=0, icon='might', fn=might),
            dict(name='Charm', desc='adaptacao p/ um slot', cost=30, hue=280, icon='nectar', fn=charm),
            dict(name='Ovo de Amigo', desc='invoca um aliado', cost=24, hue=270, icon='legs', fn=egg),
        ]

    def camp_equip(self, cid):
        if self.players and not self.players[0].dead:
            self.players[0].equip_charm(cid)

    def camp_buy(self, i):
        if not self.camp or i < 0 or i >= len(self.camp['shop']):
            return
        it = self.camp['shop'][i]
        if self.pollen >= it['cost']:
            self.pollen -= it['cost']
            audio.play('buy')
            it['fn'](self)
            it['cost'] = int(it['cost'] * 1.6)
            self.camp['msg'] = it['name']
            self.camp['msg_t'] = 1.4

    def camp_pick_route(self, i):
        if not self.camp:
            return
        r = self.camp['routes'][max(0, min(len(self.camp['routes']) - 1, i))]
        if r['bonus'] == 'cura':
            for pl in self.players:
                pl.health = pl.max_health
        elif r['bonus'] == 'polen':
            self.pollen += 25
        elif r['bonus'] == 'carta':
            for pl in self.alive_players():
                pl.pending_levelups += 1
        self.camp = None
        self.state = 'play'
        self.rounds.request_next(r['theme'])

    def _spawn_prey(self):
        return species.make(random.choice(species.PREY_SPECIES), self._rand_world())

    def _spawn_enemy(self, pos, pool=None):
        key = random.choice(pool or species.ENEMY_SPECIES)
        return species.make(key, pos)

    def nearest_edible(self, pos, rng):
        """Nearest grabbable thing within range -> the tongue auto-aims at it."""
        best, bd = None, rng
        for group in (self.pickups, self.prey):
            for e in group:
                if e.dead:
                    continue
                d = e.pos.distance_to(pos)
                if d < bd:
                    best, bd = e, d
        return best

    def spawn_fruit(self, pos):
        self.pickups.append(Fruit(pos + vfrom_angle(random.uniform(0, 360), 20)))

    def spawn_projectile(self, proj):
        self.projectiles.append(proj)

    def spawn_puddle(self, puddle):
        if len(self.puddles) < 40:
            self.puddles.append(puddle)

    def _update_projectiles(self, dt):
        for pr in self.projectiles:
            if pr.homing and not pr.hostile:      # seek the nearest enemy
                tgt = self.nearest_enemy(pr.pos, 520)
                if tgt:
                    speed = pr.vel.length()
                    desired = safe_norm(tgt.pos - pr.pos)
                    pr.vel = safe_norm(safe_norm(pr.vel).lerp(desired, min(1, 7 * dt))) * speed
            pr.update(dt)
            if pr.dead:
                continue
            if pr.hostile:
                for p in self.players:
                    if p.dead or p.down:
                        continue
                    if p.pos.distance_to(pr.pos) < p.max_r + pr.radius:
                        if pr.effect == 'slow':
                            p.apply_slow(0.5, 1.6)
                        if pr.dmg > 0:
                            p.hurt(self, safe_norm(pr.vel), pr.dmg)
                        self.fx.burst(pr.pos, pr.color, 8, 160)
                        self.fx.spark_burst(pr.pos, palette.lighten(pr.color, 0.3), 6, 200)
                        pr.dead = True
                        break
            else:
                for e in self.enemies:
                    if e.dead:
                        continue
                    if e.pos.distance_to(pr.pos) < e.max_r + pr.radius:
                        e.take_hit(self, safe_norm(pr.vel), pr.dmg)
                        if pr.effect == 'poison':
                            e.apply_poison(3.0, 3.0)
                        pr.dead = True
                        break
                if not pr.dead:                     # player shots also chip nests
                    for n in self.rounds.nests:
                        if not n.dead and n.pos.distance_to(pr.pos) < n.max_r + pr.radius:
                            n.take_hit(self, pr.dmg)
                            pr.dead = True
                            break
        self.projectiles = [p for p in self.projectiles if not p.dead]

    # ---- eating / growth ------------------------------------------------ #
    def eat(self, player, target):
        target.dead = True
        audio.play('eat', 0.7)
        color = getattr(target, 'color', C.COL_BUG)
        self.fx.burst(target.pos, color, 16, 220)
        self.fx.spark_burst(target.pos, color, 10, 300)
        self.fx.ring(target.pos, color)
        kind = getattr(target, 'kind', 'bug')
        if kind == 'bug':
            player.energy = clamp(player.energy + 8, 0, player.max_energy)
            player.food += 1
            self.add_score(5)
            self.fx.popup(target.pos, "+5")
        elif kind == 'fruit':
            player.energy = clamp(player.energy + 22, 0, player.max_energy)
            player.health = min(player.max_health, player.health + 25)
            player.food += 1
            self.add_score(10)
            self.fx.popup(target.pos, "+cura", (120, 240, 120))
        elif kind == 'egg':
            f = AILizard(target.pos, 'friend', 0.9, C.COL_FRIEND)
            f.hp = 3
            self.friends.append(f)
            self.add_score(20)
            self.fx.popup(target.pos, "AMIGO!", C.COL_FRIEND)
        elif kind == 'prey':
            player.energy = clamp(player.energy + 30, 0, player.max_energy)
            player.food += 2
            sv = getattr(target, 'score_value', 25)
            self.add_score(sv)
            player.gain_xp(getattr(target, 'xp_value', 6), self)
            # eating a trait-carrier grants its body part (comer-para-evoluir)
            if getattr(target, 'grants', None):
                player.grant_part(target.grants, self)
            self.fx.popup(target.pos, f"+{sv}")
        if player.food and player.food % 4 == 0:
            self._grow(player)

    def _grow(self, player):
        sp = player.spine
        if len(sp.joints) < 22:
            sp.joints.append(Vector2(sp.joints[-1]))
            sp.radii = build_radii(len(sp.joints), player.max_r)
        self.fx.ring(player.pos, player.color)

    # ---- main step ------------------------------------------------------ #
    def step(self, dt):
        if self.state != 'play':
            self.fx.update(dt)
            return
        # a queued level-up pauses the action for a card pick
        for p in self.players:
            if not p.dead and p.pending_levelups > 0:
                self._enter_levelup(p)
                return
        self.time += dt
        for p in self.players:
            if not p.dead:
                p.update(dt, self)
        for group in (self.enemies, self.prey, self.friends):
            for e in group:
                if not e.dead:
                    e.on_screen = self.cam.visible(e.pos)
                    e.update(dt, self)
        for pk in self.pickups:
            if not pk.dead:
                pk.update(dt, self)
        self._update_projectiles(dt)
        for pud in self.puddles:
            pud.update(dt, self)
        self.puddles = [p for p in self.puddles if not p.dead]

        # keep creatures from stacking into one point
        movers = [p for p in self.players if not p.dead]
        movers += [e for e in self.enemies if not e.dead]
        movers += [e for e in self.prey if not e.dead]
        movers += [f for f in self.friends if not f.dead]
        separate(movers)

        self._collisions()
        self.rounds.update(dt)
        if self.rounds.state == 'cleared':
            if getattr(self.rounds, 'is_final', False):
                self.state = 'victory'              # final boss down -> run won
                audio.play('victory')
                self._bank_run(won=True)
            else:
                self._enter_camp()                  # otherwise: camp (route + shop)
        self.fx.update(dt)
        self.flash = max(0.0, self.flash - dt * 3.2)
        self.world.update(dt)
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0
        self.combo_flash = max(0.0, self.combo_flash - dt * 2)
        self._revive()

        self.enemies = [e for e in self.enemies if not e.dead]
        self.prey = [e for e in self.prey if not e.dead]
        self.friends = [f for f in self.friends if not f.dead]
        self.pickups = [p for p in self.pickups if not p.dead]

        if len(self.pickups) < 50 and random.random() < dt * 4:
            self.pickups.append(Bug(self._rand_world()))
        if len(self.prey) < 8 and random.random() < dt * 0.6:
            self.prey.append(self._spawn_prey())

        if not self.alive_players():
            self.state = 'over'
            self._bank_run()

    def _bank_run(self, won=False):
        """Convert the finished run into permanent DNA (once)."""
        if self.run_banked:
            return
        self.run_banked = True
        self.won = won
        self.dna_gained = progression.finish_run(self.meta, self.score,
                                                 self.rounds.wave, self.kills, won=won)

    def _revive(self):
        for p in self.players:
            if p.down and not p.dead:
                for q in self.alive_players():
                    if not q.down and q.pos.distance_to(p.pos) < 70:
                        p.down = False
                        p.health = p.max_health * 0.5
                        p.hit_flash = 1.0
                        self.fx.burst(p.pos, C.COL_WHITE, 20, 220)
                        self.fx.popup(p.pos, "REVIVIDO!", C.COL_WHITE)

    def _collisions(self):
        for p in self.players:
            if p.dead or p.down:
                continue
            eat_r = p.max_r * 1.4
            head = p.spine.joints[0]
            for group in (self.pickups, self.prey):
                for e in group:
                    if e.dead:
                        continue
                    er = getattr(e, 'max_r', getattr(e, 'r', 6))
                    if head.distance_to(e.pos) < eat_r + er:
                        self.eat(p, e)
            for e in self.enemies:
                if e.dead:
                    continue
                if p.pos.distance_to(e.pos) < p.max_r + e.max_r and p.dashing:
                    grant = getattr(e, 'grants', None)
                    if p.venom:
                        e.apply_poison(2.5, 2.5)
                    e.take_hit(self, safe_norm(e.pos - p.pos), 3)
                    if e.dead:
                        self.punch(0.07, 8)          # dash-kill: crunchy freeze
                        # stealing a body part is now a rare treat, not every kill
                        if grant and random.random() < 0.12:
                            p.grant_part(grant, self)
                        p.dash_cd *= 0.35           # chain: a kill refreshes the dash
                        p.energy = min(p.max_energy, p.energy + 6)
                    self.shake(6)
            # dashing through a nest damages it
            if p.dashing:
                for n in self.rounds.nests:
                    if not n.dead and p.pos.distance_to(n.pos) < p.max_r + n.max_r:
                        n.take_hit(self, 3)
                        self.shake(5)

    # ---- draw ----------------------------------------------------------- #
    def draw(self, surf):
        self._draw_bg(surf)
        self.world.draw_decor(surf, self.cam)
        for pud in self.puddles:                    # acid pools sit on the ground
            if self.cam.visible(pud.pos, 60):
                pud.draw(surf, self.cam)
        self.rounds.draw_world(surf, self.cam)
        for group in (self.pickups, self.prey, self.friends, self.enemies, self.players):
            for e in group:
                if getattr(e, 'dead', False):
                    continue
                pos = e.spine.joints[0] if hasattr(e, 'spine') else e.pos
                if not self.cam.visible(pos):
                    continue
                r = getattr(e, 'max_r', getattr(e, 'r', 6))
                sp = self.cam.w2s(pos + Vector2(0, r * 0.7))
                shadow(surf, sp, r * 1.1 * self.cam.zoom)
        for pk in self.pickups:
            if not pk.dead and self.cam.visible(pk.pos):
                pk.draw(surf, self.cam)
        for group in (self.prey, self.friends, self.enemies):
            for e in group:
                if not e.dead and self.cam.visible(e.pos, 120):
                    e.draw(surf, self.cam)
        for p in self.players:
            if not p.dead:
                p.draw(surf, self.cam)
        for pr in self.projectiles:
            if self.cam.visible(pr.pos, 40):
                pr.draw(surf, self.cam)
        self.world.draw_ambient(surf, self.cam)
        self.fx.draw(surf, self.cam, self.font)
        if self.flash > 0:
            fl = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(150 * min(1.0, self.flash))))
            surf.blit(fl, (0, 0))
        _vignette(surf)
        if self.state == 'play':
            self._draw_offscreen(surf)
        self.rounds.draw_boss_bar(surf, self.font, self.bigfont)
        if self.state not in ('victory', 'over'):
            self.rounds.draw_banner(surf, self.font, self.bigfont)
            self._draw_hud(surf)
        if self.state == 'levelup':
            self._draw_levelup(surf)
        elif self.state == 'camp':
            self._draw_camp(surf)
        elif self.state == 'victory':
            self._draw_victory(surf)
        elif self.state == 'over':
            self._draw_over(surf)

    def _draw_bg(self, surf):
        surf.fill(C.COL_BG)
        self.world.draw_ground(surf, self.cam)
        z = self.cam.zoom
        tl = self.cam.w2s((0, 0)); br = self.cam.w2s((C.WORLD_W, C.WORLD_H))
        pygame.draw.rect(surf, (58, 54, 96), (tl[0], tl[1], br[0] - tl[0], br[1] - tl[1]),
                         max(2, int(6 * z)))

    def _draw_hud(self, surf):
        bw = 216
        for i, p in enumerate(self.players):
            x = 16 if i == 0 else C.WIDTH - bw - 16
            y = 14
            col = p.colorset[0]
            surf.blit(self.font.render(f"P{i+1}", True, col), (x, y))
            lv = self.font.render(f"Nv {p.level}", True, (210, 210, 226))
            surf.blit(lv, (x + bw - lv.get_width(), y))

            # health bar (green -> orange -> red as it drops)
            hy = y + 24
            hr = clamp(p.health / p.max_health, 0, 1)
            hcol = palette.health_color(hr)
            pygame.draw.rect(surf, (48, 48, 68), (x, hy, bw, 16), border_radius=8)
            if hr > 0:
                pygame.draw.rect(surf, hcol, (x, hy, int(bw * hr), 16), border_radius=8)
            pygame.draw.rect(surf, (14, 14, 24), (x, hy, bw, 16), 2, border_radius=8)
            hnum = self.font.render(f"{int(p.health)}/{int(p.max_health)}", True, (16, 16, 24))
            surf.blit(hnum, (x + bw // 2 - hnum.get_width() // 2, hy))

            # energy + xp slim bars
            ey = hy + 22
            pygame.draw.rect(surf, (40, 44, 60), (x, ey, bw, 7), border_radius=4)
            pygame.draw.rect(surf, (110, 210, 240),
                             (x, ey, int(bw * p.energy / p.max_energy), 7), border_radius=4)
            xy = ey + 11
            pygame.draw.rect(surf, (40, 40, 60), (x, xy, bw, 5), border_radius=3)
            pygame.draw.rect(surf, (245, 210, 90),
                             (x, xy, int(bw * clamp(p.xp / p.xp_to_next, 0, 1)), 5), border_radius=3)
            # ability cooldown dials (dash / tongue) -> readable "can I act?" feedback
            dy = xy + 16
            dash_frac = 1.0 - clamp(p.dash_cd / max(0.001, p.dash_cooldown), 0, 1)
            _dial(surf, (x + 14, dy + 14), 13, dash_frac, p.colorset[0],
                  self.font, "DASH", self.time, enabled=p.energy >= C.DASH_COST)
            t_frac = 0.0 if p.tongue_t > 0 else 1.0
            _dial(surf, (x + 92, dy + 14), 13, t_frac, (235, 90, 120),
                  self.font, "LINGUA", self.time, enabled=p.energy >= C.TONGUE_COST)

            if p.down:
                surf.blit(self.font.render(f"CAIDO {p.revive:0.0f}s - toque p/ reviver",
                                           True, C.COL_ENEMY), (x, dy + 34))
            # equipped weapons live in the bottom corners so they never collide
            # with the health/energy bars or the cooldown dials
            wy = C.HEIGHT - 34
            for wi, (wid, lvl) in enumerate(p.weapons.items()):
                w = weapons.WEAPONS[wid]
                cxw = (x + 18 + wi * 46) if i == 0 else (x + bw - 18 - wi * 46)
                c = (cxw, wy)
                icons.draw(surf, wid, c, 14, w.color)
                ln = self.font.render(str(lvl), True, C.COL_WHITE)
                lp = (c[0] + 13, c[1] + 11)
                pygame.draw.circle(surf, C.COL_INK, lp, 9)
                pygame.draw.circle(surf, w.color, lp, 9, 1)
                surf.blit(ln, (lp[0] - ln.get_width() // 2, lp[1] - ln.get_height() // 2))

        s = self.bigfont.render(str(self.score), True, C.COL_HUD)
        surf.blit(s, (C.WIDTH // 2 - s.get_width() // 2, 10))
        w = self.font.render(
            f"Onda {self.wave}   Amigos {len(self.friends)}   Abates {self.kills}",
            True, (180, 180, 200))
        surf.blit(w, (C.WIDTH // 2 - w.get_width() // 2, 48))

        # combo / streak meter (rewards staying aggressive)
        if self.combo >= 2:
            heat = min(1.0, self.combo / 25.0)
            col = palette.mix((255, 214, 90), (255, 86, 86), heat)
            img = self.bigfont.render(f"x{self.combo}  COMBO", True, col)
            sc = 1.0 + self.combo_flash * 0.25
            if sc > 1.01:
                img = pygame.transform.rotozoom(img, 0, sc)
            cx = C.WIDTH // 2
            surf.blit(img, (cx - img.get_width() // 2, 74))
            bw = 150
            f = clamp(self.combo_timer / 3.2, 0, 1)
            pygame.draw.rect(surf, (50, 46, 60), (cx - bw // 2, 74 + img.get_height() + 2, bw, 5),
                             border_radius=3)
            pygame.draw.rect(surf, col, (cx - bw // 2, 74 + img.get_height() + 2, int(bw * f), 5),
                             border_radius=3)

    def _draw_levelup(self, surf):
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 10, 20, 200))
        surf.blit(ov, (0, 0))
        title = self.bigfont.render("EVOLUIR", True, C.COL_WHITE)
        surf.blit(title, (C.WIDTH // 2 - title.get_width() // 2, 96))
        sub = self.font.render("escolha uma mutacao  -  1/2/3, setas+ENTER ou clique",
                               True, (190, 190, 210))
        surf.blit(sub, (C.WIDTH // 2 - sub.get_width() // 2, 140))

        n = len(self.cards)
        cw, ch, gap = 240, 300, 34
        total = n * cw + (n - 1) * gap
        x0 = C.WIDTH // 2 - total // 2
        y = C.HEIGHT // 2 - ch // 2 + 20
        self._card_rects = []
        for i, card in enumerate(self.cards):
            x = x0 + i * (cw + gap)
            rect = pygame.Rect(x, y, cw, ch)
            self._card_rects.append(rect)
            sel = (i == self.card_idx)
            pygame.draw.rect(surf, (30, 32, 52), rect, border_radius=16)
            edge = card.color if sel else (70, 72, 96)
            pygame.draw.rect(surf, edge, rect, 4 if sel else 2, border_radius=16)
            # procedural icon for the weapon/mutation
            icons.draw(surf, getattr(card, 'icon', None), (rect.centerx, y + 70),
                       30, card.color)
            name = self.bigfont.render(card.name, True, C.COL_WHITE)
            if name.get_width() > cw - 20:
                name = self.font.render(card.name, True, C.COL_WHITE)
            surf.blit(name, (rect.centerx - name.get_width() // 2, y + 130))
            # wrap description
            words = card.desc.split()
            line, ly = "", y + 180
            for w in words:
                test = (line + " " + w).strip()
                if self.font.size(test)[0] > cw - 30:
                    im = self.font.render(line, True, (200, 200, 216))
                    surf.blit(im, (rect.centerx - im.get_width() // 2, ly))
                    ly += 24; line = w
                else:
                    line = test
            if line:
                im = self.font.render(line, True, (200, 200, 216))
                surf.blit(im, (rect.centerx - im.get_width() // 2, ly))
            key = self.font.render(f"[{i + 1}]", True, card.color)
            surf.blit(key, (rect.centerx - key.get_width() // 2, y + ch - 34))

    def _draw_offscreen(self, surf):
        """Edge arrows pointing at enemies (and nests) you can't see -> find stragglers."""
        cx, cy = C.WIDTH / 2, C.HEIGHT / 2
        hw, hh = cx - 28, cy - 28
        shown = 0
        targets = [(e, e.color) for e in self.enemies if not e.dead]
        targets += [(n, (190, 130, 95)) for n in self.rounds.nests if not n.dead]
        for obj, col in targets:
            sp = self.cam.w2s(obj.pos)
            if -12 < sp[0] < C.WIDTH + 12 and -12 < sp[1] < C.HEIGHT + 12:
                continue
            d = Vector2(sp[0] - cx, sp[1] - cy)
            if d.length_squared() < 1:
                continue
            scale = min(hw / abs(d.x) if d.x else 1e9, hh / abs(d.y) if d.y else 1e9)
            c = Vector2(cx, cy) + d * scale
            ang = d.as_polar()[1]
            tip = c + vfrom_angle(ang, 12)
            b1 = c + vfrom_angle(ang + 138, 10)
            b2 = c + vfrom_angle(ang - 138, 10)
            palette.glow(surf, (int(c.x), int(c.y)), 16, col, 0.5)
            pygame.draw.polygon(surf, col, [tip, b1, b2])
            pygame.draw.polygon(surf, C.COL_INK, [tip, b1, b2], 1)
            shown += 1
            if shown >= 22:
                break

    def _draw_camp(self, surf):
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((10, 14, 22, 205))
        surf.blit(ov, (0, 0))
        cx = C.WIDTH // 2
        t = self.bigfont.render("ACAMPAMENTO", True, C.COL_WHITE)
        surf.blit(t, (cx - t.get_width() // 2, 40))
        # pollen purse
        pol = self.bigfont.render(str(self.pollen), True, (250, 214, 90))
        pygame.draw.circle(surf, (250, 214, 90), (cx - 70, 96), 12)
        pygame.draw.circle(surf, (200, 160, 40), (cx - 70, 96), 12, 2)
        surf.blit(self.font.render("POLEN", True, (210, 210, 226)), (cx - 54, 88))
        surf.blit(pol, (cx + 12, 78))

        # ---- shop (beetle merchant) ---- #
        surf.blit(self.font.render("LOJA DO BESOURO  (1-5 ou clique)", True, (200, 200, 220)),
                  (cx - 300, 138))
        self._shop_rects = []
        shop = self.camp['shop']
        cw, gap = 176, 14
        total = len(shop) * cw + (len(shop) - 1) * gap
        x0 = cx - total // 2
        y = 164
        for i, it in enumerate(shop):
            x = x0 + i * (cw + gap)
            rect = pygame.Rect(x, y, cw, 132)
            self._shop_rects.append(rect)
            afford = self.pollen >= it['cost']
            focused = (self.camp.get('focus') == 'shop' and self.camp.get('shop_sel') == i)
            pygame.draw.rect(surf, (34, 38, 56) if focused else (28, 32, 46),
                             rect, border_radius=12)
            edge = palette.vibrant(it['hue'], 0.8, 1.0) if afford else (70, 72, 92)
            if focused:
                edge = C.COL_WHITE
                palette.glow(surf, rect.center, 90, palette.vibrant(it['hue'], 0.8, 1.0), 0.3)
            pygame.draw.rect(surf, edge, rect, 4 if focused else (3 if afford else 2),
                             border_radius=12)
            icons.draw(surf, it.get('icon'), (rect.centerx, y + 34), 19,
                       palette.vibrant(it['hue'], 0.8, 1.0))
            nm = self.font.render(ui.fit(self.font, it['name'], cw - 16), True, C.COL_WHITE)
            surf.blit(nm, (rect.centerx - nm.get_width() // 2, y + 62))
            ds = self.font.render(ui.fit(self.font, it['desc'], cw - 16), True, (190, 190, 210))
            surf.blit(ds, (rect.centerx - ds.get_width() // 2, y + 84))
            cc = (250, 214, 90) if afford else (150, 120, 60)
            cost = self.font.render(f"{it['cost']}  polen", True, cc)
            surf.blit(cost, (rect.centerx - cost.get_width() // 2, y + 106))
            key = self.font.render(f"[{i + 1}]", True, edge)
            surf.blit(key, (x + 8, y + 6))
        if self.camp.get('msg'):
            m = self.font.render(f"comprado: {self.camp['msg']}", True, (120, 240, 140))
            surf.blit(m, (x0, y + 116))

        # ---- charms loadout ---- #
        p0 = self.players[0]
        surf.blit(self.font.render("CHARMS  (clique um charm p/ equipar no slot)", True,
                                   (200, 200, 220)), (cx - 300, 306))
        slots = [('head', 'CABECA'), ('back', 'COSTAS'), ('tail', 'CAUDA')]
        sw = 168
        sx0 = cx - (len(slots) * sw + (len(slots) - 1) * 12) // 2
        for si, (slot, nm) in enumerate(slots):
            bx = sx0 + si * (sw + 12)
            box = pygame.Rect(bx, 328, sw, 40)
            cid = p0.charm_slots.get(slot)
            col = charmlib.CHARMS[cid].color if cid else (62, 64, 88)
            pygame.draw.rect(surf, (26, 30, 44), box, border_radius=10)
            pygame.draw.rect(surf, col, box, 2, border_radius=10)
            lab = charmlib.CHARMS[cid].name if cid else '-'
            txt = ui.fit(self.font, f"{nm}: {lab}", box.width - 20)
            surf.blit(self.font.render(txt, True, (218, 218, 232)), (bx + 10, 336))
        self._charm_rects = []
        chx, chy = cx - 300, 376
        for cid in p0.charms_owned:
            ch = charmlib.CHARMS[cid]
            w = self.font.size(ch.name)[0] + 34
            rect = pygame.Rect(chx, chy, w, 30)
            self._charm_rects.append((rect, cid))
            equipped = (p0.charm_slots.get(ch.slot) == cid)
            pygame.draw.rect(surf, (30, 34, 50), rect, border_radius=8)
            pygame.draw.rect(surf, ch.color, rect, 3 if equipped else 1, border_radius=8)
            icons.draw(surf, cid, (chx + 15, chy + 15), 9, ch.color, glow=False)
            surf.blit(self.font.render(ch.name, True, (222, 222, 234)), (chx + 28, chy + 6))
            chx += w + 8
            if chx > cx + 290:
                chx, chy = cx - 300, chy + 34

        # ---- routes (choose the next round) ---- #
        surf.blit(self.font.render("ESCOLHA A ROTA  (setas+ENTER ou clique) -> avanca",
                                   True, (200, 200, 220)), (cx - 300, 470))
        self._route_rects = []
        routes = self.camp['routes']
        rw, rgap = 250, 26
        rtotal = len(routes) * rw + (len(routes) - 1) * rgap
        rx0 = cx - rtotal // 2
        ry = 496
        bonus_txt = {'cura': 'entra com vida cheia', 'polen': '+25 polen', 'carta': 'carta de evolucao'}
        bonus_col = {'cura': (120, 240, 140), 'polen': (250, 214, 90), 'carta': (150, 130, 245)}
        for i, r in enumerate(routes):
            x = rx0 + i * (rw + rgap)
            rect = pygame.Rect(x, ry, rw, 140)
            self._route_rects.append(rect)
            sel = (i == self.camp['sel'])
            focused = sel and self.camp.get('focus', 'route') == 'route'
            pygame.draw.rect(surf, (28, 32, 50) if focused else (24, 28, 42),
                             rect, border_radius=14)
            if focused:
                palette.glow(surf, rect.center, 130, C.COL_ENEMY, 0.28)
            pygame.draw.rect(surf, C.COL_ENEMY if sel else (70, 72, 92),
                             rect, 4 if focused else (3 if sel else 2), border_radius=14)
            lbl = self.bigfont.render(r['label'], True, C.COL_ENEMY)
            if lbl.get_width() > rw - 16:
                lbl = self.font.render(r['label'], True, C.COL_ENEMY)
            surf.blit(lbl, (rect.centerx - lbl.get_width() // 2, ry + 26))
            surf.blit(self.font.render("proxima onda", True, (180, 180, 200)),
                      (rect.centerx - 46, ry + 74))
            bt = self.font.render(bonus_txt[r['bonus']], True, bonus_col[r['bonus']])
            surf.blit(bt, (rect.centerx - bt.get_width() // 2, ry + 104))

    def _draw_victory(self, surf):
        """Run beaten: celebratory summary + the DNA banked (endless now unlocked)."""
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 22, 16, 190))
        surf.blit(ov, (0, 0))
        cx = C.WIDTH // 2
        pulse = 0.5 + 0.5 * math.sin(self.time * 3)
        palette.glow(surf, (cx, 190), 300, (120, 250, 170), 0.28 + 0.16 * pulse)
        t = self.bigfont.render("VITORIA!", True, (150, 255, 190))
        surf.blit(t, (cx - t.get_width() // 2, 158))
        sub = self.font.render(f"voce derrotou o chefe primordial na onda {self.rounds.wave}",
                               True, (206, 236, 220))
        surf.blit(sub, (cx - sub.get_width() // 2, 214))

        rows = [
            ("score", f"{self.score}"),
            ("abates", f"{self.kills}"),
            ("nivel", f"{self.players[0].level}"),
            ("armas", f"{len(self.players[0].weapons)}"),
        ]
        y = 268
        for label, val in rows:
            li = self.font.render(label, True, (168, 200, 184))
            vi = self.bigfont.render(val, True, C.COL_WHITE)
            surf.blit(li, (cx - 150, y + 8))
            surf.blit(vi, (cx + 150 - vi.get_width(), y))
            y += 46

        gained = getattr(self, 'dna_gained', 0)
        d = self.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
        surf.blit(d, (cx - d.get_width() // 2, y + 14))
        bonus = self.font.render(f"(inclui bonus de vitoria +{progression.WIN_BONUS})",
                                 True, (150, 210, 180))
        surf.blit(bonus, (cx - bonus.get_width() // 2, y + 58))
        unl = self.font.render("MODO INFINITO DESBLOQUEADO no menu", True, (245, 220, 120))
        surf.blit(unl, (cx - unl.get_width() // 2, y + 88))
        h = self.font.render("Enter: jogar de novo    Esc: menu", True, (200, 214, 206))
        surf.blit(h, (cx - h.get_width() // 2, y + 124))

    def _draw_over(self, surf):
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((10, 8, 20, 180))
        surf.blit(ov, (0, 0))
        t = self.bigfont.render("FIM DE JOGO", True, C.COL_ENEMY)
        surf.blit(t, (C.WIDTH // 2 - t.get_width() // 2, C.HEIGHT // 2 - 80))
        s = self.bigfont.render(f"Score {self.score}", True, C.COL_HUD)
        surf.blit(s, (C.WIDTH // 2 - s.get_width() // 2, C.HEIGHT // 2 - 24))
        # run summary + DNA banked
        cy = C.HEIGHT // 2 + 22
        line = self.font.render(
            f"onda {self.rounds.wave}   abates {self.kills}   nivel {self.players[0].level}",
            True, (198, 200, 220))
        surf.blit(line, (C.WIDTH // 2 - line.get_width() // 2, cy))
        gained = getattr(self, 'dna_gained', 0)
        d = self.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
        surf.blit(d, (C.WIDTH // 2 - d.get_width() // 2, cy + 30))
        tot = self.font.render(f"DNA total: {self.meta['dna']}   (gaste no menu > EVOLUCAO)",
                               True, (170, 210, 185))
        surf.blit(tot, (C.WIDTH // 2 - tot.get_width() // 2, cy + 76))
        h = self.font.render("Enter: jogar de novo    Esc: menu", True, (200, 200, 220))
        surf.blit(h, (C.WIDTH // 2 - h.get_width() // 2, cy + 110))
