"""Generate a cinematic teal-orange 3D LUT (.cube) for the Sepang TikTok edit.

  python3 teal_orange_lut.py out.cube [strength]

Hue remap: greens/cyans/blues are pulled toward teal, reds/yellows toward orange.
Split-tone: shadows lean teal, highlights lean warm. Exposure pull, filmic S-curve, lifted blacks.
"""
import sys
import numpy as np

N = 33
out = sys.argv[1] if len(sys.argv) > 1 else 'teal_orange.cube'
K = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

g = np.linspace(0, 1, N)
b, gg, r = np.meshgrid(g, g, g, indexing='ij')  # .cube order: red varies fastest
rgb = np.stack([r, gg, b], -1).reshape(-1, 3)


def rgb2hsv(c):
    mx, mn = c.max(1), c.min(1); d = mx - mn
    h = np.zeros(len(c))
    m = d > 1e-9
    rr, gc, bc = c[:, 0], c[:, 1], c[:, 2]
    i = m & (mx == rr); h[i] = ((gc - bc)[i] / d[i]) % 6
    i = m & (mx == gc) & (mx != rr); h[i] = (bc - rr)[i] / d[i] + 2
    i = m & (mx == bc) & (mx != rr) & (mx != gc); h[i] = (rr - gc)[i] / d[i] + 4
    return h * 60, np.where(mx > 0, d / np.maximum(mx, 1e-9), 0), mx


def hsv2rgb(h, s, v):
    h = (h % 360) / 60; i = np.floor(h).astype(int) % 6; f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return np.select([i[:, None] == k for k in range(6)],
                     [np.stack(x, 1) for x in [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]])


h, s, v = rgb2hsv(rgb)
TEAL, ORANGE = 186.0, 26.0


def pull(h, target, centre, width, amt):
    """move hues within +-width of centre toward target, smooth falloff"""
    d = (h - centre + 180) % 360 - 180
    w = np.clip(1 - np.abs(d) / width, 0, 1) ** .8 * amt
    dt = (target - h + 180) % 360 - 180
    return h + dt * w, w


h2, wt = pull(h, TEAL, 165, 85, .80 * K)        # greens (aramco boards, grass), cyans, blues -> teal
h2, wo = pull(h2, ORANGE, 25, 40, .55 * K)       # reds/yellows/skin -> orange (keeps Ferrari red-orange)
# greens get desaturated a touch so the grass/boards don't scream; oranges get a little richer
s2 = s * (1 - .28 * K * np.clip(1 - np.abs(((h - 120 + 180) % 360) - 180) / 50, 0, 1)) * (1 + .30 * K * wo)
c = hsv2rgb(h2, np.clip(s2, 0, 1), v)

# luminance-based split tone
Y = c @ np.array([.2126, .7152, .0722])
sh = np.clip(1 - Y / .55, 0, 1) ** 1.4
hi = np.clip((Y - .45) / .55, 0, 1) ** 1.2
mid = 1 - sh - hi
c = c + K * (sh[:, None] * np.array([-.070, .020, .060]) + mid[:, None] * np.array([-.032, .008, .028])
             + hi[:, None] * np.array([.065, .020, -.050]))

# exposure pull (overcast footage is high-key), then filmic S-curve with lifted blacks, soft roll-off
x = np.clip(c, 0, 1) ** (1 + .32 * K)
curve = lambda x: .022 + .94 * (x * x * (3 - 2 * x) * .75 + x * .25)
c = x + K * (curve(x) - x)
c = np.clip(c, 0, 1)

with open(out, 'w') as f:
    f.write(f'TITLE "Sepang teal-orange"\nLUT_3D_SIZE {N}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    np.savetxt(f, c, fmt='%.6f')
print('wrote', out)
