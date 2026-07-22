# Isaac-style boss pools per tier, not one boss per wave

**Context.** The original `rounds.NAMED_BOSSES` was `tier → 1 boss` — every
run at wave 5 fought the exact same boss. Fine for four bosses, boring by
the fifth run.

**Decision.** Replace with `BOSS_POOL` (id → data, wave-agnostic) plus
`BOSS_TIER_POOLS` (list of `(tier-range, [eligible ids])`). `_spawn_boss`
now does `random.choice(pool_ids)` instead of a tier index.

**Why.** Isaac's identity — "which floor 1 boss did I get this run?" — is
what turns a boss into a memory. A fixed schedule turns it into a
checkpoint. Same wave, three possible fights, none easier or harder than
the others.

**Consequences.**

- **PRIMORDIAL stays fixed** (`BOSS_FINAL = 'primordial'`). The final wave is
  the climax; randomising it drops the arc.
- Tiers without a pool fall back to the generic themed boss — this is not a
  regression, just "no authored content yet at this tier".
- New authored [`boss`](../concepts/boss.md) entries only need to land in the
  pool for the right tier band. No index-shifting, no per-wave switch.
- Distribution is uniform inside a pool. If you want weighted (e.g. rarer
  finals), that's a change to `_spawn_boss`, not a data shape change.

See also: [`Tier`](../../CONTEXT.md) definition.
