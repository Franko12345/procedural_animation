# CLAUDE.md — Lagarto (jogo com animação procedural)

Contexto permanente do projeto para agentes. Leia antes de mexer no código.

## O que é

Jogo em **pygame** onde você controla um **lagarto animado 100% proceduralmente**
(sem sprites/quadros de animação). Mistura **exploração/coleta** com
**caça/combate por dash**, em um mundo aberto com biomas. Suporta **singleplayer
(experiência completa)** e **coop local de 2 jogadores** na mesma tela.

Origem: evoluído de `procedural_animation.py` (uma "cobra" de cadeia
follow-the-leader). Esse arquivo e `pygamebase.py` ficam **intactos como referência**.

## Como rodar

```bash
python lizard_game.py             # jogar (abre o menu)
python lizard_game.py --smoke 90  # self-test headless: roda N frames e sai
```
```bash
python build.py                   # gera executavel unico em dist/ (precisa pyinstaller)
```
**Windows:** o PyInstaller **não faz cross-compile**. Rode o `build.py` no Windows, ou use
o CI: `.github/workflows/build.yml` compila **Windows + Linux** a cada push e anexa os
binários a um Release quando você empurra uma tag `v*`.
Dependências (`requirements.txt`): **`pygame-ce`** (community edition — mesma API e já
traz o `mixer`, necessário p/ som), `numpy` (numpy = **síntese de áudio**; os
loops quentes usam `math` + `pygame.Vector2`). Teste headless: prefixe
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`. **A invariante "zero assets" foi
quebrada de propósito na Fase 7** (`assets/` + `lagarto/assets.py`): ícones de
armas/mutações/charms agora preferem um PNG pixel art quando existe, com
fallback para o desenho procedural de sempre (`icons.draw`) — uma build sem a
pasta `assets/` (ou um id sem PNG) roda idêntica, então som/música seguem 100%
sintetizados e o resto da arte (corpo do lagarto, mundo, partículas) continua
gerado em código.

## Arquitetura (pacote `lagarto/`)

Um módulo por responsabilidade — mantenha assim; não volte para arquivo único.

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Constantes (janela/mundo, timing, **paleta vívida**, custos de energia). Ajuste de cores/balanço começa aqui. |
| `display.py` | **Surface lógica fixa** + escala 1x/2x/3x + tela cheia com letterbox; `present()` faz smoothscale; `to_logical(pos)` mapeia o mouse (essencial p/ cliques). |
| `settings.py` | `~/.lagarto/settings.json` (tela cheia/escala/vsync/volumes). Tolerante a arquivo corrompido. |
| `fonts.py` | Escolhe a melhor fonte instalada (Noto Sans etc.) com cache por tamanho. |
| `ui.py` | Kit visual: `panel`, `chip`, `list_menu`, `tabs`, `paragraph`, `footer`, `fit`, `Fade` e **`drop_in`** (entrada escalonada — use em toda tela nova). |
| `icons.py` | **Ícones procedurais** (armas/mutações/charms) desenhados em código — usados em cartas, HUD, loja, charms e compêndio. |
| `audio.py` | **Som sintetizado com numpy**: 12 SFX + 3 trilhas generativas (calma/combate/chefe). Degrada p/ mudo se não houver mixer. |
| `mathutil.py` | Helpers de vetor/ângulo (`math` + `Vector2`, **não numpy** nos loops quentes). |
| `palette.py` | Cor HSV (`vibrant`, `random_in_family`), lighten/darken/mix, e **glow aditivo cacheado** (`glow`, `BLEND_RGB_ADD`) p/ o rim/brilho. |
| `genome.py` | **`Genome`**: criatura = números (tamanho, nº de pernas, olhos, chifres, cauda, cor HSV, hp, behavior, diet). Núcleo (RujiK). `random_variation` p/ variedade. |
| `spine.py` | `Spine`: cadeia follow-the-leader + limite de curvatura; polígono do corpo (`body_polygon`, cabeça/cauda arredondadas). |
| `leg.py` | `Leg`: foot-planting (limiar + arco) + **IK de 2 ossos**. Suporta modo **radial** (aranha) via `rest_angle`. |
| `parts.py` | Desenho de partes pelo genoma: espinhos, chifres, placas, cauda (clava/ferrão), nadadeiras. Reusado por inimigos e evolução. |
| `lizard.py` | `Lizard` (base construída **do genoma**: espinha + N pernas pareadas/radiais + partes + status slow), `Player` (XP/nível/`grant_part`/energia/dash/língua), `AILizard` (prey/enemy/friend + behaviors chase/ranged/lunge/hop + poison). |
| `species.py` | **Genomas-template** + metadados (role, xp, score, `grants`, `diet`). `make()` spawna variação. Roster: grazer/critter/frog/fish (presa), runner/tank/snake/horned/spiky/spider/spitter/scorpion + **wasp/bomber/gunner/venomer** + **centipede/octopus** (inimigo). |
| `characters.py` | **Personagens jogáveis**: 4 genomas + modificadores de identidade + uma mecânica exclusiva cada. |
| `items.py` | **Itens**: 4 **ativos** (botão E, carga por abate) + 16 **passivos que mudam mecânica**. Qualidade 0-4 + pools por origem (level/shop/nest/boss). |
| `champions.py` | **Campeões**: variantes nomeadas (modelo Rain World) + modificadores empilháveis. `maybe_promote` no spawn, chance crescente por onda. |
| `evolution.py` | **Cartas de mutação** (`MUTATIONS`: stats + partes) + `roll_cards` + **sinergias nomeadas** (`SYNERGIES`, ex.: ARACNIDEO=legs+venom, FORTALEZA=plates+thorns). |
| `projectile.py` | `Projectile` (cuspe de veneno, teia de slow, tiro de chefe). Helpers `spit`/`web`. |
| `pickups.py` | `Bug` (skitter/foge), `Fruit` (cura), `Egg` (choca um amigo). Todos com glow. |
| `world.py` | `World`: chão em **biomas vívidos** (tiles com blend suave), **água com shimmer**, flora procedural que balança, pólen com glow. Culling. |
| `fx.py` | Partículas (pool, cap) **com glow**, **sparks** (polígonos que esticam pela velocidade — DaFluffyPotato), anéis, texto flutuante, sombras. |
| `camera.py` | `Camera`: segue 1 jogador ou enquadra 2; screen shake; `w2s`/`s2w`. |
| `collision.py` | **Separação** de corpos: amostra pontos ao longo das espinhas + spatial hash → criaturas não se atravessam. |
| `controllers.py` | Abstração de input: `KeyboardMouseController`, `KeyboardController`, `GamepadController`. |
| `game.py` | `Game`: mundo, spawns por espécie, ondas, projéteis, colisões, XP/evolução, HUD, vinheta, game over. |
| `menu.py` | **Hub**: jogar (1/2), opções (tela cheia/escala/vsync/volumes), controles, **bestiário** (criatura procedural viva + lore) e **compêndio** (armas/evoluções/charms), tudo navegável por teclado/mouse/**gamepad**. |
| `progression.py` | **Meta-progressão**: DNA persistente em `~/.lagarto/save.json` → `UPGRADES` (stats permanentes) e `UNLOCKS` (armas/charms entram no pool). `apply_to_player` no início da run; `finish_run` credita DNA. |
| `perf.py` | **Medidor de FPS/diagnóstico** (F3 ou nas Opções; `--profile` grava `~/.lagarto/perf.csv`). Separa step/draw/present e expõe o cache de brilho (entradas, MB, **misses/s**) — é o que distingue vazamento de thrashing. |
| `app.py` | Setup da janela + loop principal com **timestep fixo**. |

`lizard_game.py` é só um launcher: `from lagarto.app import main`.

## Sistema de genoma + evolução (núcleo)

Toda criatura é uma `Creature`/`Lizard` construída a partir de um `Genome` (números).
Lagarto, cobra, aranha (radial), escorpião, peixe = **genomas diferentes**, não classes.
- **Evolução do jogador = mutar o próprio genoma** e o corpo se redesenha (partes lidas
  em `parts.draw_all` a cada frame). Duas fontes: **comer** (presa portadora concede
  parte via `grants`) e **dash-matar** inimigo portador com **chance ~12%** (raro, não
  todo abate): aranha→+pernas (cap 10, +vel), espinhoso→espinhos, tanque→placas,
  chifrudo→chifres, escorpião→ferrão. Ver `Player.grant_part` / `game._collisions`.
- **Indicador de fora da tela** (`game._draw_offscreen`): setas na borda apontando
  inimigos/ninhos não visíveis — acha stragglers de uma onda.
- **XP/nível → cartas** (`Player.gain_xp` enfileira `pending_levelups`; `game.step`
  entra no estado **`levelup`** e mostra 3 cartas de `evolution.roll_cards`;
  `game.choose_card` aplica). Estados do jogo: `play` / `levelup` / `over`.
- **Mutações** = stats (vida, velocidade, dash, energia, regen, XP, língua, thorns,
  venom, wings) e partes (espinhos/placas/chifres/pernas/clava). **Sinergias** disparam
  no `apply_mutation`. Input das cartas tratado em `app.py` (1/2/3, setas+ENTER, clique).
- **Cores randomizadas**: cada spawn usa `genome.random_variation` (hue/sat/val/tamanho).

## Itens e sinergias (`items.py` + `evolution.py`)

**A divisão importa:** os passivos de **stat** continuam sendo as cartas de mutação
(`evolution.MUTATIONS`); `items.py` traz os que **mudam uma mecânica** — regra tirada do
Isaac, onde os itens memoráveis reescrevem um verbo (Spirit Sword troca o tiro por espada)
e "+10% de dano" é esquecível por construção. São 16 de mecânica contra 4 ativos.

- **`Player.ability`/`ability_cd` existiam declarados e decrementados desde muito antes,
  sem nada os usar** — um soquete vazio. Os ativos o preencheram. Carga por **abate**,
  o que amarra o recurso ao loop de combo que o jogo já roda.
- **A carga é contada em INTEIROS.** Somar `1/14` catorze vezes dá 0,9999999999999998, ou
  seja o item ficava cheio na tela e se recusava a disparar. A fração só existe para o anel.
- **Um gancho, um ponto só.** `Retaguarda` vive em `game.spawn_projectile` (o gargalo por
  onde todo projétil passa — por arma seriam 8 cópias); `Adrenalina` vive em
  `Player.damage_mult()`, lido por dash, rabada e armas.
- **Ordem importa em efeitos que se auto-consomem:** `Presa Marcada` marcava o inimigo
  *antes* do `take_hit` do próprio dash, então o crítico era gasto no golpe que o criou —
  o item não fazia nada observável. Marcar **depois**.

**Sinergias**: 12 nomeadas, e `evolution.owned_tags` achata mutações + armas + itens +
personagem num set só, para uma sinergia poder dizer "esta arma com aquele item" sem
saber de qual sistema cada metade veio. O **Synergy Factor** (Gungeon) multiplica o *peso*
da carta que avança um combo — não é sistema novo, `roll_cards` já escolhia por peso.
Medido: a carta que fecha aparece em **117/600** rolagens contra **43/600** sem o fator.
*Sinergia invisível não existe:* todas aparecem no compêndio, aba EVOLUCOES.

## Personagens jogáveis (`characters.py`)

**O jogador também é construído de um `Genome`**, então quatro personagens visualmente
distintos custam **zero arte nova** — `parts.draw_all` lê o genoma todo frame e a silhueta
acompanha. É a mesma premissa dos inimigos aplicada do outro lado.

| Personagem | Corpo | Mecânica exclusiva |
|---|---|---|
| **LAGARTO** (livre) | o padrão | `rerolls_per_level`: rerrola a mão de cartas (`game.reroll_cards`, tecla **R**) |
| **VIBORA** (loja, 120 DNA) | longa, **sem pernas** | `weapon_cap=2` + rabada rápida e forte — o teto **é** a mecânica |
| **COURACADO** (loja, 150 DNA) | grande, placas | `can_dash=False` + armadura + espinhos + `knockback_immune` |
| **LARVA** (conquista: onda 8) | minúscula | `characters.larva_growth`: cresce a cada `CHAR_LARVA_KILLS_PER_STEP` abates, 1 → 6 slots |

- **`Lizard.rebuild_body()`** recomputa **só** o que vem do genoma (espinha, pernas, `max_r`,
  `max_speed`) e nada mais. Antes o único jeito era re-chamar `__init__`, que apaga
  hp/armas/nível/aggro — por isso `champions.py` tinha uma lista `_KEEP` de 11 campos.
  Hoje ela sumiu, junto com a classe de bug que remendava. *`max_speed` acumula
  multiplicadores (DNA, cartas), então a razão contra `_speed_base` é carregada — recomputar
  do zero apagaria os upgrades em silêncio.*
- **Forma vem do personagem, MATIZ vem do slot do jogador.** `Player.__init__` passa
  `colorset[0]` explicitamente; se o personagem definisse a cor, dois jogadores com o mesmo
  personagem ficariam indistinguíveis no coop.
- **`char.apply` roda no PRIMEIRO `Player.update`**, não em `__init__` — guardado em
  `self.pending_char_apply` para o `game` existir de verdade quando disparar. O contrato
  `apply(player, game)` é uniforme com charm/item; passar `None` em `__init__` bypassava
  isso em silêncio, e um personagem futuro que leia `game` estouraria. Os quatro atuais
  não leem, mas o formato é honesto. Ele lê `armor`, `thorns`, `max_health` e
  `whip_cooldown`, todos declarados em `__init__` antes do store.
- **Destrave**: `UNLOCKS` com `kind='character'`. `cost=None` = **não está à venda**, só se
  ganha (`check_achievements` no `finish_run`). `save()` persiste tudo que estiver em
  `DEFAULT`, então basta adicionar a chave — mas a validação em `load()` tem que acompanhar.
- Personagem bloqueado **aparece na lista** com o requisito; recompensa invisível não é
  recompensa.

## Inimigos da fase 2 + campeões (`champions.py`)

Quatro comportamentos novos, cada um atacando um **hábito** diferente do jogador — é
assim que inimigo novo vira decisão nova, e não só mais um saco de vida:

| Espécie | `behavior` | Ataca o hábito de |
|---|---|---|
| **VESPA** | `fly` | esconder-se atrás da horda — `collision._samples` **pula voadores**, então eles não empurram nem são empurrados e vêm em linha reta |
| **ESTOURADOR** | `bomber` | ficar parado — pavio de `BOMBER_FUSE`, e depois de aceso ele **desacelera** |
| **METRALHADOR** | `gunner` | campo aberto — rajada de `GUNNER_BURST`, dano baixo por tiro |
| **ENVENENADOR** | `venom` | acampar num ponto — cospe onde você **está** e deixa poça |

**Telegrafo é tempo E visibilidade.** A primeira versão do pavio tinha os 0,85 s (>27
frames) e **nada para ver** além de faíscas — inútil. Hoje `_draw_fuse` desenha a
**pegada da explosão no chão**, que responde a única pergunta que importa: *estou dentro?*
Regra: ao criar um ataque de área, desenhe o raio, não só um aviso.

**Poça hostil (`weapons.Puddle(hostile=True)`): o campo `dmg` MUDA de significado.**
`hostile=False` → dano por **segundo** (multiplicado por `dt`, alimenta o acumulador de
`AILizard.damage`). `hostile=True` → dano por **tick**, com cadência própria
(`VENOM_PUDDLE_TICK`). *Os i-frames do jogador não servem de limitador* — reabrem a cada
~0,17 s e mediram **42 de dano por segundo**. E `VENOM_PUDDLE_LIFE` **tem que ser menor
que `VENOM_CD`**, senão as poças se sobrepõem e empilham: o mesmo bug do `Acido`, de novo.

### Campeões: variantes + modificadores

**Variantes** são criaturas com identidade, no modelo das raças de lagarto do **Rain
World**: o traço visual **explica** a habilidade. FILHOTE (minúsculo, 1 de vida, veloz) ·
ALFA (**antenas** porque comanda a matilha) · ESPECTRO (**pálido** porque embosca) ·
SALTADOR (**cauda-clava** porque é dela que ele se lança) · APICE. **Modificadores**
(BLINDADO/GIGANTE/EXPLOSIVO) são mecânicos puros e **empilham** sobre uma variante —
"APICE BLINDADO" é outra luta sem uma linha de comportamento nova.

Três armadilhas já corrigidas:
- **`_rebuild` chama `__init__`, que reseta TUDO.** Sem a lista `_KEEP`, os metadados de
  `species.make` (species/xp/score/grants/hp) voltavam ao padrão do genoma **e** empilhar
  um modificador apagava a variante aplicada antes. Ambos invisíveis no spawn.
- **Velocidade de variante é ABSOLUTA, não multiplicador.** `max_speed` é
  `165*(0.85+0.4/size)*speed`, então encolher **já** acelera muito; multiplicar por cima
  deu **5,75x a velocidade do jogador** (indesviável). E um multiplicador faria um
  "filhote de tanque" mais lento que o jogador, negando a única coisa que a variante
  significa. `CHAMP_FILHOTE_SPEED` fica entre andar e dashar: te alcança se você caminhar,
  perde se você dashar.
- **A camuflagem tem que valer para o rótulo também** (`champion_vis`): o nome e a aura do
  ESPECTRO flutuavam em cor cheia sobre um corpo invisível, entregando a emboscada.

`palette.glow` novo com raio/cor contínuos (pavio, aura) **foi medido**: 363 entradas,
12,9 MB, **zero misses novos** em 9 000 frames com 14 criaturas — o quantizador absorve.

**Modificador novo — DIVISOR** (Blobulon/Fistula): racha em **2 cópias menores** ao morrer.
- **Nunca `enemies.append` dentro do laço que mata.** `die()` é chamado de dentro de
  `_collisions`/`_update_projectiles`, que iteram `game.enemies` — estender a lista ali faz
  a mesma investida acertar as crias no mesmo frame. As crias vão para `game.pending_enemies`
  (`game.spawn_enemy`) e são drenadas **uma vez por step**, depois do `_collisions`.
- **`split_gen` limita a profundidade.** DIVISOR nasce com `split_gen=1`; as crias herdam
  `split_gen-1` e só voltam a rachar se `>0`. Sem isso, uma geração infinita afoga a horda.

## Corpos procedurais novos (Fase B4) — `genome.plan`

O corpo forkava só por `genome.radial` (aranha). **`genome.plan`** (declarado no `__slots__`
— a armadilha de sempre) adiciona dois planos, cada um com `rebuild_body`/`draw`/telegrafo
próprios, e **uma mecânica que ataca um hábito** (mesma régua da fase 2):

- **CENTOPEIA** (`plan='segmented'`, `behavior='burrow'`): corpo = **cadeia de círculos
  aneladas** (o anel de tinta em cada segmento É a segmentação) + patinhas em **onda
  metacronal** (parceiro = par 2 segmentos atrás, para rippar em vez de marchar). Mecânica
  **cavadora** (Para-Bite/Moles do Isaac): `surface → digging → under → erupt`.
  - **Mergulhar não pode ser "sumir".** Há uma fase `digging` enraizada (`CENT_DIG_TIME`) que
    abre um buraco crescente e joga terra — telegrafo de que vai submergir. Aí `burrowed=True`.
  - **Intangível por baixo, num ponto só:** `hit_test` devolve `None` e `collision._samples`
    pula quem tem `burrowed` (mesmo padrão do flyer). Todo dano passa por `hit_test`, então
    isso cobre dash/projétil/aura de uma vez. *Durante o `digging` ele ainda é vulnerável* —
    é a janela de contra-ataque.
  - **Telegrafo justo** (`_draw_burrow`): um **anel de erupção** no `dive_to` (travado no
    mergulho) que **enche** conforme aflora + o mound viajando com trilha de terra. Regra da
    fase 2 de novo: desenhe o raio, não só um aviso.
- **POLVO/KRAKEN** (`plan='tentacle'`, `behavior='grapple'`): manto pulsante + **braços que
  são sub-cadeias** (`self.arms`, resolvidas em `integrate`), com onda viajante + swirl para
  ondular como tentáculo e **trailing** para chicotear ao mover. Desenho **contínuo** (mesmo
  contorno left/right-rim + cap da espinha — o usuário pediu carne lisa, não miçangas).
  - Mecânica **agarradora** (Gripmaster do Gungeon): fecha devagar, enraíza e **estica todos
    os braços para você** (o `arm_target` faz `_resolve_arms` convergir/esticar — **essa
    convergência É o telegrafo**, `OCTO_WINDUP` > 27f); no estalo, te **puxa** (`OCTO_PULL_DIST`)
    e **retarda** (`apply_slow`). Fugir antes do bote nega. *Braços são cosméticos: o hitbox é
    o manto (`hit_test` amostra a espinha curta); o perigo é o agarrão, não o toque.*
  - **Bruiser lento tem que ignorar empurrão** (playtest): `take_hit`/`damage` **atribuem/somam
    velocidade** de knockback, então cada tiro do cuspe zerava a aproximação e o polvo nunca
    chegava. `genome.knockback` (mult. <1, novo dial no `__slots__`) resolve num ponto só —
    polvo=0.28, o resto=1.0. E ele **compromete a aproximação** (sem recuar para "manter
    distância"), já que a única defesa contra ele é você **correr** (top speed dele < andar do
    jogador). Medido: fecha de 430px a ~16px sob fogo e agarra.
- **Prontos para chefe (Fase 5/6):** o KRAKEN em escala ~2.2x já renderiza; a silhueta serve
  de chefe sem corpo novo.

## Bestiário / IA

`AILizard` despacha por `genome.behavior`: `chase` (corpo-a-corpo), `ranged` (cuspidor
mantém distância e atira `projectile.spit`), `lunge` (aranha telegrafa e dá o bote),
`hop` (sapo). **Ecossistema**: predadores com `diet=('prey',)` caçam presas de verdade;
presas fogem do jogador **e** de predadores (`game.nearest_threat`). Status: `apply_slow`
(afeta o steer) e `apply_poison` (DoT nas criaturas).

## Técnica de animação procedural

Lagarto = 4 elementos: **Intent** (cabeça aponta), **Action** (pernas dão o passo),
**Reaction** (espinha reage), **Follow-through** (cauda atrasa).
- Espinha: cada junta é puxada a uma distância fixa da anterior; direção limitada
  (`bend`) para o corpo não dobrar sobre si.
- Pernas: pé fica plantado até o corpo arrastar o "descanso" além de um limiar;
  então dá um passo em arco a um ponto à frente. **Marcha diagonal**: pares opostos
  nunca dão o passo juntos (`Leg.partner`). Desenho por IK de 2 ossos.
- Squash & stretch a partir da velocidade.

## Buffer de input (não volte para borda de um frame só)

`Controller` guarda um **timer por ação** (`C.INPUT_BUFFER`, 0,15 s) em vez de uma flag de
um frame; `dash_edge`/`tongue_edge`/`whip_edge` são **propriedades** (`buffer > 0`) e quem
dispara chama `ctrl.consume(...)`.
**Por quê:** `poll()` roda 1x por frame **renderizado**, mas a simulação é acumulador de
passo fixo — um frame pode rodar **zero passos** (jitter e **todo hit-stop**). A borda
detectada nesse frame nunca era consumida e o `poll()` seguinte via o botão como "ainda
pressionado" → **pressionada engolida para sempre**. Com o antigo `RENDER_FPS = 120` contra
`SIM_HZ = 60` isso era ~**metade dos frames** — a mesma raiz do problema de performance.
O buffer também deixa valer uma pressionada pouco **antes** do cooldown acabar.
*O disparo continua por **borda**: segurar o botão não repete (testado).*

## Menu de pausa (`game.state == 'pause'`)

ESC pausa; antes ele **descartava a run inteira sem confirmação**. É só mais um estado
não-`play`, então `game.step` já congela tudo de graça — a `Game` nunca é destruída.
- `game.toggle_pause()` guarda `pause_prev` (dá para pausar **dentro do acampamento** e
  voltar para lá), `pause_mode` alterna menu/opções/controles, `pause_back()` sobe um nível.
- **Reusa o menu principal**: `menu._items_for('options', ...)` e `menu._activate(...)` dão
  a tela de opções inteira com a mesma persistência. O texto de controles virou
  `menu.CONTROLS`/`controls_lines()` — **compartilhado**, senão as duas telas divergem.
- **Quatro armadilhas já corrigidas** (não reintroduza): a música ramifica em `game.state`
  todo frame → usar `pause_prev` senão pausar no acampamento troca `calm`→`combat`;
  `'pause'` tem que estar na tupla `soft` do fade senão dá blackout de 0,22 s;
  `meter.level` e o `cfg` do `app.py` precisam ser **relidos** depois das opções
  (`app._pause_pick`), senão o medidor de FPS parece morto e o próximo F3 reverte ajustes.

## Controles

- **P1**: WASD mover · mouse mirar · clique-esq/ESPAÇO dash · clique-dir/SHIFT língua ·
  **clique-meio/Q rabada** (golpe de cauda).
  No single-player, um **gamepad também controla o P1** (híbrido — usa o que estiver
  ativo; `KeyboardMouseController(joy)`), então dá pra jogar sem mouse.
- **Língua com auto-mira**: mira sozinha no alvo mais próximo no alcance
  (`game.nearest_edible` — sem cone) e **custa energia** (8). Dispensa mouse.
- **P2** (coop): gamepad (sticks + A/X/**Y**) se detectado, senão setas + IJKL +
  RCtrl/RShift/**RAlt**.
- **Janela** (`display.py`): tudo é desenhado numa **surface lógica fixa**
  (`C.WIDTH×C.HEIGHT`) e escalada (smoothscale) p/ a janela; presets **1x/2x/3x**,
  tela cheia com **letterbox**, **F11** alterna. Qualquer clique/mira precisa passar por
  `display.to_logical(pos)` — senão desalinha quando escalado.
- **Gamepad**: usa a **API GameController do SDL** quando disponível (mapeamento correto
  por device, DualSense/Xbox), com fallback p/ eixos crus + hat. **Hot-plug** funciona.
  `MenuNav` converte stick/dpad em eventos de menu (com repeat) — navega menu, cartas de
  level-up e acampamento.
- **Menu-hub** (`menu.py`): lista navegável (setas/mouse) sobre lagartos animados —
  1/2 jogadores, **Opções** (tela cheia), **Controles**, Sair. (Bestiário e navegador
  de upgrades: a fazer.)

## Combate — armas Bullet Heaven / Survivor-like (`weapons.py`)

Núcleo ofensivo é **automático** (o jogador só move/desvia). `Player.weapons = {id:
level}` + `Player.weapon_state`; cada frame roda `weapons.WEAPONS[id].tick(...)`.
- **Stats globais** (escalam todas as armas, vêm de passivas): `might` (dano),
  `area_mult` (raio/alcance), `cooldown_mult` (cadência), `amount` (+projéteis/orbitais).
- **8 armas**, cada uma com **tabela de níveis** (`levels`: cada nível faz algo específico,
  mostrado na carta via `level_desc`) e **animação própria**: Cuspe (projétil), Ferrão
  (homing — `Projectile.homing`, curvado em `game._update_projectiles`), Teia (slow),
  Nuvem de Esporos (aura de dano), Feromônio (aura de slow), Sopro (aura knockback),
  Enxame (orbitais), Ácido (`Puddle` no chão, `game.puddles`). Cap de **6 armas**.
- Armas com `layer='under'` desenham atrás do corpo (auras), `'over'` na frente (orbitais).
- **Cartas de level-up** (`evolution.roll_cards`) misturam **cartas de arma** (`WeaponCard`:
  nova ou subir nível) + **passivas** (stats globais/partes). HUD mostra chips das armas
  equipadas com o nível.
- **Dano fracionado** de auras/orbitais/poças via `AILizard.damage(game, amount)` — um
  acumulador que guarda a sobra fracionária. **Ele não é limitador de taxa**: quem chama
  todo frame *tem* que multiplicar por `dt`, senão entrega 60x. Auditado: esporos, sopro,
  enxame e poça fazem certo. *As chaves `dmg` de Enxame e Ácido são **dps**, não dano por
  acerto* — armadilha ao balancear.
- **Ácido: o multiplicador era empilhamento, não reaplicação.** `Acido.tick` re-consultava
  `nearest_enemy` dentro do laço **sem o mundo avançar**, então todas as poças caíam no
  mesmo alvo (espalhamento de 60 px contra raio ~80 → sobreposição quase total), e a vida
  da poça era maior que o cooldown. Dava ~57 dps efetivos contra 18 do esporos. Hoje as
  poças miram **inimigos distintos** e `life` é menor que antes. Medido no alvo único
  (nível 5): ácido 18,6 · esporos 23,4 · enxame 18,5.

Extras manuais: **dash** (contato + i-frames + **chain**: matar com dash recarrega o
dash e devolve energia), **língua-chicote** (mira no mais próximo entre comida/inimigo;
inimigo leva dano + é puxado; custa energia), **habilidade ativa** (a fazer no camp).
**Combo/streak** (`game.combo`): matar sobe o multiplicador (decai se você foge).

**Rabada (`Player._whip_hit`)** — golpe de cauda manual, botão próprio (**meio do mouse /
Q**, P2 **RAlt**, gamepad **Y**). Custa `C.WHIP_COST`, cooldown `Player.whip_cooldown`.
- **Como a cauda se move** (`Player._whip_arc`): quem varre é a **cauda**, não o jogador.
  A espinha é follow-the-leader, então só dá para *dirigi-la pela cabeça* — por isso as
  duas primeiras tentativas erraram o alvo (impulso na velocidade e depois arco na cabeça:
  ambas jogavam o **corpo inteiro** de lado). A solução é **reconstruir as juntas da metade
  traseira** a partir de um pivô (`_whip_span`), distribuindo `C.WHIP_SWEEP` graus de
  curvatura **entre todas elas**.
  - **A rampa de curvatura tem que ser suave.** Aplicar o giro todo na primeira junta vira
    **dobradiça** (lê como "um pedaço rígido girando"); rampa quadrática rumo à ponta joga
    ~80° num link só, acima do próprio limite de curvatura da espinha (`bend=26`) — dá bico
    e ainda é clampado pelo `resolve` seguinte. Rampa quase uniforme = arco quase circular
    = o lagarto **mantém a curvatura natural**.
  - **Envelope de período inteiro** (`sin(t*2π)`): varre um lado, passa pelo meio e varre o
    outro **num golpe só**, começando e terminando em zero (entra e sai suave sozinho).
  - Ancorar o ângulo no **corpo** (`js[pv] - js[pv-2]`), **nunca na cauda do frame
    anterior**: `spine.resolve` deriva direção das posições anteriores, então ancorar na
    cauda realimenta a curva e o balanço se cancela num tremor.
  - A sobrescrita **sobrevive até o desenho** só porque o contato do jogador é macio —
    ele nunca é empurrado, então `collision.separate` pula o re-resolve dele. Se o contato
    voltar a ser duro, isto quebra.
- **Hitbox = as juntas reais** (`spine.joints[-3:]`) com alcance explícito `max_r*1.15`
  (o `radii` da ponta é ~0.22*max_r, pequeno demais). O que você vê é o que acerta;
  cabeça do inimigo ainda dá crítico.
- **`whip_hits`** (set, limpo no disparo) = **um acerto por alvo por golpe**, mesmo padrão
  de `dash_hits`. Sem isso o bug de dano-por-frame volta.
- **Modificadores da cauda** (era tudo cosmético antes): `club` → `WHIP_CLUB_MULT` de dano
  + `WHIP_KNOCK_CLUB` de empurrão + shake maior; `sting` → `apply_poison`. *Nota: o ferrão
  dos **inimigos** aplica `apply_slow`, o do jogador envenena — divergência proposital.*
- **A cauda nua é fraca de propósito; o dano vem dos upgrades.** Antes o golpe era **5
  fixo e não escalava com nada** — `might` era lido só pelas armas — então a rabada era
  idêntica na onda 1 e na onda 20: dominava cedo e virava irrelevante tarde. Hoje
  `_whip_hit` multiplica por `player.might`, então **Vigor** (+20%/carta) e **Potência**
  (DNA, +6%/nível) finalmente melhoram o golpe, e `WHIP_CLUB_MULT` (2.6) faz da clava *o*
  upgrade que transforma a cauda em arma: 2 nua → 5 com clava → 12 com clava+Vigor+DNA.
- **O dash levou o mesmo tratamento** (`Player.dash_damage()`): base 5 → 4, ×
  `DASH_WINGS_MULT` (1.5) com Membranas, × `might`. **Membranas já melhorava
  velocidade/duração/cooldown/custo do dash mas *não* o dano**, apesar de a carta prometer
  "dash mais forte" — agora cumpre. 4 nu → 6 com membranas → 13 com membranas+Vigor+DNA.
  *O cálculo vive num método porque havia **dois** call sites lendo `C.DASH_DAMAGE` direto
  (inimigo e ninho): escala adicionada num deles pularia o outro em silêncio.*
- **Descrições de carta agora dizem a verdade**: `might` afeta armas **e** dash **e**
  rabada, não só armas. Ao adicionar escala nova, corrija o texto da carta junto — a
  promessa não-cumprida de Membranas passou despercebida por muito tempo.
- **A hitbox usa a MESMA seção que se move** (`_whip_span` serve os dois). Quando só as 3
  últimas juntas eram testadas e a seção que balança cresceu para 6, a cauda passava
  visivelmente por cima do inimigo sem acertar.
- **Alcance = o arco atrás/ao lado** (medido: 1-2 alvos por golpe), não a tela toda. Quando
  o golpe ainda movia o corpo, pegava 4-5 e o dano por acerto tinha sido baixado para
  compensar; com a cauda sozinha voltou para perto do dash, e quem paga a diferença é o
  cooldown maior. Confirmado que **não** há acerto repetido no mesmo alvo (`whip_hits`) e
  que a cauda **não fere fora do golpe**.
- `take_hit` **atribui** `vel`, então o empurrão extra vem **depois** da chamada.

**Dano do dash — um acerto por investida.** `_collisions` roda **todo frame**, então
enquanto `p.dashing` (0,16 s ≈ 10 frames) o mesmo inimigo era atingido 10x: **30 de dano
por dash em vez de 3** (60 com crítico de cabeça) — era a causa real de "os inimigos
morrem fácil demais", não o balanço de vida. `Player.dash_hits` (set, limpo ao iniciar o
dash) garante **um acerto por alvo por dash**; dano em `C.DASH_DAMAGE` (5, crítico 10;
ninho leva 2x). **Ao mexer em dano de contato, cheque sempre se a fonte é por-frame.**

**Colisão:** aliados (`kind ∈ {player,friend}`) **não colidem entre si** (`collision.py`
`FRIENDLY`) — batalhas fluidas; inimigos ainda colidem normalmente.

**Contato jogador↔inimigo é MACIO** (feedback: ser empurrado por todo inimigo parecia
pinball). O jogador **nunca é deslocado**: atravessa, **empurra o inimigo** (push cheio,
sem peso por tamanho) e paga em **velocidade**. `collision.separate` acumula a
profundidade de sobreposição em `creature.clog`; `Player.update` normaliza, suaviza
(`clog_f`, `approach` 9/s) e aplica `C.CONTACT_DRAG`. **Ignorado durante o dash**
(atravessar é a graça). *Inimigo↔inimigo continua com separação dura* — sem isso volta o
bug de empilhar.

**São DOIS freios independentes que se MULTIPLICAM** (a lentidão do ferrão × o
`clog` do contato). Medido numa briga com 6 inimigos: 89% × 89% = **80% de
velocidade média**, 40% do tempo abaixo de 80%. Nenhum é ruim sozinho; juntos
explicam o "por que estou lento?" — e nenhum dos dois tinha qualquer aviso na
tela. Hoje `Player._draw_slow_mark` desenha anéis frios sob o corpo enquanto a
lentidão dura.

**A lentidão do ferrão disparava mesmo sem o golpe acertar.** `_contact` chamava
`apply_slow` fora do resultado de `hurt()`, que sai cedo nos i-frames — então
você levava 50% de lentidão **sem número de dano nenhum para explicar**. Pior:
duração 1,4 s contra `attack_cd` de 0,8 s, ou seja **permanente por construção**.
Medido: um escorpião te mantinha lento **59% do tempo**. Hoje `hurt()` **devolve
se o golpe landou** e o ferrão só retarda nesse caso, com `STING_SLOW_TIME` (0,4)
bem menor que o `attack_cd`. *Terceira vez que este projeto tropeça em "efeito
dura mais que o intervalo de reaplicação" — Ácido, poça de veneno, ferrão.*

**Duas coisas estavam erradas no clog, e as duas foram medidas:**
- **Presa freava igual a inimigo.** `movers` inclui presas e o ramo de contato macio
  dispara para qualquer par com o jogador que não seja aliado, então um **pastador
  inofensivo a 30 px deixava o jogador a 49% da velocidade** — sem nenhuma pista visual
  que o jogador associasse à lentidão. Hoje só `collision.DRAGS_PLAYER` (= inimigos)
  acumula `clog`; presas continuam sendo empurradas, mas não custam velocidade.
- **Saturava com UM inimigo.** `clog` soma 5×5 pares de amostras, então um corredor já
  batia ~25 contra o divisor `max_r*1.2` → o freio era binário (100% ou 45%), sem
  gradiente. `C.CONTACT_FULL` (3.0) escala o divisor para "enterrado em ~3 corpos".
  Medido depois: 1 inimigo ≈ 90%, 4 ≈ 68%, 6 ≈ 65%.

## Ondas em rounds (`rounds.py`) + Acampamento

`RoundManager` substitui o antigo `update_waves`. Cada round tem um **tema** (`THEMES`:
enxame/cuspidores/tanques/aranhas/invasao) anunciado por **banner**; inimigos **pingam**
de **`Nest`** (POIs destrutíveis, com boca que brilha antes de emitir) via **`SpawnMark`**
(telegraph que cresce no chão) — nunca um dump só, e nunca em cima do jogador. Destruir
os ninhos (dash/cuspe) corta o fluxo. `game.rounds.draw_world`/`draw_banner`.

**Acampamento FÍSICO** (estado `camp`, entre rounds — modelo Hades): ao limpar
(`rounds.state=='cleared'`) o `game._enter_camp()` monta uma **clareira andável** em volta
de onde a onda foi limpa, com a **barraca do besouro** (loja) e **3 portas** (as rotas). Não
é mais uma tela. `game.pollen` = moeda da run (kill × combo). Loja: cura/vida/vigor/charm/ovo;
custo sobe a cada compra; **charm custa 150**. Cada porta = tema da próxima onda + bônus
cura/pólen/carta; atravessá-la chama `rounds.request_next(theme)` via `_apply_route`.
- **Dois modos, `camp['mode']`.** `field` = andando; `shop` = menu da barraca aberto.
  `game._step_camp` roda `player.update` só no `field` (movimento real); `shop` congela como
  a tela antiga. `game.draw` sempre desenha o mundo+jogador, então em `field` só acrescento
  `_draw_camp_pois` (barraca+portas no mundo) + `_draw_camp_field_ui` (HUD embaixo, para não
  brigar com os rótulos das portas no topo); em `shop`, o `_draw_camp` de sempre (véu por cima).
- **Nada de input novo no loop:** `app.py` já chama `ctrl.poll` e `cam.follow` **todo frame**
  em qualquer estado — por isso o movimento no `field` sai de graça. O menu (teclado/mouse/pad)
  **só age no modo `shop`** (`app._camp_shop_open`); em `field` WASD/stick andam. ESC/B fecham
  a loja (voltam à clareira), não pausam.
- **A loja é escolha, não pedágio:** dá para ignorar a barraca e ir direto na porta — é o que
  dá peso à decisão. `reopen_cd` impede reabrir no mesmo passo que fechou; **fechar** só trava
  com uma compra em absorção (`self.pick`), **não** durante o drop-in (senão não dava pra sair
  por 0,36 s). Entrar limpa presas/projéteis/poças (`_enter_camp`) — clareira limpa, sem presa
  congelada travada numa porta (não atualizo presas no camp).
- **A barraca e as portas CAEM do céu** (juice): cada peça despenca de `CAMP_DROP_H` acima,
  ease-**in** (acelera e bate), escalonadas (`_camp_drop_off`). No toque no chão,
  `_camp_impact` dispara **shake + poeira + faíscas + anel** (`_update_camp_drop`, uma vez por
  peça). Enquanto cai, uma **sombra cresce** no ponto de pouso (telegrafo). **Interação é
  travada até pousar** (`tent_landed`/`dr['landed']`) — não dá pra entrar numa porta no ar.
- **Navegação da loja — um modelo só p/ teclado e gamepad** (`app._camp_nav`), agora só
  **loja → charms** (a rota virou porta física). Charms em grade, uma coluna por slot
  (`C.CHARM_SLOTS`): cada charm **sob o cabeçalho do seu slot**; esq/dir troca coluna (pula
  vazias), cima/baixo anda na coluna e **só sai nas pontas** (`camp_move_charm` devolve `False`).
  `camp_equip(cid)` recebe **id**, não índice; `camp_equip_cursor()` resolve coluna+linha → `cid`.

## Telas de jogo: entrada animada + absorção da escolha

Level-up e acampamento **não aparecem de uma vez**. Relógio: `self.ui_t`, zerado em
`_enter_levelup`/`_enter_camp` e avançado no ramo `state != 'play'` de `game.step` (passo
fixo → independe de FPS). Dials em `config.py` (`UI_VEIL`/`UI_STAGGER`/`UI_DROP`/`PICK_*`).
- **Fase 1** (`_veil`, 0–0,20 s): o fundo escurece.
- **Fase 2** (`ui.drop_in(t, i, ...) -> (offset_y, alpha)`): cada painel **desce
  escalonado** com fade. `menu._menu_list` usa o mesmo helper — um único "feel".
- **Absorção** (`self.pick`): escolher **não aplica nada na hora**. As outras opções
  desbotam/encolhem, a escolhida vai ao centro (acima do lagarto — a câmera centraliza o
  jogador, centralizar a carta também não deixaria trajeto), segura para leitura, e
  **voa para dentro do jogador** com rastro. No impacto: `punch()` (**screenshake** +
  hit-stop + flash) + burst/anéis + som — e **só então** `_apply_card`/`_apply_buy`/
  `_apply_route`. Input bloqueado via `game.ui_busy()` + guardas de `game.pick` em `app.py`.
- Transições `play↔levelup↔camp` **não usam `ui.Fade`** (o blackout escondia o impacto).

**Partículas nestas telas:** `fx` é desenhado junto com o mundo, ou seja **por baixo do
véu** (que corta ~80% do brilho). `game._ui_fx(layer)` redesenha as partículas **por cima
dos painéis** enquanto há `pick` ou `ui_fx > 0` (pós-brilho de 1,1 s, porque a rajada de
impacto nasce no frame em que `pick` já virou `None`). Compras usam `C.COL_POLLEN` — o
pólen gasto explode da barraca, vira um cometa dourado e estoura no lagarto com o som
`buy` (o chime foi movido do clique para o impacto).

**Perf destas telas:** painéis são cacheados (`game._panel`, chave = estado do painel);
o véu usa surface opaca + `set_alpha` (SRCALPHA por-pixel custava ~6 ms/frame); a camada
de shake só é composta **quando há shake** (`_ui_dest`), senão desenha direto na tela.

## Legibilidade da tela (texto + layout do topo)

**O texto era fraco porque o antialiasing não é o problema.** Ele já estava ligado nos
~68 pontos de render. O borrão vem do `display.present()` fazer `smoothscale` da tela
inteira: o glifo é rasterizado a 14 px na surface lógica e **esticado com filtro bilinear**
para 2x/3x. Traço fino não sobrevive a isso. Duas coisas resolvem, e as duas importam:
- **`ui.text(surf, font, s, pos, cor, align=)`** desenha um **contorno escuro** atrás do
  glifo — a borda dura é a única coisa que atravessa o filtro. `pos` é onde os glifos
  caem, então é substituto direto de `surf.blit(font.render(...), pos)`, e ele **devolve o
  rect** do texto (usado pelo layout). *`ui.text_surface` devolve surface **cacheada e
  compartilhada** — `.copy()` antes de mexer no `set_alpha`, senão todo desenho seguinte
  daquela string herda a alteração (o fade do banner caiu exatamente nisso).*
- **`fonts.get(size, bold=True)` por padrão** — haste grossa sobrevive à escala.
- O cache de texto tem **teto (`_TEXT_MAX = 700`) com `clear()`**, mesmo padrão do
  `palette._GLOW_CACHE`: score, vida e timers são texto **contínuo**, então o keyspace é
  ilimitado. Medido: estável em ~608 entradas / 9,7 MB em 18 000 frames.

**A pilha do topo (`game.TopStack`).** Seis elementos — score, linha de onda, combo, banner
do tema, nome do chefe e barra do chefe — fixavam cada um o próprio `y`. Numa onda de chefe
com combo eram **três sobreposições ao mesmo tempo**, e o banner dura 2,2 s exatamente
quando o chefe nasce, ou seja era garantido de acontecer. Hoje cada elemento pede a altura
que precisa (`top.take(h)`) e recebe a próxima faixa livre.
- **Ordem de desenho = prioridade.** Permanentes (HUD, barra do chefe) reservam primeiro e
  nunca se mexem; o banner é **transitório** e vai por último, senão empurra a barra do
  chefe para dentro da área de jogo justo nos segundos do spawn.
- `top.reset()` uma vez por frame, em `game.draw`.
- O **HUD é escondido em `levelup`/`camp`**: essas telas têm cabeçalho próprio e o HUD por
  baixo do véu só competia com os painéis.

**Nada de `→` (U+2192) em texto de UI.** O Noto Sans base não cobre setas (elas vivem no
Noto Sans Symbols) e ela saía como **tofu em toda carta de upgrade de arma**. Pior: o
`font.metrics('→')` **mente** — reporta o glifo e mesmo assim não rasteriza, então teste
renderizando, não consultando. Use `->`. O travessão `—` renderiza normal.

## Modelo de dano (barra de vida)

Vida é **contínua** (`Player.health`/`max_health`, base 100), desenhada como **barra**
no HUD (verde→laranja→vermelho), com barras de energia e XP. `hurt(game, dir, dmg)`
recebe dano; melee escala com o tamanho do inimigo (`8 + max_r*0.4`), projétil ~8.
Cura: fruta +25, regen contínuo (mut. `regen` hp/s), revive a 50%. i-frames curtos
(`hit_flash > 0.45`). **Projéteis são telegrafados** (cuspidor tem wind-up
`shoot_charge` com partículas) e **lentos** (~230) → dá pra desviar; visual estilo
Gungeon (core + halo aditivo + trail) em `projectile.py`.

## Partes / juice

`parts.py` desenha tudo **orgânico**: espinhos curvos **alternando os lados** com sway,
placas = **escamas em chevron**, chifres tapered curvos, cauda clava/ferrão, nadadeiras.
Evoluir (`grant_part`/`apply_mutation`) solta burst + sparks + anéis (DaFluffyPotato).

## Gameloop / objetivo (Bullet Heaven / Survivor-like)

Ataque é **automático** (armas); você só move/desvia/posiciona. Round temático →
inimigos pingam de ninhos → limpar → **acampamento** (loja de pólen + charms + rota) →
próximo round. XP sobe nível → **3 cartas** (arma nova / +nível de arma / passiva).
Comer/dash-matar portadores pode conceder partes (raro). Cair = "down" (parceiro revive
tocando); todos caídos = fim. **Score/pólen** escalam com o **combo**.

## Modos de jogo

- **NORMAL**: a run **termina** no chefe final da onda `config.RUN_FINAL_WAVE` (20) —
  `rounds.is_final` faz o chefe nascer maior ("PRIMORDIAL", ~2x a vida) e derrotá-lo leva
  ao estado **`victory`** (tela com resumo + **bônus de +150 DNA**).
- **INFINITO**: destravado **após a primeira vitória** (`progression.beat_game`); ignora a
  onda final e escala para sempre. O menu mostra o item esmaecido enquanto travado.
- `Game(..., mode='normal'|'endless')`; `menu.run_menu` devolve **`(nº jogadores, modo)`**.

## Chefes e meta-progressão

- **Chefe a cada `rounds.BOSS_EVERY` (5) ondas**: `_spawn_boss()` pega uma espécie do
  tema, **reconstrói o corpo em escala ~2.3x**, dá muita vida, `glow_body` e um nome
  (`CUSPIDOR ALFA`). O round **só limpa quando o chefe cai**; `draw_boss_bar` mostra a
  barra grande no topo e a **música muda para `boss`** (`app.py`).
- **DNA** é creditado ao morrer (`game._bank_run` → `progression.finish_run`, mostrado na
  tela de fim). Gasta-se no menu em **EVOLUCAO (DNA)**: upgrades permanentes (vida, dano,
  cadência, velocidade, XP, pólen) e **unlocks** que liberam armas/charms no pool da run
  (`progression.unlocked` filtra `evolution._weapon_cards`, a loja e os drops de ninho).

## Balanceamento (2ª passada): subir DANO, não vida

Regra que veio da pesquisa (Isaac/Gungeon/VS) e vale para todo ajuste futuro: num jogo de
ataque automático a única agência do jogador é **posicionamento**, então dificuldade tem que
ser **consequência de erro de posição**. Vida a mais vira esponja e ainda faz a build
*parecer* mais fraca do que é.
- **Dano de contato** sai de `lizard.contact_damage(max_r, wave)`, com os dials
  `ENEMY_DMG_BASE` (11), `ENEMY_DMG_SIZE` (0.5) e uma **escada por onda em degraus**
  (`ENEMY_DMG_STEP`/`ENEMY_DMG_PER_STEP`) — rampa contínua o jogador não percebe, degrau
  ele sente. Corredor 16→26 da onda 1 à 20; tanque 26→36. Projétil: `ENEMY_PROJ_DMG` (10).
- **`ENEMY_HP_MULT`: 3.0 → 2.2 (medição) → 3.5 (playtest).** O bot headless mediu o TTK das
  **armas** e concluiu 2.2; jogando de verdade quem mata é o **dash + a rabada**, muito
  mais rápidos, e a sensação era de inimigos de papel. **Lição: o bot mede atrito, não
  dificuldade** — use-o para comparar antes/depois, nunca para decidir o valor final.
- **Não mexer nos i-frames** (`hit_flash > 0.45`) — são o que mantém o jogo justo.

**Medição (bot headless dirigido, `--smoke` não serve para isso).** Dois estilos: `kite`
(só se move, deixa as armas trabalharem) e `aggro` (caça de dash, como o usuário joga).
Resultado do rebalanceamento: aggro passou de onda mediana 2,5 / 5,5 abates para **3,0 /
8 abates** no mesmo tempo até morrer — mata mais rápido, morre igual. *Um bot que só se
move mede um jogo que ninguém joga:* no nível 1 o `cuspe` faz **1 de dano a cada 1,05 s**,
então quase todo o dano inicial vem do **dash**.

**Aberto, e é decisão de design, não bug:** jogar 100% passivo **não limpa a onda 1 em 6
minutos**. A premissa "ataque é automático, você só se posiciona" não vale no começo da
run. Subir o dano das armas base resolveria, mas deixaria o jogo *mais fácil* — o oposto do
pedido. Precisa de decisão do usuário antes de mexer.

## Balanceamento (1ª passada, a partir de playtest do usuário)

Feedback: *inimigos morriam fácil demais, amigos eram desproporcionais, e havia cura
demais no chão*. Ajustes feitos — **estes números são o lugar para mexer**:
- **Inimigos ~2x mais duros**: hp de genoma em `species.py` (runner 2→4, tank 6→14,
  snake/spider/spitter 3→6, horned/spiky/scorpion 4→8) e escala por onda mais rápida
  (`rounds`: `wave//3` → `int(wave*0.7)`).
