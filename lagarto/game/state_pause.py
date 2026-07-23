"""State 'pause': the overlay menu.

The input side (``toggle_pause``, ``pause_items``, ``pause_move``,
``pause_back``, ``pause_activate``) stays on ``Game`` -- app.py drives it.
"""

import pygame

from ..core import config as C
from ..core import palette
from ..render import ui
from . import menu as menulib


def update(game, dt):
    """No-op: pause freezes the world, and the shared UI clock in Game.step
    already advances ui_t / ui_fx / fx for the entry animation."""


def draw(game, surf, joysticks=None):
    game._veil(surf, (8, 10, 20), 200)
    cx = C.WIDTH // 2
    toff, talpha = ui.drop_in(game.ui_t, 0, 0.0, C.UI_VEIL, rise=22.0)
    if talpha > 0.01:
        title = game.bigfont.render("PAUSADO", True, C.COL_WHITE)
        im = title.copy()
        im.set_alpha(int(255 * talpha))
        surf.blit(im, (cx - im.get_width() // 2, int(120 + toff)))

    items = game.pause_items(joysticks)
    if game.pause_mode == 'controls':
        lines = menulib.controls_lines(joysticks)
        for i, line in enumerate(lines):
            off, alpha = ui.drop_in(game.ui_t, 1 + i * 0.25, C.UI_STAGGER,
                                    C.UI_DROP, rise=30.0)
            if alpha <= 0.01 or not line:
                continue
            im = game.font.render(line, True, (206, 208, 226))
            if alpha < 1.0:
                im = im.copy()
                im.set_alpha(int(255 * alpha))
            surf.blit(im, (cx - im.get_width() // 2, int(200 + i * 30 + off)))
        top = 200 + len(lines) * 30 + 16
    else:
        top = 210

    game._pause_rects = []
    for i, label in enumerate(items):
        off, alpha = ui.drop_in(game.ui_t, 1 + i * 0.5, C.UI_STAGGER, C.UI_DROP,
                                rise=34.0)
        rect = pygame.Rect(cx - 210, top + i * 46, 420, 40)
        game._pause_rects.append(rect)
        if alpha <= 0.01:
            continue
        sel = (i == min(game.pause_sel, len(items) - 1))
        y = rect.y + off
        if sel:
            palette.glow(surf, (rect.centerx, int(y + 20)), 180,
                         C.COL_PLAYER[0], 0.22 * alpha)
            box = pygame.Rect(rect.x, int(y), rect.width, rect.height)
            pygame.draw.rect(surf, (26, 30, 46), box, border_radius=12)
            pygame.draw.rect(surf, C.COL_PLAYER[0], box, 3, border_radius=12)
        im = game.font.render(label, True, C.COL_WHITE if sel else (158, 162, 190))
        if alpha < 1.0:
            im = im.copy()
            im.set_alpha(int(255 * alpha))
        surf.blit(im, (cx - im.get_width() // 2, int(y + 10)))
