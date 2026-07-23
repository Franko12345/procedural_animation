"""States 'over' and 'victory': the two run-summary screens.

They share a state module because they are the same beat -- the run is finished,
the DNA is banked, ENTER restarts and ESC goes back to the menu.
"""

import pygame

from ..core import config as C
from ..core import palette
from ..core.mathutil import pulse
from ..flow import progression


def update(game, dt):
    """No-op: the run is over and nothing simulates. The shared UI clock in
    Game.step still advances ui_t / ui_fx / fx for the lingering particles."""


def draw(game, surf):
    if game.state == 'victory':
        _draw_victory(game, surf)
    else:
        _draw_over(game, surf)


def _draw_victory(game, surf):
    """Run beaten: celebratory summary + the DNA banked (endless now unlocked)."""
    ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    ov.fill((8, 22, 16, 190))
    surf.blit(ov, (0, 0))
    cx = C.WIDTH // 2
    palette.glow(surf, (cx, 190), 300, (120, 250, 170), 0.28 + 0.16 * pulse(game.time, 3))
    t = game.bigfont.render("VITORIA!", True, (150, 255, 190))
    surf.blit(t, (cx - t.get_width() // 2, 158))
    sub = game.font.render(f"voce derrotou o chefe primordial na onda {game.rounds.wave}",
                           True, (206, 236, 220))
    surf.blit(sub, (cx - sub.get_width() // 2, 214))

    rows = [
        ("score", f"{game.score}"),
        ("abates", f"{game.kills}"),
        ("nivel", f"{game.players[0].level}"),
        ("armas", f"{len(game.players[0].weapons)}"),
    ]
    y = 268
    for label, val in rows:
        li = game.font.render(label, True, (168, 200, 184))
        vi = game.bigfont.render(val, True, C.COL_WHITE)
        surf.blit(li, (cx - 150, y + 8))
        surf.blit(vi, (cx + 150 - vi.get_width(), y))
        y += 46

    gained = getattr(game, 'dna_gained', 0)
    d = game.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
    surf.blit(d, (cx - d.get_width() // 2, y + 14))
    bonus = game.font.render(f"(inclui bonus de vitoria +{progression.WIN_BONUS})",
                             True, (150, 210, 180))
    surf.blit(bonus, (cx - bonus.get_width() // 2, y + 58))
    unl = game.font.render("MODO INFINITO DESBLOQUEADO no menu", True, (245, 220, 120))
    surf.blit(unl, (cx - unl.get_width() // 2, y + 88))
    h = game.font.render("Enter/A: jogar de novo     Esc/B: voltar ao menu", True, (200, 214, 206))
    surf.blit(h, (cx - h.get_width() // 2, y + 124))


def _draw_over(game, surf):
    ov = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    ov.fill((10, 8, 20, 180))
    surf.blit(ov, (0, 0))
    t = game.bigfont.render("FIM DE JOGO", True, C.COL_ENEMY)
    surf.blit(t, (C.WIDTH // 2 - t.get_width() // 2, C.HEIGHT // 2 - 80))
    s = game.bigfont.render(f"Score {game.score}", True, C.COL_HUD)
    surf.blit(s, (C.WIDTH // 2 - s.get_width() // 2, C.HEIGHT // 2 - 24))
    # run summary + DNA banked
    cy = C.HEIGHT // 2 + 22
    line = game.font.render(
        f"onda {game.rounds.wave}   abates {game.kills}   nivel {game.players[0].level}",
        True, (198, 200, 220))
    surf.blit(line, (C.WIDTH // 2 - line.get_width() // 2, cy))
    gained = getattr(game, 'dna_gained', 0)
    d = game.bigfont.render(f"+{gained} DNA", True, (140, 240, 170))
    surf.blit(d, (C.WIDTH // 2 - d.get_width() // 2, cy + 30))
    tot = game.font.render(f"DNA total: {game.meta['dna']}   (gaste no menu > EVOLUCAO)",
                           True, (170, 210, 185))
    surf.blit(tot, (C.WIDTH // 2 - tot.get_width() // 2, cy + 76))
    h = game.font.render("Enter/A: jogar de novo     Esc/B: voltar ao menu", True, (200, 200, 220))
    surf.blit(h, (C.WIDTH // 2 - h.get_width() // 2, cy + 110))
