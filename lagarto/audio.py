"""Synthesised audio: no sound files, everything is generated with numpy at boot.

Same philosophy as the visuals -- the game ships no assets, so SFX are little
waveform recipes and the music is a *generative* layered loop whose intensity
follows the game state (menu / camp = calm, round = driving, boss = tense).

Everything degrades safely: if the mixer can't open (headless, no audio device)
``ok()`` is False and every call is a no-op, so the game runs silently.
"""

import random

import numpy as np
import pygame

SR = 22050
_ok = False
_sfx = {}                 # name -> list of Sound variants
_music = {}               # name -> Sound
_music_name = None
_music_ch = None
_sfx_vol = 0.7
_music_vol = 0.45


# --------------------------------------------------------------------------- #
#  Synthesis helpers                                                           #
# --------------------------------------------------------------------------- #

def _wave(kind, freq, t):
    if kind == 'sine':
        return np.sin(2 * np.pi * freq * t)
    if kind == 'square':
        return np.sign(np.sin(2 * np.pi * freq * t))
    if kind == 'saw':
        return 2.0 * ((freq * t) % 1.0) - 1.0
    if kind == 'tri':
        return 2.0 * np.abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0
    return np.random.uniform(-1, 1, len(t))          # noise


def _env(t, attack=0.005, decay=8.0):
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-decay * t)


def _tone(freq, dur, kind='sine', decay=8.0, vol=0.5, sweep=0.0, attack=0.005):
    """One shaped oscillator burst. ``sweep`` glides the pitch over the sound."""
    n = max(8, int(SR * dur))
    t = np.linspace(0, dur, n, endpoint=False)
    f = freq * (1.0 + sweep * (t / dur))
    return _wave(kind, f, t) * _env(t, attack, decay) * vol


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def _sound(mono):
    peak = np.max(np.abs(mono)) or 1.0
    mono = np.clip(mono / peak * 0.85, -1, 1)
    stereo = np.column_stack([mono, mono])
    return pygame.sndarray.make_sound((stereo * 32767).astype(np.int16))


# --------------------------------------------------------------------------- #
#  SFX recipes                                                                 #
# --------------------------------------------------------------------------- #

def _recipe(name, pitch=1.0):
    p = pitch
    if name == 'dash':
        return _mix(_tone(520 * p, 0.22, 'noise', decay=16, vol=0.5, sweep=-0.7),
                    _tone(300 * p, 0.18, 'saw', decay=14, vol=0.25, sweep=-0.5))
    if name == 'shoot':
        return _tone(680 * p, 0.12, 'square', decay=26, vol=0.32, sweep=-0.55)
    if name == 'hit':
        return _mix(_tone(220 * p, 0.07, 'noise', decay=45, vol=0.4),
                    _tone(160 * p, 0.09, 'tri', decay=30, vol=0.3, sweep=-0.4))
    if name == 'kill':
        return _mix(_tone(400 * p, 0.28, 'noise', decay=13, vol=0.45, sweep=-0.8),
                    _tone(190 * p, 0.3, 'saw', decay=10, vol=0.3, sweep=-0.6))
    if name == 'eat':
        return _tone(430 * p, 0.13, 'sine', decay=20, vol=0.4, sweep=0.9)
    if name == 'levelup':
        notes = [523, 659, 784, 1047]
        parts = []
        for i, f in enumerate(notes):
            seg = np.zeros(int(SR * 0.075 * i))
            parts.append(np.concatenate([seg, _tone(f * p, 0.3, 'tri', decay=7, vol=0.3)]))
        return _mix(*parts)
    if name == 'buy':
        return _mix(_tone(880 * p, 0.10, 'square', decay=22, vol=0.25),
                    np.concatenate([np.zeros(int(SR * 0.06)),
                                    _tone(1320 * p, 0.14, 'square', decay=18, vol=0.22)]))
    if name == 'hurt':
        return _mix(_tone(150 * p, 0.26, 'saw', decay=11, vol=0.5, sweep=-0.45),
                    _tone(70 * p, 0.3, 'sine', decay=9, vol=0.4))
    if name == 'nest':
        return _mix(_tone(120 * p, 0.5, 'noise', decay=7, vol=0.5, sweep=-0.5),
                    _tone(90 * p, 0.45, 'saw', decay=8, vol=0.35, sweep=-0.3))
    if name == 'wave':
        return _mix(_tone(196 * p, 0.6, 'saw', decay=4.5, vol=0.3, attack=0.05),
                    _tone(294 * p, 0.6, 'tri', decay=4.5, vol=0.22, attack=0.06))
    if name == 'w_spit':          # projectile: wet blip
        return _tone(720 * p, 0.11, 'square', decay=28, vol=0.30, sweep=-0.5)
    if name == 'w_homing':        # stinger: rising whine
        return _mix(_tone(560 * p, 0.16, 'saw', decay=18, vol=0.24, sweep=0.55),
                    _tone(1120 * p, 0.10, 'sine', decay=26, vol=0.12, sweep=0.4))
    if name == 'w_web':           # sticky, soft
        return _tone(300 * p, 0.18, 'tri', decay=14, vol=0.22, sweep=-0.3)
    if name == 'w_aura':          # low pulsing hum
        return _tone(120 * p, 0.35, 'sine', decay=6, vol=0.16, attack=0.08)
    if name == 'w_orbit':         # tiny wing flutter
        return _tone(880 * p, 0.07, 'tri', decay=34, vol=0.14, sweep=0.3)
    if name == 'w_puddle':        # splat
        return _mix(_tone(180 * p, 0.22, 'noise', decay=16, vol=0.26, sweep=-0.6),
                    _tone(110 * p, 0.2, 'sine', decay=14, vol=0.18))
    if name == 'victory':
        notes = [523, 659, 784, 1047, 1319]
        parts = []
        for i, f in enumerate(notes):
            seg = np.zeros(int(SR * 0.10 * i))
            parts.append(np.concatenate([seg, _tone(f * p, 0.55, 'tri', decay=4.0, vol=0.26)]))
        return _mix(*parts)
    if name == 'ui':
        return _tone(600 * p, 0.05, 'square', decay=40, vol=0.18)
    if name == 'evolve':
        return _mix(_tone(330 * p, 0.5, 'tri', decay=5, vol=0.3, sweep=0.7),
                    _tone(495 * p, 0.45, 'sine', decay=6, vol=0.25, sweep=0.5))
    return _tone(440 * p, 0.1)


