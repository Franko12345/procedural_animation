# Outline via Mask (pygame.mask)

## Problema

Outline hoje só no corpo (`outline_smooth()` via polígono). Pernas, língua e algumas partes não têm outline — visual inconsistente, especialmente após pixelização.

## Técnica (DaFluffyPotato — "Outlines in Pygame")

```python
mask = pygame.mask.from_surface(surface, threshold=127)
outline_points = mask.outline(every=1)  # lista de (x, y) da borda
# Desenhar linhas entre pontos consecutivos
for i in range(len(outline_points)):
    pygame.draw.line(target_surf, color, outline_points[i-1], outline_points[i])
```

`mask.outline()` já devolve pontos em ordem conectada para o primeiro componente conexo. Zero math de borda.

## Aplicação no Lagarto

### Onde aplicar (alvo inicial)
- **Pernas** (`leg.py`): cada perna renderizada numa surface pequena → mask outline → blitar no lugar
- **Língua** (`lizard.py` `_draw_tongue`): mesmo esquema, surface pequena
- **Partes do corpo futuras** (asas, antenas, barbatanas) se não tiverem outline poligonal próprio

### Onde NÃO aplicar
- **Corpo**: já tem `outline_smooth()` por polígono vetorial — mais eficiente (sem surface intermediária), continuar usando

### Custo esperado
- Cada perna/língua é pequena (20-40px). `mask.from_surface` + `outline()` + draw lines numa surface de ~40×40 = fração de microssegundo
- Criaturas típicas têm 4-6 pernas + 1 língua → ~7 chamadas por criatura
- 20 criaturas → ~140 chamadas → <0.1ms estimado (medir)

### Implementação

```python
# utils.py ou novo outline_utils.py
def outline_from_surf(surf, color, thickness=1):
    """Retorna surface com outline de `surf`."""
    mask = pygame.mask.from_surface(surf)
    if not mask.count():
        return surf
    pts = mask.outline()
    # Surface do tamanho da original + borda
    margin = thickness + 1
    w, h = surf.get_size()
    out = pygame.Surface((w + margin*2, h + margin*2), pygame.SRCALPHA)
    offset = (margin, margin)
    for i in range(len(pts)):
        a = (pts[i-1][0] + margin, pts[i-1][1] + margin)
        b = (pts[i][0] + margin, pts[i][1] + margin)
        pygame.draw.line(out, color, a, b, thickness)
    out.blit(surf, offset)
    return out
```

Uso em `leg.py`:
```python
# Em vez de blitar perna direto:
# blit(surf, pos) → blit(outline_from_surf(surf, BLACK), pos)
```

Uso em `lizard.py._draw_tongue`:
```python
surf = render_tongue(...)  # já existente
blit(outline_from_surf(surf, OUTLINE_COLOR), pos)
```

### Ajustes pós-pixelização
Com `C.PIXEL_SCALE=3`, outline de 1px no buffer low-res vira 3px na tela — visível e consistente. Se quiser outline mais fino, desenhar com espessura 1 já resolve.

### Riscos
- **Performance**: se `mask.from_surface` for caro em muitas criaturas, cachear a mask por frame (só recriar se a surface mudou — pernas mudam pouco entre frames)
- **Componentes múltiplos**: `mask.outline()` só pega o primeiro componente. Pernas são conexas → OK. Língua é uma tira fina → OK.
- **Canto afiado**: `mask.outline()` devolve pixel a pixel — linhas retas viram escadinha. No low-res com upscale NEAREST isso é esperado (pixel art retro).

## Comparação com outline poligonal atual

| | Polígono vetorial | Mask |
|---|---|---|
| Corpo | ✅ `outline_smooth()` + Catmull-Rom | ❌ Renderizar corpo inteiro em surface = caro |
| Pernas | ❌ Não existe | ✅ Fácil, surface pequena |
| Língua | ❌ Não existe | ✅ Fácil, surface pequena |
| Consistência | Só corpo | Todas as partes |
| Custo extra | 0 | ~7 masks/criatura |

## Próximo passo
Implementar `outline_from_surf` em `utils.py` ou novo `outline.py`. Aplicar em `leg.py` e `_draw_tongue`. Testar com `--smoke 400` e medir fps.
