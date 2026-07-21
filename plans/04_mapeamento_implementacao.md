# Mapeamento: Onde Aplicar Cada Técnica no Código Existente

## Propósito

Mapear cada técnica do plano `01_animacao_procedural_avancada.md` para arquivos, funções e linhas específicas no código atual. Sem implementação nova — só inventário do que existe e roteiro do que muda.

---

## Legenda

- **`técnica #N`** — refere-se à seção correspondente no plano principal
- **[A/B/C]** — fase de implementação por prioridade
- `arquivo.py:linha` — localização no código atual
- `✔` — já implementado
- `△` — parcial (existe mas incompleto)
- `✗` — não existe
- `?` — primitiva existe mas não instanciada

---

## 1. `anim.py` — Primitivas Reutilizáveis (Base)

As 4 classes já existem. O problema é que estão **subutilizadas**.

| Classe | Status | Instâncias no código | Deveria ter |
|--------|--------|---------------------|-------------|
| `SpringDamper` (1D) | ✔ | 0 | ~12 (chifres, barbatanas, placas, olhos, ângulos) |
| `Vector2Spring` (2D) | ✔ | 1 (`tail_spring` em `lizard.py:119`) | ~20 (cada junta da cauda, pontas de chifre, antenas, asas, tentáculos) |
| `PhaseOscillator` | ✔ | 0 | ~8 (barbatanas, espinhos, chifres, asas, corpo da cobra, sacos de esporo) |
| `Anticipation` | ✔ | 0 | ~7 (lunge, shoot_charge, grapple, dash, pulo, tongue, virada de direção) |

### Substituto imediato

Adicionar `self.osc = PhaseOscillator(...)` e `self.anticip = Anticipation(...)` nos lugares certos e substituir `math.sin(creature.wobble * X + i * Y) * Z` por `self.osc.offset(i)`.

---

## 2. `lizard.py` — Classe Base Lizard (~1950 linhas)

### 2.1 Construtor / `rebuild_body` (linhas 51-130)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 62 | `self.squash = 1.0` — escalar único | **#9 Pose** [B] | Squash por região: cabeça, corpo, cauda com amplitudes independentes |
| 63 | `self.wobble = random.uniform(0, TAU)` — tempo global único | **#5 Phase** [A] | Substituir por `PhaseOscillator` por parte (cada parte tem speed/amplitude própria) |
| 72 | `rebuild_body()` chamado uma vez | **#7 Damping** [A] | Armazenar parâmetros de animação por genoma na criatura |
| 106-112 | Spine com `bend=26` constante | **#7 Damping** [A] | `bend` vindo do genoma (cobra > tanque) |
| 113-121 | `tail_spring = Vector2Spring(tip, stiffness=10, damping=0.75)` — 1 spring na ponta | **#3 Spring** [A] | N springs (um por junta da cauda) com stiffness decrescente 12→6 |
| 119 | `TAIL_SPRING_JOINTS = 4` — só 4 juntas cosméticas pegam o overshoot | **#10 2Esq** [C] | Esqueleto cosmético inteiro (32+ pontos) com spring por ponto |

### 2.2 `steer()` (linhas 297-305)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 299 | `self.vel += (target_v - self.vel) * factor` — blend instantâneo | **#8 Antic** [A] | Antes de virar, 0.1s de desaceleração; criaturas pesadas têm wind-up maior |

### 2.3 `integrate()` / `update()` (linhas 307-340)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 321-322 | `leg.update(...)` — foot target fixo relativo ao corpo | **#4 Ground** [B] | Raycast do foot target até o chão, ajustar y |
| 325-327 | `tail_spring.target = spine.joints[-1]` — spring único | **#3 Spring** [A] | Spring chain: cada junta N..N-k persegue a anterior |
| 332-336 | `squash = approach(..., speed/max_speed)` — só por velocidade | **#9 Pose** [B] | + squash em impacto, landing, wind-up de ataque |
| 337 | `wobble += dt * 6` — hardcoded | **#5 Phase** [A] | Velocidade por genoma + `PhaseOscillator` dedicado |

### 2.4 `_cosmetic_joints()` (linhas 342-366)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 344-365 | Só 4 juntas, blend linear (0→1), suprimido durante whip | **#3 Spring** [A] + **#10 2Esq** [C] | N juntas cosméticas (32+), spring por ponto, Catmull-Rom entre sim-juntas |

