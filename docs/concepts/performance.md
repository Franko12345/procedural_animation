# Performance

Python game. These rules earned their spot — do not undo them without
measuring.

## Fixed timestep, decoupled render

`config.DT` = 60 Hz sim; the `app.py` accumulator drives it. Rendering
is separate. Animation stays stable regardless of FPS. A step cap
prevents the spiral of death. See
[ADR-0002](../adr/0002-fixed-timestep-decoupled-render.md).

## `RENDER_FPS = SIM_HZ` — do not raise

Sim is fixed at `SIM_HZ` and **drawing does not interpolate** between
states. Rendering above that only **redraws identical frames**: 120
render vs 60 sim was **2× the cost of `draw` + `smoothscale` + `flip`
for zero visual gain** (GPU pegged at 100% with low usage — many flips,
little work). If you ever want render > sim, **implement interpolation
first**.

## Vectors

`pygame.Vector2` + `math` (scalar numpy is slower per operation).

## Culling

`Camera.visible` culls creatures, flora, and particles.

## Particles

Pooled with a cap (`FX.MAX`). Shadows and tile colours are **cached**.

## Entity budget

Insects / prey repopulate by probability with a limit.

## Measured cost

~0.5 ms step + ~3.3 ms draw per frame on a full round (large headroom).
`display.present()` uses **smoothscale** so vector art stays crisp at
scale. It is CPU: 2.2 ms/frame at 2×, 3.8 ms at 3× — hence the
importance of render rate.

## `palette.glow` — the cache key MUST be coarse

`_GLOW_CACHE` stores one `Surface` per `(radius, colour)`. In practice
all three axes are continuous:

- Radius shrinks with particle lifetime and scales with zoom.
- Intensity is a pulsing sine on ~29 call sites.
- Each creature spawns with a random colour, and `fx` bursts inherit it.

Without quantising, the cache **grew without bound** — measured:
459 → 1843 entries and **24.6 → 115.7 MB** of surfaces over ~7 min of
play (RSS 364 → 470 MB), which stalled long sessions. Today:

- `_quantise_radius` (step 2 / 4 / 8 px by size) + colour in **4
  bits/channel** (`& 0xF0`) applied **after** the intensity multiply.
  Similar pulses / colours collapse to the same sprite; the additive
  gradient hides the banding.
- **Cap `_GLOW_MAX = 900`** with `clear()` on overflow (more predictable
  than LRU).
- Result: RAM flat at ~35-47 MB over 9 000 frames. **When you add a new
  glow, do not reintroduce continuous intensity / radius as a key.**

See [ADR-0009](../adr/0009-glow-cache-quantized-keys.md).

## No full-screen `Surface` per frame

`ui._tint(surf, colour, alpha)` is the only path for darkening /
lightening the full screen: reuses **one cached surface per colour**
with `set_alpha` (blit faster than per-pixel alpha). Used by `ui.Fade`,
`ui.veil`, the game-screen veil (`game._veil`) and the white flash.
Allocating `Surface(SRCALPHA)` every frame cost ~6 ms **and** produced
garbage.

## Text cache

`_TEXT_MAX = 700` with `clear()` on overflow — same pattern. See
[UI legibility](./ui-legibility.md).

## Related

- [ADR-0002](../adr/0002-fixed-timestep-decoupled-render.md) — the loop.
- [ADR-0009](../adr/0009-glow-cache-quantized-keys.md) — the glow key.
- [Input buffer](./input-buffer.md) — the sim/render decoupling implies it.
- [UI legibility](./ui-legibility.md) — text cache follows the same rule.
