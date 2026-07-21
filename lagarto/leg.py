"""Leg: procedural foot-planting + two-bone IK.

A foot stays planted until the body drags its rest position too far away; then it
takes an eased, arcing step to a spot slightly ahead of where the body is going.
Diagonal partners never step at the same time, giving a natural lizard gait.
"""

import math
from pygame import Vector2

from .mathutil import clamp, ease_out, angle_of, vfrom_angle, safe_norm


class Leg:
    def __init__(self, attach_idx, side, side_off, fwd_off, seg_len,
                 step_len, step_dur, step_h, rest_angle=None, reach=None):
        self.idx = attach_idx
        self.side = side               # +1 right, -1 left
        self.side_off = side_off
        self.fwd_off = fwd_off
        self.seg = seg_len             # length of each of the two bones
        self.step_len = step_len
        self.step_dur = step_dur
        self.step_h = step_h
        # radial mode (spiders): a fixed angle around the body + a reach distance,
        # instead of a lateral (side/forward) offset. Leaves paired legs unchanged.
        self.rest_angle = rest_angle
        self.reach = reach if reach is not None else side_off
        self.foot = None               # planted world position
        self.stepping = False
        self.t = 0.0
        self.p_from = Vector2()
        self.p_to = Vector2()
        self.partner = None            # diagonal partner (won't both step at once)
        self.lift = 0.0

    def rest_target(self, spine, vel, pull=1.0):
        """``pull`` < 1 gathers the foot in toward the body (anticipation --
        a real crouch/coil instead of a body-only squash), > 1 reaches it
        further out (the launch)."""
        i = self.idx
        j = spine.joints
        fwd = safe_norm(j[i - 1] - j[i]) if i >= 1 else spine.head_dir()
        if self.rest_angle is not None:
            ang = angle_of(fwd) + self.rest_angle
            base = j[i] + vfrom_angle(ang, self.reach * pull)
            return base + vel * 0.10
        perp = Vector2(-fwd.y, fwd.x) * self.side
        base = j[i] + fwd * (self.fwd_off * pull) + perp * (self.side_off * pull)
        return base + vel * 0.12       # anticipate where the body is going

    def init_foot(self, spine):
        self.foot = Vector2(self.rest_target(spine, Vector2()))

    def update(self, spine, vel, dt, on_plant, pull=1.0):
        target = self.rest_target(spine, vel, pull)
        if self.foot is None:
            self.foot = Vector2(target)
        if self.stepping:
            self.t += dt / self.step_dur
            if self.t >= 1.0:
                self.foot = Vector2(self.p_to)
                self.stepping = False
                self.lift = 0.0
                if on_plant:
                    on_plant(self.foot)
            else:
                self.foot = self.p_from.lerp(self.p_to, ease_out(self.t))
                self.lift = math.sin(self.t * math.pi) * self.step_h
        else:
            partner_busy = self.partner.stepping if self.partner else False
            if self.foot.distance_to(target) > self.step_len and not partner_busy:
                self.stepping = True
                self.t = 0.0
                self.p_from = Vector2(self.foot)
                self.p_to = target + safe_norm(target - self.foot) * (self.step_len * 0.5)

    def solve(self, root):
        """Two-bone IK (law of cosines); the foot lifts along an arc mid-step."""
        if self.foot is None:
            return Vector2(root), Vector2(root)
        foot = Vector2(self.foot)
        if self.lift:
            foot += Vector2(0, -self.lift)
        l = self.seg
        d = clamp(root.distance_to(foot), 0.01, l * 2 - 0.01)
        base = angle_of(foot - root)
        cos_a = clamp((d * d) / (2 * l * d), -1, 1)   # l1 == l2 == l
        a = math.degrees(math.acos(cos_a))
        knee = root + vfrom_angle(base - a * self.side, l)
        return knee, foot
