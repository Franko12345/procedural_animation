"""Species = a genome template + gameplay metadata.

Spawning a species makes a colour/size-jittered variation of its genome, so every
lizard on screen looks a little different. ``role`` maps to the AI kind, ``grants``
is the body part the player gains by eating one (Phase 4 wires that up), and
``diet`` lets predators hunt other creatures for the living-ecosystem feel.
"""

import random as _random

from .genome import Genome

SPECIES = {
    # ---- prey (wander / flee, feed the player and the predators) ---------- #
    'grazer': dict(role='prey', xp=3, score=15, grants=None,
                   genome=Genome(name='grazer', size=0.85, hue=95, sat=0.8, val=0.95,
                                 behavior='flee', hp=2)),
    'critter': dict(role='prey', xp=2, score=10, grants=None,
                    genome=Genome(name='critter', size=0.62, leg_count=4, hue=190,
                                  behavior='flee', hp=1, speed=1.15)),

    # ---- enemies ---------------------------------------------------------- #
    'runner': dict(role='enemy', xp=5, score=40, grants=None,
                   genome=Genome(name='runner', size=0.72, leg_count=4, hue=42,
                                 speed=1.5, behavior='chase', hp=2, diet=('prey',))),
    'tank': dict(role='enemy', xp=9, score=70, grants='plates',
                 genome=Genome(name='tank', size=1.5, girth=1.25, leg_count=4, hue=6,
                               speed=0.68, plates=1, behavior='chase', hp=6, diet=('prey',))),
    'snake': dict(role='enemy', xp=6, score=50, grants=None,
                  genome=Genome(name='snake', size=0.95, length=1.9, leg_count=0, hue=282,
                                speed=1.2, behavior='chase', hp=3, diet=('prey',))),
    'horned': dict(role='enemy', xp=6, score=55, grants='horns',
                   genome=Genome(name='horned', size=1.12, leg_count=4, hue=20, horns=2,
                                 behavior='chase', hp=4, diet=('prey',))),
    'spiky': dict(role='enemy', xp=6, score=55, grants='spikes',
                  genome=Genome(name='spiky', size=1.0, leg_count=4, hue=322, spikes=1,
                                behavior='chase', hp=4, diet=('prey',))),
    'spider': dict(role='enemy', xp=7, score=60, grants='legs',
                   genome=Genome(name='spider', size=1.05, radial=True, leg_count=8,
                                 hue=265, sat=0.55, val=0.7, speed=1.15,
                                 behavior='lunge', hp=3, diet=('prey',))),
    'spitter': dict(role='enemy', xp=7, score=60, grants=None,
                    genome=Genome(name='spitter', size=0.95, leg_count=4, hue=150,
                                  speed=0.85, behavior='ranged', hp=3, diet=('prey',))),
    'scorpion': dict(role='enemy', xp=8, score=65, grants='sting',
                     genome=Genome(name='scorpion', size=1.05, leg_count=6, hue=18,
                                   sat=0.7, tail='sting', speed=0.95, behavior='chase',
                                   hp=4, diet=('prey',))),

    # ---- extra prey ------------------------------------------------------- #
    'frog': dict(role='prey', xp=3, score=18, grants=None,
                 genome=Genome(name='frog', size=0.7, leg_count=4, length=0.6, girth=1.3,
                               hue=110, behavior='hop', hp=2)),
    'fish': dict(role='prey', xp=3, score=15, grants=None,
                 genome=Genome(name='fish', size=0.75, leg_count=0, length=0.8, fins=1,
                               tail='fin', hue=195, behavior='flee', hp=1, speed=1.1)),
}

PREY_SPECIES = [k for k, v in SPECIES.items() if v['role'] == 'prey']
ENEMY_SPECIES = [k for k, v in SPECIES.items() if v['role'] == 'enemy']


def make(species_key, pos, rng=_random):
    """Build a jittered instance of ``species_key`` at ``pos``."""
    from .lizard import AILizard          # local import avoids a cycle
    spec = SPECIES[species_key]
    g = spec['genome'].random_variation(rng)
    c = AILizard(pos, spec['role'], genome=g)
    c.species = species_key
    c.xp_value = spec['xp']
    c.score_value = spec['score']
    c.grants = spec['grants']
    c.hp = max(1, int(round(g.hp)))
    return c
