# Plano: Sistema de Chefes com Personalidade

---

## Índice

1. [Filosofia de Boss Design](#1-filosofia)
2. [Análise: The Binding of Isaac](#2-analise-isaac)
3. [Análise: Enter the Gungeon](#3-analise-gungeon)
4. [Lições de Ambos para o Lagarto](#4-licoes)
5. [Psicologia do Jogador em Boss Fights](#5-psicologia)
6. [Framework: BossAI 2.0](#6-framework)
7. [Sistema de Padrões (Patterns)](#7-patterns)
8. [Sistema de Fases (Phases)](#8-phases)
9. [Telegrafia: Regras de Ouro](#9-telegrafia)
10. [Sistema de Personalidade (Mood)](#10-personalidade)
11. [Arena Design](#11-arena)
12. [Implementação Técnica](#12-implementacao)

---

## 1. Filosofia de Boss Design

### O que separa um chefe de um inimigo comum?

```
Inimigo comum:  testa reflexo, 1-2 padrões, morre em segundos
Chefe:          testa adaptação, 3+ fases, dura 30-90s, é um evento
```

**3 Pilares (GDC, análise de dezenas de chefes):**

1. **Legibilidade** — jogador entende o que o chefe vai fazer sem tomar dano primeiro
2. **Justiça** — todo ataque tem contra-jogada; erro é do jogador, não do RNG
3. **Personalidade** — chefe parece vivo; comportamento + animação contam quem ele é

### Regra dos 2 (aplicada em Isaac e Gungeon)

> Cada transição de fase muda no máximo 2 coisas:
> 1. Um novo padrão de ataque
> 2. Um dial numérico (velocidade, cooldown, número de projéteis)

Isso garante que jogador atribui o que mudou em vez de aprender uma luta nova do zero.

---

## 2. Análise: The Binding of Isaac

### Filosofia dos Chefes de Isaac

Isaac trata chefes como **puzzles de posicionamento**. O jogador não tem mira manual (tears são auto-aim na direção), então todo desafio é sobre **onde você está**, não **para onde você atira**.

### Chefes Analisados e Suas Mecânicas

#### Monstro (Basement — primeiro chefe)
**Aparência:** Massa de carne disforme, lábio leporino, um dente faltando
**Personalidade:** Birrento, jogando tudo que tem. Parece uma criança tendo um ataque
**Ataques:**
1. **Hop** — Pula em direção ao jogador. Usa sombra no chão como telegrafo
2. **Vomit** — Cospe 8 projéteis em cone (sorri antes de cuspir — tell facial)
3. **Jump Slam** — Sobe da tela e cai na posição do jogador + radial de tiros no impacto
**O que ensina:** Baitar o pulo. Posicionamento.
**Por que funciona:** 3 ataques simples, cada um com tell claro. Primeiro chefe = tutorial de padrões.

#### Larry Jr. (Basement — minhoca segmentada)
**Aparência:** Minhoca com segmentos que têm HP individual
**Personalidade:** Teimosa, persiste na mesma direção. Se você ficar num canto, ela vai até você
**Ataques:**
1. **Burrow-wiggle** — Nada pelo chão em zigue-zague
2. **Spawn poop** — Deixa rastro de obstáculos
**Mecânica única:** Cada segmento tem HP próprio. Pode **dividir** em 2 minhocas menores se acertar no meio. Jogador decide: foco na cabeça (mata rápido) ou atirar em qualquer lugar (cria mais inimigos).
**O que adaptar:** Split por ponto fraco. Minhoca segmentada já temos (centopeia).

#### Gurdy Jr. (Caves — filha da Gurdy)
**Aparência:** Bola de carne com boca, olhos esbugalhados
**Personalidade:** Hiperativa, não para quieta. Quando fica com raiva (fase 2), SÓ ataca
**Ataques:**
1. **Spawn Pooter** — Invoca um inimigo voador
2. **Jump + radial** — Pula e atira 8 tiros ao cair
3. **Charge** — Corre em alta velocidade, quicando em paredes. SEM TELEGRAFO (proposital — perto = perigo)
**Fases:** Fase 2 (<50% HP): só usa charge, continuamente
**O que adaptar:** Charge que quica em parede. Fase que simplifica (remove opções, foca no ataque mais perigoso).

#### Peep (Caves — olhos voadores)
**Aparência:** Monstro amarelo que atira urina. Olhos grandes e saltados
**Personalidade:** Nojento, relaxado. Perde o controle conforme toma dano
**Ataques:**
1. **Jump** — igual Monstro
2. **Urine shot** — Padrão de 8 tiros amarelos em leque
3. **Creep** — Deixa poça amarela no chão que dança
**Mecânica única:** A 66% HP, UM olho se solta e voa pela sala (bloqueia tiros, dano de contato). A 33%, o SEGUNDO olho também. Os olhos são indestrutíveis — você tem que trabalhar em torno deles.
**O que adaptar:** Fase que adiciona obstáculo permanente (não inimigo). Jogador adapta rota de fuga.

#### Chub (Caves — minhoca gigante)
**Aparência:** Minhoca enorme com boca circular cheia de dentes
**Personalidade:** Gulosona. Persegue em linha reta. Se bater em parede, fica atordoada
**Ataques:**
1. **Charge** — Atravessa a sala em linha reta. Se bater em parede, fica tonta (vulnerável)
2. **Spawn worms** — Invoca minhocas pequenas
3. **Burrow** — Some e aparece em outro lugar
**Mecânica única:** A parede é sua aliada. Fazer Chub bater na parede = janela de dano grátis.
**O que adaptar:** Chefes que interagem com o ambiente. Posicionamento importa.

#### Isaac (Cathedral — chefe final da rota "good")
**Aparência:** Isaac (criança) deitado no chão. Fase 2: senta. Fase 3: cresce asas
**Personalidade:** Triste, relutante. Você está matando uma criança
**Ataques (3 fases):**
1. **Fase 1 (deitado):**
   - 10 linhas de projéteis em TODAS direções
   - 8 grupos de projéteis que curvam de volta
   - Disparo contínuo de tears
2. **Fase 2 (sentado):**
   - 4 projéteis em cruz que se dividem em 4 menores
   - 8 projéteis em todas direções
   - Invoca Angelic Babies (adds)
   - Crack the Sky: feixes de luz em locais aleatórios
3. **Fase 3 (asas, MOVIMENTO):**
   - Teleporta pra fora, varre a tela com feixes de luz (sombra avisa)
   - Volta e faz padrões da fase 1
   - Move em direção ao jogador com dashes curtos
**O que adaptar:** Transição de fase que muda o comportamento radicalmente (estático → móvel). Telas cheias de projéteis que forçam movimento preciso.

### Padrões de Isaac: Catálogo

| Padrão | Descrição | Utilizado por |
|--------|-----------|---------------|
| Radial burst | Anel completo de tiros | Mom's Heart, Isaac |
| Cone / Fan | Leque de tiros | Monstro (vomit) |
| Aimed shot | Tiro na direção do jogador | Quase todos |
| Homing | Tiro que persegue | The Haunt, etc |
| Burst | Rajada em leque | Monstro, Peep |
| Spiral | Projéteis em espiral | Isaac, Hush |
| Split | Projétil que divide | Isaac (fase 2) |
| Creep | Poça de dano no chão | Peep, The Bloat |
| Charge | Investida em linha reta | Chub, Gurdy Jr, Pin |
| Jump | Pulo direcional | Monstro, Peep |
| Summon | Invoca inimigos | Gurdy, Duke of Flies |
| Beam | Laser contínuo | Isaac (Crack the Sky) |
| Brimstone | Laser grosso carregado | Satan, Isaac bosses |
| Bounce | Ricochete em paredes | The Cage, etc |
| Burrow | Some no chão, aparece | Chub, Pin |
| Split on death | Divide em menores | Fistula, Blob |
| Orbital | Orbitais defensivos | Duke of Flies, The Hollow |

### Progressão de Chefes em Isaac

```
Basement: Monstro, Gemini, Larry Jr, Dingle (simples, 1-2 ataques)
  → Caves: Peep, Chub, Gurdy (adiciona mecânica única, creep)
    → Depths: Mom's Foot (arena interativa, múltiplos ataques)
      → Womb: Mom's Heart (bullet hell puro, 4+ padrões)
        → Cathedral: Isaac (3 fases, movimento, tela cheia)
          → Chest: ??? / Blue Baby (bullet hell final)
```

Cada andar adiciona complexidade:
- **Layer 1 (Basement):** Aprender padrões
- **Layer 2 (Caves):** Aprender mecânicas únicas
- **Layer 3 (Depths):** Multitarefa (ataque + ambiente)
- **Layer 4+:** Bullet hell puro

---

## 3. Análise: Enter the Gungeon

### Filosofia dos Chefes de Gungeon

Gungeon combina bullet hell com twin-stick shooter. Chefe testa **dodge roll** + **posicionamento** + **gestão de munição**. Todo ataque tem dano baixo (1 coração de 6) mas a TELA INTEIRA é coberta de balas — dodge roll com i-frames é a resposta.

Dodge Roll (o estúdio) descreve o design assim:
> "If an attack felt unfair or just wrong, it was rarely a case of cutting it. Instead, it was about ensuring attack B didn't come directly after attack A, so its bullets had a chance to exit the screen."

### Chefes Analisados e Suas Mecânicas

#### Gatling Gull (Keep — primeira masmorra)
**Aparência:** Pássaro musculoso com gatling gun
**Personalidade:** Agressivo, barulhento. Atira primeiro, pensa depois
**Ataques:**
1. **Gatling burst** — Rajada de tiros em leque estreito. Anda em direção ao jogador
2. **Rocket** — Mísseis teleguiados (lentos, dá pra desviar)
3. **Airstrike** — Sobe e chove balas no chão (marcadores vermelhos avisam onde)
4. **Spin** — Gira atirando em círculo
**Arena:** Pilares no centro para cover
**O que adaptar:** Primeiro chefe = tutorial de bullet hell. Ataques lentos, bem espaçados, tells claros. Pilares (cover) são essenciais.

#### Bullet King (Keep — primeira masmorra)
**Aparência:** Caveira gigante coroada sentada num trono
**Personalidade:** Rei preguiçoso. Não levanta do trono. Atira com desdém
**Ataques:**
1. **Spinning burst** — Gira o trono atirando em círculo. Alterna direção entre ondas
2. **Tight circle** — Círculo apertado de balas que exige dodge roll ou blank
3. **Summon** — Invoca Bullet Kin
4. **Laser** — Feixe de laser da boca
**Mecânica única:** Fica atordoado depois do tight circle — janela de dano.
**O que adaptar:** Chefe parado que ainda é perigoso. Janela de vulnerabilidade após ataque forte.

#### Trigger Twins (Keep — gêmeas)
**Aparência:** Duas Bullet Kin gêmeas (Smiley e Shades)
**Personalidade:** Uma é otimista (Smiley, que atira), outra é séria (Shades, que atira mais forte). Brigam entre si
**Ataques:** Cada uma tem HP próprio. Quando uma morre, a outra fica ENRAIVECIDA (2x velocidade, 2x dano)
**Mecânica única:** Dual boss. Ordem de eliminação importa.
**O que adaptar:** Chefe duplo com sinergia. Uma morre → outra fica mais forte.

#### Ammoconda (Gungeon Proper — segunda masmorra)
**Aparência:** Cobra mecânica segmentada
**Personalidade:** Faminta. Come os nodes que spawnam para crescer e se curar
**Ataques:**
1. **Charge** — Investida rápida
2. **Spit** — Cospe projéteis
3. **Node spawn** — Spawna nodes no chão que ela come para **curar HP** e crescer
**Mecânica única:** Jogador compete com o chefe pelos nodes. Destruir node antes do chefe comer = nega a cura.
**O que adaptar:** Recurso compartilhado. Jogador decide: atacar chefe ou negar cura?

#### Beholster (Gungeon Proper)
**Aparência:** Olho gigante com asas, múltiplos tentáculos
**Personalidade:** Paranoico. Atira em todas direções ao mesmo tempo
**Ataques:**
1. **Eye laser** — Laser do olho principal (telegrafado, lento)
2. **Homing missles** — Mísseis teleguiados dos tentáculos
3. **Tentacle slap** — Tentáculos batem no chão
4. **Bullet hell** — Spawna balas em todas direções
**Arena:** Sala circular
**O que adaptar:** Chefe que ataca em múltiplas frentes simultaneamente. Força o jogador a priorizar ameaças.

#### Gorgun (Gungeon Proper)
**Aparência:** Metade mulher, metade cobra. Cabelo de serpentes
**Personalidade:** Sedutora, mortal. Quer te petrificar
**Mecânica única:** Olhar petrificante. Se você fica na frente dela por muito tempo, suas pernas viram pedra (não pode atirar por alguns segundos). A cura: dodge roll.
**Ataques:** Padrão bullet hell + petrification gaze
**O que adaptar:** Mecânica de status que muda como você joga. Não é só dano — é "perde a habilidade de atirar".

#### Cannonbalrog (Black Powder Mine — terceira masmorra)
**Aparência:** Bala de canhão demoníaca
**Personalidade:** Explosivo. Tudo nele é explosão
**Ataques:**
1. **Charge** — Atravessa a sala. Se bater em parede, spawna 4 projéteis em cruz (explosão)
2. **Grand Slam** — Pula no centro, cria onda de choque
3. **Spiral barrage** — Gira atirando em espiral
4. **Summon Bullet Kin** — Invoca inimigos
**Mecânica única:** Fica invulnerável durante o Grand Slam e Spiral. Você tem que desviar até ele terminar.
**O que adaptar:** Fases de "sobrevivência pura" onde você não pode causar dano.

#### Mine Flayer (Black Powder Mine)
**Aparência:** Cthulhu mecânico
**Personalidade:** Trapaceiro. Mina o chão, teleporta, some
**Ataques:**
1. **Mine field** — Espalha minas no chão (visíveis, lentas)
2. **Mine explosion** — Minas explodem quando você chega perto
3. **Teleport** — Some e aparece em outro lugar
4. **Bullet waves** — Ondas de projéteis
**Arena:** Salas com obstáculos
**O que adaptar:** Controle de área (zoning). Minas forçam você a se mover de forma previsível — e o chefe atira onde você vai estar.

#### High Priest (Hollow — quarta masmorra)
**Aparência:** Bruxo flutuante com múltiplos olhos
**Personalidade:** Imprevisível. Usa truques sujos. É o chefe que mais varia ataques
**Ataques:**
1. **Ring + skulls** — Anel de balas + crânios teleguiados que explodem em 6 tiros
2. **Darken room** — Escurece a sala e teleporta atirando de lugares aleatórios
3. **Rotating arms** — Estica braços e atira jatos giratórios de balas
4. **Random spray** — Braços esticados, balas em todas direções
5. **Wide spreads** — Leques largos de balas triangulares
6. **Fast homing** — Tiro rápido teleguiado
**O que adaptar:** Chefe com MAIOR variedade de ataques. Exige que jogador reconheça qual ataque está vindo e responda adequadamente.

#### Kill Pillars (Hollow)
**Aparência:** Quatro estátuas de pedra (Heretic, Blasphemous, Heretical, Idolater)
**Personalidade:** Dança sincronizada. Trabalham em equipe
**Ataques:**
1. **Slam + spokes** — Uma estátua bate no chão, criando raios de balas que giram
2. **Rings** — Anéis concêntricos de balas que se expandem
3. **Charge** — Estátuas deslizam pela sala
**Mecânica única:** Cada estátua tem HP próprio. Matar uma reduz a densidade de balas. Ordem importa?
**O que adaptar:** Chefe múltiplo com padrão geométrico sincronizado.

#### Wallmonger (Hollow)
**Aparência:** Parede de carne com boca enorme
**Personalidade:** Implacável. Empurra você contra a parede oposta
**Arena:** Sala horizontal estreita. Chefe ocupa a parede DIREITA. Fogo no chão.
**Ataques:**
1. **Fire breath** — Sopro de fogo que cobre metade da sala
2. **Bouncing bullets** — Balas que ricocheteiam nas paredes
3. **Flame jets** — Jatos de fogo do chão
4. **Fase 2:** Tela CHEIA de balas, brechas pequenas para dodge roll
**Mecânica única:** A arena É o ataque. Você é forçado a avançar contra o chefe porque o fogo empurra.
**O que adaptar:** Arena como parte do design do chefe. Sala estreita = menos espaço de manobra.

#### High Dragun (Forge — chefe final do andar 5)
**Aparência:** Dragão mecânico. Ocupa o TOPO da tela
**Personalidade:** Guardião. Sério, implacável. Fase 2 = desespero
**Ataques (2 fases):**
1. **Fase 1:**
   - Fire breath (sopro de fogo)
   - Bouncing bullets
   - Summon knives (adagas que caem do céu, sombra avisa)
   - Bullet spreads
2. **Fase 2 (asas quebram, coração exposto):**
   - Grid bullet hell (grade de balas com brechas)
   - Dodge roll pelas brechas
   - Tiro no coração = dano
**O que adaptar:** Fase final = bullet hell puro. Tela cheia, padrões geométricos, brechas precisas. Jogador prova que domina dodge roll.

#### The Lich (Bullet Hell — chefe final verdadeiro)
**Aparência:** Esqueleto de feiticeiro. 3 formas: humanoide, torso gigante, espectro
**Personalidade:** A morte em pessoa. Cada fase é uma nova forma de morrer
**Ataques (3 fases):**
1. **Fase 1 (Gunslinger):** Atira padrões de balas como um Gungeoneer
2. **Fase 2 (Torso):** Bullet hell pesado, com ataques de área
3. **Fase 3 (Specter):** Arena GIRA. Você tem que atirar no centro enquanto desvia de balas que vêm de todos ângulos
**Mecânica única:** Fase 3 roda a arena. Desorientação.
**O que adaptar:** Fase que muda a geometria da arena.

### Padrões de Gungeon: Catálogo

| Padrão | Descrição | Utilizado por |
|--------|-----------|---------------|
| Radial burst | Anel completo | Bullet King, High Priest |
| Fan shot | Leque | Gatling Gull |
| Burst | Rajada | Gatling Gull, Trigger Twins |
| Aimed barrage | Rajada com lead | High Dragun |
| Spiral | Espiral expansiva | Cannonbalrog, High Priest |
| Homing missile | Míssil teleguiado lento | Beholster, Gatling Gull |
| Laser sweep | Laser que varre | Beholster, Bullet King |
| Shockwave | Onda de choque no chão | Cannonbalrog |
| Minefield | Mina no chão | Mine Flayer |
| Ring expand | Anel que expande | Kill Pillars |
| Spokes | Raios que giram | Kill Pillars |
| Bouncing bullet | Ricochete em paredes | Wallmonger, High Dragun |
| Grid | Grade de balas com brecha | High Dragun (fase 2) |
| Summon | Invoca inimigos | Bullet King, Cannonbalrog |
| Charge/ram | Investida | Ammoconda, Cannonbalrog |
| Breath | Sopro contínuo (cone) | Wallmonger, High Dragun |
| Teleport | Chefe some e aparece | Mine Flayer, High Priest |
| Arena rotation | Arena gira | Lich (fase 3) |
| Petrify | Status que trava | Gorgun |
| Heal nodes | Cura via recurso externo | Ammoconda |

### Progressão de Chefes em Gungeon

```
Keep (1): Gatling Gull, Bullet King, Trigger Twins (tutorial, tells claros, cover)
  → Gungeon Proper (2): Ammoconda, Beholster, Gorgun (mecânicas únicas, homing)
    → Black Powder Mine (3): Cannonbalrog, Mine Flayer, Treadnaught (arena hazards, invuln phases)
      → Hollow (4): High Priest, Kill Pillars, Wallmonger (bullet hell denso, padrões complexos)
        → Forge (5): High Dragun (bullet hell + fase final de grade)
          → Bullet Hell: The Lich (3 fases, arena rotaciona)
```

---

## 4. Lições de Ambos para o Lagarto

### O que Isaac ensina

1. **Padrões simples mas claros** — 3-4 ataques por chefe, cada um com tell único
2. **Mecânica única por chefe** — Peep (olhos), Chub (parede), Fistula (split)
3. **Fases que mudam comportamento** — Isaac (parado → móvel), Gurdy Jr (charge spam)
4. **Split por ponto fraco** — Larry Jr, Fistula. Jogador decide como matar
5. **Progressão de complexidade** — cada andar adiciona 1 layer de dificuldade

### O que Gungeon ensina

1. **Telegrafia > tempo** — tells visuais, não só temporais. Sombra, glow, linha no chão
2. **Padrões geométricos** — anéis, espirais, grades, leques. Fáceis de ler, difíceis de desviar
3. **Arena como parte do design** — Wallmonger (sala estreita), Gatling Gull (pilares)
4. **Ataques que não se sobrepõem** — timing entre ataques para balas anteriores saírem da tela
5. **Chefe que interage com o ambiente** — Cannonbalrog (bate em parede), Ammoconda (come nodes)

### O que aplicar no Lagarto

| Princípio | Isaac | Gungeon | Lagarto |
|-----------|-------|---------|---------|
| Padrões como dados | Parcial (hardcoded) | Total (data-driven) | **Data-driven** |
| Telegrafo ≥27f | Sim (visual) | Sim (visual + timing) | **Já temos** |
| Fases mudam 2 coisas | Sim | Sim | **Já temos** |
| Mecânica única | Sempre | Sempre | **Cada boss** |
| Arena interativa | Raro | Frequente | **Próximo passo** |
| Personalidade via animação | Pouca (sprites) | Média (animações) | **Procedural = vantagem** |
| Split/dividir | Sim | Sim | **Já temos (DIVISOR)** |
| Data-driven patterns | Não | Sim (BulletML) | **Sim (boss.py)** |

### A Grande Vantagem do Lagarto

Animação procedural permite **personalidade visível** sem custo de arte. Cada chefe pode ter postura, movimento, reações únicas — tudo gerado em código. Isso é algo que Isaac (sprites fixos) e Gungeon (animações pré-renderizadas) têm mais dificuldade de fazer.

---

## 5. Psicologia do Jogador em Boss Fights

### Princípios (Sid Meier GDC 2010 + análise de jogos)

1. **Falha precisa ser legível** — jogador sempre sabe POR QUE morreu. "Fiquei no canto quando veio o radial" > "morri de repente"
2. **Percepção > Realidade** — chefe com 1px de vida parece mais perigoso que chefe com 50% HP. Use isso: fase final com glow vermelho, shake, etc.
3. **Interessante ≠ Difícil** — decisão interessante > décima tentativa. Ammoconda (negocio cura vs dano) > High Priest (só desvia)
4. **Curva de aprendizado em espiral** — chefe ensina → testa → combina → surpreende

### O Ciclo do Boss Fight Ideal

```
┌─────────────────────────────────────────────────────┐
│                    Fase 1                           │
│  Aprende padrão A → Testa reflexo → Domina A       │
│         ↓                                           │
│                    Fase 2                           │
│  Aprende padrão B (novo) + A combinado → Adapta    │
│         ↓                                           │
│                    Fase 3                           │
│  Tudo que aprendeu + surpresa → Maestria           │
└─────────────────────────────────────────────────────┘
```

### Gatilhos Psicológicos por Fase

| Fase | O que o jogador sente | O que o design deve fazer |
|------|----------------------|---------------------------|
| Intro | "O que esse chefe faz?" | Telegrafar claramente o primeiro ataque |
| Fase 1 | "Entendi o padrão!" | Manter consistência, recompensar aprendizado |
| Transição | "O QUE MUDA?" | Mudança visível (cor, glow, postura, fala) |
| Fase 2 | "Ah, agora é outro jogo" | Adicionar 1 padrão novo, não 5 |
| Fase final | "VOU MORRER" | Glow vermelho, shake, música intensa |

---

## 6. Framework: BossAI 2.0

### FSM Atual (boss.py)

```
intro → approach → windup → attack → recover → [transition] → death
```

### FSM 2.0

```
INTRO (invulnerável, ~1s)
  → MOVEMENT (persegue/foge/flutua)
    → WINDUP (telegrafo ≥27f)
      → ATTACK (executa pattern)
        → RECOVER (vulnerável, pausa)
          → [se HP < threshold] TRANSITION (invulnerável, glow, anuncia novos patterns)
          → MOVEMENT
```

### Classe BossAI 2.0

```python
class BossAI:
    def __init__(self, boss, phases=None, personality=None):
        self.boss = boss
        self.phases = phases or default_phases()
        self.personality = personality or default_personality()
        self.phase_i = 0
        self.state = 'intro'
        self.state_timer = BOSS_INTRO_TIME
        self.cooldown = 0.0
        self.current_pattern = None
        self.mood = 'calm'
        self.mood_timer = 0.0
        self.consecutive_misses = 0  # pra frustration

    def tick(self, dt, game):
        target = game.nearest_player(self.boss.pos)
        self._update_mood(dt, target, game)
        self._maybe_advance_phase()
        return self._fsm(dt, game, target)

    def _update_mood(self, dt, target, game):
        """Atualiza mood baseado em contexto."""
        if not target:
            self.mood = 'calm'
            return
        dist = target.pos.distance_to(self.boss.pos)
        hp_frac = self.boss.hp / self.boss.max_hp

        if dist < BOSS_CORNERED_DIST:
            self.mood = 'cornered'
        elif hp_frac < 0.33:
            self.mood = 'enraged'
        elif hp_frac < 0.66:
            self.mood = 'agitated'
        elif self.consecutive_misses > FRUSTRATION_THRESHOLD:
            self.mood = 'frustrated'
        else:
            self.mood = 'calm'

    def _update_movement(self, dt, target):
        """Movimento varia por mood."""
        speed = self.phase().get('speed', BOSS_APPROACH_SPEED)
        mood_mult = self.personality.mood_speed.get(self.mood, 1.0)
        if self.boss.plan == 'tentacle':
            speed *= 0.5  # polvo é lento
        to = safe_norm(target.pos - self.boss.pos)
        return to, speed * mood_mult

    def _choose_pattern(self, target):
        """Escolhe pattern baseado em mood + distância."""
        available = list(self.phase()['patterns'])
        dist = target.pos.distance_to(self.boss.pos)
        # Filtra por range
        suitable = [p for p in available
                    if p['range'][0] <= dist <= p['range'][1]]
        if not suitable:
            suitable = available
        # Peso por mood
        weights = [self.personality.pattern_weight.get(p['name'], 1.0)
                   for p in suitable]
        return random.choices(suitable, weights=weights, k=1)[0]
```

---

## 7. Sistema de Padrões (Patterns)

### Estrutura de Dados

```python
PATTERN_LIBRARY = {
    'radial_burst': dict(
        fn=radial_burst,
        windup=0.6,
        telegraph='radial',
        tags={'projectile', 'close'},
        range=(0, 400),
        mood_weights={'cornered': 2.0, 'calm': 1.0},
    ),
    'fan_shot': dict(
        fn=fan_shot,
        windup=0.45,
        telegraph='fan',
        tags={'projectile', 'medium'},
        range=(100, 600),
        mood_weights={'calm': 1.0, 'agitated': 1.5},
    ),
    'aimed_barrage': dict(
        fn=aimed_barrage,
        windup=0.5,
        telegraph='line',
        tags={'projectile', 'ranged'},
        range=(200, 800),
        mood_weights={'frustrated': 2.0},
    ),
    'charge': dict(
        fn=charge_attack,
        windup=0.5,
        telegraph='line',
        tags={'melee'},
        range=(100, 500),
        mood_weights={'enraged': 2.0},
    ),
    'spiral': dict(
        fn=spiral_pattern,
        windup=0.7,
        telegraph='spiral',
        tags={'projectile', 'area'},
        range=(0, 800),
        mood_weights={'enraged': 1.5},
    ),
    'laser_sweep': dict(
        fn=laser_sweep,
        windup=0.8,
        telegraph='cone',
        tags={'laser'},
        range=(100, 800),
        mood_weights={'agitated': 1.5},
    ),
    'bounce_shot': dict(
        fn=bounce_shot,
        windup=0.4,
        telegraph='bounce',
        tags={'projectile', 'indirect'},
        range=(200, 600),
        mood_weights={'calm': 1.0},
    ),
    'minefield': dict(
        fn=minefield,
        windup=0.6,
        telegraph='mine',
        tags={'hazard', 'zone'},
        range=(0, 400),
        mood_weights={'frustrated': 1.5},
    ),
    'summon': dict(
        fn=summon_adds,
        windup=0.8,
        telegraph='horn',
        tags={'summon'},
        range=(0, 800),
        mood_weights={'cornered': 2.0},
    ),
    'shockwave': dict(
        fn=shockwave,
        windup=0.6,
        telegraph='shockwave',
        tags={'area', 'melee'},
        range=(0, 250),
        mood_weights={'enraged': 1.5},
    ),
}
```

### Novos Padrões a Implementar

Cada um deve seguir a interface: `(boss, game, target) -> None`

| Pattern | Descrição | Telegrafo | Inspiração |
|---------|-----------|-----------|------------|
| `charge_attack` | Investida em linha reta, quica em parede | Linha no chão da direção | Gurdy Jr, Chub |
| `spiral_pattern` | N projéteis em espiral expansiva | Círculo giratório crescendo | Isaac (fase 1), Cannonbalrog |
| `laser_sweep` | Laser que varre um arco | Cone que se preenche | Beholster, Bullet King |
| `bounce_shot` | Projétil que ricocheteia N vezes | Linha tracejada prevendo ricochetes | Wallmonger, Mine Flayer |
| `minefield` | Espalha minas no chão | Círculos pulsando no chão | Mine Flayer |
| `shockwave` | Onda de choque que se expande | Anel crescendo no chão | Cannonbalrog (Grand Slam) |
| `gravity_well` | Puxa jogador para um ponto | Vórtice com setas | Lich (fase 3) |
| `creep_wave` | Onda de poça de dano no chão | Líquido avançando | Peep, The Bloat |
| `beam_barrage` | Rajada de lasers telegrafados | Marcadores no chão | High Dragun (knives) |
| `teleport_strike` | Some, aparece em outro lugar, ataca | Sombra no destino | Mine Flayer, Isaac (fase 3) |

---

## 8. Sistema de Fases (Phases)

### Estrutura

```python
PHASE_KIT = {
    'hp_frac': 1.0,      # HP% que esta fase começa
    'patterns': [...],     # padrões disponíveis nesta fase
    'speed': 120,         # velocidade de movimento
    'cd_mul': 1.0,        # multiplicador de cooldown
    'dmg_mul': 1.0,       # multiplicador de dano (se aplicável)
    'summon': None,        # (opcional) dados de summon específicos
    'arena_change': None,  # (opcional) muda algo na arena
}
```

### Regra dos 2

Cada transição muda no máximo:

1. **1 pattern novo** (remove outro ou adiciona)
2. **1 dial numérico** (speed, cd, dano)

Exemplo de progressão de fase:

```python
def three_phase_kit():
    return [
        dict(hp_frac=1.0, patterns=['fan', 'radial'],
             speed=100, cd_mul=1.0),
        # Transição 1: adiciona summon
        dict(hp_frac=0.66, patterns=['fan', 'radial', 'summon'],
             speed=120, cd_mul=0.9),
        # Transição 2: troca radial por charge, acelera
        dict(hp_frac=0.33, patterns=['fan', 'charge', 'summon'],
             speed=150, cd_mul=0.7),
    ]
```

---

## 9. Telegrafia: Regras de Ouro

### Princípios (extraídos de Gungeon + Isaac)

1. **≥27 frames (0.45s a 60fps)** — tempo mínimo para jogador processar e reagir
2. **VISUAL, não só temporal** — glow, linha, anel, sombra. Não confie só que jogador "aprendeu o timing"
3. **Desenhe o RAIO, não só o aviso** — se é ataque de área, mostre o tamanho da área (regra do fase 2: estou dentro?)
4. **Telegrafo ESCALA com a dificuldade** — primeiro ataque tem tell longo (0.7s), versão enraged tem tell curto (0.35s)
5. **NUNCA mude o tell sem aviso** — se o ataque é igual, o tell é igual. Sempre.

### Tipos de Telegrafo

| Tipo | Descrição | Custo | Padrões que usam |
|------|-----------|-------|-------------------|
| `radial` | Círculo ao redor do chefe | 2 draws | radial_burst |
| `fan` | Duas linhas marcando o cone | 2 lines | fan_shot |
| `line` | Linha da boca ao alvo | 1 line | aimed_barrage, charge |
| `spiral` | Círculo giratório que cresce | 1 circle + glow | spiral_pattern |
| `cone` | Setor circular se preenchendo | 1 arc | laser_sweep |
| `bounce` | Linha tracejada prevendo ricochetes | N lines | bounce_shot |
| `mine` | Círculos pulsando no chão | N circles | minefield |
| `horn` | Glow amarelo + círculo expansivo | 1 circle + glow | summon |
| `shockwave` | Anel que se expande no chão | 1 circle | shockwave |
| `vortex` | Espiral que puxa | 1 spiral + setas | gravity_well |

### Código de Telegrafo

```python
def _draw_telegraph(self, surf, cam, pattern_id, progress):
    """progress: 0.0 (início) → 1.0 (vai disparar)"""
    pat = PATTERN_LIBRARY[pattern_id]
    kind = pat['telegraph']
    mouth = self.boss.spine.joints[0]
    sp = cam.w2s(mouth)
    blink = 0.5 + 0.5 * math.sin(progress * progress * 40)
    col = palette.lighten(self.boss.color, 0.35)
    r = int(self.boss.max_r * cam.zoom)

    if kind == 'radial':
        radius = int(BOSS_RADIAL_SPEED * 0.9 * cam.zoom)
        pygame.draw.circle(surf, col, sp, radius, max(1, int((1 + 2 * progress) * cam.zoom)))
        palette.glow(surf, sp, radius, col, (0.12 + 0.2 * progress) * blink)

    elif kind == 'fan':
        base = self._windup_target - mouth if self._windup_target else Vector2(1, 0)
        base = safe_norm(base)
        for s in (-0.5, 0.5):
            edge = base.rotate(s * BOSS_FAN_SPREAD)
            far = mouth + edge * 340
            pygame.draw.line(surf, col, sp, cam.w2s(far), max(1, int((1 + 2 * progress) * cam.zoom)))

    elif kind == 'line':
        aim = self._windup_target or (mouth + Vector2(100, 0))
        pygame.draw.line(surf, col, sp, cam.w2s(aim), max(1, int((1 + 3 * progress) * cam.zoom)))
        palette.glow(surf, cam.w2s(aim), int(14 * cam.zoom), col, 0.2 + 0.3 * progress)

    elif kind == 'spiral':
        n_spokes = 8
        for i in range(n_spokes):
            ang = (360 / n_spokes) * i + progress * 720
            end = mouth + vfrom_angle(ang, r * (1.5 + progress * 2))
            pygame.draw.line(surf, col, sp, cam.w2s(end), max(1, int(2 * cam.zoom)))

    elif kind == 'shockwave':
        radius = int(r * progress * 3 * cam.zoom)
        pygame.draw.circle(surf, col, sp, radius, max(1, int(3 * cam.zoom)))
        palette.glow(surf, sp, radius, col, 0.15 * blink)
```

---

## 10. Sistema de Personalidade (Mood)

### O que é

Mood é o estado emocional atual do chefe. Afeta:
- Velocidade de movimento
- Escolha de padrões (pesos)
- Cor do glow
- Postura (procedural posing)
- Tamanho dos telegrafos (enraged = mais rápido = tell menor)

### Implementação

```python
class BossPersonality:
    """Define como um chefe REAGE a situações."""
    def __init__(self):
        self.mood_speed = {
            'calm': 1.0,
            'agitated': 1.3,
            'enraged': 1.6,
            'frustrated': 1.4,
            'cornered': 0.8,  # recua
        }
        self.pattern_weights = {}  # pattern_id: peso_base
        self.mood_colors = {
            'calm': None,       # cor normal
            'agitated': (255, 180, 50),   # laranja
            'enraged': (255, 50, 50),     # vermelho
            'frustrated': (200, 50, 255), # roxo
            'cornered': (50, 100, 255),   # azul
        }
        self.tells_faster = {  # enraged = tells mais rápidos
            'enraged': 0.65,
            'agitated': 0.8,
        }

    def get_windup_mult(self, mood):
        """Quanto mais agressivo, menos windup (tell mais curto)."""
        return self.tells_faster.get(mood, 1.0)

    def get_glow_color(self, mood, base_color):
        """Glow com cor do mood."""
        mood_color = self.mood_colors.get(mood)
        if mood_color:
            return palette.mix(base_color, mood_color, 0.4)
        return base_color
```

### Personalidade por Chefe

Cada chefe tem personalidade própria que dita:
- **Tendência de distância** — prefere ficar longe (ranged) ou perto (melee)?
- **Reação a dano** — fica agressivo (enraged) ou cauteloso (cornered)?
- **Padrões favoritos** — quais padrões ele mais usa?
- **Teimosia** — continua no mesmo padrão mesmo sem acertar, ou varia?

---

## 11. Arena Design

### Princípios

1. **Cada arena deve ter um elemento único** — pilares, fenda, poças, obstáculos
2. **Arena conta uma história** — onde o chefe vive? O que o chão conta?
3. **Arena afeta o combate** — não é só cenário

### Tipos de Arena para Lagarto

| Tipo | Descrição | Para qual chefe |
|------|-----------|-----------------|
| **Clareira circular** | Espaço aberto, sem obstáculos | Chefes bullet hell |
| **Corredor** | Sala estreita (horizontal ou vertical) | Chefes de charge |
| **Pilares** | 2-4 pilares no centro | Chefes que precisam de cover |
| **Poças** | Áreas de água/veneno no chão | Chefes que empurram |
| **Plataformas** | Múltiplos níveis de altura | Chefes voadores |
| **Caverna** | Paredes irregulares, cantos | Chefes de emboscada |

---

## 12. Implementação Técnica

### Arquivos

| Arquivo | Conteúdo | Status |
|---------|----------|--------|
| `boss.py` | BossAI, patterns, phases | Existe, expandir |
| `boss_personality.py` | BossPersonality, mood system | Novo |
| `boss_patterns.py` | TODOS os padrões de ataque | Novo (separar de boss.py) |
| `boss_telegraph.py` | Desenho de telegrafos | Novo |
| `config.py` | Dials de boss | Existe, expandir |

### Mudanças no `boss.py`

- Separar patterns em `boss_patterns.py`
- Adicionar `mood` system
- Adicionar telegraph drawing module
- BossAI 2.0 com FSM expandida
- Suporte a arena hazards

### Integração com `rounds.py`

- `rounds._spawn_boss` escolhe boss por tema + profundidade
- Boss pode modificar arena (spawn hazards)
- `draw_boss_bar` já existe

---

## Referências

- **Rain World GDC 2016**: https://www.youtube.com/watch?v=sVntwsrjNe4
- **Rock Paper Shotgun - How Enter the Gungeon brought bullet hell to the dungeon crawler**: https://www.rockpapershotgun.com/how-enter-the-gungeon-brought-bullet-hell-to-the-dungeon-crawler
- **GDC Vault - Boss Design**: https://gdcvault.com
- **Enter the Gungeon Boss Guide (Gameranx)**: https://gameranx.com/features/id/47856/article/enter-the-gungeon-boss-guide
- **Binding of Isaac Bosses Wiki**: https://bindingofisaacrebirth.fandom.com/wiki/Bosses
- **Sid Meier - Psychology of Game Design (GDC 2010)**: https://www.youtube.com/watch?v=MtzCLd93SyU
- **Game Boss Fight Design Explained**: https://solana.garden/guides/game-boss-fight-design-explained
