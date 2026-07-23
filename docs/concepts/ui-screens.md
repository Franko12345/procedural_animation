# UI Screens

Level-up and [Camp](./camp.md) do not appear all at once. Two-phase
entry, then a **pick absorption** on choice.

Clock: `self.ui_t`, zeroed in `_enter_levelup` / `_enter_camp` and
advanced in `game.step`'s `state != 'play'` branch (fixed step, so it is
FPS-independent). Dials in `core/config.py` (`UI_VEIL` / `UI_STAGGER` /
`UI_DROP` / `PICK_*`).

## Phase 1 — veil (0-0.20 s)

`_veil` darkens the background.

## Phase 2 — staggered drop-in

`ui.drop_in(t, i, ...) -> (offset_y, alpha)`. Each panel drops in with
fade. `menu._menu_list` uses the same helper — one shared "feel".

## Absorption on pick (`self.pick`)

Choosing **does not apply anything yet**. The other options fade and
shrink; the chosen one moves to centre (above the lizard — the camera
centres the player, so centering the card leaves no travel distance
either), holds for reading, and **flies into the player** with a trail.
On impact: `punch()` (screen-shake + hit-stop + flash) + burst / rings +
sound — **only then** `_apply_card` / `_apply_buy` / `_apply_route`.

Input blocked via `game.ui_busy()` + guards on `game.pick` in `app.py`.

Transitions `play↔levelup↔camp` **do not use `ui.Fade`** — the blackout
was hiding the impact.

## Particles on these screens

`fx` is drawn with the world, so under the veil (which cuts ~80% of the
glow). `game._ui_fx(layer)` redraws the particles **on top of the
panels** while there is a `pick` or `ui_fx > 0` (afterglow 1.1 s, because
the impact burst is born on the frame `pick` just went `None`).

Purchases use `C.COL_POLLEN` — the spent pollen bursts out of the tent,
becomes a golden comet, and pops on the lizard with the `buy` sound (the
chime moved from click to impact).

## Perf on these screens

- Panels are cached (`game._panel`, key = panel state).
- The veil uses an opaque surface + `set_alpha` (per-pixel SRCALPHA cost
  ~6 ms/frame — see [Performance](./performance.md)).
- The shake layer only composes when there **is** shake (`_ui_dest`);
  otherwise draws directly to the screen.

## Related

- [Camp](./camp.md) — the same entry / absorption model.
- [Evolution](./evolution.md) — the level-up card flow this hosts.
- [UI legibility](./ui-legibility.md) — text rendering rules for these
  panels.
- [Performance](./performance.md) — the surface-caching rule.
