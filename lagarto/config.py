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
# Vida dos inimigos. Historico: 3.0 -> 2.2 (medicao) -> 3.5 (playtest do usuario,
# que manda). O bot headless media o TTK das ARMAS e concluiu 2.2; jogando de
# verdade quem mata e o dash + a rabada, que sao muito mais rapidos, entao a
# sensacao real era de inimigos de papel. Licao: o bot mede atrito, nao dificuldade.
# O preco de 3.5 e que jogar passivo fica ainda mais inviavel (ver CLAUDE.md,
# "Balanceamento 2a passada") -- a dificuldade continua vindo do dano, nao daqui.
ENEMY_HP_MULT = 3.5

# --- dano dos inimigos ----------------------------------------------------- #
# Sobe DANO, nao vida. Num jogo de ataque automatico a unica agencia do jogador e
# posicionamento, entao a dificuldade tem que ser consequencia de erro de posicao;
# vida a mais so vira esponja e ainda faz a build parecer mais fraca do que e.
ENEMY_DMG_BASE = 11          # era 8 fixo
ENEMY_DMG_SIZE = 0.5         # era 0.4 -- predador maior bate mais forte
# Escada por onda em DEGRAUS discretos: uma rampa continua o jogador nao percebe,
# um degrau ele sente ("a partir da onda 5 o corredor me machuca de verdade").
ENEMY_DMG_STEP = 4           # a cada N ondas sobe um degrau
ENEMY_DMG_PER_STEP = 2.0     # quanto sobe por degrau
ENEMY_PROJ_DMG = 10          # cuspe inimigo (era 8); lento e telegrafado -> da p/ desviar
# --- inimigos da fase 2 ---------------------------------------------------- #
# Bombardeiro (kamikaze). A regra do Mulliboom (Isaac): depois que o pavio acende
# ele DESACELERA e a explosao sai onde ele parar, entao andar embora sempre
# funciona. Uma carga que te persegue ate detonar nao e telegrafo, e so dano.
BOMBER_TRIGGER = 130     # distancia que acende o pavio
BOMBER_FUSE = 0.85       # >27 frames de aviso (250ms de reacao + duracao do dash)
BOMBER_RADIUS = 108
BOMBER_DMG = 26          # no centro; a borda da ~45% disso (falloff)
BOMBER_SPLASH = 4        # fogo amigo: bombardeiros afinam a propria horda

# Metralhador: pressao continua, nao pico. Dano baixo por tiro, rajada rapida.
GUNNER_BURST = 4         # tiros por rajada
GUNNER_BURST_GAP = 0.13  # intervalo dentro da rajada
GUNNER_RELOAD = 1.9      # respiro entre rajadas -> da pra quebrar a linha de tiro
GUNNER_DMG = 5
GUNNER_SPREAD = 7.0      # graus de dispersao

# Venenoso: negacao de area. Mira onde voce ESTA e a pocas cai la, entao quem
# pune e ficar parado -- empurra o jogador a se mover, sem ser um acerto direto.
VENOM_WINDUP = 0.5
VENOM_CD = 3.1
VENOM_SPIT_SPEED = 260
VENOM_SPIT_DMG = 6
VENOM_PUDDLE_R = 62
VENOM_PUDDLE_DMG = 7     # dano POR TICK (a poca tem cadencia propria), nao dps
VENOM_PUDDLE_TICK = 0.55
# Tem que ser MENOR que VENOM_CD, senao as pocas se sobrepoem e o dano empilha --
# e exatamente o bug do Acido, ja documentado e ja corrigido uma vez.
VENOM_PUDDLE_LIFE = 2.8

