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

## AGORA — Fase B2: balanço
- [ ] Rabada — encolher hitbox e deslocar p/ perto da ponta (`_whip_span`, `reach`); suavizar escala de dano
- [ ] Regen — `+4/s` por carta é rápido demais; reduzir/suavizar empilhamento
- [ ] Abate dá pouca energia — em `die()`, `+energia` ao jogador próximo

## Fase B3: barras bio
- [ ] Vida/energia/XP orgânicas em `_draw_hud` (membrana pulsante, flagelos); cachear surfaces

## Fase B4: novas criaturas procedurais
- [ ] Corpos novos (tentáculo / segmentado / radial variado) — refs RujiK, Codeer, Sebastian Lague
- [ ] Entram como inimigos comuns (`species.py` + behavior); alguns viram chefes
- [ ] `genome.__slots__` — declarar atributo novo (armadilha recorrente)

## Fase 4c: acampamento físico (retomar)
- [ ] Clareira com barraca (encostar abre compra) + 3 portas (atravessar avança)

## Fase 5/6: chefes
- [ ] Framework FSM + padrões de projétil como dados + telegrafia ≥27 frames
- [ ] 10 chefes + PRIMORDIAL final (alguns usam os corpos da B4)

## Fase M: música adaptativa
- [ ] Stems por intensidade via `/music-generator`; mixar ao vivo por vida/inimigos/combo/chefe
- [ ] Carregar se existir, senão fallback synth numpy (headless/CI verdes)

## Fase 7: arte PNG
- [ ] `assets/` + `lagarto/assets.py` (`_MEIPASS`, lazy, fallback `icons.draw`)
- [ ] Ícones sem colisão de forma, legíveis de r=8 a r=30
