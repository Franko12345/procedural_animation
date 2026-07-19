"""Charms: Hollow-Knight-style adaptations equipped in 3 body slots.

Slots: head / back / tail (one charm each). Each charm has an ``on_equip`` and a
reversible ``on_unequip`` that tweak Player/Genome fields, plus a **visible part**
(set via genome flags, drawn by ``parts.draw_all``). Charms are a separate layer
from level-up mutations, bought at the camp shop or dropped by nests, and swapped
only at the camp.
"""

from . import palette


class Charm:
    def __init__(self, cid, slot, name, desc, hue, cost, on_equip, on_unequip):
        self.id = cid
        self.slot = slot            # 'head' | 'back' | 'tail'
        self.name = name
        self.desc = desc
        self.hue = hue
        self.cost = cost
        self.color = palette.vibrant(hue, 0.82, 1.0)
        self.on_equip = on_equip
        self.on_unequip = on_unequip


def _c(cid, slot, name, desc, hue, cost, eq, un):
    return Charm(cid, slot, name, desc, hue, cost, eq, un)


# ---- head ----------------------------------------------------------------- #
def _antenas_eq(p): p.tongue_range += 120; p.genome.antennae = True
def _antenas_un(p): p.tongue_range -= 120; p.genome.antennae = False
def _presas_eq(p): p.venom = True; p.genome.fangs = True
def _presas_un(p): p.venom = ('venom' in p.mutations); p.genome.fangs = False
def _olhos_eq(p): p.area_mult *= 1.2; p.genome.extra_eyes += 2
def _olhos_un(p): p.area_mult /= 1.2; p.genome.extra_eyes = max(0, p.genome.extra_eyes - 2)

# ---- back ----------------------------------------------------------------- #
def _carapaca_eq(p): p.armor = min(0.6, p.armor + 0.2); p.genome.plates += 1
def _carapaca_un(p): p.armor = max(0.0, p.armor - 0.2); p.genome.plates = max(0, p.genome.plates - 1)
def _espinhos_eq(p): p.thorns += 2; p.genome.spikes += 1
def _espinhos_un(p): p.thorns = max(0, p.thorns - 2); p.genome.spikes = max(0, p.genome.spikes - 1)
def _asas_eq(p): p.wings = True; p.genome.wings = True; p.max_speed *= 1.1
def _asas_un(p): p.wings = ('wings' in p.mutations); p.genome.wings = False; p.max_speed /= 1.1
def _glandula_eq(p): p.gain_weapon('esporos'); p.genome.spore_sacs = True
def _glandula_un(p): p.genome.spore_sacs = False       # weapon stays; sacs hidden

# ---- tail ----------------------------------------------------------------- #
def _tail_restore(p): return 'club' if 'club' in p.mutations else 'normal'
def _ferrao_eq(p): p.genome.tail = 'sting'
def _ferrao_un(p): p.genome.tail = _tail_restore(p)
def _clava_eq(p): p.genome.tail = 'club'
def _clava_un(p): p.genome.tail = _tail_restore(p)
def _nectar_eq(p): p.regen += 3.0; p.genome.nectar_sac = True
def _nectar_un(p): p.regen = max(0.0, p.regen - 3.0); p.genome.nectar_sac = False


CHARMS_LIST = [
    _c('antenas',  'head', 'Antenas',            '+alcance da lingua',       190, 30, _antenas_eq, _antenas_un),
    _c('presas',   'head', 'Presas de Veneno',   'ataques envenenam',        105, 34, _presas_eq, _presas_un),
    _c('olhos',    'head', 'Olhos de Cacador',   '+20% area das armas',       50, 34, _olhos_eq, _olhos_un),
    _c('carapaca', 'back', 'Carapaca',           'bloqueia 20% do dano',     260, 42, _carapaca_eq, _carapaca_un),
    _c('espinhos', 'back', 'Espinhos',           'dano de contato',          330, 32, _espinhos_eq, _espinhos_un),
    _c('asas',     'back', 'Asas de Besouro',    '+velocidade e dash',       175, 38, _asas_eq, _asas_un),
    _c('glandula', 'back', 'Glandula de Esporos', 'libera a arma de esporos', 135, 46, _glandula_eq, _glandula_un),
    _c('ferrao',   'tail', 'Ferrao',             'rabada envenena',           18, 34, _ferrao_eq, _ferrao_un),
    _c('clava',    'tail', 'Cauda-Clava',        'rabada: +dano e empurrao',  15, 34, _clava_eq, _clava_un),
    _c('nectar',   'tail', 'Glandula de Nectar', 'regeneracao de vida',       45, 36, _nectar_eq, _nectar_un),
]
CHARMS = {c.id: c for c in CHARMS_LIST}
BY_SLOT = {slot: [c.id for c in CHARMS_LIST if c.slot == slot]
           for slot in ('head', 'back', 'tail')}
