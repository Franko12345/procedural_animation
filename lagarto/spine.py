"""Spine: a follow-the-leader chain with a bend limit, plus body-outline geometry.

Grown from the original ``procedural_animation.py``: joint[0] is the head and
leads; every following joint is pulled to a fixed distance behind the previous
one, and its direction is clamped so the body cannot kink onto itself.
"""

from pygame import Vector2

from .mathutil import angle_of, clamp_angle, vfrom_angle, safe_norm, lerp

# thickness profile sampled along the body (head -> tail); kept above zero at the
# tail so the two body rims never cross into a sharp "blade".
RADII_PROFILE = [0.56, 0.84, 1.0, 1.0, 0.95, 0.88, 0.79, 0.69,
                 0.60, 0.51, 0.43, 0.35, 0.28, 0.22]


def build_radii(n, maxr):
    prof = RADII_PROFILE
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(prof) - 1)
        lo = int(t)
        hi = min(lo + 1, len(prof) - 1)
        out.append(lerp(prof[lo], prof[hi], t - lo) * maxr)
    return out


class Spine:
    def __init__(self, pos, n, link, radii, bend=30.0):
        self.joints = [Vector2(pos) for _ in range(n)]
        self.link = link
        self.radii = list(radii)
        self.bend = bend

    def resolve(self, head):
        j = self.joints
        j[0].update(head)
        for i in range(1, len(j)):
            a = angle_of(j[i] - j[i - 1])
            if i >= 2:
                prev = angle_of(j[i - 1] - j[i - 2])
                a = clamp_angle(a, prev, self.bend)
            j[i] = j[i - 1] + vfrom_angle(a, self.link)

    def head_dir(self):
        return safe_norm(self.joints[0] - self.joints[1])

    def outline(self, scale=1.0):
        """Left/right rim points for the filled body polygon."""
        j, rad = self.joints, self.radii
        n = len(j)
        left, right = [], []
        for i in range(n):
            fwd = safe_norm(j[i] - j[i + 1]) if i < n - 1 else safe_norm(j[i - 1] - j[i])
            perp = Vector2(-fwd.y, fwd.x) * (rad[i] * scale)
            left.append(j[i] + perp)
            right.append(j[i] - perp)
        return left, right

    def _cap(self, center, outward, r, reverse):
        """Semicircle of points around ``center`` opening along ``outward``."""
        base = angle_of(outward)
        angs = [-90, -55, -25, 0, 25, 55, 90]
        if reverse:
            angs = angs[::-1]
        return [center + vfrom_angle(base + a, r * (1.05 if abs(a) < 30 else 0.92))
                for a in angs]

    def head_cap(self, scale=1.0):
        """Rounded snout points, ordered right-rim -> front -> left-rim."""
        return self._cap(self.joints[0], self.head_dir(), self.radii[0] * scale, False)

    def tail_cap(self, scale=1.0):
        """Rounded tail points, ordered left-rim -> back -> right-rim."""
        n = len(self.joints)
        back = safe_norm(self.joints[n - 1] - self.joints[n - 2])
        return self._cap(self.joints[n - 1], back, self.radii[n - 1] * scale, True)

    def body_polygon(self, scale=1.0):
        """Single non-self-crossing ring around the whole body."""
        left, right = self.outline(scale)
        return left + self.tail_cap(scale) + right[::-1] + self.head_cap(scale)
