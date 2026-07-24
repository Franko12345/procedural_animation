"""Sandbox: dev-only debug overlay for spawning and testing entities live.

Isolated on purpose (ADR-0010: single-file-per-module). This one module owns the
sandbox controller and its mouse-driven, immediate-mode overlay; nothing in the
production UI knows it exists, and deleting this file plus the ``--sandbox`` branch
in ``app.main`` removes the feature whole.

Reached only via ``python lizard_game.py --sandbox`` -- a flag nobody passes on a
normal run. See ``plans/04_sandbox_debug.md`` for the full design. SB3 adds the
title feature: pick a category+target in the dropdown to *arm* a spawn, then
left-click in the world to drop it there (sticky -- each click drops another until
right-click / Esc cancels). Later slices hang round/store/loadout tooling off the
same spine.
"""

import random

import pygame
from pygame import Vector2

from .core import config as C
from .core.mathutil import random_dir
from . import champions
from . import display
from . import species
from . import ui
from .pickups import Bug, Fruit, Egg
from .rounds import BOSS_POOL, THEMES, THEME_KEYS, make_boss


# Keys that toggle the panel open/closed. Backtick is the classic dev-console key;
# F1 is the fallback for keyboards where backtick is awkward.
TOGGLE_KEYS = (pygame.K_BACKQUOTE, pygame.K_F1)

# The spawn/round categories, in panel order: (key, short label). ``round`` is
# not a spawn -- picking it swaps the item list for the theme picker and reveals
# the round-control footer (SB4).
CATEGORIES = (('boss', 'Boss'), ('champion', 'Champ'),
              ('species', 'Spec'), ('pickup', 'Pick'), ('round', 'Rnd'))
PICKUP_KEYS = ('bug', 'fruit', 'egg')
PICKUP_CTORS = {'bug': Bug, 'fruit': Fruit, 'egg': Egg}

# tier only scales a boss's hp/xp/score; the phase kit + name come from BOSS_POOL.
# A hand-spawned boss has no wave to derive a tier from, so pick a sane mid default.
SANDBOX_BOSS_TIER = 1


