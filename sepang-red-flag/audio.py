"""Synthesised soundtrack for the 50 s Sepang red-flag film (timed to main.js)."""
import numpy as np
import wave

SR, DUR = 48000, 50.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)


def env(points):
    """piecewise-linear envelope from [(time, value), ...]"""
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


def fft_filter(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.clip((f - lo * .7) / (lo * .3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * .3), 0, 1)
    return np.fft.irfft(X * m, len(x))


def place(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if i >= N: return
    s = sig[:j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)


def tt(d): return np.arange(int(d * SR)) / SR


# ---- rain bed (stereo decorrelated band-limited noise), intensity follows the picture
rain_i = env([(0, 0), (.4, .5), (6, .5), (6.01, .35), (9, .4), (11.5, 1), (20, 1), (20.05, .12), (36, .12),
              (36.05, 0), (41, 0), (41.02, .9), (45, .9), (45.02, .6), (49.3, .55), (50, 0)])
for ch, seed in ((L, 1), (R, 2)):
    n = np.random.default_rng(seed).standard_normal(N)
    hiss = fft_filter(n, 1500, 9000) * .5 + fft_filter(n, 300, 1500) * .35
    ch += hiss * rain_i * .11

# ---- drone + pad
drone_env = env([(0, 0), (1, .7), (12, .8), (20, .5), (36, .7), (41, .9), (45, .6), (49.3, .7), (50, 0)])
drone = sum(np.sin(2 * np.pi * f * t + p) * a for f, a, p in [(41.2, 1, 0), (41.6, .7, 1), (82.4, .35, 2), (61.7, .3, 3)])
L += drone * drone_env * .13; R += drone * drone_env * .13
pad_env = env([(0, 0), (2, .5), (11, .6), (12, .2), (20, .3), (35, .5), (36, .4), (40.8, .7), (41, 0), (45, 0), (46, .5), (49.3, .6), (50, 0)])
for f, pan in [(164.8, -.6), (196.0, .5), (246.9, -.2), (329.6, .7), (123.5, 0)]:
    v = np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * .13 * t) * 2) + .4 * np.sin(2 * np.pi * f * 1.003 * t)
    v *= .5 + .5 * np.sin(2 * np.pi * (.07 + f / 4000) * t)
    L += v * pad_env * .022 * np.sqrt((1 - pan) / 2); R += v * pad_env * .022 * np.sqrt((1 + pan) / 2)

# ---- thunder on lightning strikes (crack + long rumble)
for s in [.15, 3.35, 10.3, 18.7, 41.05]:
    d = tt(4.0); n = rng.standard_normal(len(d))
    crack = fft_filter(n, 800, 7000) * np.exp(-d * 9) * .6
    rumble = fft_filter(rng.standard_normal(len(d)), 25, 220) * (1 - np.exp(-d * 8)) * np.exp(-d * 1.1) * 2.2
    place(crack + rumble, s, .55, pan=rng.uniform(-.5, .5))

# ---- whoosh into cuts + cinematic hits on cuts
CUTS = [6, 12, 20, 36, 41, 45]
for c in CUTS:
    d = tt(.7); n = rng.standard_normal(len(d))
    sw = fft_filter(n, 400, 6000) * (d / .7) ** 3
    place(sw, c - .7, .35, pan=-.3); place(fft_filter(rng.standard_normal(len(d)), 400, 6000) * (d / .7) ** 3, c - .7, .35, pan=.3)
    d = tt(2.2)
    f = 55 * np.exp(-d * 3) + 32
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * 2.4)
    hit = boom * 1.0 + fft_filter(rng.standard_normal(len(d)), 60, 3000) * np.exp(-d * 14) * .5
    place(hit, c, .9 if c == 41 else .62)

# ---- title kinetic stingers (soft ticks as type lands)
for s in [.8, 1.25, 3.0, 3.25, 6.3, 9.95, 12.2, 16.0, 17.6, 18.15, 39.3, 45.3, 47.8, 48.15]:
    d = tt(.25); tick = np.sin(2 * np.pi * 1800 * d) * np.exp(-d * 60) + fft_filter(rng.standard_normal(len(d)), 3000, 12000) * np.exp(-d * 90) * .5
    place(tick, s, .12, pan=rng.uniform(-.4, .4))

# ---- formation-lap engine: steady low drone, power cut at 15.6 s, glide to silence by ~17.8 s
seg = (t >= 11.9) & (t < 20)
eng_f = np.where(t < 15.6, 92 + 6 * np.sin(2 * np.pi * .7 * t), 92 * np.exp(-(t - 15.6) * 1.4) + 18)
phase = 2 * np.pi * np.cumsum(eng_f) / SR
eng = sum(np.sin(k * phase) / k ** .9 for k in range(1, 14))
eng_env = env([(11.9, 0), (12.2, .55), (15.55, .6), (15.75, .25), (17.8, 0), (20, 0)])
eng = fft_filter(eng * eng_env, 30, 2500) * seg
L += eng * .22; R += eng * .22
# electrical "drop-out" blip at the moment drive is lost
d = tt(.6); place(np.sign(np.sin(2 * np.pi * (600 - 900 * d) * d)) * np.exp(-d * 7) * .4, 15.6, .25)

