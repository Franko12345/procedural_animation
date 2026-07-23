# Pause

`game.state == 'pause'`. ESC opens the menu. Before, ESC dropped the
entire run without confirmation.

Pause is just another non-`play` state — `game.step` already freezes
everything for free, and the `Game` is never destroyed.

## Machinery

- `game.toggle_pause()` stores `pause_prev` (so pausing inside
  [Camp](./camp.md) returns to camp).
- `pause_mode` cycles menu / options / controls.
- `pause_back()` climbs one level.

## Reuses the main [menu](../../CONTEXT.md)

`menu._items_for('options', ...)` and `menu._activate(...)` give the
options screen with the same persistence. The controls text moved to
`menu.CONTROLS` / `controls_lines()` — **shared**, otherwise the two
screens drift.

## Four traps already fixed — do not reintroduce

- Music branches on `game.state` every frame → use `pause_prev`,
  otherwise pausing in camp flips `calm` → `combat`.
- `'pause'` must be in the `soft` tuple of the fade, otherwise there is
  a 0.22 s blackout.
- `meter.level` and `app.py`'s `cfg` must be **re-read** after options
  (`app._pause_pick`), otherwise the FPS meter looks dead and the next
  F3 reverts adjustments.

## Related

- [Camp](./camp.md) — pausing inside camp returns to camp.
- [Controls](./controls.md) — the controls text shared with the main menu.
- [Game modes](./game-modes.md) — pause is one of the non-`play` states.
