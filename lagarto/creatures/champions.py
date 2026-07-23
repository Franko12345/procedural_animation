"""Champions: elite spawns that make a familiar enemy read as a different creature.

Two layers on purpose, because they solve different problems.

**Variants** are named creatures with an identity -- a colour, a *visible trait
that explains the ability*, and behaviour. Rain World's lizard breeds are the
model: the yellow one has long antennae **because** it coordinates a pack, the
white one is pale **because** it ambushes. The trait is the tell, and a recolour
with no tell is a lie the player only discovers by dying to it.

**Modifiers** are purely mechanical (armoured, giant, explosive), stack on top of
anything including a variant, and buy combinatorial variety for very little code.

Legibility rules both layers: a champion announces itself with tint + scale + its
own glow, and its health multiplier stays **modest**. A champion is a threat
because of what it *does*; an enemy that is merely a sponge teaches nothing.
"""

import random

from ..core import config as C
from ..core import palette
from ..core.mathutil import safe_norm


class Champion:
    """One elite template. ``apply`` runs at spawn, ``tick`` every frame (optional)."""

    def __init__(self, cid, name, hue, apply, tick=None, hp_mult=1.0,
                 kind='variant'):
        self.id = cid
        self.name = name
        self.hue = hue
        self.apply = apply
        self.tick = tick
        self.hp_mult = hp_mult
        self.kind = kind            # 'variant' | 'modifier'

    def color(self):
        return palette.vibrant(self.hue, 0.85, 1.0)


def _rebuild(c):
    """Rebuild the body after the genome changed.

    This used to re-run ``__init__`` behind a snapshot of ~11 fields, because
    ``__init__`` resets everything: species.make's metadata reverted to the raw
    genome defaults, and stacking a modifier onto a variant erased the variant.
    ``Lizard.rebuild_body`` only touches genome-derived state, so the snapshot --
    and the whole class of bug it was patching over -- is gone.
    """
    c.rebuild_body()


# --------------------------------------------------------------------------- #
#  Variants                                                                    #
# --------------------------------------------------------------------------- #

