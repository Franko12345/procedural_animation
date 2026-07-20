"""Meta-progression: DNA earned across runs buys permanent upgrades and unlocks.

Saved next to the options in ``~/.lagarto/save.json``. Like the settings file it is
best-effort: a missing or corrupt save just starts a fresh profile, so the game
always boots.

Two kinds of spending (Vampire-Survivors style):
  * **UPGRADES** -- permanent stat levels applied to every future run.
  * **UNLOCKS**  -- charms/weapons added to the pools a run can roll from.
"""

import json
import os

from . import settings


# ---- permanent stat upgrades (id -> definition) --------------------------- #
UPGRADES = {
    'vitality':  dict(name='Vitalidade', desc='+12 vida maxima por nivel',
                      hue=5, max_level=5, cost=lambda l: 30 + 25 * l),
    'might':     dict(name='Potencia', desc='+6% dano por nivel (armas, dash, rabo)',
                      hue=0, max_level=5, cost=lambda l: 40 + 30 * l),
    'haste':     dict(name='Cadencia', desc='-4% recarga das armas por nivel',
                      hue=190, max_level=5, cost=lambda l: 40 + 30 * l),
    'agility':   dict(name='Agilidade', desc='+4% velocidade por nivel',
                      hue=130, max_level=4, cost=lambda l: 35 + 25 * l),
    'growth':    dict(name='Crescimento', desc='+8% XP por nivel',
                      hue=50, max_level=4, cost=lambda l: 35 + 25 * l),
    'harvest':   dict(name='Colheita', desc='+10% polen por nivel',
                      hue=45, max_level=4, cost=lambda l: 30 + 20 * l),
}

# ---- unlocks (id -> what it adds to the run pools) ------------------------ #
UNLOCKS = {
    'weapon_enxame':   dict(name='Enxame', desc='libera a arma Enxame', cost=80,
                            kind='weapon', target='enxame', hue=55),
    'weapon_acido':    dict(name='Poca de Acido', desc='libera a arma Acido', cost=90,
                            kind='weapon', target='acido', hue=95),
    'charm_asas':      dict(name='Asas de Besouro', desc='libera o charm Asas', cost=70,
                            kind='charm', target='asas', hue=200),
    'charm_glandula':  dict(name='Glandula de Esporos', desc='libera o charm Esporos',
                            cost=70, kind='charm', target='glandula', hue=135),
    # --- personagens jogaveis --------------------------------------------- #
    # Dois compraveis com DNA e um por CONQUISTA (modelo Isaac/Rain World):
    # comprar da escolha desde a primeira run, conquistar da objetivo de longo
    # prazo. `cost=None` significa "nao esta a venda" -- so se ganha.
    'char_vibora':     dict(name='Vibora', desc='personagem: a cauda e a arma',
                            cost=120, kind='character', target='vibora', hue=285),
    'char_couracado':  dict(name='Couracado', desc='personagem: sem dash, blindado',
                            cost=150, kind='character', target='couracado', hue=20),
    'char_larva':      dict(name='Larva', desc='personagem: cresce durante a run',
                            cost=None, kind='character', target='larva', hue=95,
                            achieve='chegue a onda 8 numa run',
                            check=lambda d: d.get('best_wave', 0) >= 8),
}

WIN_BONUS = 150          # DNA extra por vencer a run

# `best_wave` alimenta as conquistas. save() persiste tudo que estiver aqui
# (`{k: data.get(k, v) for k, v in DEFAULT.items()}`), entao adicionar a chave
# basta para ela sobreviver -- mas load() precisa valida-la junto.
DEFAULT = {'dna': 0, 'upgrades': {}, 'unlocks': [], 'best_score': 0, 'runs': 0,
           'beat_game': False, 'wins': 0, 'best_wave': 0, 'total_kills': 0}


def path():
    return os.path.join(os.path.dirname(settings.path()), 'save.json')