class Sandbox:
    """Per-frame debug overlay driven from ``app.main``'s sandbox branch.

    ``handle_event`` consumes the toggle key, panel clicks, and -- while a spawn is
    armed -- world clicks that place the entity, so none of those reach the live
    game. ``draw`` paints the panel on top when open plus a HUD line naming the
    armed spawn. The game keeps simulating underneath either way.
    """

    def __init__(self, game, font, bigfont=None):
        self.game = game
        self.font = font
        self.bigfont = bigfont or font
        self.open = False
        # Registry of hand-spawned things. The preset (SB later) walks this to
        # serialise the live scene. Every entity spawned by the sandbox is also
        # tagged ``_sb=(kind, key)`` so a scan of the game's lists can recover the
        # same tuples independently of this list.
        self.spawned = []
        # Panel geometry: a left-docked column, sized once.
        self.rect = pygame.Rect(16, 16, 300, C.HEIGHT - 32)
        # Dropdown state: which category is showing, the half-picked champion (the
        # champion category needs a champ *and* a species), and the armed spawn.
        self.cat = 'boss'
        self.champ_sel = None            # champ_id awaiting a species to pair with
        self.armed = None                # (kind, key) once a target is chosen
        # Round control (SB4): the theme + wave a manual start_round will fire.
        self.round_theme = THEME_KEYS[0]
        self.round_wave = 1

    # ---- registry ------------------------------------------------------- #
    def track(self, entity, kind, key):
        """Tag ``entity`` as sandbox-spawned and remember it. Base for the preset."""
        entity._sb = (kind, key)
        self.spawned.append(entity)
        return entity

    # ---- spawn ---------------------------------------------------------- #
    def spawn(self, kind, key, pos):
        """Resolve one ``(kind, key, pos)`` tuple to the real factory and place it.

        The single spawn path (plans/04 §3): the menu, world clicks, and the preset
        all funnel through here so there is never a divergent second way to spawn.
        ``pos=None`` drops it near the player. Returns the tracked entity.

            ('boss',     '<boss_id>',              pos)
            ('champion', '<champ_id>:<species>',   pos)
            ('species',  '<species_key>',          pos)
            ('pickup',   'bug'|'fruit'|'egg',      pos)
        """
        g = self.game
        if pos is None:
            p = g.players[0] if g.players else None
            base = p.pos if p else Vector2(C.WORLD_W / 2, C.WORLD_H / 2)
            pos = base + random_dir(random.uniform(120, 200))
        else:
            pos = Vector2(pos)

        if kind == 'boss':
            ent = make_boss(g, key, SANDBOX_BOSS_TIER, pos)
            g.enemies.append(ent)
        elif kind == 'champion':
            champ_id, species_key = key.split(':')
            ent = species.make(species_key, pos)
            champions.promote_to(ent, champ_id, g)
            g.enemies.append(ent)
        elif kind == 'species':
            ent = species.make(key, pos)
            role = species.SPECIES[key]['role']
            (g.prey if role == 'prey' else g.enemies).append(ent)
        elif kind == 'pickup':
            ent = PICKUP_CTORS[key](pos)
            g.pickups.append(ent)
        else:
            raise ValueError(f"unknown spawn kind: {kind!r}")
        return self.track(ent, kind, key)

    # ---- dropdown model ------------------------------------------------- #
    def _items(self):
        """(value, label) rows for the current category (and champion step)."""
        if self.cat == 'boss':
            return [(k, BOSS_POOL[k]['name']) for k in BOSS_POOL]
        if self.cat == 'pickup':
            return [(k, k.upper()) for k in PICKUP_KEYS]
        if self.cat == 'species':
            return [(k, species.info(k)[0]) for k in species.SPECIES]
        if self.cat == 'round':
            return [(k, THEMES[k]['banner']) for k in THEME_KEYS]
        # champion: pick the champ first, then a species to apply it to
        if self.champ_sel is None:
            return [(cid, champions.BY_ID[cid].name) for cid in champions.BY_ID]
        return [(k, species.info(k)[0]) for k in species.SPECIES]

    def _armed_label(self):
        """Human name of the armed spawn, for the HUD; None when nothing is armed."""
        if not self.armed:
            return None
        kind, key = self.armed
        if kind == 'boss':
            return f"BOSS {BOSS_POOL[key]['name']}"
        if kind == 'champion':
            champ_id, species_key = key.split(':')
            return f"{champions.BY_ID[champ_id].name} {species.info(species_key)[0]}"
        if kind == 'species':
            return species.info(key)[0]
        return key.upper()               # pickup

    def _select_cat(self, key):
        self.cat = key
        self.champ_sel = None

    def _select_item(self, value):
        if self.cat == 'boss':
            self.armed = ('boss', value)
        elif self.cat == 'species':
            self.armed = ('species', value)
        elif self.cat == 'pickup':
            self.armed = ('pickup', value)
        elif self.cat == 'round':
            self.round_theme = value         # pick the theme; START fires it
        elif self.cat == 'champion':
            if self.champ_sel is None:
                self.champ_sel = value           # first click picks the champion
            else:
                self.armed = ('champion', f'{self.champ_sel}:{value}')
                self.champ_sel = None

    # ---- round control (SB4) -------------------------------------------- #
    def _round_layout(self):
        """Footer rects for the round controls; only live while ``cat == 'round'``.
        Computed the same for draw + hit-test so clicks never depend on a draw."""
        r = self.rect
        x, w, bh = r.x + 14, r.width - 28, 28
        reset_r = pygame.Rect(x, r.bottom - 14 - bh, w, bh)
        start_r = pygame.Rect(x, reset_r.y - 8 - bh, w, bh)
        wy = start_r.y - 12 - bh
        dec_r = pygame.Rect(x, wy, 34, bh)
        inc_r = pygame.Rect(x + w - 34, wy, 34, bh)
        wave_r = pygame.Rect(dec_r.right + 4, wy, inc_r.left - dec_r.right - 8, bh)
        return dict(dec=dec_r, inc=inc_r, wave=wave_r, start=start_r, reset=reset_r)

    def _start_round(self):
        """Fire the chosen theme+wave through the REAL wave machine.

        ``start_round`` does ``wave += 1`` and rolls a boss on ``wave % 5 == 0``,
        so setting ``wave = round_wave - 1`` first lands it exactly on the picked
        wave with the right budget/tier. Called directly (not via the frozen
        ``RoundManager.update`` sandbox path) so the manual start still runs.
        """
        rm = self.game.rounds
        rm.wave = self.round_wave - 1
        rm.start_round(self.round_theme)

    def _reset_round(self):
        """Clear the scene and zero the RoundManager -- but never touch the player.

        Empties the entity lists + the round's nests/marks/boss and returns the
        machine to a fresh intermission (plans/04 §8). The player's position, hp,
        loadout, and level are the test subject, so they are left alone.
        """
        g = self.game
        g.enemies = []
        g.pending_enemies = []       # drains into enemies each step -- clear too
        g.prey = []
        g.projectiles = []
        g.pickups = []
        g.friends = []
        g.puddles = []               # leftover ground hazards are scene, not subject
        rm = g.rounds
        rm.boss = None
        rm.nests = []
        rm.marks = []
        rm.wave = 0
        rm.state = 'intermission'
        rm.is_boss_round = False
        rm.is_final = False
        rm.budget = 0
        g.wave = 0                   # HUD mirror of rm.wave (start_round re-syncs it)
        self.spawned = []            # the hand-spawned registry is gone with the scene
        self.armed = None
        self.champ_sel = None

    # ---- layout (shared by draw + hit-test) ----------------------------- #
    def _layout(self):
        """Return (cat_rects, item_rects); computed the same way for draw + clicks
        so hit-testing never depends on a draw having run first."""
        r = self.rect
        bw, bh = 52, 28              # five categories now, so the buttons are tighter
        by = r.y + 80
        cat_rects = [(pygame.Rect(r.x + 14 + i * (bw + 2), by, bw, bh), key, lbl)
                     for i, (key, lbl) in enumerate(CATEGORIES)]
        iy = by + bh + 30                # leave a line for the breadcrumb/hint
        item_rects = [(pygame.Rect(r.x + 14, iy + i * 26, r.width - 28, 24),
                       value, lbl)
                      for i, (value, lbl) in enumerate(self._items())]
        return cat_rects, item_rects

    # ---- input ---------------------------------------------------------- #
    def handle_event(self, ev):
        """Return True if the event was consumed by the overlay (so app.main skips it)."""
        if ev.type == pygame.KEYDOWN:
            if ev.key in TOGGLE_KEYS:
                self.open = not self.open
                return True
            # Esc cancels an armed spawn (sticky mode); only then, so a bare Esc
            # still reaches app.main's pause toggle when nothing is armed.
            if ev.key == pygame.K_ESCAPE and self.armed is not None:
                self.armed = None
                return True
            return False

        if ev.type == pygame.MOUSEBUTTONDOWN:
            mp = display.to_logical(ev.pos)
            # Panel clicks (only while open) never fall through to the world.
            if self.open and self.rect.collidepoint(mp):
                if ev.button == 1:
                    self._click_panel(mp)
                return True
            # Right-click anywhere in the world cancels an armed spawn.
            if ev.button == 3:
                if self.armed is not None:
                    self.armed = None
                    return True
                return False
            # Left-click in the world drops the armed entity there; stays armed
            # (sticky). Unarmed clicks fall through so the player controls normally.
            if ev.button == 1 and self.armed is not None:
                kind, key = self.armed
                self.spawn(kind, key, self.game.cam.s2w(mp))
                return True
        return False

    def _click_panel(self, mp):
        cat_rects, item_rects = self._layout()
        for rect, key, _ in cat_rects:
            if rect.collidepoint(mp):
                self._select_cat(key)
                return
        if self.cat == 'round':
            rl = self._round_layout()
            if rl['dec'].collidepoint(mp):
                self.round_wave = max(1, self.round_wave - 1)
                return
            if rl['inc'].collidepoint(mp):
                self.round_wave += 1
                return
            if rl['start'].collidepoint(mp):
                self._start_round()
                return
            if rl['reset'].collidepoint(mp):
                self._reset_round()
                return
        for rect, value, _ in item_rects:
            if rect.collidepoint(mp):
                self._select_item(value)
                return

    # ---- draw ----------------------------------------------------------- #
    def draw(self, surf):
        # HUD: the armed spawn's name, shown whether the panel is open or closed so
        # the sticky mode stays legible while you click around the world.
        label = self._armed_label()
        if label:
            ui.text(surf, self.font, f"[armado] {label}  -  dir/Esc cancela",
                    (C.WIDTH // 2, C.HEIGHT - 30), (255, 214, 110), align='center')
        if not self.open:
            ui.text(surf, self.font, "` sandbox", (C.WIDTH - 12, 8), ui.DIM,
                    align='right')
            return

        r = self.rect
        ui.panel(surf, r, alpha=205, accent=ui.LINE)
        ui.text(surf, self.bigfont, "SANDBOX", (r.x + 16, r.y + 14), ui.TEXT)
        ui.text(surf, self.font, "` / F1 fecha", (r.x + 16, r.y + 52), ui.DIM)

        cat_rects, item_rects = self._layout()
        for rect, key, lbl in cat_rects:
            cur = (key == self.cat)
            pygame.draw.rect(surf, (40, 46, 70) if cur else (22, 24, 38), rect,
                             border_radius=8)
            pygame.draw.rect(surf, (120, 150, 220) if cur else ui.LINE, rect, 2,
                             border_radius=8)
            ui.text(surf, self.font, lbl, (rect.centerx, rect.y + 4),
                    ui.TEXT if cur else ui.DIM, align='center')

        # Breadcrumb / hint line under the category row.
        hy = cat_rects[0][0].bottom + 6
        if self.cat == 'champion' and self.champ_sel is not None:
            ui.text(surf, self.font,
                    f"{champions.BY_ID[self.champ_sel].name} > especie:",
                    (r.x + 14, hy), (255, 214, 110))
        else:
            hint = {'boss': 'escolha o chefe', 'champion': 'escolha o campeao',
                    'species': 'escolha a especie', 'pickup': 'escolha o item',
                    'round': 'escolha o tema da onda'}
            ui.text(surf, self.font, hint[self.cat], (r.x + 14, hy), ui.DIM)

        mouse = display.mouse_logical()
        for rect, value, lbl in item_rects:
            if rect.collidepoint(mouse):
                pygame.draw.rect(surf, (44, 50, 76), rect, border_radius=6)
            # in round mode the picked theme reads as selected
            sel = (self.cat == 'round' and value == self.round_theme)
            ui.text(surf, self.font, ui.fit(self.font, lbl, rect.width - 8),
                    (rect.x + 6, rect.y + 2), (255, 214, 110) if sel else ui.TEXT)

        if self.cat == 'round':
            self._draw_round(surf, mouse)

    def _draw_round(self, surf, mouse):
        """The round-control footer: wave scroller + START/RESET buttons."""
        rl = self._round_layout()

        def button(rect, label, col_on):
            hot = rect.collidepoint(mouse)
            pygame.draw.rect(surf, col_on if hot else (24, 26, 42), rect,
                             border_radius=8)
            pygame.draw.rect(surf, (120, 150, 220) if hot else ui.LINE, rect, 2,
                             border_radius=8)
            ui.text(surf, self.font, label, (rect.centerx, rect.y + 4),
                    ui.TEXT, align='center')

        button(rl['dec'], '-', (40, 46, 70))
        button(rl['inc'], '+', (40, 46, 70))
        wr = rl['wave']
        pygame.draw.rect(surf, (22, 24, 38), wr, border_radius=8)
        pygame.draw.rect(surf, ui.LINE, wr, 2, border_radius=8)
        boss = '  (chefe)' if self.round_wave % 5 == 0 else ''
        ui.text(surf, self.font, f"onda {self.round_wave}{boss}",
                (wr.centerx, wr.y + 4), ui.TEXT, align='center')
        start_lbl = ui.fit(self.font, f"START -> {THEMES[self.round_theme]['banner']}",
                           rl['start'].width - 12)
        button(rl['start'], start_lbl, (30, 60, 40))
        button(rl['reset'], 'RESET (limpa a cena)', (70, 34, 40))
