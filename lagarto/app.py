"""Entry point: window setup, the menu -> match loop, and the fixed-timestep loop.

Simulation advances in fixed ``DT`` steps (frame-rate independent, deterministic,
online-friendly); rendering happens once per frame after catching up. ``--smoke N``
runs N frames and exits, for headless self-tests.
"""

import sys
import pygame

from . import audio
from . import config as C
from . import display
from . import fonts
from . import ui
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


def _camp_nav(game, left=False, right=False, up=False, down=False, confirm=False):
    """One camp navigation model for BOTH keyboard and gamepad.

    They used to disagree: the pad had a focus flip between shop/route while the
    keyboard arrows always drove the route, and charms were reachable by mouse
    only. Areas run top-to-bottom the way they are drawn.
    """
    camp = game.camp
    if not camp:
        return
    areas = ['shop', 'charms', 'route'] if game.camp_has_charms() else ['shop', 'route']
    if camp.get('focus') not in areas:
        camp['focus'] = 'route'
    if up or down:
        step = 1 if down else -1
        # inside the charm grid, up/down walks the column and only leaves at its ends
        if not (camp['focus'] == 'charms' and game.camp_move_charm(0, step)):
            i = areas.index(camp['focus'])
            camp['focus'] = areas[max(0, min(len(areas) - 1, i + step))]
    f = camp['focus']
    if f == 'shop':
        if left:
            camp['shop_sel'] = max(0, camp['shop_sel'] - 1)
        if right:
            camp['shop_sel'] = min(len(camp['shop']) - 1, camp['shop_sel'] + 1)
        if confirm:
            game.camp_buy(camp['shop_sel'])
    elif f == 'charms':
        if left:
            game.camp_move_charm(-1, 0)
        if right:
            game.camp_move_charm(1, 0)
        if confirm:
            game.camp_equip_cursor()
    else:
        if left:
            camp['sel'] = max(0, camp['sel'] - 1)
        if right:
            camp['sel'] = min(len(camp['routes']) - 1, camp['sel'] + 1)
        if confirm:
            game.camp_pick_route(camp['sel'])


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

    font = fonts.get(18)
    bigfont = fonts.get(32, bold=True)
    titlefont = fonts.get(62, bold=True)
    print(f"[fonte] usando '{fonts.name()}'")

    audio.init(sfx_vol=cfg['sfx_vol'], music_vol=cfg['music_vol'])

    joysticks = _init_joysticks()
    clock = pygame.time.Clock()
    nav = MenuNav()          # gamepad navigation for level-up / camp screens
    fade = ui.Fade()

    while True:
        if smoke:
            num, mode = 1, 'normal'
        else:
            chosen = run_menu(screen, font, bigfont, titlefont, joysticks)
            if chosen is None:
                break
            num, mode = chosen

        controllers = make_controllers(num, joysticks)
        game = Game(num, controllers, font, bigfont, mode=mode)
        fade.start(0.35)                     # fade in from the menu
        prev_state = game.state
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
                    if game.state in ('over', 'victory') and ev.key == pygame.K_RETURN:
                        game = Game(num, controllers, font, bigfont, mode=mode)
                    elif game.state == 'levelup' and not game.pick:
                        if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                            game.choose_card(ev.key - pygame.K_1)
                        elif ev.key in (pygame.K_LEFT, pygame.K_a):
                            game.card_idx = max(0, game.card_idx - 1)
                        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                            game.card_idx = min(len(game.cards) - 1, game.card_idx + 1)
                        elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                            game.choose_card(game.card_idx)
                    elif game.state == 'camp' and game.camp and not game.pick:
                        if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                            game.camp_buy(ev.key - pygame.K_1)
                        else:
                            _camp_nav(
                                game,
                                left=ev.key in (pygame.K_LEFT, pygame.K_a),
                                right=ev.key in (pygame.K_RIGHT, pygame.K_d),
                                up=ev.key in (pygame.K_UP, pygame.K_w),
                                down=ev.key in (pygame.K_DOWN, pygame.K_s),
                                confirm=ev.key in (pygame.K_RETURN, pygame.K_SPACE))
                if ev.type == pygame.MOUSEBUTTONDOWN and not game.pick:
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
            if game.pick:                    # a choice is being absorbed: hands off
                pass
            elif game.state == 'levelup' and game.cards:
                if nav.left:
                    game.card_idx = max(0, game.card_idx - 1)
                if nav.right:
                    game.card_idx = min(len(game.cards) - 1, game.card_idx + 1)
                if nav.confirm:
                    game.choose_card(game.card_idx)
            elif game.state == 'camp' and game.camp:
                _camp_nav(game, left=nav.left, right=nav.right, up=nav.up,
                          down=nav.down, confirm=nav.confirm)
            elif game.state in ('over', 'victory') and nav.confirm:
                game = Game(num, controllers, font, bigfont, mode=mode)

            keys = pygame.key.get_pressed()
            mouse_btn = pygame.mouse.get_pressed()
            for p in game.players:
                p.ctrl.poll(keys, mouse_btn, game.cam, p.pos)

            acc += frame_dt
            steps = 0
            if game.hitstop > 0:                 # freeze frames: draw but don't simulate
                game.hitstop -= frame_dt
                acc = min(acc, C.DT)
            while game.hitstop <= 0 and acc >= C.DT and steps < C.MAX_STEPS:
                game.step(C.DT)
                acc -= C.DT
                steps += 1
            game.cam.follow(game.players, frame_dt)

            boss = getattr(game.rounds, 'boss', None)
            if game.state == 'victory':
                audio.set_music('victory')
            elif game.state == 'camp':
                audio.set_music('calm')
            elif boss is not None and not boss.dead:
                audio.set_music('boss')          # dynamic track for boss rounds
            else:
                audio.set_music('combat')
            if game.state != prev_state:
                # play/level-up/camp animate themselves in and out (veil + dropdown +
                # absorption), so a blackout there would hide the impact we just built
                soft = ('play', 'levelup', 'camp')
                if not (prev_state in soft and game.state in soft):
                    fade.start(0.22)
                prev_state = game.state
            fade.update(frame_dt)
            game.draw(screen)
            fade.draw(screen)
            display.present()

            if smoke and frames >= smoke:
                print(f"[smoke] {frames} frames ok  score={game.score} "
                      f"enemies={len(game.enemies)} friends={len(game.friends)} "
                      f"prey={len(game.prey)} pickups={len(game.pickups)}")
                pygame.quit(); return

    pygame.quit()


if __name__ == "__main__":
    main()