# ---- tech section: 120 bpm pulse, stops dead at the energy lock-out (33.2 s)
bpm = 120; beat = 60 / bpm
for k in range(int((33.2 - 20.3) / (beat / 2))):
    s = 20.3 + k * beat / 2
    d = tt(.12); click = fft_filter(rng.standard_normal(len(d)), 5000, 14000) * np.exp(-d * 70)
    place(click, s, .16 if k % 2 else .08, pan=.35 if k % 4 < 2 else -.35)
    if k % 2 == 0:
        d = tt(.45); b = np.sin(2 * np.pi * 55 * d) * np.exp(-d * 6) + .3 * np.sin(2 * np.pi * 110 * d) * np.exp(-d * 9)
        place(b, s, .35)
# arpeggio blips that slow down with the turbo (24-27 s) and the cap (28.7-30 s)
notes = [659.3, 987.8, 784.0, 1318.5]
s = 20.4; k = 0
while s < 33.2:
    rate = .125 * (1 + 1.4 * np.clip((s - 24.3) / 2.7, 0, 1))
    d = tt(.18); blip = np.sin(2 * np.pi * notes[k % 4] * d) * np.exp(-d * 28)
    place(blip, s, .06, pan=(-.5 if k % 2 else .5)); s += rate; k += 1
# power-down sweep at lock-out
d = tt(1.6); f = 420 * np.exp(-d * 2.4) + 30
place(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-d * 1.6) * (1 - np.exp(-d * 40)), 33.2, .45)
# tension sustain after lock-out
ten = (np.sin(2 * np.pi * 233.1 * t) + np.sin(2 * np.pi * 246.9 * t)) * env([(33.4, 0), (34.5, .5), (36, .3), (38.5, .35), (39, 0)])
L += ten * .03; R += ten * .03

# ---- riser into the red flag
d = tt(2.3); f = 120 * np.exp(d * 1.25)
riser = np.sin(2 * np.pi * np.cumsum(f) / SR) * (d / 2.3) ** 2 * .5 + fft_filter(rng.standard_normal(len(d)), 1500, 9000) * (d / 2.3) ** 3
place(riser, 41 - 2.3, .4)
# red-flag alarm, two-tone
for k in range(7):
    s = 41.3 + k * .5
    d = tt(.24); f0 = 880 if k % 2 == 0 else 660
    tone = np.tanh(3 * np.sin(2 * np.pi * f0 * d)) * np.minimum(1, d * 200) * np.exp(-d * 5)
    place(fft_filter(tone, 300, 4000), s, .07, pan=.25 if k % 2 else -.25)

# ---- restart: driving pulse + final resolve
for k in range(int((49.2 - 45.0) / (beat / 2))):
    s = 45.0 + k * beat / 2
    d = tt(.3); kick = np.sin(2 * np.pi * (60 * np.exp(-d * 18) + 45) * d) * np.exp(-d * 9)
    if k % 2 == 0: place(kick, s, .5)
    d = tt(.1); place(fft_filter(rng.standard_normal(len(d)), 6000, 14000) * np.exp(-d * 60), s + beat / 4, .1)
d = tt(4.0); chord = sum(np.sin(2 * np.pi * f * d) for f in [82.4, 123.5, 164.8, 246.9, 329.6]) * np.exp(-d * .9) * np.minimum(1, d * 30)
place(chord, 47.8, .12)

# ---- reverb (synthetic IR via FFT convolution) + master
ir_t = tt(2.6)
irL = np.random.default_rng(11).standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
irR = np.random.default_rng(12).standard_normal(len(ir_t)) * np.exp(-ir_t * 2.6)
irL = fft_filter(irL, 150, 7000); irR = fft_filter(irR, 150, 7000)


def conv(x, ir):
    n = len(x) + len(ir)
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]


wetL = conv(L, irL); wetR = conv(R, irR)
wetL /= np.max(np.abs(wetL)) + 1e-9; wetR /= np.max(np.abs(wetR)) + 1e-9
mixL = L / (np.max(np.abs(L)) + 1e-9) + wetL * .22
mixR = R / (np.max(np.abs(R)) + 1e-9) + wetR * .22
fade = env([(0, 0), (.3, 1), (49.2, 1), (50, 0)])
out = np.stack([np.tanh(mixL * 1.4) * fade, np.tanh(mixR * 1.4) * fade], 1)
out /= np.max(np.abs(out)) / .89
with wave.open('soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype('<i2').tobytes())
print('ok', out.shape)
