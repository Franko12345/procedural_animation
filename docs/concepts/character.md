# Character

A player-selectable [Genome](./genome.md) template plus one exclusive
mechanic. Four characters exist. Zero new art was written to add them —
the same [Parts](./parts.md) drawing pipeline runs for each.

Defined in `lagarto/characters.py`. Constrained by
[ADR-0001](../adr/0001-genome-is-the-creature.md).

## Roster

| Character | Body | Exclusive mechanic |
|---|---|---|
| **LAGARTO** (default) | standard | `rerolls_per_level`: rerolls the level-up card hand (`R`) |
| **VIBORA** | long, no legs | `weapon_cap=2` + fast strong whip — the cap _is_ the mechanic |
| **COURACADO** | large, plated | `can_dash=False` + armour + spikes + `knockback_immune` |
| **LARVA** | tiny | `characters.larva_growth`: grows every N kills, 1 → 6 weapon slots |

Two are locked at start: VIBORA and COURACADO cost DNA in the menu;
LARVA unlocks on the wave-8 achievement.

## Where the shape comes from

`Player.__init__` stores the character's callback in
`self.pending_char_apply` and runs it on the **first `Player.update()`
call**, once `game` really exists. The unified `apply(player, game)`
contract needs a real `game`, but the player is constructed before the
first game step — passing `None` there silently bypassed the contract.
None of the current four characters read `game`; a future one might, and
the deferred call keeps that possibility honest.

The callback reads `armor`, `thorns`, `max_health`, `whip_cooldown` —
all declared in `__init__` above the store, so a character can override
them safely.

Body regeneration goes through `Lizard.rebuild_body(keep_pose=True)`,
_not_ `__init__`. Previously the only path to a new body was
`__init__`, which erased hp/weapons/level/aggro — champions kept an
11-entry `_KEEP` list to remember what to restore. That whole class of
bug disappeared when `rebuild_body` was extracted.

## Colour comes from the slot, not the character

Two players picking the same character in coop still look different.
`Player.__init__` passes `colorset[0]` explicitly, overriding whatever
hue the character genome carries. If a character defined its own
colour, both slots would end up identical.

## Locking

`UNLOCKS` entries with `kind='character'`. `cost=None` = achievement-
only, never for sale. Locked characters **appear in the character list**
with the requirement — invisible rewards are not rewards. See the
`check_achievements` path in `finish_run`.

## Related

- [Genome](./genome.md) — what a character _is_.
- [Champion](./champion.md) — the enemy-side equivalent of "genome +
  named exclusive".
- [Weapon](./weapon.md) — VIBORA's cap and LARVA's growth pass through
  weapon slots.
