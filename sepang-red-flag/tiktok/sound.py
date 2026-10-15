"""Sound design for the TikTok edit: real trackside audio + explainer score + synthesised SFX.

mix(events, total, out_wav, vo=None)
  events: dicts with 'at' (edit time, s) and either
    {'wav': path, 'src': s, 'dur': s, 'gain': g, 'rate': r, 'fade': s, 'pan': p, 'bus': 'music'|'fx'|'live'}
        rate < 1 plays slower and lower (tape-style slow-mo)
    {'sfx': name, 'gain': g, 'pan': p, ...kwargs}   names: see SFX below
  vo: optional voice-over wav, placed at 0; every other bus ducks ~12 dB under it.
"""
import wave

import numpy as np

SR = 48000
_rng = np.random.default_rng(44)


def _read(path):
    with wave.open(path) as w:
        ch, sr = w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    x = x.reshape(-1, ch)
    if ch == 1:
        x = np.repeat(x, 2, 1)
    if sr != SR:
        n = int(len(x) * SR / sr); t = np.linspace(0, len(x) - 1, n)
        x = np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    return x


_cache = {}


def load(path):
    if path not in _cache:
        _cache[path] = _read(path)
    return _cache[path]


def tt(d): return np.arange(int(d * SR)) / SR


def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo * .7) / (lo * .3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * .3), 0, 1)
    return np.fft.irfft(X * m, len(x))


def noise(d): return _rng.standard_normal(int(d * SR))


# ------------------------------------------------------------------ synthesised SFX (mono)
def whoosh(d=.6, lo=300, hi=7000):
    t = tt(d); n = band(noise(d), lo, hi)
    return n * (t / d) ** 2.5 * np.minimum(1, (d - t) * 40) * .9


def rev_whoosh(d=1.0):
    return whoosh(d, 200, 9000)


def hit(d=2.2, f0=55, body=1.0):
    t = tt(d); f = f0 * np.exp(-t * 3) + 32
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    return boom * body + band(noise(d), 60, 3000) * np.exp(-t * 14) * .5


def sub_drop(d=1.4):
    t = tt(d); f = 90 * np.exp(-t * 2.5) + 28
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) * np.minimum(1, t * 200)


def riser(d=2.0):
    t = tt(d); f = 140 * np.exp(t * 1.3 / d * 1.6)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * .45 + band(noise(d), 1500, 9000)) * (t / d) ** 2.5


def tick():
    t = tt(.2)
    return np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 70) + band(noise(.2), 3000, 12000) * np.exp(-t * 90) * .5


def thunder(d=4.0):
    t = tt(d)
    crack = band(noise(d), 800, 7000) * np.exp(-t * 9) * .6
    rumble = band(noise(d), 25, 220) * (1 - np.exp(-t * 8)) * np.exp(-t * 1.1) * 2.2
    return crack + rumble


def glitch(d=.5):
    """digital stutter: chopped noise + square blips, for 'stopped' / lock-out"""
    t = tt(d); out = np.zeros_like(t)
    k = 0
    while k < len(t):
        n = int(_rng.uniform(.012, .05) * SR); seg = slice(k, min(len(t), k + n))
        f = _rng.choice([180, 360, 720, 1440, 95])
        if _rng.random() < .5:
            out[seg] = np.sign(np.sin(2 * np.pi * f * t[seg])) * .5
        else:
            out[seg] = band(noise((n + 2) / SR), 800, 8000)[:seg.stop - seg.start] * .8
        k += n + int(_rng.uniform(0, .02) * SR)
    return out * np.exp(-t * 1.5)


def powerdown(d=1.6):
    t = tt(d); f = 420 * np.exp(-t * 2.4) + 30
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) * (1 - np.exp(-t * 40))


def scanner(d=1.0):
    """x-ray sweep: rising filtered tone with tremolo + data beeps"""
    t = tt(d); f = 900 + 1800 * t / d
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * (.5 + .5 * np.sin(2 * np.pi * 22 * t)) * .35
    hum = np.sin(2 * np.pi * 110 * t) * .25 + np.sin(2 * np.pi * 220 * t) * .1
    out = (tone + hum) * np.minimum(1, t * 20) * np.minimum(1, (d - t) * 8)
    for k in np.arange(.08, d - .05, .11):
        i = int(k * SR); b = tt(.05); out[i:i + len(b)] += np.sin(2 * np.pi * 2600 * b) * np.exp(-b * 60) * .5
    return out


def beep(f=1800, d=.12):
    t = tt(d); return np.sin(2 * np.pi * f * t) * np.minimum(1, t * 400) * np.exp(-t * 18)


