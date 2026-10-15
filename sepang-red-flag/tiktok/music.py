"""Background music for the TikTok edit: one cue, 120 bpm in A minor, cut to the picture -> out/music.wav

  python3 -I tiktok/music.py                 # section marks from the edit (build.py EDL, 'mus' keys)
  render(marks, total, out)                  # what build.py calls

Every section starts its own bar on its cut, so drops land on the picture:
  hook      pluck arpeggio + drone build, tape-stop on "stopped"
  bahrain   first drop (Am - F)
  monsoon   half-time, dark pad, toms under the thunder
  footdown  pulse builds ... drops out on "nothing happened"
  ham       snare build into the punch-in
  engine    (the power-unit graphic, times inside it as in tiktok/engine_mg.py)
            build through the dismantle, full drop on the MGU-H slam, piano for "2026 - gone",
            groove back with a slowing arpeggio (lazy turbo), muffled in wet mode,
            ticking build into the lock-out, dead stop at zero kW
  untested  tense pulse
  redflag   piano + strings (red flag, session suspended)
  raceon    build
  montage   one bar of build, full drop with the hook melody on "we went racing"
  payoff    warm, F - G
  outro     resolves to C and rings out

Everything is synthesised here (no samples): wavetable saws, FFT filters, sidechain pumping, convolution reverb.
"""
import os
import sys
import wave
from collections import defaultdict

import numpy as np

SR = 48000
BEAT = .5                      # 120 bpm
BAR = 4 * BEAT
S16 = BEAT / 4
rng = np.random.default_rng(120)


def tt(d): return np.arange(max(0, int(round(d * SR)))) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------ dsp
def spec(x, g, pad=4096):
    """zero-phase FFT filter, g(freqs) -> gain"""
    n = len(x) + pad
    X = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(X * g(f), n)[:len(x)]


def lp(x, fc, o=2): return spec(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * o)))
def hp(x, fc, o=2): return spec(x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * o)))
def bp(x, lo, hi): return hp(lp(x, hi), lo)


def stft_lp(x, cut, n=2048, hop=512):
    """time-varying low-pass on a mono signal; cut(t) -> cutoff Hz (filter automation)"""
    win = np.hanning(n + 1)[:-1]
    p = np.concatenate([np.zeros(n), x, np.zeros(n)]); out = np.zeros_like(p)
    f = np.fft.rfftfreq(n, 1 / SR)
    for i in range(0, len(p) - n, hop):
        c = cut((i + n / 2 - n) / SR)
        if c >= 19000:
            out[i:i + n] += p[i:i + n] * win * win; continue
        out[i:i + n] += np.fft.irfft(np.fft.rfft(p[i:i + n] * win) / np.sqrt(1 + (f / c) ** 4), n) * win
    return out[n:n + len(x)] / 1.5


_tab = {}


def table(f, kind):
    K = max(1, int(15000 / f))
    if (kind, K) not in _tab:
        k = np.arange(1, K + 1); ph = np.arange(2048) / 2048
        a = 1 / k if kind == 'saw' else np.where(k % 2 == 1, 1 / k, 0)
        tab = (np.sin(2 * np.pi * np.outer(ph, k)) * a).sum(1)
        _tab[kind, K] = tab / np.abs(tab).max()
    return _tab[kind, K]


def osc(f, d, kind='saw', cents=0.0, vib=0.0, bend=None):
    """band-limited wavetable oscillator; vib in cents, bend(t) -> frequency multiplier"""
    t = tt(d); fr = np.full(len(t), f * 2 ** (cents / 1200))
    if vib:
        fr *= 2 ** (vib / 1200 * np.sin(2 * np.pi * 5.3 * t) * np.minimum(1, t / .4))
    if bend is not None:
        fr *= bend(t)
    ph = (rng.random() + np.cumsum(fr) / SR) % 1 * 2048
    tab = table(f, kind); i = ph.astype(int); k = ph - i
    return tab[i] * (1 - k) + tab[(i + 1) % 2048] * k


def adsr(n, a=.005, d=.1, s=1.0, r=.05):
    t = np.arange(n) / SR; dur = n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    return e * np.clip((dur - t) / max(r, 1e-4), 0, 1)


