# Plano: Sistema Avançado de Animação Procedural

> **Legacy design notes.** Actionable work moved to GitHub Issues (see
> [docs/agents/issue-tracker.md](../docs/agents/issue-tracker.md)). This
> file is preserved for the Rain World technique analysis and the
> spring/damping/phase-offset reference — no other file captures that
> catalogue in one place. Canonical vocabulary in
> [CONTEXT.md](../CONTEXT.md); implemented behaviour in
> [docs/concepts/](../docs/concepts/README.md).

---

## Índice

1. [Análise: Rain World — O Estado da Arte](#1-analise-rain-world)
2. [Técnicas por Camada](#2-tecnicas-por-camada)
3. [Spring-Damper System](#3-spring-damper-system)
4. [Ground Adaptation (IK de Pés)](#4-ground-adaptation)
5. [Phase Offsets e Onda Metacronal](#5-phase-offsets)
6. [Spline Dinâmica para Corpos Contínuos](#6-spline-dinamica)
7. [Damping, Weight e Inércia](#7-damping-weight)
8. [Anticipation (Wind-up) em Movimento](#8-anticipation)
9. [Procedural Posing (Rain World Style)](#9-procedural-posing)
10. [Dois Esqueletos (Simulação + Cosméticos)](#10-dois-esqueletos)
11. [Personalidade Emergente via Animação](#11-personalidade-emergente)
12. [Pipeline de Animação do Lagarto](#12-pipeline)
13. [Prioridade de Implementação](#13-prioridade)

---

## 1. Análise: Rain World — O Estado da Arte

### O que Rain World faz (GDC 2016 — Joar Jakobsson / James Therrien)

Rain World separa **simulação física** de **cosméticos**. Cada criatura tem dois esqueletos:

```
[AI] → [Physics Simulation (beads + sticks)] → [Cosmetic Layer (sprites + tint)]
```

**Esqueleto de Simulação:**
- Pontos 2D conectados por distância fixa (spring constraints)
- Física simples: pontos são puxados uns aos outros se distância > limiar
- Usa pathfinding (grid-based) + física (beads) combinados
- AI entende o tile map e pathfindeia até goal
- Física resolve movimento real com colisão contra terrain

**Esqueleto Cosmético:**
- Sprites escolhidos por orientação (cutout animation)
- Stretch + masking para partes que "olham" pra câmera
- Desenho em baixa resolução + upscale (pixel art shader)
- Frame rate reduzido (~12fps) para sensação de animação 2D clássica

**Por que funciona:**
- Comportamento AI = animação visível (causa e efeito)
- Criatura parece frustrada quando não alcança presa — personalidade emerge
- Movimento orgânico sem keyframes manuais
- Separação permite física complexa sem arte cara

### O que NOSSO jogo já faz

```
AI/Steering → Spine (follow-the-leader, bend limit) → Legs (IK 2-ossos, foot-planting) → Parts (desenho fixo) → Body polygon
```

**O que falta para chegar no nível Rain World:**

| Técnica | Nós temos | Rain World tem |
|---------|-----------|----------------|
| Follow-the-leader | Sim (spine.py) | Sim (básico) |
| IK de 2 ossos | Sim (leg.py) | Sim (CCD/FABRIK) |
| Foot-planting | Sim (threshold + arc) | Sim (ground raycast) |
| Spring-damper secondary | Não | Sim (cauda, chifres, orelhas) |
| Dois esqueletos | Não | Sim (física vs cosmética) |
| Ground adaptation | Não (pé flutua em斜坡) | Sim (raycast + pelvis adjust) |
| Phase offsets / onda | Parcial (centopeia) | Sim (generalizado) |
| Spline contínua | Parcial (body_polygon) | Sim (tentáculos) |
| Weight / damping | Parcial (clog) | Sim (por genoma) |
| Anticipation | Parcial (shoot_charge) | Sim (generalizado) |
| Procedural posing | Não | Sim (poses por contexto) |
| Personalidade emergente | Não | Sim (comportamento visível) |

---

## 2. Técnicas por Camada

### Pipeline proposto

```
1. SIMULAÇÃO (física simples, determinística)
   ├── AI/Steering → target velocity + direction
   ├── Spine → follow-the-leader, bend constraint
   ├── Legs → IK + foot-planting + ground adaptation
   └── Body → squash & stretch por velocidade

2. SECONDARY (spring-damper, phase offset)
   ├── Cauda → spring chain (não follow-the-leader puro)
   ├── Chifres/espinhos/cristas → spring-damper tracking parent joint
   ├── Barbatanas → phase offset + sway
   └── Respiração → sine wave no scale do corpo

3. COSMÉTICA (spline, desenho contínuo)
   ├── Body polygon → Catmull-Rom entre juntas
   ├── Thickness variável (cabeça grossa → cauda fina)
   └── Outline consistente (todas as partes)

4. JUICE (reação a eventos)
   ├── Hit-stop + shake (já temos)
   ├── Glow + flash (já temos)
   ├── Sparks + rings (já temos)
   └── Squash & stretch em impacto
```

---

## 3. Spring-Damper System

### Teoria

Sistema massa-mola com amortecimento. Cada frame:
1. Calcula força de restauração: `F = stiffness × (target - current)`
2. Aplica amortecimento: `vel *= (1 - damping × dt)`
3. Atualiza posição: `current += vel × dt`

### Implementação Base

```python
class SpringDamper:
    """Generic 1D spring-damper. Use Vector2Spring para 2D."""
    __slots__ = ('value', 'target', 'vel', 'stiffness', 'damping')

    def __init__(self, value=0.0, stiffness=8.0, damping=0.85):
        self.value = value
        self.target = value
        self.vel = 0.0
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt):
        diff = self.target - self.value
        self.vel += diff * self.stiffness * dt
        self.vel *= 1.0 - self.damping * dt
        self.value += self.vel * dt
        return self.value


class Vector2Spring:
    """2D spring-damper para posições."""
    __slots__ = ('value', 'target', 'vel', 'stiffness', 'damping')

    def __init__(self, value: Vector2, stiffness=8.0, damping=0.85):
        self.value = Vector2(value)
        self.target = Vector2(value)
        self.vel = Vector2(0, 0)
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt):
        diff = self.target - self.value
        self.vel += diff * self.stiffness * dt
        self.vel *= 1.0 - self.damping * dt
        self.value += self.vel * dt
        return self.value
```

### Onde Aplicar

**Cauda (`spine.py`):**
- Em vez de follow-the-leader puro, cada junta da cauda persegue a anterior com spring
- Overshoot natural: quando corpo para, cauda continua balançando
- Stiffness diminui da base à ponta (ponta mais "mole")

```python
# spine.py — cada junta além do pescoço usa spring
class SpringSpine:
    def __init__(self, n_joints, base_dist):
        self.joints = [Vector2(0, 0) for _ in range(n_joints)]
        self.springs = [
            Vector2Spring(Vector2(0, 0), stiffness=12 - i * 0.8, damping=0.8)
            for i in range(n_joints)
        ]
        self.base_dist = base_dist
```

**Chifres/Espinhos (`parts.py`):**
- Cada chifre tem spring que persegue posição relativa à junta
- Quando lagarto vira, chifres balançam com lag (secondary motion)
- Stiffness maior para chifre (mais rígido) que para barbatana

**Olhos/Cristas:**
- Spring no ângulo de direção do olhar (olho persegue alvo com atraso)
- Crista dorsal balança com movimento lateral

### Ajuste de Parâmetros

| Parte | Stiffness | Damping | Efeito |
|-------|-----------|---------|--------|
| Cauda (base) | 12 | 0.75 | Overshoot médio, 2-3 oscilações |
| Cauda (ponta) | 6 | 0.65 | Overshoot grande, 3-4 oscilações |
| Chifre | 16 | 0.85 | Rígido, pouco overshoot |
| Barbatana | 5 | 0.60 | Mole, muito sway |
| Orelha/crista | 8 | 0.70 | Médio |
| Respiração | N/A | N/A | Forçar target com sine wave |

---

## 4. Ground Adaptation (IK de Pés)

### O Problema

Pés do lagarto flutuam ou atravessam chão em terreno irregular. Já temos IK de 2 ossos e foot-planting, mas o target do pé é fixo em relação ao corpo — não reage ao chão.

### Solução

1. **Raycast** do target do pé para baixo até `world.ground_y_at(x)`
2. Se diferença y entre target atual e chão > limiar, tratar como degrau
3. Ajustar altura do target para y do chão
4. Spring-damper na altura da pelve para distribuir diferença

### Implementação

```python
# leg.py — ground-aware foot placement
class GroundAwareLeg(Leg):
    def _ground_target(self, pos, world):
        ground_y = world.ground_y_at(pos.x)
        diff = ground_y - pos.y
        if abs(diff) > 8:  # limiar de degrau
            pos.y = ground_y
        return pos

    def step_target(self, step_point, world):
        target = super().step_target(step_point)
        return self._ground_target(target, world)
```

### Pelvis Spring

Quando um pé sobe (degrau), pelve desce para compensar:

```python
# lizard.py — pelvis height adjustment
pelvis_height = body_height / 2
left_foot_y = left_leg.foot_target.y
right_foot_y = right_leg.foot_target.y
avg_foot_y = (left_foot_y + right_foot_y) / 2
pelvis_offset = avg_foot_y + pelvis_height  # ideal y da pelve
self.pelvis_spring.target = pelvis_offset
```

### Inclinação do Corpo em Rampa

Calcular ângulo do chão entre 2 pontos de contato e inclinar spine:

```python
# lizard.py
def _ground_angle(self, world):
    fore = world.ground_y_at(self.pos.x + self.max_r * 0.3)
    aft = world.ground_y_at(self.pos.x - self.max_r * 0.3)
    return math.atan2(fore - aft, self.max_r * 0.6)
```

---

## 5. Phase Offsets e Onda Metacronal

### Teoria

Movimento ondulatório que propaga pelo corpo. Cada segmento tem fase diferente: `sin(t + i * phase_gap)`.

### Implementação Generalizada

```python
class PhaseOscillator:
    """Onda viajante ao longo de uma cadeia."""
    def __init__(self, n_segments, speed=4.0, amplitude=0.3, phase_gap=0.8):
        self.n = n_segments
        self.speed = speed
        self.amplitude = amplitude
        self.phase_gap = phase_gap
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def get_offset(self, i):
        """i = índice do segmento (0 = base, n-1 = ponta)."""
        return math.sin(self.time * self.speed + i * self.phase_gap) * self.amplitude
```

### Onde Aplicar

| Parte | O que faz |
|-------|-----------|
| **Cauda** | Onda senoidal propaga da base à ponta (add over follow-the-leader) |
| **Espinhos** | Cada espinho na espinha tem fase diferente → ripple |
| **Pernas (centopeia)** | Já temos marcha metacronal: par i atrasa em relação a par i-1 |
| **Barbatanas** | Onda viajante vertical com amplitude maior na ponta |
| **Chifres** | Sway senoidal com fase por altura |

---

## 6. Spline Dinâmica para Corpos Contínuos

### O Problema

Juntas discretas da espinha produzem polígono com vértices visíveis. Para corpo contínuo (polvo, minhoca), precisamos de spline.

### Catmull-Rom

Interpola suave entre juntas sem controle explícito (passa por todos os pontos):

```python
def catmull_rom(p0, p1, p2, p3, t):
    """t ∈ [0, 1], retorna ponto na curva entre p1 e p2."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2 * p1) +
        (-p0 + p2) * t +
        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
        (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    )
```

### Body Polygon com Spline

```python
# spine.py — smooth body polygon
def body_polygon_smooth(self, width_scale=1.0):
    """Retorna pontos do contorno usando Catmull-Rom entre juntas."""
    pts = []
    n = len(self.joints)
    for i in range(n - 1):
        p0 = self.joints[max(0, i - 1)]
        p1 = self.joints[i]
        p2 = self.joints[i + 1]
        p3 = self.joints[min(n - 1, i + 2)]
        for t in [0.0, 0.25, 0.5, 0.75]:
            pt = catmull_rom(p0, p1, p2, p3, t)
            w = self.radius_at(i + t) * width_scale
            # normal perpendicular
            # ... left/right points
            pts.append(pt)
    return pts
```

### Thickness Variável

```python
def radius_at(self, t):
    """t = 0 (cabeça) a n-1 (cauda)."""
    frac = t / (len(self.joints) - 1)
    return self.max_r * (1.0 - frac * 0.7)  # 100% → 30%
```

---

## 7. Damping, Weight e Inércia

### O Problema

Criatura pequena (filhote) e grande (tanque) viram na mesma velocidade. Falta sensação de massa.

### Solução por Genoma

```python
# genome.py — novos slots
class Genome:
    __slots__ = (
        # ... existentes ...
        'angular_damping',  # 0.0 (nenhum) a 0.95 (máximo)
        'linear_damping',   # 0.0 a 0.95
        'weight',           # escala de massa (1.0 = normal)
        'anticipation',     # 0.0 a 1.0 (quanto wind-up)
    )
```

### Aplicação

```python
# lizard.py — steer com weight
class Lizard:
    def update(self, dt, world, ...):
        # Linear damping
        self.vel *= 1.0 - self.genome.linear_damping * dt

        # Angular damping no steering
        target_dir = safe_norm(target - self.pos)
        angle_diff = target_dir.angle_to(self.dir)
        max_turn = self.turn_speed * dt * (1.0 - self.genome.angular_damping)
        angle_diff = clamp(angle_diff, -max_turn, max_turn)
        self.dir = self.dir.rotate(angle_diff)

        # Squash & stretch escala com weight
        speed_frac = self.vel.length() / self.max_speed
        ss = 1.0 + speed_frac * 0.15 * (1.0 / self.genome.weight)
        # weight > 1 → menos squash (mais massa)
```

### Tabela de Referência

| Criatura | Angular Damping | Linear Damping | Weight |
|----------|----------------|----------------|--------|
| Filhote | 0.1 | 0.1 | 0.5 |
| Lagarto normal | 0.3 | 0.3 | 1.0 |
| Tanque | 0.6 | 0.5 | 2.5 |
| Polvo | 0.7 | 0.6 | 3.0 |
| Chefe | 0.5 | 0.4 | 3.0 |
| Aranha | 0.15 | 0.2 | 0.8 |

---

## 8. Anticipation (Wind-up) em Movimento

### O Problema

Criaturas mudam de direção instantaneamente. Falta "preparação" antes do movimento.

### O que Isaac/Gungeon fazem

- Chefe respira fundo antes de ataque (visual tell)
- Criatura recua antes de investir
- Inimigo "mira" antes de atirar

### Implementação

```python
class Anticipation:
    """Aplica wind-up antes de ações."""
    def __init__(self, duration=0.25):
        self.duration = duration
        self.timer = 0.0
        self.action = None

    def trigger(self, action):
        self.action = action
        self.timer = self.duration

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
            return None
        if self.action:
            a = self.action
            self.action = None
            return a
        return None

    @property
    def is_active(self):
        return self.timer > 0
```

### Onde Aplicar

| Ação | Wind-up | Visual |
|------|---------|--------|
| Mudar direção | ~0.1s | Desacelerar, inclinar |
| Dash (inimigo) | ~0.2s | Recuar, brilhar |
| Ataque melee | ~0.3s | Armar o corpo (lunging) |
| Ataque ranged | ~0.4s | Mira, glow na boca |
| Pulo | ~0.15s | Agachar (squash) |

---

## 9. Procedural Posing (Rain World Style)

### O Conceito

Em vez de animações fixas, o corpo é **posado proceduralmente** baseado em contexto:
- Estado emocional (calmo, agitado, irritado)
- Direção do olhar
- Histórico recente (levou dano, acabou de atacar)
- Alvo atual

### Implementação

```python
# lizard.py — procedural posing
class ProceduralPose:
    """Modifica a pose baseada em contexto."""
    def __init__(self, lizard):
        self.lizard = lizard
        self.tail_height = 0.0  # 0 = neutro, 1 = levantado
        self.body_arch = 0.0    # curvatura extra da espinha
        self.head_tilt = 0.0    # inclinação da cabeça

    def update(self, dt):
        l = self.lizard
        health_frac = l.hp / l.max_hp

        # Cauda levantada quando alerta
        target_tail = 0.3 if l.aggro_target else 0.0
        self.tail_height = approach(self.tail_height, target_tail, 2.0 * dt)

        # Corpo arqueado quando assustado
        target_arch = 0.5 if l.hit_flash > 0 else 0.0
        self.body_arch = approach(self.body_arch, target_arch, 3.0 * dt)

        # Cabeça inclinada quando ferido
        target_tilt = 0.2 * (1.0 - health_frac)
        self.head_tilt = approach(self.head_tilt, target_tilt, 1.5 * dt)

    def apply(self, spine):
        """Modifica as juntas da espinha."""
        # Arch: levanta juntas do meio
        mid = len(spine.joints) // 2
        spine.joints[mid].y += self.body_arch * 10

        # Tail height: levanta últimas juntas
        for i in range(mid, len(spine.joints)):
            frac = (i - mid) / (len(spine.joints) - mid)
            spine.joints[i].y -= self.tail_height * frac * 15
```

### Contextos de Pose

| Contexto | Postura | Cauda | Cabeça |
|----------|---------|-------|--------|
| Neutro (pastando) | Relaxado, baixo | Arrastando | Nível |
| Alerta (viu jogador) | Erguido, tenso | Levantada | Mira o alvo |
| Caçando | Agachado, foco | Rígida, reta | Inclinada pra frente |
| Ferido | Curvado, lento | Arrastando | Baixa |
| Atacando | Arqueado, impulso | Levantada | Aberta (boca) |
| Assustado | Encolhido | Entre pernas | Erguida |

---

## 10. Dois Esqueletos (Simulação + Cosméticos)

### Conceito Rain World

```
Physics skeleton (simple)  →  resolves colisão, movimento
     ↓
Cosmetic skeleton (detailed) →  desenha com spline, sprites, tint
```

### Implementação no Lagarto

**Esqueleto de Simulação** (já existe: `spine.py`, `leg.py`):
- Juntas com distância fixa
- Colisão com mundo e criaturas
- Determina hitbox

**Esqueleto Cosmético** (novo: `cosmetics.py`):
- Juntas interpoladas entre sim-juntas (mais pontos = mais suave)
- Spring-damper para follow-through
- Spline Catmull-Rom para contorno contínuo
- Sway, respiração, phase offsets

```python
class CosmeticSkeleton:
    """Camada cosmética sobre a espinha de simulação."""
    def __init__(self, n_cosmetic=32):
        self.n = n_cosmetic
        self.points = [Vector2(0, 0) for _ in range(n_cosmetic)]
        self.velocities = [0.0 for _ in range(n_cosmetic)]

    def follow_simulation(self, sim_joints, dt):
        """Interpola pontos cosméticos entre sim-juntas."""
        for i in range(self.n):
            t = i / (self.n - 1)
            idx = t * (len(sim_joints) - 1)
            frac = idx - int(idx)
            a = sim_joints[int(idx)]
            b = sim_joints[min(int(idx) + 1, len(sim_joints) - 1)]
            target = a.lerp(b, frac)
            # Spring-damper persegue target
            diff = target - self.points[i]
            self.velocities[i] += diff * 10 * dt
            self.velocities[i] *= 1.0 - 0.8 * dt
            self.points[i] += self.velocities[i] * dt
```

---

## 11. Personalidade Emergente via Animação

### Princípio Rain World

> "When a lizard is hunting, you can see it see you. You can understand its motivations. When it can't get directly to you, it gets visibly frustrated."

Personalidade **não é programada** — emerge do comportamento visível. Jogador projeta intenção na criatura porque vê causa e efeito.

### Como Aplicar em Chefes

| Situação | Reação Visível | Jogador Interpreta |
|----------|---------------|-------------------|
| Jogador foge | Chefe acelera, glow fica vermelho | "Tá irritado" |
| Jogador fica muito perto | Chefe recua, ataque radial | "Tá assustado" |
| Chefe toma muito dano rápido | Hit-flash longo, stumble | "Tá ferido" |
| Chefe não alcança jogador | Bate no chão, shake | "Tá frustrado" |
| Adds morrem | Chefe "olha" pros lados | "Tá surpreso" |

### Sistema de Mood para Chefes

```python
BOSS_MOODS = {
    'calm':      # HP > 66%, padrão
    'agitated':  # HP 33-66%, mais rápido, glow alaranjado
    'enraged':   # HP < 33%, glow vermelho, patterns agressivos
    'frustrated':# jogador fugiu >5s sem atacar
    'cornered':  # jogador < distância mínima
}
```

Mood afeta:
- Velocidade de movimento (agitated = 1.3x, enraged = 1.6x)
- Cooldown entre ataques (menor = mais agressivo)
- Escolha de patterns (frustrated → ranged, cornered → radial)
- Cor do glow (calm=cor base, agitated=laranja, enraged=vermelho)
- Postura (arch mais alto quando agressivo)

---

## 12. Pipeline de Animação do Lagarto

```
                    ┌─────────────────────┐
                    │    AI / Steering    │
                    │  (target velocity)  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  Spine Simulation   │
                    │  (follow-the-leader │
                    │   + bend limit)     │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Leg IK + Ground   │
                    │  Adaptation + Foot  │
                    │      Planting       │
                    └──────────┬──────────┘
                               ↓
          ┌────────────────────┼────────────────────┐
          ↓                    ↓                    ↓
   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │   Spring-    │   │    Phase     │   │   Anticipation   │
   │   Damper     │   │   Offsets    │   │   (wind-up)      │
   │   (secondary)│   │   (onda)     │   │                  │
   └──────────────┘   └──────────────┘   └──────────────────┘
          ↓                    ↓                    ↓
          └────────────────────┼────────────────────┘
                               ↓
                    ┌─────────────────────┐
                    │  Procedural Posing  │
                    │  (context → pose)   │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Cosmetic Spline   │
                    │   (Catmull-Rom +    │
                    │    thickness var)   │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   Draw: Body +      │
                    │   Parts + Glow +    │
                    │   Outline + Health  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │    Juice: Shake,    │
                    │    Hit-stop, FX     │
                    └─────────────────────┘
```

---

## 13. Prioridade de Implementação

| # | Técnica | Esforço | Impacto Visual | Já temos? | Fase |
|---|---------|---------|---------------|-----------|------|
| 1 | Spring-damper em cauda/chifres | 2 dias | Alto | Não | Imediata |
| 2 | Anticipation (wind-up) | 1 dia | Alto | Parcial | Imediata |
| 3 | Damping por genoma | 1 dia | Médio | Parcial | Imediata |
| 4 | Phase offsets (onda generalizada) | 2 dias | Médio | Parcial | Curto |
| 5 | Ground adaptation (IK pés) | 3 dias | Alto | Não | Curto |
| 6 | Procedural posing | 2 dias | Alto | Não | Curto |
| 7 | Spline contínua (Catmull-Rom) | 2 dias | Alto | Parcial | Médio |
| 8 | Personalidade emergente (mood) | 3 dias | Alto | Não | Médio |
| 9 | Dois esqueletos (cosmetic layer) | 5 dias | Médio | Não | Longo |

### Ordem Sugerida

```
Fase A: Spring-damper → Anticipation → Damping → Pose (1-4)
Fase B: Ground Adaptation → Phase Offsets → Spline (5-7)
Fase C: Personalidade → Dois Esqueletos (8-9)
```

---

## Referências

- **Rain World GDC 2016**: https://www.youtube.com/watch?v=sVntwsrjNe4
- **Transcript da GDC**: https://youtubetotranscript.com/transcript?v=sVntwsrjNe4
- **Merxon22 - Recreating RainWorld**: https://medium.com/@merxon22/recreating-rainworlds-2d-procedural-animation-part-1-4d882f947e9f
- **Alan Zucconi - Procedural Animations**: https://www.alanzucconi.com/2017/04/17/procedural-animations/
- **Game Juice - Springs, IK**: https://www.gamejuice.co.uk/articles/procedural-animation-springs-ik
- **WeaverDev - Procedural Animation Tutorial**: https://weaverdev.io/projects/proc-anim-tutorial
- **FABRIK Paper**: https://perso.liris.cnrs.fr/alexandre.meyer/teaching/master_charanim/M2_3_video_IK_Procedurale/FABRIK.pdf
- **A simple procedural animation technique**: https://www.youtube.com/watch?v=qlfh_rv6khY
- **Learn Inverse Kinematics**: https://youtu.be/wgpgNLEEpeY
- **Procedural Animation in 5 Minutes**: https://www.youtube.com/watch?v=PcpkBzcRdSU
- **Physics-Based Procedural Animation**: https://www.youtube.com/watch?v=Y44pKsXsCeM
