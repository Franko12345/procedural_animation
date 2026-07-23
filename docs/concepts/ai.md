# AI

`AILizard` dispatches per `genome.behavior`. Each branch is a small
steer/attack loop — no state machine class hierarchy.

## Behavior branches

- **`chase`** — melee, straight approach.
- **`ranged`** — the spitter keeps distance and fires `projectile.spit`.
- **`lunge`** — the spider telegraphs and pounces.
- **`hop`** — frog.
- **`fly`** — [VESPA](./enemy-behaviors.md); skipped by collision samples.
- **`bomber`, `gunner`, `venom`** — phase-2 behaviors. See
  [Enemy behaviors](./enemy-behaviors.md).
- **`burrow`, `grapple`** — body-plan behaviors. See
  [Body plan](./body-plan.md).

## Ecosystem

Predators with `diet=('prey',)` hunt real prey; prey flees the player
**and** predators (`game.nearest_threat`).

## Status effects

- **`apply_slow`** — affects the steer.
- **`apply_poison`** — DoT on creatures.

The player's whip poisons; enemy stings slow. Divergence is on purpose
(see [Parts](./parts.md)).

## Related

- [Species](./species.md) — roster of species per behavior.
- [Enemy behaviors](./enemy-behaviors.md) — phase-2 branches.
- [Body plan](./body-plan.md) — plan-specific behaviors.
- [Combat](./combat.md) — how AI hits and gets hit.