def noise(d): return rng.standard_normal(len(tt(d)))


# ------------------------------------------------------------------ instruments (mono unless noted)
def kick(d=.42):
    t = tt(d); f = 46 + 125 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5) * np.minimum(1, t * 1500)
    click = bp(noise(d), 1500, 7000) * np.exp(-t * 350) * .3
    return np.tanh((body + click) * 1.7)


def clap(d=.45):
    t = tt(d); n = bp(noise(d), 900, 7500)
    env = sum((t >= o) * np.exp(-np.maximum(0, t - o) * 190) for o in (0, .011, .023)) * .55 \
        + (t >= .03) * np.exp(-np.maximum(0, t - .03) * 15) * .75
    return n * env + np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * .35


def snare(d=.25):
    t = tt(d)
    return bp(noise(d), 1400, 9000) * np.exp(-t * 24) + np.sin(2 * np.pi * 205 * t) * np.exp(-t * 38) * .45


def hat(open_=False):
    d = .45 if open_ else .09; t = tt(d)
    return hp(noise(d), 7500) * np.exp(-t * (8 if open_ else 55))


def crash(d=2.6):
    t = tt(d)
    metal = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) for f in (3312, 4517, 5891, 7203)) * .08
    return (hp(noise(d), 4200) + metal) * np.exp(-t * 1.5) * np.minimum(1, t * 800)


def tom(m=41, d=.7):
    t = tt(d); f = hz(m) * (1 + .7 * np.exp(-t * 18))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) + lp(noise(d), 1200) * np.exp(-t * 40) * .3


def bass(m, d, cut=320, env=1400):
    f = hz(m); t = tt(d)
    s = osc(f, d, 'saw')
    e = np.exp(-t * 16)
    y = lp(s, cut + env) * e + lp(s, cut) * (1 - e)
    y = y * .55 + np.sin(2 * np.pi * f * t) * .8
    return y * adsr(len(t), .004, .25, .85, .03)


def sub(m, d):
    t = tt(d); f = hz(m)
    y = np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t) + lp(osc(f, d, 'saw'), 260) * .3
    return y * adsr(len(t), .08, .5, .9, .25)


def supersaw(ms, d, cut=2800, a=.01, dec=.5, sus=.75, r=.12, spread=20, voices=5, vib=0.0):
    """stereo detuned-saw chord"""
    L = np.zeros(len(tt(d))); R = np.zeros_like(L)
    for m in ms:
        for v in range(voices):
            c = (v / (voices - 1) * 2 - 1) * spread
            s = osc(hz(m), d, 'saw', cents=c, vib=vib)
            p = c / spread * .85
            L += s * np.sqrt((1 - p) / 2); R += s * np.sqrt((1 + p) / 2)
    e = adsr(len(L), a, dec, sus, r) / np.sqrt(len(ms) * voices)
    return np.stack([hp(lp(L, cut), 140) * e, hp(lp(R, cut), 140) * e], 1)


def strings(ms, d, cut=2200, a=.55, r=.7):
    return supersaw(ms, d, cut, a, 1.0, 1.0, r, spread=12, voices=6, vib=9)


def pluck(m, d=.3, bright=5200, dark=900):
    t = tt(d); s = osc(hz(m), d, 'saw') * .7 + osc(hz(m), d, 'sq', cents=7) * .3
    e = np.exp(-t * 20)
    return (lp(s, bright) * e + lp(s, dark) * (1 - e)) * np.exp(-t * 6) * np.minimum(1, t * 600)


def piano(m, d=2.5, vel=1.0):
    f = hz(m); t = tt(d); y = np.zeros(len(t))
    for n in range(1, 13):
        fn = n * f * np.sqrt(1 + .00035 * n * n)
        if fn > 11000:
            break
        a = vel ** (1 + n * .12) / n ** 1.2
        k = (.55 + .3 * n) * (f / 262) ** .4
        env = .55 * np.exp(-t * k * 2.6) + .45 * np.exp(-t * k * .45)
        for c in (-.7, .7):
            y += a * .5 * np.sin(2 * np.pi * fn * 2 ** (c / 1200) * t + rng.random() * 6.28) * env
    y += bp(noise(d), 700, 4500) * np.exp(-t * 90) * .06 * vel
    return y * np.minimum(1, t * 400) * np.clip((d - t) / .12, 0, 1)