- **Menos inimigos ao mesmo tempo**: `THEMES[...]['cap']` reduzido (11→7, 7→5, 5→4, 8→6)
  e budget menor (`(4 + wave*1.6)` → `(3 + wave*1.1)`).
- **Menos cura**: fruta cura 25→12; frutas iniciais 12→5; drop de inimigo 40%→15%;
  ninho dropa fruta 100%→50%.
- **Amigos temporários e mais fracos**: `config.FRIEND_LIFE` (45s, piscam nos últimos 5s
  e somem), hp 3→2, ataque a cada 0.6s→1.1s; ovos no mundo 6→3; ovo na loja 24→40 pólen.

## Hitbox: corpo inteiro + cabeça é ponto fraco

**Antes o dano testava só um círculo na cabeça** (`e.pos` + `e.max_r`), então uma cobra de
322 px era atingível em ~5 % do corpo — o jogador sentia "acertei mas não contou".
- **`Lizard.body_points()`** amostra a espinha (juntas 0, ¼, ½, ¾, fim, com o raio local) e
  **`hit_test(pos, raio)`** devolve `None` / `'body'` / `'head'`. Mesmo padrão do
  `collision._samples`.
- Usado por **todas** as fontes de dano: dash (`game._collisions`), projéteis
  (`_update_projectiles`) e auras/orbitais/poças (`weapons._enemies_in`).
