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

from .core import config as C
from . import audio
from .core import fonts
from .core import palette
from . import parts
from . import ui
from . import weapons
from .genome import basic_lizard
from .core.mathutil import clamp, lerp, approach, vfrom_angle, safe_norm, angle_of, decay, pulse, random_dir
from .spine import Spine, build_radii
from .leg import Leg
from .projectile import spit as game_spit
from .anim import Vector2Spring

TAIL_SPRING_JOINTS = 4          # how many tail joints get cosmetic overshoot
TAIL_SPRING_MAX_LAG = 0.45      # cap on overshoot, as a fraction of max_r -- a
                                # spring's steady-state lag scales with target
                                # speed with no ceiling, so an uncapped spring
                                # turns a dash (or any large jump, e.g. a menu
                                # backdrop lizard being repositioned) into a
                                # tail stretched way past the body's own length
TAIL_SPRING_STIFFNESS = 10.0
# Personality via animation (plans/01 #11): a boss's mood (already computed by
# BossAI for pattern/speed choice) also tightens its own secondary-motion
# springs -- calm reads loose/idle, enraged/cornered reads tense/twitchy.
# Nothing new to draw, the same springs just react faster.
BOSS_MOOD_SPRING_MULT = {'calm': 1.0, 'agitated': 1.25, 'enraged': 1.6,
                         'frustrated': 1.15, 'cornered': 1.4}

TAU = C.TAU


