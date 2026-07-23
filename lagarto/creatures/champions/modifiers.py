"""Champion **modifiers**: purely mechanical traits that stack on top of anything.

See the package docstring for why they are a separate layer from variants.

``_rebuild`` lives in :mod:`variants` rather than :mod:`base`: ``base`` imports
both applier modules to build the registry, so anything they share has to sit
upstream of it or the import cycles.
"""

from ...core import config as C
from .variants import _rebuild


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