- **Cabeça = crítico** (`config.CRIT_MULT`) com spark dourado + popup "CRITICO!"
  (`game.crit_fx`).
- **Destaque da cabeça** (`AILizard._draw_weakpoint`): um **halo suave** da cor do corpo
  clareada, desenhado **antes** do corpo (por isso `draw()` chama antes de `super().draw`)
  — brilha em volta da silhueta sem cobrir os olhos. *Já foi uma retícula/alvo: parecia UI
  colada na criatura. Mantenha orgânico — cor/brilho, nunca marcas de mira.*

## Vida visível

- **Jogador**: barra no HUD com a rampa `palette.health_color` (verde→amarelo→vermelho;
  uma mistura de 2 paradas vira oliva sujo no meio, por isso a rampa tem 3).
- **Inimigos**: `AILizard._draw_health` desenha uma barrinha acima da cabeça **só quando
  feridos** (some em vida cheia p/ não poluir). Escala por `max_hp` — se você ajustar o
  `hp` depois do spawn, chame `sync_max_hp()` (species/rounds já fazem).
- **Chefes**: sem barrinha; usam a **barra grande no topo** (`rounds.draw_boss_bar`).
- **Amigos**: além da barrinha, a **cor do corpo desbota** conforme enfraquecem
  (`AILizard._fade_by_vitality`: interpola de `base_color` até um cinza-lavanda usando o
  **pior** entre `hp/max_hp` e `life/FRIEND_LIFE`), e piscam nos últimos 5 s antes de sumir.
  Como todo o desenho lê `self.color`, basta atualizar essa cor que corpo/pernas/rim/glow
  acompanham.

