# Enemy Behaviors

Phase-2 enemies exist to attack a specific player **habit**. New enemy =
new decision, not more HP.

## Roster

| Species | `behavior` | Attacks the habit of |
|---|---|---|
| **VESPA** | `fly` | hiding behind the horde — `collision._samples` skips flyers, so they neither push nor are pushed, and come straight in |
| **ESTOURADOR** | `bomber` | standing still — `BOMBER_FUSE` fuse; once lit, it slows down |
| **METRALHADOR** | `gunner` | open field — burst of `GUNNER_BURST`, low per-shot damage |
| **ENVENENADOR** | `venom` | camping — spits where you _are_ and leaves a puddle |

## Telegraph rule: draw the footprint

Telegraph is **time AND visibility**. The first bomber fuse was 0.85 s
(>27 frames) and had **nothing to see** but sparks — useless. Today
`_draw_fuse` draws the **blast footprint on the ground**, which answers
the only question that matters: _am I inside?_

Rule: when you add an area attack, draw the radius, not just an icon.
This is the same rule as boss [Telegraph](../../CONTEXT.md).

## Hostile puddle: `dmg` changes meaning

`weapons.Puddle(hostile=True)`:

- `hostile=False` → damage per **second** (multiplied by `dt`, feeds the
  `AILizard.damage` accumulator).
- `hostile=True` → damage per **tick** with its own cadence
  (`VENOM_PUDDLE_TICK`).

Player i-frames do **not** rate-limit — they reopen every ~0.17 s and
measured **42 dmg/s**. And `VENOM_PUDDLE_LIFE` must be **less than**
`VENOM_CD`, otherwise puddles overlap and stack: the same bug as
`Acido`, again.

_Third time this project trips on "effect lasts longer than the interval
that reapplies it" — Ácido, venom puddle, sting slow._

## Related

- [Champion](./champion.md) — variants stack on any of these species.
- [Weapon](./weapon.md) — the puddle system these hostile puddles share.
- [Body plan](./body-plan.md) — centipede/octopus follow the same
  "attack a habit" rule.
