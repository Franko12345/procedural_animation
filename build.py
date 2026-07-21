"""Build a single-file executable of Lagarto with PyInstaller.

Most art/sound/music is generated in code, but Fase 7 added optional pixel-art
PNGs under assets/ (icons.draw prefers them, falls back to procedural if absent)
-- so assets/ ships alongside the bundled Python + pygame + numpy.

    python build.py            # build for the current OS
    python build.py --clean    # wipe build/ dist/ first

Output: dist/Lagarto (Linux/macOS) or dist/Lagarto.exe (Windows).

IMPORTANT -- PyInstaller does NOT cross-compile: running this on Linux produces a
Linux binary only. To get a Windows .exe, either run this script on Windows, or let
CI do it: .github/workflows/build.yml builds both on every push (and attaches them
to a GitHub Release when you push a tag like v1.0).
"""

import os
import shutil
import subprocess
import sys

NAME = 'Lagarto'
ENTRY = 'lizard_game.py'


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    if '--clean' in sys.argv:
        for d in ('build', 'dist'):
            shutil.rmtree(d, ignore_errors=True)
        spec = f'{NAME}.spec'
        if os.path.exists(spec):
            os.remove(spec)
        print('[build] limpo')

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print('[build] PyInstaller nao instalado. Rode:\n'
              '    pip install pyinstaller')
        return 1

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', NAME,
        '--noconfirm',
        # no console window on Windows/macOS; keep it on Linux for the [gamepad]/[audio] logs
        *(['--windowed'] if sys.platform != 'linux' else []),
        # the package is imported dynamically in places -> make sure it all ships
        '--hidden-import', 'pygame',
        '--collect-submodules', 'lagarto',
    ]
    # optional pixel-art PNGs (Fase 7) -- assets.py falls back to procedural icons
    # if this is missing, so skip cleanly rather than fail a build without it
    assets_dir = os.path.join(root, 'assets')
    if os.path.isdir(assets_dir):
        cmd += ['--add-data', f'{assets_dir}{os.pathsep}assets']
    cmd.append(ENTRY)
    print('[build]', ' '.join(cmd))
    rc = subprocess.call(cmd)
    if rc == 0:
        out = os.path.join('dist', NAME + ('.exe' if os.name == 'nt' else ''))
        print(f'[build] pronto -> {out}')
    else:
        print(f'[build] falhou (codigo {rc})')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