## Juice / feel

- **Hit-stop**: `game.punch(freeze, shake, flash)` — o loop de `app.py` **pula os passos de
  simulação** enquanto `game.hitstop > 0` (continua desenhando). Usado em dash-kill (0.07s),
  dano no jogador (0.05s) e **morte de chefe** (0.22s + flash branco).
- **Transições**: `ui.Fade` (fade curto) ao entrar numa run e a cada troca de estado
  (play ↔ camp ↔ levelup ↔ victory/over) e entre telas do menu.
- **Menus animados (estilo Vampire Survivors)**: `menu._menu_list` recebe um dict `anim`
  (`{'t', 'sel_f'}`) e faz **drop-in escalonado** dos itens (slide + fade, cada um ~45 ms
  após o anterior) e um **destaque que desliza** entre as opções (`sel_f` persegue `sel`),
  com o item selecionado pulsando levemente.
- `ui.fit(font, texto, largura)` trunca texto com "..." para nada vazar das caixas.

## Ícones e áudio (gerados em código)

- `icons.py`: cada arma/mutação/charm tem um desenhador procedural; `icons.draw(surf,
  id, centro, raio, cor)`. Ids batem com `weapons.WEAPONS`, `evolution.MUTATIONS`
  (`Mutation.icon`) e `charms.CHARMS`. Fallback = disco, então id novo nunca quebra.
