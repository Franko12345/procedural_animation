"""Melee-family behaviours: the plain chase, the pounce, and the frog hop."""

import random
from pygame import Vector2

from ...core.mathutil import approach, safe_norm, random_dir


def melee_tick(creature, game, dt, target):
    dist = target.pos.distance_to(creature.pos)
    if dist < (creature.max_r + target.max_r) * 1.1 and creature.attack_cd <= 0:
        creature._contact(game, target)
    return safe_norm(target.pos - creature.pos), 1.0


def lunge_tick(creature, game, dt, target):
    dist = target.pos.distance_to(creature.pos)
    to = safe_norm(target.pos - creature.pos)
    if creature.lunge_t > 0:              # telegraphing (wind-up)
        creature.lunge_t -= dt
        creature.squat_bias = 0.8          # crouching to pounce -- see integrate()
        if creature.lunge_t <= 0:
            creature.vel = to * creature.max_speed * 3.2      # pounce!
            creature.lunge_t = -0.25
            creature.squat_bias = 1.55     # explode out of the crouch
            game.fx.spark_burst(creature.pos, creature.color, 8, 260)
        return Vector2(), 0.0
    if creature.lunge_t < 0:             # mid-pounce, coast
        creature.lunge_t += dt
        if dist < (creature.max_r + target.max_r) * 1.1 and creature.attack_cd <= 0:
            creature._contact(game, target)
        return Vector2(), 0.0
    if dist < 220 and creature.attack_cd <= 0:
        creature.lunge_t = 0.45          # start wind-up
        creature.attack_cd = 1.8
        return Vector2(), 0.0
    return to, 0.95


def hop(creature, dt):
    # frogs: periodic forward hops instead of a smooth glide. The tell is
    # the LEGS gathering in under the body (leg_pull), not a body-only
    # squash -- a squash-only cue read as "wobbling side to side" since
    # nothing else in the silhouette visibly moved (feedback: the width
    # change alone wasn't legible as "about to jump").
    creature.wander_t -= dt
    if 0 < creature.wander_t < 0.18:           # about to launch -- gather in
        creature.leg_pull = approach(creature.leg_pull, 0.55, 16, dt)
        creature.squat_bias = 0.85
    if creature.wander_t <= 0:
        creature.wander_t = random.uniform(0.7, 1.3)
        creature.wander = random_dir()
        creature.vel += creature.wander * creature.max_speed * 1.4
        creature.leg_pull = 1.6                # legs kick out on launch
        creature.squat_bias = 1.4              # pop out of the crouch on launch
    return Vector2()