### 2.5 Player — `_whip_arc()` (linhas 1007-1054)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 1039 | `env = math.sin(t * 2pi)` — whip puramente cinemático | **#3 Spring** [A] | Após whip, spring na cauda por 0.2s para follow-through |
| 352 (ref) | Tail spring mutado durante whip | **#3 Spring** [A] | Não mutar — deixar spring acumular energia, soltar no fim |

### 2.6 Player — Tongue (linhas 895-928)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 908 | Tongue aparece instantâneo no alvo | **#8 Antic** [A] | 0.1s de abertura de boca antes de atirar |
| 1141-1150 | Reach = `math.sin(t * pi)` — cinemático puro | **#3 Spring** [A] | Spring-damper na ponta da língua para lash na retração |

### 2.7 Player — Dash (linhas 860-886)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 873 | `vel = safe_norm(move) * max_speed * 3.0` — instantâneo | **#8 Antic** [A] | 0.08s wind-up: agachar (squash), partículas nos pés, depois lançar |

### 2.8 AILizard — AI Behaviors (linhas ~1300-1680)

| Função | Linha | O que faz hoje | Técnica | O que muda |
|--------|-------|---------------|---------|------------|
| `_ai_melee` | ~1390 | Contato instantâneo quando em range | **#8 Antic** [A] | 0.2s wind-up: arquear corpo, recuar, depois investir |
| `_ai_ranged` | ~1396 | `shoot_charge = 0.45` — só sparks, sem pose | **#8 Antic** [A] | + agachar, inclinar cabeça, glow na boca, molas tensas (stiffness++) |
| `_ai_lunge` | ~1422 | Wind-up 0.45s mas sem animação corporal | **#8 Antic** [A] + **#9 Pose** [B] | Agachar (squash→), puxar cauda, EXPLODIR com stretch |
| `_ai_bomber` | ~1458 | Fusível conta, sparks na cabeça | **#9 Pose** [B] | Corpo incha gradualmente, muda de cor conforme fusível queima |
| `_ai_burrow` (centopeia) | ~1549 | Corpo some, depois reaparece | **#5 Phase** [B] + **#6 Spline** [B] | Onda muscular ao mergulhar (segmentos ondulam spline-driven) |
| `_ai_grapple` (polvo) | ~1609 | Braços com sine wave, cinemático | **#3 Spring** [A] | Spring nos braços: quando grapple falha, braços estalam de volta (overshoot) |
| `_hop` (sapo) | ~1675 | Velocidade instantânea | **#8 Antic** [A] + **#9 Pose** [B] | 0.12s agachamento antes do pulo; squash na aterrissagem |
| Geral — update | ~1300-1388 | AI monolithic, sem pose por estado | **#9 Pose** [B] | Pose diferente por estado: hunting (agachado, cauda erguida), fleeing (baixo, cauda entre pernas), aggro (costas arqueadas) |

---

## 3. `spine.py` — Spine Follow-the-Leader (~89 linhas)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 36-44 | `resolve()` — puramente cinemático, sem spring/inércia | **#3 Spring** [A] | N últimas juntas perseguem a anterior com spring chain |
| 86-89 | `body_polygon()` — linhas retas entre juntas, vértices visíveis | **#6 Spline** [B] | Catmull-Rom entre juntas para contorno suave contínuo |
| 14-15 | `RADII_PROFILE` — 14 pontos hardcoded, girth aplica uniforme | **#6 Spline** [B] | Perfil como função contínua (sine/bezier), modulada por genoma `girth` e `length` |
| 46-47 | `head_dir = safe_norm(js[0] - js[1])` — direção entre 2 juntas | **#9 Pose** [B] | Cabeça com rotação independente, spring perseguindo alvo de olhar |

---

## 4. `leg.py` — IK 2-Ossos (~88 linhas)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 37-47 | `rest_target()` — `base + vel * 0.12`, sem consciência de terreno | **#4 Ground** [B] | Raycast do foot target até ground_y_at(x); se diff > limiar, ajustar y |
| 52-73 | `update()` — step trigger por distância | **#4 Ground** [B] + **#8 Antic** [A] | Em terreno irregular: ajustar altura e timing do passo; antecipar com lift antes do movimento |
| 66 | `lift = math.sin(t * pi) * step_h` — arco fixo | **#9 Pose** [B] | Altura e formato do arco por tipo de criatura: pesado → baixo, rápido → alto, furtivo → rasante |
| 75-88 | `solve()` — IK simples sem ground clamp | **#4 Ground** [B] | Após IK, se foot penetra terreno, empurrar pés para superfície e re-solver |