def _filhote(c, game):
    """Blue-lizard shape: the smallest and frailest, but genuinely fast.

    Dies to one touch, so it can be aggressive without being unfair -- the threat
    is the swarm arriving faster than you can turn, not any single one of them.
    """
    g = c.genome
    g.size *= 0.55
    g.hue = 205
    g.sat = 0.95
    _rebuild(c)
    c.hp = 1
    c.max_hp = 1
    # Absolute, not a multiplier. max_speed is `165 * (0.85 + 0.4/size) * speed`,
    # so shrinking already accelerates it a lot -- multiplying on top of that
    # measured 5.75x the player, which nothing can dodge. And a *relative* boost
    # would make a "filhote of a tank" slower than the player, which contradicts
    # the one thing this variant is supposed to mean.
    c.max_speed = C.CHAMP_FILHOTE_SPEED
    c.xp_value = max(1, c.xp_value // 2)
    c.score_value = max(5, c.score_value // 2)


def _alfa(c, game):
    """Yellow-lizard shape: long antennae, and it hunts with a pack.

    The antennae are the tell -- they exist so the player can learn "that one
    makes the others dangerous" and prioritise it.
    """
    g = c.genome
    g.antennae = True
    g.size *= 1.15
    g.hue = 48
    g.sat = 0.95
    _rebuild(c)


def _alfa_tick(c, dt, game):
    c.rally_cd = getattr(c, 'rally_cd', 0.0) - dt
    if c.rally_cd > 0:
        return
    target = game.nearest_player(c.pos)
    if not target or target.pos.distance_to(c.pos) > C.CHAMP_ALFA_RANGE:
        return
    c.rally_cd = C.CHAMP_ALFA_CD
    roused = 0
    for e in game.enemies:
        if e is c or e.dead:
            continue
        if e.pos.distance_to(c.pos) < C.CHAMP_ALFA_RANGE:
            e.rally_t = C.CHAMP_ALFA_TIME
            roused += 1
    if roused:
        game.fx.ring(c.pos, (255, 226, 90))
        game.fx.spark_burst(c.pos, (255, 226, 90), 8, 240)


def _espectro(c, game):
    """White-lizard shape: an ambusher that is hard to see until it commits."""
    g = c.genome
    g.hue = 190
    g.sat = 0.12
    g.val = 1.0
    _rebuild(c)
    c.base_color = c.color


def _espectro_tick(c, dt, game):
    """Fade toward the ground until it is close, or until it has been hurt.

    Reuses the colour channel rather than real alpha: every part of the draw path
    reads ``self.color``, so body, legs, rim and glow all follow for free -- the
    same trick ``_fade_by_vitality`` uses for allies.
    """
    target = game.nearest_player(c.pos)
    dist = target.pos.distance_to(c.pos) if target else 9e9
    close = 1.0 - min(1.0, dist / C.CHAMP_ESPECTRO_REVEAL)
    hurt = 1.0 if c.hp < c.max_hp else 0.0
    vis = max(close, hurt, 0.12)
    c.color = palette.mix((58, 62, 74), c.base_color, vis)
    # the aura and the name obey the camouflage too, or the ambush is announced
    c.champion_vis = vis


def _saltador(c, game):
    """Cyan-lizard shape: covers ground in bursts instead of a steady walk."""
    g = c.genome
    g.hue = 178
    g.sat = 0.9
    g.tail = 'club'                 # the heavy tail it launches from: the tell
    _rebuild(c)


def _saltador_tick(c, dt, game):
    c.leap_cd = getattr(c, 'leap_cd', random.uniform(0.5, 1.6)) - dt
    if c.leap_cd > 0:
        return
    target = game.nearest_player(c.pos)
    if not target or target.pos.distance_to(c.pos) > C.CHAMP_SALTADOR_RANGE:
        return
    c.leap_cd = C.CHAMP_SALTADOR_CD
    c.vel = safe_norm(target.pos - c.pos) * c.max_speed * C.CHAMP_SALTADOR_POWER
    game.fx.spark_burst(c.pos, c.color, 7, 260)


def _apice(c, game):
    """Red-lizard shape: bigger, faster, relentless. The one you must respect."""
    g = c.genome
    g.size *= 1.3
    g.speed *= 1.2
    g.hue = 2
    g.sat = 1.0
    g.horns = max(1, g.horns)
    _rebuild(c)
    c.max_speed *= 1.15
    c.glow_body = True
    c.xp_value = int(c.xp_value * 1.6)
    c.score_value = int(c.score_value * 1.8)


# --------------------------------------------------------------------------- #
#  Modifiers                                                                   #
# --------------------------------------------------------------------------- #

def _blindado(c, game):
    """Armoured at the front, soft behind: rewards dashing *through* instead of into."""
    c.genome.plates = max(1, c.genome.plates)
    _rebuild(c)
    c.front_armor = C.CHAMP_ARMOR


def _gigante(c, game):
    g = c.genome
    g.size *= 1.5
    g.girth *= 1.1
    _rebuild(c)
    c.score_value = int(c.score_value * 1.5)


def _explosivo(c, game):
    """Leaves a parting gift, so killing it in your own face is a real mistake."""
    c.death_blast = True
    c.genome.spore_sacs = True
    _rebuild(c)


def _divisor(c, game):
    """Blobulon/Fistula: bursts into two smaller copies on death.

    Bloated and rounder (the tell that it is 'full'), it turns one kill into a
    small crowd -- so the counter is a weapon that clears the two children fast,
    not a single big hit. One generation only, to stay off the horde budget."""
    g = c.genome
    g.girth *= 1.25
    _rebuild(c)
    c.death_split = True
    c.split_gen = 1


CHAMPIONS = [
    Champion('filhote',  'FILHOTE',   205, _filhote,   hp_mult=1.0),
    Champion('alfa',     'ALFA',      48,  _alfa,      _alfa_tick,      hp_mult=1.5),
    Champion('espectro', 'ESPECTRO',  190, _espectro,  _espectro_tick,  hp_mult=1.2),
    Champion('saltador', 'SALTADOR',  178, _saltador,  _saltador_tick,  hp_mult=1.2),
    Champion('apice',    'APICE',     2,   _apice,     hp_mult=1.9),
    Champion('blindado', 'BLINDADO',  32,  _blindado,  hp_mult=1.3, kind='modifier'),
    Champion('gigante',  'GIGANTE',   290, _gigante,   hp_mult=1.8, kind='modifier'),
    Champion('explosivo', 'EXPLOSIVO', 18, _explosivo, hp_mult=1.1, kind='modifier'),
    Champion('divisor',  'DIVISOR',   135, _divisor,   hp_mult=1.2, kind='modifier'),
]
BY_ID = {ch.id: ch for ch in CHAMPIONS}
VARIANTS = [ch for ch in CHAMPIONS if ch.kind == 'variant']
MODIFIERS = [ch for ch in CHAMPIONS if ch.kind == 'modifier']


def chance(wave):
    """Champion odds ramp with the wave (Isaac: ~5% early, ~20% late)."""
    return min(C.CHAMP_CHANCE_MAX,
               C.CHAMP_CHANCE_BASE + C.CHAMP_CHANCE_PER_WAVE * max(0, wave - 1))


def maybe_promote(creature, game, wave, rng=random):
    """Roll a champion onto a freshly spawned enemy. Returns the Champion or None.

    A variant may additionally pick up one modifier, which is where the
    combinatorial variety comes from: APICE BLINDADO reads as a different fight
    from APICE, without a line of new behaviour code.
    """
    if getattr(creature, 'is_boss', False) or creature.kind != 'enemy':
        return None
    if rng.random() > chance(wave):
        return None
    ch = rng.choice(VARIANTS)
    _promote(creature, game, ch)
    if rng.random() < C.CHAMP_MODIFIER_CHANCE:
        _promote(creature, game, rng.choice(MODIFIERS), extra=True)
    return creature.champion


def _promote(creature, game, ch, extra=False):
    if not (extra and creature.champion is not None):
        creature.champion = ch
        creature.champion_name = ch.name
        creature.champion_ticks = []
    ch.apply(creature, game)                  # may rebuild the body (see _KEEP)
    if extra and creature.champion is not ch:
        creature.champion_name = f"{creature.champion_name} {ch.name}"
    creature.hp = max(1, int(round(creature.hp * ch.hp_mult)))
    creature.max_hp = creature.hp
    if ch.tick:
        creature.champion_ticks.append(ch.tick)
    creature.base_color = creature.color
