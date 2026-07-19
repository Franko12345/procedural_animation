"""Colour + light helpers for a vivid, glowing look.

Two jobs:
  * generate saturated, randomised creature colours from HSV hue families;
  * fake the "glow / rim light" look (Animal Well) with cached additive sprites
    blitted with ``BLEND_RGB_ADD`` -- no shaders, cheap, and it makes bright
    elements pop off the ground so the palette never reads as "dead".
"""

import colorsys
import random

import pygame


def hsv(h, s, v):
    """h in [0,360], s/v in [0,1] -> (r,g,b) 0-255."""
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, max(0.0, min(1, s)), max(0.0, min(1, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


def vibrant(hue, sat=0.82, val=1.0):
    return hsv(hue, sat, val)


# hue families for creature colours (centre hue, spread)
FAMILIES = {
    'green':   (128, 34),
    'lime':    (95, 22),
    'cyan':    (185, 26),
    'blue':    (215, 26),
    'purple':  (270, 30),
    'magenta': (315, 26),
    'red':     (2, 16),
    'orange':  (28, 18),
    'yellow':  (50, 16),
    'teal':    (165, 22),
}


def random_in_family(family, rng=random, sat=(0.7, 0.95), val=(0.85, 1.0)):
    hue_c, spread = FAMILIES.get(family, (0, 180))
    h = hue_c + rng.uniform(-spread, spread)
    return hsv(h, rng.uniform(*sat), rng.uniform(*val))


def lighten(color, t):
    return tuple(int(c + (255 - c) * t) for c in color[:3])


def darken(color, t):
    return tuple(int(c * (1 - t)) for c in color[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --------------------------------------------------------------------------- #
#  Additive glow (cached radial sprites, blitted with BLEND_RGB_ADD)           #
# --------------------------------------------------------------------------- #

_GLOW_CACHE = {}


def _glow_sprite(radius, color):
    radius = int(radius)
    if radius < 2:
        radius = 2
    key = (radius, color)
    surf = _GLOW_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 10
        for i in range(steps, 0, -1):
            t = i / steps
            r = int(radius * t)
            # brighter toward the centre; additive so RGB is what matters
            fall = (1 - t) ** 1.6
            col = (int(color[0] * fall), int(color[1] * fall), int(color[2] * fall))
            pygame.draw.circle(surf, col, (radius, radius), r)
        _GLOW_CACHE[key] = surf
    return surf


def glow(surf, center, radius, color, intensity=1.0):
    """Additive radial glow. ``intensity`` scales the colour before caching-quantise."""
    if intensity != 1.0:
        color = (int(color[0] * intensity), int(color[1] * intensity), int(color[2] * intensity))
    # quantise colour to keep the cache small
    color = (color[0] & 0xF8, color[1] & 0xF8, color[2] & 0xF8)
    sprite = _glow_sprite(radius, color)
    surf.blit(sprite, (int(center[0] - radius), int(center[1] - radius)),
              special_flags=pygame.BLEND_RGB_ADD)
