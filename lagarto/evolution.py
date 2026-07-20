"""Evolution: the level-up mutation cards and their hand-made synergies.

Each ``Mutation`` is a small data object with an ``apply(player, game)`` callback.
Levelling up rolls a few of them as cards; picking one mutates the player (stats
or a genome part -- the body redraws itself). Collecting the right set triggers a
named ``Synergy`` for an extra kick, the "just one more run" hook (Lake of Creatures).
"""

import random as _random

from . import palette


class Mutation:
    def __init__(self, mid, name, desc, hue, apply, weight=1.0):
        self.id = mid
        self.name = name
        self.desc = desc
        self.color = palette.vibrant(hue, 0.8, 1.0)
        self.apply = apply
        self.weight = weight
        self.icon = mid                 # procedural icon id (see icons.py)


def _m(mid, name, desc, hue, fn, weight=1.0):
    return Mutation(mid, name, desc, hue, fn, weight)


# ---- stat mutations ------------------------------------------------------- #
def _health(p, g): p.max_health += 30; p.health += 30
def _speed(p, g): p.speed_mult *= 1.14; p.max_speed *= 1.14
def _dash(p, g): p.dash_cooldown *= 0.8
def _energy(p, g): p.max_energy += 30; p.energy = p.max_energy
def _regen(p, g): p.regen += 4.0
def _xp(p, g): p.xp_mult *= 1.25
def _tongue(p, g): p.tongue_range += 90
def _thorns(p, g): p.thorns += 1
def _venom(p, g): p.venom = True
def _wings(p, g): p.wings = True
# global weapon stats (Vampire-Survivors passives)
def _might(p, g): p.might *= 1.2
def _area(p, g): p.area_mult *= 1.18
def _haste(p, g): p.cooldown_mult *= 0.85
def _amount(p, g): p.amount += 1

# ---- part mutations (reuse Player.grant_part; body redraws itself) -------- #
def _legs(p, g): p.grant_part('legs', g)
def _spikes(p, g): p.grant_part('spikes', g)
def _horns(p, g): p.grant_part('horns', g)
def _plates(p, g): p.grant_part('plates', g)
def _club(p, g): p.genome.tail = 'club'


MUTATIONS = [
    _m('health',  'Coracao Extra',   '+1 vida maxima',              5,   _health),
    _m('speed',   'Agilidade',       '+14% velocidade',             130, _speed),
    _m('dash',    'Arranco Rapido',  '-20% recarga do dash',        190, _dash),
    _m('energy',  'Folego',          '+30 energia maxima',          210, _energy),
    _m('regen',   'Regeneracao',     'cura vida lentamente',        150, _regen, 0.8),
    _m('xp',      'Metabolismo',     '+25% de XP',                  50,  _xp),
    _m('tongue',  'Lingua Longa',    '+alcance da lingua',          320, _tongue),
    _m('thorns',  'Espinhos',        'dano de contato + espinhos',  330, _thorns),
    _m('spikes',  'Placas Dorsais',  'mais espinhos afiados',       28,  _spikes),
    _m('plates',  'Carapaca',        'placas de armadura',          260, _plates),
    _m('horns',   'Chifres',         'chifres na cabeca',           20,  _horns, 0.9),
    _m('legs',    'Pernas Extras',   '+2 pernas (mais estavel)',    275, _legs, 0.9),
    _m('club',    'Cauda-Clava',     'rabada: +dano e empurrao',    15,  _club, 0.7),
    _m('venom',   'Peconha',         'dash/bote envenena',          105, _venom, 0.8),
    _m('wings',   'Membranas',       'dash mais forte e rapido',    175, _wings, 0.7),
    _m('might',   'Vigor',           '+20% dano das armas',         0,   _might, 1.2),
    _m('area',    'Amplitude',       '+18% area/alcance das armas', 150, _area, 1.1),
    _m('haste',   'Frenesi',         '+15% cadencia das armas',     190, _haste, 1.1),
    _m('amount',  'Fecundidade',     '+1 projetil/orbital',         55,  _amount, 0.9),
]
_BY_ID = {m.id: m for m in MUTATIONS}
_ONCE = ('venom', 'wings', 'club', 'thorns')     # don't offer twice once owned


