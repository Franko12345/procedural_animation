"""Reusable secondary-motion primitives (Fase A of ``plans/01_animacao_procedural_avancada.md``).

Generic building blocks only -- nothing here reads ``Lizard``/``Genome`` directly,
so any system (tail, horns, boss telegraphs, future rigs) can hang a spring off
its own state without this module knowing what it's animating.
"""

import math
from pygame import Vector2


class SpringDamper:
    """1D critically-ish-damped spring. ``target`` moves, ``value`` chases it
    with overshoot -- the overshoot IS the secondary motion (a part keeps
    swinging after the body that carries it stops)."""
    __slots__ = ('value', 'target', 'vel', 'stiffness', 'damping')

    def __init__(self, value=0.0, stiffness=8.0, damping=0.85):
        self.value = value
        self.target = value
        self.vel = 0.0
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt):
        diff = self.target - self.value
        self.vel += diff * self.stiffness * dt
        self.vel *= 1.0 - self.damping * dt
        self.value += self.vel * dt
        return self.value


class Vector2Spring:
    """2D counterpart of ``SpringDamper`` -- used for a joint chasing a moving
    anchor point (tail joints chasing where follow-the-leader would put them)."""
    __slots__ = ('value', 'target', 'vel', 'stiffness', 'damping')

    def __init__(self, value, stiffness=8.0, damping=0.85):
        self.value = Vector2(value)
        self.target = Vector2(value)
        self.vel = Vector2(0, 0)
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt):
        diff = self.target - self.value
        self.vel += diff * self.stiffness * dt
        self.vel *= 1.0 - self.damping * dt
        self.value += self.vel * dt
        return self.value


class PhaseOscillator:
    """A traveling wave along a chain: ``sin(t*speed + i*phase_gap)``. Segment 0
    is the base (small offset), segment n-1 the tip (full amplitude visible)."""
    __slots__ = ('speed', 'amplitude', 'phase_gap', 'time')

    def __init__(self, speed=4.0, amplitude=0.3, phase_gap=0.8):
        self.speed = speed
        self.amplitude = amplitude
        self.phase_gap = phase_gap
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def offset(self, i):
        return math.sin(self.time * self.speed + i * self.phase_gap) * self.amplitude


class Anticipation:
    """Generic wind-up timer: call ``trigger(action)``, poll ``is_active`` while
    it counts down, then ``update()`` returns the action exactly once when the
    timer expires. Distinct from ``boss.py``'s FSM states -- this is for the
    smaller "flinch before you move" beats (steer changing direction, a lunge)
    that don't deserve a whole state machine."""
    __slots__ = ('duration', 'timer', 'action')

    def __init__(self, duration=0.25):
        self.duration = duration
        self.timer = 0.0
        self.action = None

    def trigger(self, action=True):
        self.action = action
        self.timer = self.duration

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            return None
        if self.action:
            a = self.action
            self.action = None
            return a
        return None

    @property
    def is_active(self):
        return self.timer > 0

    @property
    def progress(self):
        """0 (just triggered) -> 1 (about to fire); 1 when idle."""
        if self.duration <= 0:
            return 1.0
        return 1.0 - max(0.0, self.timer) / self.duration
