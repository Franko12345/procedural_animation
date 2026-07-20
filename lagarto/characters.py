"""Playable characters: four lizards that are played differently, not just tuned.

The premise of this game pays off twice here. The **player is built from a
`Genome` too**, so a character with its own body -- long and legless, wide and
plated, a tiny grub -- costs zero new art: `parts.draw_all` reads the genome
every frame and the silhouette follows. That is why four visually distinct
characters are cheap here and expensive almost everywhere else.

Each character carries:

* a **genome** (the body),
* 2-3 **identity modifiers** -- the same shape as `champions.py`, but describing
  the player. They exist to be *listed on the select screen*: a character you
  cannot summarise is a character nobody picks on purpose.
* **one exclusive mechanic** that changes how you play. The rule taken from
  Isaac and Gungeon: a character defined only by numbers is forgettable. Every
  one of these four changes a *verb* -- how you level up, what your damage
  source is, whether you can dash, or how you grow.

Colour is deliberately NOT part of a character: `Player.__init__` passes
`colorset[0]` explicitly, and that hue is what tells P1 from P2 in co-op. Shape
comes from the character, hue from the player slot -- otherwise two players who
pick the same character are indistinguishable on screen.
"""

from . import config as C
from . import palette
from .genome import Genome


class Character:
    """One playable lizard: body, loadout and the mechanic that defines it."""

    def __init__(self, cid, name, blurb, hue, genome, weapon='cuspe',
                 mods=(), apply=None, unlock=None):
        self.id = cid
        self.name = name
        self.blurb = blurb            # one line, shown under the name
        self.hue = hue                # menu accent only -- never the body colour
        self.genome = genome
        self.weapon = weapon          # starting weapon id
        self.mods = tuple(mods)       # identity modifiers, listed on the select screen
        self.apply = apply            # stat/flag surgery on a fresh Player
        self.unlock = unlock          # None = free; else a progression unlock id

    def color(self):
        return palette.vibrant(self.hue, 0.8, 1.0)

    def make_genome(self):
        """A fresh copy -- the run mutates it (evolution cards, LARVA growth)."""
        return self.genome.copy()


# --------------------------------------------------------------------------- #
#  The four                                                                    #
# --------------------------------------------------------------------------- #

def _lagarto(p):
    """The baseline, plus the one thing that makes 'balanced' a real choice.

    A default character with no mechanic is the option nobody picks twice, so
    this one owns *consistency*: rerolling a level-up hand turns the run from
    something that happens to you into something you build (Isaac's D6).
    """
    p.rerolls_per_level = C.CHAR_LAGARTO_REROLLS


def _vibora(p):
    """The tail is the weapon. Manual, rhythmic, close-range.

    The weapon cap is the point, not a drawback bolted on: with six auto-weapons
    the whip is a bonus, with two it is your damage, and you have to actually
    swing it. Fragile so that being in whip range stays a decision.
    """
    p.weapon_cap = C.CHAR_VIBORA_WEAPON_CAP
    p.whip_cooldown *= C.CHAR_VIBORA_WHIP_CD
    p.whip_mult = C.CHAR_VIBORA_WHIP_MULT
    p.max_health *= C.CHAR_VIBORA_HP
    p.health = p.max_health


def _couracado(p):
    """No dash. You walk through the horde and let it break on you.

    Taking away the dash is the most invasive thing any of these do, so it gets
    paid for three times: armour, contact damage, and immunity to being shoved or
    slowed. The result plays like a wall that advances -- positioning stops being
    about escaping and becomes about *where you stand*.
    """
    p.can_dash = False
    p.armor = min(0.75, p.armor + C.CHAR_COURACADO_ARMOR)
    p.thorns += C.CHAR_COURACADO_THORNS
    p.knockback_immune = True
    p.max_health *= C.CHAR_COURACADO_HP
    p.health = p.max_health


def _larva(p):
    """Starts pathetic and ends enormous -- and you watch it happen.

    This is the character that only this game could have: growth is *visible*
    because the body is regenerated from the genome every frame, so gaining size
    is not a stat readout, it is a silhouette change. Weapon slots unlock as it
    grows, so the early run is genuinely bare and the late run is overloaded.
    """
    p.weapon_cap = 1
    p.growth = 0
    p.max_health *= C.CHAR_LARVA_HP
    p.health = p.max_health


