"""Score for the power-unit graphic (tiktok/engine_mg.py), 31 s, same palette as audio.py (drone, pad, 120 bpm pulse).

  python3 -I tiktok/engine_score.py out/engine_score.wav

  0.0  drone + pad swell under the reveal
  1.4  pulse builds through the dismantle (hats only, then bass)
  5.8  MGU-H: full pulse + bright arpeggio (energy) to 11.8
 11.9  2026 / "it's gone": pulse cuts, minor pad, low sustain - the sad beat
 15.0  lazy turbo: pulse back, arpeggio slows with the turbo
 21.2  wet mode: muted pulse + rain bed
 24.5  energy limit: ticking speeds up into the lock-out
 28.1  zero kW: everything stops, power-down, tension sustain
"""
import sys
import wave

import numpy as np

SR, DUR = 48000, 31.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(31)
L = np.zeros(N); R = np.zeros(N)


def env(points):
    xs, ys = zip(*points); return np.interp(t, xs, ys)


def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo * .7) / (lo * .3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * .3), 0, 1)
    return np.fft.irfft(X * m, len(x))


def place(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if i >= N or j <= i: return
    s = sig[:j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)


def tt(d): return np.arange(int(d * SR)) / SR


# drone (E) + pad: major-ish colour for the tech, minor (C-E-G -> A minor) for the sad beat
drone_e = env([(0, 0), (.6, .8), (11.8, .7), (12.0, 1.0), (15, .8), (28.1, .7), (28.3, 1.0), (31, .9)])
drone = sum(np.sin(2 * np.pi * f * t + p) * a for f, a, p in [(41.2, 1, 0), (41.6, .7, 1), (82.4, .35, 2), (61.7, .3, 3)])
L += drone * drone_e * .14; R += drone * drone_e * .14
pad_tech = env([(0, 0), (1.2, .55), (11.8, .5), (12.0, 0), (15.0, 0), (15.6, .35), (28.1, .4), (28.2, 0), (31, 0)])
pad_sad = env([(0, 0), (11.85, 0), (12.3, .9), (14.6, .8), (15.3, 0), (28.15, 0), (28.6, .5), (31, .45)])
for chord, envl in (([164.8, 196.0, 246.9, 329.6, 123.5], pad_tech), ([220.0, 261.6, 329.6, 440.0, 110.0], pad_sad)):
    for i, f in enumerate(chord):
        pan = [-.6, .5, -.2, .7, 0][i]
        v = np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .13 * t) * 2) + .4 * np.sin(2 * np.pi * f * 1.003 * t)
        v *= .5 + .5 * np.sin(2 * np.pi * (.07 + f / 4000) * t)
        L += v * envl * .024 * np.sqrt((1 - pan) / 2); R += v * envl * .024 * np.sqrt((1 + pan) / 2)

# rain bed for the wet-mode stretch
rain = env([(0, 0), (20.8, 0), (21.3, 1), (28.1, .8), (29, .3), (31, .3)])
for ch, seed in ((L, 1), (R, 2)):
    n = np.random.default_rng(seed).standard_normal(N)
    ch += (band(n, 1500, 9000) * .5 + band(n, 300, 1500) * .35) * rain * .09

# 120 bpm pulse: hats, bass on the beat; sections set what plays
beat = .5
for k in range(int(DUR / (beat / 2))):
    s = k * beat / 2
    on_hat = (1.4 <= s < 11.85) or (15.0 <= s < 28.1)
    on_bass = (3.4 <= s < 11.85) or (15.4 <= s < 28.1)
    if on_hat:
        g = .07 if (21.2 <= s < 24.5) else .14
        d = tt(.12); click = band(rng.standard_normal(len(d)), 5000, 14000) * np.exp(-d * 70)
        place(click, s, g if k % 2 else g / 2, pan=.35 if k % 4 < 2 else -.35)
    if on_bass and k % 2 == 0:
        d = tt(.45); b = np.sin(2 * np.pi * 55 * d) * np.exp(-d * 6) + .3 * np.sin(2 * np.pi * 110 * d) * np.exp(-d * 9)
        place(b, s, .5 if 5.8 <= s < 11.85 else .34)
    if 5.8 <= s < 11.85 and k % 2 == 0:  # kick under the MGU-H section
        d = tt(.3); place(np.sin(2 * np.pi * (60 * np.exp(-d * 18) + 45) * d) * np.exp(-d * 9), s, .45)

# arpeggio: fast + bright for the MGU-H, slowing with the turbo, sparse in the rain
notes = [659.3, 987.8, 784.0, 1318.5]
s, k = 1.6, 0
while s < 28.1:
    if 11.85 <= s < 15.2:
        s = 15.2; continue
    if s < 5.8: rate = .25
    elif s < 11.85: rate = .125
    else: rate = .125 * (1 + 2.0 * np.clip((s - 15.3) / 2.2, 0, 1))
    d = tt(.18); blip = np.sin(2 * np.pi * notes[k % 4] * d) * np.exp(-d * 28)
    place(blip, s, .07 if s < 21 else .045, pan=(-.5 if k % 2 else .5)); s += rate; k += 1

# riser into the MGU-H reveal and into the lock-out (ticks speed up)
d = tt(1.6); f = 140 * np.exp(d * 1.2)
place(np.sin(2 * np.pi * np.cumsum(f) / SR) * (d / 1.6) ** 2.5 * .4 + band(rng.standard_normal(len(d)), 1500, 9000) * (d / 1.6) ** 3, 5.8 - 1.6, .45)
s = 24.6
while s < 28.1:
    d = tt(.06); place(np.sin(2 * np.pi * 1900 * d) * np.exp(-d * 80), s, .12, pan=.2)
    s += .25 - .19 * np.clip((s - 24.6) / 3.5, 0, 1)
d = tt(3.3); f = 120 * np.exp(d * .9)
place(np.sin(2 * np.pi * np.cumsum(f) / SR) * (d / 3.3) ** 2 * .35, 28.1 - 3.3, .4)
# tension sustain after zero kW
ten = (np.sin(2 * np.pi * 233.1 * t) + np.sin(2 * np.pi * 246.9 * t)) * env([(28.3, 0), (29.2, .5), (31, .4)])
L += ten * .03; R += ten * .03

# reverb + master (as audio.py)
ir_t = tt(2.6)
irL = band(np.random.default_rng(11).standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6), 150, 7000)
irR = band(np.random.default_rng(12).standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6), 150, 7000)


def conv(x, ir):
    n = len(x) + len(ir); return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]


wL, wR = conv(L, irL), conv(R, irR)
wL /= np.abs(wL).max() + 1e-9; wR /= np.abs(wR).max() + 1e-9
mL = L / (np.abs(L).max() + 1e-9) + wL * .22; mR = R / (np.abs(R).max() + 1e-9) + wR * .22
out = np.stack([np.tanh(mL * 1.4), np.tanh(mR * 1.4)], 1)
out /= np.abs(out).max() / .89
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'out/engine_score.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype('<i2').tobytes())
