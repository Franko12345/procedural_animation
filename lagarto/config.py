"""Global configuration: window/world sizes, timing and the colour palette.

Keeping every tunable in one module makes balancing and re-theming a one-file job.
"""

import math

# --- window / world -------------------------------------------------------- #
WIDTH, HEIGHT = 1120, 720
WORLD_W, WORLD_H = 3200, 3200

# --- timing (fixed simulation step, render decoupled) ---------------------- #
SIM_HZ = 60
DT = 1.0 / SIM_HZ
MAX_STEPS = 5            # cap sim steps per frame -> avoids the "spiral of death"

# --- ability energy costs (shared by the logic and the HUD dials) ---------- #
RUN_FINAL_WAVE = 20      # modo normal: onda do chefe final (vitoria)

FRIEND_HP = 6            # aliados agora tomam dano de verdade -> precisam aguentar
ENEMY_HP_MULT = 2.0      # dial unico de dificuldade: vida dos inimigos
CRIT_MULT = 2.0          # dano ao acertar a cabeca (ponto fraco)
AGGRO_TIME = 5.0         # segundos que um aliado segura o aggro apos bater
FRIEND_LIFE = 45.0       # aliados sao temporarios (segundos)

DASH_COST = 14
TONGUE_COST = 8
RENDER_FPS = 120

TAU = math.tau

# --- palette: VIVID, saturated, cartoonish (dark ground -> glow pops) ------- #
COL_BG      = (16, 14, 30)                          # void / behind the world
COL_BG2     = (26, 24, 50)
COL_DOT     = (48, 46, 84)
COL_PLAYER  = [(78, 236, 126), (54, 200, 116)]     # P1 vivid green
COL_PLAYER2 = [(72, 212, 255), (52, 176, 236)]     # P2 vivid cyan
COL_ENEMY   = (255, 72, 88)
COL_PREY    = (255, 210, 64)
COL_FRIEND  = (168, 120, 255)
COL_BUG     = (255, 96, 224)
COL_FRUIT   = (255, 122, 66)
COL_EGG     = (245, 245, 224)
COL_WHITE   = (250, 250, 255)
COL_INK     = (16, 14, 26)
COL_HUD     = (240, 240, 252)
