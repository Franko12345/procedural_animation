"""Display: a fixed logical surface scaled to the window (window-size presets).

The game always draws to a logical ``C.WIDTH x C.HEIGHT`` surface. Each frame
``present()`` scales that surface onto the real window, letterboxed so the aspect
ratio is preserved in fullscreen. This is what makes 1x/2x/3x window presets
possible -- ``pygame.SCALED`` would pin the logical size to the window size.

Because the window and the logical surface no longer share coordinates, every
mouse position must go through ``to_logical()`` (aim *and* UI clicks).
"""

import pygame

from . import config as C

SCALES = (1, 2, 3)

_screen = None          # the real window surface
_logical = None         # fixed-size surface everything draws to
_scaled = None          # cached scale buffer (None when 1:1)
_scale = 2
_fullscreen = False
_vsync = True
_rect = (0, 0, C.WIDTH, C.HEIGHT)     # where the logical surface lands on screen


def init(scale=2, fullscreen=False, vsync=True):
    global _logical
    # the window must exist before .convert() can pick a pixel format
    apply(scale=scale, fullscreen=fullscreen, vsync=vsync)
    _logical = pygame.Surface((C.WIDTH, C.HEIGHT)).convert()
    return _logical


def apply(scale=None, fullscreen=None, vsync=None):
    """(Re)create the window. Returns the logical surface."""
    global _screen, _scale, _fullscreen, _vsync
    if scale is not None:
        _scale = scale if scale in SCALES else 2
    if fullscreen is not None:
        _fullscreen = bool(fullscreen)
    if vsync is not None:
        _vsync = bool(vsync)

    flags = pygame.FULLSCREEN if _fullscreen else 0
    size = (0, 0) if _fullscreen else (C.WIDTH * _scale, C.HEIGHT * _scale)
    try:
        _screen = pygame.display.set_mode(size, flags, vsync=1 if _vsync else 0)
    except pygame.error:
        _screen = pygame.display.set_mode(size, flags)
    _recompute()
    return _logical


def _recompute():
    """Letterbox: largest fit that preserves the aspect ratio; cache the scale buffer."""
    global _rect, _scaled
    sw, sh = _screen.get_size()
    k = min(sw / C.WIDTH, sh / C.HEIGHT)
    w, h = max(1, int(C.WIDTH * k)), max(1, int(C.HEIGHT * k))
    _rect = ((sw - w) // 2, (sh - h) // 2, w, h)
    _scaled = None if (w, h) == (C.WIDTH, C.HEIGHT) else pygame.Surface((w, h)).convert()


def surface():
    return _logical


def screen():
    return _screen


def get_scale():
    return _scale


def is_fullscreen():
    return _fullscreen


def get_vsync():
    return _vsync


def toggle_fullscreen():
    return apply(fullscreen=not _fullscreen)


def cycle_scale():
    i = SCALES.index(_scale) if _scale in SCALES else 1
    return apply(scale=SCALES[(i + 1) % len(SCALES)], fullscreen=False)


def toggle_vsync():
    return apply(vsync=not _vsync)


def handle_resize():
    _recompute()


def present():
    """Scale the logical surface onto the window and flip.

    The art is vector-ish (polygons, circles, anti-aliased text), so we use
    ``smoothscale`` -- nearest-neighbour made scaled-up text look jagged.
    """
    x, y, w, h = _rect
    if (x, y) != (0, 0):
        _screen.fill((0, 0, 0))              # letterbox bars
    if _scaled is None:
        _screen.blit(_logical, (x, y))
    else:
        pygame.transform.smoothscale(_logical, (w, h), _scaled)
        _screen.blit(_scaled, (x, y))
    pygame.display.flip()


def to_logical(pos):
    """Window pixel -> logical pixel (undo letterbox + scale). Clamped in-bounds."""
    x, y, w, h = _rect
    if w <= 0 or h <= 0:
        return (0, 0)
    lx = (pos[0] - x) * C.WIDTH / w
    ly = (pos[1] - y) * C.HEIGHT / h
    return (int(max(0, min(C.WIDTH - 1, lx))), int(max(0, min(C.HEIGHT - 1, ly))))


def mouse_logical():
    return to_logical(pygame.mouse.get_pos())