CHARACTERS = [
    Character(
        'lagarto', 'LAGARTO',
        'Equilibrado. Rerrola as cartas uma vez por nivel.',
        130,
        Genome(name='lagarto', size=1.25, leg_count=4, hue=130, sat=0.82, val=0.95),
        mods=('EQUILIBRADO', 'REROLL POR NIVEL'),
        apply=_lagarto,
    ),
    Character(
        'vibora', 'VIBORA',
        'Sem pernas e fragil. A cauda e a arma; so 2 armas automaticas.',
        285,
        Genome(name='vibora', size=1.1, length=2.1, girth=0.78, leg_count=0,
               hue=285, sat=0.85, val=0.95, tail='club', speed=1.12),
        mods=('FRAGIL', 'RABO LETAL', 'SO 2 ARMAS'),
        apply=_vibora,
        unlock='char_vibora',
    ),
    Character(
        'couracado', 'COURACADO',
        'Nao tem dash. Anda pela horda: blindado, espinhoso, imovel.',
        20,
        Genome(name='couracado', size=1.55, girth=1.4, length=0.85, leg_count=4,
               hue=20, sat=0.8, val=0.95, plates=2, speed=0.78),
        mods=('LENTO', 'BLINDADO', 'ESPINHOS', 'SEM DASH'),
        apply=_couracado,
        unlock='char_couracado',
    ),
    Character(
        'larva', 'LARVA',
        'Comeca minuscula com 1 arma. Cresce a cada abate ate ficar enorme.',
        58,      # amarelo: 95 ficava perto demais do verde do LAGARTO na tela
                 # de selecao, e duas cartas da mesma cor apagam a identidade
        Genome(name='larva', size=0.72, girth=1.25, length=0.8, leg_count=0,
               hue=95, sat=0.9, val=1.0, speed=1.05),
        mods=('INDEFESA NO INICIO', 'CRESCE MATANDO', 'SLOTS PROGRESSIVOS'),
        apply=_larva,
        unlock='char_larva',
    ),
]
BY_ID = {c.id: c for c in CHARACTERS}
DEFAULT = CHARACTERS[0].id


def get(cid):
    return BY_ID.get(cid) or BY_ID[DEFAULT]


def is_locked(char, meta):
    """Locked characters still appear on the select screen, greyed out with their
    requirement -- a reward you cannot see is not a reward."""
    from . import progression
    return char.unlock is not None and \
        not progression.unlocked(meta, 'character', char.id)


def available(meta):
    return [c for c in CHARACTERS if not is_locked(c, meta)]


# --------------------------------------------------------------------------- #
#  LARVA growth                                                                #
# --------------------------------------------------------------------------- #

def larva_growth(player, game):
    """One growth step: bigger body, more health, and eventually a weapon slot.

    Called on kill. Uses ``rebuild_body`` rather than re-running ``__init__``:
    the player is mid-run, so weapons, level, XP and mutations all have to
    survive the body changing underneath them.
    """
    if player.character_id != 'larva':
        return
    player.growth += 1
    step = C.CHAR_LARVA_KILLS_PER_STEP
    if player.growth % step or player.genome.size >= C.CHAR_LARVA_MAX_SIZE:
        return
    g = player.genome
    g.size = min(C.CHAR_LARVA_MAX_SIZE, g.size * C.CHAR_LARVA_SIZE_STEP)
    player.rebuild_body()
    player.max_health += C.CHAR_LARVA_HP_STEP
    player.health = min(player.max_health, player.health + C.CHAR_LARVA_HP_STEP)
    grew_slot = player.weapon_cap < C.CHAR_LARVA_MAX_SLOTS
    if grew_slot:
        player.weapon_cap += 1
    game.fx.ring(player.pos, palette.vibrant(95, 0.8, 1.0))
    game.fx.spark_burst(player.pos, palette.vibrant(95, 0.7, 1.0), 16, 320)
    game.fx.popup(player.pos, "CRESCEU!" if not grew_slot else "+1 ARMA")
    return True
