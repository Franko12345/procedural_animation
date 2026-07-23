# Input Buffer

Don't go back to a one-frame edge. `Controller` keeps a **timer per
action** (`C.INPUT_BUFFER`, 0.15 s) instead of a one-frame flag.
`dash_edge` / `tongue_edge` / `whip_edge` are properties (`buffer > 0`);
whatever fires calls `ctrl.consume(...)`.

## Why

`poll()` runs once per **rendered** frame, but the simulation is a
fixed-step accumulator — one frame can run **zero steps** (jitter, and
every hit-stop). An edge detected on such a frame was never consumed,
and the next `poll()` saw the button as "still pressed" → **press
swallowed forever**. With the old `RENDER_FPS = 120` vs `SIM_HZ = 60`
this was ~half of frames — the same root as the perf problem.

The buffer also lets a press just **before** cooldown ends still count.

## Firing is still by edge

Holding the button does not repeat (tested). The buffer is a grace
window, not autofire.

## Related

- [Controls](./controls.md) — how P1 / P2 / gamepad map to actions.
- [Performance](./performance.md) — `RENDER_FPS = SIM_HZ` context.
