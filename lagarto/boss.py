"""Boss framework (Fase 5): a phase-based attack-pattern engine layered on any
existing enemy body (``rounds._spawn_boss`` just scales up a themed species) --
so ten different "fights" can share one engine and differ only by DATA (which
patterns each phase rolls), the same split ``champions.py`` uses between
identity and mechanics.

Timeline, per boss:

    intro (invulnerable, ~1s) -> [approach -> windup -> attack -> recover] x N
        -> phase transition (invulnerable, ~1s, swaps the pattern list)
        -> ... -> death

Patterns are functions ``(boss, game, target) -> None`` that spawn Projectiles
through the existing ``game.spawn_projectile`` pipeline -- no new projectile
type, just new arrangements of the one every ranged enemy already uses. Every
pattern telegraphs (>=27 frames, drawn on screen, not just timed) before it
fires -- the phase-2 lesson ("telegrafo é tempo E visibilidade") applies here
at boss scale too.

A phase change swaps *at most two things* (its pattern list + one numeric
dial), so the player can attribute what changed instead of relearning a new
fight from scratch every threshold.
"""

import random
from pygame import Vector2

from . import audio
from . import config as C
from . import palette
from .mathutil import safe_norm, vfrom_angle, clamp
from .projectile import spit as game_spit


# --------------------------------------------------------------------------- #
#  Patterns: (boss, game, target) -> fires projectiles / spawns adds          #
# --------------------------------------------------------------------------- #

def radial_burst(boss, game, target):
    """A full ring of shots, all at once -- the "get away from me" pattern."""
    mouth = boss.spine.joints[0]
    n = C.BOSS_RADIAL_COUNT
    for i in range(n):
        ang = (360.0 / n) * i
        aim = mouth + vfrom_angle(ang, 100)
        pr = game_spit(mouth, aim, boss.color, dmg=C.BOSS_RADIAL_DMG,
                       effect=None, speed=C.BOSS_RADIAL_SPEED, radius=8)
        game.spawn_projectile(pr)
    game.fx.ring(boss.pos, boss.color)
    game.fx.spark_burst(mouth, palette.lighten(boss.color, 0.3), 16, 260)
    audio.play('w_spit', 0.5)


def fan_shot(boss, game, target):
    """A cone of shots toward the player -- dodge sideways, not backward."""
    mouth = boss.spine.joints[0]
    n = C.BOSS_FAN_COUNT
    base = safe_norm(target.pos - mouth)
    for i in range(n):
        t = (i / max(1, n - 1)) - 0.5              # -0.5 .. 0.5
        aim = mouth + base.rotate(t * C.BOSS_FAN_SPREAD) * 100
        pr = game_spit(mouth, aim, boss.color, dmg=C.BOSS_FAN_DMG,
                       effect=None, speed=C.BOSS_FAN_SPEED, radius=8)
        game.spawn_projectile(pr)
    game.fx.spark_burst(mouth, boss.color, 10, 240)
    audio.play('w_spit', 0.45)


def aimed_barrage(boss, game, target):
    """A few shots aimed with lead at where the player is HEADING."""
    mouth = boss.spine.joints[0]
    lead = target.pos + target.vel * 0.35
    boss._barrage_left = C.BOSS_BARRAGE_SHOTS
    boss._barrage_aim = lead
    boss._barrage_cd = 0.0


def _tick_barrage(boss, game):
    """Called every frame while a barrage is in flight (set by aimed_barrage)."""
    if getattr(boss, '_barrage_left', 0) <= 0:
        return
    boss._barrage_cd -= game.dt_last
    if boss._barrage_cd > 0:
        return
    boss._barrage_left -= 1
    boss._barrage_cd = C.BOSS_BARRAGE_GAP
    mouth = boss.spine.joints[0]
    pr = game_spit(mouth, boss._barrage_aim, boss.color, dmg=C.BOSS_BARRAGE_DMG,
                   effect=None, speed=C.BOSS_BARRAGE_SPEED, radius=7)
    game.spawn_projectile(pr)
    game.fx.spark_burst(mouth, boss.color, 5, 200)
    audio.play('w_spit', 0.35)