- `audio.py`: `init()` sintetiza **19 SFX** (3 variações de pitch cada; inclui um por
  arquétipo de arma: `w_spit`/`w_homing`/`w_web`/`w_aura`/`w_orbit`/`w_puddle`) + 4 loops
  generativos; `play(nome, vol)` e `set_music('calm'|'combat'|'boss'|'victory')`. **Se o pygame
  não tiver `mixer`, tudo vira no-op** e o jogo roda mudo (verificado).

## Decisões de performance (Python) — mantenha

- **Timestep fixo** (`config.DT`, 60 Hz) com acumulador em `app.py`; render
  desacoplado → animação estável independente de FPS. Cap de passos evita spiral.
- Vetores com `pygame.Vector2` + `math` (numpy escalar é mais lento por overhead).
- **Culling** por `Camera.visible` em criaturas, flora e partículas.
- Partículas **pooled** com teto (`FX.MAX`); sombras e cores de tile **cacheadas**.
- Orçamento de entidades (insetos/presas repopulam por probabilidade, com limite).
- Custo medido: ~0.5ms step + ~3.3ms draw por frame com round cheio (larga folga).
- `display.present()` usa **smoothscale** (arte vetorial fica nítida ao escalar). É
  **CPU**: 2,2 ms/frame no 2x, 3,8 ms no 3x — por isso a taxa de render importa tanto.

