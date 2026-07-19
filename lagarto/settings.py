"""Persisted options in ``~/.lagarto/settings.json``.

Only display options for now (fullscreen / window scale / vsync). Everything is
best-effort: a missing, unreadable or corrupt file just falls back to defaults so
the game always starts. The meta-progression save (DNA/unlocks) will live in the
same folder later.
"""

import json
import os

DEFAULTS = {'fullscreen': False, 'scale': 2, 'vsync': True}


def _dir():
    return os.path.join(os.path.expanduser('~'), '.lagarto')


def path():
    return os.path.join(_dir(), 'settings.json')


def load():
    data = dict(DEFAULTS)
    try:
        with open(path(), 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for k, v in DEFAULTS.items():
                got = raw.get(k, v)
                if isinstance(got, type(v)) or (isinstance(v, int) and isinstance(got, int)):
                    data[k] = got
    except Exception:
        pass                       # missing/corrupt -> defaults
    if data['scale'] not in (1, 2, 3):
        data['scale'] = DEFAULTS['scale']
    return data


def save(data):
    try:
        os.makedirs(_dir(), exist_ok=True)
        tmp = path() + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({k: data.get(k, v) for k, v in DEFAULTS.items()}, f, indent=1)
        os.replace(tmp, path())     # atomic-ish: never leave a half-written file
        return True
    except Exception:
        return False


def save_display(display_mod):
    return save({'fullscreen': display_mod.is_fullscreen(),
                 'scale': display_mod.get_scale(),
                 'vsync': display_mod.get_vsync()})
