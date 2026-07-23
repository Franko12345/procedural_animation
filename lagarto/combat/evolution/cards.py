"""The level-up hand: rolling weapon/item/mutation cards for the player to pick.

Levelling up rolls a few cards from the mutation table (`mutations.py`), the
weapon roster and the item pool; picking one applies its effect. The roll is
biased toward closing a `Synergy` (`synergies.py`) -- see ``synergy_factor``.
"""

import random as _random

from ...core import config as C
from .mutations import MUTATIONS, _ONCE
from .synergies import SYNERGIES, owned_tags


class WeaponCard:
    """A level-up card that grants a new weapon or upgrades an owned one."""
    is_weapon = True

    def __init__(self, wid, gaining, next_level):
        from .. import weapons
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
        from .. import items as _items
        _items.give(player, self.item, game)


def _weapon_cards(player):
    from .. import weapons
    from ...flow import progression
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
    from .. import items as _items
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
