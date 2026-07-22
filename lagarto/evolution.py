"""Evolution: the level-up mutation cards and their hand-made synergies.

Each ``Mutation`` is a small data object with an ``apply(player, game)`` callback.
Levelling up rolls a few of them as cards; picking one mutates the player (stats
or a genome part -- the body redraws itself). Collecting the right set triggers a
named ``Synergy`` for an extra kick, the "just one more run" hook (Lake of Creatures).
"""

import random as _random

from .core import config as C
from .core import palette
from .core.registry import Registry


class Mutation:
    def __init__(self, mid, name, desc, hue, apply, weight=1.0):
        self.id = mid
        self.name = name
        self.desc = desc
        self.color = palette.vibrant(hue, 0.8, 1.0)
        self.apply = apply
        self.weight = weight            # plain float -- Registry._default_weight handles it
        self.icon = mid                 # procedural icon id (see icons.py)


def _m(mid, name, desc, hue, fn, weight=1.0):
    return Mutation(mid, name, desc, hue, fn, weight)


# ---- stat mutations ------------------------------------------------------- #
def _health(p, g): p.max_health += 30; p.health += 30
def _speed(p, g): p.speed_mult *= 1.14; p.max_speed *= 1.14
def _dash(p, g): p.dash_cooldown *= 0.8
def _energy(p, g): p.max_energy += 30; p.energy = p.max_energy
def _regen(p, g): p.regen += 2.2  # era 4.0/s -- curava rapido demais
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


MUTATIONS_LIST = [
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
    _m('wings',   'Membranas',       'dash: +50% dano e mais rapido', 175, _wings, 0.7),
    _m('might',   'Vigor',           '+20% dano (armas, dash, rabo)', 0,   _might, 1.2),
    _m('area',    'Amplitude',       '+18% area/alcance das armas', 150, _area, 1.1),
    _m('haste',   'Frenesi',         '+15% cadencia das armas',     190, _haste, 1.1),
    _m('amount',  'Fecundidade',     '+1 projetil/orbital',         55,  _amount, 0.9),
]
MUTATIONS = Registry(MUTATIONS_LIST)
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


class ItemCard:
    """A level-up card that grants an item (items.py)."""
    is_item = True

    def __init__(self, item):
        self.item = item
        self.id = item.id
        self.icon = item.icon
        self.color = item.color
        self.name = item.name
        self.desc = item.desc
        self.weight = item.weight()

    def apply(self, player, game):
        from . import items as _items
        _items.give(player, self.item, game)


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
        elif len(player.weapons) < getattr(player, 'weapon_cap', 6):
            cards.append(WeaponCard(wid, True, 1))
    return cards


def _card_tag(card):
    """The id a synergy would match this card by."""
    return getattr(card, 'wid', None) or getattr(card, 'id', None)


def synergy_factor(player, card):
    """Gungeon's Synergy Factor: bias the roll toward COMPLETING a combo.

    Not a new system -- ``roll_cards`` already picks by weight, so this is a
    multiplier on that weight. It exists as anti-frustration: the game quietly
    conspires to let your build close, instead of dangling half a synergy for
    the rest of the run.
    """
    tag = _card_tag(card)
    if not tag:
        return 1.0
    owned = owned_tags(player)
    best = 1.0
    for s in SYNERGIES:
        if s.id in player.synergies or tag not in s.needs or tag in owned:
            continue
        missing = len(s.needs - owned)
        if missing == 1:                      # this card finishes it
            best = max(best, C.SYNERGY_FACTOR_CLOSE)
        elif missing > 1:                     # this card starts it
            best = max(best, C.SYNERGY_FACTOR_START)
    return best


