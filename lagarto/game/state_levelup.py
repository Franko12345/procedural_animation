"""State 'levelup': the card panel and the absorption animation.

The absorption machinery (``_start_pick`` .. ``_finish_pick``) lives here
because the level-up card is what it was built for, but the camp drives it too
for purchases and routes -- ``state_camp`` imports it from here.
"""

import pygame
from pygame import Vector2

from ..audio import engine as audio
from ..core import config as C
from ..core import palette
from ..core.mathutil import clamp, ease_out, lerp
from ..render import icons
from ..render import ui


def update(game, dt):
    # ui_t / ui_fx / fx are the shared UI clock and are ticked by Game.step
    if game.pick:
        _step_pick(game, dt)


# ---- choosing: pick -> absorption animation -> effect --------------------- #
def _start_pick(game, kind, index, rect, color, dur, item=None):
    game.pick = dict(kind=kind, index=index, item=item, color=color,
                     rect=pygame.Rect(rect), t=0.0, dur=dur, sparked=False)
    audio.play('ui')
    game.punch(freeze=0.0, shake=3)      # small kick as it leaves the slot
    if kind == 'shop':
        # the pollen you just spent bursts out of the stall
        slot = game.cam.s2w(rect.center)
        game.fx.burst(slot, C.COL_POLLEN, 18, 260)
        game.fx.spark_burst(slot, palette.lighten(C.COL_POLLEN, 0.35), 14, 340)
        game.fx.burst(slot, color, 14, 200)
        game.fx.ring(slot, C.COL_POLLEN)


def _pick_player(game):
    return game.levelup_player or (game.players[0] if game.players else None)


def _pick_pose(game):
    """Where the chosen item is *right now*: (screen pos, scale, alpha)."""
    pk = game.pick
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
    p = _pick_player(game)
    tgt = Vector2(game.cam.w2s(p.pos)) if p else mid
    return mid.lerp(tgt, f), lerp(1.22, 0.10, f), lerp(1.0, 0.4, f)


def _step_pick(game, dt):
    pk = game.pick
    pk['t'] += dt
    if pk['kind'] != 'route':
        pos = game.cam.s2w(_pick_pose(game)[0])
        shop = pk['kind'] == 'shop'
        if pk['t'] >= C.PICK_HOLD:        # comet trail on the way to the player
            game.fx.trail(pos, pk['color'])
            if shop:                      # purchases fly in a thicker, golden comet
                game.fx.trail(pos, C.COL_POLLEN)
                game.fx.spark_burst(pos, C.COL_POLLEN, 2, 150)
        elif shop and pk['t'] < C.PICK_CENTER:
            # sparkles while it drifts up out of the stall
            game.fx.trail(pos, C.COL_POLLEN)
    if pk['t'] >= pk['dur']:
        _finish_pick(game)


def _finish_pick(game):
    """Impact: the choice lands *in* the player -- only now does it take effect."""
    pk = game.pick
    game.pick = None
    game.ui_fx = 1.1          # the impact burst must survive the veil too
    p = _pick_player(game)
    if p is not None and pk['kind'] != 'route':
        game.fx.burst(p.pos, pk['color'], 26, 260)
        game.fx.spark_burst(p.pos, palette.lighten(pk['color'], 0.4), 18, 380)
        game.fx.ring(p.pos, pk['color'])
        game.fx.ring(p.pos, palette.lighten(pk['color'], 0.5))
        game.punch(freeze=0.09, shake=12, flash=0.10)
        audio.play('evolve')
        if pk['kind'] == 'shop':
            # a purchase lands with a golden pop on top of the item's own colour
            game.fx.burst(p.pos, C.COL_POLLEN, 30, 320)
            game.fx.spark_burst(p.pos, C.COL_POLLEN, 24, 460)
            game.fx.spark_burst(p.pos, C.COL_WHITE, 10, 260)
            game.fx.ring(p.pos, C.COL_POLLEN)
            if pk['item']:
                game.fx.popup(p.pos, pk['item']['name'], C.COL_POLLEN)
            audio.play('buy')
    if pk['kind'] == 'card':
        game._apply_card(pk['item'])
    elif pk['kind'] == 'shop':
        game._apply_buy(pk['index'])
    elif pk['kind'] == 'route':
        game._apply_route(pk['index'])