### `RENDER_FPS = SIM_HZ` — não aumente

A simulação é fixa em `SIM_HZ` e **o desenho não interpola entre estados**. Renderizar
acima disso só **redesenha frames idênticos**: era 120 contra 60 de simulação, ou seja
**2x o custo de `draw` + `smoothscale` + `flip` por zero ganho visual** (a GPU do usuário
ficava em 100% com consumo baixo — muito flip, pouco trabalho útil). Se um dia quiser
render acima da simulação, precisa **implementar interpolação** antes.

### `palette.glow` — a chave do cache TEM que ser grossa

`_GLOW_CACHE` guarda um `Surface` por `(raio, cor)`. Os três eixos são **contínuos na
prática**: o raio encolhe com a vida da partícula e escala com o zoom; a intensidade é uma
senoide pulsante em vários dos ~29 call sites; e **cada criatura nasce com cor aleatória**,
que os bursts de `fx` herdam. Sem quantizar, o cache **crescia sem limite** — medido:
459 → 1843 entradas e **24,6 → 115,7 MB** de surfaces em ~7 min de jogo (RSS 364 → 470 MB),
o que fazia sessões longas travarem. Hoje:
- `_quantise_radius` (degraus 2/4/8 px conforme o tamanho) + cor em **4 bits/canal**
  (`& 0xF0`) aplicada **depois** de dobrar a intensidade → pulsos e cores parecidas
  colapsam no mesmo sprite (o gradiente aditivo esconde o banding);
