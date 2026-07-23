"""Evolution: the level-up mutation cards and their hand-made synergies.

Split in three: the mutation table (`mutations.py`), the synergy table
(`synergies.py`), and the card-rolling machinery that consumes both
(`cards.py`). Deliberate exception to the empty-``__init__`` convention --
callers say ``evolution.roll_cards`` / ``evolution.MUTATIONS``, so the names
below stay where they always were. Re-exports only; no logic lives here.
"""

from .cards import roll_cards
from .mutations import MUTATIONS
from .synergies import SYNERGIES, check_synergies, owned_tags, synergy_progress

__all__ = ['MUTATIONS', 'SYNERGIES', 'roll_cards', 'check_synergies',
           'owned_tags', 'synergy_progress']
