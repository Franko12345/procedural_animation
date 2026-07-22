"""Collectibles: skittering Bug (main food), Fruit (heal), Egg (hatches a friend)."""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import palette
from .mathutil import clamp, vfrom_angle, safe_norm, decay

TAU = C.TAU


class Bug:
    kind = 'bug'

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.vel = vfrom_angle(random.uniform(0, 360)) * 30
        self.dead = False
        self.t = random.uniform(0, TAU)
        self.r = 6
        self.hop = 0.0
        self.color = C.COL_BUG

    def update(self, dt, game):
        self.t += dt * 12
        self.hop = decay(self.hop, dt)
        p = game.nearest_player(self.pos)
        if p and p.pos.distance_to(self.pos) < 150:
            self.vel += safe_norm(self.pos - p.pos) * 400 * dt
            if self.hop <= 0:
                self.hop = 0.25
        else:
            self.vel *= math.exp(-1.5 * dt)
            if random.random() < dt * 2:
                self.vel += vfrom_angle(random.uniform(0, 360)) * 40
        if self.vel.length() > 120:
            self.vel.scale_to_length(120)
        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, 8, C.WORLD_W - 8)
        self.pos.y = clamp(self.pos.y, 8, C.WORLD_H - 8)

    def draw(self, surf, cam):
        legw = math.sin(self.t) * 4
        base = cam.w2s(self.pos)
        for s in (-1, 1):
            for lo in (-3, 0, 3):
                a = cam.w2s(self.pos + Vector2(lo, 0))
                b = cam.w2s(self.pos + Vector2(lo + legw * s, 7 * s))
                pygame.draw.line(surf, C.COL_INK, a, b, max(1, int(cam.zoom)))
        rr = max(2, int(self.r * cam.zoom))
        palette.glow(surf, base, rr * 3.0, self.color, 0.5)
        pygame.draw.circle(surf, self.color, base, rr)
        pygame.draw.circle(surf, palette.lighten(self.color, 0.4), base, rr, max(1, int(cam.zoom)))


class Fruit:
    kind = 'fruit'

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.dead = False
        self.t = random.uniform(0, TAU)
        self.r = 9
        self.color = C.COL_FRUIT

    def update(self, dt, game):
        self.t += dt * 3

    def draw(self, surf, cam):
        wob = 1 + math.sin(self.t) * 0.12
        p = cam.w2s(self.pos)
        rr = int(max(2, int(self.r * cam.zoom)) * wob)
        pygame.draw.circle(surf, self.color, p, rr)
        pygame.draw.circle(surf, C.COL_INK, p, rr, max(1, int(cam.zoom)))
        pygame.draw.line(surf, (90, 200, 90), p, (p[0], p[1] - int(rr * 1.4)),
                         max(1, int(2 * cam.zoom)))


class Egg:
    kind = 'egg'

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.dead = False
        self.t = random.uniform(0, TAU)
        self.r = 11
        self.color = C.COL_EGG

    def update(self, dt, game):
        self.t += dt * 5

    def draw(self, surf, cam):
        p = cam.w2s(self.pos)
        wob = math.sin(self.t) * 2
        rr = max(3, int(self.r * cam.zoom))
        rect = pygame.Rect(0, 0, int(rr * 1.5), int(rr * 1.9))
        rect.center = (p[0] + wob, p[1])
        pygame.draw.ellipse(surf, self.color, rect)
        pygame.draw.ellipse(surf, C.COL_INK, rect, max(1, int(cam.zoom)))
        pygame.draw.circle(surf, C.COL_FRIEND, rect.center, max(1, int(2 * cam.zoom)))
