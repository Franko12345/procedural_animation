"""Performance HUD + optional CSV log.

Exists because a stutter that only shows up after minutes of play cannot be
diagnosed by guessing. The overlay separates the frame budget into step / draw /
present and -- crucially -- exposes the glow-sprite cache, whose unbounded growth
was the cause of the first long-session slowdown. Two numbers tell that story
apart at a glance:

  * cache ENTRIES climbing forever  -> leaking (keys too fine-grained)
  * cache MISSES/s staying high     -> thrashing (working set > cap, so it keeps
                                       clearing and rebuilding; each miss is a
                                       surface alloc + 10 filled circles)

Off by default. ``OFF``/``BASIC``/``FULL`` cycle with F3, and the level persists
in settings.json so the options menu can drive it too.
"""

import os
import time

import pygame

from . import config as C
from . import palette

OFF, BASIC, FULL = 0, 1, 2
LEVEL_NAMES = ('desligado', 'fps', 'detalhado')

_LOG_PATH = os.path.join(os.path.expanduser('~'), '.lagarto', 'perf.csv')
_COLS = ('t', 'fps', 'frame_ms', 'step_ms', 'draw_ms', 'present_ms',
         'glow_entries', 'glow_mb', 'glow_miss_s', 'glow_clears',
         'enemies', 'parts', 'sparks', 'projectiles', 'puddles', 'rss_mb')


def _rss_mb():
    """Resident memory, best effort -- Linux /proc, else psutil, else 0."""
    try:
        with open('/proc/self/statm') as f:
            return int(f.read().split()[1]) * os.sysconf('SC_PAGE_SIZE') / (1 << 20)
    except Exception:
        pass
    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return kb / 1024.0
    except Exception:
        return 0.0


class Perf:
    def __init__(self, level=OFF, log=False):
        self.level = level
        self.log = log
        self.step_ms = self.draw_ms = self.present_ms = self.frame_ms = 0.0
        self.fps = 0.0
        self._acc = 0.0                  # seconds since the last 1 Hz sample
        self._frames = 0
        self._sum = [0.0, 0.0, 0.0, 0.0]
        self._last_misses = 0
        self.snap = {}
        self._t0 = time.time()
        self._fh = None
        self._font = None

    # ---- lifecycle ------------------------------------------------------ #
    def cycle(self):
        self.level = (self.level + 1) % 3
        return self.level

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None

    def _open_log(self):
        if self._fh or not self.log:
            return
        try:
            os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
            self._fh = open(_LOG_PATH, 'w', buffering=1)
            self._fh.write(','.join(_COLS) + '\n')
            print(f'[perf] gravando {_LOG_PATH}')
        except Exception as exc:
            print(f'[perf] nao consegui abrir o log ({exc})')
            self.log = False

    # ---- per-frame ------------------------------------------------------ #
    def frame(self, dt, step_ms, draw_ms, present_ms, game):
        """Feed one frame; aggregates to a 1 Hz sample (cheap when OFF)."""
        if self.level == OFF and not self.log:
            return
        self._frames += 1
        self._acc += dt
        s = self._sum
        s[0] += dt * 1000.0
        s[1] += step_ms
        s[2] += draw_ms
        s[3] += present_ms
        if self._acc < 1.0:
            return

        n = max(1, self._frames)
        entries, nbytes, _hits, misses, clears = palette.glow_stats()
        self.fps = self._frames / self._acc
        self.frame_ms = s[0] / n
        self.step_ms = s[1] / n
        self.draw_ms = s[2] / n
        self.present_ms = s[3] / n
        self.snap = dict(
            glow_entries=entries,
            glow_mb=nbytes / (1 << 20),
            glow_miss_s=(misses - self._last_misses) / self._acc,
            glow_clears=clears,
            enemies=len(game.enemies),
            parts=len(game.fx.parts),
            sparks=len(game.fx.sparks),
            projectiles=len(game.projectiles),
            puddles=len(game.puddles),
            rss_mb=_rss_mb(),
        )
        self._last_misses = misses
        self._acc = 0.0
        self._frames = 0
        self._sum = [0.0, 0.0, 0.0, 0.0]

        if self.log:
            self._open_log()
            self._write_row()

    def _write_row(self):
        if not self._fh:
            return
        d = self.snap
        row = [f'{time.time() - self._t0:.1f}', f'{self.fps:.1f}',
               f'{self.frame_ms:.2f}', f'{self.step_ms:.2f}',
               f'{self.draw_ms:.2f}', f'{self.present_ms:.2f}',
               str(d['glow_entries']), f"{d['glow_mb']:.1f}",
               f"{d['glow_miss_s']:.0f}", str(d['glow_clears']),
               str(d['enemies']), str(d['parts']), str(d['sparks']),
               str(d['projectiles']), str(d['puddles']), f"{d['rss_mb']:.1f}"]
        try:
            self._fh.write(','.join(row) + '\n')
        except Exception:
            self.log = False

    # ---- drawing -------------------------------------------------------- #
    def draw(self, surf, font):
        if self.level == OFF:
            return
        col = (120, 240, 150) if self.fps >= 55 else (
            (250, 210, 90) if self.fps >= 30 else (255, 96, 96))
        lines = [(f'{self.fps:4.0f} FPS   {self.frame_ms:5.2f} ms', col)]
        if self.level == FULL:
            d = self.snap
            lines += [
                (f'step {self.step_ms:5.2f}  draw {self.draw_ms:5.2f}  '
                 f'present {self.present_ms:5.2f}', (206, 208, 226)),
                (f"glow {d.get('glow_entries', 0):4d} entradas  "
                 f"{d.get('glow_mb', 0):5.1f} MB  "
                 f"{d.get('glow_miss_s', 0):4.0f} miss/s  "
                 f"limpezas {d.get('glow_clears', 0)}",
                 (255, 170, 120) if d.get('glow_miss_s', 0) > 400 else (206, 208, 226)),
                (f"inim {d.get('enemies', 0):3d}  part {d.get('parts', 0):4d}  "
                 f"spark {d.get('sparks', 0):4d}  proj {d.get('projectiles', 0):3d}  "
                 f"poca {d.get('puddles', 0):2d}", (206, 208, 226)),
                (f"RSS {d.get('rss_mb', 0):6.1f} MB", (206, 208, 226)),
            ]
        w = max(font.size(t)[0] for t, _ in lines) + 16
        h = len(lines) * 20 + 10
        x = C.WIDTH - w - 10
        bg = pygame.Surface((w, h))
        bg.set_alpha(170)
        bg.fill((10, 12, 20))
        surf.blit(bg, (x, 8))
        for i, (text, c) in enumerate(lines):
            surf.blit(font.render(text, True, c), (x + 8, 13 + i * 20))