SFX_NAMES = ('dash', 'shoot', 'hit', 'kill', 'eat', 'levelup', 'buy',
             'hurt', 'nest', 'wave', 'ui', 'evolve', 'victory',
             'w_spit', 'w_homing', 'w_web', 'w_aura', 'w_orbit', 'w_puddle')


# --------------------------------------------------------------------------- #
#  Generative music                                                            #
# --------------------------------------------------------------------------- #

PENTA = [0, 3, 5, 7, 10]          # minor pentatonic steps


def _note(semitone, base=220.0):
    return base * (2.0 ** (semitone / 12.0))


def _build_music(intensity, seed=7):
    """A short seamless loop; higher intensity = faster, busier, more percussive."""
    rng = random.Random(seed + intensity)
    bpm = (78, 104, 132)[intensity]
    beat = 60.0 / bpm
    bars, beats_per_bar = 4, 4
    dur = bars * beats_per_bar * beat
    n = int(SR * dur)
    out = np.zeros(n)

    def place(buf, at, part):
        i = int(at * SR)
        end = min(n, i + len(part))
        if end > i:
            buf[i:end] += part[:end - i]

    root = [0, -2, 3, -4][:bars]
    for b in range(bars):
        bar_t = b * beats_per_bar * beat
        r = root[b % len(root)]
        # bass: root on beats 1 and 3
        for k in (0, 2):
            place(out, bar_t + k * beat,
                  _tone(_note(r, 110), beat * 1.6, 'saw', decay=3.2, vol=0.30))
        # pad: soft sustained fifth
        place(out, bar_t, _tone(_note(r + 7, 220), beat * 3.6, 'tri',
                                decay=1.1, vol=0.13, attack=0.25))
        # arpeggio: pentatonic sparkle (denser at higher intensity)
        steps = (2, 4, 8)[intensity]
        for k in range(steps):
            if intensity == 0 and rng.random() < 0.35:
                continue
            deg = rng.choice(PENTA)
            place(out, bar_t + k * (beats_per_bar * beat / steps),
                  _tone(_note(r + deg + 12, 220), beat * 0.7, 'square',
                        decay=7.0, vol=0.10))
        # percussion from intensity 1 up
        if intensity >= 1:
            for k in range(beats_per_bar):
                place(out, bar_t + k * beat,
                      _tone(60, 0.10, 'sine', decay=26, vol=0.22, sweep=-0.6))
            if intensity >= 2:
                for k in range(beats_per_bar * 2):
                    place(out, bar_t + k * beat / 2 + beat / 2,
                          _tone(1, 0.05, 'noise', decay=55, vol=0.10))
    # tiny fade at the seam so the loop doesn't click
    f = int(SR * 0.02)
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    return out


# --------------------------------------------------------------------------- #
#  Public API                                                                  #
# --------------------------------------------------------------------------- #

def init(sfx_vol=0.7, music_vol=0.45):
    """Open the mixer and pre-render every sound. Safe to call when audio is absent."""
    global _ok, _sfx_vol, _music_vol, _music_ch
    _sfx_vol, _music_vol = sfx_vol, music_vol
    try:
        pygame.mixer.pre_init(SR, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(24)
    except Exception as exc:
        print(f"[audio] sem som ({exc})")
        _ok = False
        return False
    try:
        for name in SFX_NAMES:
            _sfx[name] = [_sound(_recipe(name, p)) for p in (0.92, 1.0, 1.09)]
        for i, key in enumerate(('calm', 'combat', 'boss')):
            _music[key] = _sound(_build_music(i))
        _music['victory'] = _sound(_build_music(0, seed=42))
        _music_ch = pygame.mixer.Channel(0)
        _ok = True
        print(f"[audio] {len(_sfx)} efeitos + {len(_music)} trilhas sintetizados")
    except Exception as exc:
        print(f"[audio] falha ao sintetizar ({exc})")
        _ok = False
    return _ok


def ok():
    return _ok


def play(name, vol=1.0):
    if not _ok:
        return
    variants = _sfx.get(name)
    if not variants:
        return
    s = random.choice(variants)
    s.set_volume(max(0.0, min(1.0, vol * _sfx_vol)))
    try:
        s.play()
    except Exception:
        pass


def set_music(name):
    """Switch the generative track ('calm' / 'combat' / 'boss'), with a crossfade."""
    global _music_name
    if not _ok or name == _music_name or name not in _music:
        return
    _music_name = name
    try:
        _music_ch.fadeout(400)
        _music[name].set_volume(_music_vol)
        _music_ch.play(_music[name], loops=-1, fade_ms=600)
    except Exception:
        pass


def set_volumes(sfx=None, music=None):
    global _sfx_vol, _music_vol
    if sfx is not None:
        _sfx_vol = max(0.0, min(1.0, sfx))
    if music is not None:
        _music_vol = max(0.0, min(1.0, music))
        if _ok and _music_name:
            try:
                _music[_music_name].set_volume(_music_vol)
            except Exception:
                pass


def volumes():
    return _sfx_vol, _music_vol