def summon_adds(boss, game, target):
    """Call in reinforcements from the round's own theme pool (a real cost:
    it spends a window where the boss does nothing else, and the adds count
    against the round's cap like anything else)."""
    from . import species
    from . import rounds as roundslib
    pool = roundslib.THEMES.get(game.rounds.theme, {}).get('pool', species.ENEMY_SPECIES)
    for _ in range(C.BOSS_SUMMON_COUNT):
        key = random.choice(pool)
        pos = boss.pos + vfrom_angle(random.uniform(0, 360), boss.max_r * 1.6)
        e = species.make(key, pos)
        game.spawn_enemy(e)
        game.fx.ring(pos, boss.color)
    game.fx.spark_burst(boss.pos, palette.lighten(boss.color, 0.4), 20, 300)
    audio.play('nest', 0.6)


PATTERNS = {
    'radial': dict(fn=radial_burst, windup=C.BOSS_RADIAL_WINDUP, telegraph='radial'),
    'fan': dict(fn=fan_shot, windup=C.BOSS_FAN_WINDUP, telegraph='fan'),
    'barrage': dict(fn=aimed_barrage, windup=C.BOSS_BARRAGE_WINDUP, telegraph='line'),
    'summon': dict(fn=summon_adds, windup=C.BOSS_SUMMON_WINDUP, telegraph='horn'),
}


# --------------------------------------------------------------------------- #
#  Phase kits: which patterns are live at each HP threshold                    #
# --------------------------------------------------------------------------- #

