# Architecture

The `lagarto/` package is one module per responsibility. Do not collapse
back to a single file — see
[ADR-0010](../adr/0010-single-file-per-module.md).

`lizard_game.py` is a launcher: `from lagarto.app import main`.

## `lagarto/core/` — leaves of the import graph

Utilities with no game-side dependencies. Everything imports from here:
`from .core import config as C`, `from .core.mathutil import ...`.
`lagarto/core/__init__.py` is intentionally empty — explicit imports
grep better than re-exports.

| Module | Responsibility |
|---|---|
| `core/config.py` | Constants (window/world, timing, vivid palette, energy costs). Colour/balance dials start here. |
| `core/palette.py` | HSV colour (`vibrant`, `random_in_family`), lighten/darken/mix, and cached additive `glow` (`BLEND_RGB_ADD`) for rim/brilho. Cache quantised — see [ADR-0009](../adr/0009-glow-cache-quantized-keys.md). |
| `core/mathutil.py` | Vector/angle helpers (`math` + `Vector2`, **not numpy** in hot loops). |
| `core/fonts.py` | Picks the best installed font (Noto Sans etc.), cached by size. |
| `core/settings.py` | `~/.lagarto/settings.json` (fullscreen/scale/vsync/volumes). Tolerates corrupted file. |
| `core/registry.py` | Lookup/filter/weighted-roll helper shared by charms, characters, items, mutations, synergies. |

## Game modules

| Module | Responsibility |
|---|---|
| `display.py` | Fixed logical surface + 1x/2x/3x + fullscreen letterbox; `present()` smoothscales; `to_logical(pos)` maps mouse (essential for clicks). |
| `ui.py` | Visual kit: `panel`, `chip`, `list_menu`, `tabs`, `paragraph`, `footer`, `fit`, `Fade`, and `drop_in` (staggered entry — use on every new screen). |
| `icons.py` | Procedural icons (weapons/mutations/charms) drawn in code — cards, HUD, shop, charms, compendium. |
| `audio.py` | Synthesised SFX (numpy) + generative music. See [Icons & Audio](./icons-audio.md). |
| `genome.py` | [`Genome`](./genome.md): creature = numbers. |
| `spine.py` | [`Spine`](./spine.md): follow-the-leader chain + `body_polygon`. |
| `leg.py` | [`Leg`](./leg.md): foot-planting + 2-bone IK. |
| `parts.py` | [Parts](./parts.md) drawing pipeline. |
| `lizard.py` | `Lizard` (base built from genome), `Player` (XP/level/energy/dash/tongue), `AILizard` (prey/enemy/friend + behaviors). |
| `species.py` | [Species](./species.md): genome templates + metadata. |
| `characters.py` | [Playable characters](./character.md). |
| `items.py` | [Items](./item.md): actives + mechanic-changing passives. |
| `champions.py` | [Champions](./champion.md): variants + modifiers. |
| `evolution.py` | [Mutation cards + Synergies](./evolution.md). |
| `projectile.py` | `Projectile` (spit, web, boss shots). Helpers `spit`/`web`. |
| `pickups.py` | `Bug`, `Fruit`, `Egg`. |
| `world.py` | `World`: biome tiles, water shimmer, flora, culling. |
| `fx.py` | Particles (pool, cap), sparks, rings, floating text, shadows. |
| `camera.py` | Follow 1 player or frame 2; screen shake; `w2s`/`s2w`. |
| `collision.py` | Body separation via spatial hash. See [Combat](./combat.md). |
| `controllers.py` | Input abstraction: `KeyboardMouseController`, `KeyboardController`, `GamepadController`. |
| `game.py` | `Game`: world, spawns, waves, projectiles, XP/evolution, HUD, game over. |
| `menu.py` | Hub: play (1/2), options, controls, bestiary, compendium. |
| `progression.py` | [Meta-progression](./progression.md): DNA save file. |
| `perf.py` | FPS meter / diagnostics. See [Performance](./performance.md). |
| `app.py` | Window setup + main loop with fixed timestep. |
| `rounds.py` | [Round](./round.md) manager. |
| `weapons.py` | [Weapons](./weapon.md). |
| `charms.py` | [Charms](./charm.md). |
| `boss.py` | [Boss](./boss.md) FSM. |
| `assets.py` | Optional pixel-art PNG loader with procedural fallback. See [ADR-0003](../adr/0003-zero-assets-with-png-fallback.md). |

## Related

- [ADR-0010](../adr/0010-single-file-per-module.md) — why the split.
- [Performance](./performance.md) — the fixed-timestep / render decoupling.
