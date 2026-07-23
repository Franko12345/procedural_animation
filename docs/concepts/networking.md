# Networking

Not implemented yet. But the seams are set up for it.

## The plan

Every input crosses `Controller`. A future `NetworkController` (inputs
coming from the wire) would plug in without touching the simulation.
The fixed / deterministic timestep already favours this — see
[Performance](./performance.md) and
[ADR-0002](../adr/0002-fixed-timestep-decoupled-render.md).

## Today

Coop is **local** only. Two controllers, one machine, one screen.

## Related

- [Controls](./controls.md) — the `Controller` abstraction.
- [ADR-0002](../adr/0002-fixed-timestep-decoupled-render.md) — the
  determinism story.
