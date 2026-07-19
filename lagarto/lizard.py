"""Lizard creatures: a shared procedural body, the Player, and the AI lizards.

``Lizard`` wires a Spine to four Legs (diagonal gait) plus squash & stretch and
all the drawing. ``Player`` adds input/dash/tongue/energy. ``AILizard`` adds the
prey / enemy / friend behaviours. Everything reuses the same body so any number
of them can be on screen animating procedurally at once.
"""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import palette
from . import parts
from . import weapons
from .genome import basic_lizard
from .mathutil import clamp, lerp, approach, vfrom_angle, safe_norm, angle_of
from .spine import Spine, build_radii
from .leg import Leg
from .projectile import spit as game_spit

TAU = C.TAU


class Lizard:
    def __init__(self, pos, kind, scale=1.0, color=None, genome=None):
        self.kind = kind
        self.genome = genome or basic_lizard(scale)
        g = self.genome
        self.scale = g.size
        self.dead = False
        self.pos = Vector2(pos)          # head position (leads the body)
        self.vel = Vector2()
        self.facing = Vector2(1, 0)
        self.color = color or g.color()
        self.squash = 1.0
        self.wobble = random.uniform(0, TAU)
        self.hit_flash = 0.0
        self.attack_cd = 0.0
        self.on_screen = True
        self.slow_t = 0.0
        self.slow_mul = 1.0

        if g.radial:                      # spider: compact body, few joints
            n = 3
            maxr = 15 * g.size * g.girth
            link = maxr * 0.7
        else:
            n = max(6, int(11 * g.size * g.length))
            maxr = 17 * g.size * g.girth
            link = maxr * 1.05
        self.max_r = maxr
        self.spine = Spine(pos, n, link, build_radii(n, maxr), bend=26)
        self.legs = self._build_legs(g, n, maxr)
        for leg in self.legs:
            leg.init_foot(self.spine)

        self.max_speed = 165 * (0.85 + 0.4 / g.size) * g.speed
        self.accel = 900.0
        self.target_dir = Vector2()

    def _build_legs(self, g, n, maxr):
        if g.leg_count <= 0:
            return []
        if g.radial:
            return self._build_radial_legs(g, n, maxr)
        seg = maxr * 1.35 * g.leg_len
        so = maxr * 1.7
        step_len = maxr * 1.5
        pairs = max(1, g.leg_count // 2)
        if pairs == 1:
            fracs = [0.35]
        elif pairs == 2:
            fracs = [0.22, 0.55]
        else:
            fracs = [0.18 + i * (0.52 / (pairs - 1)) for i in range(pairs)]
        legs = []
        for pi, frac in enumerate(fracs):
            idx = max(1, min(n - 2, int(n * frac)))
            fwd_off = maxr * lerp(0.3, -0.2, pi / max(1, pairs - 1))
            legs.append(Leg(idx, -1, so, fwd_off, seg, step_len, 0.14, maxr * 0.9))
            legs.append(Leg(idx, +1, so, fwd_off, seg, step_len, 0.14, maxr * 0.9))
        # diagonal gait: left of a pair steps with the right of the next pair
        for i in range(pairs):
            j = (i + 1) % pairs
            legs[2 * i].partner = legs[2 * j + 1]
            legs[2 * i + 1].partner = legs[2 * j]
        return legs

    def _build_radial_legs(self, g, n, maxr):
        """Spider-style legs: fixed angles around the body, IK reach outward."""
        count = max(4, g.leg_count)
        half = count // 2
        reach = maxr * 2.4 * g.leg_len
        seg = reach * 0.62
        step_len = maxr * 1.15
        idx = max(1, n // 2)
        legs = []
        for k in range(half):
            a = 38 + k * (118 / (half - 1)) if half > 1 else 90    # 38..156 deg
            legs.append(Leg(idx, +1, reach, 0, seg, step_len, 0.12, maxr * 0.7,
                            rest_angle=a, reach=reach))
            legs.append(Leg(idx, -1, reach, 0, seg, step_len, 0.12, maxr * 0.7,
                            rest_angle=-a, reach=reach))
        # opposite legs alternate so it never stands on all/none at once
        h = len(legs) // 2
        for i, leg in enumerate(legs):
            leg.partner = legs[(i + h) % len(legs)]
        return legs

    # ---- status --------------------------------------------------------- #
    def apply_slow(self, mul, dur):
        self.slow_mul = min(self.slow_mul, mul) if self.slow_t > 0 else mul
        self.slow_t = max(self.slow_t, dur)

    def _speed_scale(self):
        return self.slow_mul if self.slow_t > 0 else 1.0

    # ---- movement ------------------------------------------------------- #
    def steer(self, desired_dir, dt, speed_mul=1.0):
        speed_mul *= self._speed_scale()
        if desired_dir.length_squared() > 1e-4:
            self.target_dir = safe_norm(desired_dir)
            target_v = self.target_dir * self.max_speed * speed_mul
        else:
            target_v = Vector2()
        self.vel += (target_v - self.vel) * clamp(self.accel * dt / self.max_speed, 0, 1)

    def integrate(self, dt, on_plant=None):
        self.pos += self.vel * dt
        m = self.max_r
        for ax, lim in ((0, C.WORLD_W), (1, C.WORLD_H)):
            if self.pos[ax] < m:
                self.pos[ax] = m
                self.vel[ax] = abs(self.vel[ax]) * 0.5
            elif self.pos[ax] > lim - m:
                self.pos[ax] = lim - m
                self.vel[ax] = -abs(self.vel[ax]) * 0.5

        self.spine.resolve(self.pos)
        if self.vel.length_squared() > 1:
            self.facing = safe_norm(self.vel)
        for leg in self.legs:
            leg.update(self.spine, self.vel, dt, on_plant)

        spd = self.vel.length()
        self.squash = approach(self.squash,
                               1.0 + clamp(spd / self.max_speed, 0, 1.6) * 0.16, 9, dt)
        self.wobble += dt * 6
        self.hit_flash = max(0.0, self.hit_flash - dt * 3)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.slow_t = max(0.0, self.slow_t - dt)

    # ---- drawing -------------------------------------------------------- #
    def draw(self, surf, cam):
        squish = 1.0 / math.sqrt(self.squash)
        # soft glow behind the body so it pops off the ground (Animal Well vibe).
        # Bounded to the player (+ bosses via glow_body) so a horde stays cheap;
        # everyone else pops via rim light + vivid colour instead.
        if getattr(self, 'glow_body', self.kind == 'player'):
            mid = self.spine.joints[len(self.spine.joints) // 3]
            palette.glow(surf, cam.w2s(mid), self.max_r * 2.6 * cam.zoom, self.color, 0.34)

        leg_col = tuple(int(x * 0.7) for x in self.color)
        for leg in self.legs:
            root = self.spine.joints[leg.idx]
            knee, foot = leg.solve(root)
            r = cam.w2s(root); k = cam.w2s(knee); f = cam.w2s(foot)
            w = max(2, int(self.max_r * 0.42 * cam.zoom))
            pygame.draw.line(surf, leg_col, r, k, w)
            pygame.draw.line(surf, leg_col, k, f, w)
            pygame.draw.circle(surf, leg_col, f, max(2, int(self.max_r * 0.28 * cam.zoom)))

        if self.genome.radial:
            self._draw_spider(surf, cam)
            return

        poly = [cam.w2s(p) for p in self.spine.body_polygon(squish)]
        if len(poly) >= 3:
            base = self.color
            if self.hit_flash > 0:
                base = tuple(int(lerp(base[i], 255, self.hit_flash)) for i in range(3))
            pygame.draw.polygon(surf, base, poly)
            # rim light: a bright edge just inside the dark ink outline
            pygame.draw.polygon(surf, palette.lighten(base, 0.55), poly, max(1, int(3 * cam.zoom)))
            pygame.draw.polygon(surf, C.COL_INK, poly, max(1, int(2 * cam.zoom)))

        spot = tuple(int(x * 0.8) for x in self.color)
        js, rad = self.spine.joints, self.spine.radii
        for i in range(2, len(js) - 2, 2):
            pygame.draw.circle(surf, spot, cam.w2s(js[i]),
                               max(1, int(rad[i] * 0.32 * cam.zoom)))
        parts.draw_all(surf, cam, self)
        self._draw_head(surf, cam)

    def _draw_spider(self, surf, cam):
        js = self.spine.joints
        base = self.color
        if self.hit_flash > 0:
            base = tuple(int(lerp(base[i], 255, self.hit_flash)) for i in range(3))
        ink_w = max(1, int(2 * cam.zoom))
        head = js[0]
        abdomen = js[-1]
        d = self.spine.head_dir()
        hc = cam.w2s(head)
        ac = cam.w2s(abdomen)
        ar = max(3, int(self.max_r * 1.5 * cam.zoom))
        hr = max(2, int(self.max_r * 0.85 * cam.zoom))
        # abdomen
        pygame.draw.circle(surf, base, ac, ar)
        pygame.draw.circle(surf, palette.lighten(base, 0.5), ac, ar, ink_w)
        pygame.draw.circle(surf, C.COL_INK, ac, ar, ink_w)
        # cephalothorax
        pygame.draw.circle(surf, palette.darken(base, 0.1), hc, hr)
        pygame.draw.circle(surf, C.COL_INK, hc, hr, ink_w)
        # cluster of eyes on the head
        perp = Vector2(-d.y, d.x)
        r = self.max_r
        for ex, ey in ((0.25, -0.3), (0.25, 0.3), (0.45, -0.12), (0.45, 0.12)):
            ep = head + d * (r * ex) + perp * (r * ey)
            pygame.draw.circle(surf, C.COL_WHITE, cam.w2s(ep), max(1, int(r * 0.16 * cam.zoom)))

    def _look_dir(self):
        if self.kind == 'player':
            return self.facing
        return safe_norm(self.vel) if self.vel.length_squared() > 1 else self.spine.head_dir()

    def _draw_head(self, surf, cam):
        head = self.spine.joints[0]
        d = self.spine.head_dir()
        perp = Vector2(-d.y, d.x)
        r = self.max_r
        look = self._look_dir()
        eye_glow = getattr(self, 'glow_body', self.kind == 'player')
        for s in (-1, 1):
            ep = head + d * (r * 0.15) + perp * (s * r * 0.62)
            sp = cam.w2s(ep)
            if eye_glow:
                palette.glow(surf, sp, r * 0.9 * cam.zoom, (200, 200, 210), 0.5)
            pygame.draw.circle(surf, C.COL_WHITE, sp, max(2, int(r * 0.42 * cam.zoom)))
            pygame.draw.circle(surf, C.COL_INK, cam.w2s(ep + look * (r * 0.18)),
                               max(1, int(r * 0.2 * cam.zoom)))


# --------------------------------------------------------------------------- #
#  Player                                                                      #
# --------------------------------------------------------------------------- #

class Player(Lizard):
    def __init__(self, pos, controller, colorset, index):
        super().__init__(pos, 'player', scale=1.25, color=colorset[0])
        self.colorset = colorset
        self.ctrl = controller
        self.index = index
        self.energy = 100.0
        self.max_energy = 100.0
        self.max_health = 100.0
        self.health = 100.0
        self.food = 0
        self.dash_time = 0.0
        self.dash_cd = 0.0
        self.tongue_t = 0.0
        self.tongue_target = None
        self.aim = Vector2(1, 0)
        self.down = False
        self.revive = 0.0
        self.xp = 0.0
        self.level = 1
        self.xp_to_next = 20.0        # level-ups pause the action: keep them meaningful
        self.pending_levelups = 0
        # evolution state
        self.mutations = []
        self.synergies = set()
        self.thorns = 0
        self.venom = False
        self.wings = False
        self.regen = 0.0
        self._regen_acc = 0.0
        self.xp_mult = 1.0
        self.speed_mult = 1.0
        self.dash_cooldown = 0.45
        self.tongue_range = 230
        # global weapon stats (Vampire-Survivors style; boosted by passives)
        self.might = 1.0             # damage multiplier
        self.area_mult = 1.0         # aura/range size
        self.cooldown_mult = 1.0     # <1 = faster
        self.amount = 0              # +projectiles / +orbitals
        self.weapons = {}            # weapon id -> level
        self.weapon_state = {}       # weapon id -> per-weapon state
        self.gain_weapon('cuspe')    # everyone starts with the acid spit
        self.ability = None          # active ability id (from charms/evolution)
        self.ability_cd = 0.0
        # charms (Hollow-Knight-style adaptations in 3 body slots)
        self.armor = 0.0             # fraction of damage blocked (carapaca)
        self.charm_slots = {'head': None, 'back': None, 'tail': None}
        self.charms_owned = []

    @property
    def dashing(self):
        return self.dash_time > 0

    def gain_charm(self, cid, game=None):
        from . import charms
        ch = charms.CHARMS.get(cid)
        if not ch or cid in self.charms_owned:
            return False
        self.charms_owned.append(cid)
        if self.charm_slots.get(ch.slot) is None:      # auto-equip an empty slot
            self.equip_charm(cid, game)
        return True

    def equip_charm(self, cid, game=None):
        from . import charms
        ch = charms.CHARMS.get(cid)
        if not ch:
            return
        slot = ch.slot
        old = self.charm_slots.get(slot)
        if old == cid:
            return
        if old:
            charms.CHARMS[old].on_unequip(self)
        self.charm_slots[slot] = cid
        ch.on_equip(self)
        if game:
            game.fx.burst(self.pos, ch.color, 16, 200)
            game.fx.spark_burst(self.pos, palette.lighten(ch.color, 0.4), 10, 260)
            game.fx.ring(self.pos, ch.color)

    def gain_weapon(self, wid):
        if wid not in self.weapons and len(self.weapons) < 6:
            self.weapons[wid] = 1
            self.weapon_state[wid] = weapons.WEAPONS[wid].new_state()
            return True
        return False

    def level_weapon(self, wid):
        w = weapons.WEAPONS.get(wid)
        if wid in self.weapons and w and self.weapons[wid] < w.maxlevel():
            self.weapons[wid] += 1
            return True
        return False

    def apply_mutation(self, mutation, game):
        mutation.apply(self, game)
        self.mutations.append(mutation.id)
        game.fx.burst(self.pos, mutation.color, 24, 260)
        game.fx.spark_burst(self.pos, palette.lighten(mutation.color, 0.4), 16, 340)
        game.fx.ring(self.pos, mutation.color)
        from .evolution import check_synergies
        for name in check_synergies(self, game):
            game.fx.popup(self.pos + Vector2(0, -40), name, C.COL_WHITE)
            game.fx.ring(self.pos, self.colorset[0])
            game.shake(5)

    def gain_xp(self, amount, game):
        if self.down or self.dead:
            return
        self.xp += amount * self.xp_mult
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next *= 1.42
            self.pending_levelups += 1     # game.step turns these into card picks

    def grant_part(self, part, game):
        g = self.genome
        if part == 'spikes':
            g.spikes += 1
        elif part == 'horns':
            g.horns = min(3, g.horns + 1)
        elif part == 'plates':
            g.plates += 1
        elif part == 'sting':
            g.tail = 'sting'
        elif part == 'legs':
            if g.leg_count >= 10:            # cap so legs don't pile up absurdly
                return
            g.leg_count += 2
            self.max_speed *= 1.05           # more legs = better locomotion
            self.speed_mult *= 1.05
            self.legs = self._build_legs(g, len(self.spine.joints), self.max_r)
            for leg in self.legs:
                leg.init_foot(self.spine)
        game.fx.popup(self.pos, "EVOLUIU!", C.COL_WHITE)
        game.fx.ring(self.pos, self.color)
        game.fx.ring(self.pos, palette.lighten(self.color, 0.4))
        game.fx.burst(self.pos, palette.lighten(self.color, 0.3), 20, 240)
        game.fx.spark_burst(self.pos, C.COL_WHITE, 14, 320)
        game.shake(4)

    def hurt(self, game, src_dir, dmg=10):
        if self.dashing or self.hit_flash > 0.45 or self.down:
            return
        dmg *= (1.0 - self.armor)                       # carapaca charm blocks a %
        self.health -= dmg
        self.hit_flash = 1.0
        self.vel = src_dir * (140 + dmg * 6)
        game.fx.burst(self.pos, self.color, 10 + int(dmg / 2), 200)
        game.fx.spark_burst(self.pos, (255, 240, 200), 8 + int(dmg / 3), 320)
        game.shake(4 + dmg * 0.4)
        if self.health <= 0:
            self.health = 0
            self.down = True
            self.revive = 6.0
            game.fx.burst(self.pos, C.COL_WHITE, 26, 260)
            game.fx.ring(self.pos, self.color)

    def update(self, dt, game):
        if self.down:
            self.revive -= dt
            self.steer(Vector2(), dt)
            self.integrate(dt)
            self.squash = approach(self.squash, 0.7, 6, dt)
            if self.revive <= 0:
                self.dead = True
            return

        c = self.ctrl
        self.aim = safe_norm(c.aim_world - self.pos)

        speed_mul = 1.0
        if self.dash_time > 0:
            self.dash_time -= dt
            speed_mul = 3.4 if self.wings else 2.9
            game.fx.trail(self.pos, self.color)
        self.dash_cd = max(0.0, self.dash_cd - dt)

        if c.dash_edge and self.dash_cd <= 0 and self.energy > 14:
            move = c.move if c.move.length_squared() > 0.1 else self.facing
            self.vel = safe_norm(move) * self.max_speed * (3.5 if self.wings else 3.0)
            self.dash_time = 0.2 if self.wings else 0.16
            self.dash_cd = self.dash_cooldown * (0.8 if self.wings else 1.0)
            self.energy -= 14 if self.wings else 18
            game.fx.burst(self.pos, self.color, 14, 200)
            game.fx.spark_burst(self.pos, palette.lighten(self.color, 0.3), 12, 340)
            game.shake(5)

        self.steer(c.move, dt, speed_mul)
        self.integrate(dt, on_plant=game.fx.dust)

        if c.tongue_edge and self.tongue_t == 0 and self.energy >= 8:
            self.tongue_t = 0.001
            self.energy -= 8                                   # tongue costs energy
            # auto-aim at the nearest edible OR enemy, whichever is closer
            ed = game.nearest_edible(self.pos, self.tongue_range)
            en = game.nearest_enemy(self.pos, self.tongue_range)
            if ed and en:
                self.tongue_target = ed if self.pos.distance_to(ed.pos) <= \
                    self.pos.distance_to(en.pos) else en
            else:
                self.tongue_target = ed or en
            if self.tongue_target:
                self.aim = safe_norm(self.tongue_target.pos - self.pos)
        if self.tongue_t > 0:
            self.tongue_t += dt / 0.22
            if self.tongue_t >= 1:
                self.tongue_t = 0.0
                t = self.tongue_target
                if t and not t.dead:
                    if getattr(t, 'kind', None) == 'enemy':    # whip: hurt + yank in
                        t.take_hit(game, safe_norm(t.pos - self.pos), 2)
                        t.vel += safe_norm(self.pos - t.pos) * 200
                        game.fx.spark_burst(t.pos, (255, 240, 200), 7, 240)
                    else:
                        game.eat(self, t)
                self.tongue_target = None

        # --- auto-weapons (Vampire-Survivors style: they act on their own) ---
        self.ability_cd = max(0.0, self.ability_cd - dt)
        for wid, lvl in self.weapons.items():
            weapons.WEAPONS[wid].tick(self, game, dt, self.weapon_state[wid], lvl)

        self.energy = clamp(self.energy + dt * 6, 0, self.max_energy)
        if self.regen > 0 and self.health < self.max_health:
            self.health = min(self.max_health, self.health + self.regen * dt)

    def tongue_tip(self):
        if self.tongue_t <= 0:
            return None
        reach = math.sin(self.tongue_t * math.pi)
        if self.tongue_target and not self.tongue_target.dead:
            aim = self.tongue_target.pos
        else:
            aim = self.pos + self.aim * 210
        mouth = self.spine.joints[0] + self.spine.head_dir() * self.max_r
        return mouth.lerp(aim, reach), mouth

    def draw(self, surf, cam):
        for wid, lvl in self.weapons.items():        # auras behind the body
            w = weapons.WEAPONS[wid]
            if w.layer == 'under':
                w.draw(surf, cam, self, self.weapon_state[wid], lvl)
        tip = self.tongue_tip()
        if tip:
            t, mouth = tip
            pygame.draw.line(surf, (230, 60, 90), cam.w2s(mouth), cam.w2s(t),
                             max(2, int(3 * cam.zoom)))
            pygame.draw.circle(surf, (255, 90, 120), cam.w2s(t), max(2, int(4 * cam.zoom)))
        super().draw(surf, cam)
        for wid, lvl in self.weapons.items():        # orbitals in front
            w = weapons.WEAPONS[wid]
            if w.layer == 'over':
                w.draw(surf, cam, self, self.weapon_state[wid], lvl)


# --------------------------------------------------------------------------- #
#  AI lizards: prey / enemy / friend                                          #
# --------------------------------------------------------------------------- #

class AILizard(Lizard):
    def __init__(self, pos, kind, scale=1.0, color=None, genome=None):
        super().__init__(pos, kind, scale, color, genome)
        self.wander = vfrom_angle(random.uniform(0, 360))
        self.wander_t = 0.0
        self.hp = int(self.genome.hp)
        self.species = None
        self.xp_value = 3
        self.score_value = 15
        self.grants = None
        self.poison_t = 0.0
        self.poison_dps = 0.0
        self._pacc = 0.0
        self._dmg_acc = 0.0          # fractional damage from auras/orbitals
        self.lunge_t = 0.0            # >0 telegraphing, <0 mid-lunge
        self.shoot_cd = 0.0
        self.shoot_charge = 0.0      # >0 = winding up a shot (telegraph)

    def apply_poison(self, dps, dur):
        self.poison_dps = max(self.poison_dps, dps)
        self.poison_t = max(self.poison_t, dur)

    def damage(self, game, amount, direction=None):
        """Fractional damage (for auras/orbitals/puddles that tick every frame)."""
        self._dmg_acc += amount
        whole = int(self._dmg_acc)
        if whole > 0:
            self._dmg_acc -= whole
            self.hit_flash = max(self.hit_flash, 0.4)
            if direction is not None:
                self.vel += direction * 120
            self.hp -= whole
            if self.hp <= 0:
                self.die(game)
                return True
        return False

    def _tick_status(self, dt, game):
        if self.poison_t > 0:
            self.poison_t -= dt
            self._pacc += self.poison_dps * dt
            if random.random() < dt * 8:
                game.fx.burst(self.pos, (120, 240, 90), 1, 60)
            if self._pacc >= 1.0:
                d = int(self._pacc)
                self._pacc -= d
                self.hp -= d
                if self.hp <= 0:
                    self.die(game)
                    return True
        return False

    def wander_dir(self, dt):
        self.wander_t -= dt
        if self.wander_t <= 0:
            self.wander_t = random.uniform(0.6, 1.6)
            self.wander = vfrom_angle(random.uniform(0, 360))
        return self.wander

    def update(self, dt, game):
        if self._tick_status(dt, game):
            return
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        d = Vector2()
        speed = 1.0
        if self.kind == 'prey':
            # flee the nearest threat: a player or a predator (living ecosystem)
            threat = game.nearest_threat(self.pos, 230)
            if threat:
                d = safe_norm(self.pos - threat.pos); speed = 1.2
            elif self.genome.behavior == 'hop':
                d = self._hop(dt); speed = 1.0
            else:
                d = self.wander_dir(dt); speed = 0.5
        elif self.kind == 'enemy':
            target = game.nearest_player(self.pos)
            beh = self.genome.behavior
            if target and target.pos.distance_to(self.pos) < 700:
                if beh == 'ranged':
                    d, speed = self._ai_ranged(dt, game, target)
                elif beh == 'lunge':
                    d, speed = self._ai_lunge(dt, game, target)
                else:
                    d, speed = self._ai_melee(dt, game, target)
            elif 'prey' in self.genome.diet:
                prey = game.nearest_prey(self.pos, 480)
                if prey:
                    d = safe_norm(prey.pos - self.pos); speed = 0.9
                    if prey.pos.distance_to(self.pos) < (self.max_r + prey.max_r) and self.attack_cd <= 0:
                        self.attack_cd = 0.7
                        prey.take_hit(game, safe_norm(prey.pos - self.pos), 3)
                        self.hp = min(int(self.genome.hp) + 2, self.hp + 1)
                else:
                    d = self.wander_dir(dt); speed = 0.45
            else:
                d = self.wander_dir(dt); speed = 0.45
        elif self.kind == 'friend':
            leader = game.nearest_player(self.pos)
            foe = game.nearest_enemy(self.pos, 360)
            if foe:
                d = safe_norm(foe.pos - self.pos); speed = 1.2
                if foe.pos.distance_to(self.pos) < (self.max_r + foe.max_r) and self.attack_cd <= 0:
                    foe.take_hit(game, safe_norm(foe.pos - self.pos), 1)
                    self.attack_cd = 0.6
                    game.fx.burst(foe.pos, C.COL_FRIEND, 8, 160)
            elif leader:
                off = leader.pos.distance_to(self.pos)
                if off > 120:
                    d = safe_norm(leader.pos - self.pos)
                    speed = clamp(off / 200, 0.4, 1.3)
                else:
                    d = self.wander_dir(dt) * 0.3
        self.steer(d, dt, speed)
        self.integrate(dt, on_plant=game.fx.dust if self.on_screen else None)

    def _ai_melee(self, dt, game, target):
        dist = target.pos.distance_to(self.pos)
        if dist < (self.max_r + target.max_r) * 1.1 and self.attack_cd <= 0:
            self._contact(game, target)
        return safe_norm(target.pos - self.pos), 1.0

    def _ai_ranged(self, dt, game, target):
        dist = target.pos.distance_to(self.pos)
        to = safe_norm(target.pos - self.pos)
        mouth = self.spine.joints[0] + self.spine.head_dir() * self.max_r

        if self.shoot_charge > 0:                 # telegraph -> gives time to dodge
            self.shoot_charge -= dt
            if random.random() < dt * 26:
                game.fx.burst(mouth, palette.lighten(self.color, 0.3), 1, 50)
            if self.shoot_charge <= 0:
                game.spawn_projectile(game_spit(mouth, target.pos, self.color))
                game.fx.spark_burst(mouth, self.color, 7, 200)
            return to * 0.05, 0.0                 # brace while charging

        if dist < 260:
            d = -to                               # back away
        elif dist > 380:
            d = to                                # close in
        else:
            d = Vector2(-to.y, to.x) * (1 if int(self.wobble) % 2 else -1)  # strafe
        if self.shoot_cd <= 0 and dist < 440:
            self.shoot_cd = 2.3
            self.shoot_charge = 0.45              # start the wind-up
        return d, 0.75

    def _ai_lunge(self, dt, game, target):
        dist = target.pos.distance_to(self.pos)
        to = safe_norm(target.pos - self.pos)
        if self.lunge_t > 0:              # telegraphing (wind-up)
            self.lunge_t -= dt
            if self.lunge_t <= 0:
                self.vel = to * self.max_speed * 3.2      # pounce!
                self.lunge_t = -0.25
                game.fx.spark_burst(self.pos, self.color, 8, 260)
            return Vector2(), 0.0
        if self.lunge_t < 0:             # mid-pounce, coast
            self.lunge_t += dt
            if dist < (self.max_r + target.max_r) * 1.1 and self.attack_cd <= 0:
                self._contact(game, target)
            return Vector2(), 0.0
        if dist < 220 and self.attack_cd <= 0:
            self.lunge_t = 0.45          # start wind-up
            self.attack_cd = 1.8
            return Vector2(), 0.0
        return to, 0.95

    def _hop(self, dt):
        # frogs: periodic forward hops instead of a smooth glide
        self.wander_t -= dt
        if self.wander_t <= 0:
            self.wander_t = random.uniform(0.7, 1.3)
            self.wander = vfrom_angle(random.uniform(0, 360))
            self.vel += self.wander * self.max_speed * 1.4
        return Vector2()

    def _contact(self, game, target):
        self.attack_cd = 0.8
        if target.dashing:
            self.take_hit(game, safe_norm(self.pos - target.pos), 3)
        else:
            dmg = int(8 + self.max_r * 0.4)      # bigger predators hit harder
            target.hurt(game, safe_norm(target.pos - self.pos), dmg)
            if self.genome.tail == 'sting':      # scorpion sting also slows
                target.apply_slow(0.5, 1.4)
            thorns = getattr(target, 'thorns', 0)
            if thorns:                            # attacker gets pricked
                self.take_hit(game, safe_norm(self.pos - target.pos), thorns)

    def take_hit(self, game, direction, dmg):
        self.hit_flash = 1.0
        self.vel = direction * 200
        game.fx.burst(self.pos, self.color, 10, 180)
        game.fx.spark_burst(self.pos, (255, 240, 200), 9, 300)
        self.hp -= dmg
        if self.hp <= 0:
            self.die(game)

    def die(self, game):
        self.dead = True
        game.fx.burst(self.pos, self.color, 22, 240)
        game.fx.spark_burst(self.pos, palette.lighten(self.color, 0.4), 18, 380)
        game.fx.ring(self.pos, self.color)
        if self.kind == 'enemy':
            game.add_combo()
            game.add_score(self.score_value)
            game.add_pollen(max(1, self.score_value // 12))
            game.kills += 1
            game.give_xp(self.xp_value)
            if random.random() < 0.4:
                game.spawn_fruit(self.pos)
