"""Airborne behaviours: the straight-line flyer and the kamikaze bomber."""

import math
import random
from pygame import Vector2

from ...core import config as C
from ...audio import engine as audio
from ...core.mathutil import safe_norm


def fly_tick(creature, game, dt, target):
    """Straight-line hunter that ignores the horde (collision skips flyers).

    It has no legs to plant, so the read comes entirely from the hover bob --
    without it a flyer looks like a ground lizard sliding, and the player has
    no way to know it cannot be body-blocked.
    """
    creature.bob += dt * 7.0
    to = safe_norm(target.pos - creature.pos)
    dist = target.pos.distance_to(creature.pos)
    if dist < (creature.max_r + target.max_r) * 1.1 and creature.attack_cd <= 0:
        creature._contact(game, target)
    drift = Vector2(-to.y, to.x) * math.sin(creature.bob) * 0.35
    return safe_norm(to + drift), 1.15


def bomber_tick(creature, game, dt, target):
    """Kamikaze whose fuse, once lit, is a promise it cannot take back.

    The Mulliboom rule: after the fuse lights the bomber *slows down* and the
    blast happens wherever it ends up, so walking away always works. A charge
    that tracks you until it detonates is not a telegraph, it is just damage.
    """
    to = safe_norm(target.pos - creature.pos)
    dist = target.pos.distance_to(creature.pos)
    if creature.fuse > 0:
        creature.fuse -= dt
        if random.random() < dt * 40:
            game.fx.burst(creature.spine.joints[0], (255, 210, 120), 1, 90)
        if creature.fuse <= 0:
            creature.explode(game)
        return to, 0.25                       # committed and slow: dodgeable
    if dist < C.BOMBER_TRIGGER:
        creature.fuse = C.BOMBER_FUSE
        audio.play('nest', 0.5)
        game.fx.ring(creature.pos, (255, 170, 90))
    return to, 1.05