def roll_cards(player, n=3, rng=_random):
    """Mix of weapon cards (new/upgrade, VS-style) and passive mutation cards."""
    pool = list(_weapon_cards(player))
    for m in MUTATIONS:
        if m.id in _ONCE and m.id in player.mutations:
            continue
        pool.append(m)
    from . import items as _items
    for it in _items.in_pool(_items.POOL_LEVEL, getattr(player, 'items', ())):
        pool.append(ItemCard(it))
    rng.shuffle(pool)
    weights = [c.weight * synergy_factor(player, c) for c in pool]
    chosen = []
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
def _syn_corrosao(p, g): p.area_mult *= 1.35
def _syn_metralha(p, g): p.amount += 1
def _syn_ceifador(p, g): p.might *= 1.25
def _syn_praga(p, g): p.venom = True; p.might *= 1.15
def _syn_bola(p, g): p.whip_mult *= 1.5; p.whip_cooldown *= 0.8
def _syn_fantasma(p, g): p.dash_cooldown *= 0.6; p.max_speed *= 1.1
def _syn_colmeia(p, g): p.amount += 1; p.cooldown_mult *= 0.85
def _syn_ultimo(p, g): p.armor = min(0.7, p.armor + 0.15); p.regen += 3.0
def _syn_chicote(p, g): p.whip_cooldown *= 0.7


# `needs` may name a mutation, a weapon, an ITEM or a character id -- see
# `owned_tags`. Gungeon's rule applies: every synergy is NAMED and shown in the
# compendium, because one the player never learns about may as well not exist.
SYNERGIES_LIST = [
    Synergy('arachnid', 'ARACNIDEO', {'legs', 'venom'},
            'pernas + peconha: velocidade e veneno', _syn_arachnid),
    Synergy('fortress', 'FORTALEZA', {'plates', 'thorns'},
            'placas + espinhos: reflete dano', _syn_fortress),
    Synergy('glass', 'RELAMPAGO', {'speed', 'wings'},
            'agilidade + membranas: dash brutal', _syn_glass),
    Synergy('corrosao', 'CORROSAO', {'rastro', 'acido'},
            'rastro do dash + poca de acido: area muito maior', _syn_corrosao),
    Synergy('metralha', 'METRALHA', {'retaguarda', 'cuspe'},
            'retaguarda + cuspe: mais um projetil por salva', _syn_metralha),
    Synergy('ceifador', 'CEIFADOR', {'estopim', 'carnica'},
            'estopim + carnica: cada abate alimenta o proximo', _syn_ceifador),
    Synergy('praga', 'PRAGA VIVA', {'contagio', 'venom'},
            'contagio + peconha: o veneno nunca para de se espalhar', _syn_praga),
    Synergy('bola', 'BOLA DE DEMOLICAO', {'club', 'farpas'},
            'clava + farpas: a rabada vira arma de cerco', _syn_bola),
    Synergy('fantasma', 'FANTASMA', {'marcado', 'ricochete'},
            'presa marcada + ricochete: dash atras de dash', _syn_fantasma),
    Synergy('colmeia', 'COLMEIA', {'enxame', 'chamado'},
            'enxame + chamado: voce nunca luta sozinho', _syn_colmeia),
    Synergy('ultimo', 'ULTIMO SUSPIRO', {'segundo', 'adrenalina'},
            'segundo folego + adrenalina: mais forte a beira da morte', _syn_ultimo),
    Synergy('chicote', 'CHICOTE VIVO', {'vibora', 'espiral'},
            'vibora + cauda em espiral: a cauda nao para', _syn_chicote),
]
SYNERGIES = Registry(SYNERGIES_LIST)


def owned_tags(player):
    """Everything a synergy can key on: mutations, weapons, items, character.

    One flat set on purpose -- a synergy should be able to say "this weapon plus
    that item" without caring which system each half comes from.
    """
    tags = set(player.mutations) | set(player.weapons)
    tags |= set(getattr(player, 'items', ()))
    cid = getattr(player, 'character_id', None)
    if cid:
        tags.add(cid)
    return tags


def synergy_progress(player):
    """[(synergy, owned_count, total)] -- what the compendium shows."""
    tags = owned_tags(player)
    return [(s, len(s.needs & tags), len(s.needs)) for s in SYNERGIES]


def check_synergies(player, game):
    """Fire any newly-completed synergy; returns names triggered this call."""
    owned = owned_tags(player)
    fired = []
    for s in SYNERGIES:
        if s.id not in player.synergies and s.needs <= owned:
            player.synergies.add(s.id)
            s.apply(player, game)
            fired.append(s.name)
    return fired
