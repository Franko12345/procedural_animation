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
- [x] Lote 2 (32x32 + 80): coin_pollen, health (coracao), cuspe (glob veneno),
      tent_beetle (loja). Sombreamento esferico, curvas orgânicas. **Aprovado o estilo.**
      Scripts: `scratchpad/pxgen.py` + `batch2.py`. PNGs em scratchpad.
- [ ] Gerar restante dos **8 icones de arma** (ferrao/teia/esporos/feromonio/sopro/enxame/
      acido) + mutacoes/charms, mesmos ids de `icons.py` (fallback disco nunca quebra).
- [ ] **Pipeline** `assets/` no repo + `lagarto/assets.py` (`resource_path`/`_MEIPASS`, lazy,
      `.convert_alpha()` so apos `display.init`, fallback `icons.draw`). `build.py --add-data`.
- [ ] Nitidez: pre-escala NEAREST por fator inteiro antes do `present()` borrar.

Nota: os PNGs ainda **nao estao ligados** ao jogo (falta `assets.py`). Gerar primeiro,
ligar depois. Manter os geradores no repo (reproduzivel, zero-asset ainda roda).
