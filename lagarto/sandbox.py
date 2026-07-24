"""Sandbox: dev-only debug overlay for spawning and testing entities live.

Isolated on purpose (ADR-0010: single-file-per-module). This one module owns the
sandbox controller and its mouse-driven, immediate-mode overlay; nothing in the
production UI knows it exists, and deleting this file plus the ``--sandbox`` branch
in ``app.main`` removes the feature whole.

Reached only via ``python lizard_game.py --sandbox`` -- a flag nobody passes on a
normal run. See ``plans/04_sandbox_debug.md`` for the full design; this file is the
SB2 skeleton: a real ``Game`` with no auto-waves plus an empty panel that toggles
open/closed. Later slices hang spawn/round/store/loadout tooling off this spine.
"""

import pygame

from .core import config as C
from . import ui


# Keys that toggle the panel open/closed. Backtick is the classic dev-console key;
# F1 is the fallback for keyboards where backtick is awkward.
TOGGLE_KEYS = (pygame.K_BACKQUOTE, pygame.K_F1)


class Sandbox:
    """Per-frame debug overlay driven from ``app.main``'s sandbox branch.

    ``handle_event`` consumes the toggle key (and, while open, clicks that land on
    the panel) so they never reach the live game. ``draw`` paints the panel on top
    when open. The game keeps simulating underneath either way -- toggling never
    freezes it.
    """

    def __init__(self, game, font, bigfont=None):
        self.game = game
        self.font = font
        self.bigfont = bigfont or font
        self.open = False
        # Registry of hand-spawned things. Empty in SB2; the preset (SB later) walks
        # this to serialise the live scene. Every entity spawned by the sandbox is
        # also tagged ``_sb=(kind, key)`` so a scan of the game's lists can recover
        # the same tuples independently of this list.
        self.spawned = []
        # Panel geometry: a left-docked column, sized once.
        self.rect = pygame.Rect(16, 16, 300, C.HEIGHT - 32)

    # ---- registry ------------------------------------------------------- #
    def track(self, entity, kind, key):
        """Tag ``entity`` as sandbox-spawned and remember it. Base for the preset."""
        entity._sb = (kind, key)
        self.spawned.append(entity)
        return entity

    # ---- input ---------------------------------------------------------- #
    def handle_event(self, ev):
        """Return True if the event was consumed by the overlay (so app.main skips it)."""
        if ev.type == pygame.KEYDOWN and ev.key in TOGGLE_KEYS:
            self.open = not self.open
            return True
        # While open, swallow clicks that land on the panel so they don't also arm
        # a game action underneath. Clicks outside the panel fall through to the
        # world (armed spawns place there -- SB later).
        if self.open and ev.type == pygame.MOUSEBUTTONDOWN:
            from . import display
            if self.rect.collidepoint(display.to_logical(ev.pos)):
                return True
        return False

    # ---- draw ----------------------------------------------------------- #
    def draw(self, surf):
        if not self.open:
            # Closed: a small unobtrusive hint so the dev knows the panel is there.
            ui.text(surf, self.font, "` sandbox", (C.WIDTH - 12, 8), ui.DIM,
                    align='right')
            return
        r = self.rect
        ui.panel(surf, r, alpha=205, accent=ui.LINE)
        ui.text(surf, self.bigfont, "SANDBOX", (r.x + 16, r.y + 14), ui.TEXT)
        ui.text(surf, self.font, "` / F1 fecha", (r.x + 16, r.y + 52), ui.DIM)
        # Dropdown panel body is intentionally EMPTY in SB2 -- the spine other
        # slices hang their tools on.
