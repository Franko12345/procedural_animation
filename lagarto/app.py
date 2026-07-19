"""Entry point: window setup, the menu -> match loop, and the fixed-timestep loop.

Simulation advances in fixed ``DT`` steps (frame-rate independent, deterministic,
online-friendly); rendering happens once per frame after catching up. ``--smoke N``
runs N frames and exits, for headless self-tests.
"""

import sys
import pygame

from . import config as C
from . import display
from . import settings
from .controllers import (make_controllers, describe_joysticks, Pad, MenuNav,
                          KeyboardMouseController, GamepadController)
from .game import Game
from .menu import run_menu


def _init_joysticks():
    # NOTE: never call pygame.joystick.quit() here -- doing it while the event
    # queue is being built (JOYDEVICEADDED) corrupts it (KeyError inside event.get).
    pygame.joystick.init()
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            joysticks.append(Pad(i))
        except Exception as e:
            print(f"[gamepad] falha ao abrir o controle {i}: {e}")
    if joysticks:
        describe_joysticks(joysticks)
    else:
        print("[gamepad] nenhum controle detectado pelo SDL/pygame. "
              "Conecte via USB (ou pareie), verifique se o SO o reconhece "
              "(Linux: pacote 'joystick'/driver xpad; modo XInput no controle) "
              "e conecte antes/depois — o jogo redetecta ao plugar.")
    return joysticks


def _reattach(controllers, joysticks):
    """Point the current controllers at the (re)detected pad after a hot-plug."""
    for c in controllers:
        if isinstance(c, (KeyboardMouseController, GamepadController)):
            c.joy = joysticks[0] if joysticks else (c.joy if isinstance(c, GamepadController) else None)


def main():
    smoke = 0
    if '--smoke' in sys.argv:
        i = sys.argv.index('--smoke')
        smoke = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 120

    pygame.init()
    pygame.joystick.init()
    # Everything draws to a fixed logical surface; display.present() scales it to the
    # window (letterboxed). That's what allows the 1x/2x/3x window-size presets.
    cfg = settings.load()
    screen = display.init(scale=cfg['scale'], fullscreen=cfg['fullscreen'],
                          vsync=cfg['vsync'])
    pygame.display.set_caption("Lagarto - procedural animation game")

    font = pygame.font.SysFont("dejavusans", 18)
    bigfont = pygame.font.SysFont("dejavusans", 34, bold=True)
    titlefont = pygame.font.SysFont("dejavusans", 64, bold=True)

    joysticks = _init_joysticks()
    clock = pygame.time.Clock()
    nav = MenuNav()          # gamepad navigation for level-up / camp screens

    while True:
        if smoke:
            num = 1
        else:
            num = run_menu(screen, font, bigfont, titlefont, joysticks)
            if num is None:
                break

        controllers = make_controllers(num, joysticks)
        game = Game(num, controllers, font, bigfont)
        acc = 0.0
        frames = 0
        running = True

        while running:
            frame_dt = min(clock.tick(0 if smoke else C.RENDER_FPS) / 1000.0, 0.05)
            frames += 1

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    joysticks = _init_joysticks()          # hot-plug: redetect + reattach
                    _reattach(controllers, joysticks)
                if ev.type == pygame.VIDEORESIZE:
                    display.handle_resize()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    if ev.key == pygame.K_F11:
                        display.toggle_fullscreen()
                        settings.save_display(display)
                    if game.state == 'over' and ev.key == pygame.K_RETURN:
                        game = Game(num, controllers, font, bigfont)
                    elif game.state == 'levelup':
                        if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                            game.choose_card(ev.key - pygame.K_1)
                        elif ev.key in (pygame.K_LEFT, pygame.K_a):
                            game.card_idx = max(0, game.card_idx - 1)
                        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                            game.card_idx = min(len(game.cards) - 1, game.card_idx + 1)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            game.choose_card(game.card_idx)
                    elif game.state == 'camp' and game.camp:
                        if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                            game.camp_buy(ev.key - pygame.K_1)
                        elif ev.key in (pygame.K_LEFT, pygame.K_a):
                            game.camp['sel'] = max(0, game.camp['sel'] - 1)
                        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                            game.camp['sel'] = min(len(game.camp['routes']) - 1, game.camp['sel'] + 1)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            game.camp_pick_route(game.camp['sel'])
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    # window pixels -> logical pixels (the surface is scaled)
                    mp = display.to_logical(ev.pos)
                    if game.state == 'levelup':
                        for i, rect in enumerate(getattr(game, '_card_rects', [])):
                            if rect.collidepoint(mp):
                                game.choose_card(i)
                    elif game.state == 'camp':
                        for i, rect in enumerate(getattr(game, '_shop_rects', [])):
                            if rect.collidepoint(mp):
                                game.camp_buy(i)
                        for rect, cid in getattr(game, '_charm_rects', []):
                            if rect.collidepoint(mp):
                                game.camp_equip(cid)
                        for i, rect in enumerate(getattr(game, '_route_rects', [])):
                            if rect.collidepoint(mp):
                                game.camp_pick_route(i)

            # gamepad navigation for the upgrade/camp screens (mirrors the keyboard)
            nav.poll(joysticks, frame_dt)
            if game.state == 'levelup' and game.cards:
                if nav.left:
                    game.card_idx = max(0, game.card_idx - 1)
                if nav.right:
                    game.card_idx = min(len(game.cards) - 1, game.card_idx + 1)
                if nav.confirm:
                    game.choose_card(game.card_idx)
            elif game.state == 'camp' and game.camp:
                camp = game.camp
                if nav.up or nav.down:
                    camp['focus'] = 'shop' if camp.get('focus') == 'route' else 'route'
                if camp.get('focus') == 'shop':
                    if nav.left:
                        camp['shop_sel'] = max(0, camp['shop_sel'] - 1)
                    if nav.right:
                        camp['shop_sel'] = min(len(camp['shop']) - 1, camp['shop_sel'] + 1)
                    if nav.confirm:
                        game.camp_buy(camp['shop_sel'])
                else:
                    if nav.left:
                        camp['sel'] = max(0, camp['sel'] - 1)
                    if nav.right:
                        camp['sel'] = min(len(camp['routes']) - 1, camp['sel'] + 1)
                    if nav.confirm:
                        game.camp_pick_route(camp['sel'])
            elif game.state == 'over' and nav.confirm:
                game = Game(num, controllers, font, bigfont)

            keys = pygame.key.get_pressed()
            mouse_btn = pygame.mouse.get_pressed()
            for p in game.players:
                p.ctrl.poll(keys, mouse_btn, game.cam, p.pos)

            acc += frame_dt
            steps = 0
            while acc >= C.DT and steps < C.MAX_STEPS:
                game.step(C.DT)
                acc -= C.DT
                steps += 1
            game.cam.follow(game.players, frame_dt)

            game.draw(screen)
            display.present()

            if smoke and frames >= smoke:
                print(f"[smoke] {frames} frames ok  score={game.score} "
                      f"enemies={len(game.enemies)} friends={len(game.friends)} "
                      f"prey={len(game.prey)} pickups={len(game.pickups)}")
                pygame.quit(); return

    pygame.quit()


if __name__ == "__main__":
    main()