---

## 5. `parts.py` — Desenho de Partes (~273 linhas)

Atualmente tudo usa `creature.wobble` global. Substituir por `PhaseOscillator` + `SpringDamper` por parte.

| Função | Linha | Parte | O que faz hoje | Técnica | O que muda |
|--------|-------|-------|---------------|---------|------------|
| `draw_spikes` | 26-53 | Espinhos | `sway = sin(wobble * 1.3 + i * 0.5) * 0.18` | **#5 Phase** [A] + **#3 Spring** [A] | Oscilador dedicado por cluster + spring perseguindo posição de repouso (overshoot na virada) |
| `draw_plates` | 55-72 | Placas | Estáticas, presas à junta | **#3 Spring** [A] | Spring perpendicular pequeno para chacoalhar quando criatura se move rápido |
| `draw_horns` | 74-100 | Chifres | `sway = sin(wobble * 1.6 + k * 0.9) * 0.12` (comentário já cita plano #5) | **#3 Spring** [A] | Spring stiff (stiffness=16) perseguindo junta da cabeça — chifre atrasa na virada |
| `draw_tail` | 106-135 | Cauda (club/sting) | Pontas fixas relativas à última junta cosmética | **#3 Spring** [A] | Spring extra para club (massa pesada, overshoot maior) e sting (elástico, whip) |
| `draw_fins` | 137-156 | Barbatanas | `wob = sin(wobble * 2 + i) * 0.3` | **#5 Phase** [A] + **#3 Spring** [A] | Spring soft (stiffness=5) para ponta; amplitude escala com velocidade |
| `draw_antennae` | 162-177 | Antenas | 2 segmentos com `wig = sin(wobble * 3 + s) * 0.3` | **#3 Spring** [A] | Cadeia de 2-3 springs por antena; ponta arrasta quando cabeça vira |
| `draw_wings` | 179-193 | Asas | `flap = 0.5 + 0.5 * abs(sin(wobble * 7))` — abs(sin) = snap no trough | **#5 Phase** [A] | Oscilador dedicado com speed/amplitude por espécie; asa caída no chão (rest pose diferente) |
| `draw_extra_eyes` | 195-209 | Olhos extras | Círculos em offset fixo da cabeça | **#3 Spring** [A] + **#9 Pose** [B] | Spring pequeno perseguindo direção do olhar; pupilas dilatam em alerta |
| `draw_spore_sacs` | 211-221 | Sacos de esporo | `pu = 1 + 0.16 * sin(wobble * 3 + i)` — pulso fixo | **#9 Pose** [B] | Pulse mais rápido quando agitado; burst na morte com spring-release |
| `draw_fangs` | 237-247 | Presas | 2 linhas estáticas | **#9 Pose** [B] | Presas abrem no wind-up de ataque, fecham na mordida — spring no ângulo |

---

## 6. `species.py` — Genomas (~169 linhas)

| Linha | Espécie | Genoma atual | Técnica | Parâmetros a adicionar |
|-------|---------|-------------|---------|----------------------|
| 24-26 | `runner` | `size=0.72, speed=1.5` | **#7 Damping** [A] | `weight=0.6`, `angular_damping=0.15`, mais bounce, squash alto |
| 27-30 | `tank` | `size=1.5, plates=1, angular_damping=0.6, linear_damping=0.5, weight=2.5` | **#7 Damping** [A] | Já tem damping/weight — adicionar `wobble_speed=2` (lento), `tail_stiffness=16` |
| 31-33 | `snake` | `size=0.95, length=1.9, leg_count=0` | **#5 Phase** [B] + **#6 Spline** [B] | `body_wave_amp=0.3`, `body_wave_speed=4` — onda viajante contínua |
| 40-44 | `spider` | `radial=True, leg_count=8, angular_damping=0.15, weight=0.8` | **#4 Ground** [B] | Pernas em terreno irregular: raycast por pé |
| 57-60 | `wasp` | `wings=True, antennae=True, speed=1.55` | **#5 Phase** [A] | `wing_flap_speed=12`, `antenna_wiggle_speed=5` |
| 78-82 | `centipede` | `plan='segmented', length=1.5` | **#6 Spline** [B] | Spline contínua em vez de círculos sobrepostos |
| 85-91 | `octopus` | `plan='tentacle', leg_count=6, weight=3.0` | **#3 Spring** [A] | Spring por braço, stiffness decrescente base→ponta |
| Geral | Todas | Sem parâmetros de animação | **#7 Damping** [A] | Adicionar slots: `wobble_speed`, `tail_stiffness`, `body_bounce`, `anticipation_duration`, `idle_sway_amp` |

---

## 7. `characters.py` — Personagens Jogáveis (~204 linhas)

Só dados de genoma. Sem código de animação.

| Personagem | Genoma | Oportunidade |
|-----------|--------|-------------|
| Lagarto (padrão) | `size=1.0, speed=1.0` | Parâmetros de animação base |
| Vibora | `tail='club'` | Club pesado: spring na cauda com stiffness maior (massa extra) |
| Couraçado | `plates=2, girth=1.4, speed=0.78` | Placas chacoalham com spring (stiffness=12, damping=0.7) |
| Larva | `size=0.72` → cresce até `C.CHAR_LARVA_MAX_SIZE` | `weight` aumenta com tamanho: mais inércia, mais squash, steering mais lento |

---

## 8. `boss.py` — Sistema de Chefes (~466 linhas)

| Linha | O que faz hoje | Técnica | O que muda |
|-------|---------------|---------|------------|
| 173-201 | `BossPersonality` — mood só afeta cor/velocidade | **#11 Pers** [C] + **#9 Pose** [B] | Mood muda pose: enraged = corpo arqueado, cauda erguida; stiffness das molas aumenta |
| 182-189 | `mood_speed = {'calm':1.0, 'agitated':1.3, ...}` | **#5 Phase** [A] | Mood afeta velocidade dos osciladores (agitado = barbatana mais rápida) |
| 302-318 | `_update_mood()` — lógico, sem animação de transição | **#9 Pose** [B] | Transição de mood com spring: 0.3s de interpolação suave entre poses |
| 320-322 | `_choose_pattern()` — aleatório ponderado, invisível | **#11 Pers** [C] | Telegraph via linguagem corporal antes do padrão: enrolar para radial, baixar cabeça para carga |
| 324-406 | `tick()` — FSM sem pose por estado | **#9 Pose** [B] | Cada estado FSM dirige uma pose: intro = subindo, windup = encolhido, recover = caído |
| 410-466 | `draw()` — telegrafos são círculos/linhas HUD | **#8 Antic** [A] | Telegraph no corpo: glow na boca para ranged, cauda erguida para shockwave, corpo plantado para carga |
| 438-466 | Kinds: radial, fan, line, horn, shockwave, spiral | **#3 Spring** [A] | Shockwave: boss squash down → spring release no frame do ataque (mola acumula energia) |

---

## 9. `champions.py` — Modificadores Elite

| Champion | Efeito | Técnica | O que muda |
|----------|--------|---------|------------|
| ALFA | Speed boost + rally | **#9 Pose** [B] | Quando rallied: cabeça erguida, cauda alta, postura mais ereta |
| ESPECTRO | Camuflagem no estado parado | **#9 Pose** [B] | Camuflado: corpo baixo, cauda parada; visível: postura agressiva |
| EXPLOSIVO | Morte explosiva | **#3 Spring** [A] + **#9 Pose** [B] | Antes de explodir: corpo incha (spring no scale), depois burst |
| DIVISOR | Divide em 2 ao morrer | **#6 Spline** [B] | Animação de divisão: corpo alonga, afina no meio, separa com spline |

---

## 10. `weapons.py` — Armas Automáticas

| Linha | Weapon | O que faz hoje | Técnica | O que muda |
|-------|--------|---------------|---------|------------|
| 186-187 | Orbital aura | `pulse = 0.85 + 0.15 * sin(wobble * 2)` | **#5 Phase** [A] | `PhaseOscillator` independente em vez de global wobble |
| 210-214 | Orbitals (projéteis giratórios) | `a = wobble * 40 + k * 120` | **#5 Phase** [A] | Orbital continua girando mesmo se player parar (wobble global para) — oscilador próprio |
| 285 | Asas (item) | `wing = sin(wobble * 12 + k) * 5` | **#5 Phase** [A] | Oscilador próprio para flap durante voo |

---

## 11. `anim.py` — Primitivas: Estado Atual

| Primitiva | Implementada | Instanciada | Engrenada no pipeline |
|-----------|-------------|-------------|----------------------|
| `SpringDamper` | ✔ | ✗ (0) | ✗ |
| `Vector2Spring` | ✔ | △ (1 de ~20) | △ (só tail_spring) |
| `PhaseOscillator` | ✔ | ✗ (0) | ✗ |
| `Anticipation` | ✔ | ✗ (0) | ✗ |

### Ação imediata (Fase A, 0 implementação):

Nada precisa ser escrito — só instanciar as classes nos lugares certos.

---

## 12. Prioridade por Arquivo

### Fase A — Spring-Damper + Anticipation + Phase + Damping (1-2-3-4 no plano)

| Arquivo | O que fazer | Esforço |
|---------|------------|---------|
| `anim.py` | Nada (já existe) | 0 |
| `lizard.py` | Substituir `wobble` por `PhaseOscillator`; tail_spring único → chain; Anticipation para dash/whip/tongue; damping por genoma | 3h |
| `parts.py` | Substituir `sin(wobble * X)` por osciladores + springs por parte | 2h |
| `spine.py` | Spring chain nas últimas N juntas em vez de follow-the-leader puro | 1h |
| `species.py` | Adicionar slots de animação ao Genome | 30min |
| `weapons.py` | Osciladores próprios para orbitais/asas | 30min |
| `boss.py` | Anticipation + spring nos telegraphs corporais | 1h |
| **Total Fase A** | | **~8h** |

### Fase B — Ground Adaptation + Spline + Pose (5-6-7 no plano)

| Arquivo | O que fazer | Esforço |
|---------|------------|---------|
| `leg.py` | Raycast foot → terrain y, pelvis spring, ground clamp no IK | 3h |
| `lizard.py` | Ground adaptation no integrate(); squash em impacto/landing; pose por AI state | 3h |
| `spine.py` | Catmull-Rom body polygon; perfil contínuo de radii | 2h |
| `parts.py` | Pose por contexto (presas abrem, olhos dilatam, sacos incham) | 1h |
| `lizard.py` (AILizard) | Pose diferente por estado AI + telegraph corporal | 2h |
| **Total Fase B** | | **~11h** |

### Fase C — Dois Esqueletos + Personalidade Emergente (8-9 no plano)

| Arquivo | O que fazer | Esforço |
|---------|------------|---------|
| `cosmetics.py` (novo) | Esqueleto cosmético 32+ pontos com spring por ponto | 4h |
| `spine.py` / `lizard.py` | Engrenar cosmetic skeleton no pipeline de desenho | 2h |
| `boss.py` | Personalidade emergente: mood → pose; body language telegraphs | 3h |
| `champions.py` | Poses e animações específicas por champion | 1h |
| **Total Fase C** | | **~10h** |

---

## 13. Ordem Sugerida de Trabalho

```
Fase A (8h)
  ├── 1. species.py: slots de animação no Genome          [30min]
  ├── 2. lizard.py: substituir wobble por PhaseOscillator  [30min]
  ├── 3. parts.py: osciladores + springs por parte         [2h]
  ├── 4. spine.py: spring chain na cauda                   [1h]
  ├── 5. lizard.py: Anticipation (dash, whip, tongue, AI)  [1h]
  ├── 6. weapons.py: osciladores próprios para orbitais    [30min]
  └── 7. boss.py: Anticipation + spring telegraphs         [1h]

Fase B (11h)
  ├── 1. leg.py: ground adaptation (raycast + clamp)       [3h]
  ├── 2. lizard.py: ground adaptation no integrate()        [1h]
  ├── 3. lizard.py: squash em impacto/landing               [1h]
  ├── 4. spine.py: Catmull-Rom + radii contínuo            [2h]
  ├── 5. parts.py: pose por contexto                        [1h]
  └── 6. lizard.py (AI): pose por estado                    [3h]

Fase C (10h)
  ├── 1. cosmetics.py: esqueleto cosmético                  [5h]
  ├── 2. lizard.py + spine.py: engrenar cosmetic skeleton   [2h]
  └── 3. boss.py: personalidade emergente                   [3h]
```

---

## 14. Dependências

```
Fase A (nenhuma dependência externa)
  └── Pode começar imediatamente

Fase B (depende de Fase A)
  ├── Ground adaptation precisa de PhaseOscillator? Não
  └── Spline precisa de Spring chain? Não

Fase C (depende de Fase A + B)
  ├── Cosmetic skeleton precisa de Spring chain (A) + Spline (B)
  └── Personalidade precisa de Pose (B)
```
