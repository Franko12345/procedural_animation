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

# Display name + lore for the bestiary screen (kept apart so the tables stay lean).
LORE = {
    'grazer':  ('PASTADOR', 'Herbivoro placido que rumina flores. Foge de tudo que se '
                            'move rapido. Alimento farto para quem sabe caçar.'),
    'critter': ('BICHINHO', 'Pequeno e nervoso, corre em zigue-zague. Pouca carne, mas '
                            'facil de abocanhar quando se esta com fome.'),
    'frog':    ('SAPO', 'Anfibio saltador: nunca anda em linha reta, so pula. Dificil '
                        'de acertar em movimento, mas indefeso quando pousa.'),
    'fish':    ('PEIXE', 'Nada em cardume nas aguas do pantano. Suas nadadeiras ondulam '
                         'mesmo fora d agua. Presa dos que ousam entrar no lago.'),
    'runner':  ('CORREDOR', 'Predador magro e veloz que ataca em bando. Sozinho e fraco; '
                            'em enxame, cerca a presa antes que ela perceba.'),
    'tank':    ('COURACADO', 'Massa lenta coberta de placas osseas. Aguenta muito castigo '
                             'e empurra tudo pela frente. Comer um concede sua carapaca.'),
    'snake':   ('SERPENTE', 'Corpo longo sem pernas que desliza em curvas. Persegue sem '
                            'descanso e e dificil de encurralar.'),
    'horned':  ('CHIFRUDO', 'Investe de cabeca baixa com dois chifres curvos. Devorar um '
                            'faz nascerem chifres no seu proprio cranio.'),
    'spiky':   ('ESPINHENTO', 'Coberto de espinhos dorsais que se eriçam ao atacar. '
                              'Abate-lo pode transplantar seus espinhos para voce.'),
    'spider':  ('ARANHA', 'Oito pernas radiais que a sustentam em qualquer terreno. '
                          'Telegrafa o bote e salta. Comer uma faz brotar mais pernas.'),
    'spitter': ('CUSPIDOR', 'Mantem distancia e lança veneno a jato. Prepara o cuspe '
                            'antes de disparar — da para desviar de quem repara.'),
    'scorpion': ('ESCORPIAO', 'Arrasta um ferrao curvo na cauda que envenena e retarda. '
                              'Quem sobrevive ao ferrao pode herda-lo.'),
}


def info(key):
    """(display name, lore) for the bestiary; falls back to the raw id."""
    return LORE.get(key, (key.upper(), ''))


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
    c.sync_max_hp()
    return c
