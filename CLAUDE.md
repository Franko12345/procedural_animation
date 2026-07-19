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
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`. **O jogo não usa nenhum arquivo de
asset** — arte, ícones, som e música são todos gerados em código.

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
| `species.py` | **Genomas-template** + metadados (role, xp, score, `grants`, `diet`). `make()` spawna variação. Roster: grazer/critter/frog/fish (presa), runner/tank/snake/horned/spiky/spider/spitter/scorpion (inimigo). |
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
- **Como a cauda se move**: a espinha é follow-the-leader e `spine.resolve` **reescreve
  todas as juntas todo frame** (e `collision.separate` re-resolve depois) — *deslocar junta
  não funciona, é apagado no mesmo frame*. Em vez disso o golpe dá um **impulso lateral na
  velocidade do jogador**, e a cauda chicoteia sozinha pelo follow-through. O lado é
  escolhido pelo produto vetorial com o inimigo mais próximo (senão alterna).
- **Hitbox = as juntas reais** (`spine.joints[-3:]`) com alcance explícito `max_r*1.15`
  (o `radii` da ponta é ~0.22*max_r, pequeno demais). O que você vê é o que acerta;
  cabeça do inimigo ainda dá crítico.
- **`whip_hits`** (set, limpo no disparo) = **um acerto por alvo por golpe**, mesmo padrão
  de `dash_hits`. Sem isso o bug de dano-por-frame volta.
- **Modificadores da cauda** (era tudo cosmético antes): `club` → `WHIP_CLUB_MULT` de dano
  + `WHIP_KNOCK_CLUB` de empurrão + shake maior; `sting` → `apply_poison`. *Nota: o ferrão
  dos **inimigos** aplica `apply_slow`, o do jogador envenena — divergência proposital.*
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
profundidade de sobreposição em `creature.clog`; `Player.update` normaliza por `max_r*1.2`,
suaviza (`clog_f`, `approach` 9/s) e aplica `C.CONTACT_DRAG` (0.55) — pico de ~60% da
velocidade quando enterrado, **ignorado durante o dash** (atravessar é a graça).
*Inimigo↔inimigo continua com separação dura* — sem isso volta o bug de empilhar.

## Ondas em rounds (`rounds.py`) + Acampamento

`RoundManager` substitui o antigo `update_waves`. Cada round tem um **tema** (`THEMES`:
enxame/cuspidores/tanques/aranhas/invasao) anunciado por **banner**; inimigos **pingam**
de **`Nest`** (POIs destrutíveis, com boca que brilha antes de emitir) via **`SpawnMark`**
(telegraph que cresce no chão) — nunca um dump só, e nunca em cima do jogador. Destruir
os ninhos (dash/cuspe) corta o fluxo. `game.rounds.draw_world`/`draw_banner`.

**Acampamento** (estado `camp`, entre rounds): ao limpar (`rounds.state=='cleared'`) o
`game._enter_camp()` abre uma tela com **loja do besouro** (gasta **pólen** — moeda da
run ganha por kill × combo, `game.add_pollen` — em cura/vida/vigor/charm/ovo de amigo;
custo sobe a cada compra; **charm custa 150** por ser permanente e forte) + **escolha de
rota** (3 portas = tema da próxima onda + bônus cura/pólen/carta). Escolher a rota chama
`rounds.request_next(theme)`. Desenho: `game._draw_camp`.

**Navegação do camp — um modelo só para teclado e gamepad** (`app._camp_nav`). Antes eles
discordavam: o pad tinha um flip binário loja↔rota e as setas do teclado **ignoravam o
`focus`** (mexiam sempre na rota); e **charms só davam para equipar com o mouse** —
`camp_equip` tinha um único call site. Hoje as áreas seguem a ordem da tela:
**loja → charms → rota** (a de charms some quando você não tem nenhum).
- **Charms em grade, uma coluna por slot** (`C.CHARM_SLOTS`): cada charm aparece **sob o
  cabeçalho do seu próprio slot**, o que deixa óbvio o que ele substitui. Esquerda/direita
  troca de coluna (pulando slots vazios), cima/baixo anda na coluna e **só sai da grade
  nas pontas** (`game.camp_move_charm` devolve `False` aí).
- `camp_equip(cid)` recebe **id**, não índice — diferente de `camp_buy`/`camp_pick_route`.
  `game.camp_equip_cursor()` resolve coluna+linha → `cid`.
- **Espaço vertical é apertado**: sobram 142 px entre os charms (y=328) e o label das rotas
  (y=470), e o slot `back` tem 4 charms. Ao mexer no layout, teste com **todos os charms**,
  não com o caso vazio.

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
