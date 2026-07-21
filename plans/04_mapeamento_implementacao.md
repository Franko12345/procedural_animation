# Mapeamento: Estado Real da Implementação

## Propósito

Inventário exato do que foi implementado vs o que ainda é código morto ou pendente, referenciado ao plano `01_animacao_procedural_avancada.md`.

---

## 1. Resumo por Técnica

| # | Técnica | Arquivos-chave | Implementado | Código morto | Pendente |
|---|---------|---------------|-------------|-------------|----------|
| 3 | Spring-Damper | `anim.py`, `lizard.py`, `parts.py`, `menu.py` | `Vector2Spring` (2) — tail + head_dir; `update_secondary_springs()` choke point; `_cosmetic_joints()` com lag + ripple; `head_dir_spring` nos chifres; `menu.py` chama spring update/reset | `SpringDamper` (1D) — 0 instâncias | Spring chain na cauda; spring 1D em placas/antenas/olhos; spring pós-whip; spring pós-tongue |
| 4 | Ground Adaptation | `leg.py`, `lizard.py` | Nada | N/A | Raycast foot → terrain y; pelvis spring; ground clamp no IK; inclinação em rampa |
| 5 | Phase Offsets | `anim.py`, `parts.py`, `lizard.py` | 11 ad-hoc `math.sin(creature.wobble * X + i * Y) * Z` em spikes/horns/fins/antennae/wings/spore_sacs/tentacle/tail ripple/mantle pulse/hover bob | `PhaseOscillator` — 0 instâncias | Substituir raw wobble por `PhaseOscillator` por parte; onda metacronal generalizada |
| 6 | Spline Dinâmica | `spine.py`, `mathutil.py`, `lizard.py` | `catmull_rom()` em mathutil; `SMOOTH_SUBDIV=3`; `_smooth_samples()`; `outline_smooth()`; `body_polygon_smooth()`; `_cap()`; `_arm_polygon()`; chamado em `Lizard.draw()` | N/A | Perfil contínuo de radii (função vs array fixo); spline para paths de perna/step |
| 7 | Damping/Weight | `genome.py`, `lizard.py`, `species.py`, `rounds.py` | `angular_damping`/`linear_damping`/`weight` no genome; aplicado em `steer()` e `integrate()`; tank/spider/octopus com valores; boss override em rounds.py | N/A | weight não afeta turn radius/knockback; damping só em 3 de 18 espécies; sem aceleração baseada em massa |
| 8 | Anticipation | `anim.py`, `lizard.py`, `boss.py` | Raw float timers: `lunge_t`, `shoot_charge`, `grapple_t`, `boss.t`; leg step antecipa com `vel*0.12`; boss windup com `windup_mult(mood)` | `Anticipation` — 0 instâncias | Substituir timers raw por `Anticipation`; wind-up no dash/whip/tongue do player; flinch em mudança de direção |
| 9 | Procedural Posing | `spine.py`, `leg.py`, `lizard.py` | `Spine.resolve()` follow-the-leader; `Leg.solve()` IK 2-osso; `_whip_arc()`; `_resolve_arms()` com convergence/sine curl; tentacle wave; flyer hover bob; frog hop | N/A | Pose library; transition blending; pose por AI state (hunting/alert/flee/attack); pose library reutilizável |
| 10 | Dois Esqueletos | `lizard.py`, `spine.py`, `parts.py` | `_cosmetic_joints()` devolve COPY modificada só para draw; hit-test/legs/eyes leem `spine.joints` direto; `outline()`/`_smooth_samples()`/`body_polygon_smooth()` aceitam `joints` opcional; `draw_tail()` lê cosmetic joints; `head_dir_spring` só direção (não posição) | N/A | Só as últimas 4 juntas da cauda; sem esqueleto cosmético full-body; sem cosmetic leg positions; suprimido durante whip |
| 11 | Personalidade | `boss.py`, `lizard.py` | `BossPersonality` completo: mood_speed, pattern_weights, mood_colors, tell_mult; `king_personality()`, `centipede_personality()`, `kraken_personality()`, `primordial_personality()`; `_update_mood()` por distance/HP/frustration; `_choose_pattern()` weighted; `BOSS_MOOD_SPRING_MULT`; `_apply_mood_pose()`; scar mechanic; on_phase hooks | N/A | Personality só para bosses; mood não afeta leg stride/head bob/tail carriage/idle sway |
| 12 | Pipeline | `lizard.py`, `menu.py` | `rebuild_body()` → `steer()` → `integrate()` → `update_secondary_springs()`; `reset_secondary_springs()` para teleport; Player update com input/dash/whip/tongue/weapons; AILizard update com AI dispatch + champion + boss | N/A | `menu.py` replica 70% do integrate() em 3 lugares (`_step_backdrop`, `_preview_step`, character select) — mesmo bug pattern que `update_secondary_springs()` foi criado para prevenir |

