# Balance

Two passes of balancing recorded here. The design rules are more
important than the specific numbers.

## 2nd pass rule: raise DAMAGE, not HP

Coming out of Isaac / Gungeon / VS research: in an auto-attack game the
only player agency is **positioning**, so difficulty must be a
**consequence of position error**. More HP turns enemies into sponges
and makes the build feel weaker than it is.

- **Contact damage** comes from `lizard.contact_damage(max_r, wave)`, with
  the dials `ENEMY_DMG_BASE` (11), `ENEMY_DMG_SIZE` (0.5) and a
  **step-wise wave ladder** (`ENEMY_DMG_STEP` / `ENEMY_DMG_PER_STEP`).
  A continuous ramp is invisible; a step is felt. Runner 16 → 26 over
  waves 1 to 20; tank 26 → 36. Projectile: `ENEMY_PROJ_DMG` (10).
- **`ENEMY_HP_MULT`: 3.0 → 2.2 (measurement) → 3.5 (playtest).** The
  headless bot measured **weapon** TTK and said 2.2; the user plays with
  **dash + whip**, which are much faster, and enemies felt like paper.
  **Lesson: the bot measures friction, not difficulty** — use it to
  compare before/after, never to pick the final number.
- **Do not touch i-frames** (`hit_flash > 0.45`) — they are what keeps the
  game fair. See [Damage](./damage.md).

### Measurement (driven headless bot, `--smoke` is not this)

Two styles: `kite` (moves only, lets weapons work) and `aggro` (dash
hunter, how the user plays). After the rebalance: aggro went from median
wave 2.5 / 5.5 kills to **3.0 / 8 kills** in the same time-to-death —
kills faster, dies the same.

_A bot that only moves measures a game nobody plays_: at level 1 `cuspe`
does **1 damage every 1.05 s**, so almost all early damage comes from
the **dash**.

### Open, and it is a design decision, not a bug

Playing 100% passively **does not clear wave 1 in 6 minutes**. The
premise "attack is automatic, you only position" does not hold at the
start of the run. Raising base weapon damage would fix it — and make
the game easier, the opposite of what was asked. Needs a user call
before touching it.

## 1st pass — from user playtest

Feedback: _enemies died too easily, friends were disproportionate, too
much healing on the ground_. Numbers touched — **this is the place to
change them**:

- **Enemies ~2× tougher**: genome hp in `species.py` (runner 2 → 4, tank
  6 → 14, snake / spider / spitter 3 → 6, horned / spiky / scorpion
  4 → 8), and per-wave scale faster (`rounds`: `wave//3` →
  `int(wave*0.7)`).
- **Fewer enemies at once**: `THEMES[...]['cap']` down (11 → 7, 7 → 5,
  5 → 4, 8 → 6) and budget smaller (`(4 + wave*1.6)` → `(3 + wave*1.1)`).
- **Less healing**: fruit heals 25 → 12; starting fruits 12 → 5; enemy
  drop 40% → 15%; nest fruit drop 100% → 50%.
- **Friends temporary and weaker**: `config.FRIEND_LIFE` (45 s, blink
  the last 5 s and vanish), hp 3 → 2, attack every 0.6 s → 1.1 s; world
  eggs 6 → 3; shop egg 24 → 40 pollen.

## Related

- [Damage](./damage.md) — player-side HP flow.
- [Combat](./combat.md) — dash / whip damage scaling.
- [Round](./round.md) — theme caps, wave scale.
- [Species](./species.md) — genome HP baselines.
