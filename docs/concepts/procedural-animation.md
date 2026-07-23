# Procedural Animation

The lizard is 4 elements:

- **Intent** — head points at the target.
- **Action** — legs take the step.
- **Reaction** — [Spine](./spine.md) reacts.
- **Follow-through** — tail lags.

No keyframes. Every visible motion is the output of a physical or
kinematic rule.

## Spine

Each joint is pulled to a fixed distance from the previous joint.
Direction is limited by `bend` so the body cannot double back on itself.
See [Spine](./spine.md).

## Legs

The foot stays planted until the body drags its "rest point" past a
threshold. Then it steps in an arc to a target ahead of the body.
**Diagonal gait**: opposite pairs never step together (`Leg.partner`).
Drawn by two-bone IK. See [Leg](./leg.md).

## Squash & stretch

Derived from velocity — the body flexes without any authored animation.

## Related

- [Spine](./spine.md) — the follow-the-leader chain.
- [Leg](./leg.md) — 2-bone IK + foot planting.
- [Parts](./parts.md) — decorations that ride the spine.
- [ADR-0007](../adr/0007-cosmetic-skeleton-for-tail.md) — the sim vs
  draw split for tail.
