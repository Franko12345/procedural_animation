# CURRENT_PLAN — Lagarto

Plano tangível e editável. Marque `[x]` quando pronto. O raciocínio longo mora em
`~/.claude/plans/analise-o-repositorio-do-swift-gem.md`; **este** é a fonte da verdade do
que falta. Atualizado a cada commit.

## Ordem
`B1 bugs → B2 balanço → B3 barras bio → B4 criaturas → 4c acampamento físico → 5/6 chefes → M música → 7 arte`

Regra: paro sempre numa fronteira jogável; `--smoke` verde antes de cada commit.

---

## Feito
- [x] Fase 1 — texto, TopStack, dano por onda, dash/rabada com might
- [x] Fase 2 — 4 inimigos por hábito + campeões (`d8f4344`)
- [x] Fase 3 — 4 personagens + rebuild_body + seleção viva (`5ec49c5` `07902cd` `9037b31`)
- [x] Fase 4 itens — ativos, passivos, qualidade/pools, 12 sinergias, Synergy Factor, ícones (`89c61a1` `26bb438`)
- [x] Playtest — colisão só por inimigo, ferrão, F3 velocidade (`44e709c` `ea8b5c2` `f9b1cdc`)

---

## Fase B1: bugfixes — FEITO (commit pendente)
- [x] Som de menu no teclado
- [x] Seleção de personagem por controle (stick L/R) + limpar pendente ao cancelar
- [x] Abrir/fechar pausa com o controle (botão **Start** — antes só ESC de teclado)
- [x] 6 itens mortos ligados, cada um testado pelo **efeito**:
  Farpas (piercing), Arremesso, Sanguessuga, Contragolpe, Espiral, Ímã (coletáveis)
- [x] Fim de run volta ao menu (ESC / B); ENTER / A reinicia

## Fase B2: balanço — FEITO (commit pendente)
- [x] Rabada — hitbox = 3 juntas da ponta (era metade do corpo) + reach 1.6→1.05; clava 2.6→2.3. Medido: 7/12 → 2-3 alvos por golpe
- [x] Regen — `+4/s` → `+2.2/s` por carta
- [x] Abate dá energia — `+4` ao jogador mais próximo (KILL_ENERGY), coop-safe

## Fase B3: barras bio — FEITO (commit pendente)
- [x] `_bio_bar`: membrana arredondada, menisco pulsante na ponta, brilho interno, flagelos que balançam (só na vida). Sem Surface por frame; 0,23 ms p/ o HUD de 2 jogadores.

## Fase B4: novas criaturas procedurais — FEITO (commit pendente)
- [x] `genome.plan` (declarado no `__slots__`) — fork de corpo, ao lado do `radial`
- [x] **CENTOPEIA** (`plan='segmented'`): cadeia de aneis + marcha metacronal de patinhas.
      Mecânica **cavadora** (`behavior='burrow'`, Para-Bite do Isaac): superfície →
      **telegrafo de mergulho** (cava um buraco, afunda) → intangível por baixo (mound +
      **anel de erupção** no chão + trilha de terra) → aflora e estoura. Pune acampar/andar reto.
- [x] **POLVO / KRAKEN** (`plan='tentacle'`): manto pulsante + braços **contínuos** (mesma
      técnica de contorno da espinha, tapered), que ondulam e chicoteiam. Mecânica
      **agarradora** (`behavior='grapple'`, Gripmaster do Gungeon): fecha, enraíza, **estica
      os braços** (telegrafo >27f), e no estalo te **puxa + retarda**. Pune kitar de perto.
- [x] Entram nas ondas (`species.py` + THEMES `tanques`/`aranhas`/nova `toca`)
- [x] **Modificador DIVISOR** (Blobulon/Fistula): racha em 2 cópias menores ao morrer.
      Fila diferida (`game.spawn_enemy`) p/ não mutar a lista durante o laço que o mata.
- [x] Bodies prontos p/ virar **chefes** na Fase 5/6 (KRAKEN em escala ~2.2x já renderiza)
- [x] Testado: `--smoke 500` verde; teste dirigido (todos os estados disparam, sem crash);
      screenshots dos 3 telegrafos (dig / underground / grab)

