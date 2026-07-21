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


def shockwave(boss, game, target):
    """Instant AoE centred on the boss -- no projectile, just a ring of hurt.
    Tail-slam-style attacks (Rei Lagarto) use this: the telegraph already drew
    the exact radius, so at fire time it's a plain distance check."""
    for p in game.players:
        if p.dead or p.down:
            continue
        if p.pos.distance_to(boss.pos) < C.BOSS_SHOCKWAVE_RADIUS + p.max_r * 0.4:
            p.hurt(game, safe_norm(p.pos - boss.pos), C.BOSS_SHOCKWAVE_DMG)
    game.fx.ring(boss.pos, boss.color)
    game.fx.ring(boss.pos, palette.lighten(boss.color, 0.3))
    game.shake(8)
    audio.play('hit', 0.5)


def spiral_pattern(boss, game, target):
    """Kick off a rotating spray -- ticked per-frame by ``_tick_spiral`` like
    ``aimed_barrage``/``_tick_barrage``, so the spiral keeps turning while the
    boss is free to do anything else (it's not a blocking loop)."""
    boss._spiral_left = C.BOSS_SPIRAL_SHOTS
    boss._spiral_ang = random.uniform(0, 360)
    boss._spiral_cd = 0.0


def _tick_spiral(boss, game):
    if getattr(boss, '_spiral_left', 0) <= 0:
        return
    boss._spiral_cd -= game.dt_last
    if boss._spiral_cd > 0:
        return
    boss._spiral_left -= 1
    boss._spiral_cd = C.BOSS_SPIRAL_GAP
    mouth = boss.spine.joints[0]
    aim = mouth + vfrom_angle(boss._spiral_ang, 100)
    boss._spiral_ang = (boss._spiral_ang + C.BOSS_SPIRAL_TURN) % 360
    pr = game_spit(mouth, aim, boss.color, dmg=C.BOSS_SPIRAL_DMG,
                   effect=None, speed=C.BOSS_SPIRAL_SPEED, radius=7)
    game.spawn_projectile(pr)


def charge_attack(boss, game, target):
    """Not an instant fire -- flips the FSM into 'charging' (see ``BossAI.tick``)
    so the boss itself becomes the hazard for a beat, Gurdy-Jr/Chub style."""
    boss._charge_dir = safe_norm(target.pos - boss.pos)


PATTERNS = {
    'radial': dict(fn=radial_burst, windup=C.BOSS_RADIAL_WINDUP, telegraph='radial'),
    'fan': dict(fn=fan_shot, windup=C.BOSS_FAN_WINDUP, telegraph='fan'),
    'barrage': dict(fn=aimed_barrage, windup=C.BOSS_BARRAGE_WINDUP, telegraph='line'),
    'summon': dict(fn=summon_adds, windup=C.BOSS_SUMMON_WINDUP, telegraph='horn'),
    'shockwave': dict(fn=shockwave, windup=C.BOSS_SHOCKWAVE_WINDUP, telegraph='shockwave'),
    'spiral': dict(fn=spiral_pattern, windup=C.BOSS_SPIRAL_WINDUP, telegraph='spiral'),
    'charge': dict(fn=charge_attack, windup=C.BOSS_CHARGE_WINDUP, telegraph='line', charge=True),
}


# --------------------------------------------------------------------------- #
#  Personality: mood -> speed / pattern weight / glow colour / tell length     #
# --------------------------------------------------------------------------- #

class BossPersonality:
    """How a boss REACTS. A generic default works for any boss; a named boss
    (Rei Lagarto) can pass its own to bias which patterns it favours."""

    def __init__(self, pattern_weights=None):
        self.mood_speed = {
            'calm': 1.0, 'agitated': 1.3, 'enraged': 1.6,
            'frustrated': 1.4, 'cornered': 0.8,
        }
        self.pattern_weights = pattern_weights or {}
        self.mood_colors = {
            'calm': None,
            'agitated': (255, 180, 50),
            'enraged': (255, 50, 50),
            'frustrated': (200, 50, 255),
            'cornered': (50, 100, 255),
        }
        self.tell_mult = {'enraged': 0.65, 'agitated': 0.8}

    def windup_mult(self, mood):
        return self.tell_mult.get(mood, 1.0)

    def glow_color(self, mood, base_color):
        mood_color = self.mood_colors.get(mood)
        return palette.mix(base_color, mood_color, 0.4) if mood_color else base_color

    def weight(self, pattern_id, mood):
        return self.pattern_weights.get(pattern_id, {}).get(mood, 1.0)