# --- inimigos da fase B4 (corpos procedurais novos) ------------------------- #
# CENTOPEIA (corpo 'segmented'): cavadora. Ataca o habito de ACAMPAR/andar reto --
# mergulha (intangivel), viaja por baixo ate um ponto que voce ve marcado no chao
# e ERUPCIONA la. Parada = ela sai embaixo de voce; movimento = voce sai do anel.
CENT_SURFACE_TIME = 2.6     # segundos cacando na superficie antes de mergulhar
CENT_DIG_TIME = 0.5         # telegrafo de MERGULHO: enraiza, cava um buraco, afunda
CENT_UNDER_TIME = 1.4       # teto de tempo submersa (erupcao forcada) -- e o telegrafo
CENT_ERUPT_DMG = 15         # dano do estouro ao aflorar (anel curto)
# POLVO (corpo 'tentacle'): agarrador. Ataca o habito de FICAR NO MEIO-ALCANCE /
# kitar de perto -- estica os bracos (telegrafo visivel), e no estalo te puxa para
# dentro e retarda. So funciona se voce estiver por perto: fugir cedo o nega.
OCTO_GRAB_RANGE = 190      # dentro disso ele arma o agarrao
OCTO_WINDUP = 0.75         # telegrafo: bracos convergem/esticam (>27 frames)
OCTO_CD = 2.4              # respiro entre agarroes
OCTO_PULL_DIST = 120       # o quanto voce e puxado
OCTO_SLOW_MUL = 0.5
OCTO_SLOW_TIME = 0.8
OCTO_GRAB_SHOW = 0.25      # quadros mostrando o braco fisgado

# --- itens (items.py) ------------------------------------------------------- #
# Qualidade 0-4 no molde do Isaac: enviesa a chance de ser oferecido, nao trava.
# Um item forte pode existir sem ser comum; um fraco pode existir sem ser cilada.
ITEM_QUALITY_WEIGHT = (2.2, 1.6, 1.0, 0.6, 0.3)
ITEM_CHARGE_KILLS = 14   # abates para carregar o ativo (liga o recurso ao combo)

ITEM_PULSO_R = 190
ITEM_PULSO_DMG = 14
ITEM_PULSO_KNOCK = 520
ITEM_MUDA_TIME = 1.1     # segundos de invulnerabilidade da muda de pele
ITEM_CHAMADO_COUNT = 3
ITEM_FERRAO_COUNT = 8
ITEM_FERRAO_DMG = 6

# passivos de mecanica
ITEM_TRAIL_R = 44        # raio do rastro corrosivo do dash
ITEM_TRAIL_DMG = 5       # dano por tick da poca (a poca tem cadencia propria)
ITEM_TRAIL_LIFE = 1.6
ITEM_TRAIL_DROP = 0.07   # espacamento entre pocas do rastro
ITEM_CASULO_TIME = 0.45  # i-frames extras do Casulo ao levar dano
ITEM_KILL_BLAST_R = 92
ITEM_KILL_BLAST_DMG = 7
ITEM_KILL_HEAL = 1.5
ITEM_MAGNET_R = 260
ITEM_THROW_SPEED = 900   # arremesso da lingua
ITEM_ADRENALINE_HP = 0.35   # abaixo desta fracao de vida...
ITEM_ADRENALINE_MULT = 1.6  # ...o dano sobe isto
ITEM_DRAIN = 4.0         # vida drenada pela lingua por acerto
ITEM_DART_DMG = 5        # farpas disparadas pela rabada
ITEM_DART_COUNT = 5      # quantas farpas por golpe
ITEM_DART_SPREAD = 16    # graus entre farpas
ITEM_DART_SPEED = 520
ITEM_SPIRAL_MULT = 2.4   # multiplica a varredura da rabada (Cauda em Espiral)
ITEM_MAGNET_PULL = 420   # velocidade com que o ima puxa coletaveis (px/s)
ITEM_SPREAD_R = 130      # alcance do contagio

# Synergy Factor (Gungeon): multiplica o PESO de uma carta que avanca uma
# sinergia. E anti-frustracao -- o jogo conspira para a sua build fechar em vez
# de pendurar meia sinergia pelo resto da run. Nao e sistema novo: roll_cards ja
# escolhia por peso.
SYNERGY_FACTOR_CLOSE = 3.2   # esta carta COMPLETA uma sinergia
SYNERGY_FACTOR_START = 1.4   # esta carta comeca uma

# --- personagens jogaveis (characters.py) ----------------------------------- #
CHAR_LAGARTO_REROLLS = 1        # rerrolagens da mao de cartas, por ROUND

CHAR_VIBORA_WEAPON_CAP = 2      # o teto E a mecanica: com 6 armas o rabo e bonus,
                                # com 2 ele e o seu dano e voce tem que golpear