## Fase 4c: acampamento físico — FEITO (commit pendente)
- [x] Clareira andável (estado `camp`, `camp['mode']` = `field`/`shop`): tenda + 3 portas
      posicionadas em volta de onde a onda foi limpa. `_step_camp` move os jogadores em
      `field`; `_draw_camp_pois` desenha tenda/portas no mundo.
- [x] **Encostar na barraca** abre a loja (mesmo menu de antes, agora só loja+charms);
      **atravessar uma porta** chama `_apply_route` e avança (portas = rotas, no mundo).
- [x] Loja é **escolha, não pedágio** — dá pra ir direto na porta. `reopen_cd` evita reabrir
      no mesmo passo; fechar a loja só trava com compra em absorção (`pick`), não no drop-in.
- [x] Reusa `ctrl.poll`/`cam.follow` (já rodam todo frame) — movimento no `field` é só chamar
      `player.update`. Teclado/gamepad/mouse do menu **só no modo shop**; ESC/B fecha a loja.
- [x] Testado ponta a ponta (entra → anda → toca tenda → loja → fecha → cruza porta → play);
      `--smoke 400` verde; screenshots da clareira e da loja.

## Fase 5/6: chefes
- [ ] Framework FSM + padrões de projétil como dados + telegrafia ≥27 frames
- [ ] 10 chefes + PRIMORDIAL final (alguns usam os corpos da B4)

## Fase M: música adaptativa
- [ ] Stems por intensidade via `/music-generator`; mixar ao vivo por vida/inimigos/combo/chefe
- [ ] Carregar se existir, senão fallback synth numpy (headless/CI verdes)

## Fase 7: arte PNG (EM ANDAMENTO — geração de assets)
Pedido do usuario: gerar assets com o skill /pixel-art-gen. Icones 16/32, coisas
detalhadas (loja do besouro etc.) em 64/80. Mais organico, curvas, AA.
- [x] Ferramenta de autoria `pxgen.py` (scratchpad): shapes como mascaras de cobertura
      (supersample) + pintura de volume rampa-4 (highlight/base/shade/edge) + AA manual
      na borda + contorno **sel-out** (tom escuro do fill, nao preto). Emite JSON do skill
      e chama `render_pixel_art.py`. Guia: Pixel Parmesan / Lospec / Pixnote.
- [x] Lote 2 (32x32 + 80, `c026b55`): coin_pollen, health, cuspe, tent_beetle.
- [x] Lote 3 (32x32, `c026b55`): 7 armas restantes (ferrao teia esporos feromonio
      sopro enxame acido) — as 8 armas de `icons.py` completas.
- [x] Lote 4 (32x32, `6eb237a`): 8 icones de mutacao-stat que **colidem de forma**
      no `icons.py` (`_bolt`: speed/energy/might; `_arrow`: dash/ferrao) — speed
      energy might xp area haste amount dash. Refinamento em `batch4b.py`
      (might/dash reprovados na 1a passada, redesenhados: punho com sulcos, pata
      com 3 dedos+almofada+trilha).
- [x] Lote 5 (24x24, `1147304`): pickups — pickup_fruit pickup_egg pickup_bug.
- [x] Lote 6 (32x32, `1e656c6`): 9 de 10 charms — antenas presas olhos carapaca
      espinhos asas glandula nectar clava. `glandula`/`nectar` tambem colidiam
      (`_sac`); saem distintos (cacho verde vs gota ambar).
      **Charm `ferrao` pulado de proposito**: usa o MESMO id `'ferrao'` que a arma
      no dict de `icons.py` (dois conceitos, uma chave) — ja existe `ferrao.png`
      pra arma; gerar outro pro charm exigiria separar os ids no codigo primeiro.
      Documentado em `tools/pixelart/README.md`.
- **Total: 31 PNGs** em `assets/icons/` (32x32 armas+stats+charms, 24x24 pickups)
  + `assets/props/` (80x80 tent_beetle). Geradores versionados em `tools/pixelart/`
  (`pxgen.py` = camada de autoria; `batch2..6.py` = lotes; `README.md` documenta).
- [x] **Pipeline ligado** (`755b445`): `lagarto/assets.py` (`resource_path`/`_MEIPASS`,
      lazy, `.convert_alpha()` so apos `display.init`, cache `(id,diametro)` teto 300)
      + `icons.draw` tenta PNG primeiro, cai pro procedural se `None`. Verificado em
      runtime real (screenshot HUD + carta EVOLUIR mostrando `xp.png` de verdade).
      Invariante "zero assets" quebrada de proposito, documentado no CLAUDE.md.