def clank(d=.9):
    """metal part separating / locking: inharmonic partials + a click"""
    t = tt(d)
    ring = sum(np.sin(2 * np.pi * f * t) * a * np.exp(-t * k) for f, a, k in [(523, 1, 9), (1187, .6, 12), (1931, .45, 16), (2877, .3, 22)])
    return ring * .5 + band(noise(d), 2000, 12000) * np.exp(-t * 120) * .8


def zap(d=.5):
    """electric crackle for energy flowing (harvest / boost)"""
    t = tt(d); out = band(noise(d), 2500, 11000) * (np.sin(2 * np.pi * 37 * t) > .2) * .5
    return (out + np.sin(2 * np.pi * (400 + 1600 * t / d) * t) * .2) * np.minimum(1, t * 40) * np.minimum(1, (d - t) * 10)


SFX = dict(whoosh=whoosh, rev_whoosh=rev_whoosh, hit=hit, sub_drop=sub_drop, riser=riser, tick=tick,
           thunder=thunder, glitch=glitch, powerdown=powerdown, scanner=scanner, beep=beep, clank=clank, zap=zap)


# ------------------------------------------------------------------ mixer
def _place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(round(at * SR))
    if sig.ndim == 1:
        sig = np.stack([sig * np.sqrt((1 - pan) / 2), sig * np.sqrt((1 + pan) / 2)], 1) * np.sqrt(2)
    if i < 0:
        sig = sig[-i:]; i = 0
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[:j - i] * gain


def _slice(path, src, dur, rate=1.0, fade=.04):
    x = load(path); n_out = int(dur * SR)
    pos = src * SR + np.arange(n_out) * rate
    pos = pos[pos < len(x) - 1]
    i = pos.astype(int); k = (pos - i)[:, None]
    y = x[i] * (1 - k) + x[i + 1] * k
    if rate < 1:  # tape slow-down darkens the sound a little more
        y = np.stack([band(y[:, c], 20, 9000 * rate + 2000) for c in range(2)], 1)
    nf = max(1, int(fade * SR)); env = np.ones(len(y))
    env[:nf] = np.linspace(0, 1, nf); env[-nf:] = np.minimum(env[-nf:], np.linspace(1, 0, nf))
    return y * env[:, None]


def _env(x, att=.01, rel=.25):
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    e = np.abs(x).max(1) if x.ndim > 1 else np.abs(x)
    # block-wise follower (fast enough in numpy): peak per 10 ms, then one-pole smoothing
    hop = SR // 100; n = len(e) // hop
    pk = e[:n * hop].reshape(n, hop).max(1); out = np.zeros(n); s = 0.0
    for i, v in enumerate(pk):
        c = a if v > s else r; s = c * s + (1 - c) * v; out[i] = s
    return np.interp(np.arange(len(e)), np.arange(n) * hop, out)


def mix(events, total, out_wav, vo=None):
    N = int(total * SR) + SR
    bus = {b: np.zeros((N, 2), np.float32) for b in ('music', 'live', 'fx')}
    for ev in events:
        g = ev.get('gain', 1.0)
        if 'wav' in ev:
            y = _slice(ev['wav'], ev.get('src', 0), ev['dur'], ev.get('rate', 1.0), ev.get('fade', .04))
            if ev.get('hp'):
                y = np.stack([band(y[:, c], ev['hp'], 16000) for c in range(2)], 1)
            _place(bus[ev.get('bus', 'live')], y, ev['at'], g)
        else:
            kw = {k: v for k, v in ev.items() if k not in ('sfx', 'at', 'gain', 'pan', 'bus')}
            _place(bus[ev.get('bus', 'fx')], SFX[ev['sfx']](**kw), ev['at'], g, ev.get('pan', 0))
    m = bus['music'] * .9 + bus['live'] + bus['fx'] * .8
    if vo is not None:
        v = np.zeros((N, 2), np.float32); src = load(vo)[:N]; v[:len(src)] = src
        v *= .5 / (np.abs(v).max() + 1e-9) * 2.2       # voice sits on top of the mix
        m = m * (1 - .75 * np.clip(_env(v, rel=.5) / .06, 0, 1))[:, None] + v   # ~12 dB duck under speech, slow release
    m = m[:int(total * SR)]
    fo = int(.6 * SR); m[-fo:] *= np.linspace(1, 0, fo)[:, None]
    m = np.tanh(m / (np.abs(m).max() + 1e-9) * 1.6) * .9
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(m, -1, 1) * 32767).astype('<i2').tobytes())
    return out_wav
