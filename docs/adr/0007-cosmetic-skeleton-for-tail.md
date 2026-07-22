# Cosmetic joints for tail spring & wave, physical spine unchanged

**Context.** Tail overshoot and travelling waves are secondary motion — they
look great, but only if the tail can lag behind or ripple sideways of where
it physically is. The naive fix is to write to `spine.joints` after the
physics step.

**Decision.** Introduce a **cosmetic skeleton**: `_cosmetic_joints()` returns
a modified copy used only for drawing. Hit-tests, legs, eyes read
`spine.joints` untouched. Parts drawn on the cosmetic joints
(`draw_tail`, `draw_spikes`, `draw_plates`, `draw_fins`, and the body's
texture points) migrate with the tail; hit-test does not.

**Why.** Sim and draw asking the same joint two different questions is a
recipe for the hitbox drifting off the silhouette. Rain World's "two
skeletons" pitch (GDC 2016) is exactly this: physics and cosmetic
separated at the joint level, not the class level.

**Consequences.**

- Only the last `TAIL_SPRING_JOINTS` joints are cosmetic. The rest stay
  identical to `spine.joints` — cheap read-through.
- **`_cosmetic_joints()` is off during whip.** The whip authors its own
  joint override; a spring chasing pre-whip positions would blunt the
  swing. See the whip note in [CLAUDE.md](../../CLAUDE.md).
- Every part reader that used `spine.joints` for a joint the tail owns had
  to switch to cosmetic — this got missed once (plates, fins, spikes),
  producing a visual disconnect that was a real bug.
- Menus previously reimplemented `Lizard.integrate()` in three places and
  none updated the spring — the mole always chased a construction-time
  target while the body wandered the screen, producing screen-length
  streaks. All three now go through the same central update. Same lesson
  as [ADR-0008](./0008-might-scales-all-damage.md): one hook, one place.

See also: [Cosmetic Skeleton](../../CONTEXT.md), [Spine](../concepts/spine.md).
