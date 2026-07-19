"""Font loading: pick the nicest available face and cache by (role, size).

Text is always rendered anti-aliased; combined with ``display.present``'s
smooth scaling that keeps the UI crisp at 1x/2x/3x and in fullscreen.
"""

import pygame

# Ordered by preference: humanist/geometric faces read better for a cartoon game
# than the default bitmap fallback. First one actually installed wins.
_PREFERRED = [
    'Poppins', 'Nunito', 'Quicksand', 'Rubik', 'Montserrat',
    'Ubuntu', 'Cantarell', 'Noto Sans', 'Open Sans', 'Liberation Sans',
    'DejaVu Sans',
]

_cache = {}
_chosen = None


def _pick():
    global _chosen
    if _chosen is not None:
        return _chosen
    try:
        available = {n.lower().replace(' ', '') for n in pygame.font.get_fonts()}
    except Exception:
        available = set()
    for name in _PREFERRED:
        if name.lower().replace(' ', '') in available:
            _chosen = name
            break
    else:
        _chosen = ''          # '' -> pygame's default font
    return _chosen


def get(size, bold=False):
    """A cached, anti-aliased-ready font at ``size``."""
    key = (size, bold)
    f = _cache.get(key)
    if f is None:
        name = _pick()
        try:
            f = pygame.font.SysFont(name, size, bold=bold) if name else \
                pygame.font.Font(None, int(size * 1.15))
        except Exception:
            f = pygame.font.Font(None, int(size * 1.15))
        _cache[key] = f
    return f


def name():
    return _pick() or 'default'
