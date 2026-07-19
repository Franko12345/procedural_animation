"""Shared UI kit: panels, cards, chips, animated lists and tabs.

One visual language for the menu hub *and* the in-game screens (HUD, level-up
cards, camp), so everything feels like the same game. Drawing helpers return the
rects they used, which the caller stores for mouse hit-testing (positions are in
logical coordinates -- see ``display.to_logical``).
"""

import math
import pygame

from . import config as C
from . import palette

INK = (12, 14, 22)
LINE = (68, 72, 104)
TEXT = (238, 240, 252)
DIM = (158, 162, 190)


def panel(surf, rect, alpha=190, accent=None, radius=16):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((16, 18, 30, alpha))
    surf.blit(s, (rect.x, rect.y))
    pygame.draw.rect(surf, accent or LINE, rect, 2, border_radius=radius)


def title(surf, font, text, y, color, t=0.0, glow=True):
    cx = C.WIDTH // 2
    im = font.render(text, True, color)
    if glow:
        palette.glow(surf, (cx, y + im.get_height() // 2), im.get_width() * 0.55,
                     color, 0.22 + 0.10 * math.sin(t * 2))
    surf.blit(im, (cx - im.get_width() // 2, y))
    return im.get_height()


def chip(surf, font, text, x, y, color, filled=False):
    im = font.render(text, True, INK if filled else TEXT)
    r = pygame.Rect(x, y, im.get_width() + 26, im.get_height() + 10)
    if filled:
        pygame.draw.rect(surf, color, r, border_radius=999)
    else:
        pygame.draw.rect(surf, (24, 26, 40), r, border_radius=999)
        pygame.draw.rect(surf, color, r, 2, border_radius=999)
    pygame.draw.circle(surf, color if not filled else INK, (x + 13, r.centery), 5)
    surf.blit(im, (x + 22, y + 5))
    return r


def list_menu(surf, font, items, sel, top, accent, t=0.0, width=440, gap=56):
    """Vertical list with an animated selection highlight. Returns item rects."""
    cx = C.WIDTH // 2
    rects = []
    for i, label in enumerate(items):
        y = top + i * gap
        rect = pygame.Rect(cx - width // 2, y, width, 46)
        rects.append(rect)
        chosen = (i == sel)
        if chosen:
            pulse = 0.5 + 0.5 * math.sin(t * 5)
            palette.glow(surf, rect.center, width * 0.42, accent, 0.20 + 0.14 * pulse)
            pygame.draw.rect(surf, (26, 30, 46), rect, border_radius=12)
            pygame.draw.rect(surf, accent, rect, 3, border_radius=12)
            # sliding marker on the left edge
            bar = pygame.Rect(rect.x + 8, rect.y + 10, 5, rect.height - 20)
            pygame.draw.rect(surf, accent, bar, border_radius=3)
        im = font.render(label, True, TEXT if chosen else DIM)
        surf.blit(im, (cx - im.get_width() // 2, y + 8))
    return rects


def tabs(surf, font, labels, sel, y, accent):
    """Horizontal tab strip. Returns tab rects."""
    cx = C.WIDTH // 2
    ims = [font.render(l, True, TEXT if i == sel else DIM) for i, l in enumerate(labels)]
    w = sum(im.get_width() + 40 for im in ims)
    x = cx - w // 2
    rects = []
    for i, im in enumerate(ims):
        r = pygame.Rect(x, y, im.get_width() + 32, 38)
        rects.append(r)
        if i == sel:
            pygame.draw.rect(surf, (28, 32, 50), r, border_radius=10)
            pygame.draw.rect(surf, accent, r, 2, border_radius=10)
            pygame.draw.rect(surf, accent, (r.x + 10, r.bottom - 5, r.width - 20, 3),
                             border_radius=2)
        surf.blit(im, (r.centerx - im.get_width() // 2, y + 8))
        x += im.get_width() + 40
    return rects


def wrap(font, text, width):
    """Split ``text`` into lines that fit ``width`` pixels."""
    out, line = [], ''
    for word in text.split():
        test = (line + ' ' + word).strip()
        if font.size(test)[0] > width and line:
            out.append(line)
            line = word
        else:
            line = test
    if line:
        out.append(line)
    return out


def paragraph(surf, font, text, x, y, width, color=DIM, lh=24):
    for i, line in enumerate(wrap(font, text, width)):
        surf.blit(font.render(line, True, color), (x, y + i * lh))
    return y + len(wrap(font, text, width)) * lh


def footer(surf, font, text):
    im = font.render(text, True, (168, 172, 198))
    surf.blit(im, (C.WIDTH // 2 - im.get_width() // 2, C.HEIGHT - 40))


def veil(surf, alpha=120, color=(12, 10, 24)):
    s = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    s.fill((*color, alpha))
    surf.blit(s, (0, 0))
