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
ENEMY_HP_MULT = 3.0      # dial unico de dificuldade: vida dos inimigos
CRIT_MULT = 2.0          # dano ao acertar a cabeca (ponto fraco)
AGGRO_TIME = 5.0         # segundos que um aliado segura o aggro apos bater
FRIEND_LIFE = 45.0       # aliados sao temporarios (segundos)

# --- ritmo das telas de jogo (level-up / acampamento) ---------------------- #
UI_VEIL = 0.20           # fade do fundo escuro antes de qualquer conteudo
UI_STAGGER = 0.075       # atraso entre um item e o proximo no dropdown
UI_DROP = 0.30           # duracao da queda de cada item
UI_READY = 0.36          # so aceita escolha depois disso (evita clique acidental)
# slots de charm na ordem em que aparecem no acampamento (colunas da grade)
CHARM_SLOTS = (('head', 'CABECA'), ('back', 'COSTAS'), ('tail', 'CAUDA'))
# absorcao da escolha pelo jogador: centraliza -> segura -> voa pro lagarto
PICK_CENTER = 0.40       # chega ao centro da tela
PICK_HOLD = 0.56         # fica parado no centro ate aqui (da tempo de ler)
PICK_END = 0.86          # atinge o jogador -> efeito aplicado
PICK_ROUTE_END = 0.50    # rotas: versao curta (so expande e avanca)

# dano de UM dash (antes o dash reaplicava 3 por frame = ~30 por investida)
DASH_DAMAGE = 5

# colisao macia: atravessar inimigo custa ate 55% da velocidade em vez de te empurrar
CONTACT_DRAG = 0.55

# pressionada fica valida por este tempo: sobrevive a frames sem passo de simulacao
# (jitter e hit-stop) e a um clique pouco antes do cooldown acabar
INPUT_BUFFER = 0.15

DASH_COST = 14
TONGUE_COST = 8

# rabada: golpe de cauda. A clava aumenta o dano e o empurrao; o ferrao envenena.
# Curvatura TOTAL da cauda no auge, distribuida entre as juntas (peso quadratico
# rumo a ponta). Nao e o giro de um bloco: aplicar tudo na primeira junta vira
# dobradica. O golpe faz um periodo inteiro -> varre os dois lados numa so vez.
WHIP_SWEEP = 150
WHIP_TIME = 0.68         # duracao do golpe (dois lados cabem aqui). Mais lento le
                         # melhor: da peso e da tempo de ver a cauda passar.
WHIP_COST = 10
# Depois que o golpe passou a mover a CAUDA (e nao o jogador), ele so alcanca o
# arco atras/ao lado -- medido 1-2 alvos por golpe, nao 4-5. Entao o dano por
# acerto voltou para perto do dash; o que paga a diferenca e o cooldown maior.
WHIP_DAMAGE = 5
WHIP_CLUB_MULT = 1.6     # dano com cauda-clava (3 -> 4.8, critico ~10)
WHIP_KNOCK = 170         # empurrao base (a clava usa WHIP_KNOCK_CLUB)
WHIP_KNOCK_CLUB = 460
# A simulacao e fixa em SIM_HZ e o desenho NAO interpola entre estados, entao
# renderizar acima de SIM_HZ so redesenha frames identicos: era 120, ou seja 2x o
# custo de draw + smoothscale + flip (a GPU ficava em 100%) por zero ganho visual.
RENDER_FPS = SIM_HZ

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
COL_POLLEN  = (250, 214, 90)     # moeda da run (bolsa no camp, particulas de compra)
COL_WHITE   = (250, 250, 255)
COL_INK     = (16, 14, 26)
COL_HUD     = (240, 240, 252)
