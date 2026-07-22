"""Game: world state, spawning, waves, collisions, HUD and the fixed-step update.

Holds the players, AI lizards and pickups, resolves eating/combat, drives the
escalating predator waves and draws everything (background, shadows, entities,
particles, HUD, game-over).
"""

import copy
import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import fonts
from .mathutil import clamp, ease_out, lerp, vfrom_angle, safe_norm, decay
from .spine import build_radii
from .lizard import Player, AILizard
from . import species
from . import evolution
from . import audio
from . import icons
from . import ui
from . import progression
from . import palette
from . import weapons
from . import characters
from . import charms as charmlib
from .pickups import Bug, Fruit, Egg
from .fx import FX, shadow
from .camera import Camera
from .world import World
from .collision import separate
from .rounds import RoundManager


def _bar_tail(surf, bx, by, h, color, phase, t):
    """A little lizard TAIL wagging off the top of the bar.

    Same vocabulary as the real body (``spine.RADII_PROFILE``): a curved chain
    that tapers to a point, not a stick with a bead on the end. Drawn as a run of
    filled circles shrinking base->tip; the sway grows toward the tip so the last
    segments whip like a follow-through.
    """
    n = 9
    length = h * 1.5                       # long and whippy, still clears the label row
    r0 = max(2.0, h * 0.32)                # slimmer root than a leaf
    core = palette.lighten(color, 0.3)
    for k in range(n):
        f = k / (n - 1)
        py = by - f * length
        # tip sways most; a phase per tail so they don't wag in unison
        px = bx + math.sin(t * 3.4 + phase + f * 2.6) * (h * 0.62) * f * f
        r = max(1, int(r0 * (1.0 - f) ** 1.3 + 0.8))   # curved taper -> pointed tip
        pygame.draw.circle(surf, color, (int(px), int(py)), r)
        if r > 2:                                   # top-left highlight = light source
            pygame.draw.circle(surf, core,
                               (int(px - r * 0.3), int(py - r * 0.3)), max(1, r // 2))


def _bio_bar(surf, x, y, w, h, frac, color, t, flagella=0, glow=None):
    """An organic 'membrane sac' bar instead of a flat rectangle.

    Drawn entirely with primitives (no per-frame Surface -- the ui._tint rule),
    animated purely by ``t`` so it costs the same whether it moves or not:
      * a dark rounded capsule (the sac),
      * a fill whose leading edge bulges and breathes,
      * a soft inner highlight up top (a light source), and
      * optional flagella -- little cilia that sway off the fill's leading edge,
        which is what sells "biological" at a glance.
    """
    frac = 0.0 if frac < 0 else (1.0 if frac > 1 else frac)
    r = h // 2
    cap = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (16, 18, 28), cap, border_radius=r)
    fw = int(w * frac)
    if fw > 1:
        fill = pygame.Rect(x, y, fw, h)
        pygame.draw.rect(surf, palette.darken(color, 0.25), fill, border_radius=r)
        # top meniscus: a lighter band with a slow breathing wobble
        band_h = max(2, h // 3)
        pygame.draw.rect(surf, palette.lighten(color, 0.35),
                         (x, y + 1, fw, band_h), border_radius=r)
        # leading-edge bulge, pulsing -- reads as fluid under pressure
        bulge = int(h * (0.55 + 0.12 * math.sin(t * 3.0)))
        tip = (x + fw, y + h // 2)
        palette.glow(surf, tip, bulge, color, 0.5)
        pygame.draw.circle(surf, palette.lighten(color, 0.5), tip, max(2, h // 3))
        for k in range(flagella):
            fx = x + int(fw * (k + 0.5) / max(1, flagella))
            _bar_tail(surf, fx, y + 1, h, color, phase=k * 2.1, t=t)
    if glow:
        palette.glow(surf, (x + fw, y + h // 2), h, color, 0.25)
    # living rim
    pygame.draw.rect(surf, palette.lighten(color, 0.15) if frac > 0 else (40, 44, 60),
                     cap, 2, border_radius=r)

def _dial(surf, center, r, frac, color, font, label, t, enabled=True):
    """Radial cooldown dial: fills as the ability recharges, pulses when ready.

    ``enabled=False`` (not enough energy) greys the whole thing out.
    """
    ready = frac >= 0.999 and enabled
    if not enabled:
        color = (78, 82, 104)
    pygame.draw.circle(surf, (34, 38, 54), center, r)
    if frac > 0:
        pts = [center]
        steps = max(3, int(frac * 22))
        for i in range(steps + 1):
            pts.append(center + vfrom_angle(-90 + 360 * frac * (i / steps), r))
        if len(pts) >= 3:
            pygame.draw.polygon(surf, color, pts)
    if ready:
        pulse = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(t * 6))
        palette.glow(surf, center, r * 2.2, color, pulse)
    pygame.draw.circle(surf, (96, 102, 136) if not ready else color, center, r, 2)
    ui.text(surf, font, label, (center[0] + r + 6, center[1] - font.get_height() // 2),
            (232, 234, 250) if ready else (146, 150, 178))


_VIGNETTE = None


def _vignette(surf):
    """Smooth radial dark edges so the vivid centre pops (built once, then blitted)."""
    global _VIGNETTE
    if _VIGNETTE is None:
        s = 80
        small = pygame.Surface((s, s), pygame.SRCALPHA)
        cx = cy = (s - 1) / 2.0
        maxd = (cx * cx + cy * cy) ** 0.5
        for y in range(s):
            for x in range(s):
                d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / maxd
                a = 0 if d < 0.4 else int(150 * ((d - 0.4) / 0.6) ** 2)
                small.set_at((x, y), (0, 0, 0, min(150, a)))
        _VIGNETTE = pygame.transform.smoothscale(small, (C.WIDTH, C.HEIGHT))
    surf.blit(_VIGNETTE, (0, 0))


class TopStack:
    """Vertical layout for the top-centre column.

    Six things live there -- score, wave line, combo, theme banner, boss name and
    boss bar -- and each used to hardcode its own ``y`` with no idea of the others.
    On a boss wave with a live combo that was *three* overlaps at once, and the
    banner writes for 2.2s exactly when the boss spawns, so it was guaranteed to
    be seen. Now every element asks for the height it needs and gets the next free
    band, which also means new elements (boss phase bars, Phase 4) can never
    silently land on top of an existing one.

    Elements reserve in draw order, so the caller must draw top-down: HUD, then
    banner, then boss bar.
    """

    def __init__(self, top=10, gap=4):
        self.top = top
        self.gap = gap
        self.y = top

    def reset(self):
        self.y = self.top

    def take(self, h):
        """Reserve a band ``h`` tall and return its top ``y``."""
        y = self.y
        self.y += h + self.gap
        return y


class Game:
    def __init__(self, num_players, controllers, font, bigfont, meta=None,
                 mode='normal', chars=None):
        self.mode = mode                     # 'normal' (ends at the final boss) | 'endless'
        self.meta = meta if meta is not None else progression.load()
        self.run_banked = False
        self.font = font
        self.bigfont = bigfont
        # dial labels only: at 18pt "DASH" is 48px wide and ran into the next
        # dial's circle (68px pitch, 11px radius). They are secondary readouts,
        # so shrinking them fixes the collision *and* improves the hierarchy.
        self.smallfont = fonts.get(14)
        self.cam = Camera()
        self.fx = FX()
        self.world = World()

        cx, cy = C.WORLD_W / 2, C.WORLD_H / 2
        self.cam.pos = Vector2(cx, cy)
        self.players = []
        for i in range(num_players):
            off = Vector2(-80 if i == 0 else 80, 0)
            colorset = C.COL_PLAYER if i == 0 else C.COL_PLAYER2
            cid = (chars[i] if chars and i < len(chars) else characters.DEFAULT)
            pl = Player(Vector2(cx, cy) + off, controllers[i], colorset, i,
                        character=characters.get(cid))
            progression.apply_to_player(self.meta, pl)     # permanent upgrades
            self.players.append(pl)

        self.enemies = []
        self.pending_enemies = []     # spawned mid-step (e.g. DIVISOR split), drained safely
        self.friends = []
        self.prey = []
        self.pickups = []
        self.projectiles = []
        self.puddles = []

        self.score = 0
        self.kills = 0
        self.wave = 0
        self.wave_timer = 4.0
        self.time = 0.0
        self.state = 'play'
        self.combo = 0
        self.combo_timer = 0.0
        self.combo_flash = 0.0
        self.pollen = 0
        self.hitstop = 0.0        # freeze frames on heavy impacts
        self.flash = 0.0          # brief white screen flash
        self.dt_last = C.DT       # boss.py's per-frame barrage tick reads this
        self.camp = None
        self.rounds = RoundManager(self)
        self.cards = []
        self.card_idx = 0
        self.levelup_player = None
        self.pause_mode = 'menu'  # 'menu' | 'options' | 'controls'
        self.pause_sel = 0
        self.pause_prev = 'play'  # state to return to (pause can open from camp too)
        self.ui_t = 0.0           # clock for the level-up / camp entry animation
        self.pick = None          # a choice being absorbed by the player (see _step_pick)
        self.ui_fx = 0.0          # keeps fx drawn over the veil just after an impact
        self._uilayer = None      # scratch surface so screen shake can move the whole UI
        self._panels = {}         # rendered card/shop/route panels, keyed by their state
        self.top = TopStack()     # shared top-centre column (see TopStack)
        self._card_rects = []
        self._shop_rects = []
        self._route_rects = []
        self._charm_rects = []

        for _ in range(46):
            self.pickups.append(Bug(self._rand_world()))
        for _ in range(5):
            self.pickups.append(Fruit(self._rand_world()))
        for _ in range(3):
            self.pickups.append(Egg(self._rand_world()))
        for _ in range(8):
            self.prey.append(self._spawn_prey())

    # ---- helpers -------------------------------------------------------- #
    def _rand_world(self, margin=120):
        return Vector2(random.uniform(margin, C.WORLD_W - margin),
                       random.uniform(margin, C.WORLD_H - margin))

    def _rand_edge_near(self, center, dist=560):
        return center + vfrom_angle(random.uniform(0, 360), dist)

    def shake(self, m):
        self.cam.add_shake(m)

    def crit_fx(self, pos):
        """Feedback for a weak-point (head) hit."""
        self.fx.spark_burst(pos, (255, 232, 150), 12, 380)
        self.fx.popup(pos, "CRITICO!", (255, 226, 120))
        audio.play('hit', 1.0)

    def punch(self, freeze=0.06, shake=6, flash=0.0):
        """Impact feedback: brief freeze + shake (+ optional screen flash)."""
        self.hitstop = max(self.hitstop, freeze)
        self.cam.add_shake(shake)
        if flash:
            self.flash = max(self.flash, flash)

    def add_score(self, n):
        self.score += int(n * self.combo_mult())

    def combo_mult(self):
        return 1.0 + min(self.combo, 30) * 0.08     # up to ~3.4x

    def add_combo(self):
        self.combo += 1
        self.combo_timer = 3.2
        self.combo_flash = 1.0

    def add_pollen(self, n):
        mult = max((getattr(p, 'pollen_mult', 1.0) for p in self.players), default=1.0)
        self.pollen += int(n * self.combo_mult() * mult)

    def alive_players(self):
        return [p for p in self.players if not p.dead]

    def nearest_player(self, pos):
        best, bd = None, 1e9
        for p in self.players:
            if p.dead or p.down:
                continue
            d = p.pos.distance_to(pos)
            if d < bd:
                best, bd = p, d
        return best

    def nearest_enemy(self, pos, rng):
        best, bd = None, rng
        for e in self.enemies:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def nearest_prey(self, pos, rng):
        best, bd = None, rng
        for e in self.prey:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def nearest_threat(self, pos, rng):
        """Closest thing a prey should flee: a player or a predator."""
        best, bd = None, rng
        for p in self.players:
            if p.dead or p.down:
                continue
            d = p.pos.distance_to(pos)
            if d < bd:
                best, bd = p, d
        for e in self.enemies:
            if e.dead:
                continue
            d = e.pos.distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def give_xp(self, amount):
        for p in self.players:
            if not p.dead and not p.down:
                p.gain_xp(amount, self)

    def _enter_levelup(self, player):
        self.levelup_player = player
        self.cards = evolution.roll_cards(player, 3)
        self.card_idx = 0
        self.state = 'levelup'
        self.ui_t = 0.0
        self.pick = None
        self._panels.clear()
        audio.play('levelup')
        self.fx.popup(player.pos, f"NIVEL {player.level}!", C.COL_WHITE)
        self.fx.ring(player.pos, player.colorset[0])
        self.shake(4)

    def reroll_cards(self):
        """LAGARTO: redraw the level-up hand. Returns True if it happened.

        Rerolling is what turns a run from something that happens to you into
        something you build -- it is the whole reason to pick LAGARTO twice.
        Blocked while an absorption is playing (``ui_busy``) for the same reason
        picking is: the effect has not been applied yet.
        """
        p = self.levelup_player
        if self.state != 'levelup' or self.ui_busy() or not p or p.rerolls <= 0:
            return False
        p.rerolls -= 1
        self.cards = evolution.roll_cards(p, 3)
        self.card_idx = 0
        self._panels.clear()          # cards are cached by index+state
        audio.play('ui')
        self.fx.ring(p.pos, p.colorset[0])
        return True

    # ---- choosing: pick -> absorption animation -> effect ---------------- #
    def ui_busy(self):
        """True while a screen is still animating in or absorbing a choice."""
        return self.pick is not None or self.ui_t < C.UI_READY

    def _start_pick(self, kind, index, rect, color, dur, item=None):
        self.pick = dict(kind=kind, index=index, item=item, color=color,
                         rect=pygame.Rect(rect), t=0.0, dur=dur, sparked=False)
        audio.play('ui')
        self.punch(freeze=0.0, shake=3)      # small kick as it leaves the slot
        if kind == 'shop':
            # the pollen you just spent bursts out of the stall
            slot = self.cam.s2w(rect.center)
            self.fx.burst(slot, C.COL_POLLEN, 18, 260)
            self.fx.spark_burst(slot, palette.lighten(C.COL_POLLEN, 0.35), 14, 340)
            self.fx.burst(slot, color, 14, 200)
            self.fx.ring(slot, C.COL_POLLEN)

    def _pick_player(self):
        return self.levelup_player or (self.players[0] if self.players else None)

    def _pick_pose(self):
        """Where the chosen item is *right now*: (screen pos, scale, alpha)."""
        pk = self.pick
        # present it *above* the lizard, not dead centre -- the camera keeps the
        # player centred, so centring the card too would leave nothing to fly along
        mid = Vector2(C.WIDTH / 2, C.HEIGHT / 2 - 150)
        t = pk['t']
        start = Vector2(pk['rect'].center)
        if pk['kind'] == 'route':            # short version: just swells in place
            f = ease_out(min(1.0, t / max(pk['dur'], 1e-4)))
            return start, 1.0 + 0.18 * f, 1.0
        if t < C.PICK_CENTER:                # slide to the middle of the screen
            f = ease_out(t / C.PICK_CENTER)
            return start.lerp(mid, f), lerp(1.0, 1.22, f), 1.0
        if t < C.PICK_HOLD:                  # hold, so you can read what you got
            return mid, 1.22, 1.0
        f = clamp((t - C.PICK_HOLD) / max(C.PICK_END - C.PICK_HOLD, 1e-4), 0, 1)
        f = f * f                            # accelerate into the lizard
        p = self._pick_player()
        tgt = Vector2(self.cam.w2s(p.pos)) if p else mid
        return mid.lerp(tgt, f), lerp(1.22, 0.10, f), lerp(1.0, 0.4, f)

    def _step_pick(self, dt):
        pk = self.pick
        pk['t'] += dt
        if pk['kind'] != 'route':
            pos = self.cam.s2w(self._pick_pose()[0])
            shop = pk['kind'] == 'shop'
            if pk['t'] >= C.PICK_HOLD:        # comet trail on the way to the player
                self.fx.trail(pos, pk['color'])
                if shop:                      # purchases fly in a thicker, golden comet
                    self.fx.trail(pos, C.COL_POLLEN)
                    self.fx.spark_burst(pos, C.COL_POLLEN, 2, 150)
            elif shop and pk['t'] < C.PICK_CENTER:
                # sparkles while it drifts up out of the stall
                self.fx.trail(pos, C.COL_POLLEN)
        if pk['t'] >= pk['dur']:
            self._finish_pick()

    def _finish_pick(self):
        """Impact: the choice lands *in* the player -- only now does it take effect."""
        pk = self.pick
        self.pick = None
        self.ui_fx = 1.1          # the impact burst must survive the veil too
        p = self._pick_player()
        if p is not None and pk['kind'] != 'route':
            self.fx.burst(p.pos, pk['color'], 26, 260)
            self.fx.spark_burst(p.pos, palette.lighten(pk['color'], 0.4), 18, 380)
            self.fx.ring(p.pos, pk['color'])
            self.fx.ring(p.pos, palette.lighten(pk['color'], 0.5))
            self.punch(freeze=0.09, shake=12, flash=0.10)
            audio.play('evolve')
            if pk['kind'] == 'shop':
                # a purchase lands with a golden pop on top of the item's own colour
                self.fx.burst(p.pos, C.COL_POLLEN, 30, 320)
                self.fx.spark_burst(p.pos, C.COL_POLLEN, 24, 460)
                self.fx.spark_burst(p.pos, C.COL_WHITE, 10, 260)
                self.fx.ring(p.pos, C.COL_POLLEN)
                if pk['item']:
                    self.fx.popup(p.pos, pk['item']['name'], C.COL_POLLEN)
                audio.play('buy')
        if pk['kind'] == 'card':
            self._apply_card(pk['item'])
        elif pk['kind'] == 'shop':
            self._apply_buy(pk['index'])
        elif pk['kind'] == 'route':
            self._apply_route(pk['index'])

    def choose_card(self, i):
        if self.state != 'levelup' or not self.cards or self.ui_busy():
            return
        i = max(0, min(len(self.cards) - 1, i))
        self.card_idx = i
        rect = (self._card_rects[i] if i < len(self._card_rects)
                else pygame.Rect(C.WIDTH // 2 - 120, C.HEIGHT // 2 - 150, 240, 300))
        self._start_pick('card', i, rect, self.cards[i].color, C.PICK_END,
                         item=self.cards[i])

    def _apply_card(self, card):
        p = self._pick_player()
        if p is None:
            return
        if getattr(card, 'is_weapon', False) or getattr(card, 'is_item', False):
            card.apply(p, self)
            # items count toward synergies too (evolution.owned_tags), so the
            # check has to run for them as well, not only for mutations
            for name in evolution.check_synergies(p, self):
                self.fx.popup(p.pos, name, C.COL_WHITE)
        else:
            p.apply_mutation(card, self)
        p.pending_levelups = max(0, p.pending_levelups - 1)
        self.fx.popup(p.pos, card.name, card.color)
        self.cards = []
        self.state = 'play'          # step() re-enters if more level-ups are queued

    # ---- camp (route + shop between rounds) ----------------------------- #
    def _enter_camp(self):
        from .rounds import THEMES, THEME_KEYS
        picks = random.sample(THEME_KEYS, min(3, len(THEME_KEYS)))
        bonuses = ['cura', 'polen', 'carta']
        random.shuffle(bonuses)
        routes = [dict(theme=k, bonus=bonuses[i % 3], label=THEMES[k]['banner'])
                  for i, k in enumerate(picks)]
        # A PHYSICAL clearing (Hades): the shop is a tent you can walk up to and the
        # routes are three doors you walk through. Everything is placed around the
        # spot where the players cleared the wave, so no teleport is needed.
        alive = [p for p in self.players if not p.dead]
        center = Vector2()
        for p in (alive or self.players):
            center += p.pos
        center /= max(1, len(alive or self.players))
        center.x = clamp(center.x, 420, C.WORLD_W - 420)
        center.y = clamp(center.y, 420, C.WORLD_H - 420)
        tent = center + Vector2(*C.CAMP_TENT_OFF)
        n = len(routes)
        doors = []
        for i, r in enumerate(routes):
            dx = (i - (n - 1) / 2) * C.CAMP_DOOR_SPAN
            doors.append(dict(pos=center + Vector2(dx, -C.CAMP_DOOR_UP), route=r,
                              delay=C.CAMP_DOOR_DELAY + i * C.CAMP_DOOR_STAGGER,
                              landed=False))
        self.camp = dict(routes=routes, shop=self._roll_shop(), sel=0,
                         focus='shop', shop_sel=0, charm_col=0, charm_row=0,
                         mode='field', center=center, tent=tent, doors=doors,
                         reopen_cd=C.CAMP_REOPEN_CD,
                         born=self.time, tent_delay=C.CAMP_TENT_DELAY, tent_landed=False)
        self._route_rects = []
        self._shop_rects = []
        self._charm_rects = []
        self.state = 'camp'
        self.ui_t = 0.0
        self.pick = None
        self._panels.clear()
        # a clean clearing: drop leftover prey/hazards so nothing clutters a
        # doorway or lingers on the ground while you shop
        self.prey = []
        self.projectiles = []
        self.puddles = []
        for p in self.players:
            if not p.dead:
                p.health = min(p.max_health, p.health + p.max_health * 0.12)

    def _roll_shop(self):
        def heal(g):
            for pl in g.players:
                pl.health = min(pl.max_health, pl.health + 40)

        def vitality(g):
            for pl in g.players:
                pl.max_health += 20; pl.health += 20

        def might(g):
            for pl in g.players:
                pl.might *= 1.15

        def haste(g):
            for pl in g.players:
                pl.cooldown_mult *= 0.9

        def egg(g):
            for pl in g.players:
                if pl.dead:
                    continue
                f = AILizard(pl.pos, 'friend', 0.9, C.COL_FRIEND)
                f.hp = C.FRIEND_HP
                f.sync_max_hp()
                f.life = C.FRIEND_LIFE
                g.friends.append(f)

        def charm(g):
            for pl in g.players:
                if pl.dead:
                    continue
                avail = [c for c in charmlib.CHARMS if c not in pl.charms_owned
                         and progression.unlocked(self.meta, 'charm', c)]
                if avail:
                    pl.gain_charm(random.choice(avail), g)
        return [
            dict(name='Nectar de Cura', desc='+40 vida', cost=12, hue=140, icon='health', fn=heal),
            dict(name='Vitalidade', desc='+20 vida maxima', cost=28, hue=5, icon='health', fn=vitality),
            dict(name='Vigor', desc='+15% dano das armas', cost=32, hue=0, icon='might', fn=might),
            # charms sao permanentes e fortes -> tem que doer no bolso (era 30)
            dict(name='Charm', desc='adaptacao p/ um slot', cost=150, hue=280, icon='nectar', fn=charm),
            dict(name='Ovo de Amigo', desc='aliado temporario', cost=40, hue=270, icon='legs', fn=egg),
        ]

    def _step_camp(self, dt):
        """The clearing. Shop mode is the old frozen menu; field mode lets the
        players actually WALK -- touch the tent to shop, cross a door to advance."""
        self.ui_t += dt
        self.ui_fx = decay(self.ui_fx, dt)
        if self.pick:                         # absorbing a purchase: everything frozen
            self._step_pick(dt)
            self.fx.update(dt)
            return
        if self.camp.get('mode') == 'shop':   # menu open: frozen, like the old camp
            self.fx.update(dt)
            return
        # ---- field mode: live movement + POI interaction ---- #
        self.time += dt
        for p in self.players:
            if not p.dead:
                p.update(dt, self)
        for f in self.friends:                # pets keep following you between rounds
            if not f.dead:
                f.update(dt, self)
        self.world.update(dt)
        self.fx.update(dt)
        self.combo_flash = decay(self.combo_flash, dt, 2)
        self.camp['reopen_cd'] = decay(self.camp.get('reopen_cd', 0.0), dt)
        self._update_camp_drop()              # the pieces fall in with a slam
        # touch the tent -> open the shop (only once it has landed)
        if self.camp['reopen_cd'] <= 0 and self.camp['tent_landed']:
            for p in self.players:
                if not p.dead and p.pos.distance_to(self.camp['tent']) < C.CAMP_TENT_R:
                    self.camp['mode'] = 'shop'
                    self.camp['focus'] = 'shop'
                    self.ui_t = 0.0           # replay the drop-in
                    self._panels.clear()
                    audio.play('ui', 0.6)
                    return
        # cross a door -> take that route (Hades: doors commit, no menu)
        for i, dr in enumerate(self.camp['doors']):
            if not dr['landed']:
                continue
            for p in self.players:
                if not p.dead and p.pos.distance_to(dr['pos']) < C.CAMP_DOOR_R:
                    self.fx.spark_burst(dr['pos'], C.COL_ENEMY, 18, 320)
                    self.fx.ring(dr['pos'], C.COL_ENEMY)
                    self._apply_route(i)
                    return

    def camp_close_shop(self):
        """Leave the tent back to the clearing (with a re-open cooldown so a step
        standing on the tent does not instantly reopen it)."""
        if self.camp and self.camp.get('mode') == 'shop' and self.pick is None:
            self.camp['mode'] = 'field'
            self.camp['reopen_cd'] = C.CAMP_REOPEN_CD
            audio.play('ui', 0.5)

    def _camp_drop_off(self, delay):
        """World-y offset of a camp piece as it falls in (negative = still up in
        the air). Ease-IN so it accelerates and SLAMS down."""
        t = (self.time - self.camp['born']) - delay
        if t <= 0:
            return -C.CAMP_DROP_H
        if t >= C.CAMP_DROP_DUR:
            return 0.0
        f = t / C.CAMP_DROP_DUR
        return -C.CAMP_DROP_H * (1.0 - f * f)

    def _camp_impact(self, pos, big):
        """The juice when a piece hits the ground: shake + dust + sparks + ring."""
        self.shake(15 if big else 9)
        self.fx.burst(pos, (150, 120, 84), 30 if big else 18, 380)
        self.fx.spark_burst(pos, (224, 202, 150), 18 if big else 11, 400)
        self.fx.ring(pos, (214, 184, 124))
        if big:
            self.fx.ring(pos, (245, 232, 210))
        audio.play('hit', 0.65 if big else 0.45)

    def _update_camp_drop(self):
        """Fire the landing juice once, as each piece touches down."""
        elapsed = self.time - self.camp['born']
        if not self.camp['tent_landed'] and elapsed >= self.camp['tent_delay'] + C.CAMP_DROP_DUR:
            self.camp['tent_landed'] = True
            self._camp_impact(self.camp['tent'], big=True)
        for dr in self.camp['doors']:
            if not dr['landed'] and elapsed >= dr['delay'] + C.CAMP_DROP_DUR:
                dr['landed'] = True
                self._camp_impact(dr['pos'], big=False)

    def camp_equip(self, cid):
        if self.ui_busy():
            return
        if self.players and not self.players[0].dead:
            self.players[0].equip_charm(cid)

    # ---- charm grid: one column per slot, walked by keyboard/gamepad -------- #
    def camp_charms(self, col):
        """Owned charms in slot column ``col``, in the order they are drawn."""
        if not self.players:
            return []
        col = max(0, min(len(C.CHARM_SLOTS) - 1, col))
        slot = C.CHARM_SLOTS[col][0]
        return [c for c in self.players[0].charms_owned
                if charmlib.CHARMS[c].slot == slot]

    def camp_has_charms(self):
        return any(self.camp_charms(i) for i in range(len(C.CHARM_SLOTS)))

    def camp_move_charm(self, dcol, drow):
        """Walk the grid. Returns True if the cursor actually moved, so the caller
        knows whether up/down should instead leave the charm area."""
        if not self.camp:
            return False
        n = len(C.CHARM_SLOTS)
        col = self.camp.get('charm_col', 0)
        row = self.camp.get('charm_row', 0)
        if dcol:
            for _ in range(n):              # skip slots with nothing owned yet
                col = (col + dcol) % n
                if self.camp_charms(col):
                    break
            row = 0
        elif drow:
            owned = self.camp_charms(col)
            if not (0 <= row + drow < len(owned)):
                return False                # at an end -> let focus move on
            row += drow
        self.camp['charm_col'] = col
        self.camp['charm_row'] = max(0, min(row, len(self.camp_charms(col)) - 1))
        return True

    def camp_equip_cursor(self):
        if not self.camp:
            return
        owned = self.camp_charms(self.camp.get('charm_col', 0))
        row = self.camp.get('charm_row', 0)
        if 0 <= row < len(owned):
            self.camp_equip(owned[row])

    def camp_buy(self, i):
        if not self.camp or i < 0 or i >= len(self.camp['shop']) or self.ui_busy():
            return
        it = self.camp['shop'][i]
        if self.pollen < it['cost']:
            return
        # pay now (so the price can't be spent twice mid-animation), grant on impact
        self.pollen -= it['cost']
        self.camp['shop_sel'] = i
        # the 'buy' chime belongs on the impact, not here -- see _finish_pick
        rect = (self._shop_rects[i] if i < len(self._shop_rects)
                else pygame.Rect(C.WIDTH // 2 - 88, 164, 176, 132))
        self._start_pick('shop', i, rect, palette.vibrant(it['hue'], 0.8, 1.0),
                         C.PICK_END, item=it)

    def _apply_buy(self, i):
        if not self.camp or i < 0 or i >= len(self.camp['shop']):
            return
        it = self.camp['shop'][i]
        it['fn'](self)
        it['cost'] = int(it['cost'] * 1.6)
        self.camp['msg'] = it['name']
        self.camp['msg_t'] = 1.4

    def camp_pick_route(self, i):
        if not self.camp or self.ui_busy():
            return
        i = max(0, min(len(self.camp['routes']) - 1, i))
        self.camp['sel'] = i
        rect = (self._route_rects[i] if i < len(self._route_rects)
                else pygame.Rect(C.WIDTH // 2 - 125, 496, 250, 140))
        self._start_pick('route', i, rect, C.COL_ENEMY, C.PICK_ROUTE_END)

    def _apply_route(self, i):
        if not self.camp:
            return
        r = self.camp['routes'][max(0, min(len(self.camp['routes']) - 1, i))]
        if r['bonus'] == 'cura':
            for pl in self.players:
                pl.health = pl.max_health
        elif r['bonus'] == 'polen':
            self.pollen += 25
        elif r['bonus'] == 'carta':
            for pl in self.alive_players():
                pl.pending_levelups += 1
        self.camp = None
        self.state = 'play'
        self.rounds.request_next(r['theme'])

    def _spawn_prey(self):
        return species.make(random.choice(species.PREY_SPECIES), self._rand_world())

    def _spawn_enemy(self, pos, pool=None):
        key = random.choice(pool or species.ENEMY_SPECIES)
        return species.make(key, pos)

    def nearest_edible(self, pos, rng):
        """Nearest grabbable thing within range -> the tongue auto-aims at it."""
        best, bd = None, rng
        for group in (self.pickups, self.prey):
            for e in group:
                if e.dead:
                    continue
                d = e.pos.distance_to(pos)
                if d < bd:
                    best, bd = e, d
        return best

    def spawn_fruit(self, pos):
        self.pickups.append(Fruit(pos + vfrom_angle(random.uniform(0, 360), 20)))

    def spawn_enemy(self, e):
        """Queue an enemy to join next drain -- safe to call while iterating
        ``self.enemies`` (a dying DIVISOR splitting inside _collisions)."""
        self.pending_enemies.append(e)

    def spawn_projectile(self, proj, mirror=True):
        self.projectiles.append(proj)
        # Retaguarda mirrors every friendly shot backwards. It lives HERE because
        # this is the single choke point every weapon already goes through --
        # implementing it per-weapon would be eight copies of one rule.
        if not (mirror and not proj.hostile):
            return
        if not any(getattr(p, 'amount_back', False) for p in self.players if not p.dead):
            return
        back = copy.copy(proj)
        back.vel = -Vector2(proj.vel)
        back.pos = Vector2(proj.pos)
        back.trail = []
        self.spawn_projectile(back, mirror=False)      # mirror=False: no recursion

    def spawn_puddle(self, puddle):
        if len(self.puddles) < 40:
            self.puddles.append(puddle)

    def _update_projectiles(self, dt):
        for pr in self.projectiles:
            if pr.homing and not pr.hostile:      # seek the nearest enemy
                tgt = self.nearest_enemy(pr.pos, 520)
                if tgt:
                    speed = pr.vel.length()
                    desired = safe_norm(tgt.pos - pr.pos)
                    pr.vel = safe_norm(safe_norm(pr.vel).lerp(desired, min(1, 7 * dt))) * speed
            pr.update(dt)
            if pr.dead:
                continue
            if pr.hostile:
                for p in self.players:
                    if p.dead or p.down:
                        continue
                    if p.pos.distance_to(pr.pos) < p.max_r + pr.radius:
                        if pr.effect == 'slow':
                            p.apply_slow(0.5, 1.6)
                        if pr.dmg > 0:
                            p.hurt(self, safe_norm(pr.vel), pr.dmg)
                        self.fx.burst(pr.pos, pr.color, 8, 160)
                        self.fx.spark_burst(pr.pos, palette.lighten(pr.color, 0.3), 6, 200)
                        pr.dead = True
                        break
            else:
                for e in self.enemies:
                    if e.dead:
                        continue
                    if pr.pierce and pr._pierced is not None and e in pr._pierced:
                        continue                # piercing shot already went through
                    where = e.hit_test(pr.pos, pr.radius)
                    if where:
                        dmg = pr.dmg
                        if where == 'head':
                            dmg = int(round(dmg * C.CRIT_MULT))
                            self.crit_fx(e.spine.joints[0])
                        e.take_hit(self, safe_norm(pr.vel), dmg)
                        if pr.effect == 'poison':
                            e.apply_poison(3.0, 3.0)
                        elif pr.effect == 'slow':
                            e.apply_slow(0.5, 1.6)
                        if pr.pierce:           # pass through, remember this enemy
                            if pr._pierced is None:
                                pr._pierced = set()
                            pr._pierced.add(e)
                        else:
                            pr.dead = True
                            break
                if not pr.dead:                     # player shots also chip nests
                    for n in self.rounds.nests:
                        if not n.dead and n.pos.distance_to(pr.pos) < n.max_r + pr.radius:
                            n.take_hit(self, pr.dmg)
                            pr.dead = True
                            break
        # Payload projectiles leave their puddle wherever they ended, and a shot
        # can die on four different paths above (expiry, out of bounds, hitting a
        # player, hitting a nest). Doing this in one sweep instead of at each
        # `pr.dead = True` means a new death path can never silently skip it.
        for pr in self.projectiles:
            if pr.dead and pr.puddle:
                self.spawn_puddle(weapons.Puddle(pr.pos, hostile=True, **pr.puddle))
                pr.puddle = None
        self.projectiles = [p for p in self.projectiles if not p.dead]

    # ---- eating / growth ------------------------------------------------ #
    def eat(self, player, target):
        target.dead = True
        audio.play('eat', 0.7)
        color = getattr(target, 'color', C.COL_BUG)
        self.fx.burst(target.pos, color, 16, 220)
        self.fx.spark_burst(target.pos, color, 10, 300)
        self.fx.ring(target.pos, color)
        kind = getattr(target, 'kind', 'bug')
        if kind == 'bug':
            player.energy = clamp(player.energy + 8, 0, player.max_energy)
            player.food += 1
            self.add_score(5)
            self.fx.popup(target.pos, "+5")
        elif kind == 'fruit':
            player.energy = clamp(player.energy + 22, 0, player.max_energy)
            player.health = min(player.max_health, player.health + 12)
            player.food += 1
            self.add_score(10)
            self.fx.popup(target.pos, "+cura", (120, 240, 120))
        elif kind == 'egg':
            f = AILizard(target.pos, 'friend', 0.9, C.COL_FRIEND)
            f.hp = C.FRIEND_HP
            f.sync_max_hp()
            f.life = C.FRIEND_LIFE
            self.friends.append(f)
            self.add_score(20)
            self.fx.popup(target.pos, "AMIGO!", C.COL_FRIEND)
        elif kind == 'prey':
            player.energy = clamp(player.energy + 30, 0, player.max_energy)
            player.food += 2
            sv = getattr(target, 'score_value', 25)
            self.add_score(sv)
            player.gain_xp(getattr(target, 'xp_value', 6), self)
            # eating a trait-carrier grants its body part (comer-para-evoluir)
            if getattr(target, 'grants', None):
                player.grant_part(target.grants, self)
            self.fx.popup(target.pos, f"+{sv}")
        if player.food and player.food % 4 == 0:
            self._grow(player)

    def _grow(self, player):
        sp = player.spine
        if len(sp.joints) < 22:
            sp.joints.append(Vector2(sp.joints[-1]))
            sp.radii = build_radii(len(sp.joints), player.max_r)
        self.fx.ring(player.pos, player.color)

    # ---- main step ------------------------------------------------------ #
    def step(self, dt):
        if self.state == 'camp':
            self._step_camp(dt)
            return
        if self.state != 'play':
            # the UI screens have their own clock so the entry animation runs on
            # the same fixed timestep as everything else (FPS-independent)
            self.ui_t += dt
            self.ui_fx = decay(self.ui_fx, dt)
            if self.pick:
                self._step_pick(dt)
            self.fx.update(dt)
            return
        # a queued level-up pauses the action for a card pick
        for p in self.players:
            if not p.dead and p.pending_levelups > 0:
                self._enter_levelup(p)
                return
        self.time += dt
        for p in self.players:
            if not p.dead:
                p.update(dt, self)
        for group in (self.enemies, self.prey, self.friends):
            for e in group:
                if not e.dead:
                    e.on_screen = self.cam.visible(e.pos)
                    e.update(dt, self)
        for pk in self.pickups:
            if not pk.dead:
                pk.update(dt, self)
        self._update_projectiles(dt)
        for pud in self.puddles:
            pud.update(dt, self)
        self.puddles = [p for p in self.puddles if not p.dead]

        # keep creatures from stacking into one point
        movers = [p for p in self.players if not p.dead]
        movers += [e for e in self.enemies if not e.dead]
        movers += [e for e in self.prey if not e.dead]
        movers += [f for f in self.friends if not f.dead]
        separate(movers)

        self._collisions()
        self.rounds.update(dt)
        if self.rounds.state == 'cleared':
            if getattr(self.rounds, 'is_final', False):
                self.state = 'victory'              # final boss down -> run won
                audio.play('victory')
                self._bank_run(won=True)
            else:
                self._enter_camp()                  # otherwise: camp (route + shop)
        self.fx.update(dt)
        self.flash = decay(self.flash, dt, 3.2)
        self.world.update(dt)
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0
        self.combo_flash = decay(self.combo_flash, dt, 2)
        self._revive()

        if self.pending_enemies:        # children queued during this step's deaths
            self.enemies.extend(self.pending_enemies)
            self.pending_enemies = []
        self.enemies = [e for e in self.enemies if not e.dead]
        self.prey = [e for e in self.prey if not e.dead]
        self.friends = [f for f in self.friends if not f.dead]
        self.pickups = [p for p in self.pickups if not p.dead]

        if len(self.pickups) < 50 and random.random() < dt * 4:
            self.pickups.append(Bug(self._rand_world()))
        if len(self.prey) < 8 and random.random() < dt * 0.6:
            self.prey.append(self._spawn_prey())

        if not self.alive_players():
            self.state = 'over'
            self._bank_run()

    def _bank_run(self, won=False):
        """Convert the finished run into permanent DNA (once)."""
        if self.run_banked:
            return
        self.run_banked = True
        self.won = won
        self.dna_gained = progression.finish_run(self.meta, self.score,
                                                 self.rounds.wave, self.kills, won=won)

    def _revive(self):
        for p in self.players:
            if p.down and not p.dead:
                for q in self.alive_players():
                    if not q.down and q.pos.distance_to(p.pos) < 70:
                        p.down = False
                        p.health = p.max_health * 0.5
                        p.hit_flash = 1.0
                        self.fx.burst(p.pos, C.COL_WHITE, 20, 220)
                        self.fx.popup(p.pos, "REVIVIDO!", C.COL_WHITE)

    def _collisions(self):
        for p in self.players:
            if p.dead or p.down:
                continue
            eat_r = p.max_r * 1.4
            head = p.spine.joints[0]
            for group in (self.pickups, self.prey):
                for e in group:
                    if e.dead:
                        continue
                    er = getattr(e, 'max_r', getattr(e, 'r', 6))
                    if head.distance_to(e.pos) < eat_r + er:
                        self.eat(p, e)
            for e in self.enemies:
                if e.dead:
                    continue
                # one hit per enemy per dash: _collisions runs every frame, so
                # without dash_hits a single 0.16s dash landed ~10 hits (30 dmg)
                if not p.dashing or e in p.dash_hits:
                    continue
                where = e.hit_test(p.pos, p.max_r)
                if where:
                    p.dash_hits.add(e)
                    grant = getattr(e, 'grants', None)
                    if p.venom:
                        e.apply_poison(2.5, 2.5)
                    dmg = p.dash_damage()
                    if where == 'head':                 # weak point
                        dmg *= C.CRIT_MULT
                        self.crit_fx(e.spine.joints[0])
                    e.take_hit(self, safe_norm(e.pos - p.pos), int(round(dmg)))
                    # Marked AFTER the dash's own hit: marking first meant the
                    # dash spent the crit it had just created, so the item did
                    # nothing the player could ever observe.
                    if p.dash_marks and not e.dead:
                        e.marked = True
                    if e.dead:
                        self.punch(0.07, 8)          # dash-kill: crunchy freeze
                        # stealing a body part is now a rare treat, not every kill
                        if grant and random.random() < 0.12:
                            p.grant_part(grant, self)
                        # Ricochete turns the chain into a full refresh
                        p.dash_cd = 0.0 if p.dash_chain_bonus else p.dash_cd * 0.35
                        p.energy = min(p.max_energy, p.energy + 6)
                    self.shake(6)
            # dashing through a nest damages it
            if p.dashing:
                for n in self.rounds.nests:
                    if n.dead or n in p.dash_hits:
                        continue
                    if p.pos.distance_to(n.pos) < p.max_r + n.max_r:
                        p.dash_hits.add(n)
                        # a nest is a big stationary target: a full body slam lands
                        n.take_hit(self, int(round(p.dash_damage() * 2)))
                        self.shake(5)

    # ---- draw ----------------------------------------------------------- #
    def draw(self, surf):
        self._draw_bg(surf)
        self.world.draw_decor(surf, self.cam)
        for pud in self.puddles:                    # acid pools sit on the ground
            if self.cam.visible(pud.pos, 60):
                pud.draw(surf, self.cam)
        self.rounds.draw_world(surf, self.cam)
        if self.state == 'camp' and self.camp:
            self._draw_camp_pois(surf)          # tent + doors, in world space
        for group in (self.pickups, self.prey, self.friends, self.enemies, self.players):
            for e in group:
                if getattr(e, 'dead', False):
                    continue
                pos = e.spine.joints[0] if hasattr(e, 'spine') else e.pos
                if not self.cam.visible(pos):
                    continue
                r = getattr(e, 'max_r', getattr(e, 'r', 6))
                sp = self.cam.w2s(pos + Vector2(0, r * 0.7))
                shadow(surf, sp, r * 1.1 * self.cam.zoom)
        for pk in self.pickups:
            if not pk.dead and self.cam.visible(pk.pos):
                pk.draw(surf, self.cam)
        for group in (self.prey, self.friends, self.enemies):
            for e in group:
                if not e.dead and self.cam.visible(e.pos, 120):
                    e.draw(surf, self.cam)
        for p in self.players:
            if not p.dead:
                p.draw(surf, self.cam)
        for pr in self.projectiles:
            if self.cam.visible(pr.pos, 40):
                pr.draw(surf, self.cam)
        self.world.draw_ambient(surf, self.cam)
        self.fx.draw(surf, self.cam, self.font)
        if self.flash > 0:
            ui._tint(surf, (255, 255, 255), int(150 * min(1.0, self.flash)))
        _vignette(surf)
        if self.state == 'play':
            self._draw_offscreen(surf)
        # The top-centre column is shared and elements reserve their band in draw
        # order, so draw order == priority. Persistent readouts (HUD, boss bar)
        # claim their spot first and never move; the theme banner is a 2.2s
        # announcement and goes last, so it can no longer shove the boss bar down
        # into the play area for the exact seconds the boss is spawning.
        # 'levelup'/'camp' own the whole screen and have their own headers; the
        # HUD behind them was pure clutter competing with the panels.
        self.top.reset()
        if self.state not in ('victory', 'over', 'levelup', 'camp'):
            self._draw_hud(surf)
            self.rounds.draw_boss_bar(surf, self.font, self.bigfont)
            self.rounds.draw_banner(surf, self.font, self.bigfont)
        else:
            self.rounds.draw_boss_bar(surf, self.font, self.bigfont)
        if self.state == 'pause':
            self._draw_pause(surf)
        elif self.state == 'levelup':
            self._draw_levelup(surf)
        elif self.state == 'camp':
            if self.camp and self.camp.get('mode') == 'shop':
                self._draw_camp(surf)           # the tent's shop/charm menu
            else:
                self._draw_camp_field_ui(surf)  # walking the clearing
        elif self.state == 'victory':
            self._draw_victory(surf)
        elif self.state == 'over':
            self._draw_over(surf)

    def _draw_bg(self, surf):
        surf.fill(C.COL_BG)
        self.world.draw_ground(surf, self.cam)
        z = self.cam.zoom
        tl = self.cam.w2s((0, 0)); br = self.cam.w2s((C.WORLD_W, C.WORLD_H))
        pygame.draw.rect(surf, (58, 54, 96), (tl[0], tl[1], br[0] - tl[0], br[1] - tl[1]),
                         max(2, int(6 * z)))

    def _draw_hud(self, surf):
        bw = 216
        for i, p in enumerate(self.players):
            x = 16 if i == 0 else C.WIDTH - bw - 16
            y = 14
            col = p.colorset[0]
            ui.text(surf, self.font, f"P{i+1}", (x, y), col)
            ui.text(surf, self.font, f"Nv {p.level}", (x + bw, y), (226, 228, 244),
                    align='right')

            # health: the big organic sac, with swaying flagella
            hy = y + 26
            hr = clamp(p.health / p.max_health, 0, 1)
            _bio_bar(surf, x, hy, bw, 16, hr, palette.health_color(hr), self.time,
                     flagella=3, glow=True)
            # light glyphs + dark rim, not dark-on-bar: the fill shifts green ->
            # orange -> red under it, and dark ink lost contrast on every shade.
            ui.text(surf, self.font, f"{int(p.health)}/{int(p.max_health)}",
                    (x + bw // 2, hy), (255, 255, 255), align='center')

            # energy + xp: slim sacs (no flagella -- too short to read)
            ey = hy + 22
            _bio_bar(surf, x, ey, bw, 8, p.energy / p.max_energy, (96, 206, 240),
                     self.time)
            xy = ey + 12
            _bio_bar(surf, x, xy, bw, 6, clamp(p.xp / p.xp_to_next, 0, 1),
                     (245, 205, 84), self.time + 1.7)
            # ability cooldown dials (dash / tongue) -> readable "can I act?" feedback
            dy = xy + 16
            # three dials in a 216px panel: 78px pitch overflowed, so 11px radius
            # on a 68px pitch, with short labels
            dash_frac = 1.0 - clamp(p.dash_cd / max(0.001, p.dash_cooldown), 0, 1)
            _dial(surf, (x + 12, dy + 14), 11, dash_frac, p.colorset[0],
                  self.smallfont, "DASH", self.time, enabled=p.energy >= C.DASH_COST)
            t_frac = 0.0 if p.tongue_t > 0 else 1.0
            _dial(surf, (x + 80, dy + 14), 11, t_frac, (235, 90, 120),
                  self.smallfont, "LING", self.time, enabled=p.energy >= C.TONGUE_COST)
            w_frac = 1.0 - clamp(p.whip_cd / max(0.001, p.whip_cooldown), 0, 1)
            _dial(surf, (x + 148, dy + 14), 11, w_frac, (250, 190, 90),
                  self.smallfont, "RABO", self.time, enabled=p.energy >= C.WHIP_COST)

            if p.down:
                ui.text(surf, self.font, f"CAIDO {p.revive:0.0f}s - toque p/ reviver",
                        (x, dy + 34), C.COL_ENEMY)
            # Active item: its own corner, not a fourth cooldown dial (the dial
            # row is a 216px panel at 68px pitch -- a fourth lands outside it).
            # Top-right when it is free; in co-op that corner IS P2's panel, so
            # each player gets it under their own dials instead.
            if p.ability:
                from . import items as itemlib
                it = itemlib.BY_ID.get(p.ability)
                if it is not None:
                    if len(self.players) == 1:
                        ix, iy = C.WIDTH - 52, 46
                    else:
                        ix = (x + 20) if i == 0 else (x + bw - 20)
                        iy = dy + 62
                    full = p.ability_charge >= 1.0
                    col = it.color if full else (96, 100, 128)
                    if full:
                        pulse = 0.5 + 0.5 * math.sin(self.time * 6)
                        palette.glow(surf, (ix, iy), 30, it.color, 0.28 + 0.2 * pulse)
                    icons.draw(surf, it.icon, (ix, iy), 13, col, glow=False)
                    pygame.draw.circle(surf, (36, 40, 58), (ix, iy), 18, 3)
                    if p.ability_charge > 0:
                        pygame.draw.arc(surf, col, (ix - 18, iy - 18, 36, 36),
                                        math.pi / 2,
                                        math.pi / 2 + p.ability_charge * C.TAU, 3)
                    lbl = "E" if i == 0 else "U"
                    if len(self.players) == 1:
                        ui.text(surf, self.smallfont, lbl, (ix, iy + 24), col,
                                align='center')
                        ui.text(surf, self.smallfont, it.name, (ix - 26, iy - 7),
                                col, align='right')
                    else:
                        ui.text(surf, self.smallfont, lbl, (ix + 22, iy - 8), col)

            # equipped weapons live in the bottom corners so they never collide
            # with the health/energy bars or the cooldown dials
            wy = C.HEIGHT - 34
            for wi, (wid, lvl) in enumerate(p.weapons.items()):
                w = weapons.WEAPONS[wid]
                cxw = (x + 18 + wi * 46) if i == 0 else (x + bw - 18 - wi * 46)
                c = (cxw, wy)
                icons.draw(surf, wid, c, 14, w.color)
                lp = (c[0] + 13, c[1] + 11)
                pygame.draw.circle(surf, C.COL_INK, lp, 9)
                pygame.draw.circle(surf, w.color, lp, 9, 1)
                lh = self.font.get_height()
                ui.text(surf, self.font, str(lvl), (lp[0], lp[1] - lh // 2),
                        C.COL_WHITE, align='center')

        # ---- top-centre column: every element reserves its own band ---- #
        cx = C.WIDTH // 2
        y = self.top.take(self.bigfont.get_height())
        ui.text(surf, self.bigfont, str(self.score), (cx, y), C.COL_HUD, align='center')

        y = self.top.take(self.font.get_height())
        ui.text(surf, self.font,
                f"Onda {self.wave}   Amigos {len(self.friends)}   Abates {self.kills}",
                (cx, y), (214, 217, 238), align='center')

        # combo / streak meter (rewards staying aggressive)
        if self.combo >= 2:
            heat = min(1.0, self.combo / 25.0)
            col = palette.mix((255, 214, 90), (255, 86, 86), heat)
            # composed first: the flash scales the *outlined* image, and the band
            # it reserves has to be the scaled height or the banner lands on it
            img = ui.text_surface(self.bigfont, f"x{self.combo}  COMBO", col)
            sc = 1.0 + self.combo_flash * 0.25
            if sc > 1.01:
                img = pygame.transform.rotozoom(img, 0, sc)
            cbar = 150                      # NB: not `bw`, which is the player panel
            y = self.top.take(img.get_height() + 9)
            surf.blit(img, (cx - img.get_width() // 2, y))
            by = y + img.get_height() + 2
            f = clamp(self.combo_timer / 3.2, 0, 1)
            pygame.draw.rect(surf, (50, 46, 60), (cx - cbar // 2, by, cbar, 5),
                             border_radius=3)
            pygame.draw.rect(surf, col, (cx - cbar // 2, by, int(cbar * f), 5),
                             border_radius=3)

    # ---- UI screen compositing ------------------------------------------ #
    def _layer(self):
        """Scratch full-screen surface: the UI is drawn here, then blitted with the
        shake offset, so a `punch()` kicks the *whole screen* -- the world behind
        is frozen on these screens, so shaking the camera alone reads as nothing."""
        if self._uilayer is None:
            self._uilayer = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        self._uilayer.fill((0, 0, 0, 0))
        return self._uilayer

    def _ui_fx(self, layer):
        """Particles are drawn with the world, i.e. *under* the veil, which mutes
        them ~80%. Around a choice, redraw them on top of the panels so the trail
        and the impact burst actually read."""
        if self.pick or self.ui_fx > 0:
            self.fx.draw(layer, self.cam, self.font)

    def _ui_dest(self, surf):
        """Where the screen's content should be drawn.

        Compositing through the scratch layer costs a full-screen per-pixel-alpha
        blit (~4 ms), so only pay it while a shake is actually displacing the UI;
        the rest of the time draw straight to the screen.
        """
        if abs(self.cam.shake_off.x) < 0.5 and abs(self.cam.shake_off.y) < 0.5:
            return surf
        return self._layer()

    def _blit_ui(self, surf, layer):
        if layer is not surf:
            surf.blit(layer, (int(self.cam.shake_off.x), int(self.cam.shake_off.y)))

    @staticmethod
    def _blit_card(dst, src, center, scale=1.0, alpha=1.0):
        """Blit a pre-rendered panel centred, scaled and faded (used by the entry
        animation and by the absorption)."""
        if alpha <= 0.01:
            return
        w = max(1, int(src.get_width() * scale))
        h = max(1, int(src.get_height() * scale))
        im = src if (w, h) == src.get_size() else pygame.transform.smoothscale(src, (w, h))
        if alpha < 1.0:
            im = im.copy()
            im.set_alpha(int(255 * alpha))
        dst.blit(im, (int(center[0] - w / 2), int(center[1] - h / 2)))

    def _panel(self, key, build):
        """Panels are redrawn only when their state changes -- rebuilding three
        text-heavy cards every frame cost ~8 ms on the paused screens."""
        s = self._panels.get(key)
        if s is None:
            s = self._panels[key] = build()
        return s

    def _veil(self, surf, color, target_alpha):
        """Background dim that fades in first -- phase 1 of every screen."""
        # plain surface + set_alpha, NOT an SRCALPHA fill: the per-pixel-alpha
        # full-screen blit was costing ~8 ms a frame on these screens
        f = clamp(self.ui_t / C.UI_VEIL, 0, 1)
        ui._tint(surf, color, int(target_alpha * f))
        return f

    def _card_surface(self, card, i, sel):
        """One level-up card, drawn at the origin so it can be moved/scaled freely."""
        cw, ch = 240, 300
        s = pygame.Surface((cw, ch), pygame.SRCALPHA)
        box = pygame.Rect(0, 0, cw, ch)
        pygame.draw.rect(s, (30, 32, 52), box, border_radius=16)
        edge = card.color if sel else (70, 72, 96)
        pygame.draw.rect(s, edge, box, 4 if sel else 2, border_radius=16)
        icons.draw(s, getattr(card, 'icon', None), (cw // 2, 70), 30, card.color)
        name = self.bigfont.render(card.name, True, C.COL_WHITE)
        if name.get_width() > cw - 20:
            name = self.font.render(card.name, True, C.COL_WHITE)
        s.blit(name, (cw // 2 - name.get_width() // 2, 130))
        for li, line in enumerate(ui.wrap(self.font, card.desc, cw - 30)):
            im = self.font.render(line, True, (200, 200, 216))
            s.blit(im, (cw // 2 - im.get_width() // 2, 180 + li * 24))
        key = self.font.render(f"[{i + 1}]", True, card.color)
        s.blit(key, (cw // 2 - key.get_width() // 2, ch - 34))
        return s

    def _draw_levelup(self, surf):
        f = self._veil(surf, (8, 10, 20), 200)
        layer = self._ui_dest(surf)
        # heading rides in with the veil, before the cards
        toff, talpha = ui.drop_in(self.ui_t, 0, 0.0, C.UI_VEIL, rise=22.0)
        if talpha > 0.01:
            title = self.bigfont.render("EVOLUIR", True, C.COL_WHITE)
            hint = "escolha uma mutacao  -  1/2/3, setas+ENTER ou clique"
            p = self.levelup_player
            if p is not None and p.rerolls > 0:
                hint += f"   [R] rerrolar ({p.rerolls})"
            sub = self.font.render(hint, True, (190, 190, 210))
            for im, ty in ((title, 96), (sub, 140)):
                im = im.copy()
                im.set_alpha(int(255 * talpha))
                layer.blit(im, (C.WIDTH // 2 - im.get_width() // 2, int(ty + toff)))

        n = len(self.cards)
        cw, ch, gap = 240, 300, 34
        total = n * cw + (n - 1) * gap
        x0 = C.WIDTH // 2 - total // 2
        y = C.HEIGHT // 2 - ch // 2 + 20
        self._card_rects = []
        chosen = self.pick if (self.pick and self.pick['kind'] == 'card') else None
        for i, card in enumerate(self.cards):
            rect = pygame.Rect(x0 + i * (cw + gap), y, cw, ch)
            self._card_rects.append(rect)
            sel = (i == self.card_idx) or (chosen is not None and chosen['index'] == i)
            src = self._panel(('card', i, sel), lambda c=card, i=i, s=sel:
                              self._card_surface(c, i, s))
            if chosen is None:
                off, alpha = ui.drop_in(self.ui_t, i, C.UI_STAGGER, C.UI_DROP, rise=46.0)
                self._blit_card(layer, src, (rect.centerx, rect.centery + off),
                                1.0, alpha)
            elif chosen['index'] != i:
                # the ones you didn't take shrink away
                g = clamp(chosen['t'] / 0.18, 0, 1)
                self._blit_card(layer, src, rect.center, 1.0 - 0.25 * g, 1.0 - g)
        if chosen is not None:
            pos, scale, alpha = self._pick_pose()
            ci = chosen['index']
            src = self._panel(('card', ci, True),
                              lambda: self._card_surface(self.cards[ci], ci, True))
            palette.glow(layer, (int(pos.x), int(pos.y)), int(120 * scale + 30),
                         chosen['color'], 0.30 + 0.30 * (1 - alpha))
            self._blit_card(layer, src, pos, scale, alpha)
        self._ui_fx(layer)
        self._blit_ui(surf, layer)
        return f

    def _draw_offscreen(self, surf):
        """Edge arrows pointing at enemies (and nests) you can't see -> find stragglers."""
        cx, cy = C.WIDTH / 2, C.HEIGHT / 2
        hw, hh = cx - 28, cy - 28
        shown = 0
        targets = [(e, e.color) for e in self.enemies if not e.dead]
        targets += [(n, (190, 130, 95)) for n in self.rounds.nests if not n.dead]
        for obj, col in targets:
            sp = self.cam.w2s(obj.pos)
            if -12 < sp[0] < C.WIDTH + 12 and -12 < sp[1] < C.HEIGHT + 12:
                continue
            d = Vector2(sp[0] - cx, sp[1] - cy)
            if d.length_squared() < 1:
                continue
            scale = min(hw / abs(d.x) if d.x else 1e9, hh / abs(d.y) if d.y else 1e9)
            c = Vector2(cx, cy) + d * scale
            ang = d.as_polar()[1]
            tip = c + vfrom_angle(ang, 12)
            b1 = c + vfrom_angle(ang + 138, 10)
            b2 = c + vfrom_angle(ang - 138, 10)
            palette.glow(surf, (int(c.x), int(c.y)), 16, col, 0.5)
            pygame.draw.polygon(surf, col, [tip, b1, b2])
            pygame.draw.polygon(surf, C.COL_INK, [tip, b1, b2], 1)
            shown += 1
            if shown >= 22:
                break

    def _shop_surface(self, it, i, focused):
        """One beetle-shop item, drawn at the origin (see _card_surface)."""
        cw, chh = 176, 132
        s = pygame.Surface((cw, chh), pygame.SRCALPHA)
        box = pygame.Rect(0, 0, cw, chh)
        afford = self.pollen >= it['cost']
        pygame.draw.rect(s, (34, 38, 56) if focused else (28, 32, 46), box, border_radius=12)
        edge = palette.vibrant(it['hue'], 0.8, 1.0) if afford else (70, 72, 92)
        if focused:
            edge = C.COL_WHITE
        pygame.draw.rect(s, edge, box, 4 if focused else (3 if afford else 2),
                         border_radius=12)
        icons.draw(s, it.get('icon'), (cw // 2, 34), 19, palette.vibrant(it['hue'], 0.8, 1.0))
        nm = self.font.render(ui.fit(self.font, it['name'], cw - 16), True, C.COL_WHITE)
        s.blit(nm, (cw // 2 - nm.get_width() // 2, 62))
        ds = self.font.render(ui.fit(self.font, it['desc'], cw - 16), True, (190, 190, 210))
        s.blit(ds, (cw // 2 - ds.get_width() // 2, 84))
        cc = C.COL_POLLEN if afford else (150, 120, 60)
        cost = self.font.render(f"{it['cost']}  polen", True, cc)
        s.blit(cost, (cw // 2 - cost.get_width() // 2, 106))
        s.blit(self.font.render(f"[{i + 1}]", True, edge), (8, 6))
        return s

    def _route_surface(self, r, sel, focused):
        rw, rh = 250, 140
        s = pygame.Surface((rw, rh), pygame.SRCALPHA)
        box = pygame.Rect(0, 0, rw, rh)
        bonus_txt = {'cura': 'entra com vida cheia', 'polen': '+25 polen',
                     'carta': 'carta de evolucao'}
        bonus_col = {'cura': (120, 240, 140), 'polen': C.COL_POLLEN,
                     'carta': (150, 130, 245)}
        pygame.draw.rect(s, (28, 32, 50) if focused else (24, 28, 42), box, border_radius=14)
        pygame.draw.rect(s, C.COL_ENEMY if sel else (70, 72, 92), box,
                         4 if focused else (3 if sel else 2), border_radius=14)
        lbl = self.bigfont.render(r['label'], True, C.COL_ENEMY)
        if lbl.get_width() > rw - 16:
            lbl = self.font.render(r['label'], True, C.COL_ENEMY)
        s.blit(lbl, (rw // 2 - lbl.get_width() // 2, 26))
        s.blit(self.font.render("proxima onda", True, (180, 180, 200)), (rw // 2 - 46, 74))
        bt = self.font.render(bonus_txt[r['bonus']], True, bonus_col[r['bonus']])
        s.blit(bt, (rw // 2 - bt.get_width() // 2, 104))
        return s

    # ---- pause ---------------------------------------------------------- #
    PAUSE_ITEMS = ('CONTINUAR', 'OPCOES', 'CONTROLES', 'SAIR PARA O MENU')

    def toggle_pause(self):
        """ESC. Pausing is just another non-'play' state, so game.step already
        freezes the whole simulation for us -- the run is never destroyed."""
        if self.state == 'pause':
            self.state = self.pause_prev
            self.ui_t = 99.0            # returning: don't replay the entry animation
            return False
        if self.state not in ('play', 'camp', 'levelup') or self.pick:
            return False                # not during an absorption or a run-over screen
        self.pause_prev = self.state
        self.state = 'pause'
        self.pause_mode = 'menu'
        self.pause_sel = 0
        self.ui_t = 0.0
        audio.play('ui')
        return True

    def pause_items(self, joysticks=None):
        from . import menu as menulib
        if self.pause_mode == 'options':
            return menulib._items_for('options', None, 0, None)
        if self.pause_mode == 'controls':
            return ['VOLTAR']
        return list(self.PAUSE_ITEMS)

    def pause_move(self, d):
        n = len(self.pause_items())
        self.pause_sel = (self.pause_sel + d) % max(1, n)

    def pause_back(self):
        """B / ESC inside a sub-screen: step back one level instead of resuming."""
        if self.pause_mode != 'menu':
            self.pause_mode = 'menu'
            self.pause_sel = 0
            self.ui_t = 0.0
            return True
        return False

    def pause_activate(self, toggle_fs):
        """Returns 'resume', 'quit' or None. Options reuse the menu's own actions."""
        from . import menu as menulib
        items = self.pause_items()
        sel = min(self.pause_sel, len(items) - 1)
        if self.pause_mode == 'controls':
            self.pause_back()
            return None
        if self.pause_mode == 'options':
            # same handler the main menu uses -> identical behaviour + persistence
            r = menulib._activate('options', sel, toggle_fs, len(items))
            if r is not None:                 # 'VOLTAR'
                self.pause_back()
            return None
        audio.play('ui')
        if sel == 0:
            self.toggle_pause()
            return 'resume'
        if sel == 1:
            self.pause_mode = 'options'
        elif sel == 2:
            self.pause_mode = 'controls'
        else:
            return 'quit'
        self.pause_sel = 0
        self.ui_t = 0.0
        return None

    def _draw_pause(self, surf, joysticks=None):
        from . import menu as menulib
        self._veil(surf, (8, 10, 20), 200)
        cx = C.WIDTH // 2
        toff, talpha = ui.drop_in(self.ui_t, 0, 0.0, C.UI_VEIL, rise=22.0)
        if talpha > 0.01:
            title = self.bigfont.render("PAUSADO", True, C.COL_WHITE)
            im = title.copy()
            im.set_alpha(int(255 * talpha))
            surf.blit(im, (cx - im.get_width() // 2, int(120 + toff)))

        items = self.pause_items(joysticks)
        if self.pause_mode == 'controls':
            lines = menulib.controls_lines(joysticks)
            for i, line in enumerate(lines):
                off, alpha = ui.drop_in(self.ui_t, 1 + i * 0.25, C.UI_STAGGER,
                                        C.UI_DROP, rise=30.0)
                if alpha <= 0.01 or not line:
                    continue
                im = self.font.render(line, True, (206, 208, 226))
                if alpha < 1.0:
                    im = im.copy()
                    im.set_alpha(int(255 * alpha))
                surf.blit(im, (cx - im.get_width() // 2, int(200 + i * 30 + off)))
            top = 200 + len(lines) * 30 + 16
        else:
            top = 210

        self._pause_rects = []
        for i, label in enumerate(items):
            off, alpha = ui.drop_in(self.ui_t, 1 + i * 0.5, C.UI_STAGGER, C.UI_DROP,
                                    rise=34.0)
            rect = pygame.Rect(cx - 210, top + i * 46, 420, 40)
            self._pause_rects.append(rect)
            if alpha <= 0.01:
                continue
            sel = (i == min(self.pause_sel, len(items) - 1))
            y = rect.y + off
            if sel:
                palette.glow(surf, (rect.centerx, int(y + 20)), 180,
                             C.COL_PLAYER[0], 0.22 * alpha)
                box = pygame.Rect(rect.x, int(y), rect.width, rect.height)
                pygame.draw.rect(surf, (26, 30, 46), box, border_radius=12)
                pygame.draw.rect(surf, C.COL_PLAYER[0], box, 3, border_radius=12)
            im = self.font.render(label, True, C.COL_WHITE if sel else (158, 162, 190))
            if alpha < 1.0:
                im = im.copy()
                im.set_alpha(int(255 * alpha))
            surf.blit(im, (cx - im.get_width() // 2, int(y + 10)))

    def _label(self, layer, text, x, y, off, alpha, color=(200, 200, 220)):
        if alpha <= 0.01:
            return
        im = self.font.render(text, True, color)
        if alpha < 1.0:
            im = im.copy()
            im.set_alpha(int(255 * alpha))
        layer.blit(im, (int(x), int(y + off)))

    def _draw_camp(self, surf):
        self._veil(surf, (10, 14, 22), 205)
        layer = self._ui_dest(surf)   # a scratch layer only while shaking
        cx = C.WIDTH // 2
        bought = self.pick if (self.pick and self.pick['kind'] == 'shop') else None
        taken = self.pick if (self.pick and self.pick['kind'] == 'route') else None

        # ---- header + pollen purse (rides in with the veil) ---- #
        hoff, halpha = ui.drop_in(self.ui_t, 0, 0.0, C.UI_VEIL, rise=22.0)
        if halpha > 0.01:
            head = pygame.Surface((C.WIDTH, 130), pygame.SRCALPHA)
            t = self.bigfont.render("ACAMPAMENTO", True, C.COL_WHITE)
            head.blit(t, (cx - t.get_width() // 2, 40))
            pol = self.bigfont.render(str(self.pollen), True, C.COL_POLLEN)
            pygame.draw.circle(head, C.COL_POLLEN, (cx - 70, 96), 12)
            pygame.draw.circle(head, (200, 160, 40), (cx - 70, 96), 12, 2)
            head.blit(self.font.render("POLEN", True, (210, 210, 226)), (cx - 54, 88))
            head.blit(pol, (cx + 12, 78))
            if halpha < 1.0:
                head.set_alpha(int(255 * halpha))
            layer.blit(head, (0, int(hoff)))

        # ---- shop (beetle merchant) ---- #
        shop = self.camp['shop']
        cw, gap = 176, 14
        x0 = cx - (len(shop) * cw + (len(shop) - 1) * gap) // 2
        y = 164
        self._shop_rects = []
        soff, salpha = ui.drop_in(self.ui_t, 1, C.UI_STAGGER, C.UI_DROP, rise=40.0)
        self._label(layer, "LOJA DO BESOURO  (1-5 ou clique)", cx - 300, 138, soff, salpha)
        for i, it in enumerate(shop):
            rect = pygame.Rect(x0 + i * (cw + gap), y, cw, 132)
            self._shop_rects.append(rect)
            if bought is not None and bought['index'] == i:
                continue                      # drawn last, mid-absorption
            focused = (self.camp.get('focus') == 'shop' and self.camp.get('shop_sel') == i)
            off, alpha = ui.drop_in(self.ui_t, 1 + i * 0.4, C.UI_STAGGER, C.UI_DROP,
                                    rise=40.0)
            if bought is not None:            # the ones you passed on dim away
                alpha *= 1.0 - clamp(bought['t'] / 0.18, 0, 1) * 0.8
            if focused and alpha > 0.5:
                palette.glow(layer, (rect.centerx, int(rect.centery + off)), 90,
                             palette.vibrant(it['hue'], 0.8, 1.0), 0.3 * alpha)
            src = self._panel(('shop', i, focused, it['cost'], self.pollen >= it['cost']),
                              lambda it=it, i=i, f=focused: self._shop_surface(it, i, f))
            self._blit_card(layer, src, (rect.centerx, rect.centery + off), 1.0, alpha)
        if self.camp.get('msg') and bought is None and salpha > 0.9:
            m = self.font.render(f"comprado: {self.camp['msg']}", True, (120, 240, 140))
            layer.blit(m, (x0, y + 116))

        # ---- charms loadout ---- #
        p0 = self.players[0]
        coff, calpha = ui.drop_in(self.ui_t, 3, C.UI_STAGGER, C.UI_DROP, rise=40.0)
        self._charm_rects = []
        if calpha > 0.01:
            focus_ch = self.camp.get('focus') == 'charms'
            self._label(layer, "CHARMS  (setas/controle ou clique p/ equipar)",
                        cx - 300, 306, coff, calpha)
            block = pygame.Surface((C.WIDTH, 145), pygame.SRCALPHA)
            # One column per slot, owned charms listed under their own slot header:
            # makes it obvious what a charm replaces, and gives up/down + left/right
            # a real grid to walk (see app.py camp nav).
            sw = 168
            sx0 = cx - (len(C.CHARM_SLOTS) * sw + (len(C.CHARM_SLOTS) - 1) * 12) // 2
            for si, (slot, nm) in enumerate(C.CHARM_SLOTS):
                bx = sx0 + si * (sw + 12)
                box = pygame.Rect(bx, 0, sw, 32)          # block starts at y=328
                cid = p0.charm_slots.get(slot)
                col = charmlib.CHARMS[cid].color if cid else (62, 64, 88)
                pygame.draw.rect(block, (26, 30, 44), box, border_radius=10)
                pygame.draw.rect(block, col, box, 2, border_radius=10)
                lab = charmlib.CHARMS[cid].name if cid else '-'
                txt = ui.fit(self.font, f"{nm}: {lab}", box.width - 16)
                block.blit(self.font.render(txt, True, (218, 218, 232)), (bx + 8, 6))
                owned = [c for c in p0.charms_owned
                         if charmlib.CHARMS[c].slot == slot]
                for ri, ccid in enumerate(owned):
                    ch = charmlib.CHARMS[ccid]
                    rect = pygame.Rect(bx, 38 + ri * 25, sw, 24)
                    self._charm_rects.append((rect.move(0, 328), ccid))
                    equipped = (p0.charm_slots.get(slot) == ccid)
                    cur = (focus_ch and self.camp.get('charm_col') == si
                           and self.camp.get('charm_row') == ri)
                    pygame.draw.rect(block, (38, 44, 64) if cur else (30, 34, 50),
                                     rect, border_radius=7)
                    edge = C.COL_WHITE if cur else ch.color
                    pygame.draw.rect(block, edge, rect, 3 if (equipped or cur) else 1,
                                     border_radius=7)
                    icons.draw(block, ccid, (bx + 14, rect.centery), 8, ch.color, glow=False)
                    im = self.font.render(ui.fit(self.font, ch.name, sw - 40), True,
                                          (222, 222, 234))
                    block.blit(im, (bx + 26, rect.centery - im.get_height() // 2))
            if calpha < 1.0:
                block.set_alpha(int(255 * calpha))
            layer.blit(block, (0, int(328 + coff)))

        # Routes are now physical DOORS in the clearing -- no route panel here.
        self._route_rects = []
        eoff, ealpha = ui.drop_in(self.ui_t, 4, C.UI_STAGGER, C.UI_DROP, rise=40.0)
        if ealpha > 0.01:
            self._label(layer, "ESC / B: voltar a clareira  ->  atravesse uma porta p/ avancar",
                        cx - 300, 512, eoff, ealpha)

        # ---- the item being absorbed, on top of everything ---- #
        if bought is not None:
            pos, scale, alpha = self._pick_pose()
            it = shop[bought['index']]
            src = self._panel(('shop', bought['index'], True, it['cost'],
                               self.pollen >= it['cost']),
                              lambda: self._shop_surface(it, bought['index'], True))
            palette.glow(layer, (int(pos.x), int(pos.y)), int(100 * scale + 30),
                         bought['color'], 0.30 + 0.30 * (1 - alpha))
            self._blit_card(layer, src, pos, scale, alpha)
        self._ui_fx(layer)
        self._blit_ui(surf, layer)

    _DOOR_HUES = (150, 45, 285)          # green (cura) / gold (polen) / purple (carta)
    _BONUS_TAG = {'cura': '+ cura', 'polen': '+ polen', 'carta': '+ carta'}

    def _near_player(self, pos, r):
        return any(not p.dead and p.pos.distance_to(pos) < r for p in self.players)

    def _draw_camp_pois(self, surf):
        """The clearing's furniture, in world space: three route DOORS and the
        beetle's TENT. Both light up and prompt when a player is in reach."""
        cam, z, t = self.cam, self.cam.zoom, self.time
        # ---- doors (routes) ---- #
        for i, dr in enumerate(self.camp['doors']):
            pos = dr['pos']
            if not cam.visible(pos, 220):
                continue
            col = palette.vibrant(self._DOOR_HUES[i % 3], 0.7, 1.0)
            off = self._camp_drop_off(dr['delay'])       # falling in from the sky
            if off < -2:                                 # growing shadow marks the landing
                prog = 1.0 - min(1.0, -off / C.CAMP_DROP_H)
                shadow(surf, cam.w2s(pos), int(34 * z * (0.4 + 0.6 * prog)))
            sp = cam.w2s(pos + Vector2(0, off))
            hot = dr['landed'] and self._near_player(pos, C.CAMP_DOOR_R * 2.4)
            pulse = 0.5 + 0.5 * math.sin(t * 3 + i)
            w, h = int(66 * z), int(108 * z)
            rad = int(w * 0.5)
            palette.glow(surf, sp, int(w * (1.5 if hot else 1.05)), col,
                         (0.34 if hot else 0.2) + 0.12 * pulse)
            frame = pygame.Rect(sp[0] - w // 2, sp[1] - h, w, h)
            inner = frame.inflate(-int(14 * z), -int(12 * z))
            pygame.draw.rect(surf, (16, 18, 28), inner, border_top_left_radius=rad,
                             border_top_right_radius=rad)
            ew = max(2, int((5 if hot else 4) * z))
            pygame.draw.rect(surf, col, frame, ew, border_top_left_radius=rad,
                             border_top_right_radius=rad)
            pygame.draw.rect(surf, palette.lighten(col, 0.4), frame, max(1, int(2 * z)),
                             border_top_left_radius=rad, border_top_right_radius=rad)
            ui.text(surf, self.font, dr['route']['label'], (sp[0], frame.top - int(30 * z)),
                    C.COL_WHITE, align='center')
            ui.text(surf, self.font, self._BONUS_TAG[dr['route']['bonus']],
                    (sp[0], frame.top - int(13 * z)), palette.lighten(col, 0.35), align='center')
            if hot:
                ui.text(surf, self.font, 'ATRAVESSE', (sp[0], sp[1] + int(8 * z)),
                        C.COL_WHITE, align='center')
        # ---- tent (shop) ---- #
        pos = self.camp['tent']
        if cam.visible(pos, 260):
            off = self._camp_drop_off(self.camp['tent_delay'])
            if off < -2:
                prog = 1.0 - min(1.0, -off / C.CAMP_DROP_H)
                shadow(surf, cam.w2s(pos), int(64 * z * (0.4 + 0.6 * prog)))
            sp = cam.w2s(pos + Vector2(0, off))
            hot = self.camp['tent_landed'] and self._near_player(pos, C.CAMP_TENT_R)
            pulse = 0.5 + 0.5 * math.sin(t * 2.4)
            gold = C.COL_POLLEN
            w = int(120 * z)
            palette.glow(surf, sp, int(w * (0.95 if hot else 0.72)), gold,
                         (0.3 if hot else 0.17) + 0.1 * pulse)
            counter = pygame.Rect(sp[0] - w // 2, sp[1] - int(4 * z), w, int(34 * z))
            pygame.draw.rect(surf, (120, 82, 54), counter, border_radius=int(6 * z))
            pygame.draw.rect(surf, (60, 40, 26), counter, max(1, int(2 * z)),
                             border_radius=int(6 * z))
            roof_h = int(48 * z)
            base_y = sp[1] - int(4 * z)
            left = (sp[0] - w // 2 - int(8 * z), base_y)
            right = (sp[0] + w // 2 + int(8 * z), base_y)
            peak = (sp[0], base_y - roof_h)
            pygame.draw.polygon(surf, (214, 74, 78), [left, right, peak])
            pygame.draw.polygon(surf, C.COL_INK, [left, right, peak], max(1, int(2 * z)))
            # scalloped valance: little triangles hanging under the awning base
            n = 5
            for k in range(n):
                x0 = left[0] + (right[0] - left[0]) * k / n
                x1 = left[0] + (right[0] - left[0]) * (k + 1) / n
                tip = ((x0 + x1) / 2, base_y + int(9 * z))
                shade = (214, 74, 78) if k % 2 == 0 else (245, 232, 210)
                pygame.draw.polygon(surf, shade, [(x0, base_y), (x1, base_y), tip])
            pygame.draw.circle(surf, gold, (sp[0], peak[1] - int(9 * z)), max(2, int(7 * z)))
            pygame.draw.circle(surf, (200, 160, 40), (sp[0], peak[1] - int(9 * z)),
                               max(2, int(7 * z)), max(1, int(2 * z)))
            # the beetle merchant behind the counter
            bc = (sp[0] - int(w * 0.26), base_y + int(6 * z))
            pygame.draw.circle(surf, (74, 62, 88), bc, max(2, int(11 * z)))
            for s in (-1, 1):                       # antennae
                pygame.draw.line(surf, (74, 62, 88), (bc[0], bc[1] - int(8 * z)),
                                 (bc[0] + s * int(7 * z), bc[1] - int(16 * z)),
                                 max(1, int(2 * z)))
            ui.text(surf, self.font, 'LOJA DO BESOURO', (sp[0], counter.bottom + int(6 * z)),
                    gold, align='center')
            if hot:
                ui.text(surf, self.font, 'ENCOSTE p/ abrir', (sp[0], counter.bottom + int(23 * z)),
                        C.COL_WHITE, align='center')

    def _draw_camp_field_ui(self, surf):
        """Light HUD while walking the clearing -- at the BOTTOM, so it never
        competes with the doors and their labels up top. Title, hint, pollen."""
        cx, y = C.WIDTH // 2, C.HEIGHT - 92
        ui.text(surf, self.bigfont, "ACAMPAMENTO", (cx, y), C.COL_WHITE, align='center')
        ui.text(surf, self.font,
                "encoste na barraca p/ a loja  -  atravesse uma porta p/ avancar",
                (cx, y + 38), (210, 214, 228), align='center')
        pygame.draw.circle(surf, C.COL_POLLEN, (cx - 54, y + 68), 11)
        pygame.draw.circle(surf, (200, 160, 40), (cx - 54, y + 68), 11, 2)
        ui.text(surf, self.font, "POLEN", (cx - 38, y + 60), (214, 214, 230))
        ui.text(surf, self.bigfont, str(self.pollen), (cx + 16, y + 52), C.COL_POLLEN)

    def _draw_victory(self, surf):
        """Run beaten: celebratory summary + the DNA banked (endless now unlocked)."""
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 22, 16, 190))
        surf.blit(ov, (0, 0))
        cx = C.WIDTH // 2
        pulse = 0.5 + 0.5 * math.sin(self.time * 3)
        palette.glow(surf, (cx, 190), 300, (120, 250, 170), 0.28 + 0.16 * pulse)
        t = self.bigfont.render("VITORIA!", True, (150, 255, 190))
        surf.blit(t, (cx - t.get_width() // 2, 158))
        sub = self.font.render(f"voce derrotou o chefe primordial na onda {self.rounds.wave}",
                               True, (206, 236, 220))
        surf.blit(sub, (cx - sub.get_width() // 2, 214))

        rows = [
            ("score", f"{self.score}"),
            ("abates", f"{self.kills}"),
            ("nivel", f"{self.players[0].level}"),
            ("armas", f"{len(self.players[0].weapons)}"),
        ]
        y = 268
        for label, val in rows:
            li = self.font.render(label, True, (168, 200, 184))
            vi = self.bigfont.render(val, True, C.COL_WHITE)
            surf.blit(li, (cx - 150, y + 8))
            surf.blit(vi, (cx + 150 - vi.get_width(), y))
            y += 46

        gained = getattr(self, 'dna_gained', 0)
        d = self.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
        surf.blit(d, (cx - d.get_width() // 2, y + 14))
        bonus = self.font.render(f"(inclui bonus de vitoria +{progression.WIN_BONUS})",
                                 True, (150, 210, 180))
        surf.blit(bonus, (cx - bonus.get_width() // 2, y + 58))
        unl = self.font.render("MODO INFINITO DESBLOQUEADO no menu", True, (245, 220, 120))
        surf.blit(unl, (cx - unl.get_width() // 2, y + 88))
        h = self.font.render("Enter/A: jogar de novo     Esc/B: voltar ao menu", True, (200, 214, 206))
        surf.blit(h, (cx - h.get_width() // 2, y + 124))

    def _draw_over(self, surf):
        ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        ov.fill((10, 8, 20, 180))
        surf.blit(ov, (0, 0))
        t = self.bigfont.render("FIM DE JOGO", True, C.COL_ENEMY)
        surf.blit(t, (C.WIDTH // 2 - t.get_width() // 2, C.HEIGHT // 2 - 80))
        s = self.bigfont.render(f"Score {self.score}", True, C.COL_HUD)
        surf.blit(s, (C.WIDTH // 2 - s.get_width() // 2, C.HEIGHT // 2 - 24))
        # run summary + DNA banked
        cy = C.HEIGHT // 2 + 22
        line = self.font.render(
            f"onda {self.rounds.wave}   abates {self.kills}   nivel {self.players[0].level}",
            True, (198, 200, 220))
        surf.blit(line, (C.WIDTH // 2 - line.get_width() // 2, cy))
        gained = getattr(self, 'dna_gained', 0)
        d = self.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
        surf.blit(d, (C.WIDTH // 2 - d.get_width() // 2, cy + 30))
        tot = self.font.render(f"DNA total: {self.meta['dna']}   (gaste no menu > EVOLUCAO)",
                               True, (170, 210, 185))
        surf.blit(tot, (C.WIDTH // 2 - tot.get_width() // 2, cy + 76))
        h = self.font.render("Enter/A: jogar de novo     Esc/B: voltar ao menu", True, (200, 200, 220))
        surf.blit(h, (C.WIDTH // 2 - h.get_width() // 2, cy + 110))
