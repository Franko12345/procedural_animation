# Might multiplies weapons, dash, and whip

**Context.** `Player.might` was originally read only by weapons. Cards
advertised "damage bonus" but affected 1/3 of the ways the player deals
damage. Dash was a constant. Whip was a constant. Wave 20 whip did the
same 5 damage as wave 1 whip.

**Decision.** [`Might`](../../CONTEXT.md) is the one damage multiplier.
Weapons, dash (`Player.dash_damage()`), and whip (`Player._whip_hit`) all
read it. Base numbers are lowered to compensate; the multipliers do the
scaling.

**Why.** The card text is a promise. When Vigor said "+20% damage" and only
weapons noticed, the promise was broken. And Membranas advertised "stronger
dash" while only affecting dash speed/duration/cost — the wing card lied
about the wing effect for months before anyone noticed.

**Consequences.**

- The dash calculation lives inside `Player.dash_damage()` because there
  were **two** call sites reading `C.DASH_DAMAGE` directly (enemy and nest).
  Adding a scale to one would have skipped the other silently. Same
  centralisation pattern as [ADR-0007](./0007-cosmetic-skeleton-for-tail.md).
- Card descriptions had to be corrected to say "affects weapons, dash and
  whip". Not doing this in the same PR re-broke the promise from the other
  side. **When you add scale to a new source, fix the card text in the same
  commit.**
- The whip's tail-club modifier now stacks _on top_ of Might, so the
  progression reads: 2 (nude) → 5 (with club) → 12 (club + Vigor + DNA
  Potência). Same for dash: 4 → 6 → 13. The dash / whip cards are now
  actually the meaningful upgrades they claimed to be.
- **Contact damage is not scaled.** Enemies use `lizard.contact_damage(max_r,
  wave)`; that's their difficulty knob, not the player's damage.

See also: [Weapon](../concepts/weapon.md), [Mutation](../../CONTEXT.md).
