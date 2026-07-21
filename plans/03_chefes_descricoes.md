# Chefes do Lagarto — Descrições Detalhadas

---

**10 chefes + PRIMORDIAL final.** Cada um usa um corpo procedural existente ou novo, com ataques, fases, personalidade e animação procedural próprias.

---

## Índice

1. [REI LAGARTO — O Tirano do Deserto](#1-rei-lagarto)
2. [A CENTOPEIADEIRA — A Engrenagem Viva](#2-centopeiadeira)
3. [KRAKEN-MOR — O Abraço do Abismo](#3-kraken-mor)
4. [TERROR ALADO — A Praga dos Céus](#4-terror-alado)
5. [OLHO-SÍSMICO — O Observador](#5-olho-sismico)
6. [MÃE-ESCARAVELHO — A Colmeia](#6-mae-escaravelho)
7. [ARANHA-REI — A Tecedeira](#7-aranha-rei)
8. [SERPENTE DE CRISTAL — A Fractal](#8-serpente-cristal)
9. [A MURALHA — O Portão](#9-muralha)
10. [ANKH — A Eterna](#10-ankh)
11. [PRIMORDIAL — O Primeiro Lagarto](#11-primordial)

---

## 1. REI LAGARTO — O Tirano do Deserto

**Aparição:** Onda 5 (primeiro chefe)
**Corpo:** Lizard (plan='standard'), escala 2.5x

### Aparência

Lagarto colossal, verde-escuro com faixas douradas. Crista dorsal de espinhos que vai da cabeça à cauda, cada espinho com ponta dourada. Olhos âmbar que brilham. Cauda grossa com clava óssea. Cicatrizes no focinho — velho lutador.

### Animação Procedural

- **Marcha:** Pesada (angular_damping=0.5). Cada passo faz o chão tremer (shake pequeno no impacto)
- **Crista:** Espinhos com spring-damper (stiffness=14). Balançam com o movimento, ficam eriçados quando agressivo (target_angle muda por mood)
- **Cauda:** Spring chain (stiffness=10 na base, 5 na ponta). Overshoot grande. Quando enraged, cauda sobe (postura de ataque)
- **Respiração:** Inspira fundo antes de ataques ranged (peito expande, glow na boca)
- **Olhos:** Perseguem o jogador com spring angular (atraso natural)
- **Postura:** Calmo = cabeça baixa, cauda arrastando. Agressivo = cabeça erguida, cauda levantada, espinhos eriçados

### Personalidade

**Orgulhoso.** Anda devagar, com ar de superioridade. Quando toma dano, olha para o ferimento, depois para o jogador — como se dissesse "você vai pagar por isso". Fase 2: fica visivelmente irritado (bufa, bate o rabo no chão). Fase 3: desesperado mas ainda orgulhoso — ataca sem parar, respiração ofegante visível.

### Ataques

**Fase 1 (100-66% HP):** `calm`
1. **Fan Shot** — Cospe 5 projéteis em leque. Telegrafo: glow amarelo na boca, 0.5s
2. **Tail Slam** — Bate a cauda no chão, cria 3 ondas de choque que se expandem. Telegrafo: cauda levanta, glow na clava, 0.6s
3. **Charge** — Investida em linha reta. Telegrafo: linha vermelha no chão, 0.4s

**Transição 1 (66%):** Glow dourado → laranja. Rugido (shake na tela). Espinhos eriçam permanentemente.

**Fase 2 (66-33% HP):** `agitated`
- Mantém Fan Shot + Charge
- Adiciona **Radial Burst** — Anel de 12 projéteis. Telegrafo: círculo ao redor do corpo, 0.6s
- Speed 1.3x

**Transição 2 (33%):** Glow laranja → vermelho. Olhos brilham. Respiração ofegante visível.

**Fase 3 (<33% HP):** `enraged`
- Mantém Radial Burst + Charge
- Troca Fan Shot por **Spiral Barrage** — Projéteis em espiral expansiva
- Speed 1.6x, cooldown 0.7x

### Mecânica Única: Cicatriz

Cada 25% de HP perdido, o Rei Lagarto "marca" o chão com uma cicatriz (fenda no tile). Pisar na fenda dá dano de contato e aplica slow. As fendas somem na transição de fase. Jogador precisa reposicionar.

---

## 2. A CENTOPEIADEIRA — A Engrenagem Viva

**Aparição:** Onda 7
**Corpo:** Centipede (plan='segmented'), escala 2.0x

### Aparência

Centopeia de 12 segmentos, cada um um anel metálico enferrujado que range. Cabeça é uma engrenagem dentada com um olho vermelho no centro. Patas são pinças de metal que arranham o chão. Deixa rastro de faíscas.

### Animação Procedural

- **Locomoção:** Onda metacronal nas patinhas (já implementada). Velocidade constante, nunca para
- **Segmentos:** Cada anel range com fase offset (som de metal), balançam com spring
- **Cabeça:** Gira 360° lentamente, o olho sempre no jogador
- **Pinças:** Abrem e fecham num ritmo, mais rápido quando agitado
- **Dano:** Quando acertada, solta faíscas (sparks metálicos, não sangue)

### Personalidade

**Máquina sem propósito.** Não sente dor. Não reage a dano — só continua. Não tem fase de raiva. O medo vem do fato que ela NÃO MUDA EXPRESSÃO (porque não tem). A única indicação de fase é a velocidade e os padrões. Isso a torna mais assustadora.

### Ataques

**Fase 1 (100-60%):** `methodical`
1. **Burrow** — Cava e emerge em outro lugar (já implementado). Telegrafo: mound viajando, 0.8s
2. **Spiral** — Gira o corpo e atira projéteis em espiral dos segmentos. Telegrafo: círculo giratório, 0.7s
3. **Pincha** — Estende as pinças frontais em investida. Telegrafo: pinças abrem, 0.3s (rápido!)

**Transição (60%):** Range mais alto. Peças começam a cair (partículas de ferrugem).

**Fase 2 (60-30%):** `accelerating`
- Mantém Burrow + Spiral
- Adiciona **Shrapnel Burst** — Segmentos disparam estilhaços em 360°. Telegrafo: anéis nos segmentos, 0.5s
- Speed 1.4x. Perde 2 segmentos (fica mais curta, mais rápida)

**Transição (30%):** Perde mais 2 segmentos. Fumaça preta. Movimento errático.

**Fase 3 (<30%):** `broken`
- Só 8 segmentos. Movimento caótico (zigue-zague)
- Mantém Shrapnel Burst. Adiciona **Death Roll** — Gira sem parar, atirando projéteis em TODAS direções
- Speed 2.0x. Fica mais perigosa conforme quebra

### Mecânica Única: Degradação

Quanto mais dano, menos segmentos. Cada segmento perdido = mais velocidade, menos previsibilidade. Mas menos segmentos = menos área de hitbox. Jogador decide: foco em matar rápido (chefe fica caótico) ou dano controlado (mantém previsível)?

---

## 3. KRAKEN-MOR — O Abraço do Abismo

**Aparição:** Onda 10
**Corpo:** Octopus (plan='tentacle'), escala 2.5x

### Aparência

Manto pulsante de 5 braços, preto-roxo com bioluminescência azul nas ventosas. Olho único no centro do manto, branco leitoso. Brilho pulsante que acelera quando agitado. Cada braço tem espinhos retráteis.

### Animação Procedural

- **Manto:** Pulso constante (sine wave no scale, frequência = 2Hz, amplitude = 0.05). Acelera com agitação
- **Braços:** Cadeias de juntas com onda viajante + spring trailing. Cada braço tem fase diferente para parecer independente
- **Bioluminescência:** Pulsa em onda que vai do centro às pontas dos braços
- **Olho:** Dilata conforme agitação. Fase 3: olho fica vermelho
- **Swirl:** Quando parado, braços fazem movimento de redemoinho lento

### Personalidade

**Paciente.** Fica parado no centro, braços ondulando. Parece meditar. Fase 1: quase sonolento. Fase 2: desperta, braços ficam mais ativos. Fase 3: frenético, braços chicoteiam.

### Ataques

**Fase 1 (100-66%):** `dormant`
1. **Tentacle Swipe** — Um braço varre em arco. Telegrafo: braço levanta, glow azul, 0.5s
2. **Spit Burst** — Cospe 6 projéteis em leque da boca. Telegrafo: glow na boca, 0.4s
3. **Grapple** — (já implementado) Braço estica, puxa jogador. Telegrafo: braço converge, 0.6s

**Transição 1 (66%):** Glow azul → roxo. Braços começam a se mover mais. Olho abre mais.

**Fase 2 (66-33%):** `awakened`
- Mantém todos os padrões
- Adiciona **Arms Rain** — Braços batem no chão em áreas marcadas. Telegrafo: círculos roxos no chão, 0.6s
- 2 braços atacam simultaneamente

**Transição 2 (33%):** Glow roxo → vermelho. Olho totalmente aberto. Manto pulsa rápido.

**Fase 3 (<33%):** `frenzied`
- Mantém Arms Rain + Grapple
- Adiciona **Constrict** — Braços cercam jogador e fecham. Telegrafo: círculo de glow vermelho diminuindo, 0.8s
- TODOS os braços atacam. Espaço seguro diminui

### Mecânica Única: Braços Destrutíveis

Cada braço tem HP próprio. Destruir um braço reduz os ataques do Kraken, mas na transição de fase ele regenera todos os braços com mais HP. Jogador decide: focar no manto (dano no chefe) ou nos braços (sobrevivência)?

---

## 4. TERROR ALADO — A Praga dos Céus

**Aparição:** Onda 8
**Corpo:** Novo — Vespid (plan='winged'), corpo pequeno com asas grandes

### Aparência

Corpo alongado como o de uma vespa, mas com 4 asas translúcidas que vibram. Exoesqueleto preto-e-amarelo. Ferrão longo na cauda que goteja veneno. Olhos compostos vermelhos. Asas têm nervuras que brilham em tom amarelo.

### Animação Procedural

- **Voo:** Flutua no ar (collision._samples pula voadores — já implementado). Movimento suave com steering
- **Asas:** Batem em frequência variável (12-20Hz). Spring-damper na posição de cada asa para wobble natural
- **Ferrão:** Aponta na direção do movimento + offset para baixo
- **Pouso:** Pousa no chão para alguns ataques, asas fecham, depois decola
- **Morte:** Cai no chão, asas batem fracamente, param

### Personalidade

**Sádica.** Gosta de ver o jogador correr. Persegue por cima, ataca de cima. Fase 2: começa a mirar onde você VAI (lead). Fase 3: frenética, não para.

### Ataques

**Fase 1 (100-60%):** `hunter`
1. **Sting Dive** — Mergulha com ferrão. Telegrafo: glow no ferrão, 0.4s
2. **Venom Spray** — Cospe veneno em leque. Telegrafo: glow verde na boca, 0.5s. Deixa poças no chão
3. **Wing Gust** — Bate asas, empurra jogador para longe. Telegrafo: asas abrem, 0.3s

**Transição (60%):** Asas brilham mais. Zumbido aumenta.

**Fase 2 (60-30%):** `stalker`
- Mantém Sting Dive + Venom Spray
- Adiciona **Aimed Barrage** — Rajada de projéteis com lead (mira onde jogador VAI). Telegrafo: laser sight no chão, 0.5s
- Voo mais rápido, padrões mais precisos

**Transição (30%):** Glow amarelo → laranja. Asas vibram no limite.

**Fase 3 (<30%):** `desperate`
- Mantém tudo. Adiciona **Rain of Stings** — Múltiplos mergulhos em sequência
- Nunca pousa. Speed máximo. Ataques contínuos

### Mecânica Única: Altitude

Terror Alado tem altitude que afeta seus ataques. Alta (padrão): ataca de cima, fácil de desviar. Baixa (após mergulho): vulnerável por 1s, mas ataca mais rápido. Jogador pode "baitar" o mergulho para janela de dano.

---

## 5. OLHO-SÍSMICO — O Observador

**Aparição:** Onda 12
**Corpo:** Novo — Eye (plan='orbital'), corpo esférico com múltiplos tentáculos finos

### Aparência

Globo ocular gigante flutuante, íris vertical de gato. Pupila se dilata e contrai. Cercado por 6 tentáculos finos que terminam em pontas ósseas. O olho pisca em intervalos irregulares. Veias pulsantes na superfície.

### Animação Procedural

- **Flutuação:** Corpo sobe e desce (sine wave, amplitude 8px, 1.5Hz). Os tentáculos ondulam em torno
- **Íris:** Segue o jogador com spring (atraso). Quando o jogador dasha, a íris "tenta" acompanhar
- **Piscada:** Pisca a cada 2-5s (aleatório). Animação: uma membrana desce e sobe (0.1s)
- **Veias:** Pulsam sync com o heartbeat do chefe (mais rápido quando agitado)
- **Tentáculos:** Onda viajante + spring. Na chuva de projéteis, os tentáculos "apontam" para direções específicas

### Personalidade

**Observador calmo.** Não se move do lugar. Só observa. Fase 1: pisca lentamente, quase entediado. Fase 2: pisca mais rápido, íris mais aberta. Fase 3: olho arregalado, veias saltadas, pisca constantemente.

### Ataques

**Fase 1 (100-66%):** `watching`
1. **Gaze** — Laser contínuo da íris, varre lentamente. Telegrafo: íris brilha 0.6s
2. **Tentacle Swipe** — Tentáculo varre em arco. Telegrafo: tentáculo levanta, 0.4s
3. **Spawn Orb** — Spawna 3 orbes que flutuam e atiram projéteis. Telegrafo: glow nos tentáculos, 0.7s

**Transição 1 (66%):** Veias começam a pulsar. Íris se dilata.

**Fase 2 (66-33%):** `scanning`
- Mantém Gaze + Spawn Orb
- Adiciona **Siesmic Pulse** — Onda de choque que se expande em todas direções. Telegrafo: anel no centro, 0.6s
- Gaze varre mais rápido

**Transição 2 (33%):** Olho arregalado. Veias vermelhas. Pisca sem parar.

**Fase 3 (<33%):** `panicked`
- Mantém Siesmic Pulse
- Adiciona **Bullet Hell** — Projéteis em todas direções continuamente + Gaze simultâneo
- Múltiplos orbes. Arena fica caótica

### Mecânica Única: O Olho

Não atirar no olho quando ele está piscando causa dano reduzido (75% menos). Acertar o olho ABERTO dá crítico garantido. Mas a piscada é aleatória e dura só 0.1s — timing é tudo.

---

## 6. MÃE-ESCARAVELHO — A Colmeia

**Aparição:** Onda 9
**Corpo:** Spider (plan='radial', 8 pernas), escala 2.2x

### Aparência

Escaravelho gigante com carapaça marrom-escura rachada, por onde vaza um brilho âmbar. 8 pernas grossas e espinhosas. Abdômen inchado que pulsa — de lá nascem os filhotes. Mandíbulas que se mexem constantemente. Antenas que farejam o ar.

### Animação Procedural

- **Marcha:** 8 pernas em onda metacronal (2 ondas, 4 pernas cada). Passo pesado, shake no chão
- **Antenas:** Spring-damper (stiffness=6, damping=0.7). Sempre farejando em direção ao jogador
- **Abdômen:** Pulsa a cada spawn de filhote. Fica murcho após spawn, incha gradualmente
- **Carapaça:** Rachaduras se abrem conforme toma dano, brilho âmbar mais intenso
- **Mandíbulas:** Ritmo constante de mastigação. Acelera quando agitada

### Personalidade

**Mãe protetora.** Prioriza spawnar filhotes acima de atacar. Se filhotes morrem, ela "chora" (solta glow triste) e fica mais agressiva. Fase 2: desesperada, spawna filhotes mais fortes. Fase 3: sacrifício — explode em filhotes ao morrer.

### Ataques

**Fase 1 (100-66%):** `brooding`
1. **Spawn Grubs** — Invoca 3 larvas que rastejam e mordem. Telegrafo: abdômen pulsa, 0.5s
2. **Acid Spit** — Cospe ácido em arco. Telegrafo: glow verde na boca, 0.4s. Deixa poça
3. **Leg Stomp** — Levanta 2 pernas e bate no chão. Telegrafo: pernas levantam, 0.5s. Onda de choque

**Transição 1 (66%):** Carapaça racha mais. Brilho âmbar vaza.

**Fase 2 (66-33%):** `defensive`
- Mantém Acid Spit + Leg Stomp
- Adiciona **Spawn Soldiers** — Invoca 2 escaravelhos soldados (mais HP, atiram projéteis)
- Adiciona **Web Trap** — Teia no chão que prende jogador. Telegrafo: círculo branco no chão, 0.5s

**Transição 2 (33%):** Carapaça quase toda aberta. Glow forte.

**Fase 3 (<33%):** `sacrificial`
- Mantém Spawn Soldiers + Web Trap
- Adiciona **Enrage** — Bônus de dano e velocidade. Carapaça brilha intensamente
- Ao morrer: **explode** em 6 larvas.

### Mecânica Única: Enxame

Mãe-Escaravelho é suport, não tank. Ela NÃO ataca diretamente na maioria do tempo — quem ataca são os filhotes. Matar ela rápido é a estratégia, mas os filhotes protegem. Se ignorar os filhotes, o enxame cresce. Jogador decide: foco nela (ignora adds) ou limpa enxame (luta longa)?

---

## 7. ARANHA-REI — A Tecedeira

**Aparição:** Onda 11
**Corpo:** Spider (plan='radial'), escala 2.0x, pernas mais longas

### Aparência

Aranha pálida, quase albina, com 8 pernas finas e longas que parecem dedos. Olhos pequenos e pretos (8 deles). Corpo pequeno comparado às pernas. Tece teias que brilham no escuro. Movimento nervoso, espasmódico.

### Animação Procedural

- **Marcha:** Pernas longas em marcha diagonal + levantamento extra (parece que está andando sobre os ovos). Movimento rápido e nervoso
- **Teias:** Fios de teia visíveis (draw_line) que conectam pontos da arena. Balançam com wind
- **Olhos:** 8 olhos seguem o jogador independentemente (cada um com spring próprio para atraso diferente) — efeito perturbador
- **Pernas:** Spring stiffness baixo (6) = pernas "moles", parecem frágeis. Quando ataca, pernas ficam rígidas
- **Idle:** Balança para os lados como se estivesse calculando o próximo movimento

### Personalidade

**Nervosa.** Não para quieta. Corre de um lado pro outro. Fica imóvel por 0.5s e dispara. Parece ter TDAH. Fase 2: mais frenética, movimentos mais largos. Fase 3: descontrolada, pula sem parar.

### Ataques

**Fase 1 (100-60%):** `twitchy`
1. **Web Shot** — Atira teia que prende jogador (slow). Telegrafo: glow branco no abdômen, 0.3s
2. **Leap** — Pula na direção do jogador. Telegrafo: agacha 0.2s (muito rápido)
3. **Spiderling Spawn** — Invoca 4 aranhas pequenas. Telegrafo: abdômen pulsa, 0.4s

**Transição (60%):** Olhos brilham. Pernas tremem.

**Fase 2 (60-30%):** `agitated`
- Mantém Web Shot + Spiderling
- Adiciona **Web Dome** — Cria um domo de teia que encolhe o espaço seguro. Telegrafo: fios de teia crescendo, 0.8s
- Adiciona **Poison Bite** — Mordida com veneno. Telegrafo: glow verde nas mandíbulas, 0.3s

**Transição (30%):** Olhos vermelhos. Movimentos imprevisíveis.

**Fase 3 (<30%):** `frenzied`
- Mantém Web Dome + Poison Bite
- Adiciona **Spider Rain** — Pula no teto (fora da tela) e chove aranhas. Telegrafo: sombra no teto, 0.6s
- Speed 2.0x. Nunca para

### Mecânica Única: Teia Persistente

Teias não somem. Cada teia colocada reduz o espaço da arena permanentemente. Na fase 3, se o jogador não moveu o chefe para longe das teias, a arena fica minúscula. Jogador precisa "convidar" a aranha para tecer em lugares menos críticos.

---

## 8. SERPENTE DE CRISTAL — A Fractal

**Aparição:** Onda 13
**Corpo:** Centipede (plan='segmented'), mas segmentos são cristais

### Aparência

Serpente feita de 10 segmentos de cristal translúcido. Cada segmento é um prisma de cor diferente (arco-íris). A luz passa através dela e cria refrações no chão. Não tem olhos — a cabeça é uma ponta de cristal afiada. Flutua acima do chão.

### Animação Procedural

- **Flutuação:** Corpo inteiro ondula no ar (spline + wave). Não toca o chão
- **Cristais:** Cada segmento rotaciona lentamente (fase offset). A refração no chão (desenho de luz projetada) acompanha
- **Refração:** Rastro de luz no chão que muda de cor conforme segmento. Party visual
- **Impacto:** Quando acertada, som de vidro quebrando. Partículas de cristal
- **Morte:** Explode em 10 cristais que caem no chão e brilham por 2s antes de sumir

### Personalidade

**Elegante, alienígena.** Não demonstra emoção — não tem rosto. Se move como uma fita ao vento. Os ataques são frios, calculados, geométricos. Não acelera — fica mais precisa.

### Ataques

**Fase 1 (100-66%):** `geometric`
1. **Prism Laser** — Laser que refrata em ângulos retos. Telegrafo: linha que mostra o caminho do laser, 0.6s
2. **Crystal Shard** — Atira 3 estilhaços em leque. Telegrafo: glow no segmento, 0.4s
3. **Reflection** — Cria um espelho de cristal que reflete projéteis do jogador de volta. Telegrafo: cristal crescendo no chão, 0.5s

**Transição 1 (66%):** Rotação dos cristais acelera. Refração fica mais intensa.

**Fase 2 (66-33%):** `crystalline`
- Mantém Prism Laser + Crystal Shard
- Adiciona **Fractal Burst** — Projéteis que se dividem em 2 ao meio caminho. Telegrafo: projétil com glow pulsando, 0.5s
- 2 lasers simultâneos

**Transição 2 (33%):** Todos os cristais brilham no máximo.

**Fase 3 (<33%):** `prismatic`
- Mantém Fractal Burst + Reflection
- Adiciona **Prism Dance** — Múltiplos lasers que refratam pela arena, criando grade de luz.
- Speed 1.0x (não acelera) — mas padrões são mais densos

### Mecânica Única: Refração

Projéteis do jogador que ACERTAM um segmento de cristal são refratados em 2 tiros menores em ângulos diferentes. Pode acertar a própria Serpente de novo (dano extra) ou errar completamente. Jogador decide ângulo de ataque.

---

## 9. A MURALHA — O Portão

**Aparição:** Onda 15
**Corpo:** Novo — Wall (plan='fixed'), estrutura fixa que ocupa um lado da arena

### Aparência

Parede de carne e pedra que ocupa o lado direito da tela. Uma boca enorme no centro, com dentes de stalactite. Múltiplos olhos pequenos espalhados pela superfície que piscam independentemente. Veias pulsantes. Mãos de pedra nas laterais.

### Animação Procedural

- **Boca:** Abre e fecha (sine wave, 0.5-3Hz). Antes de ataque de breath, abre totalmente
- **Olhos:** Cada olho abre/fecha independente (parece que a parede está VIGIANDO). Onde o jogador está, os olhos mais próximos se abrem
- **Veias:** Pulsam da boca para as bordas. Aceleram conforme dano
- **Mãos:** Emergem das laterais para bater. Spring-damper na posição
- **Dano:** Pequenos pedaços de pedra caem. Rachaduras aparecem na superfície

### Personalidade

**Implacável.** Você não vai passar. A arena foi feita para você morrer aqui. Não tem piedade. Fase 2: mais olhos abrem, mais ataques. Fase 3: TUDO ao mesmo tempo.

### Arena

Sala horizontal estreita (700px largura × 500px altura). Muralha no lado DIREITO. Fogo no chão da esquerda que empurra o jogador para a direita (em direção ao chefe). Jogador preso entre o fogo e a Muralha.

### Ataques

**Fase 1 (100-66%):** `gatekeeper`
1. **Fire Breath** — Sopro de fogo que cobre a metade da arena. Telegrafo: boca abre, glow vermelho, 0.6s
2. **Hand Slam** — Mão emerge e bate. Telegrafo: glow na lateral, 0.4s
3. **Eye Laser** — 3 olhos atiram laser simultaneamente. Telegrafo: olhos brilham, 0.5s

**Transição 1 (66%):** Mais olhos abrem. Veias pulsam mais forte.

**Fase 2 (66-33%):** `warden`
- Mantém Fire Breath + Hand Slam
- Adiciona **Bouncing Bullets** — Projéteis que ricocheteiam nas paredes. Telegrafo: glow amarelo na boca, 0.4s
- Fire Breath mais frequente. Fogo no chão avança mais

**Transição 2 (33%):** Rachaduras na superfície. Glow vermelho.

**Fase 3 (<33%):** `judgment`
- Mantém Bouncing Bullets + Eye Laser
- Adiciona **Grid of Fire** — Grade de fogo no chão com brechas pequenas.
- Fire Breath+Hand Slam simultâneos. Mínimo espaço seguro

### Mecânica Única: A Parede

A Muralha NÃO pode ser flanqueada. Ela ocupa um lado da tela. Você só pode atirar na boca (crítico) ou nos olhos (dano normal). A boca fecha quando você está muito perto (proteção). Distância ideal: médio alcance.

---

## 10. ANKH — A Eterna

**Aparição:** Onda 18
**Corpo:** Lizard (plan='standard'), escala 2.0x, espectro/sombra

### Aparência

Lagarto translúcido, feito de sombra e brilho dourado. O corpo é uma silhueta preta com bordas douradas pulsantes. Olhos são dois pontos de luz dourada. Caveira de lagarto como máscara. Rastro de partículas douradas. Ela não anda — desliza.

### Animação Procedural

- **Deslizamento:** Flutua 10px acima do chão. Não tem marcha — desliza como fantasma
- **Partículas:** Rastro dourado que fica por 2s. Cada movimento deixa um traço
- **Máscara:** Caveira que chacoalha com spring nos movimentos bruscos
- **Dissolução:** Quando "morre" em uma fase, o corpo se desfaz em partículas douradas e se reforma
- **Glow:** Pulsa no ritmo do heartbeat. Mais rápido conforme dano

### Personalidade

**Antiga.** Não fala. Não reage. Você não é o primeiro a enfrentá-la. Ela já viu tudo. Sua calma é o que a torna aterrorizante. Cada fase é uma "memória" — ela revive uma forma anterior.

### Fases Únicas

Cada fase é um estilo de luta completamente diferente (ANKH é a exceção à regra dos 2 — ela é especial).

**Fase 1 — O Caçador (100-75%):** Forma de lagarto ágil.
- Padrões: Charge, Leap, Tail Sweep
- Veloz, corpo-a-corpo. Testing: reflexo

**Transição:** Corpo desfaz, reforma em forma maior.

**Fase 2 — O Tanque (75-50%):** Forma grande, placas ósseas.
- Padrões: Radial Burst, Shockwave, Summon Specters
- Lento, ranged. Testing: posicionamento

**Transição:** Corpo desfaz, reforma em forma fluída.

**Fase 3 — O Tentáculo (50-25%):** Forma de Kraken espectral.
- Padrões: Grapple, Arms Rain, Laser Sweep
- Controle de área. Testing: mobilidade

**Transição:** Corpo desfaz, reforma em forma final.

**Fase 4 — A Eterna (<25%):** Forma original, lagarto dourado.
- TODOS os padrões das fases anteriores misturados
- Bullet hell. Testing: TUDO

### Mecânica Única: Memórias

ANKH revive ataques de chefes anteriores que o jogador já enfrentou. Ela "aprendeu" com cada morte. Jogador reconhece os padrões, mas combinados de formas novas.

---

## 11. PRIMORDIAL — O Primeiro Lagarto

**Aparição:** Onda 20 (chefe final em NORMAL), ~2x vida extra
**Corpo:** Lizard (plan='standard'), escala 4.0x

### Aparência

Lagarto monstruoso, 4x o tamanho normal. Corpo coberto de espinhos, placas, chifres e membranas — TODAS as partes do jogo ao mesmo tempo. Cauda com clava + ferrão. Asas membranosas que se abrem na fase 2. Carapaça rachada que brilha magma. 4 olhos (2 normais + 2 menores abaixo). O corpo pulsa com glow vermelho-laranja como lava.

É o que um lagarto se torna se evoluir além do limite.

### Animação Procedural

- **Marcha:** 8 pernas (4 pares) em onda metacronal. Cada passo = shake grande
- **Cauda:** Dupla (clava + ferrão). Cada uma com spring independente
- **Asas:** Fechadas nas costas (fase 1). Abrem na fase 2 (membrana estica entre os espinhos)
- **Carapaça:** Rachaduras brilham sync com ataques. Cada ataque = flash na rachadura correspondente
- **Olhos:** 4 olhos seguem jogador independentemente. 2 normais (foco) + 2 abaixo (visão periférica)
- **Respiração:** Inspiração DENTRO do ataque (o tell É a respiração)

### Personalidade

**Deus primitivo.** Não se importa com você. Você é um inseto. O rugido inicial não é ameaça — é indiferença. Só na fase 3 ele "nota" você (olhos focam, glow muda). Aí é tarde.

### Fases

**Fase 1 (100-66%):** `primordial`
- Movimento lento, padrões simples mas de escala massiva
- **Massive Fan** — 12 projéteis em leque (2x tamanho normal)
- **Tail Slam** — Cauda-clava bate no chão, 3 ondas de choque concêntricas
- **Wing Buffet** — Empurrão de vento + projéteis (se got wings, não ainda)
- Telegrafos são GRANDES e lentos (0.8s+)

**Transição 1 (66%):** Rugido tectônico (shake na tela 0.5s). Asas se abrem. Glow aumenta.

**Fase 2 (66-33%):** `ancient`
- Movimento mais rápido. Asas permitem pequenos voos
- **Sky Slam** — Sobe e cai na posição do jogador (sombra ENORME)
- **Magma Spit** — Cospe magma que deixa poça grande e persistente
- **Wing Storm** — Asas criam vento que empurra para as poças
- **Summon Echoes** — Invoca espectros de chefes anteriores (versões fracas)

**Transição 2 (33%):** Olhos focam em você. Glow vermelho intenso.

**Fase 3 (<33%):** `apocalypse`
- TUDO ao mesmo tempo
- **Apocalypse** — Projéteis em TODAS direções continuamente + ataques normais
- **Rage** — Speed 2.0x, cooldown 0.5x
- Arena fica gradualmente coberta de fogo/magma (jogador tem menos espaço)
- Se você chegar aqui, você merece vencer

---

## Resumo: Distribuição dos Chefes

| # | Nome | Onda | Corpo | Mecânica Única | Inspiração |
|---|------|------|-------|----------------|------------|
| 1 | Rei Lagarto | 5 | Lizard | Cicatriz no chão | Gatling Gull |
| 2 | Centopeiadeira | 7 | Centipede | Degradação (perde segmentos) | Ammoconda / Larry Jr |
| 3 | Kraken-Mor | 10 | Octopus | Braços destrutíveis | Beholster |
| 4 | Terror Alado | 8 | Wasp (novo) | Altitude (vulnerabilidade) | The Haunt |
| 5 | Olho-Sísmico | 12 | Eye (novo) | Crítico no olho aberto | Peep / Beholster |
| 6 | Mãe-Escaravelho | 9 | Spider | Suport (adds são o perigo) | Duke of Flies |
| 7 | Aranha-Rei | 11 | Spider (longa) | Teia persistente (reduz arena) | The Bloat / Mine Flayer |
| 8 | Serpente Cristal | 13 | Crystal (novo) | Refração de projéteis | Isaac / Hush |
| 9 | Muralha | 15 | Wall (novo) | Parede fixa + fogo empurra | Wallmonger |
| 10 | ANKH | 18 | Spectral Lizard | 4 fases, revive ataques de outros | Isaac / The Lich |
| 11 | PRIMORDIAL | 20 | Lizard 4x | Todas as partes, todas as fases | Hush / Delirium |

### Novos Corpos a Implementar

| Plan | Descrição |
|------|-----------|
| `winged` | Corpo com asas, voador (collision skip). Asas com spring. Ferrão. |
| `orbital` | Corpo esférico flutuante. Tentáculos finos com spring. Olho grande. |
| `wall` | Estrutura fixa que ocupa um lado. Boca, olhos, mãos. Sem locomoção. |
| `crystal` | Centipede modificado com segmentos de cristal. Flutua. Refração. |

---

## Config Dials (para `config.py`)

```python
# Boss general
BOSS_SCALE = 2.3
BOSS_INTRO_TIME = 1.0
BOSS_TRANSITION_TIME = 0.8
BOSS_INTRO_INVULN = True

# Boss mood
BOSS_FRUSTRATION_THRESHOLD = 5  # seconds without hitting player
BOSS_CORNERED_DIST = 120

# Per-boss HP pools
BOSS_HP = {
    'king': 800,
    'centipede': 700,
    'kraken': 1200,
    'terror': 600,
    'eye': 900,
    'beetle': 750,
    'spider': 650,
    'crystal': 850,
    'wall': 1500,
    'ankh': 2000,
    'primordial': 4000,
}
```
