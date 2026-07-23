# Juice / Feel

Whole-screen feedback layers that make hits feel like hits.

## Hit-stop

`game.punch(freeze, shake, flash)`. The `app.py` loop **skips
simulation steps** while `game.hitstop > 0` (still draws). Uses:

- dash-kill (0.07 s)
- damage to player (0.05 s)
- boss death (0.22 s + white flash)

## Transitions

`ui.Fade` (short fade) on entering a run and on every state change
(play ↔ camp ↔ levelup ↔ victory / over), and between menu screens.

## Menu animation (Vampire Survivors-style)

`menu._menu_list` takes an `anim` dict (`{'t', 'sel_f'}`) and does:

- **Staggered drop-in** of items (slide + fade, ~45 ms apart)
- **Sliding highlight** between options (`sel_f` chases `sel`)
- Selected item pulses softly

## `ui.fit`

`ui.fit(font, text, width)` truncates text with `"..."` so nothing
overflows a box.

## Related

- [UI screens](./ui-screens.md) — where drop-in + absorption compose.
- [Combat](./combat.md) — where hit-stop is called.
- [Boss](./boss.md) — the 0.22 s freeze on boss death.
