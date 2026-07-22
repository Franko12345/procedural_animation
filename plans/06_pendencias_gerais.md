# Plano 06 — Pendências Gerais (todos os pedidos não implementados)

Compilado exaustivo de tudo que o usuário pediu e ainda não foi feito. Organizado por prioridade/tipo.

---

## 1. 🔧 Performance — colisão lenta após níveis

Pedido: investigar lentidão que surge ao crescer alguns níveis. Suspeita: hitboxes ou broadphase.

- [ ] Instrumentar sistema de colisão (`collision.py`): nº hitboxes, testes/frame, tempo broadphase/narrowphase
- [ ] Verificar `rebuild_body()` duplicando segmentos ou colliders
- [ ] Confirmar que segmentos antigos são removidos corretamente da estrutura de colisão
- [ ] Medir com `--profile` e comparar antes/depois

---

## 2. 🎨 Outline consistente em todas as partes

Pedido: outline em pernas e língua, continuidade entre segmentos do corpo.

- [ ] **Plano 05**: implementar `outline_from_surf()` via `pygame.mask` em `utils.py` ou `outline.py`
- [ ] Aplicar em pernas (`leg.py`)
- [ ] Aplicar em língua (`lizard.py._draw_tongue`)
- [ ] Melhorar continuidade do outline entre segmentos do corpo
- [ ] Aumentar levemente a pixelização da imagem (`PIXEL_SCALE` — hoje = 1, foi desligado)

---

## 3. 👅 Língua — reescrita com IK

Pedido: língua mais grossa, animação procedural tipo camaleão, IK, alongamento/curvatura natural.

- [ ] Aumentar espessura da língua
- [ ] Reescrever animação usando cinemática inversa (IK) — FABRIK ou 2-bone
- [ ] Movimento procedural tipo camaleão (alongamento, retração, curvatura)
- [ ] Estudar língua do camaleão real e referência Rain World

---

## 4. 🧬 Evoluções — ajuste

- [ ] Remover cauda-clava da árvore de evolução (só Charm)
- [ ] Manter cauda-clava apenas como Charm

---

## 5. 📈 Dificuldade — escalonamento mais agressivo

Pedido: dificuldade escalar mais rápido durante a run.

- [ ] Aumentar progressivamente HP, velocidade, quantidade de inimigos e campeões mais rápido
- [ ] Evitar efeito snowball onde jogador deixa de correr risco no meio da partida

---

## 6. 👾 Chefes Endless (6 restantes de 10)

Pool de tier5+ (onda 25+). Ordem sugerida: corpo existente primeiro, corpo novo depois.

### 6a. Corpo existente (reuso)
- [ ] **ARANHA-REI** (corpo=`spider`): mecânica de teia + spawn de filhotes
- [ ] **SERPENTE CRISTAL** (corpo=`segmented`/centipede): estética cristal, padrões laser/barragem

### 6b. Corpo novo `winged`
- [ ] Implementar `genome.plan='winged'`: asas batendo com phase oscillator
- [ ] **TERROR ALADO**: mob voador que mergulha, ataque em sweep

### 6c. Corpo novo `orbital`
- [ ] Implementar `genome.plan='orbital'`: olho flutuante com anéis de projéteis
- [ ] **OLHO-SÍSMICO**: padrão radial + shockwave + gravity_well

### 6d. Corpo novo + arena
- [ ] **MURALHA**: precisa de sistema de confinamento/arena (mundo aberto contínuo, sem salas) — requisito de infra
- [ ] Implementar arena params mínimos (bordas/paredes temporárias)

### 6e. Boss final especial (mais trabalho)
- [ ] **ANKH**: 4 formas, dissolve em partículas, transição entre formas — candidato natural a `CosmeticSkeleton`

### 6f. Infra compartilhada
- [ ] Padrões de catálogo restantes: `laser_sweep`, `bounce`, `minefield`, `gravity_well`, `teleport_strike`
- [ ] Arena design individual por chefe (pilares/corredor/poças)

---

## 7. 🎵 Música adaptativa (Fase M)

Pedido: stems por intensidade, mix dinâmico.

- [ ] Gerar stems por intensidade via skill `/music-generator`
- [ ] Mixar ao vivo por: vida do jogador, nº inimigos, combo, chefe
- [ ] Fallback synth numpy se stems não existirem (headless/CI verdes)

---

## 8. 🖼️ Assets restantes

- [ ] Pré-escalar NEAREST por fator inteiro antes do `present()` (nitidez)
- [ ] Integrar `tent_beetle.png` ao acampamento (`_draw_camp_pois`)
- [ ] Criar props de acampamento (portas, ninho)
- [ ] Criar flora/mundo procedural assets
- [ ] Separar id do charm `ferrao` do id da arma `ferrao` para gerar o PNG do charm

---

## 9. 🧠 Código morto / infra não usada

Classes em `anim.py` que existem mas têm zero instâncias:

- [ ] `SpringDamper` (1D) — candidatos: placas, antenas, olhos, ângulos
- [ ] `PhaseOscillator` — substituir `math.sin(wobble * X + i * Y) * Z` espalhado em `parts.py`
- [ ] `Anticipation` — substituir timers raw em `_ai_lunge`, `_ai_ranged`, boss windup

---

## 10. 🎭 Sistema de pose por IA

- [ ] Pose por estado de IA: caçando agachado, fugindo baixo, agressivo arqueado
- [ ] `_ai_melee` com wind-up anticipation

---

## 11. 📚 Pesquisa e documentação

- [ ] Estudar referências:
  - Rain World GDC (https://www.youtube.com/watch?v=sVntwsrjNe4)
  - Merxon22 (https://medium.com/@merxon22/recreating-rainworlds-2d-procedural-animation-part-1-4d882f947e9f)
  - Procedural Animation in 5 Minutes (https://www.youtube.com/watch?v=PcpkBzcRdSU)
  - IK tutorial (https://youtu.be/wgpgNLEEpeY)
- [ ] Anotar técnicas e adaptar para arquitetura do Lagarto
- [ ] Criar guia interno reutilizável

---

## 12. 🧹 Organizacional (refatoração)

- [ ] Telegraph modularizado em `boss_telegraph.py`
- [ ] Identidade visual além do emblema (partes/props únicos no CORPO de cada chefe)
- [ ] `_ai_melee` com wind-up (rebalanceamento de fato)

---

## Adiados por decisão de arquitetura (não pendências)

- Ground Adaptation (§4) — jogo top-down flat, sem campo de altura
- `CosmeticSkeleton` genérico — YAGNI, revisitar se ANKH precisar
- Anticipation no jogador (dash/whip/tongue) — input buffer já existe, introduzir latência piora o feel
