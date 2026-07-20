"""Design the four character icons as ASCII maps, emit the pixel-art JSON.

Maps beat hand-typed coordinates: an off-by-one in a 200-entry JSON list is
invisible, but a wrong character in a 16x16 grid you can literally see.

Legend:  . transparent   K ink outline   D dark   B base   L light   W eye
"""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(OUT, exist_ok=True)

PAL = {
    'lagarto':   dict(K='#14121A', D='#20A536', B='#32FF54', L='#8EFFA0', W='#FAFAFF'),
    'vibora':    dict(K='#14121A', D='#8420A5', B='#CC32FF', L='#E28EFF', W='#FAFAFF'),
    'couracado': dict(K='#14121A', D='#A54C20', B='#FF7632', L='#FFB38E', W='#FAFAFF'),
    'larva':     dict(K='#14121A', D='#A5A120', B='#FFF832', L='#FFFB8E', W='#FAFAFF'),
}

# Four legs, long tail, snout to the right: the baseline shape.
LAGARTO = [
    "................",
    "................",
    "................",
    "..........KKKK..",
    ".........KBBBBK.",
    "....KKKKKBLBWBK.",
    "..KKBBBBBBBBBKK.",
    ".KDBBBBBBBBBBBK.",
    "KDBBBBBBBBBBBK..",
    ".KKKKKKKKKKKKK..",
    "...DD..DD..DD.D.",
    "...DD..DD..DD.D.",
    "...KK..KK..KK.K.",
    "................",
    "................",
    "................",
]

# No legs, S-curve, heavy club at the tail: the tail IS the weapon.
VIBORA = [
    "................",
    "..KKKK..........",
    ".KBWBBK.........",
    ".KBBBBKK........",
    "..KKBBBBK.......",
    "....KKBBBK......",
    "......KBBBK.....",
    ".......KBBBK....",
    "........KBBBK...",
    ".......KBBBK....",
    "......KBBBK.....",
    ".....KBBBKKK....",
    "....KBBBBBBBK...",
    "...KBBLBBBBBBK..",
    "...KBBBBBBBBK...",
    "....KKKKKKKK....",
]

# Wide, plated, low to the ground: reads as 'wall' before you read the name.
COURACADO = [
    "................",
    "................",
    "...KKKKKKKKKK...",
    "..KBBBBBBBBBBK..",
    ".KBLBBLBBLBBBBK.",
    ".KBBDBBDBBDBBWK.",
    "KDBBBBBBBBBBBBK.",
    "KDBBBBBBBBBBBK..",
    ".KKKKKKKKKKKK...",
    "..DD..DD..DD....",
    "..DD..DD..DD....",
    "..KK..KK..KK....",
    "................",
    "................",
    "................",
    "................",
]

# Deliberately the smallest of the four: segmented, plump, no legs.
LARVA = [
    "................",
    "................",
    "................",
    ".....KKKKKK.....",
    "...KKBBDBBDBKK..",
    "..KBLBBDBBDBBBK.",
    ".KBBBBBDBBDBBWK.",
    ".KBBBBBDBBDBBBK.",
    "..KBBBBDBBDBBK..",
    "...KKBBDBBDBKK..",
    ".....KKKKKK.....",
    "................",
    "................",
    "................",
    "................",
    "................",
]

SPRITES = [('lagarto', LAGARTO), ('vibora', VIBORA),
           ('couracado', COURACADO), ('larva', LARVA)]


def to_json(name, rows):
    pal = PAL[name]
    px = []
    for y, row in enumerate(rows):
        assert len(row) == 16, f"{name} linha {y} tem {len(row)} colunas"
        for x, ch in enumerate(row):
            if ch == '.':
                continue
            assert ch in pal, f"{name}: caractere '{ch}' desconhecido em {x},{y}"
            px.append({"x": x, "y": y, "color": pal[ch]})
    return {"width": 16, "height": 16, "background": "transparent",
            "grid_lines": False, "pixel_size": 16, "pixels": px}


for name, rows in SPRITES:
    assert len(rows) == 16, f"{name} tem {len(rows)} linhas"
    path = os.path.join(OUT, f'char_{name}.json')
    with open(path, 'w') as f:
        json.dump(to_json(name, rows), f)
    print(f"  {name:10s} {len(to_json(name, rows)['pixels']):3d} pixels -> {path}")