# ---- the card panel ------------------------------------------------------ #
def _card_surface(game, card, i, sel):
    """One level-up card, drawn at the origin so it can be moved/scaled freely."""
    cw, ch = 240, 300
    s = pygame.Surface((cw, ch), pygame.SRCALPHA)
    box = pygame.Rect(0, 0, cw, ch)
    pygame.draw.rect(s, (30, 32, 52), box, border_radius=16)
    edge = card.color if sel else (70, 72, 96)
    pygame.draw.rect(s, edge, box, 4 if sel else 2, border_radius=16)
    icons.draw(s, getattr(card, 'icon', None), (cw // 2, 70), 30, card.color)
    name = game.bigfont.render(card.name, True, C.COL_WHITE)
    if name.get_width() > cw - 20:
        name = game.font.render(card.name, True, C.COL_WHITE)
    s.blit(name, (cw // 2 - name.get_width() // 2, 130))
    for li, line in enumerate(ui.wrap(game.font, card.desc, cw - 30)):
        im = game.font.render(line, True, (200, 200, 216))
        s.blit(im, (cw // 2 - im.get_width() // 2, 180 + li * 24))
    key = game.font.render(f"[{i + 1}]", True, card.color)
    s.blit(key, (cw // 2 - key.get_width() // 2, ch - 34))
    return s


def draw(game, surf):
    f = game._veil(surf, (8, 10, 20), 200)
    layer = game._ui_dest(surf)
    # heading rides in with the veil, before the cards
    toff, talpha = ui.drop_in(game.ui_t, 0, 0.0, C.UI_VEIL, rise=22.0)
    if talpha > 0.01:
        title = game.bigfont.render("EVOLUIR", True, C.COL_WHITE)
        hint = "escolha uma mutacao  -  1/2/3, setas+ENTER ou clique"
        p = game.levelup_player
        if p is not None and p.rerolls > 0:
            hint += f"   [R] rerrolar ({p.rerolls})"
        sub = game.font.render(hint, True, (190, 190, 210))
        for im, ty in ((title, 96), (sub, 140)):
            im = im.copy()
            im.set_alpha(int(255 * talpha))
            layer.blit(im, (C.WIDTH // 2 - im.get_width() // 2, int(ty + toff)))

    n = len(game.cards)
    cw, ch, gap = 240, 300, 34
    total = n * cw + (n - 1) * gap
    x0 = C.WIDTH // 2 - total // 2
    y = C.HEIGHT // 2 - ch // 2 + 20
    game._card_rects = []
    chosen = game.pick if (game.pick and game.pick['kind'] == 'card') else None
    for i, card in enumerate(game.cards):
        rect = pygame.Rect(x0 + i * (cw + gap), y, cw, ch)
        game._card_rects.append(rect)
        sel = (i == game.card_idx) or (chosen is not None and chosen['index'] == i)
        src = game._panel(('card', i, sel), lambda c=card, i=i, s=sel:
                          _card_surface(game, c, i, s))
        if chosen is None:
            off, alpha = ui.drop_in(game.ui_t, i, C.UI_STAGGER, C.UI_DROP, rise=46.0)
            game._blit_card(layer, src, (rect.centerx, rect.centery + off),
                            1.0, alpha)
        elif chosen['index'] != i:
            # the ones you didn't take shrink away
            g = clamp(chosen['t'] / 0.18, 0, 1)
            game._blit_card(layer, src, rect.center, 1.0 - 0.25 * g, 1.0 - g)
    if chosen is not None:
        pos, scale, alpha = _pick_pose(game)
        ci = chosen['index']
        src = game._panel(('card', ci, True),
                          lambda: _card_surface(game, game.cards[ci], ci, True))
        palette.glow(layer, (int(pos.x), int(pos.y)), int(120 * scale + 30),
                     chosen['color'], 0.30 + 0.30 * (1 - alpha))
        game._blit_card(layer, src, pos, scale, alpha)
    game._ui_fx(layer)
    game._blit_ui(surf, layer)
    return f
