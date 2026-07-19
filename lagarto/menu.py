"""Title hub: play (1/2 players), options (fullscreen/resize) and controls.

A navigable menu (arrows/mouse) over a live backdrop of procedurally-animated
lizards. Returns the chosen player count to `app`, or None to quit.
"""

import math
import random
from pygame import Vector2
import pygame

from . import audio
from . import charms
from . import config as C
from . import display
from . import evolution
from . import icons
from . import palette
from . import progression
from . import settings
from . import species
from . import ui
from . import weapons
from .mathutil import vfrom_angle
from .mathutil import approach, clamp, safe_norm, vfrom_angle
from .lizard import AILizard
from .camera import Camera
from .world import World


def _make_backdrop():
    demo = [AILizard(Vector2(0, 0), 'prey', random.uniform(0.7, 1.4),
                     random.choice([C.COL_PREY, C.COL_FRIEND, C.COL_BUG,
                                    C.COL_PLAYER[0], C.COL_PLAYER2[0], C.COL_ENEMY]))
            for _ in range(6)]
    cam = Camera()
    cam.pos = Vector2(C.WORLD_W / 2, C.WORLD_H / 2)
    cam.zoom = 1.0
    for d in demo:
        d.pos = cam.pos + Vector2(random.uniform(-420, 420), random.uniform(-280, 280))
        d.spine.resolve(d.pos)
    return demo, cam, World()


def _step_backdrop(demo, cam, world, dt):
    world.update(dt)
    for d in demo:
        d.on_screen = True
        d.steer(d.wander_dir(dt), dt, 0.5)
        for ax in (0, 1):
            if d.pos[ax] < cam.pos[ax] - 470:
                d.vel[ax] = abs(d.vel[ax])
            if d.pos[ax] > cam.pos[ax] + 470:
                d.vel[ax] = -abs(d.vel[ax])
        d.pos += d.vel * dt
        d.spine.resolve(d.pos)
        if d.vel.length_squared() > 1:
            d.facing = safe_norm(d.vel)
        for leg in d.legs:
            leg.update(d.spine, d.vel, dt, None)
        d.squash = approach(d.squash, 1 + clamp(d.vel.length() / d.max_speed, 0, 1) * 0.16,
                            9, dt)


def _draw_backdrop(screen, demo, cam, world):
    screen.fill(C.COL_BG)
    world.draw_ground(screen, cam)
    world.draw_decor(screen, cam)
    for d in demo:
        d.draw(screen, cam)
    world.draw_ambient(screen, cam)
    veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    veil.fill((12, 10, 24, 120))
    screen.blit(veil, (0, 0))