- **teto `_GLOW_MAX = 900`** com `clear()` ao estourar (mais previsível que LRU).
- Resultado medido: a curva **fica plana** (~35-47 MB, estável). **Ao adicionar um glow
  novo, não reintroduza intensidade/raio contínuos como chave.**

### Nada de `Surface` de tela cheia por frame

`ui._tint(surf, cor, alpha)` é o único caminho para escurecer/clarear a tela inteira:
reusa **uma surface cacheada por cor** com `set_alpha` (blit mais rápido que alpha
por-pixel). Usado por `ui.Fade`, `ui.veil`, o véu das telas de jogo (`game._veil`) e o
flash branco. Alocar `Surface(SRCALPHA)` a cada frame custava ~6 ms **e** gerava lixo.

## Pronto para online (não implementado ainda)

Todo input passa por `Controller`. Um `NetworkController` (inputs vindos da rede)
plugaria sem tocar na simulação. O timestep fixo/determinístico já favorece isso.
Coop atual é **local** apenas.

## Convenções

- Ângulos em **graus** (via `Vector2`/`math`); `y` cresce para baixo (tela).
- Novo tipo de criatura: subclasse de `Lizard`/`AILizard` reusando espinha+pernas.
- Novo bioma/flora: edite `BIOMES` e `_PROP` em `world.py`.
- Ao mudar algo com efeito visível, rode `--smoke` e, de preferência, gere um
  screenshot headless (blit para `Surface(...,0,24)` e salve BMP→PNG; o driver
  dummy não salva PNG do surface de display direto).

