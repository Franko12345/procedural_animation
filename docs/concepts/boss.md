# Boss

A large enemy with an FSM, phase transitions, and a personality. Bosses
gate rounds — the round only `cleared`s when the boss dies. Not to be
confused with a [Champion](./champion.md), which lives inside a round.

Defined in `lagarto/boss.py`. Selection rules in
[ADR-0004](../adr/0004-boss-pool-per-tier.md).

## FSM

```
intro
  ├─ (invulnerable) ──► approach ──► windup ──► attack ──► recover
  │                        ▲                                 │
  │                        └─────────────────────────────────┘
  └─ (phase transition) ── invulnerable ── next phase
```

Bosses use a **catalogue of patterns** — each is a data-driven
`(boss, game, target) -> None`. There is no "attack class" hierarchy.

## Patterns

`radial`, `fan`, `barrage`, `shockwave`, `spiral`, `charge`, `pincha`,
`swipe`, `arms_rain`, `sky_slam`, `deathroll`, `summon`, `web_trap`,
`massive_fan`. Each has a telegraph rule
([Telegraph](../../CONTEXT.md)): draw the footprint, not just a
warning icon.

Two patterns need state beyond a windup timer:

- **`charge`** — introduced the `'charging'` FSM state. Windup → dash
  along `_charge_dir` → N seconds of real motion with contact damage.
- **`arms_rain`** — introduced the `select` hook on the FSM (called
  when the pattern is chosen, not at end of windup) because the ground
  markers must exist for the whole telegraph, not just the impact frame.

## Phases

`on_phase` fires at HP thresholds (defaults 66%, 33%). The **rule of two**:
each transition changes at most _two_ things — one pattern in/out plus one
numeric dial. More than that and the player has to relearn the fight
instead of adapting.

## Personality

`BossPersonality` (`mood_speed`, per-mood pattern weights, glow-per-mood,
telegraph length multiplier). `_update_mood` derives current mood from
distance / HP / frustration; `_choose_pattern` weights by
personality × mood, not `random.choice`. Mood also scales
`tail_spring.stiffness` — calm bosses look loose, cornered bosses look
tense. Zero draw code new.

## Two things you must set for a boss

- **`gen.knockback = 0`** — projectiles used to punt bosses out of their
  own approach, effectively interrupting the fight for free.
- Body scale of ~2.3× (2.3 × 1.35 for the final tier). "4×" mentioned in
  design docs is flavour text — the numbers on the wire.

## Boss vs generic

Named bosses live in `BOSS_POOL` with overrides (patterns per phase,
`on_phase`, `emblem`, `boss_attrs`). Tiers without an authored entry fall
back to the generic "themed species scaled up" boss. This is not a
regression — it's "no authored content yet at this tier".

## Related

- [ADR-0004](../adr/0004-boss-pool-per-tier.md) — how a tier picks a boss.
- [Tier](../../CONTEXT.md) — the slot bosses fill.
- [Round](./round.md) — the wave a boss gates.
- [Species](./species.md) — the body a boss is scaled up from.
- [Champion](./champion.md) — sibling big-enemy concept.
