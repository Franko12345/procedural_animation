# Camp is a walkable clearing, not a menu screen

**Context.** The between-round camp started as a menu screen: pause the
world, show a full-screen UI, pick an option, unpause. Fine mechanically,
completely disconnected from the play state.

**Decision.** The camp is a state of the world (`state == 'camp'`) with two
modes on the same substrate: `camp['mode'] = 'field'` (the player walks
around) or `'shop'` (menu open). Three doors + a beetle tent are POIs in
world space. Picking a route means crossing a door.

**Why.** The play loop already runs `ctrl.poll` and `cam.follow` every frame
in every state, so movement in `field` is free — `player.update` in a
different `game.state`. Bolting menus on top of that would have re-invented
input and camera. And "step through a door" reads as commitment; picking
a list item does not.

**Consequences.**

- Shop is **choice, not toll**: skipping the tent and walking straight to a
  door is legal. That's the point — the tent has to earn the visit.
- Interaction is locked until each POI touches the ground (`_camp_impact`).
  Objects fall from the sky with shadow-grows telegraph on landing; entering
  a mid-air door was a bug that had to be closed.
- Two navigation models had to converge: keyboard/mouse/gamepad in shop mode,
  WASD/stick in field mode. `app._camp_shop_open` gates which owns input.
- The two states share the same [Round](../concepts/round.md) pipeline; the
  world does not tear down between camp and play.

See also: [`Camp`](../concepts/camp.md), [`Route`](../../CONTEXT.md).