CHAR_VIBORA_WHIP_CD = 0.42      # multiplicador da recarga da rabada
CHAR_VIBORA_WHIP_MULT = 2.4     # multiplicador do dano da rabada
CHAR_VIBORA_HP = 0.7            # fragil: ficar no alcance do rabo tem que custar

CHAR_COURACADO_ARMOR = 0.3      # tirar o dash e invasivo -> pago tres vezes:
CHAR_COURACADO_THORNS = 2       # armadura, dano de contato e imunidade a empurrao
CHAR_COURACADO_HP = 1.45

CHAR_LARVA_HP = 0.62            # comeca indefesa de verdade
CHAR_LARVA_KILLS_PER_STEP = 12  # abates por degrau de crescimento
CHAR_LARVA_SIZE_STEP = 1.13     # cada degrau multiplica o tamanho
CHAR_LARVA_MAX_SIZE = 1.75
CHAR_LARVA_HP_STEP = 14
CHAR_LARVA_MAX_SLOTS = 6

# --- campeoes (champions.py) ------------------------------------------------ #
# Chance sobe com a onda, no formato do Isaac (~5% cedo, ~20% tarde). Vida dos
# campeoes fica MODESTA de proposito: campeao e ameaca pelo que FAZ; um que so
# tem mais vida nao ensina nada e vira pedagio.
CHAMP_CHANCE_BASE = 0.05
CHAMP_CHANCE_PER_WAVE = 0.012
CHAMP_CHANCE_MAX = 0.22
CHAMP_MODIFIER_CHANCE = 0.28   # variante que ainda ganha um modificador em cima

# Velocidade ABSOLUTA do filhote (jogador ~224, dash ~672): mais rapido que andar,
# mais lento que um dash. Ele te alcanca se voce so caminhar, e voce escapa se
# usar o dash -- e o que torna "minusculo e veloz" uma ameaca justa e nao um golpe
# inevitavel. Relativo nao serve: um filhote de tanque sairia mais lento que voce.
CHAMP_FILHOTE_SPEED = 440
CHAMP_ALFA_RANGE = 360   # alcance do chamado e da deteccao
CHAMP_ALFA_CD = 4.5
CHAMP_ALFA_TIME = 3.0    # duracao do frenesi nos aliados
CHAMP_ALFA_SPEED = 1.35
CHAMP_ESPECTRO_REVEAL = 330   # distancia em que a camuflagem se desfaz
CHAMP_SALTADOR_RANGE = 420
CHAMP_SALTADOR_CD = 2.4
CHAMP_SALTADOR_POWER = 3.1
CHAMP_ARMOR = 0.6        # fracao bloqueada de frente (por tras leva normal)
CHAMP_SPLIT_SIZE = 0.62  # DIVISOR: tamanho de cada cria (do pai) -- Blobulon/Fistula
CHAMP_SPLIT_HP = 0.5     # vida de cada cria (fracao da max_hp do pai)

# Ferrao (escorpiao/envenenador): TEM que durar menos que o attack_cd de 0.8s de
# quem o aplica, senao a lentidao e permanente por construcao -- foi o terceiro
# bug desta mesma forma no projeto (Acido, poca de veneno, agora o ferrao).
STING_SLOW = 0.7         # 30% mais lento (era 50%, e invisivel demais para tanto)
STING_SLOW_TIME = 0.4    # << attack_cd (0.8): uptime ~50%, nao ~75%

CRIT_MULT = 2.0          # dano ao acertar a cabeca (ponto fraco)
AGGRO_TIME = 5.0         # segundos que um aliado segura o aggro apos bater
FRIEND_LIFE = 45.0       # aliados sao temporarios (segundos)

# --- acampamento FISICO (clareira estilo Hades: barraca + 3 portas) --------- #
CAMP_TENT_R = 66         # encostar a esta distancia da barraca abre a loja
CAMP_DOOR_R = 52         # atravessar a esta distancia de uma porta avanca a onda
CAMP_REOPEN_CD = 0.7     # respiro apos fechar a loja (nao reabre no mesmo passo)
CAMP_TENT_OFF = (-260, 40)     # posicao da barraca relativa ao centro da clareira
CAMP_DOOR_SPAN = 285     # espacamento entre as 3 portas
CAMP_DOOR_UP = 215       # o quanto as portas ficam "a frente" (para cima) do centro
# a barraca e as portas CAEM do ceu ao entrar no acampamento (juice: shake + poeira)
CAMP_DROP_H = 900        # altura inicial (mundo) de onde tudo despenca -- fora da tela
CAMP_DROP_DUR = 0.40     # duracao da queda de cada peca
CAMP_TENT_DELAY = 0.12   # a barraca cai primeiro
CAMP_DOOR_DELAY = 0.30   # 1a porta; as outras escalonam por CAMP_DOOR_STAGGER
CAMP_DOOR_STAGGER = 0.14

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