def lead(m, d):
    t = tt(d)
    s = osc(hz(m), d, 'saw', vib=14) * .6 + osc(hz(m), d, 'sq', cents=-6, vib=14) * .4
    return lp(s, 3600) * adsr(len(t), .008, .25, .7, .06)


def riser(d, lo=300, hi=9000):
    """noise sweep + rising tone"""
    t = tt(d); k = t / d
    n = stft_lp(noise(d), lambda x: lo + (hi - lo) * np.clip(x / d, 0, 1) ** 2)
    f = 180 * 2 ** (3 * k)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .35
    return (hp(n, 250) + tone) * k ** 2.2


def tape_stop(ms, d=.5):
    """the chord slowing to a halt, for the freeze on "stopped" """
    bend = lambda t: np.maximum(.02, 1 - t / d) ** 1.6
    y = sum(osc(hz(m), d, 'saw', bend=bend) for m in ms) / len(ms)
    t = tt(d)
    return lp(y, 1800) * (1 - t / d) ** .7


# ------------------------------------------------------------------ harmony (A minor)
AM = (45, [57, 60, 64]); F = (41, [57, 60, 65]); C = (48, [55, 60, 64]); G = (43, [55, 59, 62])
DM = (38, [57, 62, 65]); E = (40, [56, 59, 64]); FM7 = (41, [53, 57, 60, 64]); CADD9 = (36, [55, 60, 62, 64, 67])
MAIN = [AM, F, C, G]


# ------------------------------------------------------------------ the mix
class Mix:
    def __init__(self, total):
        self.N = int((total + 4) * SR)
        self.bus = defaultdict(lambda: np.zeros((self.N, 2)))
        self.kicks = []

    def add(self, bus, sig, at, gain=1.0, pan=0.0, until=None):
        """until: section end - the note is cut there with a short fade (music edited to picture)"""
        if until is not None and at >= until - .01:
            return
        if sig.ndim == 1:
            sig = np.stack([sig * np.sqrt((1 - pan) / 2), sig * np.sqrt((1 + pan) / 2)], 1) * np.sqrt(2)
        if until is not None and at + len(sig) / SR > until:
            n = max(1, int((until - at) * SR)); sig = sig[:n].copy()
            f = min(n, int(.02 * SR)); sig[-f:] *= np.linspace(1, 0, f)[:, None]
        i = int(round(at * SR))
        if i < 0:
            sig = sig[-i:]; i = 0
        j = min(self.N, i + len(sig))
        if j > i:
            self.bus[bus][i:j] += sig[:j - i] * gain

    def kick(self, at, gain=1.0, until=None):
        if until is None or at < until - .01:
            self.add('kick', kick(), at, gain, until=until); self.kicks.append(at)


def steps(t0, t1, org, step):
    """grid times from origin org, every `step`, within [t0, t1)"""
    k = int(np.ceil((t0 - org) / step - 1e-6))
    while org + k * step < t1 - 1e-6:
        yield k, org + k * step
        k += 1


def chord_at(prog, org, t, bar=BAR):
    return prog[int(np.floor((t - org) / bar + 1e-6)) % len(prog)]


def drums(M, t0, t1, org, kpat='4', claps=True, hats='8', g=1.0, opens=True):
    for k, t in steps(t0, t1, org, S16):
        s = k % 16
        if (kpat == '4' and s % 4 == 0) or (kpat == '2' and s % 8 == 0) or (kpat == '1' and s == 0):
            M.kick(t, .95 * g, until=t1)
        if claps and s in (4, 12):
            M.add('drums', clap(), t, .5 * g, until=t1)
        if hats in ('8', '16') and s % 4 == 2:
            if opens and s == 14 and k % 32 == 30:
                M.add('drums', hat(True), t, .16 * g, .3, until=t1)
            else:
                M.add('drums', hat(), t, .28 * g, .3, until=t1)
        elif hats == '16' and s % 2 == 1:
            M.add('drums', hat(), t, .12 * g, -.3, until=t1)


