"""Vector / angle helpers.

Uses the standard-library ``math`` module and pygame's C-accelerated
``Vector2`` on purpose: per-call ``numpy`` scalar ops are slower here because of
their dispatch overhead. These run in the hottest per-joint loops.
"""

import math
from pygame import Vector2


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def approach(cur, target, rate, dt):
    """Frame-rate-independent exponential smoothing toward ``target``."""
    return target + (cur - target) * math.exp(-rate * dt)


def vfrom_angle(deg, length=1.0):
    r = math.radians(deg)
    return Vector2(math.cos(r) * length, math.sin(r) * length)


def angle_of(v):
    return math.degrees(math.atan2(v.y, v.x))


def clamp_angle(a, ref, max_delta):
    """Keep angle ``a`` within +/- ``max_delta`` of ``ref`` (degrees, wrapped)."""
    diff = (a - ref + 180.0) % 360.0 - 180.0
    diff = clamp(diff, -max_delta, max_delta)
    return ref + diff


def ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)


def safe_norm(v):
    l = v.length()
    return Vector2(v) / l if l > 1e-6 else Vector2(1, 0)
