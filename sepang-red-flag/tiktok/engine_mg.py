"""Power-unit motion graphic from real photos: one unit -> exploded view -> MGU-H close-up -> what went wrong.

  python3 -I tiktok/engine_mg.py out/engine.mp4                 # full 31 s, 1080x1920 30 fps
  python3 -I tiktok/engine_mg.py out/engine_sheet.jpg --sheet 1 3 6 9 13.9 18.5 23 27 29.6

photos/pu/img0.jpeg  a real F1 V6 turbo-hybrid power unit (Renault Energy F1) on white
photos/pu/img1.jpeg  a Garrett electric turbocharger - the road-car descendant of the MGU-H
Both are gitignored like the other photos. The parts are cut out with hand-drawn polygons and animated in
2.5D; the MGU-H "cutaway" on the turbo photo is an illustration of where it sits (on the turbo shaft,
between turbine and compressor), not a scan.

Timeline (s), locked to the AI voice-over lines in tiktok/voice.py (the build places them at the same times):
  0.0  reveal: the whole unit                       VO 'inside' tail
  1.4  dismantle: V6 / airbox / exhausts / turbo     VO 'unit'   (1.4 - 6.5)
  5.8  MGU-H slam on the turbo shaft
  6.7  cut to the turbo photo: harvest -> boost      VO 'mguh'   (6.9 - 11.75)  "Zero lag!" 10.85
 12.0  2026: MGU-H deleted                           VO 'gone'   (12.1 - 14.4)
 15.0  back together: lazy turbo -> MGU-K            VO 'lazy'   (15.0 - 20.9)
 21.2  wet mode: 348 -> 250 kW                       VO 'wet'    (21.2 - 24.2)
 24.5  energy limit lock-out                         VO 'lock'   (24.5 - 27.9)
 28.1  zero kW, throttle ignored                     VO 'zero'   (28.1 - 30.5)
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OW, OH, FPS = 1080, 1920, 30
DUR = 31.0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = '/usr/share/fonts/opentype/inter/'
_fonts = {}


def font(w, size):
    k = (w, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FD + {'black': 'InterDisplay-Black.otf', 'semi': 'InterDisplay-SemiBold.otf',
                                             'light': 'InterDisplay-Light.otf'}[w], size)
    return _fonts[k]


WHITE, RED, AMBER, TEAL, BLUE = (255, 255, 255), (255, 48, 64), (255, 168, 40), (64, 214, 230), (70, 170, 255)
INK = (4, 10, 18)


def clamp(x, a=0., b=1.): return max(a, min(b, x))
def lin(t, a, b): return clamp((t - a) / (b - a)) if b != a else float(t >= a)
def ease_out(k): return 1 - (1 - k) ** 3
def ease_io(k): return 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2
def back(k, s=1.6): k -= 1; return 1 + k * k * ((s + 1) * k + s)
def mixc(a, b, k): return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ------------------------------------------------------------------ the power unit photo, cut into parts
S, OX, OY = 1.1, 32, 500          # img0 -> canvas (leaves y 1340-1480 for the subtitles)
POLY = {  # img0 pixel polygons (hand-traced)
    'airbox': [(268, 95), (280, 70), (305, 62), (340, 68), (365, 90), (400, 92), (440, 100), (475, 125), (500, 160), (525, 200),
               (548, 240), (552, 262), (530, 285), (495, 300), (470, 320), (455, 345), (430, 345), (400, 335), (370, 310),
               (345, 290), (325, 250), (310, 235), (300, 215), (280, 160), (268, 125)],
    'ex_l': [(150, 395), (200, 380), (240, 400), (275, 430), (310, 470), (335, 500), (355, 520), (380, 548), (395, 580), (402, 603),
             (420, 615), (450, 618), (480, 590), (520, 550), (545, 525), (562, 536), (545, 562), (510, 602), (470, 642), (440, 662),
             (400, 664), (370, 652), (345, 642), (300, 627), (240, 617), (190, 617), (150, 602), (125, 562), (108, 520), (113, 460), (128, 420)],
    'ex_r': [(555, 100), (600, 72), (650, 58), (700, 57), (745, 68), (785, 95), (810, 140), (812, 195), (800, 240), (780, 280), (780, 320),
             (770, 360), (745, 385), (705, 405), (680, 410), (655, 400), (645, 385), (665, 365), (700, 350), (722, 330), (700, 320),
             (670, 330), (640, 315), (625, 280), (600, 240), (575, 190), (560, 150)],
    'turbo': [(505, 420), (545, 385), (590, 365), (640, 380), (680, 400), (700, 430), (695, 470), (730, 510), (790, 590), (803, 612),
              (780, 640), (752, 662), (735, 650), (700, 600), (655, 555), (615, 545), (575, 530), (545, 515), (515, 490), (500, 455)],
}
ORDER = ['ex_l', 'airbox', 'ex_r', 'turbo']
DELTA = {'airbox': (-40, -230), 'ex_l': (-150, 90), 'ex_r': (150, -150), 'turbo': (140, 110)}
P_V6, P_MGUH, P_MGUK, P_TURBO = (330, 300), (585, 455), (440, 470), (640, 470)   # img0 points (illustrative for the motors)


def to_canvas(p, d=(0, 0)): return (OX + S * p[0] + d[0], OY + S * p[1] + d[1])


def cutout(img):
    """alpha = not the white studio background (flood-filled from the border + enclosed white gaps)"""
    a = np.asarray(img).astype(int)
    white = (a.min(2) > 228) & (a.max(2) - a.min(2) < 22)
    m = Image.fromarray(np.uint8(white) * 255).copy()  # fromarray images can be read-only views; floodfill needs its own pixels
    for seed in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1), (470, 545), (440, 590), (600, 590),
                 (640, 330), (130, 330)]:
        if m.getpixel(seed) == 255:
            ImageDraw.floodfill(m, seed, 128)
    bg = np.asarray(m) == 128
    al = Image.fromarray(np.uint8(~bg) * 255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.8))
    return al


class Unit:
    def __init__(self, path):
        im = Image.open(path).convert('RGB')
        al = cutout(im)
        size = (round(im.width * S), round(im.height * S))
        im = im.resize(size, Image.LANCZOS)
        im = Image.fromarray(np.uint8(np.clip((np.asarray(im, float) / 255) ** 1.08 * 255 * 1.04, 0, 255)))  # a touch more contrast
        al = al.resize(size, Image.LANCZOS)
        self.size = size
        taken = Image.new('L', size, 0); self.parts = {}
        for n in ORDER:
            pm = Image.new('L', size, 0); ImageDraw.Draw(pm).polygon([(x * S, y * S) for x, y in POLY[n]], fill=255)
            pm = ImageChops.subtract(pm, taken); taken = ImageChops.lighter(taken, pm)
            pm = pm.filter(ImageFilter.GaussianBlur(.7))
            a = ImageChops.multiply(al, pm)
            bb = a.getbbox(); rgba = im.copy(); rgba.putalpha(a); rgba = rgba.crop(bb)
            self.parts[n] = (rgba, bb[:2], self._glow(rgba))
        base_a = ImageChops.multiply(al, ImageChops.invert(taken.filter(ImageFilter.GaussianBlur(.7))))
        base = im.copy(); base.putalpha(base_a)
        # empty slots left behind by the parts: dark recess with a teal outline
        holes = ImageChops.multiply(al, taken)
        slot = Image.new('RGBA', size, (10, 16, 24, 0)); slot.putalpha(holes.point(lambda v: int(v * .92)))
        edge = holes.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3)).point(lambda v: min(255, v * 3))
        line = Image.new('RGBA', size, TEAL + (0,)); line.putalpha(edge.point(lambda v: int(v * .55)))
        slot = Image.alpha_composite(slot, line)
        self.base = Image.alpha_composite(slot, base)
        self.base_glow = self._glow(self.base, 26)
        self.full_alpha = al

    @staticmethod
    def _glow(rgba, r=14):
        """soft silhouette used for rim-light / highlight halos (alpha only, padded by r*2)"""
        pad = r * 2
        a = Image.new('L', (rgba.width + 2 * pad, rgba.height + 2 * pad), 0); a.paste(rgba.split()[3], (pad, pad))
        return a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(r)), pad

    def draw(self, canvas, explode, dim, hl=None, hl_col=AMBER, hl_k=0.0, rim=.35):
        """explode: {part: 0..1}, dim: {part|'base': brightness}, hl: part to halo"""
        def put(rgba, xy, b):
            if b < .999:
                arr = np.asarray(rgba).astype(np.float32); arr[..., :3] *= b
                rgba = Image.fromarray(np.uint8(arr))
            canvas.alpha_composite(rgba, (int(xy[0]), int(xy[1])))

        def halo(gl, xy, col, k):
            g, pad = gl
            lay = Image.new('RGBA', g.size, col + (0,)); lay.putalpha(g.point(lambda v: int(v * k)))
            canvas.alpha_composite(lay, (int(xy[0] - pad), int(xy[1] - pad)))
        if rim > 0:
            halo(self.base_glow, (OX, OY), (40, 120, 150), rim)
        put(self.base, (OX, OY), dim.get('base', 1))
        for n in ORDER:
            rgba, (bx, by), gl = self.parts[n]
            e = explode.get(n, 0); dx, dy = DELTA[n]
            xy = (OX + bx + dx * e, OY + by + dy * e)
            if n == hl and hl_k > 0:
                halo(gl, xy, hl_col, hl_k)
            elif rim > 0 and e > .02:
                halo(gl, xy, (40, 120, 150), rim * e)
            put(rgba, xy, dim.get(n, dim.get('base', 1)))


# ------------------------------------------------------------------ drawing helpers
def text(d, xy, s, size, col, w='black', a=1.0, anchor='la', stroke=0):
    if a <= 0:
        return
    d.text(xy, s, font=font(w, size), fill=col + (int(255 * clamp(a)),), anchor=anchor,
           stroke_width=stroke, stroke_fill=INK + (int(220 * clamp(a)),))


def title_block(d, t, t0, lines, x=70, y=210, t1=None):
    """kinetic title: each line rises + fades in 70 ms after the previous; fades out at t1"""
    for i, (s, size, col, w) in enumerate(lines):
        k = ease_out(lin(t, t0 + i * .07, t0 + i * .07 + .28))
        if t1 is not None:
            k *= 1 - lin(t, t1 - .15, t1)
        text(d, (x, y + (1 - k) * 30), s, size, col, w, k, stroke=2 if size > 40 else 0)
        y += int(size * 1.08) + 4


def callout(d, p, lab, col, k, sub=None, size=58, side=1, length=150, ring=14, pulse=0.0):
    """dot + ring at p, elbow leader, label; k = 0..1 reveal"""
    if k <= 0:
        return
    x, y = p; a = clamp(k * 1.5)
    r = ring * (1 + .25 * pulse)
    d.ellipse([x - r, y - r, x + r, y + r], outline=col + (int(255 * a),), width=4)
    d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=col + (int(255 * a),))
    kk = ease_out(clamp(k * 1.3))
    ex, ey = x + side * 50 * kk, y - 50 * kk
    lx = ex + side * length * kk
    d.line([(x + side * r * .7, y - r * .7), (ex, ey), (lx, ey)], fill=col + (int(255 * a),), width=3)
    if k > .4:
        ka = lin(k, .4, 1)
        anchor = 'ls' if side > 0 else 'rs'
        text(d, (lx + side * 6, ey - 10), lab, size, col, 'black', ka, anchor=anchor, stroke=3)
        if sub:
            text(d, (lx + side * 6, ey + 34), sub, 28, (230, 236, 242), 'semi', ka, anchor=anchor, stroke=2)


def glow_layer(size, fn, r=8):
    """draw with fn(draw) on a transparent layer, return sharp + blurred copy for a bloom"""
    lay = Image.new('RGBA', size, (0, 0, 0, 0)); fn(ImageDraw.Draw(lay))
    bl = lay.filter(ImageFilter.GaussianBlur(r))
    return Image.alpha_composite(bl, Image.alpha_composite(bl, lay))


def flow(d, pts, t, col, n=14, speed=.6, size=7, a=1.0, phase=0.0):
    """particles travelling along a polyline"""
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; L = sum(seg)
    for j in range(n):
        u = ((t * speed + j / n + phase) % 1.0) * L
        for i, sl in enumerate(seg):
            if u <= sl:
                f = u / sl; x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f; y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
                fade = min(1, u / 40, (L - u) / 40)
                r = size * (.6 + .4 * math.sin(j * 1.7 + t * 9) ** 2)
                d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(255 * a * fade),)); break
            u -= sl


def wheel(d, c, R, ang, col, a=1.0, blades=9):
    """compressor wheel icon: hub + curved blades rotating by ang (rad)"""
    x, y = c
    d.ellipse([x - R, y - R, x + R, y + R], outline=col + (int(200 * a),), width=4)
    for b in range(blades):
        th = ang + b * 2 * math.pi / blades
        pts = [(x + R * .22 * math.cos(th + s * .9) * (1 + s * 3.4), y + R * .22 * math.sin(th + s * .9) * (1 + s * 3.4))
               for s in np.linspace(0, 1, 6)]
        d.line(pts, fill=col + (int(255 * a),), width=5)
    d.ellipse([x - R * .18, y - R * .18, x + R * .18, y + R * .18], fill=col + (int(255 * a),))


def battery(d, c, k, level, col=BLUE, a=1.0, label=True):
    x, y = c; w, h = 150, 70
    if a <= 0:
        return
    al = int(255 * a)
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], 10, outline=col + (al,), width=4)
    d.rectangle([x + w / 2, y - 14, x + w / 2 + 10, y + 14], fill=col + (al,))
    d.rectangle([x - w / 2 + 8, y - h / 2 + 8, x - w / 2 + 8 + (w - 16) * clamp(level), y + h / 2 - 8], fill=col + (int(al * .85),))
    if label:
        text(d, (x, y + h / 2 + 14), 'BATTERY', 28, (230, 236, 242), 'semi', a, anchor='mt')


def camera(img, cx, cy, z):
    """zoom z >= 1 about (cx, cy) on the canvas, clamped to the frame"""
    if z <= 1.001:
        return img, (lambda p: p)
    w, h = OW / z, OH / z
    x0 = clamp(cx - w / 2, 0, OW - w); y0 = clamp(cy - h / 2, 0, OH - h)
    out = img.transform((OW, OH), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
    return out, (lambda p: ((p[0] - x0) * z, (p[1] - y0) * z))


def zoom_blur(img, amount, n=6):
    if amount < .004:
        return img
    acc = np.asarray(img, np.float32).copy()
    for i in range(1, n):
        s = 1 + amount * i / (n - 1); w, h = OW / s, OH / s
        acc += np.asarray(img.transform((OW, OH), Image.EXTENT, ((OW - w) / 2, (OH - h) / 2, (OW + w) / 2, (OH + h) / 2), Image.BILINEAR), np.float32)
    return Image.fromarray(np.uint8(acc / n))


def rgb_split(img, px):
    if px < 1:
        return img
    r, g, b = img.split()
    return Image.merge('RGB', (ImageChops.offset(r, -px, 0), g, ImageChops.offset(b, px, 0)))


# ------------------------------------------------------------------ backgrounds
def studio_bg():
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    r = np.sqrt(((xx - 540) / 900) ** 2 + ((yy - 900) / 1100) ** 2)
    v = np.clip(1 - r, 0, 1) ** 1.6
    out = np.stack([6 + 18 * v, 12 + 34 * v, 20 + 46 * v], -1)
    # perspective floor grid under the unit
    floor = yy > 1300
    gy = (yy - 1300) / 620
    lines = (np.abs(((xx - 540) / np.maximum(gy, .02)) % 160 - 80) > 77) | (np.abs((np.sqrt(np.maximum(gy, 0)) * 9) % 1 - .5) > .46)
    out += (floor & lines)[..., None] * np.array([10, 40, 50]) * np.clip(1 - gy, 0, 1)[..., None] * .8
    noise = np.random.default_rng(3).normal(0, 2.2, (OH, OW, 1))
    return Image.fromarray(np.uint8(np.clip(out + noise, 0, 255)))


def turbo_scene(path):
    """the Garrett e-turbo photo as a 1080-wide card over a blurred, darkened cover copy"""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im, np.float32) / 255
    a = np.clip((a - .5) * 1.18 + .5, 0, 1) ** 1.05                       # contrast
    tint = np.array([.92, 1.0, 1.06]); a = np.clip(a * tint, 0, 1)        # cool steel
    im = Image.fromarray(np.uint8(a * 255))
    cov = im.resize((round(im.width * OH / im.height), OH), Image.BILINEAR)
    cov = cov.crop(((cov.width - OW) // 2 + 220, 0, (cov.width - OW) // 2 + 220 + OW, OH)).filter(ImageFilter.GaussianBlur(28))
    cov = Image.fromarray(np.uint8(np.asarray(cov, np.float32) * .28))
    return im, cov


CARD_Y, CARD_W = 540, OW
# Garrett photo points (img1 px): turbine side under the heat blanket, compressor inlet, shaft between them
G_TURB, G_COMP = (318, 172), (396, 256)
G_MOTOR = (G_TURB[0] + (G_COMP[0] - G_TURB[0]) * .5, G_TURB[1] + (G_COMP[1] - G_TURB[1]) * .5)


# ------------------------------------------------------------------ the film
class Film:
    def __init__(self):
        self.unit = Unit(os.path.join(ROOT, 'photos/pu/img0.jpeg'))
        self.bg = studio_bg()
        self.gimg, self.gcov = turbo_scene(os.path.join(ROOT, 'photos/pu/img1.jpeg'))
        self.rain = np.random.default_rng(9).uniform(0, 1, (160, 3))

    # ---------------- power unit scenes (0 - 6.7, 15.0 - 31)
    def unit_frame(self, t):
        U = self.unit
        cv = self.bg.copy().convert('RGBA')
        # explode amounts
        if t < 14.9:
            ex = {'airbox': back(lin(t, 1.75, 2.35)), 'ex_l': back(lin(t, 2.35, 2.9)), 'ex_r': back(lin(t, 2.45, 3.0)),
                  'turbo': back(lin(t, 3.45, 4.0))}
        else:  # snap back together for the second half
            k = 1 - ease_io(lin(t, 14.95, 15.4)); ex = {n: k for n in ORDER}
        dim = {}
        foc = ease_io(lin(t, 4.3, 5.4)) * (1 - lin(t, 14.9, 15.2))
        for n in ('base', 'airbox', 'ex_l', 'ex_r'):
            dim[n] = 1 - .7 * foc
        dim['turbo'] = 1.0
        hl, hl_k, hl_col = None, 0, AMBER
        if 3.45 <= t < 6.7:
            hl, hl_k = 'turbo', .55 * lin(t, 3.5, 3.9) + .25 * foc
        # lazy turbo -> MGU-K -> wet -> lock-out: the unit stays together and darkens under the data
        late = t >= 15.0
        if late:
            k_wet = ease_io(lin(t, 21.0, 21.6))
            for n in ('base', 'airbox', 'ex_l', 'ex_r'):
                dim[n] = 1 - .25 * lin(t, 17.4, 18.0) - .45 * k_wet
            dim['turbo'] = 1 - .55 * k_wet
            if t < 17.6:
                hl, hl_k, hl_col = 'turbo', (.6 + .25 * math.sin(t * 7)) * lin(t, 15.3, 15.7) * (1 - .6 * lin(t, 16.2, 17.4)), AMBER
        U.draw(cv, ex, dim, hl, hl_col, hl_k, rim=.35 if not late else .35 * (1 - .5 * lin(t, 21, 21.6)))

        # light sweep across the unit on the reveal
        if t < 1.4:
            sweep = Image.new('L', (OW, OH), 0); sx = -400 + 1900 * ease_io(lin(t, .15, 1.25))
            ImageDraw.Draw(sweep).polygon([(sx, 420), (sx + 140, 420), (sx - 260, 1320), (sx - 400, 1320)], fill=90)
            sweep = ImageChops.multiply(sweep.filter(ImageFilter.GaussianBlur(30)), self._unit_alpha())
            cv.alpha_composite(Image.merge('RGBA', (*Image.new('RGB', (OW, OH), (220, 240, 255)).split(), sweep)))

        # camera
        cz, cx, cy = 1.0, 540, 900
        if t < 1.4:
            cz = 1.12 - .12 * ease_out(lin(t, 0, 1.4))
        tc = to_canvas(P_TURBO, DELTA['turbo'])
        if 4.2 <= t < 6.8:
            k = ease_io(lin(t, 4.3, 5.6)); cz = 1 + .55 * k + .25 * ease_io(lin(t, 6.2, 6.7))
            cx, cy = 540 + (tc[0] - 540) * k, 900 + (tc[1] - 900) * k
        if t >= 15:
            cz = 1.0 + .04 * lin(t, 15.4, 31)
        frame, M = camera(cv.convert('RGB'), cx, cy, cz)
        if t < .45:
            frame = zoom_blur(frame, .18 * (1 - lin(t, 0, .45)))
        if 6.25 <= t < 6.8:
            frame = zoom_blur(frame, .25 * lin(t, 6.25, 6.7))
        ov = Image.new('RGBA', (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)

        if t < 6.8:
            ta = 1 - lin(t, 4.1, 4.4)
            title_block(d, t, .05, [('INSIDE THE POWER UNIT', 34, AMBER, 'semi'), ('V6 TURBO', 100, WHITE, 'black'),
                                    ('HYBRID', 100, TEAL, 'black')], t1=1.8)
            v6 = M(to_canvas(P_V6))
            callout(d, v6, '1.6L V6', WHITE, lin(t, 1.45, 1.9) * ta, 'ENGINE', side=-1, length=60, size=54)
            ab = M(to_canvas((420, 150), (DELTA['airbox'][0] * ex['airbox'], DELTA['airbox'][1] * ex['airbox'])))
            callout(d, ab, 'AIRBOX', (200, 210, 220), lin(t, 2.2, 2.6) * ta, size=40, side=1, length=90, ring=10)
            el = M(to_canvas((230, 560), (DELTA['ex_l'][0] * ex['ex_l'], DELTA['ex_l'][1] * ex['ex_l'])))
            callout(d, el, 'EXHAUST', (200, 210, 220), lin(t, 2.8, 3.2) * ta, size=40, side=1, length=40, ring=10)
            tb = M(to_canvas(P_TURBO, (DELTA['turbo'][0] * ex['turbo'], DELTA['turbo'][1] * ex['turbo'])))
            callout(d, (tb[0] + 60 * (cz - 1), tb[1] + 80 * (cz - 1)), 'TURBO', AMBER, lin(t, 3.6, 4.0) * (1 - lin(t, 5.5, 5.75)),
                    size=56, side=-1, length=90)
            if t >= 4.4:
                title_block(d, t, 4.45, [('HIDDEN ON THE TURBO SHAFT…', 40, WHITE, 'semi')], y=230, t1=5.8)
            if t >= 5.75:  # MGU-H slam
                p = M(to_canvas(P_MGUH, (DELTA['turbo'][0] * ex['turbo'], DELTA['turbo'][1] * ex['turbo'])))
                k = lin(t, 5.75, 5.95)
                lay = glow_layer((OW, OH), lambda g: (g.ellipse([p[0] - 40, p[1] - 40, p[0] + 40, p[1] + 40], outline=TEAL + (255,), width=8),
                                                       g.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=TEAL + (255,))), 10)
                lay.putalpha(lay.split()[3].point(lambda v: int(v * k)))
                ov.alpha_composite(lay)
                sc = 1 + .5 * (1 - ease_out(k))
                text(d, (540, 330), 'MGU-H', int(150 * sc), TEAL, 'black', k, anchor='mm', stroke=4)
                text(d, (540, 430), 'MOTOR GENERATOR UNIT · HEAT', 34, WHITE, 'semi', lin(t, 5.95, 6.2), anchor='mm', stroke=2)
        else:
            self._late_overlay(d, ov, t, M)
        frame = frame.convert('RGBA'); frame.alpha_composite(ov)
        out = frame.convert('RGB')
        if t < .2:  # out of the white flash from the punch-in
            out = Image.blend(out, Image.new('RGB', out.size, (235, 242, 255)), 1 - lin(t, 0, .2))
        if 6.55 <= t < 6.8:
            out = Image.blend(out, Image.new('RGB', out.size, (235, 242, 255)), .85 * lin(t, 6.55, 6.7))
        if 28.1 <= t < 31:  # zero kW: red wash + glitch
            k = 1 - lin(t, 28.1, 28.6)
            out = Image.blend(out, Image.new('RGB', out.size, (120, 0, 10)), .35 * k + .12)
            if (28.1 <= t < 28.45) or (29.4 <= t < 29.6):
                out = rgb_split(out, 16)
        return out

    def _unit_alpha(self):
        if not hasattr(self, '_ua'):
            a = Image.new('L', (OW, OH), 0); a.paste(self.unit.full_alpha.resize(self.unit.size), (OX, OY)); self._ua = a
        return self._ua

    def _late_overlay(self, d, ov, t, M):
        """15 s onwards: lazy turbo, MGU-K, wet mode, energy lock-out"""
        tb = M(to_canvas(P_TURBO)); mk = M(to_canvas(P_MGUK))
        # --- lazy turbo
        if t < 21.0:
            title_block(d, t, 15.1, [('FORMATION LAP · IN THE RAIN', 34, AMBER, 'semi'), ('SLOW CAR,', 100, WHITE, 'black'),
                                     ('LAZY TURBO', 100, AMBER, 'black')], t1=17.5)
            callout(d, tb, 'TURBO', AMBER, lin(t, 15.4, 15.8) * (1 - lin(t, 17.3, 17.6)), 'SPINNING DOWN', side=1, length=30, size=52)
            # rpm gauge with a wheel that slows
            k = ease_io(lin(t, 15.5, 17.2)); rpm = 125000 - 85000 * k
            ga = lin(t, 15.3, 15.6) * (1 - lin(t, 17.4, 17.7))
            if ga > 0:
                spin = getattr(self, '_ang', 0.0); self._ang = spin + (rpm / 125000) * 1.1
                lay = glow_layer((OW, OH), lambda g: wheel(g, (180, 1620), 64, self._ang, AMBER, ga), 6); ov.alpha_composite(lay)
                text(d, (290, 1570), f'{int(rpm):,}', 80, WHITE, 'black', ga, stroke=2)
                text(d, (290, 1665), 'TURBO RPM', 28, AMBER, 'semi', ga)
                d.rounded_rectangle([290, 1710, 990, 1724], 7, fill=(255, 255, 255, int(40 * ga)))
                d.rounded_rectangle([290, 1710, 290 + 700 * rpm / 125000, 1724], 7, fill=AMBER + (int(255 * ga),))
            # MGU-K takes over
            if t >= 17.4:
                title_block(d, t, 17.45, [('SO THE CAR LEANS ON', 44, WHITE, 'semi'), ('THE MGU-K', 112, TEAL, 'black')], t1=21.0)
                bt = (540, 1620)
                ka = lin(t, 17.5, 17.9) * (1 - lin(t, 20.8, 21.0))
                lay = glow_layer((OW, OH), lambda g: (battery(g, bt, 0, .8, BLUE, ka, label=False),
                                                       flow(g, [(bt[0], bt[1] - 40), (bt[0], mk[1] + 160), (mk[0], mk[1] + 30)], t, BLUE, 12, .9, 7, ka)), 8)
                ov.alpha_composite(lay)
                text(d, (bt[0], bt[1] + 50), 'BATTERY', 28, (230, 236, 242), 'semi', ka, anchor='mt')
                pulse = math.sin(t * 8) ** 2
                callout(d, mk, 'MGU-K', TEAL, lin(t, 18.2, 18.7) * (1 - lin(t, 20.8, 21.0)), 'ELECTRIC MOTOR', side=1, length=60, size=60,
                        ring=18, pulse=pulse)
        # --- wet mode: 348 -> 250 kW
        if 21.0 <= t < 28.1 or t >= 28.1:
            k_in = lin(t, 21.1, 21.4)
            if t < 24.4:
                title_block(d, t, 21.15, [('STEP 02 · RAIN SETTINGS', 34, AMBER, 'semi'), ('WET MODE', 112, WHITE, 'black'),
                                          ('caps how hard the battery can push', 40, (220, 228, 236), 'light')], t1=24.4)
            # rain streaks
            ra = .55 * k_in
            for i, (x, y, s) in enumerate(self.rain):
                yy = (y * 2200 + t * (1500 + 900 * s)) % 2200 - 140; xx = (x * 1300 + yy * .18) % 1300 - 110
                d.line([(xx, yy), (xx + 14, yy + 70 + 50 * s)], fill=(190, 215, 235, int(255 * ra * (.25 + .4 * s))), width=2)
            kw = 348 - 98 * ease_io(lin(t, 22.3, 23.6))
            if t >= 28.1:
                kw = 250 * (1 - ease_out(lin(t, 28.1, 28.45)))
            col = TEAL if t < 28.1 else RED
            ca = k_in
            text(d, (70, 950), f'{int(round(kw))}', 220, col, 'black', ca, stroke=3)
            text(d, (70 + font('black', 220).getlength(f'{int(round(kw))}') + 20, 1120), 'kW', 70, col, 'semi', ca, anchor='ls')
            text(d, (74, 1180), 'MGU-K DEPLOYMENT', 30, (220, 228, 236), 'semi', ca)
            bx0, bx1, by = 74, 1000, 1240
            d.rounded_rectangle([bx0, by, bx1, by + 18], 9, fill=(255, 255, 255, int(40 * ca)))
            d.rounded_rectangle([bx0, by, bx0 + (bx1 - bx0) * kw / 350, by + 18], 9, fill=col + (int(255 * ca),))
            if t >= 22.2:
                cap_x = bx0 + (bx1 - bx0) * 250 / 350; a = lin(t, 22.2, 22.5)
                d.line([(cap_x, by - 20), (cap_x, by + 38)], fill=AMBER + (int(255 * a),), width=4)
                text(d, (cap_x, by + 44), 'WET CAP 250 kW', 26, AMBER, 'semi', a, anchor='mt')
        # --- energy-limit lock-out
        if 24.4 <= t:
            title_block(d, t, 24.45, [('STEP 03 · SEPANG ENERGY LIMIT', 34, AMBER, 'semi'), ('ENERGY LIMIT', 104, WHITE, 'black')])
            if t >= 26.3:
                k = lin(t, 26.3, 26.5); sc = 1 + .4 * (1 - ease_out(k))
                text(d, (70, 362 + 56), 'LOCK-OUT', int(112 * sc), RED, 'black', k, anchor='lm', stroke=3)
            chips = ['THROTTLE', 'TORQUE MAP', 'ENERGY LIMIT', 'MGU-K']
            x, y = 70, 560
            for i, c in enumerate(chips):
                f = font('semi', 26); w = f.getlength(c) + 30
                if x + w > 1030:
                    x, y = 70, y + 78
                on = lin(t, 24.7 + i * .35, 24.9 + i * .35)
                bad = c == 'ENERGY LIMIT' and t >= 26.3
                dead = c == 'MGU-K' and t >= 26.3
                colc = RED if bad else ((120, 130, 140) if dead else TEAL)
                d.rounded_rectangle([x, y, x + w, y + 56], 12, outline=colc + (int(255 * on),), width=3,
                                    fill=(colc + (int(70 * on),)) if bad else (0, 0, 0, int(120 * on)))
                text(d, (x + w / 2, y + 28), c, 26, WHITE if not dead else (150, 155, 160), 'semi', on, anchor='mm')
                if bad:
                    k = lin(t, 26.3, 26.45); cx, cy = x + w - 4, y + 2
                    d.line([(cx - 16 * k, cy - 16 * k), (cx + 16 * k, cy + 16 * k)], fill=RED + (255,), width=7)
                    d.line([(cx - 16 * k, cy + 16 * k), (cx + 16 * k, cy - 16 * k)], fill=RED + (255,), width=7)
                if i < len(chips) - 1:
                    nx = x + w + 8
                    if nx + 36 < 1030:
                        text(d, (nx + 4, y + 28), '→', 34, (200, 210, 220) if not (bad or dead) else RED, 'semi', on, anchor='lm')
                        x = nx + 38
                    else:
                        x = 1100
            if t >= 29.35:
                k = lin(t, 29.35, 29.55); sc = 1 + .5 * (1 - ease_out(k))
                text(d, (540, 1600), 'THROTTLE IGNORED', int(76 * sc), RED, 'black', k, anchor='mm', stroke=3)

    # ---------------- turbo photo scene (6.7 - 15.0)
    def turbo_frame(self, t):
        im = self.gcov.copy().convert('RGBA')
        k_in = lin(t, 6.7, 6.95)
        z = 1.0 + .12 * ease_io(lin(t, 6.7, 14.9))
        # card: crop the photo around the motor and scale to 1080 wide
        gw, gh = self.gimg.size; w = gw / z; h = gh / z
        x0 = clamp(G_MOTOR[0] - w / 2, 0, gw - w); y0 = clamp(G_MOTOR[1] - h / 2, 0, gh - h)
        ch = round(CARD_W * gh / gw)
        card = self.gimg.transform((CARD_W, ch), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)
        gone = lin(t, 13.85, 14.2)
        if t >= 12.0:  # 2026: drain the colour
            g = card.convert('L').convert('RGB'); card = Image.blend(card, g, lin(t, 12.0, 12.6))
            card = Image.fromarray(np.uint8(np.asarray(card, np.float32) * (1 - .3 * gone)))
        card = card.convert('RGBA')
        m = Image.new('L', card.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, card.width - 1, card.height - 1], 0, fill=255)
        im.alpha_composite(card, (0, CARD_Y))

        def P(p):  # photo px -> frame
            return ((p[0] - x0) / w * CARD_W, CARD_Y + (p[1] - y0) / h * ch)
        tu, co, mo = P(G_TURB), P(G_COMP), P(G_MOTOR)
        ov = Image.new('RGBA', (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        # card frame lines
        d.line([(0, CARD_Y), (OW, CARD_Y)], fill=TEAL + (int(140 * k_in),), width=3)
        d.line([(0, CARD_Y + ch), (OW, CARD_Y + ch)], fill=TEAL + (int(140 * k_in),), width=3)
        text(d, (OW - 40, CARD_Y + ch + 14), 'GARRETT E-TURBO · MGU-H TECH ON THE ROAD', 22, (190, 200, 210), 'semi', k_in, anchor='ra')

        dead = t >= 12.0
        mcol = mixc(TEAL, RED, lin(t, 12.6, 13.2)) if dead else TEAL
        # x-ray cutaway: shaft + motor coils between turbine and compressor
        vx, vy = co[0] - tu[0], co[1] - tu[1]; L = math.hypot(vx, vy); ux, uy = vx / L, vy / L; nx, ny = -uy, ux
        ka = lin(t, 7.0, 7.4) * (1 - gone)

        def cut(g):
            ext = 70
            g.line([(tu[0] - ux * ext, tu[1] - uy * ext), (co[0] + ux * 30, co[1] + uy * 30)], fill=(220, 235, 245, int(230 * ka)), width=6)
            for i in range(7):
                f = .3 + .4 * i / 6; cx, cy = tu[0] + vx * f, tu[1] + vy * f; r = 46
                g.ellipse([cx - r * .45, cy - r, cx + r * .45, cy + r], outline=mcol + (int(255 * ka),), width=4)
            g.ellipse([tu[0] - 50, tu[1] - 50, tu[0] + 50, tu[1] + 50], outline=AMBER + (int(200 * ka),), width=4)
        ov.alpha_composite(glow_layer((OW, OH), cut, 9))
        d = ImageDraw.Draw(ov)
        lab_k = lin(t, 7.3, 7.7) * (1 - lin(t, 11.6, 11.9))
        callout(d, tu, 'TURBINE', AMBER, lab_k, 'HOT EXHAUST SPINS IT', side=-1, length=40, size=46, ring=10)
        callout(d, (co[0] + 10, co[1] + 60), 'COMPRESSOR', (220, 230, 240), lab_k, 'PUSHES AIR INTO THE V6', side=1, length=20, size=46, ring=10)
        # MGU-H label under the card
        mk = lin(t, 7.0, 7.3)
        ly0 = CARD_Y + ch + 34
        text(d, (70, ly0), 'MGU-H', 116, mcol, 'black', mk, stroke=3)
        sa = mk * (1 - lin(t, 11.6, 11.9))
        text(d, (505, ly0 + 32), 'ELECTRIC MOTOR', 26, (220, 228, 236), 'semi', sa)
        text(d, (505, ly0 + 66), 'ON THE TURBO SHAFT', 26, (220, 228, 236), 'semi', sa)
        # harvest: exhaust in (orange) -> electricity out (blue) to the battery
        bt = (940, CARD_Y + ch + 90)
        h_a = lin(t, 7.4, 7.7) * (1 - lin(t, 8.8, 9.1))
        b_a = lin(t, 8.9, 9.2) * (1 - lin(t, 11.6, 11.9))
        lay = Image.new('RGBA', (OW, OH), (0, 0, 0, 0)); g = ImageDraw.Draw(lay)
        if h_a > 0:
            flow(g, [(-40, tu[1] - 120), (tu[0] - 120, tu[1] - 60), tu], t, (255, 130, 30), 18, 1.1, 9, h_a)
            flow(g, [mo, (mo[0] + 120, mo[1] + 140), (bt[0], CARD_Y + ch - 10), (bt[0], bt[1] - 40)], t, BLUE, 16, .9, 8, h_a, .3)
        if b_a > 0:
            flow(g, [(bt[0], bt[1] - 40), (bt[0], CARD_Y + ch - 10), (mo[0] + 120, mo[1] + 140), mo], t, BLUE, 16, 1.2, 8, b_a)
            spin = 6.0 + 30 * lin(t, 9.0, 10.3)
            wheel(g, co, 70, t * spin, TEAL, b_a * .9, blades=8)
        battery(g, bt, 0, .3 + .5 * lin(t, 7.6, 8.9) - .3 * lin(t, 9.0, 10.5), BLUE, max(h_a, b_a) * (1 - gone), label=False)
        bl = lay.filter(ImageFilter.GaussianBlur(7)); ov.alpha_composite(bl); ov.alpha_composite(lay)
        d = ImageDraw.Draw(ov)
        text(d, (bt[0], bt[1] + 50), 'BATTERY', 28, (230, 236, 242), 'semi', max(h_a, b_a), anchor='mt')
        # titles
        title_block(d, t, 7.0, [('1 · HARVEST', 34, AMBER, 'semi'), ('EXHAUST HEAT', 92, (255, 150, 60), 'black'),
                                ('→ ELECTRICITY', 92, BLUE, 'black')], t1=8.95)
        title_block(d, t, 9.0, [('2 · BOOST', 34, AMBER, 'semi'), ('SPINS THE TURBO', 92, WHITE, 'black'),
                                ('UP INSTANTLY', 92, TEAL, 'black')], t1=10.85)
        if 10.85 <= t < 11.9:
            k = lin(t, 10.85, 11.0); sc = 1 + .6 * (1 - ease_out(k))
            text(d, (540, 380), 'ZERO LAG', int(150 * sc), TEAL, 'black', k * (1 - lin(t, 11.7, 11.9)), anchor='mm', stroke=4)
        if t >= 12.0:
            title_block(d, t, 12.05, [('2026 RULES', 40, RED, 'black'), ('NO MORE', 96, WHITE, 'black'), ('MGU-H', 140, RED, 'black')])
            if t >= 13.85:  # big red X over the motor
                k = ease_out(lin(t, 13.85, 14.0)); r = 150 * k
                xl = glow_layer((OW, OH), lambda g: (g.line([(mo[0] - r, mo[1] - r), (mo[0] + r, mo[1] + r)], fill=RED + (255,), width=26),
                                                     g.line([(mo[0] - r, mo[1] + r), (mo[0] + r, mo[1] - r)], fill=RED + (255,), width=26)), 12)
                ov.alpha_composite(xl)
                text(d, (70, 1540), 'TURBO LAG IS BACK', 54, WHITE, 'black', lin(t, 14.05, 14.3), stroke=2)
            # strike through the MGU-H label
            k = ease_out(lin(t, 13.85, 14.05)); ly = CARD_Y + ch + 34 + 70
            d.line([(60, ly), (60 + 400 * k, ly)], fill=RED + (255,), width=12)
        im.alpha_composite(ov)
        out = im.convert('RGB')
        if t < 6.95:
            out = Image.blend(out, Image.new('RGB', out.size, (235, 242, 255)), .9 * (1 - lin(t, 6.7, 6.95)))
        if 13.85 <= t < 14.05:
            out = rgb_split(out, 18)
        if t >= 14.75:  # whip back to the unit
            out = zoom_blur(out, .3 * lin(t, 14.75, 15.0))
        return out

    def frame(self, t):
        return self.turbo_frame(t) if 6.7 <= t < 15.0 else self.unit_frame(t)


def main():
    out = sys.argv[1]
    f = Film()
    if '--sheet' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--sheet') + 1:]]
        fr = [f.frame(t).resize((360, 640)) for t in ts]
        sh = Image.new('RGB', (360 * len(fr), 640))
        for i, im in enumerate(fr):
            sh.paste(im, (360 * i, 0))
        sh.save(out); return
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(round(DUR * FPS)):
        ff.stdin.write(f.frame(i / FPS).tobytes())
    ff.stdin.close(); ff.wait()
    print('wrote', out, DUR, 's')


if __name__ == '__main__':
    main()
