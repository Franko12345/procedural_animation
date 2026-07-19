"""Procedural icons for weapons, mutations and charms.

The game ships no image files, so icons are *drawn* with the same vocabulary as
the rest of the art (filled shape + lighter rim + ink edge + a soft glow). Every
icon is a function that fills a circle of radius ``r`` around ``c``; unknown ids
fall back to a plain disc, so adding content never crashes the UI.
"""

import math
import pygame

from . import config as C
from . import palette
from .mathutil import vfrom_angle

INK = C.COL_INK


def _disc(s, c, r, col):
    pygame.draw.circle(s, col, c, r)
    pygame.draw.circle(s, palette.lighten(col, 0.45), c, r, max(1, r // 6))
    pygame.draw.circle(s, INK, c, r, max(1, r // 8))


def _drop(s, c, r, col):
    """Teardrop pointing up-right (spit/venom)."""
    pts = [(c[0], c[1] - r), (c[0] + r * 0.72, c[1] + r * 0.35),
           (c[0], c[1] + r * 0.9), (c[0] - r * 0.72, c[1] + r * 0.35)]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, INK, pts, max(1, r // 8))
    pygame.draw.circle(s, palette.lighten(col, 0.5), (c[0] - r // 4, c[1]), max(1, r // 5))


def _star(s, c, r, col, spikes=8, inner=0.45):
    pts = []
    for k in range(spikes * 2):
        rad = r if k % 2 == 0 else r * inner
        pts.append(c + vfrom_angle(k * (180 / spikes) - 90, rad))
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, INK, pts, max(1, r // 9))


def _rings(s, c, r, col, n=3):
    for k in range(n):
        rr = int(r * (1 - k * 0.28))
        if rr > 1:
            pygame.draw.circle(s, palette.lighten(col, 0.15 * k), c, rr, max(1, r // 7))


def _bubbles(s, c, r, col):
    for dx, dy, f in ((-0.4, 0.25, 0.5), (0.35, 0.3, 0.42), (0.0, -0.25, 0.62),
                      (0.45, -0.3, 0.3)):
        pygame.draw.circle(s, col, (int(c[0] + dx * r), int(c[1] + dy * r)),
                           max(2, int(r * f * 0.6)))
        pygame.draw.circle(s, INK, (int(c[0] + dx * r), int(c[1] + dy * r)),
                           max(2, int(r * f * 0.6)), 1)


def _arrow(s, c, r, col, ang=-45):
    tip = c + vfrom_angle(ang, r)
    tail = c + vfrom_angle(ang + 180, r * 0.85)
    l = c + vfrom_angle(ang + 140, r * 0.6)
    rr = c + vfrom_angle(ang - 140, r * 0.6)
    pygame.draw.polygon(s, col, [tip, l, tail, rr])
    pygame.draw.polygon(s, INK, [tip, l, tail, rr], max(1, r // 9))


def _heart(s, c, r, col):
    pygame.draw.circle(s, col, (int(c[0] - r * 0.38), int(c[1] - r * 0.2)), int(r * 0.5))
    pygame.draw.circle(s, col, (int(c[0] + r * 0.38), int(c[1] - r * 0.2)), int(r * 0.5))
    pygame.draw.polygon(s, col, [(c[0] - r * 0.86, c[1] - r * 0.05),
                                 (c[0] + r * 0.86, c[1] - r * 0.05),
                                 (c[0], c[1] + r * 0.95)])


def _bolt(s, c, r, col):
    pts = [(c[0] - r * 0.15, c[1] - r), (c[0] + r * 0.55, c[1] - r * 0.1),
           (c[0] + r * 0.1, c[1] - r * 0.05), (c[0] + r * 0.35, c[1] + r),
           (c[0] - r * 0.55, c[1] + r * 0.05), (c[0] - r * 0.05, c[1])]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, INK, pts, max(1, r // 9))


def _clock(s, c, r, col):
    pygame.draw.circle(s, col, c, r)
    pygame.draw.circle(s, INK, c, r, max(1, r // 7))
    pygame.draw.line(s, INK, c, (c[0], c[1] - r * 0.6), max(2, r // 6))
    pygame.draw.line(s, INK, c, (c[0] + r * 0.45, c[1]), max(2, r // 7))


def _spikes_icon(s, c, r, col):
    for k, ang in enumerate((-120, -90, -60)):
        base_l = c + vfrom_angle(ang - 22, r * 0.55)
        base_r = c + vfrom_angle(ang + 22, r * 0.55)
        tip = c + vfrom_angle(ang, r * 1.05)
        pygame.draw.polygon(s, col, [base_l, tip, base_r])
        pygame.draw.polygon(s, INK, [base_l, tip, base_r], 1)
    pygame.draw.arc(s, palette.darken(col, 0.2),
                    (c[0] - r, c[1] - r * 0.35, r * 2, r * 1.3), math.pi, 2 * math.pi,
                    max(2, r // 5))


def _plates_icon(s, c, r, col):
    for k in range(3):
        y = c[1] - r * 0.5 + k * r * 0.5
        pygame.draw.lines(s, col, False,
                          [(c[0] - r * 0.75, y + r * 0.25), (c[0], y - r * 0.2),
                           (c[0] + r * 0.75, y + r * 0.25)], max(2, r // 5))


def _horns_icon(s, c, r, col):
    for sgn in (-1, 1):
        pts = [(c[0] + sgn * r * 0.15, c[1] + r * 0.7),
               (c[0] + sgn * r * 0.55, c[1] - r * 0.1),
               (c[0] + sgn * r * 0.85, c[1] - r * 0.9),
               (c[0] + sgn * r * 0.45, c[1] - r * 0.2),
               (c[0] + sgn * r * 0.05, c[1] + r * 0.55)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, INK, pts, 1)


def _legs_icon(s, c, r, col):
    pygame.draw.circle(s, col, c, int(r * 0.42))
    pygame.draw.circle(s, INK, c, int(r * 0.42), 1)
    for a in (-140, -100, -60, 140, 100, 60):
        mid = c + vfrom_angle(a, r * 0.72)
        tip = mid + vfrom_angle(a + (18 if a < 0 else -18), r * 0.5)
        pygame.draw.lines(s, col, False, [c, mid, tip], max(2, r // 6))


def _wings_icon(s, c, r, col):
    for sgn in (-1, 1):
        pts = [c, (c[0] + sgn * r, c[1] - r * 0.55), (c[0] + sgn * r * 0.85, c[1] + r * 0.5)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, INK, pts, 1)


def _orbit(s, c, r, col):
    pygame.draw.circle(s, palette.darken(col, 0.35), c, int(r * 0.85), max(1, r // 9))
    for a in (0, 120, 240):
        p = c + vfrom_angle(a, r * 0.85)
        pygame.draw.circle(s, col, (int(p.x), int(p.y)), max(2, r // 4))
        pygame.draw.circle(s, INK, (int(p.x), int(p.y)), max(2, r // 4), 1)


def _puddle(s, c, r, col):
    rect = pygame.Rect(c[0] - r, c[1] - r * 0.5, r * 2, r * 1.1)
    pygame.draw.ellipse(s, col, rect)
    pygame.draw.ellipse(s, INK, rect, max(1, r // 8))
    for dx, dy in ((-0.35, -0.05), (0.3, 0.1), (0.0, 0.2)):
        pygame.draw.circle(s, palette.lighten(col, 0.4),
                           (int(c[0] + dx * r), int(c[1] + dy * r)), max(1, r // 6))


def _fan(s, c, r, col):
    for a in (-40, 0, 40):
        pygame.draw.arc(s, col, (c[0] - r, c[1] - r, r * 2, r * 2),
                        math.radians(a - 18), math.radians(a + 18), max(2, r // 4))
    _arrow(s, (c[0] - r * 0.3, c[1]), int(r * 0.4), palette.lighten(col, 0.3), 0)


def _antennae(s, c, r, col):
    for sgn in (-1, 1):
        base = (c[0] + sgn * r * 0.2, c[1] + r * 0.7)
        mid = (c[0] + sgn * r * 0.55, c[1] - r * 0.1)
        tip = (c[0] + sgn * r * 0.9, c[1] - r * 0.75)
        pygame.draw.lines(s, col, False, [base, mid, tip], max(2, r // 6))
        pygame.draw.circle(s, palette.lighten(col, 0.4), (int(tip[0]), int(tip[1])),
                           max(2, r // 5))


def _eyes(s, c, r, col):
    for dx, dy, f in ((-0.45, -0.1, 0.42), (0.45, -0.1, 0.42), (0.0, 0.45, 0.3)):
        p = (int(c[0] + dx * r), int(c[1] + dy * r))
        pygame.draw.circle(s, (245, 245, 250), p, max(2, int(r * f)))
        pygame.draw.circle(s, INK, p, max(1, int(r * f * 0.45)))


def _fangs(s, c, r, col):
    for sgn in (-1, 1):
        pts = [(c[0] + sgn * r * 0.2, c[1] - r * 0.5),
               (c[0] + sgn * r * 0.6, c[1] - r * 0.45),
               (c[0] + sgn * r * 0.35, c[1] + r * 0.75)]
        pygame.draw.polygon(s, (245, 245, 250), pts)
        pygame.draw.polygon(s, INK, pts, 1)
    pygame.draw.circle(s, col, (c[0], int(c[1] - r * 0.72)), max(2, r // 4))


def _sac(s, c, r, col):
    rect = pygame.Rect(c[0] - r * 0.62, c[1] - r * 0.5, r * 1.24, r * 1.35)
    pygame.draw.ellipse(s, col, rect)
    pygame.draw.ellipse(s, INK, rect, max(1, r // 8))
    pygame.draw.circle(s, palette.lighten(col, 0.5),
                       (int(c[0] - r * 0.2), int(c[1] - r * 0.1)), max(1, r // 5))


def _club(s, c, r, col):
    pygame.draw.line(s, palette.darken(col, 0.25), (c[0] - r * 0.8, c[1] + r * 0.8),
                     (c[0] + r * 0.1, c[1] - r * 0.1), max(2, r // 4))
    pygame.draw.circle(s, col, (int(c[0] + r * 0.35), int(c[1] - r * 0.35)), int(r * 0.55))
    pygame.draw.circle(s, INK, (int(c[0] + r * 0.35), int(c[1] - r * 0.35)), int(r * 0.55), 1)
    for a in range(0, 360, 72):
        p = vfrom_angle(a, r * 0.62) + pygame.Vector2(c[0] + r * 0.35, c[1] - r * 0.35)
        pygame.draw.circle(s, palette.lighten(col, 0.3), (int(p.x), int(p.y)), max(1, r // 6))


def _sting(s, c, r, col):
    pygame.draw.lines(s, col, False,
                      [(c[0] - r * 0.8, c[1] + r * 0.6), (c[0], c[1] + r * 0.1),
                       (c[0] + r * 0.55, c[1] - r * 0.45)], max(2, r // 4))
    tip = (int(c[0] + r * 0.8), int(c[1] - r * 0.8))
    pygame.draw.circle(s, (255, 120, 130), tip, max(2, r // 4))
    pygame.draw.circle(s, INK, tip, max(2, r // 4), 1)


def _tongue(s, c, r, col):
    pygame.draw.lines(s, (235, 90, 120), False,
                      [(c[0] - r * 0.85, c[1] + r * 0.5), (c[0], c[1]),
                       (c[0] + r * 0.7, c[1] - r * 0.55)], max(2, r // 5))
    pygame.draw.circle(s, (255, 140, 160), (int(c[0] + r * 0.75), int(c[1] - r * 0.6)),
                       max(2, r // 5))


def _plus_one(s, c, r, col, font=None):
    pygame.draw.line(s, col, (c[0] - r * 0.6, c[1]), (c[0] + r * 0.6, c[1]), max(2, r // 4))
    pygame.draw.line(s, col, (c[0], c[1] - r * 0.6), (c[0], c[1] + r * 0.6), max(2, r // 4))


def _expand(s, c, r, col):
    pygame.draw.circle(s, col, c, int(r * 0.32))
    pygame.draw.circle(s, col, c, int(r * 0.7), max(1, r // 8))
    pygame.draw.circle(s, palette.darken(col, 0.2), c, r, max(1, r // 9))


ICONS = {
    # weapons
    'cuspe': _drop, 'ferrao': _arrow, 'teia': _star, 'esporos': _bubbles,
    'feromonio': _rings, 'sopro': _fan, 'enxame': _orbit, 'acido': _puddle,
    # mutations / passives
    'health': _heart, 'speed': _bolt, 'dash': _arrow, 'energy': _bolt,
    'regen': _heart, 'xp': _star, 'tongue': _tongue, 'thorns': _spikes_icon,
    'spikes': _spikes_icon, 'plates': _plates_icon, 'horns': _horns_icon,
    'legs': _legs_icon, 'club': _club, 'venom': _drop, 'wings': _wings_icon,
    'might': _bolt, 'area': _expand, 'haste': _clock, 'amount': _plus_one,
    # charms
    'antenas': _antennae, 'olhos': _eyes, 'carapaca': _plates_icon,
    'asas': _wings_icon, 'nectar': _sac, 'glandula': _sac, 'presas': _fangs,
    'espinhos': _spikes_icon, 'clava': _club,
}


def draw(surf, key, center, radius, color, glow=True):
    """Draw icon ``key`` centred at ``center`` with ``radius`` in ``color``."""
    c = (int(center[0]), int(center[1]))
    r = int(radius)
    if glow:
        palette.glow(surf, c, r * 1.9, color, 0.35)
    fn = ICONS.get(key)
    if fn is None:
        _disc(surf, c, r, color)
        return
    try:
        fn(surf, c, r, color)
    except Exception:
        _disc(surf, c, r, color)
