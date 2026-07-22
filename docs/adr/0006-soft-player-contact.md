# Player↔enemy contact is soft (drag, not push)

**Context.** Enemy↔enemy uses hard separation — bodies do not overlap. When
that rule was applied to the player, being touched by anything punted the
player around; playtest described it as "pinball".

**Decision.** The player is **never displaced**. Contact accumulates
`creature.clog` (soft drag) via `collision.separate`; the enemy gets the
full push. The player pays in velocity, smoothed by `clog_f` at approach 9/s
with `C.CONTACT_DRAG`. Dash ignores the whole system — passing through is
the point.

**Why.** The player already has i-frames (`hit_flash > 0.45`) for damage. A
second bounce-off layer stacked on top made the input feel taken away. Soft
contact still communicates "you're touching an enemy" — just as speed loss
that scales with how buried you are — without stealing agency.

**Consequences.**

- `collision.FRIENDLY` set: aliases + player + player don't push each other.
  Only enemies drag the player.
- **Prey are exempt** (`collision.DRAGS_PLAYER` = enemies only). A harmless
  grazer standing next to the player used to knock them to 49% speed with
  no visual cue why.
- **`C.CONTACT_FULL` (3.0) shapes the curve.** Sampling 5×5 pairs saturated
  at one enemy; the divisor turns "buried in ~3 bodies" into full brake, so
  1 enemy ≈ 90%, 4 ≈ 68%, 6 ≈ 65%.
- Slow effects (venom, web) multiply _on top_ of clog — see the "two brakes"
  playtest note in [CLAUDE.md](../../CLAUDE.md). Both need to be visible;
  `Player._draw_slow_mark` draws cool rings for the slow half.
- Enemy↔enemy stays hard. Softening that would let enemies pile on the same
  tile — the original bug this system was written for.

See also: [ADR-0002](./0002-fixed-timestep-decoupled-render.md) — the fixed
timestep is what makes `approach 9/s` deterministic frame-to-frame.