def default_personality():
    return BossPersonality()


# --------------------------------------------------------------------------- #
#  Rei Lagarto (plans/03, first authored boss, onda 5): CicatriZ mechanic --   #
#  every 25% HP lost, a scarred patch (slow + tick damage) appears underfoot;  #
#  it clears whenever the fight moves to the next phase.                      #
# --------------------------------------------------------------------------- #

def spawn_scar(boss, game):
    from . import weapons
    pos = boss.pos + vfrom_angle(random.uniform(0, 360), boss.max_r * 0.6)
    p = weapons.Puddle(pos, boss.max_r * 0.9, C.KING_SCAR_DMG, C.KING_SCAR_LIFE,
                       22, hostile=True, tick=0.5,
                       slow=(C.KING_SCAR_SLOW, C.KING_SCAR_TIME))
    game.spawn_puddle(p)
    game.fx.burst(pos, (150, 90, 50), 10, 140)
    return p


def king_phases():
    """3 fases (66/33 -- doc's own thresholds for this boss). Fase 2 adds
    Radial Burst (1 thing); fase 3 swaps Fan for Spiral + faster cd (2 things)."""
    return [
        dict(hp_frac=1.0, patterns=['fan', 'shockwave', 'charge'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['fan', 'shockwave', 'charge', 'radial'], cd_mul=1.0),
        dict(hp_frac=0.33, patterns=['spiral', 'shockwave', 'charge', 'radial'], cd_mul=0.7),
    ]


def king_personality():
    """Orgulhoso: prefere a investida quando encurralado (não foge, comete);
    fica mais raivoso, não mais covarde."""
    return BossPersonality(pattern_weights={
        'charge': {'cornered': 2.2, 'enraged': 1.6},
        'shockwave': {'agitated': 1.5, 'calm': 1.0},
        'spiral': {'enraged': 1.6},
    })


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
    def __init__(self, boss, phases=None, personality=None, name=None, on_phase=None):
        self.boss = boss
        self.phases = phases or default_phases()
        self.personality = personality or default_personality()
        self.name = name
        self.on_phase = on_phase   # optional (boss, phase_i) hook -- per-boss mechanics
        self.phase_i = 0
        self.state = 'intro'
        self.t = C.BOSS_INTRO_TIME
        self.cd = random.uniform(C.BOSS_CD_MIN, C.BOSS_CD_MAX)
        self.pattern_id = None
        self.summon_cd = 0.0
        self.mood = 'calm'
        self.no_hit_t = 0.0        # time since this boss last connected -- frustration
        self.scar_thresholds = None   # e.g. [0.75, 0.5, 0.25] -- opt-in (Rei Lagarto)
        self.scars = []
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
            if self.scars:                     # scars don't survive a phase change
                for s in self.scars:
                    s.dead = True
                self.scars = []
            if self.on_phase:
                self.on_phase(b, self.phase_i)

    def _update_mood(self, dt, target):
        if target is None:
            self.mood = 'calm'
            return
        self.no_hit_t += dt
        dist = target.pos.distance_to(self.boss.pos)
        frac = self.boss.hp / max(1, self.boss.max_hp)
        if dist < C.BOSS_CORNERED_DIST:
            self.mood = 'cornered'
        elif frac < 0.33:
            self.mood = 'enraged'
        elif frac < 0.66:
            self.mood = 'agitated'
        elif self.no_hit_t > C.BOSS_FRUSTRATION_SEC:
            self.mood = 'frustrated'
        else:
            self.mood = 'calm'

    def _choose_pattern(self, pats):
        weights = [self.personality.weight(p, self.mood) for p in pats]
        return random.choices(pats, weights=weights, k=1)[0]

    def tick(self, dt, game):
        b = self.boss
        game.dt_last = dt          # aimed_barrage's/spiral's per-frame tick reads this
        _tick_barrage(b, game)
        _tick_spiral(b, game)
        self.summon_cd = max(0.0, self.summon_cd - dt)
        self._maybe_advance_phase()
        if self.scar_thresholds:
            frac = b.hp / max(1, b.max_hp)
            while self.scar_thresholds and frac <= self.scar_thresholds[0]:
                self.scar_thresholds.pop(0)
                self.scars.append(spawn_scar(b, game))
        target = game.nearest_player(b.pos)
        self._update_mood(dt, target)
        speed_mul = self.personality.mood_speed.get(self.mood, 1.0)
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
                pid = self._choose_pattern(pats) if pats else 'fan'
                self.pattern_id = pid
                self.state = 'windup'
                self.t = PATTERNS[pid]['windup'] * self.personality.windup_mult(self.mood)
                self._windup_target = Vector2(target.pos)
                return Vector2(), 0.0
            speed = C.BOSS_APPROACH_SPEED * speed_mul if dist > 240 else 0.0
            return to, speed

        if self.state == 'windup':
            self.t -= dt
            if self.t <= 0:
                pat = PATTERNS[self.pattern_id]
                pat['fn'](b, game, target)
                if self.pattern_id == 'summon':
                    self.summon_cd = C.BOSS_SUMMON_CD
                if pat.get('charge'):
                    self.state = 'charging'
                    self.t = C.BOSS_CHARGE_TIME
                else:
                    self.state = 'recover'
                    self.t = 0.5
            return Vector2(), 0.0

        if self.state == 'charging':
            self.t -= dt
            if dist < (b.max_r + target.max_r) * 1.1 and b.attack_cd <= 0:
                b._contact(game, target)
                self.no_hit_t = 0.0
            if self.t <= 0:
                self.state = 'recover'
                self.t = 0.4
                return Vector2(), 0.0
            return getattr(b, '_charge_dir', to), C.BOSS_CHARGE_SPEED_MULT

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
        base_color = self.personality.glow_color(self.mood, b.color)
        if self.state == 'intro' or self.state == 'transition':
            f = clamp(self.t / (C.BOSS_INTRO_TIME if self.state == 'intro'
                                 else C.BOSS_TRANSITION_TIME), 0, 1)
            sp = cam.w2s(b.pos)
            col = palette.lighten(base_color, 0.5)
            palette.glow(surf, sp, int(b.max_r * (2.2 + 1.4 * f) * cam.zoom), col, 0.35 + 0.25 * f)
            return
        if self.state == 'charging':
            sp = cam.w2s(b.spine.joints[0])
            aim = b.spine.joints[0] + getattr(b, '_charge_dir', Vector2(1, 0)) * 260
            col = palette.lighten(base_color, 0.4)
            import pygame
            pygame.draw.line(surf, col, sp, cam.w2s(aim), max(1, int(3 * cam.zoom)))
            return
        if self.state != 'windup' or not self.pattern_id:
            return
        kind = PATTERNS[self.pattern_id]['telegraph']
        mouth = b.spine.joints[0]
        sp = cam.w2s(mouth)
        windup_dur = PATTERNS[self.pattern_id]['windup'] * self.personality.windup_mult(self.mood)
        prog = 1.0 - clamp(self.t / max(1e-4, windup_dur), 0, 1)   # 0 -> 1
        blink = 0.5 + 0.5 * __import__('math').sin(prog * prog * 40)
        col = palette.lighten(base_color, 0.35)
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
        elif kind == 'shockwave':
            r = int(C.BOSS_SHOCKWAVE_RADIUS * cam.zoom * (0.3 + 0.7 * prog))
            pygame.draw.circle(surf, col, sp, r, max(1, int((1 + 2 * prog) * cam.zoom)))
            palette.glow(surf, sp, r, col, (0.14 + 0.22 * prog) * (0.5 + 0.5 * blink))
        elif kind == 'spiral':
            n_spokes = 8
            rr = int(b.max_r * (1.5 + prog * 2) * cam.zoom)
            for i in range(n_spokes):
                ang = (360 / n_spokes) * i + prog * 300
                end = mouth + vfrom_angle(ang, rr / max(cam.zoom, 1e-4))
                pygame.draw.line(surf, col, sp, cam.w2s(end), max(1, int(2 * cam.zoom)))
