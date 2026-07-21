---
name: Procedural Animation Master
description: "Comprehensive skill for procedural animation in 2D games. Covers spring-damper systems, inverse kinematics, follow-the-leader chains, phase offsets, spline dynamics, ground adaptation, anticipation, procedural posing, two-skeleton architecture, and emergent personality. Based on analysis of Rain World, Binding of Isaac, Enter the Gungeon, and production codebase in pygame."
version: 0.1.0
---

# Procedural Animation Master

## Core Philosophy

Procedural animation generates motion at runtime through code and math rather than pre-authored keyframes. It trades CPU for adaptability: characters respond to terrain, physics, and game state in real time. The goal is not photorealism but **readability of intent** — the player should infer what a creature is thinking from how it moves.

### Key Principles

1. **AI behavior = visible animation.** When a lizard hunts, you see it see you. When it can't reach you, it gets visibly frustrated. Cause and effect must be visible.
2. **Two skeletons.** Separate the physical simulation (few joints, collision, hitbox) from the cosmetic layer (many joints, spring overshoot, smooth curves). The physical skeleton drives gameplay; the cosmetic skeleton makes it look alive.
3. **Secondary motion IS personality.** The way a tail drags, horns lag, or plates rattle on a turn communicates weight, mood, and species identity without a single line of dialogue.
4. **Every parameter tunable by genome.** Size, weight, damping, stiffness, wobble speed — all per-species knobs so different creatures feel different to fight and watch.

### Games That Defined the Techniques

| Game | Technique | Why It Matters |
|------|-----------|----------------|
| **Rain World** | Two skeletons + spring-damper chains | The gold standard. Creatures feel alive because physics + cosmetic layers are separate. Personality emerges from AI behavior being visible in the body. |
| **Grow Home** | Physics-driven limb placement | Each foot is placed by code; the body follows via joint constraints. Character feels weighty and clumsy. |
| **Gang Beasts** | Full ragdoll motor control | Pure physics as gameplay. Characters are floppy, unpredictable, hilarious. |
| **The Majesty of Colors** | Tentacle IK | Early indie IK: each segment rotates to reach a target point. Simple math, huge expressiveness. |
| **Binding of Isaac** | Anticipation + telegraph clarity | Every boss attack has a wind-up that communicates exactly what's coming. The body language IS the telegraph. |
| **Enter the Gungeon** | Phase-based boss design + mood systems | Bosses change pattern sets at HP thresholds. Mood affects speed and behavior. |
| **Hollow Knight** | Procedural secondary motion + boss posing | Charms, tails, capes all have spring-based follow-through. Bosses use body pose to communicate state. |
| **Spelunky** | Verlet integration for ropes/ chains | Interactive physics objects that feel consistent because they use the same simulation every time. |

---

## Technique 1: Spring-Damper Systems

### The Problem

Body parts (tails, horns, ears, clothing) that are rigidly attached to joints look dead. When the body stops, they stop instantly with no overshoot. The fix: make each part **chase** its target position with a spring that allows overshoot.

### Mathematics

A spring-damper is a simplified mass-spring system:

```
F = stiffness × (target - current)           // Hooke's law (restoring force)
vel += F × dt                                 // Integrate force → velocity
vel *= (1 - damping × dt)                     // Damping (energy dissipation)
current += vel × dt                           // Integrate velocity → position
```

The damping coefficient determines behavior:
- **Underdamped** (damping < critical): overshoots and oscillates before settling
- **Critically damped** (damping ~2√stiffness): fastest return without overshoot
- **Overdamped** (damping > critical): slow return, no overshoot — feels heavy

For animation we almost always want **underdamped**: overshoot IS the secondary motion.

### Base Implementation

```python
# 1D spring — for angles, scalars, amplitudes
class SpringDamper:
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


# 2D spring — for positions, joint chasing
class Vector2Spring:
    def __init__(self, value, stiffness=8.0, damping=0.75):
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
```

### Parameter Tuning Guide

| Element | Stiffness | Damping | Effect |
|---------|-----------|---------|--------|
| Tail (base) | 12 | 0.75 | Medium overshoot, 2-3 oscillations |
| Tail (tip) | 6 | 0.65 | Large overshoot, 3-4 oscillations, feels loose |
| Horn/rigid part | 16 | 0.85 | Stiff, little overshoot, feels heavy |
| Fin/soft tissue | 5 | 0.60 | Very loose, large sway |
| Ear/wattle | 8 | 0.70 | Medium-soft |
| Plate/armour | 14 | 0.80 | Rigid but can rattle on sharp turns |
| Mouth/jaw | 12 | 0.75 | Snappy open/close with tiny overshoot |

### Application: Tail Overshoot (codebase pattern)

```python
# Cosmetically override the last N tail joints
TAIL_SPRING_JOINTS = 4
TAIL_SPRING_STIFFNESS = 10.0
TAIL_SPRING_MAX_LAG = 0.45    # fraction of max_r

# In rebuild_body():
tip = Vector2(self.spine.joints[-1])
self.tail_spring = Vector2Spring(tip, stiffness=TAIL_SPRING_STIFFNESS, damping=0.75)

# Per-frame in update_secondary_springs():
self.tail_spring.target = self.spine.joints[-1]
self.tail_spring.update(dt)

# Cosmetic joint override:
js = list(self.spine.joints)       # COPY — don't modify physical joints
lag = self.tail_spring.value - js[-1]
# Cap extreme lag to prevent stretching on teleport/dash
if lag.length_squared() > (max_r * TAIL_SPRING_MAX_LAG) ** 2:
    lag.scale_to_length(max_r * TAIL_SPRING_MAX_LAG)
for i in range(n - k, n):
    js[i] = js[i] + lag * t        # blend 0..1 toward tip
```