# Dano de UM dash (antes o dash reaplicava 3 por frame = ~30 por investida).
# Mesmo tratamento da rabada: base menor + escala com `might`, porque 5 fixo era
# igual na onda 1 e na onda 20. Membranas ja melhorava velocidade/duracao/custo
# do dash mas NAO o dano, apesar de a carta prometer "dash mais forte" -- agora
# `DASH_WINGS_MULT` cumpre a promessa e da ao dash o mesmo par base+upgrade que a
# cauda tem com a clava.
#   nu ............... 4  (critico 8)
#   + membranas ...... 6  (critico 12)
#   + membranas e 3 Vigor  10 (critico 21)
DASH_DAMAGE = 4
DASH_WINGS_MULT = 1.5

# Colisao macia: atravessar inimigo custa velocidade em vez de te empurrar.
# Medido antes: um pastador (inofensivo!) a 30px te deixava a 49% da velocidade, e
# UM corredor ja saturava o efeito -- ou seja, era liga-desliga, nao gradiente.
# Hoje so INIMIGOS arrastam (collision.DRAGS_PLAYER) e a saturacao exige estar
# enterrado em ~3 corpos.
CONTACT_DRAG = 0.35      # freio maximo, quando totalmente enterrado
CONTACT_FULL = 3.0       # quantos corpos sobrepostos equivalem a "atolado de vez"

# pressionada fica valida por este tempo: sobrevive a frames sem passo de simulacao
# (jitter e hit-stop) e a um clique pouco antes do cooldown acabar
INPUT_BUFFER = 0.15

DASH_COST = 14
TONGUE_COST = 8
KILL_ENERGY = 4      # energia devolvida ao abater (sustenta o combo agressivo)

# rabada: golpe de cauda. A clava aumenta o dano e o empurrao; o ferrao envenena.
# Curvatura TOTAL da cauda no auge, distribuida entre as juntas (peso quadratico
# rumo a ponta). Nao e o giro de um bloco: aplicar tudo na primeira junta vira
# dobradica. O golpe faz um periodo inteiro -> varre os dois lados numa so vez.
WHIP_SWEEP = 150
WHIP_TIME = 0.68         # duracao do golpe (dois lados cabem aqui). Mais lento le
                         # melhor: da peso e da tempo de ver a cauda passar.
WHIP_COST = 10
# A cauda NUA e fraca de proposito: sem upgrade ela vale pelo empurrao e pelo
# controle de espaco, nao pelo dano. O dano de verdade vem dos modificadores.
# Antes era 5 fixo e NAO escalava com nada (`might` so era lido pelas armas), ou
# seja a rabada era identica na onda 1 e na onda 20: dominava cedo e sumia tarde.
# Hoje `_whip_hit` multiplica por `player.might`, entao Vigor (+20%/carta) e
# Potencia (DNA, +6%/nivel) finalmente melhoram o golpe.
#   nua .............. 2   (critico 4)
#   + cauda-clava .... 5,2 (critico 10,4)
#   + clava e 3 Vigor  9   (critico 18)
WHIP_DAMAGE = 2
# 2.6 -> 2.3: retoque leve na escala ("dano subindo rapido demais"). O corte
# maior veio da area (7 -> 2-3 alvos por golpe); a clava continua sendo O upgrade
# da cauda, so um pouco menos ingreme.
WHIP_CLUB_MULT = 2.3
# Hitbox da rabada: so as juntas da PONTA (nao a metade que anima) e alcance
# menor -- a area cheia acertava ~7 de 12 num circulo, "matava a sala inteira".
WHIP_HIT_JOINTS = 3      # quantas juntas do final ferem
WHIP_REACH = 1.05        # x max_r (era 1.6)
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