- [x] `build.py --add-data` p/ empacotar `assets/` no executavel PyInstaller (`9b1ba7c`).
- [ ] Nitidez: pre-escala NEAREST por fator inteiro antes do `present()` borrar
      (hoje `smoothscale`; aceito por ora — confirmado visualmente nitido nos
      screenshots reais de HUD/carta, baixa prioridade).
- [ ] `tent_beetle.png` gerado mas **NAO ligado** — `_draw_camp_pois` continua
      procedural (tem a animacao de queda do ceu; integrar o PNG e mais invasivo).
- [ ] Assets restantes possiveis: props do acampamento (portas, ninho), flora/mundo.

Geradores versionados em `tools/pixelart/` (reproduzivel). Build sem `assets/`
continua rodando (fallback procedural cobre qualquer PNG faltando).

### Ajustes pendentes

- [ ] Fazer dificuldade escalar mais rapidamente durante a run.
- [ ] Aumentar progressivamente HP, velocidade, quantidade de inimigos e campeões um pouco mais rapido.
- [ ] Evitar efeito snowball onde jogador deixa de correr risco no meio da partida.

---

### Correções pendentes

- [ ] Investigar lentidão que aparece após crescer alguns níveis. Desta vez não houve queda de FPS, apenas colisões excessivas. Suspeita principal: hitboxes ou broadphase. ![alt text](image-1.png) ![alt text](image.png)
- [ ] Instrumentar sistema de colisão para medir:
  - número de hitboxes
  - testes de colisão por frame
  - tempo gasto em broadphase e narrowphase
- [ ] Verificar se `rebuild_body()` está duplicando segmentos ou colliders.
- [ ] Confirmar que segmentos antigos são removidos corretamente da estrutura de colisão.

### Renderização

- [ ] Tornar outline consistente em todas as partes do corpo.
- [ ] Adicionar outline nas pernas.
- [ ] Adicionar outline na língua.
- [ ] Melhorar continuidade do outline entre segmentos.
- [ ] Aumentar levemente a pixelização da imagem.

### Língua

- [ ] Aumentar espessura da língua.
- [ ] Reescrever animação usando cinemática inversa (IK).
- [ ] Movimento procedural semelhante ao de um camaleão.
- [ ] Alongamento, retração e curvatura mais naturais.
- [ ] Estudar língua do camaleão real.
- [ ] Analisar língua do lagarto de Rain World como referência.

### Evoluções

- [ ] Remover cauda-clava da árvore de evolução.
- [ ] Manter cauda-clava apenas como Charm.

### Assets restantes

- [ ] Pré-escalar usando NEAREST antes de `present()`.
- [ ] Integrar `tent_beetle.png` ao acampamento.
- [ ] Criar props restantes (portas, ninho, flora e elementos do mapa).

---

## Pesquisa — animação procedural

Objetivo: absorver técnicas para elevar qualidade de movimentação de criaturas, chefes e jogador.

### Referências

- [ ] Estudar profundamente:
  - https://www.youtube.com/watch?v=sVntwsrjNe4
  - https://medium.com/@merxon22/recreating-rainworlds-2d-procedural-animation-part-1-4d882f947e9f
  - https://www.youtube.com/watch?v=PcpkBzcRdSU
  - https://youtu.be/wgpgNLEEpeY?si=8YfssF0-jhYjGSkA

### Documentação

- [ ] Anotar técnicas utilizadas.
- [ ] Documentar princípios, vantagens e limitações.
- [ ] Adaptar cada técnica para arquitetura do Lagarto.

### Técnicas para estudar

- [ ] IK (CCD/FABRIK)
- [ ] Follow chains
- [ ] Restrições articulares
- [ ] Secondary motion
- [ ] Phase offsets
- [ ] Damping
- [ ] Procedural posing
- [ ] Spline dinâmica
- [ ] Squash & Stretch
- [ ] Anticipation
- [ ] Weight e overlap
- [ ] Ground adaptation

### Resultado esperado

- [ ] Criar guia interno reutilizável para futuras criaturas, chefes e animações procedurais do projeto.