def bassline(M, t0, t1, org, prog, g=1.0, cut=320, rate=2):
    """8ths (rate 2) on the chord root, octave up on the last eighth of each beat pair"""
    for k, t in steps(t0, t1, org, BEAT / rate):
        root = chord_at(prog, org, t)[0]
        m = root + (12 if rate == 2 and k % 4 == 3 else 0)
        M.add('bass', bass(m, BEAT / rate * .9, cut), t, .5 * g, until=t1)


def pads(M, t0, t1, org, prog, cut=2800, g=1.0, kind='saw'):
    k = int(np.floor((t0 - org) / BAR + 1e-6))
    while org + k * BAR < t1 - 1e-6:
        a = max(t0, org + k * BAR); b = min(t1, org + (k + 1) * BAR)
        ch = prog[k % len(prog)][1]
        sig = supersaw(ch, b - a + .3, cut) if kind == 'saw' else strings(ch, b - a + .6, cut)
        M.add('pad', sig, a, .3 * g, until=t1 if kind == 'saw' else None)
        k += 1


def arp(M, t0, t1, org, prog, step=S16, g=1.0, bright=5200, rate=None):
    pat = [0, 1, 2, 3, 2, 1, 2, 3]
    t, k = t0, 0
    first = next(steps(t0, t1, org, step), None)
    if first is None:
        return
    t = first[1]
    while t < t1 - 1e-6:
        ch = chord_at(prog, org, t)[1]
        tones = sorted(ch) + [sorted(ch)[0] + 12]
        m = tones[pat[k % len(pat)] % len(tones)] + 12
        M.add('arp', pluck(m, .32, bright), t, .16 * g, (-.45 if k % 2 else .45), until=t1)
        t += rate(t) if rate else step; k += 1


def keys(M, at, ch, bass_m=None, g=1.0, d=3.5, roll=.03, until=None):
    for i, m in enumerate(sorted(ch)):
        M.add('keys', piano(m, d, .8), at + i * roll, .3 * g, (i - 1.5) * .2, until=until)
    if bass_m is not None:
        M.add('keys', piano(bass_m, d, .9) + piano(bass_m - 12, d, .7) * .6, at, .32 * g, until=until)


def roll(M, t0, t1, g=1.0):
    """snare build: 8ths -> 16ths -> 32nds, rising"""
    t = t0
    while t < t1 - .01:
        k = (t - t0) / (t1 - t0)
        M.add('drums', snare(), t, (.12 + .35 * k ** 1.5) * g, until=t1)
        t += BEAT / 2 if k < .4 else BEAT / 4 if k < .75 else BEAT / 8