class WeaponCard:
    """A level-up card that grants a new weapon or upgrades an owned one."""
    is_weapon = True

    def __init__(self, wid, gaining, next_level):
        from . import weapons
        w = weapons.WEAPONS[wid]
        self.wid = wid
        self.icon = wid                 # procedural icon id (see icons.py)
        self.color = w.color
        self.weight = 1.6                        # weapons show up a bit more
        if gaining:
            self.name = f'{w.name}  [NOVA]'
            self.desc = w.level_desc(1)
        else:
            # ASCII '->' e nao a seta U+2192: o Noto Sans base nao cobre setas
            # (elas vivem no Noto Sans Symbols), entao ela sai como tofu na carta.
            # font.metrics() mente aqui -- reporta o glifo e mesmo assim nao rasteriza.
            self.name = f'{w.name}  Nv{next_level - 1}->{next_level}'
            self.desc = w.level_desc(next_level)
        self._gaining = gaining
        self._next = next_level

    def apply(self, player, game):
        if self._gaining:
            player.gain_weapon(self.wid)
        else:
            player.level_weapon(self.wid)


def _weapon_cards(player):
    from . import weapons
    from . import progression
    meta = getattr(player, 'meta', None)
    cards = []
    for wid, w in weapons.WEAPONS.items():
        if meta is not None and not progression.unlocked(meta, 'weapon', wid):
            continue                          # locked behind meta-progression
        if wid in player.weapons:
            lvl = player.weapons[wid]
            if lvl < w.maxlevel():
                cards.append(WeaponCard(wid, False, lvl + 1))
        elif len(player.weapons) < 6:
            cards.append(WeaponCard(wid, True, 1))
    return cards


def roll_cards(player, n=3, rng=_random):
    """Mix of weapon cards (new/upgrade, VS-style) and passive mutation cards."""
    pool = list(_weapon_cards(player))
    for m in MUTATIONS:
        if m.id in _ONCE and m.id in player.mutations:
            continue
        pool.append(m)
    rng.shuffle(pool)
    chosen, weights = [], [c.weight for c in pool]
    while pool and len(chosen) < n:
        total = sum(weights)
        r = rng.uniform(0, total)
        acc = 0
        for i, w in enumerate(weights):
            acc += w
            if r <= acc:
                chosen.append(pool.pop(i))
                weights.pop(i)
                break
    return chosen


# --------------------------------------------------------------------------- #
#  Synergies: named combos that fire when the player owns the right set        #
# --------------------------------------------------------------------------- #

class Synergy:
    def __init__(self, sid, name, needs, desc, apply):
        self.id = sid
        self.name = name
        self.needs = needs        # set of mutation ids required
        self.desc = desc
        self.apply = apply


def _syn_arachnid(p, g): p.speed_mult *= 1.15; p.max_speed *= 1.15; p.venom = True
def _syn_fortress(p, g): p.thorns += 2; p.max_health += 30; p.health += 30
def _syn_glass(p, g): p.max_speed *= 1.2; p.dash_cooldown *= 0.7


SYNERGIES = [
    Synergy('arachnid', 'ARACNIDEO', {'legs', 'venom'},
            'pernas + peconha: velocidade e veneno', _syn_arachnid),
    Synergy('fortress', 'FORTALEZA', {'plates', 'thorns'},
            'placas + espinhos: reflete dano', _syn_fortress),
    Synergy('glass', 'RELAMPAGO', {'speed', 'wings'},
            'agilidade + membranas: dash brutal', _syn_glass),
]


def check_synergies(player, game):
    """Fire any newly-completed synergy; returns names triggered this call."""
    owned = set(player.mutations)
    fired = []
    for s in SYNERGIES:
        if s.id not in player.synergies and s.needs <= owned:
            player.synergies.add(s.id)
            s.apply(player, game)
            fired.append(s.name)
    return fired