---

## 2. `anim.py` — Primitivas

| Classe | Existe | Instâncias | Uso real | Status |
|--------|--------|-----------|----------|--------|
| `SpringDamper` (1D) | ✅ lines 12-30 | 0 | Nenhum | **Código morto** |
| `Vector2Spring` (2D) | ✅ lines 33-50 | 2 | `tail_spring` + `head_dir_spring` | ✅ Ativo |
| `PhaseOscillator` | ✅ lines 53-68 | 0 | Nenhum | **Código morto** |
| `Anticipation` | ✅ lines 71-107 | 0 | Nenhum | **Código morto** |

---

## 3. `genome.py` — ✅ Completo

`angular_damping` (58), `linear_damping` (59), `weight` (60) — default 0/0/1.0.

---

## 4. `species.py` — Damping/Weight em 3 espécies

| Espécie | angular_damping | linear_damping | weight |
|---------|----------------|----------------|--------|
| tank | 0.6 | 0.5 | 2.5 |
| spider | 0.15 | 0.2 | 0.8 |
| octopus | 0.7 | 0.6 | 3.0 |

Demais 15 espécies: default 0/0/1.0.

---

## 5. `lizard.py` — Lizard (2006 linhas)

### 5.1 O que foi ADICIONADO no Fase A/B Overhaul

| Item | Linha | Descrição |
|------|-------|-----------|
| `TAIL_SPRING_STIFFNESS = 10.0` | 35 | Constante para stiffness da cauda |
| `HEAD_SPRING_STIFFNESS = 16.0` | 36 | Constante para stiffness dos chifres |
| `BOSS_MOOD_SPRING_MULT` dict | 37-42 | Mood → stiffness multiplier |
| `head_dir_spring` | 129-133 | Spring 2D para direção da cabeça |
| `angular_damping` em `steer()` | 319 | `turn_resp = 1.0 - genome.angular_damping` |
| `update_secondary_springs()` | 355-370 | Choke point único para springs cosméticos |
| `reset_secondary_springs()` | 372-380 | Snap springs ao teleportar |
| `linear_damping` em `integrate()` | 342-343 | `vel *= exp(-linear_damping * 3 * dt)` |
| `weight` no squash | 346-349 | `approach(squash, ..., 9/sqrt(weight), dt)` |
| Traveling ripple em `_cosmetic_joints()` | 403-409 | `perp * wave_amp * t * sin(wobble * 2.2 - i * 0.9)` |
| Lag cap em `_cosmetic_joints()` | 399-402 | `TAIL_SPRING_MAX_LAG * max_r` |
| `_apply_mood_pose()` | 1688-1697 | Stiffness multiplier por mood do boss |
| `body_polygon_smooth()` no draw | 445 | Catmull-Rom com cosmetic joints |

### 5.2 O que NÃO mudou (ainda raw/pre-Fase A)

| Item | Linha | Descrição |
|------|-------|-----------|
| `wobble += dt * 6` | 350 | Hardcoded, sem `PhaseOscillator` |
| Dash instantâneo | 925 | `vel = norm(move) * max_speed * 3.0` — sem wind-up |
| Tongue cinemático | 1185-1194 | `reach = sin(t * pi)` — sem spring pós-retração |
| Whip puramente cinemático | 1051-1098 | `env = sin(t * 2pi)` — spring mutado durante whip |
| AILizard timers raw | ~1446-1679 | `shoot_charge`, `lunge_t`, `grapple_t` sem `Anticipation` |
| AI sem pose por estado | ~1300-1680 | Monolithic, sem Procedural Posing |

---

## 6. `spine.py` (125 linhas)

### Adicionado no Overhaul

| Item | Linha | Descrição |
|------|-------|-----------|
| `SMOOTH_SUBDIV = 3` | 12 | Subdivisão Catmull-Rom |
| `_smooth_samples(joints=None)` | 68-83 | Amostras densas via Catmull-Rom |
| `outline_smooth()` | 85-95 | Rims sobre chain suavizada |
| `body_polygon_smooth()` | 97-100 | Polígono fechado suave |
| `_cap()`, `head_cap()`, `tail_cap()` | 102-120 | Capas semicirculares |

### Não mudou

| Item | Linha | Descrição |
|------|-------|-----------|
| `resolve()` puramente cinemático | 38-46 | Sem spring chain nas juntas |
| `RADII_PROFILE` array fixo | 16-17 | 14 pontos hardcoded |
| `head_dir()` entre 2 juntas | 48-49 | Sem rotação independente de cabeça |

---

## 7. `leg.py` (88 linhas) — ✗ Nada mudou