def default_phases():
    """A generic 3-phase kit any boss body can use. Phase 2 adds 'summon' (one
    new thing); phase 3 adds 'barrage' and hands out shorter cooldowns (the
    other thing) -- never more than two changes per threshold."""
    return [
        dict(hp_frac=1.0, patterns=['radial', 'fan'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['radial', 'fan', 'summon'], cd_mul=1.0),
        dict(hp_frac=0.33, patterns=['fan', 'barrage', 'summon'], cd_mul=0.75),
    ]


# --------------------------------------------------------------------------- #
#  The FSM itself                                                             #
# --------------------------------------------------------------------------- #

class BossAI:
    def __init__(self, boss, phases=None):
        self.boss = boss
        self.phases = phases or default_phases()
        self.phase_i = 0
        self.state = 'intro'
        self.t = C.BOSS_INTRO_TIME
        self.cd = random.uniform(C.BOSS_CD_MIN, C.BOSS_CD_MAX)
        self.pattern_id = None
        self.summon_cd = 0.0
        boss.boss_invuln = True

    def phase(self):
        return self.phases[self.phase_i]

    def _maybe_advance_phase(self):
        b = self.boss
        frac = b.hp / max(1, b.max_hp)
        while self.phase_i + 1 < len(self.phases) and frac <= self.phases[self.phase_i + 1]['hp_frac']:
            self.phase_i += 1
            self.state = 'transition'
            self.t = C.BOSS_TRANSITION_TIME
            b.boss_invuln = True
            b.hit_flash = 1.0
            self.pattern_id = None

    def tick(self, dt, game):
        b = self.boss
        game.dt_last = dt          # aimed_barrage's per-frame tick reads this
        _tick_barrage(b, game)
        self.summon_cd = max(0.0, self.summon_cd - dt)
        self._maybe_advance_phase()
        target = game.nearest_player(b.pos)
        if target is None:
            return Vector2(), 0.0

        if self.state == 'intro':
            self.t -= dt
            if self.t <= 0:
                self.state = 'approach'
                b.boss_invuln = False
            return Vector2(), 0.0

        if self.state == 'transition':
            self.t -= dt
            if self.t <= 0:
                self.state = 'approach'
                b.boss_invuln = False
                self.cd = random.uniform(C.BOSS_CD_MIN, C.BOSS_CD_MAX) * self.phase()['cd_mul']
            return safe_norm(target.pos - b.pos) * 0.1, 0.15

        to = safe_norm(target.pos - b.pos)
        dist = target.pos.distance_to(b.pos)

        if self.state == 'approach':
            self.cd -= dt
            if self.cd <= 0:
                pats = list(self.phase()['patterns'])
                if 'summon' in pats and self.summon_cd > 0:
                    pats.remove('summon')          # on cooldown -- don't roll it
                pid = random.choice(pats) if pats else 'fan'
                self.pattern_id = pid
                self.state = 'windup'
                self.t = PATTERNS[pid]['windup']
                self._windup_target = Vector2(target.pos)
                return Vector2(), 0.0
            speed = C.BOSS_APPROACH_SPEED if dist > 240 else 0.0
            return to, speed

        if self.state == 'windup':
            self.t -= dt
            if self.t <= 0:
                pat = PATTERNS[self.pattern_id]
                pat['fn'](b, game, target)
                if self.pattern_id == 'summon':
                    self.summon_cd = C.BOSS_SUMMON_CD
                self.state = 'recover'
                self.t = 0.5
            return Vector2(), 0.0

        if self.state == 'recover':
            self.t -= dt
            if self.t <= 0:
                self.state = 'approach'
                self.cd = random.uniform(C.BOSS_CD_MIN, C.BOSS_CD_MAX) * self.phase()['cd_mul']
            return Vector2(), 0.0

        return Vector2(), 0.0

    # ---- drawing: the telegraph IS the pattern's real hitbox preview ------- #
    def draw(self, surf, cam):
        b = self.boss
        if self.state == 'intro' or self.state == 'transition':
            f = clamp(self.t / (C.BOSS_INTRO_TIME if self.state == 'intro'
                                 else C.BOSS_TRANSITION_TIME), 0, 1)
            sp = cam.w2s(b.pos)
            col = palette.lighten(b.color, 0.5)
            palette.glow(surf, sp, int(b.max_r * (2.2 + 1.4 * f) * cam.zoom), col, 0.35 + 0.25 * f)
            return
        if self.state != 'windup' or not self.pattern_id:
            return
        kind = PATTERNS[self.pattern_id]['telegraph']
        mouth = b.spine.joints[0]
        sp = cam.w2s(mouth)
        windup_dur = PATTERNS[self.pattern_id]['windup']
        prog = 1.0 - clamp(self.t / max(1e-4, windup_dur), 0, 1)   # 0 -> 1
        blink = 0.5 + 0.5 * __import__('math').sin(prog * prog * 40)
        col = palette.lighten(b.color, 0.35)
        import pygame
        if kind == 'radial':
            r = int(C.BOSS_RADIAL_SPEED * 0.9 * cam.zoom)
            pygame.draw.circle(surf, col, sp, r, max(1, int((1 + 2 * prog) * cam.zoom)))
            palette.glow(surf, sp, r, col, (0.12 + 0.2 * prog) * (0.5 + 0.5 * blink))
        elif kind == 'fan':
            base = safe_norm(self._windup_target - mouth) if hasattr(self, '_windup_target') else Vector2(1, 0)
            for s in (-0.5, 0.5):
                edge = base.rotate(s * C.BOSS_FAN_SPREAD)
                far = mouth + edge * 340
                pygame.draw.line(surf, col, sp, cam.w2s(far), max(1, int((1 + 2 * prog) * cam.zoom)))
        elif kind == 'line':
            aim = getattr(self, '_windup_target', mouth + Vector2(100, 0))
            pygame.draw.line(surf, col, sp, cam.w2s(aim), max(1, int((1 + 3 * prog) * cam.zoom)))
            palette.glow(surf, cam.w2s(aim), int(14 * cam.zoom), col, 0.2 + 0.3 * prog)
        elif kind == 'horn':
            r = int(b.max_r * (1.3 + 0.6 * prog) * cam.zoom)
            palette.glow(surf, sp, r, (255, 226, 90), (0.2 + 0.3 * prog) * (0.5 + 0.5 * blink))
            pygame.draw.circle(surf, (255, 226, 90), sp, r, max(1, int(2 * cam.zoom)))
