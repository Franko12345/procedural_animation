"""Registry: lookup + filtering + weighted rolling for a list of data objects.

Five subsystems (charms, characters, items, mutations, synergies) all rebuilt
the same three lines: a ``BY_ID`` dict, a ``get(id)`` helper, and some flavour
of pool/roll. The helper unifies **lookup**, not identity -- each subsystem
keeps its own dataclass, its own fields, its own tables. Nothing changes for
the caller; the ``.get`` / iteration / filtering surface just lives once.

Effect-shape rule (see the ticket): the passives across these subsystems are
now callables of shape ``apply(player, game)`` (and, where reversible,
``unapply(player, game)``). The Registry does not itself run effects; it just
carries them uniformly so ``owned_tags`` and card rolling stop caring which
subsystem a callback came from.
"""

import random as _random


class Registry:
    """Wrap a list of items keyed by an attribute (default ``id``)."""

    __slots__ = ('_items', '_by_key', '_key')

    def __init__(self, items, key='id'):
        self._items = list(items)
        self._key = key
        self._by_key = {getattr(it, key): it for it in self._items}

    # ---- lookup ---------------------------------------------------------- #
    def get(self, key, default=None):
        return self._by_key.get(key, default)

    def __contains__(self, key):
        return key in self._by_key

    def __getitem__(self, key):
        return self._by_key[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def all(self):
        """List of items in declaration order (safe to iterate/mutate)."""
        return list(self._items)

    def keys(self):
        return [getattr(it, self._key) for it in self._items]

    def values(self):
        return list(self._items)

    # ---- filtering ------------------------------------------------------- #
    def by(self, **filters):
        """Items where every attribute in ``filters`` matches.

        A value may be a container (list/tuple/set); membership in ``pools``
        etc. is a common enough shape that we support ``pool='shop'`` matching
        a tuple attribute without the caller building a lambda.
        """
        out = []
        for it in self._items:
            ok = True
            for name, want in filters.items():
                have = getattr(it, name, None)
                if isinstance(have, (list, tuple, set, frozenset)):
                    if want not in have:
                        ok = False
                        break
                elif have != want:
                    ok = False
                    break
            if ok:
                out.append(it)
        return out

    # ---- weighted roll --------------------------------------------------- #
    def roll(self, pool=None, n=1, rng=_random, filter=None, weight=None):
        """Weighted pick of ``n`` distinct items.

        ``pool`` filters to items whose ``pools`` attribute contains ``pool``
        (or, if the attribute is scalar, whose value equals ``pool``).
        ``filter`` is an optional callable ``(item) -> bool`` layered on top.
        ``weight`` is an optional callable ``(item) -> float``; defaults to
        the item's ``weight()`` method if present, else 1.0.
        """
        cand = self._items
        if pool is not None:
            cand = [it for it in cand if _in_pool(it, pool)]
        if filter is not None:
            cand = [it for it in cand if filter(it)]
        cand = list(cand)                    # local copy: we pop from it
        if weight is None:
            weight = _default_weight
        out = []
        while cand and len(out) < n:
            weights = [weight(it) for it in cand]
            total = sum(weights)
            if total <= 0:
                break
            r = rng.uniform(0, total)
            acc = 0.0
            for k, it in enumerate(cand):
                acc += weights[k]
                if r <= acc:
                    out.append(cand.pop(k))
                    break
        return out


def _in_pool(item, pool):
    have = getattr(item, 'pools', None)
    if isinstance(have, (list, tuple, set, frozenset)):
        return pool in have
    return have == pool


def _default_weight(item):
    w = getattr(item, 'weight', None)
    if callable(w):
        return w()
    if isinstance(w, (int, float)):
        return w
    return 1.0
