# Plano 07 — Pendências gerais (levantamento consolidado)

**Data:** 2026-07-21. **Substitui o doc 06** (que ficou parcialmente desatualizado:
seção 6 marcava Aranha-Rei / Serpente Cristal / Terror Alado como pendentes; os três
já estão feitos). Este doc é a fonte da verdade das pendências a partir de agora.

Levantado por auditoria do contexto: estado do git, marcadores no código,
diagnósticos recorrentes, e o que ficou substituído/adiado por decisão.

Legenda: 🔴 bug/risco · 🟡 dívida/limpeza · 🟢 feature/conteúdo · ⚪ pesquisa/decisão

---

## A. Pontas soltas concretas achadas nesta sessão

### A1. 🔴 Lixo versionado — screenshots commitados sem querer
`image.png` (281 KB) e `image-1.png` (94 KB) entraram no commit `761db8e`
("Centipede and octopus"). Estão **deletados no working tree mas ainda
rastreados** (aparecem como `D` no `git status` faz várias sessões).
- [ ] `git rm image.png image-1.png` + commit (ou restaurar se forem
      intencionais — não parecem, são screenshots de dev).

### A2. 🟡 Atributos de chefe não declarados em `AILizard.__init__`
`is_boss`, `glow_body`, `boss_name`, `emblem` são setados dinamicamente em
`rounds._spawn_boss` mas nunca declarados no `__init__`. Funciona (Python
permite), e todo LEITOR usa `getattr(..., default)`, então não quebra — mas:
- gera ruído constante do pyright ("Cannot assign to attribute ... for class
  AILizard");
- um acesso direto `e.is_boss` num não-chefe daria `AttributeError`.
- [ ] Declarar os 4 no `AILizard.__init__` com default (`is_boss=False`,
      `glow_body=False`, `boss_name=None`, `emblem=None`). Barato, mata o ruído.

### A3. 🟡 `projectile.spit(effect=...)` — anotação de tipo incompleta
Assinatura é `effect='poison'` (tipo `str`), mas `None` é valor de runtime
**documentado e válido** (`self.effect  # None | 'poison' | 'slow'`, e o único
uso checa `== 'slow'`). Todo `spit(effect=None)` (boss.py, weapons.py) dispara
erro do pyright. Não é bug — é anotação faltando.
- [ ] Tipar `effect` como `Optional[str]` (ou default `None`) pra calar o ruído.

### A4. 🟡 Testes dirigidos de chefe usam `random` sem seed
Os `test_*_boss.py` (scratchpad, não versionados) rodam milhares de frames de
combate estocástico e às vezes falham em pegar um padrão específico dentro da
janela, ou o retry-loop de spawn (pool com 4 chefes no tier5+) não acha o
chefe-alvo em N tentativas. Não é bug de produção — é flakiness de teste.
- [ ] Se esses testes forem promovidos pro repo: `random.seed(...)` fixo no
      topo de cada um. Hoje são scratchpad, então baixa prioridade.

### A5. 🟢 Serpente de Cristal — mecânicas do doc 03 substituídas
Doc 03 pede "Reflection" (espelha tiro do jogador de volta) e "Fractal Burst"
(projétil que se divide no meio do voo). **Nenhum dos dois existe no motor de
projéteis** (sem lógica de reflexão nem split-em-voo). Substituídos por
spiral/deathroll pra não ficar pela metade — decisão registrada, não lacuna
silenciosa. Se quiser as mecânicas reais:
- [ ] `Projectile.reflect` (inverte hostile+vel ao bater em X) — parcialmente
      já existe no item Contragolpe da rabada, dá pra generalizar.
- [ ] `Projectile.split_at` (divide em 2 num t do voo) — lógica nova em
      `game._update_projectiles`.

### A6. 🟢 Identidade visual dos chefes ainda é só emblema no HUD
Cada chefe tem emblema pixel art no HUD, mas o CORPO continua sendo "inimigo
padrão, só que grande" com override de cor/partes do genoma. O doc 03 descreve
partes/props únicos (coroa do Rei, engrenagem da Centopeia, etc.) NO corpo.
- [ ] Partes exclusivas por chefe em `parts.py` (toca genoma/desenho por chefe)
      — escopo médio, foi conscientemente deixado de fora até agora.

---

## B. Chefes restantes (3 de 11) — precisam de infra nova, não são reuso

Feitos (8/11): Rei Lagarto, Centopeiadeira, Kraken-Mor, Primordial (normal
5/10/15/20) + Mãe-Escaravelho, Aranha-Rei, Serpente de Cristal, Terror Alado
(endless, pool tier5+). **Nota:** Terror Alado saiu por REUSO do corpo `wasp`
+ flag `flying=True` (via `boss_attrs`), NÃO pelo plano `winged` do doc — o
`winged` como body-plan próprio (asas com phase-oscillator) segue não-feito e
provavelmente não é mais necessário.

### B1. 🟢 OLHO-SÍSMICO — corpo novo `orbital`
- [ ] `genome.plan='orbital'` no `__slots__` + `rebuild_body`/`draw`: esfera
      flutuante + tentáculos finos (sub-cadeias, tipo os braços do polvo) + íris
      que segue o jogador.
- [ ] Mecânica: crítico só no olho ABERTO (piscada aleatória curta).
- [ ] Padrões: gaze (laser que varre — precisa de `laser_sweep`), shockwave (já
      existe), spawn de orbes (reusa summon).

### B2. 🟢 MURALHA — precisa de sistema de arena/confinamento
- [ ] Mundo hoje é aberto contínuo, sem salas. Muralha ocupa um lado e empurra
      o jogador contra ela — requer confinamento (paredes temporárias/bordas de
      arena). **Requisito de infra, não só de dados.**
- [ ] Só depois: o chefe em si (parede fixa, boca, olhos, fogo que empurra).

### B3. 🟢 ANKH — chefe de 4 formas (o mais trabalhoso)
- [ ] 4 formas completas trocando por `rebuild_body` na virada de fase (caçador
      ágil → tanque → tentáculo → forma final), cada uma com kit próprio.
- [ ] "Revive ataques de chefes anteriores" — reusa os phase-kits já escritos.
- [ ] Dissolve em partículas na transição — candidato natural pro
      `CosmeticSkeleton` que foi adiado por YAGNI (ver seção E).

### B4. 🟡 Padrões de catálogo ainda não implementados
Usados pelos chefes acima: `laser_sweep`, `bounce`, `minefield`,
`gravity_well`, `teleport_strike`. Implementar sob demanda quando o chefe que
usa cada um for escrito (evita código especulativo sem chamador).

---

## C. Animação procedural (doc 04 restante)

### C1. 🟡 Código morto em `anim.py`
3 das 4 classes têm **zero instâncias** (só `Vector2Spring` está em uso):
- [ ] `SpringDamper` (1D) — candidatos: chacoalho de placas, olhos.
- [ ] `PhaseOscillator` — substituir os `math.sin(wobble*X + i*Y)*Z` espalhados
      em `parts.py` (espinhos/nadadeiras/antenas) por instâncias próprias.
- [ ] `Anticipation` — hoje `_ai_lunge`/`_ai_ranged`/windup de chefe usam timer
      manual; poderia usar essa classe. **Ou** remover as 3 classes se não for
      usar (é infra sem chamador — YAGNI diz cortar).

### C2. 🟢 Pose por estado de IA
- [ ] Caçando (agachado, cauda erguida) / fugindo (baixo) / agressivo
      (arqueado). Sistema novo — reusa `squat_bias`/`leg_pull` já existentes.
- [ ] `_ai_melee` com wind-up — **muda o timing real do dano de contato de todo
      inimigo base**, é rebalanceamento, não só visual. Precisa de decisão.

### C3. 👅 Língua — reescrita com IK (doc 06 §3)
- [ ] Mais grossa; animação tipo camaleão (IK FABRIK/2-bone; alongar/retrair/
      curvar). Referência: língua real de camaleão + Rain World.

### C4. 🎨 Outline consistente (doc 05 inteiro)
- [ ] `outline_from_surf()` via `pygame.mask` (técnica DaFluffyPotato).
- [ ] Aplicar em pernas (`leg.py`) e língua (`_draw_tongue`) — hoje sem outline.
- [ ] Corpo já tem outline poligonal, não mexer.

---

## D. Balanço / gameplay

### D1. 🔧 Performance — colisão lenta em ondas altas (doc 06 §1, não investigado)
- [ ] Instrumentar `collision.py` (nº hitboxes, testes/frame, broad vs narrow).
- [ ] Confirmar que `rebuild_body` (Centopeiadeira encolhe todo frame de fase,
      Larva cresce) não vaza segmentos/colliders.
- [ ] Medir com `--profile`. **Suspeito nº1:** chefes segmentados grandes
      (Serpente 2.0 length, Centopeiadeira) multiplicam pontos de amostra.

### D2. 🟢 Escalonamento de dificuldade mais agressivo (doc 06 §5)
- [ ] HP/velocidade/quantidade/campeões subindo mais rápido; evitar snowball no
      meio da run.

### D3. 🧬 Evoluções — tirar cauda-clava da árvore (doc 06 §4)
- [ ] Remover clava das cartas de mutação; manter só como Charm.

---

## E. Música + assets + pesquisa (baixa prioridade / longo prazo)

### E1. 🎵 Fase M — música adaptativa em stems
- [ ] Stems por intensidade via `/music-generator`, mix ao vivo por vida/
      inimigos/combo/chefe, fallback synth se ausente.

### E2. 🖼️ Assets restantes
- [ ] `tent_beetle.png` ligado ao acampamento (`_draw_camp_pois` ainda 100%
      procedural).
- [ ] Separar id do charm `ferrao` do id da arma `ferrao` antes de gerar o PNG
      do charm (colisão de id conhecida).
- [ ] Pré-escala NEAREST por fator inteiro antes do `present()` (nitidez de
      ícone) — hoje `assets.icon` usa smoothscale.
- [ ] Props de acampamento (portas, ninho), flora/mundo.

### E3. ⚪ Pesquisa e documentação (doc 01 refs)
- [ ] Estudar Rain World GDC, Merxon22, tutoriais de IK; guia interno.

---

## F. Adiados por DECISÃO de arquitetura (não são pendências)

- **Pixelização** (`PIXEL_SCALE`): implementada, testada, e **desligada a
  pedido** (=1). Mecanismo fica no código; não reativar sem pedido.
- **Ground Adaptation** (doc 01 §4): jogo top-down flat, sem campo de altura.
- **`CosmeticSkeleton` genérico** (doc 01 §10): YAGNI; revisitar SE ANKH (B3)
  precisar de cosmética própria mais rica.
- **Anticipation no jogador** (dash/rabada/língua): disparam na borda do botão
  de propósito (input buffer documentado no CLAUDE.md); atrasar pioraria o feel.
- **`smoothscale` no downsample da pixelização**: já corrigido pra NEAREST nas
  duas etapas (ficava borrado); só relevante se reativar a pixelização.