Sem ground adaptation, sem raycast, sem terrain clamp.

---

## 8. `parts.py` (279 linhas)

### Mudança no Overhaul

| Item | Linha | Descrição |
|------|-------|-----------|
| `draw_horns()` lê `head_dir_spring` | 84-89 | Lean dos chifres oposto à virada |

### Não mudou

Todas as outras funções continuam com `math.sin(creature.wobble * X + i * Y) * Z` — mesmo pattern de antes.

---

## 9. `boss.py` (466 linhas) — ✅ Reescrevido

### Adicionado

| Item | Linha | Descrição |
|------|-------|-----------|
| `BossPersonality` | 169-201 | mood_speed, pattern_weights, mood_colors, tell_mult |
| 7 patterns | 39-166 | radial_burst, fan_shot, aimed_barrage (+tick), summon_adds, shockwave, spiral_pattern (+tick), charge_attack |
| 4 personalidades nomeadas | 332-418 | king, centipede, kraken, primordial |
| `_update_mood()` | 479-495 | Mood por distance/HP/frustration |
| `_choose_pattern()` | 497-499 | Weighted random |
| FSM completa | 501-618 | intro → approach → windup → attack → recover → transition → charging |
| Telegraph drawing | 623-685 | radial, fan, line, horn, shockwave, spiral, rain |
| CicatriZ (Rei Lagarto) | 303-319 | Scar puddles que causam slow + tick |
| `BOSS_MOOD_SPRING_MULT` em lizard.py | 37-42 | Mood → stiffness multiplier |

### Ainda pendente

Telegraph corporal (body pose, glow na boca, cauda erguida) em vez de só círculos/linhas HUD.

---

## 10. `weapons.py` — Nada mudou

| Weapon | Linha | Uso de wobble | Status |
|--------|-------|---------------|--------|
| Orbital aura | 186-187 | `sin(wobble * 2)` | Raw |
| Orbitals | 210-214 | `a = wobble * 40 + k * 120` | Raw |
| Wings (item) | 285 | `sin(wobble * 12 + k)` | Raw |

---

## 11. `champions.py` — Nada mudou

---

## 12. Código Morto

3 classes em `anim.py` que NUNCA são instanciadas:

| Classe | Linhas | Serviria para |
|--------|--------|---------------|
| `SpringDamper` | 12-30 | Placas (rattle), ângulo de chifres, pupilas de olhos, amplitude de barbatana |
| `PhaseOscillator` | 53-68 | Substituir TODOS os `math.sin(creature.wobble * X + i * Y) * Z` em parts.py, weapons.py, lizard.py |
| `Anticipation` | 71-107 | Substituir TODOS os timers raw (shoot_charge, lunge_t, grapple_t, dash wind-up, tongue wind-up) |

---

## 13. Prioridade Pendente

### Fácil (só instanciar classes que já existem)

| # | Tarefa | Arquivos | Esforço |
|---|--------|----------|---------|
| 1 | Instanciar `PhaseOscillator` por parte (spikes, horns, fins, antennae, wings, spore_sacs) | `parts.py`, `lizard.py` | 1h |
| 2 | Instanciar `Anticipation` para lunge/shoot/grapple/dash/whip/tongue | `lizard.py` | 1h |
| 3 | Instanciar `SpringDamper` (1D) para placas, ângulo de chifres, pupilas | `parts.py` | 30min |

### Médio

| # | Tarefa | Arquivos | Esforço |
|---|--------|----------|---------|
| 4 | Spring pós-whip (follow-through 0.2s ao fim do swing) | `lizard.py` | 30min |
| 5 | Spring pós-tongue (lash na retração) | `lizard.py` | 30min |
| 6 | Spring chain na cauda (N springs stiffness 12→6 em vez de 1) | `lizard.py` | 1h |
| 7 | Das wind-up (0.08s squash + partícula) | `lizard.py` | 30min |
| 8 | Tongue wind-up (0.1s abertura de boca) | `lizard.py` | 30min |

### Pesado

| # | Tarefa | Arquivos | Esforço |
|---|--------|----------|---------|
| 9 | Ground adaptation (raycast foot → terrain y, pelvis spring, IK ground clamp) | `leg.py`, `lizard.py` | 3h |
| 10 | Procedural posing por AI state (hunting/alert/flee/attack) | `lizard.py` | 3h |
| 11 | Esqueleto cosmético full-body (32+ pontos, spring por ponto, independente da simulação) | `cosmetics.py` (novo) | 5h |
| 12 | Telegraph corporal no boss (body pose no windup em vez de só círculos HUD) | `boss.py` | 2h |
| 13 | Eliminar duplicação do pipeline em `menu.py` (3 lugares replicam integrate()) | `menu.py` | 1h |