## Documentação — como manter consistente

Estrutura no repo (Matt Pocock ecosystem — leia isto antes de mexer em qualquer `.md`):

```
CONTEXT.md               ← glossário de domínio (um lugar só, palavra canônica)
docs/
├── README.md            ← índice da árvore de docs
├── adr/                 ← Architecture Decision Records (UM arquivo por decisão, NNNN-slug.md)
│   └── README.md        ← formato + índice
├── concepts/            ← docs de conceito (UM arquivo por conceito, cross-linkado)
│   └── README.md        ← índice
└── agents/              ← convenções operacionais para agentes (issue tracker, labels)
```

**Regra número um: um conceito por arquivo.** Se um `.md` cobre 5 coisas, ele
não é um doc — é uma pilha. Quebre. `CONTEXT.md` é a exceção (é um índice de
termos), e mesmo assim é _plano_, não hierárquico.

**Regra número dois: uma palavra por conceito.** `CONTEXT.md` lista o termo
canônico e os `_Avoid_` (sinônimos a evitar). Prosa em docs, mensagens de
commit, PRs e comentários usam o termo canônico. Se você inventou uma palavra
nova, ou ela vira canônica em `CONTEXT.md` (adicione no mesmo commit) ou você
está desviando (repense).

**Regra número três: cross-links, não repetição.** Um doc introduz UM conceito
e aponta para os relacionados: `[Genome](../concepts/genome.md)`,
`[ADR-0007](../adr/0007-cosmetic-skeleton-for-tail.md)`. Nunca duplique a
definição de outro conceito — linke.

### Quando editar cada arquivo

Faça na MESMA sessão do código, senão a doc pega ferrugem:

| Você mexeu em… | Atualize… |
|---|---|
| Nome / significado de um termo do jogo (Genome, Charm, Might, Mood…) | `CONTEXT.md` (renomeia canônico; mantém antigo em `_Avoid_` se ainda aparece na base) |
| Arquitetura ou trade-off difícil de reverter | Novo ADR em `docs/adr/NNNN-slug.md`; adiciona linha no índice de `docs/adr/README.md` |
| Comportamento observável de um conceito existente (spine, boss FSM, camp modes…) | O `docs/concepts/<conceito>.md` correspondente |
| Um novo conceito nasceu no código | 1) entrada em `CONTEXT.md`, 2) `docs/concepts/<slug>.md`, 3) link nos conceitos que o mencionam |
| Fluxo operacional (issue tracker, labels, skills) | `docs/agents/*.md` |
| Este `CLAUDE.md` | Só o pedaço que ficou desatualizado, cirurgicamente. NÃO transforme isto num changelog. |

### Quando NÃO criar um ADR

Um ADR só existe se as TRÊS forem verdade: (1) difícil de reverter,
(2) surpreendente sem contexto — alguém no futuro vai perguntar "por quê?",
(3) foi um trade-off real. Se faltar uma, é comentário no código ou mensagem
de commit, não ADR. Ver `docs/adr/README.md`.

### Convenção de commit — um arquivo, um commit

Docs são commitados **granularmente**: um arquivo por commit, mensagem que
diz o QUE virou canônico e POR QUÊ. Assim `git log -- docs/` conta a
história de decisões, não a história de "atualizei umas coisas". Push
direto na `main` (é como este repo trabalha; ver git log recente).

Exceção: se um único termo/decisão exigir editar N docs de uma vez (renomear
`Might` afeta CONTEXT.md + 3 concept docs + 2 ADRs), aí é UM commit para o
conjunto — o commit é a unidade de _decisão_, não de arquivo.

### Antes de escrever novo doc — cheque se já existe

`grep -r "TERMO" docs/ CONTEXT.md` primeiro. Se o conceito já tem lar,
edite o existente. Duplicata é o pecado mortal do sistema (dois docs
divergem em silêncio e ninguém sabe qual vale).

### Agent skills

- **Issue tracker**: GitHub Issues via `gh`. Ver `docs/agents/issue-tracker.md`.
- **Triage labels**: cinco rótulos canônicos. Ver `docs/agents/triage-labels.md`.
- **Domain docs**: single-context — `CONTEXT.md` + `docs/adr/` na raiz. Ver `docs/agents/domain.md`.