# ------------------------------------------------------------------ arrangement
def arrange(M, mk, total):
    sec = lambda name: (mk[name], mk[NEXT[name]] if NEXT[name] else total)
    autom = []                                     # (t, cutoff) master filter on the music buses

    # hook: plucked Am arpeggio over a drone, filter opening; tape-stop on "stopped"
    a, b = sec('hook'); stop = a + 2.6
    M.add('bass', sub(33, stop - a + .4), a, .3, until=stop + .05)
    pads(M, a, stop, a, [AM], cut=1600, g=.5)
    arp(M, a + .1, stop, a, [AM], g=1.0, bright=6000)
    for k, t in steps(a + 1.0, stop, a, S16):
        M.add('drums', hat(), t, .05 + .1 * (t - a) / 2.6, .3)
    M.add('fx', riser(stop - a - .4), a + .4, .22)
    M.add('fx', tape_stop(AM[1] + [45]), stop, .35)
    autom += [(a, 900), (stop - .1, 9000), (stop, 20000)]

    # bahrain: first drop
    a, b = sec('bahrain')
    M.add('drums', crash(), a, .3)
    drums(M, a, b, a); bassline(M, a, b, a, [AM, F]); pads(M, a, b, a, [AM, F]); arp(M, a, b, a, [AM, F], g=.8)
    autom += [(a, 20000)]

    # monsoon: half-time, dark, toms under the thunder
    a, b = sec('monsoon')
    M.add('bass', sub(33, b - a + .5), a, .4, until=b)
    pads(M, a, b, a, [DM, AM], cut=900, g=.8, kind='str')
    for k, t in steps(a, b, a, BEAT):
        if k % 4 == 0:
            M.add('drums', tom(36), t, .5)
        if k % 4 == 2:
            M.add('drums', tom(41), t, .3)
    for k, t in steps(a + 1.0, b, a, S16):
        M.add('drums', hat(), t, .05 if k % 2 else .09, .25)
    autom += [(a, 20000)]

    # footdown: pulse builds ... everything drops out on "nothing happened"
    a, b = sec('footdown'); nothing = a + 2.1
    bassline(M, a, nothing, a, [AM, AM, F], g=.8, cut=200)
    drums(M, a, nothing, a, kpat='4', claps=False, hats='16', g=.8)
    pads(M, a, nothing, a, [AM, F], cut=1200, g=.6, kind='str')
    M.add('fx', riser(nothing - a), a, .18)
    M.add('pad', strings([71, 72], b - nothing + .8, 3000, a=.05, r=.6), nothing, .22)     # B/C rub: suspense
    M.add('drums', crash(), nothing, .15)
    autom += [(a, 600), (nothing - .05, 5000), (nothing, 20000)]

    # ham: snare build into the punch-in (hit at +1.2)
    a, b = sec('ham')
    roll(M, a, a + 1.2, g=.8)
    M.add('fx', riser(1.2), a, .25)
    M.add('bass', sub(33, b - a - 1.2 + .3), a + 1.2, .5)

    # engine (31 s graphic); grid put so a downbeat lands on the MGU-H slam (5.75)
    e0, b = sec('engine'); org = e0 - .25
    t = lambda x: e0 + x
    M.add('pad', supersaw([57, 64, 71], 1.8, 1400, a=.6), e0, .25)                       # reveal: Am add9 swell
    M.add('bass', sub(33, 6.0), e0, .4, until=t(5.75))
    pads(M, t(1.75), t(5.75), org, MAIN, cut=1500, g=.6)
    arp(M, t(1.75), t(5.75), org, MAIN, step=BEAT / 2, g=.9)
    for k, x in steps(t(1.75), t(5.75), org, S16):
        M.add('drums', hat(), x, .1 if k % 2 == 0 else .05, .3)
    bassline(M, t(3.75), t(5.75), org, MAIN, g=.7, cut=220)
    M.add('fx', riser(1.6), t(4.15), .3)
    # MGU-H: full drop
    M.add('drums', crash(), t(5.75), .3)
    drums(M, t(5.75), t(11.85), org); bassline(M, t(5.75), t(11.85), org, MAIN)
    pads(M, t(5.75), t(11.85), org, MAIN); arp(M, t(5.75), t(11.85), org, MAIN, bright=7000)
    # "but for 2026, it's gone": piano + strings
    keys(M, t(11.9), FM7[1], 29, g=1.0, d=2.6, until=t(15.0))
    keys(M, t(13.85), AM[1] + [69], 33, g=.9, d=1.6, until=t(15.0))
    M.add('pad', strings(FM7[1], 2.1, 1800), t(11.9), .25)
    M.add('pad', strings(AM[1], 1.4, 1600), t(13.85), .25)
    # lazy turbo: groove back, half-time, arpeggio slows with the turbo
    drums(M, t(15.0), t(21.2), org, kpat='2', claps=True, hats='8', g=.85)
    bassline(M, t(15.0), t(21.2), org, MAIN, g=.85, cut=260)
    pads(M, t(15.0), t(21.2), org, MAIN, cut=1300, g=.8)
    arp(M, t(15.25), t(21.2), org, MAIN, g=.8, rate=lambda x: S16 * (1 + 3 * np.clip((x - t(15.3)) / 2.4, 0, 1)))
    # wet mode: same groove, muffled (master filter below) + rain on the fx bus
    drums(M, t(21.2), t(24.3), org, kpat='4', claps=False, hats='16', g=.8)
    bassline(M, t(21.2), t(24.3), org, MAIN, g=.8, cut=200)
    pads(M, t(21.2), t(24.3), org, MAIN, cut=1200, g=.7)
    rain = (hp(noise(3.6), 1800) * .5 + bp(noise(3.6), 300, 1500) * .3) * adsr(len(tt(3.6)), .3, 1, 1, .5)
    M.add('fx', rain, t(21.0), .12)
    # energy limit: ticks speed up into the lock-out, E chord tension, then dead stop at zero kW
    x = t(24.4)
    while x < t(28.1):
        M.add('drums', np.sin(2 * np.pi * 1900 * tt(.06)) * np.exp(-tt(.06) * 80), x, .1, .2)
        x += .25 - .19 * np.clip((x - t(24.4)) / 3.5, 0, 1)
    M.add('bass', sub(28, 3.9), t(24.3), .45, until=t(28.1))
    M.add('pad', strings(E[1] + [71], 3.9, 1400, a=1.2), t(24.3), .28, until=t(28.1))
    roll(M, t(26.3), t(28.1), g=.9)
    M.add('fx', riser(3.3), t(24.8), .25, until=t(28.1))
    M.add('pad', strings([70, 71], 3.0, 2500, a=.6), t(28.3), .12)                      # zero kW: dissonant hang
    M.add('bass', sub(33, 2.8), t(28.2), .3)
    autom += [(e0, 1400), (t(5.6), 6000), (t(5.75), 20000), (t(15.0), 2600), (t(21.1), 2600), (t(21.2), 520),
              (t(24.3), 520), (t(24.35), 1600), (t(28.0), 9000), (t(28.1), 20000)]

    # untested: tense pulse
    a, b = sec('untested')
    for k, x in steps(a, b, a, S16):
        M.add('bass', bass(33 + (12 if k % 4 == 2 else 0), S16 * .8, 260), x, .35, until=b)
    for k, x in steps(a, b, a, BEAT):
        M.add('drums', tom(36, .5) if k % 2 == 0 else snare(), x, .35 if k % 2 == 0 else .12, until=b)
    pads(M, a, b, a, [AM, E], cut=2000, g=.8, kind='str')

    # red flag + session suspended: piano + strings
    a, b = sec('redflag')
    M.add('bass', sub(33, 2.2), a, .4)
    keys(M, a + .05, AM[1] + [64 + 12], 33, g=1.1, d=2.2, until=a + 2.0)
    keys(M, a + 2.0, FM7[1], 29, g=1.0, d=2.4, until=b)
    M.add('pad', strings(AM[1], 2.2, 1600), a, .25)
    M.add('pad', strings(FM7[1], 2.2, 1600), a + 2.0, .25)

    # race on: build
    a, b = sec('raceon')
    M.add('pad', strings(G[1] + [67], b - a + .3, 2400, a=.3), a, .28, until=b)
    bassline(M, a, b, a, [G], g=.7, cut=220, rate=4)
    roll(M, a + .4, b)
    M.add('fx', riser(b - a), a, .25)
    autom += [(a, 900), (b - .05, 7000), (b, 20000)]

    # montage: a bar of build, then the full drop with the hook melody on "we went racing"
    a, b = sec('montage'); drop = a + BAR
    drums(M, a, drop, a, kpat='4', claps=False, hats='16', g=.85)
    bassline(M, a, drop, a, [AM], g=.85, cut=240)
    pads(M, a, drop, a, [AM], cut=1600, g=.7)
    roll(M, drop - BEAT * 2, drop, g=.8)
    M.add('drums', crash(), drop, .32)
    prog = [F, C, G]
    drums(M, drop, b, drop); bassline(M, drop, b, drop, prog); pads(M, drop, b, drop, prog); arp(M, drop, b, drop, prog, g=.7)
    mel = [(0, 76, 1), (1, 76, .5), (1.5, 74, .5), (2, 72, 1), (3, 74, 1), (4, 76, 1.5), (5.5, 79, .5), (6, 79, 1), (7, 76, 1)]
    for bt, m, d in mel:
        M.add('lead', lead(m, d * BEAT * .95), drop + bt * BEAT, .22, until=b)
    autom += [(a, 1200), (drop - .05, 8000), (drop, 20000)]

    # payoff: warm F - G, light pulse
    a, b = sec('payoff')
    M.add('drums', crash(), a, .18)
    for x, ch in ((a, F), (a + BAR, G)):
        keys(M, x, ch[1], ch[0] - 12, g=.8, d=2.3, roll=.05, until=b)
        M.add('pad', strings(ch[1], BAR + .4, 2600), x, .22)
    for k, x in steps(a, b, a, BEAT):
        if k % 2 == 0:
            M.kick(x, .5, until=b)
        M.add('drums', hat(), x + BEAT / 2, .07, .3, until=b)
    bassline(M, a, b, a, [F, G], g=.55, cut=260, rate=1)

    # outro: resolve to C and ring out
    a, b = sec('outro')
    M.add('drums', crash(3.5), a, .22)
    keys(M, a, CADD9[1], 36, g=1.0, d=3.6, roll=.06)
    M.add('pad', strings(CADD9[1], b - a + 1.2, 3000), a, .25)
    M.add('bass', sub(36, b - a + .5), a, .35)
    return sorted(autom)


