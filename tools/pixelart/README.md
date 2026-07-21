# Pixel art (assets PNG — Fase 7, LIGADOS via `lagarto/assets.py`)

Gerado com a skill `pixel-art-gen` (Pillow). Ha dois geradores:

## v2 — `pxgen.py` + `batch2.py` / `batch3.py`  (o atual)
`pxgen.py` e a camada de autoria: cada forma e uma **mascara de cobertura**
(predicado super-amostrado 4x4), pintada com uma **rampa de 4 tons**
(highlight/base/shade/edge) com **anti-aliasing manual** na borda curva, contorno
**sel-out** (tom escuro do fill, nao preto) e sombreamento esferico (luz no topo-
esquerda). Curvas organicas. Guias: Pixel Parmesan (AA), Lospec/Pixnote (outlines).

Saida em `assets/`:
- `assets/icons/` — 32x32: as 8 armas (`cuspe ferrao teia esporos feromonio sopro
  enxame acido`) + `coin_pollen`, `health` + 8 mutacoes de stat (`speed energy
  might xp area haste amount dash`) — estas ultimas escolhidas por serem as que
  **colidem de forma** no `icons.py` atual (`_bolt` serve speed/energy/might,
  `dash`/`ferrao` dividem `_arrow`). **Ids batem com `lagarto/icons.py`** — quando
  a Fase 7 ligar via `lagarto/assets.py`, o fallback `icons.draw` cobre qualquer
  id sem PNG.
- `assets/props/` — 80x80: `tent_beetle` (a loja do besouro).
- `assets/icons/` — 24x24: `pickup_fruit pickup_egg pickup_bug` (coletaveis do
  mundo, ids proprios — `pickups.py` ainda desenha em codigo, sem dispatch por id).
- `assets/icons/` — 32x32: 9 charms (`antenas presas olhos carapaca espinhos asas
  glandula nectar clava`). `glandula`/`nectar` dividiam o mesmo desenhador `_sac`
  no `icons.py` — aqui saem visualmente distintos (glandula = cacho verde de
  esporos, nectar = gota ambar unica).

**Colisao de id conhecida, NAO resolvida em arte:** o charm de cauda `ferrao`
("rabada envenena") usa o **mesmo id** que a arma `Ferrão Teleguiado` no dict de
`icons.py` — as duas sao `id='ferrao'`. Ja existe `assets/icons/ferrao.png` (lote 3,
desenhado para a ARMA). Gerar um segundo PNG pro charm exigiria ids separados no
codigo (`icons.py`/`charms.py`) antes — **nao gerado** de proposito, pra nao ligar
o PNG errado num dos dois usos quando a Fase 7 acoplar.

Regerar (renderiza ao lado do script):
```bash
python tools/pixelart/batch2.py    # coin/health/cuspe/tent
python tools/pixelart/batch3.py    # 7 armas restantes
python tools/pixelart/batch4.py    # 8 stat icons (1a passada)
python tools/pixelart/batch4b.py   # refinamento de might + dash
python tools/pixelart/batch5.py    # pickups (fruta/ovo/inseto)
python tools/pixelart/batch6.py    # 9 charms
```

## v1 — `mkicons.py` (personagens 16x16, legado)
Mapas ASCII 16x16 dos 4 personagens. **Nao entram no jogo**: a selecao mostra um
render vivo da criatura procedural (`menu._char_previews`), mais honesto. Ficam como
ponto de partida se quisermos icones de personagem pequenos.

## Ligado ao jogo (`lagarto/assets.py`)

`icons.draw(surf, key, center, radius, color, glow)` tenta `assets.icon(key,
radius*2)` primeiro: carrega o PNG **preguicosamente** (`resource_path` ciente de
`sys._MEIPASS` p/ build do PyInstaller, senao raiz do repo), `.convert_alpha()`
**so na 1a chamada** (ja depois de `display.init`, nunca no import) e escala com
`smoothscale` pro diametro pedido, cacheado por `(key, diametro)` (teto 300,
`clear()` ao estourar — mesmo padrao do `palette._GLOW_CACHE`). Se nao existir
PNG pro id, devolve `None` e `icons.draw` cai no desenhador procedural de sempre
— **nunca quebra pra id novo**, e uma build sem `assets/` (stripped) roda igual.

**Por que bakear cor fixa no PNG e seguro:** todo call site de `icons.draw` passa
a MESMA cor pro mesmo id sempre (o hue proprio da arma/mutacao/charm — `w.color`,
`card.color`, `ch.color` — nunca varia por instancia/frame). Confirmado por grep
nos 6 call sites (`game.py`x5, `menu.py`x2) antes de ligar.

**Verificado em runtime real** (nao so isolado): screenshot do HUD (chips de
arma equipada) e de uma carta de EVOLUIR mostrando `xp.png` (estrela do lote 4)
dentro da carta de verdade, com glow/escala/centralizacao corretos; ids sem PNG
(`venom`, `wings`) caem no procedural na mesma tela, sem diferenca visual de
qualidade. `--smoke 600` verde.

## Ainda faltando (Fase 7)
- `assets/props/tent_beetle.png` **nao esta ligado** ao desenho da tenda
  (`game._draw_camp_pois` continua 100% procedural, com a animacao de queda do
  ceu) — trocar exigiria integrar o PNG com o sistema de drop-in/sombra/glow,
  mais invasivo, nao feito ainda.
- `build.py --add-data` p/ empacotar `assets/` no executavel do PyInstaller.
- Nitidez: pre-escala NEAREST por fator inteiro antes do `present()` borrar
  (hoje `assets.icon` usa `smoothscale`, correto p/ escala arbitraria mas
  suaviza um pouco a 2x/3x — aceito por ora, mesmo trade-off do resto da UI).