### Spring Chain (Tail with Propagation)

Single spring only moves the tip. For a wave that propagates, use N springs in sequence:

```python
class SpringChain:
    def __init__(self, n_joints, stiffness_start=12, stiffness_end=6, damping=0.75):
        self.joints = [Vector2(0, 0) for _ in range(n_joints)]
        self.springs = []
        for i in range(n_joints):
            s = stiffness_start - i * (stiffness_start - stiffness_end) / (n_joints - 1)
            self.springs.append(Vector2Spring(Vector2(0, 0), stiffness=s, damping=damping))

    def follow(self, anchor, dt):
        """Chain chases anchor at joint[0]; each subsequent joint chases the previous."""
        self.springs[0].target = anchor
        self.springs[0].update(dt)
        self.joints[0] = self.springs[0].value
        for i in range(1, len(self.springs)):
            self.springs[i].target = self.joints[i - 1]
            self.springs[i].update(dt)
            self.joints[i] = self.springs[i].value
```

### Exact Spring (Frame-Rate Independent)

From [The Orange Duck](https://theorangeduck.com/page/spring-roll-call) — critical for deterministic springs:

```python
def spring_damper_exact(x, v, x_goal, halflife, dt):
    """Frame-rate-independent spring. halflife = time to decay 50%."""
    y = math.log(2) / halflife if halflife > 0 else 1
    j0 = x - x_goal
    j1 = v + j0 * y
    eydt = math.exp(-y * dt)
    x = eydt * (j0 + j1 * dt) + x_goal
    v = eydt * (v - j1 * y * dt)
    return x, v
```

### Game Examples

- **Rain World**: every lizard tail uses spring-damper chains. The base is stiffer, the tip looser — tapering stiffness creates natural-looking waves.
- **Hollow Knight**: the Knight's cape, Quirrel's mask tassels, Hornet's needle — all spring-dampers on 2D bone positions.
- **Dead Cells**: every enemy has spring-based secondary motion on cloth, hair, and weapons.

---

## Technique 2: Follow-the-Leader Chain

### The Problem

A spine with N joints needs to maintain length constraints while following the head. The naive approach (move each joint toward the previous by link distance) works but produces **no secondary motion**.

### Implementation

```python
class Spine:
    def __init__(self, pos, n, link, radii, bend=30.0):
        self.joints = [Vector2(pos) for _ in range(n)]
        self.link = link
        self.radii = list(radii)
        self.bend = bend              # max angle change between adjacent segments

    def resolve(self, head):
        """Pull the chain from the head; each joint follows at fixed distance."""
        self.joints[0].update(head)
        for i in range(1, len(self.joints)):
            a = angle_of(self.joints[i] - self.joints[i - 1])
            if i >= 2:
                prev = angle_of(self.joints[i - 1] - self.joints[i - 2])
                a = clamp_angle(a, prev, self.bend)    # prevent kinking
            self.joints[i] = self.joints[i - 1] + vfrom_angle(a, self.link)
```

### Bend Limit

The `bend` parameter prevents the body from folding onto itself. 26 deg is good for lizard bodies; 45+ for snakes/tentacles; 10 for armored creatures.

### Why No Spring in the Base Chain

The physical spine must be deterministic for collision/hit-test. Springs go in the **cosmetic layer** (Technique 10).

### Game Examples

- **Every creature in Rain World**: all use follow-the-leader chains for their bodies, with varying bend limits per species.
- **Snake games**: classic chain with sine-wave offset for slithering.

---

## Technique 3: Phase Offsets and Traveling Waves

### The Problem

Parts that oscillate (fins, antennae, spikes, wings) need to look organic, not robotic. A single global sine wave makes everything pulse in unison. Real creatures have **waves that travel** down chains.

### The Math

For chain segment `i` at time `t`:
```
offset(i, t) = sin(t × speed + i × phase_gap) × amplitude
```

Each segment has a slightly different phase, creating a ripple that appears to travel.

### Implementation

```python
class PhaseOscillator:
    def __init__(self, speed=4.0, amplitude=0.3, phase_gap=0.8):
        self.speed = speed
        self.amplitude = amplitude
        self.phase_gap = phase_gap
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def offset(self, i):
        return math.sin(self.time * self.speed + i * self.phase_gap) * self.amplitude
```

### Parameter Guide

| Parameter | Effect | Typical Range |
|-----------|--------|---------------|
| `speed` | How fast the wave travels | 1 (slow idle) — 12 (rapid flap) |
| `amplitude` | How wide the wave swings | 0.05 (subtle) — 0.5 (dramatic) |
| `phase_gap` | How far apart adjacent segments are | 0.3 (smooth wave) — 1.5 (choppy) |

### Application: Parts (codebase pattern)

```python
# Before — global wobble, manual phase:
sway = math.sin(creature.wobble * 1.3 + i * 0.5) * 0.18

# After — dedicated oscillator per part type:
if not hasattr(creature, 'spike_osc'):
    creature.spike_osc = PhaseOscillator(speed=2.6, amplitude=0.18, phase_gap=0.5)
creature.spike_osc.update(dt)
sway = creature.spike_osc.offset(i)
```

### Where Each Oscillator Goes

| Part | Speed | Amplitude | Phase Gap | Notes |
|------|-------|-----------|-----------|-------|
| Spikes | 2.6 | 0.18 | 0.5 | Alternating sides, subtle |
| Horns | 3.2 | 0.12 | 0.9 | Higher horns lag more |
| Fins | 4.0 | 0.30 | 1.0 | Soft, large amplitude |
| Antennae | 5.0 | 0.30 | 1.5 | Fast, twitchy |
| Wings | 7.0 | 0.50 | — | abs(sin) = no negative flap |
| Tail ripple | 2.2 | 0.12×max_r | 0.9 | Traveling wave on overshoot |
| Spore sacs | 3.0 | 0.16 | 1.0 | Breathing pulse |
| Tentacle mantra | 2.4 | 34.0deg | 0.9 | Big angular swing |

### Superposition

Combine two oscillators for complex motion:
```python
breathe = breath_osc.offset(i) * 0.5    # slow, subtle
swim = swim_osc.offset(i) * 1.0          # fast, visible
total = breathe + swim                    # looks alive, not mechanical
```

### Game Examples

- **Rain World**: all fins, antennae, and tail frills use phase-offset waves. Each species has unique speed/amplitude.
- **ABZU**: fish fins use traveling sine waves. Entire schools are one oscillator with different phases per fish.
- **Centipede enemies**: each segment's legs are phase-offset by segment index, creating the signature ripple.

---

## Technique 4: Inverse Kinematics (2-Bone Analytical)

### The Problem

A leg has two bones (thigh + shin) and needs to place its foot at a target position while keeping both bones at fixed length. The standard solution: the Law of Cosines.

### Mathematics

Given two bones of equal length `L` and a target distance `d` from hip to foot:

```
cos(θ) = (d² + L² - L²) / (2 × L × d) = d / (2L)
θ = acos(d / (2L))
```

Where θ is the angle from hip-to-target direction to the thigh bone.

### Implementation

```python
def solve_2bone_ik(root, foot, seg_len, side):
    """Two-bone IK via Law of Cosines. Returns knee position."""
    l = seg_len
    d = clamp(root.distance_to(foot), 0.01, l * 2 - 0.01)
    base = angle_of(foot - root)
    cos_a = clamp((d * d) / (2 * l * d), -1, 1)
    a = math.degrees(math.acos(cos_a))
    knee = root + vfrom_angle(base - a * side, l)
    return knee, foot
```

### Foot Planting with Step Trigger

A foot doesn't slide — it plants until the body moves far enough, then takes an arcing step:

```python
class Leg:
    def rest_target(self, spine, vel, pull=1.0):
        """Where the foot WANTS to be (relative to body + velocity anticipation)."""
        i = self.idx
        fwd = safe_norm(spine.joints[i - 1] - spine.joints[i])
        perp = Vector2(-fwd.y, fwd.x) * self.side
        base = spine.joints[i] + fwd * (self.fwd_off * pull) + perp * (self.side_off * pull)
        return base + vel * 0.12       # anticipate movement direction

    def update(self, spine, vel, dt, on_plant, pull=1.0):
        target = self.rest_target(spine, vel, pull)
        if self.stepping:
            self.t += dt / self.step_dur
            if self.t >= 1.0:
                self.foot = Vector2(self.p_to)
                self.stepping = False
                if on_plant: on_plant(self.foot)
            else:
                self.foot = self.p_from.lerp(self.p_to, ease_out(self.t))
                self.lift = math.sin(self.t * math.pi) * self.step_h
        else:
            partner_busy = self.partner.stepping if self.partner else False
            if self.foot.distance_to(target) > self.step_len and not partner_busy:
                self.stepping = True
                self.p_from = Vector2(self.foot)
                self.p_to = target + safe_norm(target - self.foot) * (self.step_len * 0.5)
```

### Diagonal Gait (Quadruped)

```python
# Pair legs diagonally so opposite front/back move together:
for i in range(pairs):
    j = (i + 1) % pairs
    legs[2*i].partner = legs[2*j + 1]       # left i <-> right j
    legs[2*i + 1].partner = legs[2*j]       # right i <-> left j
```

### Spider Radial Legs

```python
def rest_target(self, spine, vel):
    fwd = safe_norm(spine.joints[idx - 1] - spine.joints[idx])
    ang = angle_of(fwd) + self.rest_angle    # fixed angle around body center
    base = spine.joints[idx] + vfrom_angle(ang, self.reach)
    return base + vel * 0.10
```

### Game Examples

- **Rain World**: every lizard leg uses 2-bone IK with foot planting. Diagonal gait emerges from partner rules.
- **Grow Home**: BUD's legs use IK to place feet on procedural terrain. The body is hauled by the feet, not the other way around.
- **Spider enemies**: radial IK with 8 legs phased in 4 pairs, creating realistic gait.

---

## Technique 5: FABRIK (Multi-Joint IK)

### The Problem

2-bone IK is analytical and fast but only works for exactly 2 bones. For tentacles, tails, spider legs with 3+ segments, you need an iterative solver.

### The Algorithm

FABRIK (Forward And Backward Reaching Inverse Kinematics) by Aristidou & Lasenby (2011):

1. **Forward pass**: Set joint[N-1] (end effector) to target. For i = N-2 down to 0: project joint[i] toward joint[i+1] at link distance.
2. **Backward pass**: Set joint[0] to root. For i = 1 to N-1: project joint[i] toward joint[i-1] at link distance.
3. Repeat until end effector is within tolerance or max iterations reached.

No angles or matrices — just line projections. Fast, stable, realistic.

### Implementation

```python
def fabrik(joints, link_lengths, target, tolerance=0.01, max_iter=10):
    """Modifies joints in-place to reach target. Returns True if reached."""
    n = len(joints)
    root = Vector2(joints[0])     # snapshot original root
    for _ in range(max_iter):
        # Forward: pull end effector to target
        joints[-1] = Vector2(target)
        for i in range(n - 2, -1, -1):
            d = joints[i + 1] - joints[i]
            d.scale_to_length(link_lengths[i])
            joints[i] = joints[i + 1] - d

        # Backward: pull root back to original
        joints[0] = Vector2(root)
        for i in range(1, n):
            d = joints[i] - joints[i - 1]
            d.scale_to_length(link_lengths[i - 1])
            joints[i] = joints[i - 1] + d

        if joints[-1].distance_to(target) < tolerance:
            return True
    return False
```

### Bend Constraints with FABRIK

```python
# After each forward/backward pass, clamp joint angles:
for i in range(1, n - 1):
    a = angle_of(joints[i] - joints[i - 1])
    b = angle_of(joints[i + 1] - joints[i])
    clamped_b = clamp_angle(b, a, self.bend)  # keep in cone
    # Rotate joint[i+1] around joint[i] to match clamped angle
```

### Game Examples

- **Unreal Engine**: built-in FABRIK node for animation blueprints.
- **The Majesty of Colors**: tentacle IK (CCD, predecessor to FABRIK).
- **Rain World**: vulture wings use multi-joint IK to reach target wingtip positions.
- **Spider enemies** (3+ leg segments): FABRIK gives natural-looking leg placement on uneven terrain.

---

## Technique 6: Catmull-Rom Spline (Smooth Body Outline)

### The Problem

A follow-the-leader chain with few joints produces visible vertices in the body outline. For continuous-bodied creatures (snakes, worms, octopus arms), you need smooth interpolation between joints.

### The Math

Catmull-Rom is a cubic spline that passes through ALL control points (unlike Bezier):

```
q(t) = 0.5 × (
    (2 × P1) +
    (-P0 + P2) × t +
    (2×P0 - 5×P1 + 4×P2 - P3) × t² +
    (-P0 + 3×P1 - 3×P2 + P3) × t³
)
```

Where `t` in [0,1] and `P0, P1, P2, P3` are four consecutive joints.

### Implementation

```python
def catmull_rom(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t
                  + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)

# Smooth body outline:
SMOOTH_SUBDIV = 3   # extra points per segment

def smooth_samples(joints, radii):
    n = len(joints)
    pts, rads = [joints[0]], [radii[0]]
    for i in range(n - 1):
        p0, p1, p2 = joints[max(0, i-1)], joints[i], joints[i+1]
        p3 = joints[min(n - 1, i + 2)]
        for s in range(1, SMOOTH_SUBDIV + 1):
            t = s / SMOOTH_SUBDIV
            pts.append(catmull_rom(p0, p1, p2, p3, t))
            rads.append(lerp(radii[i], radii[i+1], t))
    return pts, rads
```

### Stroke vs Fill

Smooth outlines for filled polygons can self-intersect on tight curls. Solution: draw as **quad strip** (one quad per adjacent pair of left/right rim points) instead of one big polygon. Pygame's fill rule opens holes where the ring crosses itself.

```python
# Build quads from smooth samples:
left = [pt + perp * radii[i] for i, pt in enumerate(pts)]
right = [pt - perp * radii[i] for i, pt in enumerate(pts)]
# Draw each quad individually:
for i in range(len(pts) - 1):
    quad = [left[i], left[i+1], right[i+1], right[i]]
    pygame.draw.polygon(surf, fill_color, quad)
# Stroke as a single ring (self-crossing harmless for outlines):
ring = left + tail_cap + right[::-1] + head_cap
pygame.draw.polygon(surf, outline_color, ring, outline_width)
```

### Radial Profile

Body thickness should taper from head to tail. Use a sampled profile:

```python
RADII_PROFILE = [0.56, 0.84, 1.0, 1.0, 0.95, 0.88, 0.79, 0.69,
                 0.60, 0.51, 0.43, 0.35, 0.28, 0.22]

def build_radii(n, maxr):
    prof = RADII_PROFILE
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(prof) - 1)
        lo, hi = int(t), min(int(t) + 1, len(prof) - 1)
        out.append(lerp(prof[lo], prof[hi], t - lo) * maxr)
    return out
```

### Game Examples

- **Rain World**: tentacles, lizard tails, and vulture wings all use Catmull-Rom for smooth outlines.
- **Snake enemies**: continuous body with smooth interpolation between physics joints.
- **Octopus arms**: each tentacle is a follow-the-leader chain with Catmull-Rom rendering.

---

## Technique 7: Anticipation and Wind-Up

### The Problem

Instant direction changes and attacks feel snappy but weightless. Players need a **visual tell** before an action to read it and react. This is the single most important technique for fair gameplay.

### The Pattern

```
[trigger] → [wind-up] → [action] → [recovery]
             0.1-0.4s           0.1-0.2s
```

During wind-up:
- Body squashes (coils energy)
- Part moves backward (arm pulls back, tail raises)
- Glow/particles build up
- Spring stiffness increases (tension)

### Implementation

```python
class Anticipation:
    def __init__(self, duration=0.25):
        self.duration = duration
        self.timer = 0.0
        self.action = None    # callable or True

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
            return a           # fires exactly once when timer expires
        return None

    @property
    def is_active(self):
        return self.timer > 0

    @property
    def progress(self):
        """0 (just triggered) → 1 (about to fire)"""
        if self.duration <= 0:
            return 1.0
        return 1.0 - max(0.0, self.timer) / self.duration
```

### Wind-Up Durations by Action

| Action | Wind-up | Visual Tell |
|--------|---------|-------------|
| Direction change | 0.08s | Decelerate, tilt body |
| Dash (player) | 0.08s | Squash down, particles at feet |
| Melee attack | 0.2s | Pull arm/body back, arch |
| Ranged attack | 0.35s | Glow in mouth, aim line |
| Boss charge | 0.5s | Head low, tail straight, glow |
| Jump/leap | 0.12s | Squash, crouch |
| Tongue strike | 0.1s | Mouth opens, eyes focus |
| Lunge (spider) | 0.45s | Body lowers, legs coil |

### Why Wind-Up Works

Isaac and Gungeon boss design principle: **the telegraph IS the attack's hitbox preview**. The player should know exactly what's coming and where, just not when they'll have time to dodge. Boss patterns always telegraph for >=27 frames (0.45s at 60fps) before firing.

### Game Examples

- **Binding of Isaac**: every boss attack has a distinct wind-up animation. Mom's foot shadow, Gurdy's jump squash, Monstro's hop tell.
- **Enter the Gungeon**: boss wind-ups are unmistakable. Cannon's aim line, Ammoconda's coil before charge.
- **Hollow Knight**: every enemy attack has a wind-up. The player learns to recognize the tell and react.
- **Rain World**: creatures telegraph intentions through body language — a lizard's head tracking before a lunge.

---

## Technique 8: Two-Skeleton Architecture

### The Problem

Hit-testing, collision, and gameplay logic need deterministic positions. But animation needs overshoot, smooth curves, and cosmetic effects. If you put springs on the physical joints, the hitbox drifts — attacks miss, feet float.

### The Solution

Maintain two separate joint arrays:

```
Physical Skeleton (sim_joints):
  - Few joints (3-12)
  - Follow-the-leader chain (deterministic)
  - No springs, no overshoot
  - Used for: hit-testing, leg IK, eye positions, collision

Cosmetic Skeleton (cos_joints):
  - Many joints (16-32)
  - Interpolated from physical + spring overshoot
  - Catmull-Rom smoothing between physical joints
  - Used for: body polygon, part attachment, tail wave
```

### Implementation

```python
def cosmetic_joints(spine, tail_spring, tail_spring_joints=4, max_lag=0.45):
    """Returns cosmetic positions for drawing ONLY."""
    if tail_spring is None:
        return None
    js = list(spine.joints)      # COPY — physical stays untouched
    n = len(js)
    k = min(tail_spring_joints, n - 1)
    lag = tail_spring.value - js[-1]
    # Cap extreme lag
    cap = spine.max_r * max_lag
    if lag.length_squared() > cap * cap:
        lag.scale_to_length(cap)
    for i in range(n - k, n):
        t = (i - (n - k - 1)) / k         # 0 → 1 toward tip
        js[i] = js[i] + lag * t
    return js
```

### Full Cosmetic Skeleton (for the future)

```python
class CosmeticSkeleton:
    def __init__(self, n_cosmetic=32):
        self.n = n_cosmetic
        self.points = [Vector2(0, 0) for _ in range(n_cosmetic)]
        self.velocities = [Vector2(0, 0) for _ in range(n_cosmetic)]

    def follow(self, sim_joints, spring_stiffness=10, spring_damping=0.8, dt=1/60):
        """Each cosmetic point spring-chases its ideal position on the physical chain."""
        for i in range(self.n):
            t = i / (self.n - 1)
            # Ideal position = Catmull-Rom sample of physical chain
            target = self._sample_chain(sim_joints, t)
            # Spring chase
            diff = target - self.points[i]
            self.velocities[i] += diff * spring_stiffness * dt
            self.velocities[i] *= 1.0 - spring_damping * dt
            self.points[i] += self.velocities[i] * dt
```

### Single Choke Point

```python
def update_secondary_springs(self):
    """Only ONE place to tick all cosmetic springs."""
    if self.tail_spring is not None:
        self.tail_spring.target = self.spine.joints[-1]
        self.tail_spring.update(dt)
    if self.head_dir_spring is not None:
        self.head_dir_spring.target = self.spine.head_dir()
        self.head_dir_spring.update(dt)
    # Future: ear_spring, plate_springs, antenna_springs all go here

def reset_secondary_springs(self):
    """Snap cosmetic to physical — call after teleport/reposition."""
    if self.tail_spring is not None:
        self.tail_spring.value = self.tail_spring.target = Vector2(self.spine.joints[-1])
    if self.head_dir_spring is not None:
        hd = self.spine.head_dir()
        self.head_dir_spring.value = self.head_dir_spring.target = Vector2(hd)
```

**Critical rule**: Any code path that moves a creature without calling `integrate()` (menu previews, bestiary, character select) MUST call `update_secondary_springs()` or `reset_secondary_springs()` itself.

### Game Examples

- **Rain World**: the entire game runs on this architecture. Physical skeleton = beads connected by sticks. Cosmetic skeleton = sprites masked by orientation + stretch.
- **Dead Cells**: physical hitbox is a simple capsule; cosmetic layer has full spring-based secondary motion on cloth and hair.

---

## Technique 9: Ground Adaptation

### The Problem

On flat ground, IK foot placement works perfectly. On any terrain with elevation changes, feet float above or clip through the ground. The fix: raycast down from the foot's ideal position to find actual ground height.

### Implementation

```python
def ground_adapt(foot_target, world, max_step=8):
    """Returns adjusted foot position snapped to terrain."""
    ground_y = world.ground_y_at(foot_target.x)
    diff = ground_y - foot_target.y
    if abs(diff) > max_step:      # treat as stair/ledge
        foot_target.y = ground_y
    return foot_target
```

### Pelvis Spring

When one foot is on higher ground, the pelvis should tilt to compensate:

```python
# Average foot height → pelvis offset
left_foot_y = left_leg.foot.y
right_foot_y = right_leg.foot.y
avg_foot_y = (left_foot_y + right_foot_y) / 2
pelvis_offset = avg_foot_y + body_height / 2    # ideal pelvis Y
self.pelvis_spring.target = pelvis_offset
```

### Body Tilt on Slopes

```python
def ground_angle(self, world):
    fore = world.ground_y_at(self.pos.x + self.max_r * 0.3)
    aft = world.ground_y_at(self.pos.x - self.max_r * 0.3)
    return math.atan2(fore - aft, self.max_r * 0.6)
```

### Game Examples

- **Rain World**: every creature raycasts feet to terrain. The pelvis spring makes lizards look like they're actually standing on the ground.
- **Spelunky 2**: mount physics use ground adaptation for riding creatures over uneven terrain.
- **Hollow Knight**: ground slam attacks adapt to terrain height.

---

## Technique 10: Emergent Personality via Mood

### The Problem

Bosses that cycle through patterns with no visible emotion feel like turrets. The player should infer mood from body language — and mood should affect mechanics.

### Design Principles (from Rain World + Gungeon)

1. **Mood must be readable at a glance.** Color change, body arch height, tail position, speed — all change with mood.
2. **Mood must affect gameplay.** Enraged = faster + shorter wind-ups but patterns are more aggressive. Cornered = defensive patterns.
3. **Mood transitions must be smooth.** No instant switches — use spring-blended pose transitions over 0.3s.
4. **Frustration is a mood.** When the player kites too long without attacking, the boss gets frustrated and uses faster/longer-range attacks.

### Implementation

```python
class BossPersonality:
    def __init__(self, pattern_weights=None):
        self.mood_speed = {
            'calm': 1.0, 'agitated': 1.3, 'enraged': 1.6,
            'frustrated': 1.4, 'cornered': 0.8,
        }
        self.mood_colors = {
            'calm': None, 'agitated': (255, 180, 50),
            'enraged': (255, 50, 50), 'frustrated': (200, 50, 255),
            'cornered': (50, 100, 255),
        }
        self.tell_mult = {'enraged': 0.65, 'agitated': 0.8}
        self.pattern_weights = pattern_weights or {}

    def windup_mult(self, mood):
        return self.tell_mult.get(mood, 1.0)    # enraged = shorter tells

    def glow_color(self, mood, base_color):
        return palette.mix(base_color, self.mood_colors.get(mood), 0.4)

    def weight(self, pattern_id, mood):
        return self.pattern_weights.get(pattern_id, {}).get(mood, 1.0)
```

### Mood State Machine

```
Mood transitions checked per-frame:
  - dist < cornered_dist  → 'cornered'
  - HP < 33%              → 'enraged'
  - HP < 66%              → 'agitated'
  - no_hit_t > 5s         → 'frustrated'
  - else                  → 'calm'
```

### Mood → Body Pose (codebase pattern)

```python
BOSS_MOOD_SPRING_MULT = {
    'calm': 1.0, 'agitated': 1.25, 'enraged': 1.6,
    'frustrated': 1.15, 'cornered': 1.4,
}

def apply_mood_pose(self, mood):
    """Tighten springs when agitated — same springs, faster reaction = tension."""
    mult = BOSS_MOOD_SPRING_MULT.get(mood, 1.0)
    if self.tail_spring:
        self.tail_spring.stiffness = TAIL_SPRING_STIFFNESS * mult
    if self.head_dir_spring:
        self.head_dir_spring.stiffness = HEAD_SPRING_STIFFNESS * mult
```

### Named Boss Personalities

```python
def king_personality():
    """Orgulhoso: prefere charge quando encurralado, fica mais raivoso."""
    return BossPersonality(pattern_weights={
        'charge': {'cornered': 2.2, 'enraged': 1.6},
        'shockwave': {'agitated': 1.5},
        'spiral': {'enraged': 1.6},
    })

def centipede_personality():
    """Furtivo: prefere deathroll quando encurralado."""
    return BossPersonality(pattern_weights={
        'deathroll': {'cornered': 2.5, 'enraged': 1.8},
    })

def kraken_personality():
    """Paciente: grapple mais pesado no estado calm."""
    return BossPersonality(pattern_weights={
        'grapple': {'calm': 1.8, 'agitated': 1.0},
        'arms_rain': {'enraged': 2.0},
        'spiral': {'frustrated': 2.2},
    })

def primordial_personality():
    """Caótico: quase neutro, mas fica imprevisível quando enraged."""
    return BossPersonality(pattern_weights={
        'deathroll': {'enraged': 1.5},
        'sky_slam': {'enraged': 1.8, 'frustrated': 2.0},
    })
```

### Game Examples

- **Binding of Isaac**: mood is communicated through attack pattern selection (enraged = more projectiles, tighter patterns) and visual changes (red tint, faster movement).
- **Enter the Gungeon**: bosses have distinct personality weights. Cannon flails when enraged; Ammoconda splits more aggressively.
- **Rain World**: personality emerges from AI + physics. A lizard that can't reach you gets visibly frustrated, pacing and snapping.

---

## Technique 11: Procedural Posing

### The Problem

All creatures stand the same way — neutral spine, identical tail position. Real animals change posture based on context: hunting, fleeing, attacking, injured.

### Pose Library

```python
POSES = {
    'neutral':    {'arch': 0.0,  'tail': 0.0,  'head_tilt': 0.0,  'leg_spread': 1.0},
    'alert':      {'arch': 0.3,  'tail': 0.5,  'head_tilt': 0.1,  'leg_spread': 1.1},
    'hunting':    {'arch': 0.1,  'tail': 0.7,  'head_tilt': -0.2, 'leg_spread': 0.9},
    'fleeing':    {'arch': -0.2, 'tail': -0.3, 'head_tilt': 0.0,  'leg_spread': 1.3},
    'attacking':  {'arch': 0.5,  'tail': 0.8,  'head_tilt': 0.3,  'leg_spread': 0.8},
    'injured':    {'arch': -0.3, 'tail': -0.5, 'head_tilt': 0.2,  'leg_spread': 0.7},
}
```

### Pose Blending

```python
class ProceduralPose:
    def __init__(self):
        self.current = 'neutral'
        self.blend = 1.0       # 1 = fully in current pose

    def transition_to(self, pose_name, speed=3.0):
        self.target_pose = pose_name
        self.blend = 0.0

    def update(self, dt):
        self.blend = min(1.0, self.blend + dt * 3.0)

    def apply_to(self, spine, legs):
        pose = POSES[self.current]
        # Arch mid-body
        mid = len(spine.joints) // 2
        spine.joints[mid].y += pose['arch'] * 10
        # Raise/lower tail
        for i in range(mid, len(spine.joints)):
            frac = (i - mid) / (len(spine.joints) - mid)
            spine.joints[i].y -= pose['tail'] * frac * 15
        # Leg spread
        for leg in legs:
            leg.side_off *= pose['leg_spread']
```

### Game Examples

- **Rain World**: every lizard dynamically poses based on AI state. Hunting pose (low, tail still) is unmistakable. Alert pose (head up, tail raised) signals the creature has seen you.
- **Hollow Knight**: boss poses communicate health thresholds and attack readiness. Broken Vessel's limp tells you it's almost dead.

---

## Technique 12: Pipeline Architecture

### The Complete Pipeline

```
1. AI / Steering
   └── target velocity + direction

2. Physics Simulation (deterministic)
   ├── Position integration
   ├── Spine follow-the-leader resolve
   ├── Leg IK + foot planting (+ ground adaptation)
   ├── Tentacle/arm resolve
   └── Squash & stretch (speed-based)

3. Secondary Motion (cosmetic)
   ├── Spring-damper update (tail, head_dir, future parts)
   ├── Phase oscillator update (fins, spikes, wings)
   └── Anticipation timers

4. Procedural Posing (context-driven)
   ├── Mood → pose
   ├── AI state → pose
   └── Event-driven squash (landing, hit, wind-up)

5. Cosmetic Layer (draw-only)
   ├── Catmull-Rom spline samples
   ├── Cosmetic joint override
   └── Part attachment with spring offsets

6. Render
   ├── Body fill (quad strip to avoid self-crossing)
   ├── Body outline stroke
   ├── Parts (with spring/oscillator offsets)
   ├── Eyes + head details
   ├── Juice (glow, particles, shake)
   └── Health bar, telegraphs
```

### Code Organization

```
anim.py          — Reusable primitives (no game knowledge)
   SpringDamper, Vector2Spring, PhaseOscillator, Anticipation

spine.py         — Follow-the-leader chain + Catmull-Rom rendering
   Spine.resolve(), Spine.body_render_smooth()

leg.py           — 2-bone IK + foot planting
   Leg.update(), Leg.solve()

lizard.py        — Wires everything together
   Lizard.integrate()        — phases 1-3
   Lizard.update_secondary_springs()  — phase 3 choke point
   Lizard._cosmetic_joints() — phase 5
   Lizard.draw()             — phase 6
   AILizard.update()         — phase 0 + all phases

boss.py          — FSM + personality + telegraphs
   BossAI.tick()             — phase 0 (pattern selection)
   BossAI.draw()             — phase 6 (telegraph overlay)
```

### Critical Rule

One choke point per phase. `update_secondary_springs()` exists because adding a new spring meant touching 4 call sites. Any new cosmetic spring only goes in that one method.

---

## Technique 13: Boss FSM Design (for Procedural Bosses)

### The FSM

```
[intro] → [approach] → [windup] → [attack] → [recover] → (repeat)
                ↑                                        |
                └────────────────────────────────────────┘
                
                ↓ (HP threshold)
           [transition] → next phase → ...
```

### States

| State | Duration | Invuln | Movement | Body Pose |
|-------|----------|--------|----------|-----------|
| `intro` | 1-2s | Yes | None | Rising, glowing |
| `approach` | Variable (cooldown) | No | Toward player | Forward lean |
| `windup` | 0.3-1.0s | No | None | Coiled, tense, telegraph |
| `attack` | Instant or timed | No | Depends | Full extension |
| `recover` | 0.3-0.6s | No | None | Slumped, open |
| `charging` | 0.3-0.6s | No | Toward player | Head low, line |
| `transition` | 0.8-1.2s | Yes | Drift back | Flash, rising |

### Phase Design Constraints (from Gungeon analysis)

1. **Phase 1**: teach the core pattern (1-2 patterns max).
2. **Phase 2**: add exactly ONE new thing (new pattern or mechanic).
3. **Phase 3**: swap a pattern AND reduce cooldown. Never more than 2 changes per threshold.

### Pattern Catalog

| Pattern | Telegraph | Counterplay |
|---------|-----------|-------------|
| `radial_burst` | Expanding circle | Create distance |
| `fan_shot` | Two edge lines | Move between lines |
| `aimed_barrage` | Line to target | Strafe perpendicular |
| `summon_adds` | Glowing ring | Clear adds first |
| `shockwave` | Expanding ring | Jump over / get behind |
| `spiral_pattern` | Spinning spokes | Stand at spoke midpoint |
| `charge_attack` | Line showing charge path | Step aside |
| `deathroll` | Circle under boss | Move to edge of arena |
| `sky_slam` | Shadow on ground | Move out of shadow |
| `arms_rain` | Circular targeting zone | Keep moving |

---

## References

### Academic Papers

- **FABRIK**: Aristidou, A., Lasenby, J. (2011). "FABRIK: A fast, iterative solver for the Inverse Kinematics problem." *Graphical Models*, 73(5), 243-260. http://andreasaristidou.com/FABRIK.html
- **Constrained FABRIK**: Aristidou, A., Chrysanthou, Y., Lasenby, J. (2016). "Extending FABRIK with model constraints." *Computer Animation & Virtual Worlds*, 27(1), 35-57.
- **Inverse Kinematics Survey**: Aristidou, A., Lasenby, J. (2018). "Inverse Kinematics Techniques in Computer Graphics: A Survey." *Computer Graphics Forum*, 37(6).

### GDC Talks

- **Rain World GDC 2016**: Jakobsson, J., Therrien, J. "Animation Bootcamp: Rainworld Animation Process." https://www.youtube.com/watch?v=sVntwsrjNe4
- **Transcript**: https://youtubetotranscript.com/transcript?v=sVntwsrjNe4

### Tutorials & Articles

- **Alan Zucconi — Procedural Animation Series**: https://www.alanzucconi.com/2017/04/17/procedural-animations/
- **Merxon22 — Recreating Rain World**: https://medium.com/@merxon22/recreating-rainworlds-2d-procedural-animation-part-1-4d882f947e9f
- **Game Juice — Springs, IK, Living Characters**: https://www.gamejuice.co.uk/articles/procedural-animation-springs-ik
- **The Orange Duck — Spring Roll Call**: https://theorangeduck.com/page/spring-roll-call
- **WeaverDev — Procedural Animation Tutorial**: https://weaverdev.io/projects/proc-anim-tutorial
- **Little Polygon — 2-Bone IK**: https://blog.littlepolygon.com/posts/twobone
- **Abratabia — Procedural Animation in Games**: https://www.abratabia.com/game-animation/procedural-animation.php

### Videos

- **A simple procedural animation technique** (argonaut): https://www.youtube.com/watch?v=qlfh_rv6khY
- **Physics-Based Procedural Animation** (Lincoln Margison): https://www.youtube.com/watch?v=Y44pKSXsCeM
- **Learn Inverse Kinematics**: https://youtu.be/wgpgNLEEpeY
- **Procedural Animation in 5 Minutes**: https://www.youtube.com/watch?v=PcpkBzcRdSU

### Code Repositories

- **Btzel/ProceduralAnimation**: Unity procedural animation playground. https://github.com/Btzel/ProceduralAnimation
- **cristhiandrm/2D-Procedural-Hyper-Motion-Controller**: Unity 2D procedural character with Verlet cloth. https://github.com/cristhiandrm/2D-Procedural-Hyper-Motion-Controller
- **mradovic38/ik-proc-anim-2d**: Unity 2D IK procedural animation. https://github.com/mradovic38/ik-proc-anim-2d
- **CALIKO**: Open source FABRIK library in Java. https://github.com/FedUni/caliko
- **FULLIK**: 3D FABRIK demo. https://github.com/lo-th/fullik
