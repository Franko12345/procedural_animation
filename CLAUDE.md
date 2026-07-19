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
Dependências: `pygame`, `numpy` (numpy é legado dos arquivos de referência; o jogo
usa `math` + `pygame.Vector2`). Teste headless: prefixe `SDL_VIDEODRIVER=dummy
SDL_AUDIODRIVER=dummy`.

## Arquitetura (pacote `lagarto/`)

Um módulo por responsabilidade — mantenha assim; não volte para arquivo único.

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Constantes (janela/mundo, timing, **paleta vívida**). Ajuste de cores/balanço começa aqui. |
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
| `menu.py` | Tela inicial (1/2 jogadores) com demo ao vivo sobre o mundo. |
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

- **P1**: WASD mover · mouse mirar · clique-esq/ESPAÇO dash · clique-dir/SHIFT língua.
  No single-player, um **gamepad também controla o P1** (híbrido — usa o que estiver
  ativo; `KeyboardMouseController(joy)`), então dá pra jogar sem mouse.
- **Língua com auto-mira**: mira sozinha no alvo mais próximo no alcance
  (`game.nearest_edible` — sem cone) e **custa energia** (8). Dispensa mouse.
- **P2** (coop): gamepad (sticks + A/X) se detectado, senão setas + IJKL + RCtrl/RShift.
- **Janela**: `pygame.SCALED | RESIZABLE` (resolução lógica fixa, mouse mapeado
  automaticamente); **F11** alterna tela cheia; a janela é arrastável p/ redimensionar.
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
- **Dano fracionado** de auras/orbitais/poças via `AILizard.damage(game, amount)`.

Extras manuais: **dash** (contato + i-frames + **chain**: matar com dash recarrega o
dash e devolve energia), **língua-chicote** (mira no mais próximo entre comida/inimigo;
inimigo leva dano + é puxado; custa energia), **habilidade ativa** (a fazer no camp).
**Combo/streak** (`game.combo`): matar sobe o multiplicador (decai se você foge).

**Colisão:** aliados (`kind ∈ {player,friend}`) **não colidem entre si** (`collision.py`
`FRIENDLY`) — batalhas fluidas; inimigos ainda colidem normalmente.

## Ondas em rounds (`rounds.py`) + Acampamento

`RoundManager` substitui o antigo `update_waves`. Cada round tem um **tema** (`THEMES`:
enxame/cuspidores/tanques/aranhas/invasao) anunciado por **banner**; inimigos **pingam**
de **`Nest`** (POIs destrutíveis, com boca que brilha antes de emitir) via **`SpawnMark`**
(telegraph que cresce no chão) — nunca um dump só, e nunca em cima do jogador. Destruir
os ninhos (dash/cuspe) corta o fluxo. `game.rounds.draw_world`/`draw_banner`.

**Acampamento** (estado `camp`, entre rounds): ao limpar (`rounds.state=='cleared'`) o
`game._enter_camp()` abre uma tela com **loja do besouro** (gasta **pólen** — moeda da
run ganha por kill × combo, `game.add_pollen` — em cura/vida/vigor/frenesi/ovo de amigo;
custo sobe a cada compra) + **escolha de rota** (3 portas = tema da próxima onda + bônus
cura/pólen/carta). Escolher a rota chama `rounds.request_next(theme)`. Input em `app.py`
(1-5 compra, setas+ENTER/clique escolhe a rota). Desenho: `game._draw_camp`.

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

## Gameloop / objetivo

Explorar → comer insetos/frutas → **crescer a cauda** (junta a mais) e energia →
chocar ovos vira **amigos** que seguem e lutam. **Ondas** de predadores escalam.
Dash atravessa e mata predador; ser atingido tira coração; cair = "down" (parceiro
revive tocando); todos caídos = fim de jogo. **Score** = comida + abates + crescimento.

## Decisões de performance (Python) — mantenha

- **Timestep fixo** (`config.DT`, 60 Hz) com acumulador em `app.py`; render
  desacoplado → animação estável independente de FPS. Cap de passos evita spiral.
- Vetores com `pygame.Vector2` + `math` (numpy escalar é mais lento por overhead).
- **Culling** por `Camera.visible` em criaturas, flora e partículas.
- Partículas **pooled** com teto (`FX.MAX`); sombras e cores de tile **cacheadas**.
- Orçamento de entidades (insetos/presas repopulam por probabilidade, com limite).
- Custo medido: ~0.2ms step + ~1.1ms draw por frame (larga folga).

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