def load():
    data = dict(DEFAULT)
    data['upgrades'] = {}
    data['unlocks'] = []
    try:
        with open(path(), 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data['dna'] = max(0, int(raw.get('dna', 0)))
            data['best_score'] = max(0, int(raw.get('best_score', 0)))
            data['runs'] = max(0, int(raw.get('runs', 0)))
            data['beat_game'] = bool(raw.get('beat_game', False))
            data['wins'] = max(0, int(raw.get('wins', 0)))
            data['best_wave'] = max(0, int(raw.get('best_wave', 0)))
            data['total_kills'] = max(0, int(raw.get('total_kills', 0)))
            ups = raw.get('upgrades', {})
            if isinstance(ups, dict):
                for k, v in ups.items():
                    if k in UPGRADES:
                        data['upgrades'][k] = max(0, min(int(v), UPGRADES[k]['max_level']))
            unl = raw.get('unlocks', [])
            if isinstance(unl, list):
                data['unlocks'] = [u for u in unl if u in UNLOCKS]
    except Exception:
        pass                      # missing/corrupt -> fresh profile
    return data


def save(data):
    try:
        os.makedirs(os.path.dirname(path()), exist_ok=True)
        tmp = path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({k: data.get(k, v) for k, v in DEFAULT.items()}, f, indent=1)
        os.replace(tmp, path())
        return True
    except Exception:
        return False


# ---- queries -------------------------------------------------------------- #
def level(data, uid):
    return int(data.get('upgrades', {}).get(uid, 0))


def upgrade_cost(data, uid):
    spec = UPGRADES[uid]
    lvl = level(data, uid)
    return None if lvl >= spec['max_level'] else int(spec['cost'](lvl))


def buy_upgrade(data, uid):
    cost = upgrade_cost(data, uid)
    if cost is None or data['dna'] < cost:
        return False
    data['dna'] -= cost
    data.setdefault('upgrades', {})[uid] = level(data, uid) + 1
    save(data)
    return True


def buy_unlock(data, uid):
    spec = UNLOCKS.get(uid)
    # cost=None -> achievement-only, never purchasable
    if not spec or spec.get('cost') is None or uid in data['unlocks'] \
            or data['dna'] < spec['cost']:
        return False
    data['dna'] -= spec['cost']
    data['unlocks'].append(uid)
    save(data)
    return True


def unlocked(data, kind, target):
    """Is this weapon/charm available? Anything without an UNLOCKS entry is free."""
    for uid, spec in UNLOCKS.items():
        if spec['kind'] == kind and spec['target'] == target:
            return uid in data['unlocks']
    return True


# ---- run integration ------------------------------------------------------ #
def apply_to_player(data, player):
    """Bake the permanent upgrades into a freshly-created player."""
    player.meta = data                       # lets card/charm pools check unlocks
    lv = lambda k: level(data, k)                                   # noqa: E731
    if lv('vitality'):
        player.max_health += 12 * lv('vitality')
        player.health = player.max_health
    if lv('might'):
        player.might *= 1.0 + 0.06 * lv('might')
    if lv('haste'):
        player.cooldown_mult *= (1.0 - 0.04) ** lv('haste')
    if lv('agility'):
        f = 1.0 + 0.04 * lv('agility')
        player.max_speed *= f
        player.speed_mult *= f
    if lv('growth'):
        player.xp_mult *= 1.0 + 0.08 * lv('growth')
    player.pollen_mult = 1.0 + 0.10 * lv('harvest')


def dna_for_run(score, wave, kills):
    """How much DNA a finished run is worth."""
    return int(score / 90 + wave * 4 + kills * 0.4)


def finish_run(data, score, wave, kills, won=False):
    """Bank a finished run. Winning pays a bonus and unlocks endless mode."""
    gained = dna_for_run(score, wave, kills)
    if won:
        gained += WIN_BONUS
        data['beat_game'] = True
        data['wins'] = data.get('wins', 0) + 1
    data['dna'] += gained
    data['runs'] += 1
    data['best_score'] = max(data['best_score'], int(score))
    data['best_wave'] = max(data.get('best_wave', 0), int(wave))
    data['total_kills'] = data.get('total_kills', 0) + int(kills)
    check_achievements(data)          # may grant characters -- before save()
    save(data)
    return gained


def check_achievements(data):
    """Grant any achievement-gated unlock whose condition is now met.

    Returns the newly granted specs so the end-of-run screen can announce them --
    an unlock the player never sees might as well not have happened.
    """
    won = []
    for uid, spec in UNLOCKS.items():
        check = spec.get('check')
        if check and uid not in data['unlocks'] and check(data):
            data['unlocks'].append(uid)
            won.append(spec)
    return won


def unlock_hint(kind, target):
    """How this thing is obtained, for the locked row on a select screen."""
    for spec in UNLOCKS.values():
        if spec['kind'] == kind and spec['target'] == target:
            if spec.get('achieve'):
                return spec['achieve']
            return f"{spec['cost']} DNA em EVOLUCAO"
    return ''


def endless_unlocked(data):
    return bool(data.get('beat_game'))
