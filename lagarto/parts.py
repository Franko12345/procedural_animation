"""Body-part drawing, driven by the genome.

Each function draws one appendage along a creature's spine, so the same code makes
an enemy look spiky and makes the player look spiky when it evolves. Everything is
built to read as *organic* (curved, tapered, alternating, gently swaying) rather
than geometric -- with a dark ink edge and a lighter rim to sit in the vivid style.
"""

import math
from pygame import Vector2
import pygame

from . import config as C
from . import palette
from .mathutil import safe_norm, lerp


def _poly(surf, cam, pts, fill, edge_w=1):
    sp = [cam.w2s(p) for p in pts]
    if len(sp) >= 3:
        pygame.draw.polygon(surf, fill, sp)
        pygame.draw.polygon(surf, C.COL_INK, sp, max(1, int(edge_w * cam.zoom)))
    return sp


def draw_spikes(surf, cam, creature):
    """Curved, tapered spines alternating left/right down the back."""
    g = creature.genome
    if g.spikes <= 0:
        return
    js, rad = creature.spine.joints, creature.spine.radii
    n = len(js)
    hi = palette.lighten(creature.color, 0.35)
    body = palette.lighten(creature.color, 0.05)
    length = creature.max_r * (0.9 + 0.35 * g.spikes)
    step = max(1, n // (5 + g.spikes * 2))
    side = 1
    for i in range(1, n - 2, step):
        fwd = safe_norm(js[i] - js[i + 1])
        back = -fwd
        perp = Vector2(-fwd.y, fwd.x) * side
        sway = math.sin(creature.wobble * 1.3 + i * 0.5) * 0.18
        base = js[i]
        base_a = base + fwd * (rad[i] * 0.42)
        base_b = base + back * (rad[i] * 0.42)
        tip = base + perp * (length * (1.0 + sway)) + back * (length * 0.45)
        mid = base + perp * (length * 0.55) + back * (length * 0.12)
        # tapered, slightly curved spine (base -> curved mid -> tip)
        _poly(surf, cam, [base_a, mid, tip, base_b], body, 1)
        pygame.draw.line(surf, hi, cam.w2s(base_b.lerp(tip, 0.15)),
                         cam.w2s(tip), max(1, int(cam.zoom)))
        side = -side


def draw_plates(surf, cam, creature):
    """Armour = overlapping scale chevrons pointing forward along the back."""
    g = creature.genome
    if g.plates <= 0:
        return
    js, rad = creature.spine.joints, creature.spine.radii
    edge = palette.lighten(creature.color, 0.28)
    w = max(1, int((1 + g.plates) * cam.zoom))
    for i in range(1, len(js) - 1):
        fwd = safe_norm(js[i] - js[i + 1])
        perp = Vector2(-fwd.y, fwd.x)
        c = js[i]
        left = c + perp * rad[i] * 0.72
        right = c - perp * rad[i] * 0.72
        tip = c + fwd * rad[i] * 0.55
        pygame.draw.lines(surf, edge, False,
                          [cam.w2s(left), cam.w2s(tip), cam.w2s(right)], w)


def draw_horns(surf, cam, creature):
    """Smooth, curved, tapered horns sweeping forward from the head."""
    g = creature.genome
    if g.horns <= 0:
        return
    head = creature.spine.joints[0]
    d = creature.spine.head_dir()
    perp = Vector2(-d.y, d.x)
    r = creature.max_r
    fill = palette.lighten(creature.color, 0.25)
    # real secondary motion (plans/01 #3): head_dir_spring lags a beat behind
    # the actual head direction, so this is ~0 moving straight and grows
    # during a turn -- horns lean toward where the head WAS pointing, like
    # hair blown back, instead of an idle canned wave
    hds = getattr(creature, 'head_dir_spring', None)
    lean = (hds.value - d) * 0.5 if hds is not None else Vector2()
    for k in range(min(g.horns, 3)):
        spread = 0.3 + k * 0.24
        # phase-offset sway (plans/01 #5): taller/farther horns lag a bit more,
        # same "wave down the chain" idea already used for spikes/fins/antennae
        sway = math.sin(creature.wobble * 1.6 + k * 0.9) * 0.12
        for s in (-1, 1):
            base = head + perp * (s * r * spread) - d * (r * 0.05)
            out = safe_norm(d * 0.85 + perp * (s * (0.4 + sway)) + lean)
            mid = base + out * (r * 0.72)
            tipdir = safe_norm(d * 0.95 - perp * (s * (0.12 - sway * 1.5)) + lean * 1.4)
            tip = mid + tipdir * (r * 0.7)
            wv = perp * (s * r * 0.17)
            _poly(surf, cam, [base + wv, mid + wv * 0.5, tip, mid - wv * 0.5, base - wv],
                  fill, 1)
            pygame.draw.line(surf, palette.lighten(fill, 0.4),
                             cam.w2s(base + wv * 0.6), cam.w2s(tip), max(1, int(cam.zoom)))


def draw_plates_body_tint(surf, cam, creature):
    pass


def draw_tail(surf, cam, creature):
    """Special tail tips: club (heavy ball) or sting (scorpion hook)."""
    g = creature.genome
    if g.tail not in ('club', 'sting'):
        return
    js = creature._cosmetic_joints() or creature.spine.joints
    tail = js[-1]
    d = safe_norm(js[-1] - js[-2])
    r = creature.max_r
    if g.tail == 'club':
        c = tail + d * r * 0.5
        cc = cam.w2s(c)
        rr = max(3, int(r * 0.95 * cam.zoom))
        pygame.draw.circle(surf, palette.lighten(creature.color, 0.08), cc, rr)
        pygame.draw.circle(surf, C.COL_INK, cc, rr, max(1, int(cam.zoom)))
        # little knobs so it reads as a mace, not a ball
        for a in range(0, 360, 60):
            k = c + Vector2(math.cos(math.radians(a)), math.sin(math.radians(a))) * r * 0.9
            pygame.draw.circle(surf, palette.lighten(creature.color, 0.25),
                               cam.w2s(k), max(1, int(r * 0.22 * cam.zoom)))
    else:  # sting
        base = tail
        curl = safe_norm(d + Vector2(-d.y, d.x) * 0.9)
        hook = tail + curl * r * 1.1
        tip = hook + safe_norm(Vector2(-d.y, d.x) * 0.4 - d) * r * 0.6
        col = palette.lighten(creature.color, 0.2)
        pygame.draw.line(surf, col, cam.w2s(base), cam.w2s(hook), max(2, int(r * 0.32 * cam.zoom)))
        pygame.draw.line(surf, col, cam.w2s(hook), cam.w2s(tip), max(2, int(r * 0.24 * cam.zoom)))
        pygame.draw.circle(surf, (255, 120, 130), cam.w2s(tip), max(2, int(r * 0.28 * cam.zoom)))


def draw_fins(surf, cam, creature):
    """Soft translucent fins along the sides (fish/aquatic)."""
    g = creature.genome
    if g.fins <= 0:
        return
    js, rad = creature.spine.joints, creature.spine.radii
    col = palette.lighten(creature.color, 0.3)
    n = len(js)
    for i in (n // 3, 2 * n // 3):
        if i + 1 >= n:
            continue
        fwd = safe_norm(js[i] - js[i + 1])
        perp = Vector2(-fwd.y, fwd.x)
        wob = math.sin(creature.wobble * 2 + i) * 0.3
        for s in (-1, 1):
            b1 = js[i] + perp * (s * rad[i])
            b2 = js[i + 1] + perp * (s * rad[i + 1])
            tip = js[i] + perp * (s * rad[i] * (2.3 + wob * s)) - fwd * rad[i]
            _poly(surf, cam, [b1, tip, b2], col, 1)


# --------------------------------------------------------------------------- #
#  Charm-driven parts (antennae, wings, extra eyes, spore sacs, nectar, fangs) #
# --------------------------------------------------------------------------- #

def draw_antennae(surf, cam, creature):
    head = creature.spine.joints[0]
    d = creature.spine.head_dir()
    perp = Vector2(-d.y, d.x)
    r = creature.max_r
    col = palette.darken(creature.color, 0.3)
    for s in (-1, 1):
        base = head + d * (r * 0.2) + perp * (s * r * 0.35)
        wig = math.sin(creature.wobble * 3 + s) * 0.3
        mid = base + d * (r * 0.9) + perp * (s * r * (0.5 + wig))
        tip = mid + d * (r * 0.5) + perp * (s * r * (0.8 + wig))
        pygame.draw.line(surf, col, cam.w2s(base), cam.w2s(mid), max(1, int(2 * cam.zoom)))
        pygame.draw.line(surf, col, cam.w2s(mid), cam.w2s(tip), max(1, int(cam.zoom)))
        pygame.draw.circle(surf, palette.lighten(creature.color, 0.4), cam.w2s(tip),
                           max(1, int(2 * cam.zoom)))


def draw_wings(surf, cam, creature):
    js, rad = creature.spine.joints, creature.spine.radii
    i = max(1, len(js) // 4)
    if i + 1 >= len(js):
        return
    fwd = safe_norm(js[i] - js[i + 1])
    perp = Vector2(-fwd.y, fwd.x)
    flap = 0.5 + 0.5 * abs(math.sin(creature.wobble * 7))
    col = palette.lighten(creature.color, 0.4)
    for s in (-1, 1):
        b1 = js[i] + perp * (s * rad[i] * 0.9)
        tip = js[i] + perp * (s * rad[i] * (2.7 * flap)) - fwd * rad[i] * 1.3
        b2 = js[i] - fwd * rad[i] * 1.9 + perp * (s * rad[i] * 0.7)
        _poly(surf, cam, [b1, tip, b2], col, 1)


def draw_extra_eyes(surf, cam, creature):
    n = creature.genome.extra_eyes
    head = creature.spine.joints[0]
    d = creature.spine.head_dir()
    perp = Vector2(-d.y, d.x)
    r = creature.max_r
    look = creature._look_dir()
    for k in range(n):
        s = -1 if k % 2 == 0 else 1
        row = k // 2
        ep = head + d * (r * (0.05 + row * 0.22)) + perp * (s * r * 0.38)
        pygame.draw.circle(surf, C.COL_WHITE, cam.w2s(ep), max(1, int(r * 0.24 * cam.zoom)))
        pygame.draw.circle(surf, C.COL_INK, cam.w2s(ep + look * (r * 0.08)),
                           max(1, int(r * 0.12 * cam.zoom)))


def draw_spore_sacs(surf, cam, creature):
    js, rad = creature.spine.joints, creature.spine.radii
    col = palette.vibrant(135, 0.7, 0.92)
    for i in range(2, len(js) - 2, 3):
        pu = 1 + 0.16 * math.sin(creature.wobble * 3 + i)
        p = cam.w2s(js[i])
        rr = max(2, int(rad[i] * 0.5 * cam.zoom * pu))
        palette.glow(surf, p, rr * 2, col, 0.4)
        pygame.draw.circle(surf, col, p, rr)
        pygame.draw.circle(surf, C.COL_INK, p, rr, max(1, int(cam.zoom)))


def draw_nectar_sac(surf, cam, creature):
    js = creature.spine.joints
    tail = js[-1]
    d = safe_norm(js[-1] - js[-2])
    r = creature.max_r
    cc = cam.w2s(tail + d * r * 0.4)
    rr = max(2, int(r * 0.7 * cam.zoom))
    col = palette.vibrant(45, 0.85, 1.0)
    palette.glow(surf, cc, rr * 2, col, 0.5)
    pygame.draw.circle(surf, col, cc, rr)
    pygame.draw.circle(surf, palette.lighten(col, 0.4), cc, max(1, int(rr * 0.4)))
    pygame.draw.circle(surf, C.COL_INK, cc, rr, max(1, int(cam.zoom)))


def draw_fangs(surf, cam, creature):
    head = creature.spine.joints[0]
    d = creature.spine.head_dir()
    perp = Vector2(-d.y, d.x)
    r = creature.max_r
    for s in (-1, 1):
        base = head + d * (r * 0.7) + perp * (s * r * 0.28)
        tip = base + d * (r * 0.55) - perp * (s * r * 0.04)
        pygame.draw.line(surf, (245, 245, 252), cam.w2s(base), cam.w2s(tip),
                         max(1, int(2.4 * cam.zoom)))


def draw_all(surf, cam, creature):
    """Draw every part the genome declares (called from Creature.draw)."""
    g = creature.genome
    if g.wings:
        draw_wings(surf, cam, creature)
    if g.plates:
        draw_plates(surf, cam, creature)
    if g.spore_sacs:
        draw_spore_sacs(surf, cam, creature)
    if g.fins:
        draw_fins(surf, cam, creature)
    if g.spikes:
        draw_spikes(surf, cam, creature)
    if g.tail in ('club', 'sting'):
        draw_tail(surf, cam, creature)
    if g.nectar_sac:
        draw_nectar_sac(surf, cam, creature)
    if g.horns:
        draw_horns(surf, cam, creature)
    if g.antennae:
        draw_antennae(surf, cam, creature)
    if g.extra_eyes:
        draw_extra_eyes(surf, cam, creature)
    if g.fangs:
        draw_fangs(surf, cam, creature)
