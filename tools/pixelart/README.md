# Pixel art (assets PNG — Fase 7, ainda NAO ligados ao jogo)

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

Regerar (renderiza ao lado do script):
```bash
python tools/pixelart/batch2.py    # coin/health/cuspe/tent
python tools/pixelart/batch3.py    # 7 armas restantes
python tools/pixelart/batch4.py    # 8 stat icons (1a passada)
python tools/pixelart/batch4b.py   # refinamento de might + dash
python tools/pixelart/batch5.py    # pickups (fruta/ovo/inseto)
```

## v1 — `mkicons.py` (personagens 16x16, legado)
Mapas ASCII 16x16 dos 4 personagens. **Nao entram no jogo**: a selecao mostra um
render vivo da criatura procedural (`menu._char_previews`), mais honesto. Ficam como
ponto de partida se quisermos icones de personagem pequenos.

## Importante
**Nenhum destes PNGs e carregado pelo jogo ainda** — em runtime o jogo continua
zero-asset (CLAUDE.md). Ligar e a tarefa da Fase 7: `lagarto/assets.py`
(`resource_path`/`_MEIPASS`, lazy, `.convert_alpha()` so apos `display.init`,
fallback `icons.draw`) + `build.py --add-data`.
