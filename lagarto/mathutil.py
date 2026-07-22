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


def decay(value, dt, scale=1.0):
    """Countdown clamped at zero: ``max(0.0, value - dt * scale)``."""
    return max(0.0, value - dt * scale)


def pulse(t, freq=1.0):
    """Oscillate in [0, 1] at ``freq`` cycles per 2*pi -- same shape as
    ``0.5 + 0.5 * math.sin(t * freq)`` but names the intent."""
    return 0.5 + 0.5 * math.sin(t * freq)


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


def catmull_rom(p0, p1, p2, p3, t):
    """Point at ``t`` in [0,1] on the segment between ``p1`` and ``p2``,
    curved by the two neighbours ``p0``/``p3`` -- passes exactly through every
    control point, unlike Bezier (plans/01 #6, smooths a joint-chain body
    outline without moving the joints themselves)."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t
                  + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
