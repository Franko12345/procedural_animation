# Quantise radius + colour before caching glow surfaces

**Context.** `palette.glow` returns a pre-rendered additive `Surface` for
`(radius, colour)`. The three natural inputs are all continuous in
practice: radius shrinks with particle life, brightness is a sine, and
every creature spawns with a random colour that its bursts inherit.

**Decision.** Quantise before the cache: radius in 2/4/8-pixel bins by size,
colour in 4 bits/channel (`& 0xF0`) applied _after_ doubling for intensity.
Cap the cache at `_GLOW_MAX = 900` entries with `clear()` on overflow.

**Why.** Without quantising, the cache measured 459 → 1843 entries and
24.6 → 115.7 MB of surfaces in ~7 minutes of play; RSS climbed from 364 →
470 MB. Long sessions ground to a halt. Continuous inputs against an
unbounded cache is the same failure mode Sqlite pages hit in hot
transactions.

**Consequences.**

- **The cache key must remain quantised.** Any glow call site that reaches
  in with a continuous radius or float colour will reopen the leak. The
  regression signature is `perf.py` reporting rising cache MB + rising
  misses/s. See [`perf.py` metrics](../../CLAUDE.md).
- Additive gradients hide the banding introduced by 4-bit colour. Non-
  additive draws that go through `glow` will look posterised.
- `clear()` on overflow is more predictable than LRU under bursty spawn.
  With LRU, worst-case eviction happens exactly when the spawn wave
  requests the most new entries.
- Stability measurement: 35–47 MB, flat over 9000 frames. This is the
  budget. If a session doubles it, the quantiser was bypassed somewhere.
