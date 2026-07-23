# Body Plan

`Genome.plan` forks `rebuild_body` / `draw` / telegraph. Three values:

- **`'normal'`** — [Spine](./spine.md) + [Legs](./leg.md). Every classic
  creature.
- **`'segmented'`** — CENTOPEIA. Chain of ringed circles + metacronal legs.
- **`'tentacle'`** — POLVO/KRAKEN. Mantle + arm sub-chains.

`plan` is a slot on `Genome.__slots__` — the trap of always. Missing it
means silent fallback to `'normal'`.

Both new plans follow the [Enemy behaviors](./enemy-behaviors.md) rule:
each attacks one player habit.

## CENTOPEIA (`plan='segmented'`, `behavior='burrow'`)

Body = chain of ringed circles (the ink ring on each segment _is_ the
segmentation) + tiny legs in **metacronal wave** (partner = pair 2
segments back, so it ripples instead of marching). Mechanic: **burrower**
(Para-Bite / Moles of Isaac): `surface → digging → under → erupt`.

### Diving cannot mean "vanishes"

`digging` is a rooted phase (`CENT_DIG_TIME`) that opens a growing hole
and throws dirt — telegraphs that it is about to submerge. Then
`burrowed=True`.

### Intangible while under — in one place

`hit_test` returns `None` and `collision._samples` skips creatures with
`burrowed` (same pattern as flyer). All damage flows through `hit_test`,
so this covers dash + projectile + aura in one spot. During `digging` it
is still vulnerable — that is the counter-attack window.

### Fair telegraph (`_draw_burrow`)

An **eruption ring** at `dive_to` (locked in on dive) fills as it
surfaces + the mound travels with a dirt trail. Same rule: draw the
radius, not just a warning.

## POLVO / KRAKEN (`plan='tentacle'`, `behavior='grapple'`)

Pulsing mantle + arms as sub-chains (`self.arms`, resolved in
`integrate`), with a travelling wave + swirl to undulate like a
tentacle, and trailing to whip when moving. Drawing is **continuous**
(same left/right-rim outline + spine cap — the user asked for smooth
flesh, not beads).

### Grapple mechanic

Gungeon Gripmaster: closes in slowly, roots, and **stretches all arms
toward you** (`arm_target` makes `_resolve_arms` converge/stretch —
that convergence _is_ the telegraph, `OCTO_WINDUP` > 27f). On the snap,
**pulls** you (`OCTO_PULL_DIST`) and **slows** you (`apply_slow`).
Escaping before the snap negates.

Arms are cosmetic: the hitbox is the mantle (`hit_test` samples the
short spine); the danger is the grapple, not the touch.

### Slow bruisers must ignore knockback

`take_hit` / `damage` assign / add velocity for knockback, so every spit
zeroed the approach and the octopus never arrived. `genome.knockback`
(multiplier <1, a new dial on `__slots__`) fixes it in one place —
octopus 0.28, everyone else 1.0. And it **commits to the approach**
(does not retreat "to keep distance"), because the only defence is you
**run** (top speed < player walk). Measured: closes from 430 px to
~16 px under fire, then grapples.

## Boss-ready

The KRAKEN scaled ~2.2× already renders — a boss without a new body.

## Related

- [Genome](./genome.md) — where `plan` and `knockback` live.
- [Enemy behaviors](./enemy-behaviors.md) — the "attack a habit" rule
  these follow.
- [Boss](./boss.md) — future scaled-up KRAKEN.
