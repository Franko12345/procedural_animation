# Every creature is a Genome

**Context.** The game's original prototype was a snake — one hard-coded class
that drew a specific silhouette. New creature types would each demand a new
class with duplicated spine / leg / draw code.

**Decision.** Every creature (prey, enemy, champion, boss, and the four
playable characters) is a `Lizard` built from a [`Genome`](../concepts/genome.md)
— a bag of numbers: size, leg count, colour, hp, body plan, behaviour, diet.
No class hierarchy per species; only `Lizard` / `Player` / `AILizard`.

**Why.** The whole "no sprites, no keyframes" pitch depends on this. Adding a
scorpion means one entry in [`species.py`](../concepts/species.md) — not a
new draw path. Player evolution is genome mutation, which is why picking a
"spider" card literally re-runs `rebuild_body`. If different creatures were
different classes, every part-drawing routine in [`parts.py`](../concepts/parts.md)
would need per-class branches and evolution would be impossible.

**Consequences.**

- Two forks live inside the same code path: `Genome.plan` selects `normal` /
  `segmented` / `tentacle`; `Genome.radial` picks the leg layout. Any new
  body shape adds a branch, not a class.
- `Lizard.rebuild_body(keep_pose=True)` must recompute only genome-derived
  fields, never re-`__init__` — that would erase hp, weapons, level. See
  [ADR-0007](./0007-cosmetic-skeleton-for-tail.md) for the related sim-vs-cosmetic split.
- Champions and modifiers (BLINDADO, DIVISOR) stack via `apply()` calls on
  top of a species genome — see [`champion`](../concepts/champion.md).