def _title(screen, titlefont, font, t):
    cx = C.WIDTH // 2
    glow = 0.6 + 0.4 * math.sin(t * 2)
    palette.glow(screen, (cx, 118), 240, C.COL_PLAYER[0], 0.25 + 0.15 * glow)
    title = titlefont.render("L A G A R T O", True, C.COL_PLAYER[0])
    screen.blit(title, (cx - title.get_width() // 2, 78))
    sub = font.render("roguelite de evolucao procedural", True, (205, 205, 225))
    screen.blit(sub, (cx - sub.get_width() // 2, 150))


def _panel(screen, rect):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((16, 18, 30, 180))
    screen.blit(s, (rect.x, rect.y))
    pygame.draw.rect(screen, (60, 64, 96), rect, 2, border_radius=16)


def _menu_list(screen, font, bigfont, items, sel, top, accent):
    """Draw a vertical list; return clickable rects. Spacing adapts to item count."""
    cx = C.WIDTH // 2
    rects = []
    # keep the whole list on screen even when a screen grows new entries
    gap = 58
    if items:
        gap = max(40, min(58, (C.HEIGHT - top - 56) // len(items)))
    small = gap < 52
    for i, label in enumerate(items):
        chosen = (i == sel)
        y = top + i * gap
        w = 420
        rect = pygame.Rect(cx - w // 2, y, w, gap - 10)
        rects.append((i, rect))
        if chosen:
            palette.glow(screen, rect.center, 120, accent, 0.35)
            pygame.draw.rect(screen, accent, rect, 3, border_radius=12)
        col = C.COL_WHITE if chosen else (150, 152, 172)
        f = font if small else bigfont
        im = f.render(label, True, col)
        screen.blit(im, (cx - im.get_width() // 2, rect.centery - im.get_height() // 2))
    return rects


def _side_list(screen, font, items, sel, rect, accent, scroll=0):
    """Compact list inside `rect` (bestiary/compendium). Returns clickable rects."""
    _panel(screen, rect)
    rects = []
    row = 32
    visible = (rect.height - 16) // row
    top = max(0, min(sel - visible // 2, max(0, len(items) - visible)))
    for i in range(top, min(len(items), top + visible)):
        y = rect.y + 8 + (i - top) * row
        r = pygame.Rect(rect.x + 6, y, rect.width - 12, row - 3)
        rects.append((i, r))
        if i == sel:
            pygame.draw.rect(screen, (30, 34, 52), r, border_radius=8)
            pygame.draw.rect(screen, accent, r, 2, border_radius=8)
        im = font.render(items[i], True, C.COL_WHITE if i == sel else (152, 155, 178))
        screen.blit(im, (r.x + 10, r.y + 3))
    return rects


def _preview_step(c, cam, dt, t):
    """Walk the bestiary creature in a slow circle so its legs animate."""
    c.on_screen = True
    c.steer(vfrom_angle(t * 45), dt, 0.5)
    c.pos += c.vel * dt
    c.spine.resolve(c.pos)
    if c.vel.length_squared() > 1:
        c.facing = safe_norm(c.vel)
    for leg in c.legs:
        leg.update(c.spine, c.vel, dt, None)
    c.squash = approach(c.squash, 1 + clamp(c.vel.length() / c.max_speed, 0, 1) * 0.16, 9, dt)
    c.wobble += dt * 6
    cam.pos = Vector2(c.pos)


def _draw_bestiary(screen, font, bigfont, keys, sel, preview, cam):
    left = pygame.Rect(70, 200, 330, 452)
    right = pygame.Rect(420, 200, C.WIDTH - 490, 452)
    labels = [species.info(k)[0] for k in keys] + ['VOLTAR']
    rects = _side_list(screen, font, labels, sel, left, C.COL_PLAYER2[0])
    _panel(screen, right)

    if sel >= len(keys):
        im = font.render("voltar ao menu", True, (170, 172, 194))
        screen.blit(im, (right.centerx - im.get_width() // 2, right.centery))
        return rects

    key = keys[sel]
    spec = species.SPECIES[key]
    name, lore = species.info(key)
    # live procedural creature, clipped to the panel
    old = screen.get_clip()
    stage = pygame.Rect(right.x + 8, right.y + 8, right.width - 16, 210)
    screen.set_clip(stage)
    cam.center = (stage.centerx, stage.centery)
    if preview:
        preview.draw(screen, cam)
    screen.set_clip(old)
    pygame.draw.rect(screen, (54, 58, 88), stage, 1, border_radius=12)

    y = stage.bottom + 14
    screen.blit(bigfont.render(name, True, C.COL_WHITE), (right.x + 22, y))
    y += 44
    role = 'PREDADOR' if spec['role'] == 'enemy' else 'PRESA'
    rc = C.COL_ENEMY if spec['role'] == 'enemy' else C.COL_PREY
    ui.chip(screen, font, role, right.x + 22, y, rc)
    ui.chip(screen, font, f"XP {spec['xp']}", right.x + 150, y, (245, 210, 90))
    ui.chip(screen, font, f"PTS {spec['score']}", right.x + 250, y, (150, 200, 245))
    if spec['grants']:
        ui.chip(screen, font, f"concede: {spec['grants']}", right.x + 360, y, C.COL_FRIEND)
    y += 44
    ui.paragraph(screen, font, lore, right.x + 22, y, right.width - 44)
    return rects


def _draw_compendium(screen, font, bigfont, tab, entries, sel):
    tabs_r = ui.tabs(screen, font, ['ARMAS', 'EVOLUCOES', 'CHARMS'], tab, 196,
                     C.COL_PLAYER[0])
    left = pygame.Rect(70, 246, 330, 400)
    right = pygame.Rect(420, 246, C.WIDTH - 490, 400)
    labels = [e['name'] for e in entries] + ['VOLTAR']
    rects = _side_list(screen, font, labels, sel, left, C.COL_PLAYER[0])
    _panel(screen, right)
    if sel >= len(entries):
        im = font.render("voltar ao menu", True, (170, 172, 194))
        screen.blit(im, (right.centerx - im.get_width() // 2, right.centery))
        return rects, tabs_r

    e = entries[sel]
    x, y = right.x + 22, right.y + 20
    icons.draw(screen, e.get('icon'), (x + 18, y + 18), 18, e['color'])
    screen.blit(bigfont.render(e['name'], True, C.COL_WHITE), (x + 50, y + 2))
    y += 56
    if e.get('tag'):
        ui.chip(screen, font, e['tag'], x, y, e['color'])
        y += 40
    y = ui.paragraph(screen, font, e['desc'], x, y, right.width - 44) + 12
    for line in e.get('levels', []):
        screen.blit(font.render(line, True, (186, 190, 214)), (x + 8, y))
        y += 24
    return rects, tabs_r



def _buy_meta(meta, entries, sel):
    """Confirm on a meta row = buy that upgrade/unlock. Returns True if bought."""
    if sel >= len(entries):
        return False
    e = entries[sel]
    if e['cost'] is None:
        return False
    ok = (progression.buy_upgrade(meta, e['id']) if e['kind'] == 'upgrade'
          else progression.buy_unlock(meta, e['id']))
    return ok

def _meta_entries():
    """Rows for the DNA screen: permanent upgrades then unlocks."""
    data = progression.load()
    out = []
    for uid, spec in progression.UPGRADES.items():
        lvl = progression.level(data, uid)
        cost = progression.upgrade_cost(data, uid)
        out.append(dict(kind='upgrade', id=uid, name=spec['name'], desc=spec['desc'],
                        hue=spec['hue'], level=lvl, maxlevel=spec['max_level'],
                        cost=cost))
    for uid, spec in progression.UNLOCKS.items():
        owned = uid in data['unlocks']
        out.append(dict(kind='unlock', id=uid, name=spec['name'], desc=spec['desc'],
                        hue=spec['hue'], level=1 if owned else 0, maxlevel=1,
                        cost=None if owned else spec['cost']))
    return out


def _draw_meta(screen, font, bigfont, entries, sel, dna):
    box = pygame.Rect(120, 196, C.WIDTH - 240, 460)
    _panel(screen, box)
    hdr = bigfont.render("EVOLUCAO PERMANENTE", True, C.COL_WHITE)
    screen.blit(hdr, (box.centerx - hdr.get_width() // 2, box.y + 12))
    dn = bigfont.render(f"{dna} DNA", True, (140, 240, 170))
    screen.blit(dn, (box.right - dn.get_width() - 22, box.y + 14))

    rects = []
    row_h = 50
    top = box.y + 62
    visible = (box.height - 80) // row_h
    start = max(0, min(sel - visible // 2, max(0, len(entries) + 1 - visible)))
    labels = entries + ['VOLTAR']
    for i in range(start, min(len(labels), start + visible)):
        y = top + (i - start) * row_h
        r = pygame.Rect(box.x + 14, y, box.width - 28, row_h - 6)
        rects.append((i, r))
        chosen = (i == sel)
        e = labels[i]
        if chosen:
            pygame.draw.rect(screen, (30, 34, 52), r, border_radius=10)
        if isinstance(e, str):                    # VOLTAR
            pygame.draw.rect(screen, (120, 124, 150) if chosen else (70, 72, 92),
                             r, 2, border_radius=10)
            im = font.render(e, True, C.COL_WHITE if chosen else (150, 152, 172))
            screen.blit(im, (r.centerx - im.get_width() // 2, r.y + 8))
            continue
        col = palette.vibrant(e['hue'], 0.8, 1.0)
        maxed = e['cost'] is None
        afford = (not maxed) and dna >= e['cost']
        edge = col if (chosen or afford) else (70, 72, 92)
        pygame.draw.rect(screen, edge, r, 3 if chosen else 1, border_radius=10)
        icons.draw(screen, e['id'].replace('weapon_', '').replace('charm_', ''),
                   (r.x + 26, r.centery), 13, col, glow=False)
        screen.blit(font.render(e['name'], True, C.COL_WHITE), (r.x + 50, r.y + 3))
        screen.blit(font.render(e['desc'], True, (168, 172, 196)), (r.x + 50, r.y + 21))
        # level pips
        px = r.right - 210
        for k in range(e['maxlevel']):
            c = col if k < e['level'] else (58, 60, 82)
            pygame.draw.circle(screen, c, (px + k * 18, r.centery), 6)
        txt = 'MAX' if maxed else f"{e['cost']} DNA"
        tc = (150, 240, 180) if afford else ((160, 200, 175) if maxed else (140, 120, 90))
        im = font.render(txt, True, tc)
        screen.blit(im, (r.right - im.get_width() - 14, r.centery - 9))
    return rects


def _compendium_entries(tab):
    out = []
    if tab == 0:
        for wid, w in weapons.WEAPONS.items():
            lv = [f"Nv{i+1}: {w.level_desc(i+1)}" for i in range(w.maxlevel())]
            out.append(dict(name=w.name, color=w.color, icon=wid, tag='ARMA AUTOMATICA',
                            desc='Ataca sozinha. Suba de nivel nas cartas para melhorar.',
                            levels=lv))
    elif tab == 1:
        for m in evolution.MUTATIONS:
            out.append(dict(name=m.name, color=m.color, icon=m.icon, tag='MUTACAO', desc=m.desc))
        for s in evolution.SYNERGIES:
            out.append(dict(name=f"SINERGIA: {s.name}", color=C.COL_WHITE,
                            tag='COMBO', desc=s.desc,
                            levels=[f"requer: {', '.join(sorted(s.needs))}"]))
    else:
        for c in charms.CHARMS.values():
            out.append(dict(name=c.name, color=palette.vibrant(c.hue, 0.8, 1.0), icon=c.id,
                            tag=f"SLOT: {c.slot.upper()}", desc=c.desc,
                            levels=[f"custo: {c.cost} polen"]))
    return out


def run_menu(screen, font, bigfont, titlefont, joysticks):
    from .controllers import MenuNav
    clock = pygame.time.Clock()
    nav = MenuNav()
    fade = ui.Fade()
    fade.start(0.3)
    prev_mode = 'main'
    demo, cam, world = _make_backdrop()
    t = 0.0
    mode = 'main'
    sel = 0
    rects = []            # menu item rects (from the previous frame, for mouse hits)
    # bestiary / compendium state
    bkeys = list(species.SPECIES.keys())
    preview = {'key': None, 'creature': None, 'cam': Camera()}
    preview['cam'].zoom = 1.0
    tab = 0
    tab_rects = []
    meta = progression.load()

    def toggle_fs():
        display.toggle_fullscreen()
        settings.save_display(display, audio)

    while True:
        dt = clock.tick(60) / 1000.0
        t += dt
        mouse = pygame.mouse.get_pos()

        items = _items_for(mode, bkeys, tab, meta)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    toggle_fs()
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % len(items)
                elif ev.key in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % len(items)
                elif ev.key in (pygame.K_LEFT, pygame.K_a) and mode == 'compendium':
                    tab, sel = (tab - 1) % 3, 0
                elif ev.key in (pygame.K_RIGHT, pygame.K_d) and mode == 'compendium':
                    tab, sel = (tab + 1) % 3, 0
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if mode == 'meta' and _buy_meta(meta, items[:-1], sel):
                        audio.play('buy'); meta = progression.load(); continue
                    r = _activate(mode, sel, toggle_fs, len(items))
                    if r == 'quit':
                        return None
                    st = _start_for(r, meta)
                    if st:
                        return st
                    if r is not None and r not in ('play1', 'play2', 'endless'):
                        mode, sel = r, 0
                elif ev.key == pygame.K_ESCAPE:
                    if mode == 'main':
                        return None
                    mode, sel = 'main', 0
            if ev.type == pygame.VIDEORESIZE:
                display.handle_resize()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = display.to_logical(ev.pos)      # window px -> logical px
                for ti, trect in enumerate(tab_rects):
                    if trect.collidepoint(mp):
                        tab, sel = ti, 0
                for i, rect in rects:
                    if rect.collidepoint(mp):
                        sel = i
                        if mode == 'meta' and _buy_meta(meta, items[:-1], sel):
                            audio.play('buy'); meta = progression.load(); break
                        r = _activate(mode, sel, toggle_fs, len(items))
                        if r == 'quit':
                            return None
                        st = _start_for(r, meta)
                        if st:
                            return st
                        if r is not None and r not in ('play1', 'play2', 'endless'):
                            mode, sel = r, 0
                        break

        # gamepad navigation (same actions as the keyboard)
        nav.poll(joysticks, dt)
        if nav.down:
            sel = (sel + 1) % len(items); audio.play('ui', 0.5)
        if nav.up:
            sel = (sel - 1) % len(items); audio.play('ui', 0.5)
        if mode == 'compendium':
            if nav.left:
                tab, sel = (tab - 1) % 3, 0
            if nav.right:
                tab, sel = (tab + 1) % 3, 0
        if nav.confirm and mode == 'meta' and _buy_meta(meta, items[:-1], sel):
            audio.play('buy'); meta = progression.load()
        elif nav.confirm:
            r = _activate(mode, sel, toggle_fs, len(items))
            if r == 'quit':
                return None
            st = _start_for(r, meta)
            if st:
                return st
            if r is not None and r not in ('play1', 'play2', 'endless'):
                mode, sel = r, 0
        if nav.cancel:
            if mode == 'main':
                return None
            mode, sel = 'main', 0

        # input may have switched screens this frame -> refresh the item list so we
        # never draw one screen's items with another screen's layout
        items = _items_for(mode, bkeys, tab, meta)

        _step_backdrop(demo, cam, world, dt)
        _draw_backdrop(screen, demo, cam, world)
        _title(screen, titlefont, font, t)

        if mode == 'main':
            rects = _menu_list(screen, font, bigfont, items, sel, 250, C.COL_PLAYER[0])
            legend = ("gamepad detectado" if joysticks else "gamepad: conecte p/ P2")
            foot = font.render(f"setas/mouse p/ navegar - ENTER p/ escolher - {legend}",
                               True, (170, 172, 194))
            screen.blit(foot, (C.WIDTH // 2 - foot.get_width() // 2, C.HEIGHT - 44))
        elif mode == 'options':
            _panel(screen, pygame.Rect(C.WIDTH // 2 - 300, 230, 600, 240))
            rects = _menu_list(screen, font, bigfont, items, sel, 268, C.COL_PLAYER2[0])
            hint = font.render("arraste a janela p/ redimensionar - vsync ligado",
                               True, (180, 182, 202))
            screen.blit(hint, (C.WIDTH // 2 - hint.get_width() // 2, 420))
        elif mode == 'meta':
            rects = _draw_meta(screen, font, bigfont, items[:-1], sel, meta['dna'])
            tab_rects = []
            ui.footer(screen, font, "ENTER/A compra - ganhe DNA jogando - ESC/B volta")
        elif mode == 'bestiary':
            # keep a live creature of the highlighted species
            key = bkeys[sel] if sel < len(bkeys) else None
            if key != preview['key']:
                preview['key'] = key
                preview['creature'] = species.make(key, Vector2(C.WORLD_W / 2,
                                                                C.WORLD_H / 2)) if key else None
            if preview['creature']:
                _preview_step(preview['creature'], preview['cam'], dt, t)
            rects = _draw_bestiary(screen, font, bigfont, bkeys, sel,
                                   preview['creature'], preview['cam'])
            tab_rects = []
            ui.footer(screen, font, "setas p/ navegar - ESC/B volta")
        elif mode == 'compendium':
            entries = _compendium_entries(tab)
            rects, tab_rects = _draw_compendium(screen, font, bigfont, tab, entries, sel)
            ui.footer(screen, font, "setas cima/baixo: item - esquerda/direita: aba - ESC/B volta")
        else:  # controls
            _panel(screen, pygame.Rect(C.WIDTH // 2 - 360, 220, 720, 300))
            lines = [
                "P1:  WASD mover  -  mouse mirar  -  clique/ESPACO dash  -  dir/SHIFT lingua",
                "P1 (gamepad):  sticks  -  A dash  -  X lingua   (no single-player)",
                "P2:  setas mover  -  IJKL mirar  -  RCtrl dash  -  RShift lingua",
                "P2 (gamepad):  sticks  -  A dash  -  X lingua",
                "",
                "armas atacam sozinhas - suba de nivel p/ evoluir - F11 tela cheia - ESC pausa",
                "",
                (f"gamepad: {joysticks[0].name}" if joysticks else
                 "gamepad: nenhum detectado (conecte e ele e reconhecido na hora)"),
            ]
            for i, l in enumerate(lines):
                im = font.render(l, True, (206, 208, 226) if l else (150, 150, 170))
                screen.blit(im, (C.WIDTH // 2 - im.get_width() // 2, 250 + i * 32))
            rects = _menu_list(screen, font, bigfont, items, sel, 470, C.COL_PLAYER2[0])

        if mode != prev_mode:
            fade.start(0.2)
            prev_mode = mode
        fade.update(dt)
        fade.draw(screen)
        display.present()


def _start_for(r, meta):
    """Map a menu action to (num_players, mode), or None if it isn't a start."""
    if r == 'play1':
        return (1, 'normal')
    if r == 'play2':
        return (2, 'normal')
    if r == 'endless':
        return (1, 'endless') if progression.endless_unlocked(meta) else None
    return None


def _main_items(meta):
    endless = ('MODO INFINITO' if progression.endless_unlocked(meta)
               else 'MODO INFINITO (vença a run p/ liberar)')
    return ['JOGAR (1 JOGADOR)', endless, '2 JOGADORES (COOP)', 'EVOLUCAO (DNA)',
            'OPCOES', 'CONTROLES', 'BESTIARIO', 'COMPENDIO', 'SAIR']


def _items_for(mode, bkeys, tab, meta):
    """The navigable item list for a screen (drives selection + hit-testing)."""
    if mode == 'main':
        return _main_items(meta)
    if mode == 'options':
        return [f'TELA CHEIA: {"LIGADA" if display.is_fullscreen() else "DESLIGADA"}  (F11)',
                f'ESCALA DA JANELA: {display.get_scale()}x',
                f'VSYNC: {"LIGADO" if display.get_vsync() else "DESLIGADO"}',
                f'VOLUME EFEITOS: {int(audio.volumes()[0] * 100)}%',
                f'VOLUME MUSICA: {int(audio.volumes()[1] * 100)}%',
                'VOLTAR']
    if mode == 'meta':
        return _meta_entries() + ['VOLTAR']
    if mode == 'bestiary':
        return bkeys + ['VOLTAR']
    if mode == 'compendium':
        return _compendium_entries(tab) + ['VOLTAR']
    return ['VOLTAR']


def _activate(mode, sel, toggle_fs, n_items=0):
    """Return 1/2 to start, a mode name to switch screen, or None for no-op."""
    if mode in ('bestiary', 'compendium'):
        return 'main' if sel >= n_items - 1 else None    # only VOLTAR does anything
    if mode == 'meta':
        return 'main' if sel >= n_items - 1 else None    # buying handled by the caller
    if mode == 'main':
        opts = ['play1', 'endless', 'play2', 'meta', 'options', 'controls',
                'bestiary', 'compendium', 'quit']
        return opts[sel] if sel < len(opts) else None
    if mode == 'options':
        if sel == 0:
            toggle_fs()
        elif sel == 1:
            display.cycle_scale()
            settings.save_display(display)
        elif sel == 2:
            display.toggle_vsync()
            settings.save_display(display, audio)
        elif sel == 3:
            sfx, mus = audio.volumes()
            audio.set_volumes(sfx=0.0 if sfx >= 0.99 else min(1.0, sfx + 0.1))
            audio.play('ui')
            settings.save_display(display, audio)
        elif sel == 4:
            sfx, mus = audio.volumes()
            audio.set_volumes(music=0.0 if mus >= 0.99 else min(1.0, mus + 0.1))
            settings.save_display(display, audio)
        else:
            return 'main'                 # VOLTAR
        return None
    return 'main'                         # controls/bestiary/compendium -> VOLTAR


