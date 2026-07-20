# Pixel art dos personagens (NAO usado pelo jogo)

Gerado com a skill `pixel-art-gen`: `mkicons.py` define cada sprite como um mapa
ASCII 16x16 e emite o JSON que o script da skill renderiza.

**Estes PNGs nao entram no jogo.** A tela de selecao mostra um **render vivo** da
criatura procedural (`menu._char_previews`), que e mais honesto: voce ve o corpo
que vai controlar, animado, em vez de uma ilustracao dele. E o jogo continua sem
nenhum arquivo de asset, como o CLAUDE.md descreve.

Ficam aqui porque sao o ponto de partida obvio caso a Fase 7 (arte PNG) queira
icones de personagem em tamanhos pequenos, onde um render vivo nao funciona.

Regerar:
```bash
python tools/pixelart/mkicons.py saida/
python .claude/skills/pixel-art-gen/scripts/render_pixel_art.py saida/char_lagarto.json -o saida/char_lagarto.png -p 16
```
