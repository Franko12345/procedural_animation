# Concepts

One file per concept. Each file introduces the concept, links to the
neighbours that reference it, and points at the ADRs that constrain it.

Prose here uses the canonical term from [`CONTEXT.md`](../../CONTEXT.md).
If a concept file names a word the glossary avoids, one of the two is
wrong.

## Index

### Anatomy

- [Genome](./genome.md) — the bag of numbers that defines a creature
- [Spine](./spine.md) — the follow-the-leader physical chain
- [Leg](./leg.md) — two-bone IK with foot planting
- [Parts](./parts.md) — spikes, plates, horns, tail-tip, fins

### Creatures

- [Species](./species.md) — named genome templates
- [Character](./character.md) — playable genomes + exclusive mechanic
- [Champion](./champion.md) — named variant + orthogonal modifier
- [Boss](./boss.md) — FSM + personality + phase transitions

### Combat

- [Weapon](./weapon.md) — the 8 automatic attacks
- [Charm](./charm.md) — permanent camp slot
- [Synergy](./synergy.md) — named combos with Synergy Factor

### Run

- [Round](./round.md) — themed wave from nests to camp
- [Camp](./camp.md) — walkable clearing with shop + doors

## When you add a concept file

1. Add a `**Term**` block to [`CONTEXT.md`](../../CONTEXT.md) with `_Avoid_`
   synonyms.
2. Write `<slug>.md` here — short. Intro sentence, then the pieces that
   matter, then links out.
3. Update this index.
4. Grep for the word in existing concept docs and link back to yours where
   it's referenced.
