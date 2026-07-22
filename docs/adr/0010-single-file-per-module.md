# One responsibility per module in `lagarto/`

**Context.** The prototype was a single `procedural_animation.py`. Growth
pushed it past comprehension. The natural pull is to keep everything in
one file "for now" — the natural cost is that "now" never ends.

**Decision.** The `lagarto/` package has one module per responsibility.
`config`, `display`, `settings`, `fonts`, `ui`, `icons`, `audio`,
`mathutil`, `palette`, `genome`, `spine`, `leg`, `parts`, `lizard`,
`species`, `characters`, `items`, `champions`, `evolution`, `projectile`,
`pickups`, `world`, `fx`, `camera`, `collision`, `controllers`, `game`,
`menu`, `progression`, `perf`, `app`. Don't collapse. Don't grow a
`utils.py`.

**Why.** With one file per responsibility, "where does X live?" has one
answer. `git blame` tells a specific story per topic. Tests can import the
smallest surface. And critically: the "no classes for kinds" rule from
[ADR-0001](./0001-genome-is-the-creature.md) makes the file per topic
because there is no class per creature.

**Consequences.**

- **`lizard_game.py` is a launcher** — three lines, imports `lagarto.app`.
  Anything more substantial there is a symptom.
- **`procedural_animation.py` and `pygamebase.py` are frozen references.**
  They pre-date the package split. Don't edit them; they document where
  the shape came from.
- **New helpers pick a module by responsibility.** A vector-math helper
  goes in `mathutil`, a colour helper in `palette`. `utils.py` is a
  smell — it's what the split was created to avoid.
- If a module grows past ~600 lines with more than one job inside it,
  that's a signal to split — usually into a `<name>_<subtopic>.py` sibling.
  This has not happened yet; when it does, the ADR that describes the
  split is the ADR that revises this one.

See also: [architecture table](../../CLAUDE.md) for the current module list
and each responsibility.
