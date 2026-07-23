"""Boss attack patterns and phase kits.

A pattern is a plain function ``(boss, game, target) -> None`` that spawns
Projectiles through the existing ``game.spawn_projectile`` pipeline. A phase kit
is just a list of pattern ids per HP threshold -- "boss is data" (see
``lagarto.flow.boss`` for the framework overview).
"""

import random
from pygame import Vector2

from ...audio import engine as audio
from ...core import config as C
from ...core import palette
from ...core.mathutil import safe_norm, vfrom_angle, random_dir
from ...combat.projectile import spit as game_spit

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
    """A cone of shots toward the player -- dodge sideways, not backward.
    Dials come from the pattern dict (Primordial's Massive Fan reuses this
    with a wider/denser dict entry instead of new code)."""
    pat = PATTERNS[boss.boss_ai.pattern_id]
    mouth = boss.spine.joints[0]
    n = pat.get('count', C.BOSS_FAN_COUNT)
    spread = pat.get('spread', C.BOSS_FAN_SPREAD)
    base = safe_norm(target.pos - mouth)
    for i in range(n):
        t = (i / max(1, n - 1)) - 0.5              # -0.5 .. 0.5
        aim = mouth + base.rotate(t * spread) * 100
        pr = game_spit(mouth, aim, boss.color, dmg=pat.get('dmg', C.BOSS_FAN_DMG),
                       effect=None, speed=pat.get('shot_speed', C.BOSS_FAN_SPEED), radius=8)
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
    from ...creatures import species
    from .. import rounds as roundslib
    pool = roundslib.THEMES.get(game.rounds.theme, {}).get('pool', species.ENEMY_SPECIES)
    for _ in range(C.BOSS_SUMMON_COUNT):
        key = random.choice(pool)
        pos = boss.pos + random_dir(boss.max_r * 1.6)
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
    boss is free to do anything else (it's not a blocking loop).

    Dials come from the PATTERN, not hardcoded config: ``deathroll`` reuses
    this exact function with a denser/faster dict entry instead of duplicating
    the tick logic -- "boss is data" applies to variants of one pattern too.
    """
    pat = PATTERNS[boss.boss_ai.pattern_id]
    boss._spiral_left = pat.get('shots', C.BOSS_SPIRAL_SHOTS)
    boss._spiral_ang = random.uniform(0, 360)
    boss._spiral_cd = 0.0
    boss._spiral_turn = pat.get('turn', C.BOSS_SPIRAL_TURN)
    boss._spiral_gap = pat.get('gap', C.BOSS_SPIRAL_GAP)
    boss._spiral_speed = pat.get('shot_speed', C.BOSS_SPIRAL_SPEED)
    boss._spiral_dmg = pat.get('shot_dmg', C.BOSS_SPIRAL_DMG)


def _tick_spiral(boss, game):
    if getattr(boss, '_spiral_left', 0) <= 0:
        return
    boss._spiral_cd -= game.dt_last
    if boss._spiral_cd > 0:
        return
    boss._spiral_left -= 1
    boss._spiral_cd = boss._spiral_gap
    mouth = boss.spine.joints[0]
    aim = mouth + vfrom_angle(boss._spiral_ang, 100)
    boss._spiral_ang = (boss._spiral_ang + boss._spiral_turn) % 360
    pr = game_spit(mouth, aim, boss.color, dmg=boss._spiral_dmg,
                   effect=None, speed=boss._spiral_speed, radius=7)
    game.spawn_projectile(pr)


def charge_attack(boss, game, target):
    """Not an instant fire -- flips the FSM into 'charging' (see ``BossAI.tick``)
    so the boss itself becomes the hazard for a beat, Gurdy-Jr/Chub style."""
    boss._charge_dir = safe_norm(target.pos - boss.pos)


def pincha_bite(boss, game, target):
    """Quick short-range strike -- fast windup, no projectile, just a contact
    check at the reach the telegraph line showed. Dials come from the pattern
    dict (default = Centopeiadeira's pincers); Kraken-Mor's tentacle swipe
    reuses this exact function with a longer reach, Aranha-Rei's poison bite
    with an optional `slow` (the player has no poison status to apply, so it
    substitutes the same "landed bite roots you" idea every sting in this
    game already uses) -- instead of new code either time."""
    pat = PATTERNS[boss.boss_ai.pattern_id]
    reach = boss.max_r * pat.get('reach', C.BOSS_PINCHA_REACH)
    dmg = pat.get('dmg', C.BOSS_PINCHA_DMG)
    if target.pos.distance_to(boss.pos) < reach:
        landed = target.hurt(game, safe_norm(target.pos - boss.pos), dmg)
        slow = pat.get('slow')
        if landed and slow:
            target.apply_slow(*slow)
        game.fx.spark_burst(boss.spine.joints[0], boss.color, 10, 260)
        game.shake(4)


def _select_arms_rain(boss, game, target):
    """Picks the slam points at WINDUP START (not fire time), so the
    telegraph can show them as growing circles for the whole windup -- called
    once by the FSM via the pattern's ``select`` hook (see ``tick()``).
    Dials from the pattern dict: Primordial's Sky Slam reuses this with
    ``count=1, spread=0`` (a single point pinned on the target = a giant
    shadow, not a cluster) instead of new selection code."""
    pat = PATTERNS[boss.boss_ai.pattern_id]
    n = pat.get('count', C.BOSS_ARMS_RAIN_COUNT)
    spread = pat.get('spread', C.BOSS_ARMS_RAIN_SPREAD)
    boss._rain_points = [Vector2(target.pos) + random_dir(random.uniform(0, spread))
                         for _ in range(n)]


def arms_rain(boss, game, target):
    """Fires at windup end -- damages wherever ``_select_arms_rain`` marked."""
    pat = PATTERNS[boss.boss_ai.pattern_id]
    radius = pat.get('radius', C.BOSS_ARMS_RAIN_RADIUS)
    dmg = pat.get('dmg', C.BOSS_ARMS_RAIN_DMG)
    for pt in getattr(boss, '_rain_points', []):
        for p in game.players:
            if p.dead or p.down:
                continue
            if p.pos.distance_to(pt) < radius + p.max_r * 0.4:
                p.hurt(game, safe_norm(p.pos - pt), dmg)
        game.fx.ring(pt, boss.color)
        game.fx.burst(pt, palette.lighten(boss.color, 0.3), 14, 260)
    boss._rain_points = []
    game.shake(6)
    audio.play('hit', 0.4)


def sky_slam(boss, game, target):
    """Primordial: the same single-point slam as ``arms_rain`` (pattern dict
    sets count=1) plus a lingering magma puddle where it lands -- 'Sky Slam'
    and 'Magma Spit' folded into one attack instead of two separate ones."""
    from ...combat import weapons
    pts = list(getattr(boss, '_rain_points', []))
    arms_rain(boss, game, target)
    for pt in pts:
        game.spawn_puddle(weapons.Puddle(pt, C.BOSS_SKY_SLAM_PUDDLE_R,
                                         C.BOSS_SKY_SLAM_PUDDLE_DMG,
                                         C.BOSS_SKY_SLAM_PUDDLE_LIFE, 18,
                                         hostile=True, tick=0.5))


def web_trap(boss, game, target):
    """Mãe-Escaravelho's Web Trap: a patch that roots (heavy slow, tiny
    damage) instead of hurting -- reuses the single-point select from
    ``sky_slam``/``arms_rain`` and ``weapons.Puddle``'s ``slow=`` param
    (added for Rei Lagarto's scar) instead of new hazard code. Dials come
    from the pattern dict -- Aranha-Rei's Web Dome reuses this exact
    function with more points and a bigger radius via ``arms_rain``'s
    ``count``/``spread`` select, no new selection or hazard code either."""
    from ...combat import weapons
    pat = PATTERNS[boss.boss_ai.pattern_id]
    radius = pat.get('radius', C.BOSS_WEB_TRAP_R)
    dmg = pat.get('dmg', C.BOSS_WEB_TRAP_DMG)
    life = pat.get('life', C.BOSS_WEB_TRAP_LIFE)
    slow = pat.get('slow', C.BOSS_WEB_TRAP_SLOW)
    for pt in getattr(boss, '_rain_points', []):
        game.spawn_puddle(weapons.Puddle(pt, radius, dmg, life, 200, hostile=True,
                                         tick=0.4, slow=(slow, 1.2)))
    boss._rain_points = []
    game.fx.burst(boss.pos, (240, 240, 250), 8, 140)


PATTERNS = {
    'radial': dict(fn=radial_burst, windup=C.BOSS_RADIAL_WINDUP, telegraph='radial'),
    'fan': dict(fn=fan_shot, windup=C.BOSS_FAN_WINDUP, telegraph='fan'),
    'barrage': dict(fn=aimed_barrage, windup=C.BOSS_BARRAGE_WINDUP, telegraph='line'),
    'summon': dict(fn=summon_adds, windup=C.BOSS_SUMMON_WINDUP, telegraph='horn'),
    'shockwave': dict(fn=shockwave, windup=C.BOSS_SHOCKWAVE_WINDUP, telegraph='shockwave'),
    'pincha': dict(fn=pincha_bite, windup=C.BOSS_PINCHA_WINDUP, telegraph='line'),
    # Kraken-Mor's tentacle swipe: same pincha_bite fn, just a longer/harder
    # reach via the pattern dict -- no new logic for a longer arm
    'swipe': dict(fn=pincha_bite, windup=0.5, telegraph='line', reach=2.4, dmg=19),
    'arms_rain': dict(fn=arms_rain, select=_select_arms_rain,
                      windup=C.BOSS_ARMS_RAIN_WINDUP, telegraph='rain'),
    'sky_slam': dict(fn=sky_slam, select=_select_arms_rain,
                     windup=C.BOSS_SKY_SLAM_WINDUP, telegraph='rain',
                     count=1, spread=0, radius=C.BOSS_SKY_SLAM_RADIUS,
                     dmg=C.BOSS_SKY_SLAM_DMG),
    'massive_fan': dict(fn=fan_shot, windup=C.BOSS_MASSIVE_FAN_WINDUP, telegraph='fan',
                        count=12, spread=70, shot_speed=220, dmg=20),
    'web_trap': dict(fn=web_trap, select=_select_arms_rain, windup=C.BOSS_WEB_TRAP_WINDUP,
                     telegraph='rain', count=1, spread=60),
    # Aranha-Rei's Web Dome: same web_trap fn/select, just more/bigger patches
    'web_dome': dict(fn=web_trap, select=_select_arms_rain, windup=0.8, telegraph='rain',
                     count=5, spread=180, radius=70, life=9.0),
    # Aranha-Rei's poison bite: same pincha_bite, roots instead of poisoning
    # (the player has no poison status -- see pincha_bite's docstring)
    'poison_bite': dict(fn=pincha_bite, windup=0.3, telegraph='line',
                        reach=1.6, dmg=15, slow=(0.5, 1.4)),
    'deathroll': dict(fn=spiral_pattern, windup=0.5, telegraph='spiral',
                      shots=C.BOSS_DEATHROLL_SHOTS, turn=C.BOSS_DEATHROLL_TURN,
                      gap=C.BOSS_DEATHROLL_GAP, shot_speed=260, shot_dmg=12),
    # burrow has no `fn`/instant fire -- BossAI.tick special-cases `burrow=True`
    # and delegates every frame to the boss's OWN ai.burrow.tick (the
    # regular centipede's dig/erupt state machine, telegraphs included for
    # free -- AILizard.draw() already checks self.burrowed/burrow_state)
    'burrow': dict(fn=None, windup=0.05, telegraph=None, burrow=True),
    # same idea as burrow: no `fn`, BossAI.tick delegates every frame to the
    # octopus's own ai.grapple.tick (reach/root/snap+pull+slow, telegraph
    # included -- Lizard.draw already shows the arms converging via arm_target)
    'grapple': dict(fn=None, windup=0.05, telegraph=None, grapple=True),
    'spiral': dict(fn=spiral_pattern, windup=C.BOSS_SPIRAL_WINDUP, telegraph='spiral'),
    'charge': dict(fn=charge_attack, windup=C.BOSS_CHARGE_WINDUP, telegraph='line', charge=True),
}


def king_phases():
    """3 fases (66/33 -- doc's own thresholds for this boss). Fase 2 adds
    Radial Burst (1 thing); fase 3 swaps Fan for Spiral + faster cd (2 things)."""
    return [
        dict(hp_frac=1.0, patterns=['fan', 'shockwave', 'charge'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['fan', 'shockwave', 'charge', 'radial'], cd_mul=1.0),
        dict(hp_frac=0.33, patterns=['spiral', 'shockwave', 'charge', 'radial'], cd_mul=0.7),
    ]


# --------------------------------------------------------------------------- #
#  Centopeiadeira (onda 10 / tier 2): "Degradação" -- perde segmentos e        #
#  acelera a cada fase, reusando o dig/erupt do centipede comum como um       #
#  padrão a mais entre outros.                                                #
# --------------------------------------------------------------------------- #

def centipede_phases():
    return [
        dict(hp_frac=1.0, patterns=['burrow', 'spiral', 'pincha'], cd_mul=1.0),
        dict(hp_frac=0.6, patterns=['burrow', 'spiral', 'pincha', 'radial'], cd_mul=0.85),
        dict(hp_frac=0.3, patterns=['spiral', 'pincha', 'radial', 'deathroll'], cd_mul=0.7),
    ]


def centipede_on_phase(boss, phase_i):
    """Perde segmentos + acelera a cada transição (armadura quebra ao vivo,
    mesmo padrão de `champions.py`): menos corpo, mais velocidade, mais caos --
    e MENOS hitbox de corpo, então o jogador troca "mais perigoso" por "mais
    fácil de acertar em cheio", a decisão que o doc descreve."""
    boss.genome.length = max(0.5, boss.genome.length - C.CENT_BOSS_SHRINK)
    boss.genome.speed *= C.CENT_BOSS_SPEED_BUMP
    boss.rebuild_body(keep_pose=True)


# --------------------------------------------------------------------------- #
#  Kraken-Mor (onda 15 / tier 3): reels you in, then rains arms on the arena. #
# --------------------------------------------------------------------------- #

def kraken_phases():
    return [
        dict(hp_frac=1.0, patterns=['grapple', 'fan', 'swipe'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['grapple', 'fan', 'swipe', 'arms_rain'], cd_mul=1.0),
        dict(hp_frac=0.33, patterns=['grapple', 'spiral', 'swipe', 'arms_rain'], cd_mul=0.75),
    ]


# --------------------------------------------------------------------------- #
#  PRIMORDIAL (onda 20 -- chefe final do modo normal): tudo ao mesmo tempo,   #
#  cada fase soma em vez de trocar (a fase final do jogo ganha a licenca de   #
#  quebrar a "regra dos 2" -- ANKH tem a mesma exceção documentada no doc 03).#
# --------------------------------------------------------------------------- #

def primordial_phases():
    return [
        dict(hp_frac=1.0, patterns=['massive_fan', 'shockwave'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['massive_fan', 'shockwave', 'sky_slam', 'summon'],
             cd_mul=0.85),
        dict(hp_frac=0.33, patterns=['massive_fan', 'shockwave', 'sky_slam', 'summon',
                                     'deathroll'], cd_mul=0.5),
    ]


# --------------------------------------------------------------------------- #
#  Mae-Escaravelho (endless, tier5+): a support, not a tank -- SHE barely     #
#  attacks directly, her adds do the damage. Explodes into larvae on death.  #
# --------------------------------------------------------------------------- #

def beetle_phases():
    return [
        dict(hp_frac=1.0, patterns=['summon', 'fan', 'shockwave'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['summon', 'fan', 'shockwave', 'web_trap'], cd_mul=0.9),
        dict(hp_frac=0.33, patterns=['summon', 'shockwave', 'web_trap', 'radial'], cd_mul=0.65),
    ]


# --------------------------------------------------------------------------- #
#  Aranha-Rei (endless, tier5+): nervosa, para e dispara -- teia acumula.     #
# --------------------------------------------------------------------------- #

def spider_king_phases():
    return [
        dict(hp_frac=1.0, patterns=['charge', 'web_trap', 'summon'], cd_mul=1.0),
        dict(hp_frac=0.6, patterns=['charge', 'web_trap', 'summon', 'web_dome'], cd_mul=0.85),
        dict(hp_frac=0.3, patterns=['poison_bite', 'web_trap', 'summon', 'web_dome'], cd_mul=0.6),
    ]


# --------------------------------------------------------------------------- #
#  Serpente de Cristal (endless, tier5+): fria, nunca acelera, so fica mais   #
#  densa. Nota: o doc pede "Reflection" (espelha tiro do jogador de volta) e  #
#  "Fractal Burst" (projetil que se divide no meio do caminho) -- nenhum dos #
#  dois existe no motor de projeteis hoje (precisaria de logica nova de      #
#  colisao/split em voo); substituidos por padroes ja existentes (spiral/    #
#  deathroll) em vez de ficar pela metade -- decisao registrada no plano.    #
# --------------------------------------------------------------------------- #

def crystal_phases():
    return [
        dict(hp_frac=1.0, patterns=['barrage', 'fan'], cd_mul=1.0),
        dict(hp_frac=0.66, patterns=['barrage', 'fan', 'spiral'], cd_mul=1.0),
        # "nao acelera, fica mais precisa" -- cd_mul quase intocado de proposito
        # (os outros chefes cortam pra 0.5-0.75; este so ganha 1 padrao a mais)
        dict(hp_frac=0.33, patterns=['fan', 'spiral', 'deathroll'], cd_mul=0.85),
    ]


# --------------------------------------------------------------------------- #
#  Terror Alado (endless, tier5+): um voador. `flying=True` (via boss_attrs)  #
#  faz collision._samples pular ele -- paira sem ser empurrado, mas continua  #
#  atingivel por hit_test. Sadico, cacador aereo: mergulha e mira onde voce   #
#  VAI estar.                                                                 #
# --------------------------------------------------------------------------- #

def wasp_phases():
    return [
        dict(hp_frac=1.0, patterns=['charge', 'fan'], cd_mul=0.9),
        dict(hp_frac=0.6, patterns=['charge', 'fan', 'barrage'], cd_mul=0.85),
        dict(hp_frac=0.3, patterns=['charge', 'barrage', 'spiral'], cd_mul=0.6),
    ]


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