def contact_damage(max_r, wave):
    """Melee damage an enemy of this size deals on wave ``wave``.

    Size still matters (a tank should hurt more than a runner), but the wave term
    is a *staircase*, not a ramp: the player can feel "runners started hurting"
    at a step boundary, whereas a smooth curve just reads as the game drifting.
    """
    step = max(0, int(wave)) // C.ENEMY_DMG_STEP
    return int(C.ENEMY_DMG_BASE + max_r * C.ENEMY_DMG_SIZE
               + step * C.ENEMY_DMG_PER_STEP)


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
        self.leg_pull = 1.0      # anticipation hook, twin of squat_bias: < 1 pulls
                                 # legs in toward the body (a real crouch/coil),
                                 # > 1 reaches them out (the launch); same
                                 # decays-on-its-own contract, see integrate()
        self.squat_bias = 1.0    # anticipation hook (plans/01 #8): a caller sets
                                 # this < 1 every frame of its own wind-up window
                                 # (hop/lunge/ranged/dash); integrate() multiplies
                                 # it into the squash TARGET and decays it back to
                                 # 1.0 on its own once the caller stops touching it
                                 # -- composes with the speed-based squash instead
                                 # of fighting it frame-to-frame
        self.wobble = random.uniform(0, TAU)
        self.hit_flash = 0.0
        self.attack_cd = 0.0
        self.on_screen = True
        self.slow_t = 0.0
        self.slow_mul = 1.0

        self.max_speed = 0.0
        self._speed_base = 0.0
        self.rebuild_body(keep_pose=False)
        self.accel = 900.0
        self.target_dir = Vector2()

    def rebuild_body(self, keep_pose=True):
        """Recompute everything derived from the genome -- and nothing else.

        Calling ``__init__`` again also wipes hp, weapons, level, aggro and the
        rest of the run state, which is why ``champions.py`` had to snapshot a
        list of fields around it. Three features need the *body* to follow a
        changed genome while the run continues: the LARVA growing, a champion
        being promoted, and (phase 5) a boss shedding armour between phases. They
        all go through here.

        ``max_speed`` accumulates multipliers from meta-progression and cards, so
        recomputing it from scratch would silently delete them; the ratio against
        ``_speed_base`` is carried across instead.
        """
        g = self.genome
        self.scale = g.size
        plan = getattr(g, 'plan', 'normal')
        if g.radial:                      # spider: compact body, few joints
            n = 3
            maxr = 15 * g.size * g.girth
            link = maxr * 0.7
        elif plan == 'tentacle':          # octopus: small soft mantle + arms
            n = 4
            maxr = 20 * g.size * g.girth
            link = maxr * 0.55
        elif plan == 'segmented':         # centipede: long thin chain of segments
            n = max(10, int(16 * g.size * g.length))
            maxr = 14 * g.size * g.girth
            link = maxr * 1.15
        else:
            n = max(6, int(11 * g.size * g.length))
            maxr = 17 * g.size * g.girth
            link = maxr * 1.05
        self.max_r = maxr
        head = Vector2(self.spine.joints[0]) if (keep_pose and hasattr(self, 'spine')) \
            else Vector2(self.pos)
        self.spine = Spine(head, n, link, build_radii(n, maxr), bend=26)
        self.spine.resolve(head)
        if plan == 'normal':
            tip = Vector2(self.spine.joints[-1])
            if keep_pose and getattr(self, 'tail_spring', None) is not None:
                self.tail_spring.target = tip     # keep momentum across a rebuild
            else:
                self.tail_spring = Vector2Spring(tip, stiffness=TAIL_SPRING_STIFFNESS, damping=0.75)
        else:
            self.tail_spring = None
        self.legs = self._build_legs(g, n, maxr)
        for leg in self.legs:
            leg.init_foot(self.spine)
        self.arms = self._build_arms(g, maxr) if plan == 'tentacle' else []

        base = 165 * (0.85 + 0.4 / g.size) * g.speed
        mult = (self.max_speed / self._speed_base) if self._speed_base else 1.0
        self.max_speed = base * mult
        self._speed_base = base

    def _build_legs(self, g, n, maxr):
        plan = getattr(g, 'plan', 'normal')
        if plan == 'tentacle':            # arms are not IK legs
            return []
        if g.leg_count <= 0:
            return []
        if plan == 'segmented':
            return self._build_centipede_legs(g, n, maxr)
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

    def _build_centipede_legs(self, g, n, maxr):
        """A short pair on (almost) every segment, phased down the body.

        The point is the *metachronal wave*: partnering each pair with the pair
        two segments back keeps neighbours from planting together, so the many
        tiny legs ripple front-to-back instead of marching in sync.
        """
        seg = maxr * 1.0 * g.leg_len
        so = maxr * 1.25
        step_len = maxr * 1.05
        legs = []
        for idx in range(1, n - 1):
            legs.append(Leg(idx, -1, so, 0.0, seg, step_len, 0.11, maxr * 0.5))
            legs.append(Leg(idx, +1, so, 0.0, seg, step_len, 0.11, maxr * 0.5))
        m = len(legs)
        for i, leg in enumerate(legs):
            leg.partner = legs[(i + 4) % m] if m > 4 else None
        return legs

    def _build_arms(self, g, maxr):
        """Octopus arms: each is a follow-the-leader sub-chain hung off the mantle.

        Not IK legs -- they don't plant. They sway/curl on their own and (in
        ``_resolve_arms``) trail the body, so a moving kraken whips its arms.
        """
        count = max(4, g.leg_count or 6)
        ajoints = 10
        link = maxr * 0.68 * g.leg_len
        base = Vector2(self.spine.joints[0])
        arms = []
        for k in range(count):
            arms.append({'a': (360.0 / count) * k,
                         'phase': k * 1.9,
                         'link': link,
                         'j': [Vector2(base) for _ in range(ajoints)]})
        return arms

    def _resolve_arms(self, dt):
        """Curl + trail the octopus arms. Each joint eases toward an outward,
        sine-curled target and then re-clamps to the link length, so the chain
        stays taut but whips when the body moves (soft follow-the-leader)."""
        mantle = self.spine.joints[0]
        base_ang = angle_of(self.spine.head_dir())
        trailing = -safe_norm(self.vel) if self.vel.length_squared() > 400 else Vector2()
        k = min(1.0, 18 * dt)
        # during a grab wind-up the arms all reach toward the target and straighten
        # -- that convergence IS the telegraph (see _ai_grapple)
        reach = getattr(self, 'arm_target', None)
        reach_ang = angle_of(reach - mantle) if reach is not None else 0.0
        for arm in self.arms:
            js = arm['j']
            link = arm['link']
            if reach is not None:
                anchor_ang = reach_ang + arm['a'] * 0.14      # cluster toward target
                swirl, amp = 7.0, 9.0                          # nearly straight spears
            else:
                anchor_ang = base_ang + arm['a']
                swirl, amp = 24.0, 34.0
            js[0].update(mantle + vfrom_angle(anchor_ang, self.max_r * 1.35))
            m = len(js)
            for i in range(1, m):
                t = i / (m - 1)
                # a wave that travels down the arm (i term) + a constant swirl so
                # even a still arm hooks like a tentacle, not a straight spoke
                wave = math.sin(self.wobble * 2.4 - i * 0.9 + arm['phase'])
                ang = anchor_ang + (swirl + wave * amp) * t
                desired = js[i - 1] + vfrom_angle(ang, link) + trailing * (link * 0.9 * t)
                js[i] += (desired - js[i]) * k
                off = js[i] - js[i - 1]
                L = off.length()
                if L > 1e-4:
                    js[i] = js[i - 1] + off * (link / L)

    # ---- hit testing ----------------------------------------------------- #
    def body_points(self):
        """Sample points along the spine: [(pos, radius, is_head), ...].

        Damage used to test a single circle at the head, so a 322px snake was only
        ~5% hittable. Same sampling idea as ``collision._samples``.
        """
        js, rs = self.spine.joints, self.spine.radii
        m = len(js)
        idx = sorted({0, m // 4, m // 2, (3 * m) // 4, m - 1})
        return [(js[i], rs[i], i == 0) for i in idx]

    def hit_test(self, pos, radius=0.0):
        """None if it misses; 'head' (weak point) or 'body' if it connects."""
        if getattr(self, 'burrowed', False):     # underground = untouchable
            return None
        if getattr(self, 'boss_invuln', False):  # boss intro / phase transition
            return None
        best = None
        for jp, r, is_head in self.body_points():
            dx = jp.x - pos[0]
            dy = jp.y - pos[1]
            reach = r + radius
            if dx * dx + dy * dy <= reach * reach:
                if is_head:
                    return 'head'            # weak point wins outright
                best = 'body'
        return best

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
        turn_resp = 1.0 - self.genome.angular_damping   # 1.0 = old behaviour unchanged
        self.vel += (target_v - self.vel) * clamp(self.accel * dt * turn_resp / self.max_speed, 0, 1)

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
            leg.update(self.spine, self.vel, dt, on_plant, self.leg_pull)
        if self.arms:
            self._resolve_arms(dt)
        self.update_secondary_springs(dt)
        self.leg_pull = approach(self.leg_pull, 1.0, 6, dt)  # decays if no one re-asserts it

        if self.genome.linear_damping > 0:
            self.vel *= math.exp(-self.genome.linear_damping * 3.0 * dt)

        spd = self.vel.length()
        w = self.genome.weight
        target_squash = (1.0 + clamp(spd / self.max_speed, 0, 1.6) * 0.16 / w) * self.squat_bias
        self.squash = approach(self.squash, target_squash, 9 / math.sqrt(w), dt)
        self.squat_bias = approach(self.squat_bias, 1.0, 6, dt)  # decays if no one re-asserts it
        self.wobble += dt * 6
        self.hit_flash = decay(self.hit_flash, dt, 3)
        self.attack_cd = decay(self.attack_cd, dt)
        self.slow_t = decay(self.slow_t, dt)

    def update_secondary_springs(self, dt):
        """Advance every cosmetic spring that chases the physical body.

        A single choke point on purpose: this project has hit "a second call
        site forgot to update the new state" three times already (the menu's
        3 hand-rolled ``integrate()`` subsets all forgot ``tail_spring``, see
        CURRENT_PLAN.md). Any bypass of ``integrate()`` (menu backdrops,
        bestiary/char-select previews) MUST call this too, and adding a new
        spring later only means touching this one method.
        """
        if self.tail_spring is not None:
            self.tail_spring.target = self.spine.joints[-1]
            self.tail_spring.update(dt)

    def reset_secondary_springs(self):
        """Snap every cosmetic spring to the current pose -- call after
        teleporting/repositioning a creature outside of normal movement, or
        the spring spends its next few frames chasing a stale anchor."""
        if self.tail_spring is not None:
            self.tail_spring.value = self.tail_spring.target = Vector2(self.spine.joints[-1])

    def _cosmetic_joints(self):
        """Physical joints with the last few tail joints blended toward
        ``tail_spring`` (overshoot/lag) -- draw-only, so hit-test/legs/eyes
        (which read ``spine.joints`` directly) are never thrown off.

        Suppressed while the tail-whip is swinging (``whip_t`` > 0): that
        directly overwrites these same joints with a hand-tuned arc
        (``_whip_arc``), and the spring -- still chasing last frame's
        pre-whip position -- fought it, visibly dulling/glitching the swing.
        """
        if self.tail_spring is None or getattr(self, 'whip_t', 0.0) > 0:
            return None
        js = list(self.spine.joints)
        n = len(js)
        k = min(TAIL_SPRING_JOINTS, n - 1)
        if k <= 0:
            return None
        lag = self.tail_spring.value - js[-1]
        cap = self.max_r * TAIL_SPRING_MAX_LAG
        if lag.length_squared() > cap * cap:
            lag.scale_to_length(cap)
        wave_amp = self.max_r * 0.12    # traveling ripple (plans/01 #5), on top
        for i in range(n - k, n):       # of the overshoot -- both draw-only
            t = (i - (n - k - 1)) / k          # ramps 0 -> 1 toward the tip
            fwd = safe_norm(js[i] - js[i + 1]) if i < n - 1 else safe_norm(js[i - 1] - js[i])
            perp = Vector2(-fwd.y, fwd.x)
            ripple = perp * (wave_amp * t * math.sin(self.wobble * 2.2 - i * 0.9))
            js[i] = js[i] + lag * t + ripple
        return js

    # ---- drawing -------------------------------------------------------- #
    def draw(self, surf, cam):
        squish = 1.0 / math.sqrt(self.squash)
        # soft glow behind the body so it pops off the ground (Animal Well vibe).
        # Bounded to the player (+ bosses via glow_body) so a horde stays cheap;
        # everyone else pops via rim light + vivid colour instead.
        if getattr(self, 'glow_body', self.kind == 'player'):
            mid = self.spine.joints[len(self.spine.joints) // 3]
            palette.glow(surf, cam.w2s(mid), self.max_r * 2.6 * cam.zoom, self.color, 0.34)

        plan = getattr(self.genome, 'plan', 'normal')
        leg_col = palette.darken(self.color, 0.3)
        thin = (plan == 'segmented')      # many little legs read better skinny
        legw = max(1, int(self.max_r * (0.18 if thin else 0.42) * cam.zoom))
        footr = max(1, int(self.max_r * (0.14 if thin else 0.28) * cam.zoom))
        for leg in self.legs:
            root = self.spine.joints[leg.idx]
            knee, foot = leg.solve(root)
            r = cam.w2s(root); k = cam.w2s(knee); f = cam.w2s(foot)
            pygame.draw.line(surf, leg_col, r, k, legw)
            pygame.draw.line(surf, leg_col, k, f, legw)
            pygame.draw.circle(surf, leg_col, f, footr)

        if self.genome.radial:
            self._draw_spider(surf, cam)
            return
        if plan == 'tentacle':
            self._draw_tentacle(surf, cam)
            return
        if plan == 'segmented':
            self._draw_segmented(surf, cam)
            return

        cj = self._cosmetic_joints()
        base = self.color
        if self.hit_flash > 0:
            base = palette.lighten(base, self.hit_flash)
        quads, head_fan, tail_fan, ring = self.spine.body_render_smooth(squish, cj)
        for q in quads:
            pygame.draw.polygon(surf, base, [cam.w2s(p) for p in q])
        if len(head_fan) >= 3:
            pygame.draw.polygon(surf, base, [cam.w2s(p) for p in head_fan])
        if len(tail_fan) >= 3:
            pygame.draw.polygon(surf, base, [cam.w2s(p) for p in tail_fan])
        poly = [cam.w2s(p) for p in ring]
        if len(poly) >= 3:
            # rim light: a bright edge just inside the dark ink outline
            pygame.draw.polygon(surf, palette.lighten(base, 0.55), poly, max(1, int(3 * cam.zoom)))
            pygame.draw.polygon(surf, C.COL_INK, poly, max(1, int(2 * cam.zoom)))

        spot = palette.darken(self.color, 0.2)
        js = cj or self.spine.joints
        rad = self.spine.radii
        for i in range(2, len(js) - 2, 2):
            pygame.draw.circle(surf, spot, cam.w2s(js[i]),
                               max(1, int(rad[i] * 0.32 * cam.zoom)))
        parts.draw_all(surf, cam, self)
        self._draw_head(surf, cam)

    def _draw_spider(self, surf, cam):
        js = self.spine.joints
        base = self.color
        if self.hit_flash > 0:
            base = palette.lighten(base, self.hit_flash)
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

    def _draw_segmented(self, surf, cam):
        """Centipede: overlapping ringed segments (the ink ring on each = the
        segmentation), head last so it sits on top, with mandibles + antennae."""
        js, rad = self.spine.joints, self.spine.radii
        n = len(js)
        base = self.color
        if self.hit_flash > 0:
            base = palette.lighten(base, self.hit_flash)
        seg = palette.lighten(base, 0.05)
        rim = palette.lighten(base, 0.5)
        ink_w = max(1, int(1.6 * cam.zoom))
        for i in range(n - 1, -1, -1):
            c = cam.w2s(js[i])
            rr = max(2, int(rad[i] * 1.2 * cam.zoom))
            pygame.draw.circle(surf, base if i == 0 else seg, c, rr)
            pygame.draw.circle(surf, rim, (c[0] - int(rr * 0.28), c[1] - int(rr * 0.3)),
                               max(1, int(rr * 0.36)))
            pygame.draw.circle(surf, C.COL_INK, c, rr, ink_w)
        head = js[0]
        d = self.spine.head_dir()
        perp = Vector2(-d.y, d.x)
        r = self.max_r
        for s in (-1, 1):                                   # mandibles
            b = head + d * (r * 0.7) + perp * (s * r * 0.42)
            tip = b + d * (r * 0.6) - perp * (s * r * 0.18)
            pygame.draw.line(surf, C.COL_INK, cam.w2s(b), cam.w2s(tip), max(2, int(2 * cam.zoom)))
        acol = palette.darken(base, 0.2)
        for s in (-1, 1):                                   # antennae
            b = head + d * (r * 0.5) + perp * (s * r * 0.5)
            wig = math.sin(self.wobble * 3 + s) * 0.3
            tip = b + d * (r * 0.95) + perp * (s * r * (0.6 + wig))
            pygame.draw.line(surf, acol, cam.w2s(b), cam.w2s(tip), max(1, int(1.5 * cam.zoom)))
        look = self._look_dir()
        for s in (-1, 1):                                   # eyes
            ep = head + d * (r * 0.2) + perp * (s * r * 0.46)
            pygame.draw.circle(surf, C.COL_WHITE, cam.w2s(ep), max(2, int(r * 0.3 * cam.zoom)))
            pygame.draw.circle(surf, C.COL_INK, cam.w2s(ep + look * (r * 0.1)),
                               max(1, int(r * 0.15 * cam.zoom)))

    def _arm_polygon(self, cam, js, base_r):
        """Smooth tapering outline around an arm chain -- same left/right-rim +
        rounded-tip technique as the spine body, so arms read as continuous flesh
        (not a string of beads)."""
        m = len(js)
        radii = [base_r * (1.0 - 0.93 * (i / (m - 1))) for i in range(m)]
        left, right = [], []
        for i in range(m):
            fwd = safe_norm(js[i + 1] - js[i]) if i < m - 1 else safe_norm(js[i] - js[i - 1])
            perp = Vector2(-fwd.y, fwd.x) * radii[i]
            left.append(js[i] + perp)
            right.append(js[i] - perp)
        tip, tdir = js[-1], safe_norm(js[-1] - js[-2])
        base_a = angle_of(tdir)
        cap = [tip + vfrom_angle(base_a + a, radii[-1] * 1.1) for a in (-60, -25, 0, 25, 60)]
        return [cam.w2s(p) for p in (left + cap + right[::-1])]

    def _draw_tentacle(self, surf, cam):
        """Octopus/kraken: reaching arms drawn as smooth continuous tentacles
        behind a pulsing mantle bulb."""
        base = self.color
        if self.hit_flash > 0:
            base = palette.lighten(base, self.hit_flash)
        arm_col = palette.darken(base, 0.1)
        rim = palette.lighten(base, 0.5)
        spot = palette.darken(base, 0.2)
        rim_w = max(1, int(2 * cam.zoom))
        ink_w = max(1, int(2 * cam.zoom))
        arm_r = self.max_r * 0.62
        for arm in self.arms:
            js = arm['j']
            poly = self._arm_polygon(cam, js, arm_r)
            if len(poly) >= 3:
                pygame.draw.polygon(surf, arm_col, poly)
                pygame.draw.polygon(surf, rim, poly, rim_w)
                pygame.draw.polygon(surf, C.COL_INK, poly, ink_w)
            for i in range(2, len(js) - 2, 3):    # faint spots, like the lizard body
                t = i / (len(js) - 1)
                rr = max(1, int(arm_r * (1.0 - 0.93 * t) * 0.34 * cam.zoom))
                pygame.draw.circle(surf, spot, cam.w2s(js[i]), rr)
        head = self.spine.joints[0]
        mc = cam.w2s(head)
        pulse = 1.0 + 0.05 * math.sin(self.wobble * 2.4)
        mr = max(4, int(self.max_r * 1.7 * pulse * cam.zoom))
        pygame.draw.circle(surf, base, mc, mr)
        pygame.draw.circle(surf, rim, (mc[0] - int(mr * 0.3), mc[1] - int(mr * 0.34)),
                           max(1, int(mr * 0.42)))
        pygame.draw.circle(surf, palette.lighten(base, 0.55), mc, mr, max(1, int(3 * cam.zoom)))
        pygame.draw.circle(surf, C.COL_INK, mc, mr, max(1, int(2 * cam.zoom)))
        d = self.spine.head_dir()
        perp = Vector2(-d.y, d.x)
        r = self.max_r
        look = self._look_dir()
        for s in (-1, 1):
            ep = head + d * (r * 0.4) + perp * (s * r * 0.62)
            sp = cam.w2s(ep)
            pygame.draw.circle(surf, C.COL_WHITE, sp, max(2, int(r * 0.46 * cam.zoom)))
            pygame.draw.circle(surf, C.COL_INK, cam.w2s(ep + look * (r * 0.2)),
                               max(1, int(r * 0.22 * cam.zoom)))

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
    def __init__(self, pos, controller, colorset, index, character=None):
        from . import characters
        char = character if character is not None else characters.get(characters.DEFAULT)
        # Shape comes from the character, HUE comes from the player slot: the
        # colourset is what tells P1 from P2, so letting a character own the hue
        # would make two players who picked the same one indistinguishable.
        super().__init__(pos, 'player', genome=char.make_genome(), color=colorset[0])
        self.character = char
        self.character_id = char.id
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
        # everything this dash already hit -- collisions run every frame, so
        # without this one dash lands ~10 hits on whatever it overlaps
        self.dash_hits = set()
        self.clog = 0.0           # how buried in enemy bodies we are (collision.py)
        self.clog_f = 0.0         # smoothed, so the drag eases in/out
        # tail whip ("rabada"): a lateral lunge whose follow-through swings the tail
        self.whip_t = 0.0         # 0 -> 1 over the swing
        self.whip_cd = 0.0
        self.whip_cooldown = 0.85
        self.whip_hits = set()    # one hit per enemy per swing (see dash_hits)
        self.whip_side = 1
        self.whip_dir = Vector2()
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
        self.pollen_mult = 1.0       # from meta-progression (Colheita)
        self.weapons = {}            # weapon id -> level
        self.weapon_state = {}       # weapon id -> per-weapon state
        # --- character-driven knobs (characters.py sets these via char.apply) ---
        self.weapon_cap = 6          # VIBORA caps at 2, LARVA grows 1 -> 6
        self.can_dash = True         # COURACADO cannot dash at all
        self.knockback_immune = False
        self.whip_mult = 1.0         # VIBORA's tail hits far harder
        self.rerolls_per_round = 0   # LAGARTO: rerolls of the level-up hand,
        # refilled once per ROUND (not per level-up: you level several times a
        # round, so refilling there made them effectively unlimited)
        self.rerolls = 0
        self.growth = 0              # LARVA: kills banked toward the next size step
        # --- items (items.py) ---
        self.items = []              # owned item ids, in pickup order
        self.ability = None          # equipped ACTIVE item id (the socket)
        self.ability_cd = 0.0
        self.ability_charge = 0.0    # 0..1, for the HUD ring
        self.ability_kills = 0       # the real counter (integers do not drift)
        self.shed_t = 0.0            # Muda de Pele / Casulo: extra i-frames
        self._trail_cd = 0.0         # spacing of the dash's corrosive puddles
        # mechanic-rewriting passives. Each is read at exactly ONE call site --
        # the dash taught us what happens when the same rule lives in two places.
        self.dash_trail = False      # dash leaves a corrosive puddle
        self.dash_marks = False      # dashing through marks the enemy
        self.dash_chain_bonus = False
        self.tongue_throw = False    # tongue throws instead of pulling
        self.tongue_drain = False
        self.whip_darts = False      # whip fires darts from the arc tips
        self.whip_reflect = False    # whip bats enemy shots back
        self.whip_full = False       # whip sweeps the whole circle
        self.kill_blast = False
        self.kill_heal = False
        self.poison_spreads = False
        self.pollen_magnet = False
        self.amount_back = False     # weapons also fire backwards
        self.adrenaline = False
        self.extra_life = False
        self.used_extra_life = False
        self.shed_on_hurt = False    # Casulo: extra i-frames after being hit
        # charms (Hollow-Knight-style adaptations in 3 body slots)
        self.armor = 0.0             # fraction of damage blocked (carapaca)
        self.charm_slots = {'head': None, 'back': None, 'tail': None}
        self.charms_owned = []
        # LAST: the character reads and adjusts fields declared above (armour,
        # thorns, health, whip cooldown), so it cannot run any earlier.
        self.gain_weapon(char.weapon)
        if char.apply:
            char.apply(self)

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
            charms.CHARMS[old].unapply(self, game)
        self.charm_slots[slot] = cid
        ch.apply(self, game)
        if game:
            game.fx.burst(self.pos, ch.color, 16, 200)
            game.fx.spark_burst(self.pos, palette.lighten(ch.color, 0.4), 10, 260)
            game.fx.ring(self.pos, ch.color)

    def damage_mult(self):
        """Every player damage source multiplies by this.

        Adrenalina lives here rather than in each weapon/dash/whip: a global rule
        written once cannot drift out of sync with the sources that read it.
        """
        m = self.might
        if self.adrenaline and self.health < self.max_health * C.ITEM_ADRENALINE_HP:
            m *= C.ITEM_ADRENALINE_MULT
        return m

    def dash_damage(self):
        """Damage one dash contact deals.

        Single source of truth on purpose: the nest call site in ``game`` read
        ``C.DASH_DAMAGE`` directly, so any scaling added at the enemy call site
        would have silently skipped nests -- the same "two places that must agree"
        shape as the whip's hitbox vs. its animation span.
        """
        return (C.DASH_DAMAGE * (C.DASH_WINGS_MULT if self.wings else 1.0)
                * self.damage_mult())

    def gain_weapon(self, wid):
        if wid not in self.weapons and len(self.weapons) < self.weapon_cap:
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
        """Take damage. Returns True only if it actually LANDED.

        The return value matters: side effects that ride along with a hit (the
        scorpion's slow) must not fire when the hit bounced off i-frames --
        otherwise you get a debuff with no damage number to explain it.
        """
        # Sandbox god mode (SB6): the player under test ignores all damage
        # application -- energy, movement and dash stay real. ``hurt`` is THE
        # single choke point every damage source funnels through (projectiles,
        # body contact, boss AoEs), so guarding it here covers them all with one
        # early-out. No-op on the normal path: the check short-circuits on
        # ``game.mode == 'sandbox'`` before ``god_mode`` is ever read, and only a
        # player (never an enemy) is in ``game.players``.
        if game.mode == 'sandbox' and game.god_mode and self in game.players:
            return False
        if self.dashing or self.hit_flash > 0.45 or self.down or self.shed_t > 0:
            return False
        dmg *= (1.0 - self.armor)                       # carapaca charm blocks a %
        self.health -= dmg
        self.hit_flash = 1.0
        if not self.knockback_immune:   # COURACADO does not get moved, by anything
            self.vel = src_dir * (140 + dmg * 6)
        game.fx.burst(self.pos, self.color, 10 + int(dmg / 2), 200)
        game.fx.spark_burst(self.pos, C.COL_FX_SPARK, 8 + int(dmg / 3), 320)
        game.shake(4 + dmg * 0.4)
        if self.shed_on_hurt:
            self.shed_t = max(self.shed_t, C.ITEM_CASULO_TIME)
        if self.health <= 0 and self.extra_life and not self.used_extra_life:
            # Segundo Folego: one escape per run, and it has to be LOUD or the
            # player will not know it happened
            self.used_extra_life = True
            self.health = self.max_health * 0.5
            self.shed_t = C.ITEM_MUDA_TIME
            game.punch(0.12, 16, flash=0.5)
            game.fx.ring(self.pos, C.COL_FX_REVIVE)
            game.fx.spark_burst(self.pos, C.COL_FX_REVIVE, 34, 460)
            game.fx.popup(self.pos, "SEGUNDO FOLEGO!", C.COL_FX_REVIVE)
            audio.play('levelup', 0.9)
        elif self.health <= 0:
            self.health = 0
            self.down = True
            self.revive = 6.0
            game.fx.burst(self.pos, C.COL_WHITE, 26, 260)
            game.fx.ring(self.pos, self.color)
        return True

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

        # Soft collision: pushing through enemies costs speed instead of shoving you
        # around (collision.py fills `clog` with the overlap depth). Eased so it
        # doesn't stutter, and ignored mid-dash -- ploughing through is the point.
        # `clog` sums the overlap of 5x5 sample pairs, so ONE enemy already reached
        # ~25 against the old max_r*1.2 divisor -- the drag saturated on first
        # contact and read as binary (full speed or half speed, nothing between).
        # Scaling the divisor to CONTACT_FULL enemies restores the gradient: one
        # body slows you a little, being buried in the horde slows you a lot.
        full = max(self.max_r * 1.2 * C.CONTACT_FULL, 1.0)
        target_clog = clamp(self.clog / full, 0.0, 1.0)
        self.clog_f = approach(self.clog_f, target_clog, 9, dt)
        drag = 1.0 - C.CONTACT_DRAG * self.clog_f

        speed_mul = 1.0
        if self.dash_time > 0:
            self.dash_time -= dt
            speed_mul = 3.4 if self.wings else 2.9
            drag = 1.0
            game.fx.trail(self.pos, self.color)
            if self.dash_trail:
                self._trail_cd -= dt
                if self._trail_cd <= 0:
                    from . import weapons as W
                    self._trail_cd = C.ITEM_TRAIL_DROP
                    # hostile=False -> `dmg` is DPS and hits ENEMIES (see Puddle)
                    game.spawn_puddle(W.Puddle(self.pos, C.ITEM_TRAIL_R,
                                               C.ITEM_TRAIL_DMG, C.ITEM_TRAIL_LIFE,
                                               hue=95))
        speed_mul *= drag
        self.dash_cd = decay(self.dash_cd, dt)

        if c.dash_edge and self.can_dash and self.dash_cd <= 0 \
                and self.energy >= C.DASH_COST:
            c.consume('dash')
            move = c.move if c.move.length_squared() > 0.1 else self.facing
            self.vel = safe_norm(move) * self.max_speed * (3.5 if self.wings else 3.0)
            self.dash_time = 0.2 if self.wings else 0.16
            self.dash_hits.clear()          # fresh dash -> everyone is hittable again
            self.dash_cd = self.dash_cooldown * (0.8 if self.wings else 1.0)
            self.energy -= C.DASH_COST if self.wings else C.DASH_COST + 4
            audio.play('dash')
            game.fx.burst(self.pos, self.color, 14, 200)
            game.fx.spark_burst(self.pos, palette.lighten(self.color, 0.3), 12, 340)
            game.shake(5)

        self.steer(c.move, dt, speed_mul)
        self.integrate(dt, on_plant=game.fx.dust)
        self._whip_arc(dt)

        if c.tongue_edge and self.tongue_t == 0 and self.energy >= C.TONGUE_COST:
            c.consume('tongue')
            self.tongue_t = 0.001
            self.energy -= C.TONGUE_COST                       # tongue costs energy
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
                    if getattr(t, 'kind', None) == 'enemy':    # tongue: hurt + move
                        t.take_hit(game, safe_norm(t.pos - self.pos), 2)
                        if self.tongue_throw:      # Arremesso: fling OUT, not in
                            t.vel += safe_norm(t.pos - self.pos) * C.ITEM_THROW_SPEED
                        else:
                            t.vel += safe_norm(self.pos - t.pos) * 200   # yank in
                        if self.tongue_drain:      # Sanguessuga: steal life
                            self.health = min(self.max_health,
                                              self.health + C.ITEM_DRAIN)
                            game.fx.popup(self.pos, "+vida", (120, 240, 140))
                        game.fx.spark_burst(t.pos, C.COL_FX_SPARK, 7, 240)
                    else:
                        game.eat(self, t)
                self.tongue_target = None

        # Iman de Polen: coletaveis (fruta/inseto/ovo) driftam ate voce. Pollen is
        # a counter, not a world pickup, so the magnet pulls the things you can
        # actually pick up -- and killing near them is how you bank pollen anyway.
        if self.pollen_magnet:
            for pk in game.pickups:
                if pk.dead:
                    continue
                d = pk.pos - self.pos
                dist = d.length()
                if 1.0 < dist < C.ITEM_MAGNET_R:
                    pk.pos += safe_norm(d) * -min(dist, C.ITEM_MAGNET_PULL * dt)

        # --- active item ------------------------------------------------- #
        # Same buffer/consume contract as dash and whip: the press survives a
        # frame that ran zero sim steps, and is eaten only when it actually fires.
        self.shed_t = decay(self.shed_t, dt)
        if c.item_edge and self.ability and self.ability_charge >= 1.0:
            from . import items as itemlib
            if itemlib.use_active(self, game):
                c.consume('item')
                audio.play('levelup', 0.5)

        # --- tail whip ("rabada") ---------------------------------------- #
        self.whip_cd = decay(self.whip_cd, dt)
        if c.whip_edge and self.whip_cd <= 0 and self.energy >= C.WHIP_COST:
            c.consume('whip')
            self.whip_t = 0.001
            self.whip_cd = self.whip_cooldown
            self.energy -= C.WHIP_COST
            self.whip_hits.clear()          # fresh swing -> everyone hittable again
            # swing toward the nearest enemy; with nobody around, alternate sides
            side = self.whip_side
            foe = game.nearest_enemy(self.pos, 280)
            if foe is not None:
                d = foe.pos - self.pos
                side = 1 if (self.facing.x * d.y - self.facing.y * d.x) > 0 else -1
            self.whip_side = -side
            # Sideways ARC, not a velocity impulse. An impulse got erased within a
            # few frames by steer() pulling velocity back to the input direction --
            # what survived was whatever pointed the way you were already going, so
            # the whip read as a forward lunge. Driving the head along the arc (and
            # muting steer while it runs) is what makes the tail crack sideways.
            self.whip_dir = Vector2(-self.facing.y, self.facing.x) * side
            if self.whip_darts:                 # Farpas: piercing barbs off the arc
                self._fire_whip_darts(game)
            audio.play('dash', 0.65)
            game.shake(3)
        if self.whip_t > 0:
            self.whip_t += dt / C.WHIP_TIME
            if self.whip_t >= 1:
                self.whip_t = 0.0
            else:
                game.fx.trail(self.spine.joints[-1], palette.lighten(self.color, 0.3))
                self._whip_hit(game)

        # --- auto-weapons (Vampire-Survivors style: they act on their own) ---
        self.ability_cd = decay(self.ability_cd, dt)
        for wid, lvl in self.weapons.items():
            weapons.WEAPONS[wid].tick(self, game, dt, self.weapon_state[wid], lvl)

        self.energy = clamp(self.energy + dt * 6, 0, self.max_energy)
        if self.regen > 0 and self.health < self.max_health:
            self.health = min(self.max_health, self.health + self.regen * dt)

    def _whip_span(self):
        """(pivot index, joint count) of the section that whips.

        Shared by the animation and the hitbox on purpose: the damaging joints
        MUST be the ones that visibly move, or you get the classic 'it looked
        like it hit' complaint. When only the last 3 joints were tested and the
        swinging section grew to 6, the tail swept right past enemies.
        """
        n = len(self.spine.joints)
        k = max(4, n // 2)                      # blend the bend over half the body
        pv = n - k - 1                          # pivot joint (behind the legs)
        return (pv, k) if pv >= 1 else (None, 0)

    def _whip_arc(self, dt):
        """Curl the TAIL sideways through the swing, leaving the head where it is.

        The spine is follow-the-leader, so it can only be *driven* from the head --
        which is exactly why an earlier version swung the whole player instead of
        the tail. Here the last few joints are rebuilt from a pivot with a
        per-segment angle offset: link distances stay exact, and the club/sting
        art follows for free because ``parts.draw_tail`` reads js[-1]/js[-2].

        This override survives to draw time only because player contact is soft
        (``collision.py``): the player is never pushed, so ``separate`` skips the
        re-resolve that would otherwise wipe it the same frame.
        """
        if self.whip_t <= 0 or self.whip_dir.length_squared() < 1e-6:
            return
        js = self.spine.joints
        pv, k = self._whip_span()
        if pv is None:
            return
        n = len(js)
        # Anchor the swing to the BODY (straight back from the pivot), not to last
        # frame's tail: spine.resolve rebuilds joint directions from their previous
        # positions, so anchoring to the tail fed the curl back into itself and the
        # swing cancelled out to a wobble.
        back = js[pv] - js[max(0, pv - 2)]
        if back.length_squared() < 1e-6:
            return
        cross = back.x * self.whip_dir.y - back.y * self.whip_dir.x
        side = 1.0 if cross > 0 else -1.0
        # A full period, not a half: the tail sweeps out one side, back through
        # the middle and out the other in a single press. Starts and ends at 0
        # with matching slope, so it eases in and out on its own.
        env = math.sin(self.whip_t * 2.0 * math.pi)
        sweep = C.WHIP_SWEEP * (C.ITEM_SPIRAL_MULT if self.whip_full else 1.0)
        total = side * sweep * env
        # Spread the bend across every joint instead of turning the whole section
        # at the pivot -- that hinge is what read as "a rigid chunk rotating".
        # The ramp toward the tip is GENTLE on purpose: a steep one (quadratic)
        # put ~80 deg into the last link, well past the spine's own bend limit
        # (26 deg), so it showed as a kink and then got clamped by the next
        # resolve. Near-uniform turns = near-circular arc = the lizard keeps its
        # natural curve while still whipping a little harder at the end.
        w = [0.6 + 0.8 * (idx / max(1, k - 1)) for idx in range(k)]
        inv = 1.0 / sum(w)
        ang = angle_of(back)
        for idx, i in enumerate(range(pv + 1, n)):
            ang += total * w[idx] * inv
            js[i] = js[i - 1] + vfrom_angle(ang, self.spine.link)

    def _fire_whip_darts(self, game):
        """Farpas de Cauda: a fan of PIERCING barbs thrown along the swing.

        Fired once at swing start (not per frame). Piercing so they read as the
        tail flinging shrapnel through the horde, not single-target pokes.
        """
        from .projectile import Projectile
        base = angle_of(self.whip_dir)
        tail = self.spine.joints[-1]
        for k in range(C.ITEM_DART_COUNT):
            off = (k - (C.ITEM_DART_COUNT - 1) / 2) * C.ITEM_DART_SPREAD
            v = vfrom_angle(base + off, C.ITEM_DART_SPEED)
            pr = Projectile(tail, v, (255, 210, 120),
                            dmg=int(round(C.ITEM_DART_DMG * self.damage_mult())),
                            radius=5, hostile=False, life=0.9)
            pr.pierce = True
            game.spawn_projectile(pr)
        game.fx.spark_burst(tail, (255, 220, 150), 8, 300)

    def _whip_reflect(self, game):
        """Contragolpe: the swinging tail bats enemy shots back at their owners."""
        js = self.spine.joints
        pv, _k = self._whip_span()
        tail = js[pv + 1:] if pv is not None else js[-3:]
        reach = self.max_r * 1.6
        for pr in game.projectiles:
            if not pr.hostile:
                continue
            if any(pr.pos.distance_to(j) < reach for j in tail):
                pr.hostile = False              # now it hits enemies
                pr.vel = -pr.vel
                pr.color = (255, 230, 150)
                pr.dmg = max(pr.dmg, int(round(8 * self.damage_mult())))
                game.fx.spark_burst(pr.pos, (255, 240, 180), 5, 240)

    def _whip_hit(self, game):
        """The real tail joints are the hitbox -- what you see is what hits.

        The tip's own ``spine.radii`` is tiny (~0.22*max_r), so the swing uses an
        explicit reach instead. Gated by ``whip_hits`` for the same reason as
        ``dash_hits``: this runs every frame of the swing.
        """
        if self.whip_t < 0.06 or self.whip_t > 0.97:
            return                      # only the very start/end don't connect
        if self.whip_reflect:
            self._whip_reflect(game)
        js = self.spine.joints
        # Hitbox is the TIP end of the swing, not the whole animated span. The
        # span (half the body) still *moves* -- but damaging all of it hit ~7 of
        # 12 enemies in a full circle, which read as "the tail one-shots the room".
        # The last few joints are the fastest, most visible part of the sweep, so
        # concentrating damage there keeps "what you see hits" while shrinking the
        # area to the arc behind/beside you (measured 2-3 targets).
        tail = js[-C.WHIP_HIT_JOINTS:]
        reach = self.max_r * C.WHIP_REACH
        club = self.genome.tail == 'club'
        sting = self.genome.tail == 'sting'
        # scales with `might` like every auto-weapon does. Without this the whip
        # was a flat number for the whole run -- strong on wave 1, irrelevant by
        # wave 15 -- and no upgrade could ever improve it.
        dmg = (C.WHIP_DAMAGE * (C.WHIP_CLUB_MULT if club else 1.0)
               * self.damage_mult() * self.whip_mult)
        knock = C.WHIP_KNOCK_CLUB if club else C.WHIP_KNOCK
        for e in game.enemies:
            if e.dead or e in self.whip_hits:
                continue
            for j in tail:
                where = e.hit_test(j, reach)
                if not where:
                    continue
                self.whip_hits.add(e)
                d = dmg * (C.CRIT_MULT if where == 'head' else 1.0)
                if where == 'head':
                    game.crit_fx(e.spine.joints[0])
                away = safe_norm(e.pos - j)
                e.take_hit(game, away, int(round(d)))
                e.vel += away * knock   # take_hit ASSIGNS vel, so add afterwards
                if sting:
                    e.apply_poison(2.5, 2.5)
                game.fx.spark_burst(j, palette.lighten(self.color, 0.4), 9, 320)
                game.shake(6 if club else 3)
                if e.dead:
                    game.punch(0.05, 7)
                break

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

    def _draw_slow_mark(self, surf, cam):
        """Show WHY you are slow.

        Two independent brakes multiply on the player (a sting's slow and the
        contact drag) and neither had any tell, so being at half speed looked
        like the game misbehaving. Cold rings under the body read as "something
        is holding you" without adding a HUD element.
        """
        if self.slow_t <= 0:
            return
        sp = cam.w2s(self.pos)
        f = clamp(self.slow_t / 0.4, 0, 1)
        r = int(self.max_r * 1.9 * cam.zoom)
        col = (120, 190, 255)
        palette.glow(surf, sp, r, col, 0.22 * f)
        pygame.draw.circle(surf, col, sp, r, max(1, int(2 * cam.zoom)))

    def draw(self, surf, cam):
        self._draw_slow_mark(surf, cam)
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
        self.wander = random_dir()
        self.wander_t = 0.0
        self.hp = int(self.genome.hp)
        self.max_hp = self.hp
        self.species = None
        self.xp_value = 3
        self.score_value = 15
        self.grants = None
        self.base_color = self.color   # pristine colour; friends fade from this
        self.aggro = None         # creature that pulled this enemy's attention
        self.aggro_t = 0.0
        self.life = None          # friends are temporary: seconds left before leaving
        self.poison_t = 0.0
        self.poison_dps = 0.0
        self._pacc = 0.0
        self._dmg_acc = 0.0          # fractional damage from auras/orbitals
        self.lunge_t = 0.0            # >0 telegraphing, <0 mid-lunge
        self.shoot_cd = 0.0
        self.shoot_charge = 0.0      # >0 = winding up a shot (telegraph)
        # --- behaviours added in phase 2 ---
        self.flying = self.genome.behavior == 'fly'   # collision.py skips flyers
        self.bob = random.uniform(0, C.TAU)           # flyer's hover wobble
        self.fuse = 0.0               # bomber: >0 = lit, counts down to the blast
        self._blown = False           # bomber: already detonated (recursion guard)
        self.burst_left = 0           # gunner: shots left in the current burst
        # --- phase B4 behaviours (new procedural bodies) ---
        self.burrowed = False         # centipede: intangible while underground
        self.burrow_state = 'surface'
        self.burrow_t = random.uniform(1.4, C.CENT_SURFACE_TIME)
        self.dive_to = Vector2(self.pos)   # where a burrower will surface
        self.grapple_t = 0.0          # octopus: >0 winding up a grab (arms reach)
        self.grapple_cd = random.uniform(0.4, 1.6)
        self.arm_target = None        # world point the arms reach toward (telegraph)
        self.grab_show = 0.0          # octopus: frames drawing the hooked arm
        self.grabbed = None
        # --- Fase 5: boss FSM (see boss.py; None on a non-boss spawn) ---
        self.boss_ai = None
        self.boss_invuln = False      # intro / phase-transition windows only
        # --- champion layer (see champions.py; None on a plain spawn) ---
        self.champion = None
        self.champion_name = ''
        self.champion_ticks = []      # per-frame hooks from the applied champions
        self.rally_t = 0.0            # ALFA's call: temporary speed boost
        # How strongly the champion advertises itself (aura + name). ESPECTRO
        # drops this while camouflaged -- otherwise its own label floats above it
        # in full colour and gives away the ambush the variant exists to make.
        self.champion_vis = 1.0
        self.marked = False       # Presa Marcada: next hit lands as a crit
        self.front_armor = 0.0        # BLINDADO: fraction blocked from the front
        self.death_blast = False      # EXPLOSIVO: parting AoE
        self.death_split = False       # DIVISOR: splits into smaller copies on death
        self.split_gen = 0             # remaining split generations
        self.split_count = 2           # copies per split (DIVISOR=2; a boss can override)

    def apply_poison(self, dps, dur):
        self.poison_dps = max(self.poison_dps, dps)
        self.poison_t = max(self.poison_t, dur)

    def sync_max_hp(self):
        """Call after spawn-time hp tweaks so the health bar scale is right."""
        self.max_hp = max(self.max_hp, self.hp)

    def damage(self, game, amount, direction=None):
        """Fractional damage (for auras/orbitals/puddles that tick every frame)."""
        self._dmg_acc += amount
        whole = int(self._dmg_acc)
        if whole > 0:
            self._dmg_acc -= whole
            self.hit_flash = max(self.hit_flash, 0.4)
            if direction is not None:
                self.vel += direction * 120 * self.genome.knockback
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
            self.wander = random_dir()
        return self.wander

    def _fade_by_vitality(self):
        """Allies desaturate as they lose health OR run out of time -> readable at a glance."""
        hp_f = self.hp / max(1, getattr(self, 'max_hp', self.hp))
        life_f = 1.0 if self.life is None else clamp(self.life / C.FRIEND_LIFE, 0, 1)
        v = clamp(min(hp_f, life_f), 0, 1)
        self.color = palette.mix((116, 110, 138), self.base_color, v)

    def update(self, dt, game):
        if self.life is not None:                 # allies wander off after a while
            self.life -= dt
            self._fade_by_vitality()
            if self.life <= 0:
                self.dead = True
                game.fx.burst(self.pos, self.color, 14, 170)
                game.fx.ring(self.pos, self.color)
                return
        if self._tick_status(dt, game):
            return
        self.shoot_cd = decay(self.shoot_cd, dt)
        self.aggro_t = decay(self.aggro_t, dt)
        self.rally_t = decay(self.rally_t, dt)
        self.grab_show = decay(self.grab_show, dt)
        for hook in self.champion_ticks:
            hook(self, dt, game)
        if self.aggro is not None and (self.aggro.dead or self.aggro_t <= 0):
            self.aggro = None
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
            # a friend that hits us steals the aggro for a few seconds -> allies tank
            target = self.aggro if self.aggro is not None else game.nearest_player(self.pos)
            beh = self.genome.behavior
            if target and target.pos.distance_to(self.pos) < 700:
                if beh == 'ranged':
                    d, speed = self._ai_ranged(dt, game, target)
                elif beh == 'lunge':
                    d, speed = self._ai_lunge(dt, game, target)
                elif beh == 'fly':
                    d, speed = self._ai_fly(dt, game, target)
                elif beh == 'bomber':
                    d, speed = self._ai_bomber(dt, game, target)
                elif beh == 'gunner':
                    d, speed = self._ai_gunner(dt, game, target)
                elif beh == 'venom':
                    d, speed = self._ai_venom(dt, game, target)
                elif beh == 'burrow':
                    d, speed = self._ai_burrow(dt, game, target)
                elif beh == 'grapple':
                    d, speed = self._ai_grapple(dt, game, target)
                elif beh == 'boss' and self.boss_ai is not None:
                    d, speed = self.boss_ai.tick(dt, game)
                    self._apply_mood_pose()
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
                    foe.aggro = self              # taunt: it now comes after us
                    foe.aggro_t = C.AGGRO_TIME
                    self.attack_cd = 1.1          # allies hit slower than the player
                    game.fx.burst(foe.pos, C.COL_FRIEND, 8, 160)
            elif leader:
                off = leader.pos.distance_to(self.pos)
                if off > 120:
                    d = safe_norm(leader.pos - self.pos)
                    speed = clamp(off / 200, 0.4, 1.3)
                else:
                    d = self.wander_dir(dt) * 0.3
        if self.rally_t > 0:               # roused by an ALFA's call
            speed *= C.CHAMP_ALFA_SPEED
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
            self.squat_bias = 0.88                # coiling to spit -- see integrate()
            if random.random() < dt * 26:
                game.fx.burst(mouth, palette.lighten(self.color, 0.3), 1, 50)
            if self.shoot_charge <= 0:
                game.spawn_projectile(game_spit(mouth, target.pos, self.color,
                                                dmg=C.ENEMY_PROJ_DMG))
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
            self.squat_bias = 0.8          # crouching to pounce -- see integrate()
            if self.lunge_t <= 0:
                self.vel = to * self.max_speed * 3.2      # pounce!
                self.lunge_t = -0.25
                self.squat_bias = 1.55     # explode out of the crouch
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

    # ---- phase-2 behaviours ------------------------------------------------ #
    def _ai_fly(self, dt, game, target):
        """Straight-line hunter that ignores the horde (collision skips flyers).

        It has no legs to plant, so the read comes entirely from the hover bob --
        without it a flyer looks like a ground lizard sliding, and the player has
        no way to know it cannot be body-blocked.
        """
        self.bob += dt * 7.0
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        if dist < (self.max_r + target.max_r) * 1.1 and self.attack_cd <= 0:
            self._contact(game, target)
        drift = Vector2(-to.y, to.x) * math.sin(self.bob) * 0.35
        return safe_norm(to + drift), 1.15

    def _ai_bomber(self, dt, game, target):
        """Kamikaze whose fuse, once lit, is a promise it cannot take back.

        The Mulliboom rule: after the fuse lights the bomber *slows down* and the
        blast happens wherever it ends up, so walking away always works. A charge
        that tracks you until it detonates is not a telegraph, it is just damage.
        """
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        if self.fuse > 0:
            self.fuse -= dt
            if random.random() < dt * 40:
                game.fx.burst(self.spine.joints[0], (255, 210, 120), 1, 90)
            if self.fuse <= 0:
                self.explode(game)
            return to, 0.25                       # committed and slow: dodgeable
        if dist < C.BOMBER_TRIGGER:
            self.fuse = C.BOMBER_FUSE
            audio.play('nest', 0.5)
            game.fx.ring(self.pos, (255, 170, 90))
        return to, 1.05

    def _ai_gunner(self, dt, game, target):
        """High rate of fire, low damage per shot: pressure, not burst.

        Holds mid-range and fires a burst, so the threat is a *stream* you have to
        break line with, unlike the spitter's single telegraphed spike.
        """
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        mouth = self.spine.joints[0] + self.spine.head_dir() * self.max_r
        if self.burst_left > 0 and self.shoot_cd <= 0:
            self.burst_left -= 1
            self.shoot_cd = C.GUNNER_BURST_GAP
            spread = random.uniform(-C.GUNNER_SPREAD, C.GUNNER_SPREAD)
            aim = self.pos + (target.pos - self.pos).rotate(spread)
            game.spawn_projectile(game_spit(mouth, aim, self.color,
                                            dmg=C.GUNNER_DMG, effect=None,
                                            speed=300, radius=5))
            game.fx.spark_burst(mouth, self.color, 3, 150)
        elif self.burst_left <= 0 and self.shoot_cd <= 0 and dist < 460:
            self.burst_left = C.GUNNER_BURST
            self.shoot_cd = C.GUNNER_RELOAD
        if dist < 240:
            d = -to
        elif dist > 400:
            d = to
        else:
            d = Vector2(-to.y, to.x) * (1 if int(self.wobble) % 2 else -1)
        return d, 0.8

    def _ai_venom(self, dt, game, target):
        """Lobs venom that leaves a puddle where it lands -- area denial.

        The shot is aimed at where you *are* and its life is set so it lands
        there, which makes it a zoning tool rather than a hit: standing still is
        what punishes you, so it pushes the player to keep moving.
        """
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        mouth = self.spine.joints[0] + self.spine.head_dir() * self.max_r
        if self.shoot_charge > 0:
            self.shoot_charge -= dt
            if random.random() < dt * 30:
                game.fx.burst(mouth, (150, 240, 110), 1, 60)
            if self.shoot_charge <= 0:
                pr = game_spit(mouth, target.pos, (140, 235, 100),
                               dmg=C.VENOM_SPIT_DMG, effect='poison',
                               speed=C.VENOM_SPIT_SPEED, radius=7)
                # land ON the aim point: life = travel time, so the puddle is
                # dropped where the telegraph pointed instead of flying past
                travel = mouth.distance_to(target.pos) / C.VENOM_SPIT_SPEED
                pr.life = max(0.12, min(travel, 2.2))
                pr.puddle = dict(r=C.VENOM_PUDDLE_R, dmg=C.VENOM_PUDDLE_DMG,
                                 life=C.VENOM_PUDDLE_LIFE, hue=100,
                                 tick=C.VENOM_PUDDLE_TICK)
                game.spawn_projectile(pr)
                game.fx.spark_burst(mouth, (150, 240, 110), 6, 190)
            return to * 0.05, 0.0
        if self.shoot_cd <= 0 and dist < 430:
            self.shoot_cd = C.VENOM_CD
            self.shoot_charge = C.VENOM_WINDUP
        if dist < 250:
            d = -to
        elif dist > 390:
            d = to
        else:
            d = Vector2(-to.y, to.x) * (1 if int(self.wobble) % 2 else -1)
        return d, 0.72

    def _ai_burrow(self, dt, game, target):
        """CENTOPEIA: hunt on the surface, then dive and ambush (Isaac Para-Bite).

        The dive is intangible, so you cannot chip it underground; it surfaces at
        a point locked in when it dove, drawn as a growing ring on the ground.
        Standing still = it erupts under you; the fair counter is to leave the
        ring. Punishes camping and running in a straight line."""
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        self.burrow_t -= dt
        dirt = (150, 112, 74)
        if self.burrow_state == 'surface':
            if dist < (self.max_r + target.max_r) * 1.1 and self.attack_cd <= 0:
                self._contact(game, target)
            if self.burrow_t <= 0:                    # start the dig telegraph
                self.burrow_state = 'digging'
                self.burrow_t = C.CENT_DIG_TIME
                audio.play('nest', 0.35)
            return to, 1.2
        if self.burrow_state == 'digging':
            # rooted, kicking up dirt: the body sinks into a hole (_draw_burrow),
            # so it reads as burrowing rather than blinking out
            if random.random() < dt * 55:
                game.fx.burst(self.pos + random_dir(random.uniform(0, self.max_r)),
                              dirt, 1, 150)
            if self.burrow_t <= 0:
                self.burrow_state = 'under'
                self.burrowed = True
                self.burrow_t = C.CENT_UNDER_TIME
                self.dive_to = Vector2(target.pos) + vfrom_angle(
                    random.uniform(0, 360), random.uniform(0, 70))
                game.fx.burst(self.pos, dirt, 24, 280)
                game.fx.ring(self.pos, (170, 128, 86))
            return Vector2(), 0.0
        # underground: race to the marked spot, leaving a dust trail, then erupt
        du = self.dive_to - self.pos
        if random.random() < dt * 34:
            game.fx.burst(self.pos, dirt, 1, 90)
        if du.length() < 42 or self.burrow_t <= 0:
            self.burrow_state = 'surface'
            self.burrowed = False
            self.burrow_t = C.CENT_SURFACE_TIME
            self._erupt(game)
            return to, 0.0
        return safe_norm(du), 2.4

    def _erupt(self, game):
        pos = Vector2(self.pos)
        game.fx.burst(pos, (150, 112, 74), 28, 340)
        game.fx.spark_burst(pos, (215, 185, 125), 15, 380)
        game.fx.ring(pos, (200, 150, 90))
        game.shake(8)
        audio.play('hit', 0.5)
        r = self.max_r * 2.2
        for p in game.players:
            if p.dead or getattr(p, 'down', False):
                continue
            if p.pos.distance_to(pos) < r + p.max_r:
                p.hurt(game, safe_norm(p.pos - pos), C.CENT_ERUPT_DMG)

    def _ai_grapple(self, dt, game, target):
        """POLVO: an anti-kite grappler (Gungeon Gripmaster). It closes to mid
        range, roots, and reaches ALL arms toward you (a >0.7s telegraph); if you
        are still in reach at the snap it reels you in and slows you. Fleeing the
        wind-up is the counter -- so it punishes lingering at its doorstep."""
        to = safe_norm(target.pos - self.pos)
        dist = target.pos.distance_to(self.pos)
        if dist < (self.max_r + target.max_r) and self.attack_cd <= 0:
            self._contact(game, target)
        if self.grapple_t > 0:                     # winding up: arms reach in
            self.grapple_t -= dt
            self.arm_target = Vector2(target.pos)
            if random.random() < dt * 20:
                game.fx.burst(self.spine.joints[0], palette.lighten(self.color, 0.3), 1, 60)
            if self.grapple_t <= 0:
                self.arm_target = None
                if dist < C.OCTO_GRAB_RANGE:        # snap!
                    pull = min(C.OCTO_PULL_DIST, dist - self.max_r)
                    target.pos += safe_norm(self.pos - target.pos) * max(0, pull)
                    target.apply_slow(C.OCTO_SLOW_MUL, C.OCTO_SLOW_TIME)
                    self.grabbed = target
                    self.grab_show = C.OCTO_GRAB_SHOW
                    game.fx.spark_burst(target.pos, self.color, 12, 280)
                    game.shake(5)
                    audio.play('hit', 0.45)
            return to * 0.08, 0.0                   # rooted, mantle exposed
        self.arm_target = None
        if self.grapple_cd > 0:
            self.grapple_cd -= dt
        elif dist < C.OCTO_GRAB_RANGE:
            self.grapple_t = C.OCTO_WINDUP
            self.grapple_cd = C.OCTO_CD
        return to, 1.0                              # commit to closing (it is slow anyway)

    def _apply_mood_pose(self):
        """Personality via animation (plans/01 #11): bias the SAME tail spring
        that already draws the tail by the boss's current mood -- calm stays
        loose, enraged/cornered snap back faster and read tense, with zero
        new state or draw calls."""
        mult = BOSS_MOOD_SPRING_MULT.get(self.boss_ai.mood, 1.0)
        if self.tail_spring is not None:
            self.tail_spring.stiffness = TAIL_SPRING_STIFFNESS * mult

    def explode(self, game):
        """Bomber blast: one hit per victim, radius damage, then the bomber dies.

        ``_blown`` is set *first*: this ends by calling ``die``, and ``die``
        detonates unexploded bombers -- without the flag the two call each other.
        """
        if self._blown:
            return
        self._blown = True
        pos = Vector2(self.pos)
        r = C.BOMBER_RADIUS
        game.fx.burst(pos, (255, 180, 90), 34, 420)
        game.fx.spark_burst(pos, (255, 240, 180), 18, 480)
        game.fx.ring(pos, (255, 140, 70))
        game.shake(11)
        audio.play('hit', 0.7)
        for p in game.players:
            if p.dead or p.down:
                continue
            d = p.pos.distance_to(pos)
            if d < r + p.max_r:
                # falloff so the edge of the blast is a graze, not a full hit
                f = 1.0 - clamp((d - p.max_r) / max(1.0, r), 0, 1) * 0.55
                p.hurt(game, safe_norm(p.pos - pos), C.BOMBER_DMG * f)
        for e in game.enemies:      # friendly fire: bombers thin their own horde
            if e is self or e.dead:
                continue
            if e.pos.distance_to(pos) < r + e.max_r:
                e.take_hit(game, safe_norm(e.pos - pos), C.BOMBER_SPLASH)
        if not self.dead:
            self.die(game)

    def _hop(self, dt):
        # frogs: periodic forward hops instead of a smooth glide. The tell is
        # the LEGS gathering in under the body (leg_pull), not a body-only
        # squash -- a squash-only cue read as "wobbling side to side" since
        # nothing else in the silhouette visibly moved (feedback: the width
        # change alone wasn't legible as "about to jump").
        self.wander_t -= dt
        if 0 < self.wander_t < 0.18:           # about to launch -- gather in
            self.leg_pull = approach(self.leg_pull, 0.55, 16, dt)
            self.squat_bias = 0.85
        if self.wander_t <= 0:
            self.wander_t = random.uniform(0.7, 1.3)
            self.wander = random_dir()
            self.vel += self.wander * self.max_speed * 1.4
            self.leg_pull = 1.6                # legs kick out on launch
            self.squat_bias = 1.4              # pop out of the crouch on launch
        return Vector2()

    def _draw_weakpoint(self, surf, cam):
        """Mark the head: it is the weak point (crit) and where aiming pays off.

        A crosshair read as UI stuck on the creature. This is purely organic
        instead: a warm halo that breathes *behind* the head, so it glows out
        around the silhouette without painting over the eyes.
        """
        if self.kind != 'enemy' or getattr(self, 'is_boss', False):
            return
        head = self.spine.joints[0]
        if not cam.visible(head, 40):
            return
        sp = cam.w2s(head)
        r = max(6, int(self.spine.radii[0] * 2.1 * cam.zoom))
        pulse = 0.55 + 0.45 * math.sin(self.wobble * 2.4)
        palette.glow(surf, sp, r, palette.lighten(self.color, 0.5),
                     0.30 + 0.16 * pulse)

    def draw(self, surf, cam):
        if self.life is not None and self.life < 5.0:
            # blink faster as the ally is about to leave
            if int(self.life * (12 if self.life < 2 else 6)) % 2 == 0:
                return
        if self.burrowed:                    # underground: only the mound + warning
            self._draw_burrow(surf, cam)
            return
        if self.fuse > 0:
            self._draw_fuse(surf, cam)
        if self.burrow_state == 'digging':
            self._draw_dig_hole(surf, cam)   # behind the body: a growing pit
        if self.champion is not None:
            self._draw_champion_aura(surf, cam)
        if self.boss_ai is not None:
            self.boss_ai.draw(surf, cam)     # windup telegraph, behind the body
        self._draw_weakpoint(surf, cam)      # behind the body: reads as a halo
        super().draw(surf, cam)
        self._draw_health(surf, cam)
        if self.champion is not None:
            self._draw_champion_name(surf, cam)

    def _draw_dig_hole(self, surf, cam):
        """The pit opening under a diving centipede -- so the dive reads as
        burrowing, not a blink-out. Grows over the dig telegraph."""
        f = 1.0 - clamp(self.burrow_t / max(1e-4, C.CENT_DIG_TIME), 0, 1)   # 0->1
        sp = cam.w2s(self.pos)
        r = int(self.max_r * (1.4 + 0.9 * f) * cam.zoom)
        pygame.draw.circle(surf, (44, 32, 22), sp, r)                      # dark pit
        pygame.draw.circle(surf, (150, 112, 74), sp, r, max(1, int(2 * cam.zoom)))  # rim
        palette.glow(surf, sp, int(r * 1.2), (150, 112, 74), 0.18 + 0.2 * f)

    def _draw_burrow(self, surf, cam):
        """Underground: a traveling dirt mound + the ring where it will erupt.

        The ring is the fair telegraph -- it fills as the surfacing nears, so the
        player can read where to NOT be standing (the whole point of the ambush)."""
        sp = cam.w2s(self.pos)
        r = max(3, int(self.max_r * 0.9 * cam.zoom))
        bob = int(math.sin(self.wobble * 3.0) * self.max_r * 0.15 * cam.zoom)
        pygame.draw.circle(surf, (120, 90, 60), (sp[0], sp[1] + bob), r)   # mound
        pygame.draw.circle(surf, (150, 112, 74), (sp[0], sp[1] + bob), r,
                           max(1, int(2 * cam.zoom)))
        tp = cam.w2s(self.dive_to)
        f = 1.0 - clamp(self.burrow_t / max(1e-4, C.CENT_UNDER_TIME), 0, 1)   # 0->1
        rr = max(4, int(self.max_r * 2.2 * cam.zoom))
        warn = (220, 95, 70)
        blink = 0.55 + 0.45 * math.sin(f * f * 40)
        pygame.draw.circle(surf, warn, tp, rr, max(1, int((1 + 2 * f) * cam.zoom)))
        pygame.draw.circle(surf, warn, tp, max(1, int(rr * f)))            # fills in
        palette.glow(surf, tp, int(rr * 1.2), warn, (0.14 + 0.3 * f) * blink)

    def _draw_fuse(self, surf, cam):
        """Draw the blast footprint while the fuse burns.

        The timing rule (>=27 frames of warning) is only half of a telegraph --
        the first version had the time but nothing to *see*, just a few sparks,
        so the player had no way to act on it. Showing the actual radius on the
        ground answers the only question that matters: am I standing in it?
        """
        sp = cam.w2s(self.pos)
        r = int(C.BOMBER_RADIUS * cam.zoom)
        f = 1.0 - clamp(self.fuse / max(1e-4, C.BOMBER_FUSE), 0, 1)   # 0 -> 1
        # flashes faster the closer it gets: reads as urgency without a timer
        blink = pulse(f * f, 46)
        col = palette.mix((255, 170, 60), (255, 250, 220), f)
        palette.glow(surf, sp, r, col, (0.16 + 0.30 * f) * (0.55 + 0.45 * blink))
        pygame.draw.circle(surf, col, sp, r, max(2, int((1 + 2 * f) * cam.zoom)))
        # the body swells and whitens as it is about to go
        palette.glow(surf, cam.w2s(self.spine.joints[0]),
                     int(self.max_r * (1.6 + 1.4 * f) * cam.zoom), col,
                     0.35 + 0.4 * blink)

    def _draw_champion_aura(self, surf, cam):
        """Behind the body, breathing: says 'elite' before you are in its range."""
        if self.champion_vis <= 0.02:
            return
        sp = cam.w2s(self.pos)
        r = max(10, int(self.max_r * 2.6 * cam.zoom))
        palette.glow(surf, sp, r, self.champion.color(),
                     (0.30 + 0.16 * pulse(self.wobble, 2.0)) * self.champion_vis)

    def _draw_champion_name(self, surf, cam):
        """A champion has to be *identifiable*, or the player cannot learn it.

        Sits above the health bar, and only on screen -- an off-screen name would
        just be text floating at the edge of the world.
        """
        if not self.on_screen or cam.zoom < 0.5 or self.champion_vis <= 0.05:
            return
        head = self.spine.joints[0]
        sp = cam.w2s(head + Vector2(0, -self.max_r * 2.0))
        # fade the label by mixing toward the ground, not with alpha: ui.text
        # hands back a shared cached surface, so set_alpha would tint every other
        # champion drawing the same string this frame
        col = palette.mix((48, 52, 62), self.champion.color(), self.champion_vis)
        ui.text(surf, fonts.get(13), self.champion_name,
                (sp[0], sp[1] - 16), col, align='center')

    def _draw_health(self, surf, cam):
        """Small bar above the head, only while hurt -- keeps the screen clean."""
        if getattr(self, 'is_boss', False):      # bosses have the big bar up top
            return
        mx = max(1, getattr(self, 'max_hp', self.hp))
        if self.hp >= mx or self.hp <= 0:
            return
        f = clamp(self.hp / mx, 0, 1)
        head = self.spine.joints[0]
        sp = cam.w2s(head + Vector2(0, -self.max_r * 2.0))
        w = max(16, int(self.max_r * 2.2 * cam.zoom))
        h = max(3, int(4 * cam.zoom))
        x = sp[0] - w // 2
        col = palette.health_color(f)
        pygame.draw.rect(surf, (18, 16, 26), (x - 1, sp[1] - 1, w + 2, h + 2),
                         border_radius=3)
        pygame.draw.rect(surf, col, (x, sp[1], int(w * f), h), border_radius=2)

    def _contact(self, game, target):
        self.attack_cd = 0.8
        if getattr(target, 'dashing', False):
            self.take_hit(game, safe_norm(self.pos - target.pos), 3)
            return
        away = safe_norm(target.pos - self.pos)
        if not hasattr(target, 'hurt'):           # an allied creature, not the player
            target.take_hit(game, away, 2 if self.max_r > 25 else 1)
            if self.genome.tail == 'sting':
                target.apply_slow(C.STING_SLOW, C.STING_SLOW_TIME)
            return
        else:
            landed = target.hurt(game, away, contact_damage(self.max_r, game.wave))
            # The sting only slows on a hit that CONNECTED. It used to fire even
            # when hurt() bounced off i-frames, and its 1.4s duration was longer
            # than the 0.8s attack cooldown -- so a single scorpion kept the
            # player at 50% speed 59% of the time, with no damage number to
            # explain why. Same shape as the Acido and venom-puddle bugs:
            # an effect that lasts longer than its own reapplication interval
            # is permanent by construction.
            if landed and self.genome.tail == 'sting':
                target.apply_slow(C.STING_SLOW, C.STING_SLOW_TIME)
            thorns = getattr(target, 'thorns', 0)
            if thorns:                            # attacker gets pricked
                self.take_hit(game, safe_norm(self.pos - target.pos), thorns)

    def _death_item_fx(self, game):
        """On-death effects owned by player items (Estopim, Contagio).

        One place, not one per item: both need "who died, where, and was it
        poisoned", and splitting that across call sites is how the dash ended up
        with two copies of its damage rule.
        """
        blast = any(p.kill_blast for p in game.players if not p.dead)
        spread = any(p.poison_spreads for p in game.players if not p.dead)
        if not (blast or spread):
            return
        pos = Vector2(self.pos)
        if blast:
            game.fx.burst(pos, (255, 170, 90), 18, 300)
            game.fx.ring(pos, (255, 150, 80))
        poisoned = self.poison_t > 0
        for e in game.enemies:
            if e is self or e.dead:
                continue
            d = e.pos.distance_to(pos)
            if blast and d < C.ITEM_KILL_BLAST_R + e.max_r:
                e.take_hit(game, safe_norm(e.pos - pos), C.ITEM_KILL_BLAST_DMG)
            if spread and poisoned and d < C.ITEM_SPREAD_R + e.max_r:
                e.apply_poison(self.poison_dps, 2.6)

    def take_hit(self, game, direction, dmg):
        if self.marked:                  # Presa Marcada, consumed on use
            self.marked = False
            dmg *= C.CRIT_MULT
            game.crit_fx(self.spine.joints[0])
        if self.front_armor > 0 and direction.length_squared() > 1e-6:
            # `direction` is the knockback, i.e. it points AWAY from the attacker,
            # so the attacker sits at -direction. Blocking the front makes going
            # around (or dashing straight through) the counter-play -- which is
            # what the dash already wants you to do.
            if self.spine.head_dir().dot(-safe_norm(direction)) > 0.25:
                dmg = dmg * (1.0 - self.front_armor)
                game.fx.spark_burst(self.spine.joints[0], (215, 225, 255), 5, 180)
        self.hit_flash = 1.0
        self.vel = direction * 200 * self.genome.knockback   # heavy bruisers barely budge
        game.fx.burst(self.pos, self.color, 10, 180)
        game.fx.spark_burst(self.pos, C.COL_FX_SPARK, 9, 300)
        self.hp -= dmg
        if self.hp <= 0:
            self.die(game)

    def die(self, game):
        self.dead = True
        # A bomber killed before its fuse runs out still goes off -- otherwise the
        # safe play is to shoot it from range and its whole threat evaporates.
        # `_blown` guards the recursion: explode() ends by calling die().
        if self.genome.behavior == 'bomber' or self.death_blast:
            self.explode(game)          # no-op if it already went off (_blown)
        if getattr(self, 'is_boss', False):
            game.punch(0.22, 20, flash=0.9)      # boss death: big stop + flash
            game.fx.spark_burst(self.pos, C.COL_FX_SPARK, 46, 520)
            game.fx.ring(self.pos, (255, 200, 140))
        audio.play('kill', 0.8)
        game.fx.burst(self.pos, self.color, 22, 240)
        game.fx.spark_burst(self.pos, palette.lighten(self.color, 0.4), 18, 380)
        game.fx.ring(self.pos, self.color)
        if self.kind == 'enemy':
            game.add_combo()
            game.add_score(self.score_value)
            game.add_pollen(max(1, self.score_value // 12))
            game.kills += 1
            game.give_xp(self.xp_value)
            from . import characters
            from . import items as itemlib
            for p in game.players:            # LARVA feeds on the whole run
                if p.dead:
                    continue
                characters.larva_growth(p, game)
                itemlib.add_charge(p)         # kills charge the active item
                if p.kill_heal:
                    p.health = min(p.max_health, p.health + C.ITEM_KILL_HEAL)
            # A kill trickles energy back to the NEAREST player (not all, in co-op),
            # so an aggressive combo self-sustains its dash/tongue/whip a little.
            killer = game.nearest_player(self.pos)
            if killer is not None and not killer.dead:
                killer.energy = min(killer.max_energy,
                                    killer.energy + C.KILL_ENERGY)
            self._death_item_fx(game)
            if random.random() < 0.15:
                game.spawn_fruit(self.pos)
        # DIVISOR (Blobulon/Fistula): burst into two smaller copies. Queued, not
        # appended, so it can't extend the loop that is killing this one.
        if self.death_split and self.species and self.split_gen > 0:
            self._do_split(game)

    def _do_split(self, game):
        from . import species as splib
        game.fx.ring(self.pos, self.color)
        for k in range(self.split_count):
            child = splib.make(self.species, self.pos)
            child.genome.size = max(0.4, self.genome.size * C.CHAMP_SPLIT_SIZE)
            child.rebuild_body()
            child.hp = max(1, int(self.max_hp * C.CHAMP_SPLIT_HP))
            child.max_hp = child.hp
            child.split_gen = self.split_gen - 1
            child.death_split = child.split_gen > 0
            child.base_color = child.color
            child.pos = self.pos + vfrom_angle(k * 180 + random.uniform(-40, 40), self.max_r)
            child.vel = random_dir(child.max_speed * 0.8)
            game.spawn_enemy(child)