NEXT = {'hook': 'bahrain', 'bahrain': 'monsoon', 'monsoon': 'footdown', 'footdown': 'ham', 'ham': 'engine', 'engine': 'untested',
        'untested': 'redflag', 'redflag': 'raceon', 'raceon': 'montage', 'montage': 'payoff', 'payoff': 'outro', 'outro': None}


def reverb_ir(d=2.4, seed=0):
    t = tt(d); r = np.random.default_rng(seed)
    ir = bp(r.standard_normal(len(t)), 220, 6500) * np.exp(-t * 2.9)
    ir[:int(.018 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum())


def conv(x, ir):
    n = len(x) + len(ir)
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]


def render(marks, total, out):
    M = Mix(total)
    autom = arrange(M, marks, total)
    N = M.N
    # sidechain: tonal buses pump under the kick
    g = np.ones(N); L = int(.45 * SR); sh = 1 - .55 * np.exp(-np.arange(L) / SR / .13)
    for k in M.kicks:
        i = int(k * SR); j = min(N, i + L); g[i:j] = np.minimum(g[i:j], sh[:j - i])
    for b in ('bass', 'pad', 'arp', 'lead'):
        M.bus[b] *= g[:, None]
    # ping-pong dotted-eighth delay on the arp and lead
    for b in ('arp', 'lead'):
        x = M.bus[b].copy(); dl = int(.375 * SR)
        for k in range(1, 5):
            src = x[:, 0] + x[:, 1]
            M.bus[b][dl * k:, k % 2] += src[:-dl * k] * .5 * .38 ** k
    # master filter automation on the tonal buses (wet mode, builds)
    xs, ys = zip(*autom)
    cut = lambda x: float(np.interp(x, xs, ys))
    for b in ('bass', 'pad', 'arp', 'drums', 'kick', 'lead'):
        M.bus[b] = np.stack([stft_lp(M.bus[b][:, c], cut) for c in range(2)], 1)
    lvl = dict(kick=1.0, drums=1.1, bass=.75, pad=2.3, arp=2.6, keys=1.1, lead=2.3, fx=1.0)
    dry = sum(M.bus[b] * lvl[b] for b in M.bus)
    send = sum(M.bus[b] * s for b, s in dict(drums=.12, pad=.3, arp=.35, keys=.45, lead=.3, fx=.3).items() if b in M.bus)
    wet = np.stack([conv(send[:, 0], reverb_ir(seed=1)), conv(send[:, 1], reverb_ir(seed=2))], 1)
    m = dry + wet * .9
    m = hp(m[:, 0], 28)[:, None] * [1, 0] + hp(m[:, 1], 28)[:, None] * [0, 1]
    m = m[:int(total * SR)]
    m = np.tanh(m / (np.abs(m).max() + 1e-9) * 1.5)
    m *= .89 / np.abs(m).max()
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((m * 32767).astype('<i2').tobytes())
    return out


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
    import build
    marks, t = {}, 0.0
    for s in build.EDL:
        if s.get('mus'):
            marks[s['mus']] = t
        t += s['dur']
    print(marks, round(t, 3))
    print(render(marks, t, sys.argv[1] if len(sys.argv) > 1 else os.path.join(build.OUT, 'music.wav')))
