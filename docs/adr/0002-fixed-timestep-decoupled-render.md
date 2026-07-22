# Fixed timestep at `SIM_HZ`, render at the same rate

**Context.** `app.py` runs a fixed-timestep accumulator (`config.DT`, 60 Hz).
An earlier version rendered at `RENDER_FPS = 120` on top of `SIM_HZ = 60`.

**Decision.** `RENDER_FPS = SIM_HZ`. Do not increase render rate without also
building state interpolation between simulation steps.

**Why.** Drawing does not interpolate between physics states. Rendering at
2× sim rate just redraws identical frames — measured 2× cost for zero visual
change (users reported "GPU pegged, low power draw" — many flips, little
work). The same asymmetry also broke input: `poll()` runs per rendered
frame, so an edge could be detected in a step-less render frame and the next
poll would see the button still down → the input was consumed forever. See
the input-buffer note in [ADR-0006](./0006-soft-player-contact.md) for the
downstream fix.

**Consequences.**

- Hit-stop works by skipping simulation steps while continuing to render.
  That only functions because the render loop is not tied to fresh sim
  states.
- Any future "render at 144 Hz" plan **must** ship state interpolation
  first. Do not just raise `RENDER_FPS`.
- `--smoke N` counts sim frames, not render frames — same clock.
