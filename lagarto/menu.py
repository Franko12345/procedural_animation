"""Title hub: play (1/2 players), options (fullscreen/resize) and controls.

A navigable menu (arrows/mouse) over a live backdrop of procedurally-animated
lizards. Returns the chosen player count to `app`, or None to quit.
"""

import math
import random
from pygame import Vector2
import pygame

from . import config as C
from . import display
from . import palette
from . import settings
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
    """Draw a vertical list; return clickable rects."""
    cx = C.WIDTH // 2
    rects = []
    for i, label in enumerate(items):
        chosen = (i == sel)
        y = top + i * 58
        w = 420
        rect = pygame.Rect(cx - w // 2, y, w, 48)
        rects.append(rect)
        if chosen:
            palette.glow(screen, rect.center, 120, accent, 0.35)
            pygame.draw.rect(screen, accent, rect, 3, border_radius=12)
        col = C.COL_WHITE if chosen else (150, 152, 172)
        im = bigfont.render(label, True, col)
        screen.blit(im, (cx - im.get_width() // 2, y + 4))
    return rects


def run_menu(screen, font, bigfont, titlefont, joysticks):
    from .controllers import MenuNav
    clock = pygame.time.Clock()
    nav = MenuNav()
    demo, cam, world = _make_backdrop()
    t = 0.0
    mode = 'main'
    sel = 0
    rects = []            # menu item rects (from the previous frame, for mouse hits)

    main_items = ['1 JOGADOR', '2 JOGADORES (COOP)', 'OPCOES', 'CONTROLES',
                  'BESTIARIO', 'COMPENDIO', 'SAIR']

    def toggle_fs():
        display.toggle_fullscreen()
        settings.save_display(display)

    while True:
        dt = clock.tick(60) / 1000.0
        t += dt
        mouse = pygame.mouse.get_pos()

        if mode == 'main':
            items = main_items
        elif mode == 'options':
            items = [f'TELA CHEIA: {"LIGADA" if display.is_fullscreen() else "DESLIGADA"}  (F11)',
                     f'ESCALA DA JANELA: {display.get_scale()}x',
                     f'VSYNC: {"LIGADO" if display.get_vsync() else "DESLIGADO"}',
                     'VOLTAR']
        else:
            items = ['VOLTAR']

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
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    r = _activate(mode, sel, toggle_fs)
                    if r == 'quit':
                        return None
                    if r in (1, 2):
                        return r
                    if r is not None:
                        mode, sel = r, 0
                elif ev.key == pygame.K_ESCAPE:
                    if mode == 'main':
                        return None
                    mode, sel = 'main', 0
            if ev.type == pygame.VIDEORESIZE:
                display.handle_resize()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = display.to_logical(ev.pos)      # window px -> logical px
                for i, rect in enumerate(rects):
                    if rect.collidepoint(mp):
                        sel = i
                        r = _activate(mode, sel, toggle_fs)
                        if r == 'quit':
                            return None
                        if r in (1, 2):
                            return r
                        if r is not None:
                            mode, sel = r, 0
                        break

        # gamepad navigation (same actions as the keyboard)
        nav.poll(joysticks, dt)
        if nav.down:
            sel = (sel + 1) % len(items)
        if nav.up:
            sel = (sel - 1) % len(items)
        if nav.confirm:
            r = _activate(mode, sel, toggle_fs)
            if r == 'quit':
                return None
            if r in (1, 2):
                return r
            if r is not None:
                mode, sel = r, 0
        if nav.cancel:
            if mode == 'main':
                return None
            mode, sel = 'main', 0

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
        else:  # controls
            _panel(screen, pygame.Rect(C.WIDTH // 2 - 360, 220, 720, 300))
            lines = [
                "P1:  WASD mover  -  mouse mirar  -  clique/ESPACO dash  -  dir/SHIFT lingua",
                "P1 (gamepad):  sticks  -  A dash  -  X lingua   (no single-player)",
                "P2:  setas mover  -  IJKL mirar  -  RCtrl dash  -  RShift lingua",
                "P2 (gamepad):  sticks  -  A dash  -  X lingua",
                "",
                "armas atacam sozinhas - suba de nivel p/ evoluir - F11 tela cheia - ESC pausa",
            ]
            for i, l in enumerate(lines):
                im = font.render(l, True, (206, 208, 226) if l else (150, 150, 170))
                screen.blit(im, (C.WIDTH // 2 - im.get_width() // 2, 250 + i * 32))
            rects = _menu_list(screen, font, bigfont, items, sel, 470, C.COL_PLAYER2[0])

        display.present()


def _activate(mode, sel, toggle_fs):
    """Return 1/2 to start, a mode name to switch screen, or None for no-op."""
    if mode == 'main':
        opts = [1, 2, 'options', 'controls', 'bestiary', 'compendium', 'quit']
        return opts[sel] if sel < len(opts) else None
    if mode == 'options':
        if sel == 0:
            toggle_fs()
        elif sel == 1:
            display.cycle_scale()
            settings.save_display(display)
        elif sel == 2:
            display.toggle_vsync()
            settings.save_display(display)
        else:
            return 'main'                 # VOLTAR
        return None
    return 'main'                         # controls/bestiary/compendium -> VOLTAR


