"""Word-by-word 3D subtitles for the voice-over -> a transparent overlay (out/subs.mov, qtrle + alpha).

  render(lines, bands, total, out)
    lines: [(edit time the line starts, line id)] - word timings come from out/vo/<id>.json (tiktok/voice.py)
    bands: [(t0, t1, y)] - vertical centre of the subtitle band per stretch of the edit
  python3 -I tiktok/subs3d.py out/subs_sheet.jpg      # preview sheet of a few lines

Look: extruded block letters (stacked depth copies + drop shadow) with a top-lit gradient face. Each
word flips up into place about its horizontal axis (perspective rotateX with a little overshoot) as it is
spoken, the spoken word pops forward, and the chunk flips away when the next one comes in. Words marked
*like this* in voice.py take the line's emotion colour.
"""
import json
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OW, OH, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOD = os.path.join(ROOT, 'out', 'vo')
FONT = ImageFont.truetype('/usr/share/fonts/opentype/inter/InterDisplay-Black.otf', 92)
INK = (6, 10, 18)
WHITE = (255, 255, 255)
ACCENT = {'excited': (255, 176, 40), 'hype': (255, 206, 40), 'curious': (64, 214, 230), 'warm': (64, 214, 230),
          'tense': (255, 72, 84), 'sad': (120, 168, 255), 'confused': (196, 140, 255)}
DEPTH, STROKE, PAD, GAP = 11, 6, 40, 24
MAX_W, LINE_H = 980, 116


def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out(k): return 1 - (1 - k) ** 3
def ease_in(k): return k ** 3
def back(k, s=2.2): k -= 1; return 1 + k * k * ((s + 1) * k + s)
def mixc(a, b, k): return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


@lru_cache(maxsize=512)
def word_img(txt, col):
    """RGBA block word: shadow, extrusion, outlined gradient face. Returns (image, face width)."""
    x0, y0, x1, y1 = FONT.getbbox(txt, stroke_width=STROKE)
    w, h = x1 - x0 + DEPTH + 2 * PAD, y1 - y0 + DEPTH + 2 * PAD
    org = (PAD - x0, PAD - y0)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text(org, txt, font=FONT, fill=255, stroke_width=STROKE, stroke_fill=255)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh = Image.new('L', (w, h), 0); sh.paste(mask, (DEPTH + 4, DEPTH + 12))
    sh = sh.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * .75))
    im.paste(Image.new('RGBA', (w, h), (0, 0, 0, 255)), (0, 0), sh)
    dark = mixc(col, (0, 0, 0), .78)
    for i in range(DEPTH, 0, -1):                       # extrusion, darker towards the back
        c = mixc(dark, (0, 0, 0), i / DEPTH * .6)
        layer = Image.new('RGBA', (w, h), c + (255,))
        m = Image.new('L', (w, h), 0); m.paste(mask, (int(i * .55), i))
        im.paste(layer, (0, 0), m)
    stroke = Image.new('RGBA', (w, h), INK + (255,)); im.paste(stroke, (0, 0), mask)
    face = Image.new('L', (w, h), 0)
    ImageDraw.Draw(face).text(org, txt, font=FONT, fill=255)
    top = mixc(col, WHITE, .45) if col != WHITE else WHITE
    bot = col if col != WHITE else (196, 210, 224)
    g = np.linspace(0, 1, h)[:, None, None] ** 1.3
    grad = (np.array(top) * (1 - g) + np.array(bot) * g) * np.ones((1, w, 1))
    im.paste(Image.fromarray(np.uint8(grad)).convert('RGBA'), (0, 0), face)
    return im, x1 - x0


def _coeffs(dst, src):
    """PIL PERSPECTIVE coefficients mapping output points dst -> input points src"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]; B += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def rotate_x(im, theta, f=1000.0):
    """tilt about the horizontal centre line; theta > 0 tips the top away from the camera"""
    if abs(theta) < .01:
        return im
    w, h = im.size; cx, cy = w / 2, h / 2
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = []
    for x, y in src:
        X, Y = x - cx, y - cy
        Z = -Y * math.sin(theta); s = f / (f + Z)
        dst.append((cx + X * s, cy + Y * math.cos(theta) * s))
    return im.transform((w, h), Image.PERSPECTIVE, _coeffs(dst, src), Image.BICUBIC)


def chunks(words):
    """group timed words into 1-3 word subtitle chunks, breaking at punctuation"""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) == 3 or sum(len(x['w']) for x in cur) + len(w['w']) > 16):
            out.append(cur); cur = []
        cur.append(w)
        if w['p']:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def set_ends(allc):
    """each chunk holds until its last word is said (+0.35 s) but is gone - flipped away - as the next chunk
    lands, across line boundaries too; word ends include trailing pauses, so the next start wins"""
    allc.sort(key=lambda ce: ce[0][0]['s'])
    for i, (c, _) in enumerate(allc):
        end, ex = c[-1]['e'] + .35, .12
        if i + 1 < len(allc):
            nxt = allc[i + 1][0][0]['s']
            end = max(min(end, nxt - .10), c[-1]['s'] + .06)
            ex = min(.12, max(.04, nxt - .08 - end))       # fast speech: a quicker flip-away
        for w in c:
            w['chunk_end'], w['exit'] = end, ex
    return allc


def load(lines):
    """all chunks on the edit timeline: [(words with absolute s/e, emotion)]"""
    allc = []
    for at, lid in lines:
        d = json.load(open(os.path.join(VOD, lid + '.json')))
        ws = [dict(w, s=w['s'] + at, e=w['e'] + at) for w in d['words']]
        for c in chunks(ws):
            allc.append((c, d['emo']))
    return set_ends(allc)


def draw_chunk(frame, t, c, emo, y):
    t0, tend, exd = c[0]['s'] - .08, c[0]['chunk_end'], c[0]['exit']
    if t < t0 or t > tend + exd:
        return
    acc = ACCENT[emo]
    items = []
    for w in c:
        col = acc if w['emph'] else WHITE
        txt = w['w'].upper()                              # shown text already carries its ? and !
        items.append((w, *word_img(txt, col)))
    # layout: one line, or two balanced lines if too wide
    widths = [fw for _, _, fw in items]
    rows = [items]
    if sum(widths) + GAP * (len(items) - 1) > MAX_W and len(items) > 1:
        k = min(range(1, len(items)), key=lambda j: abs(sum(widths[:j]) - sum(widths[j:])))
        rows = [items[:k], items[k:]]
    ex = clamp((t - tend) / exd)                         # chunk exit
    for r, row in enumerate(rows):
        rw = sum(fw for _, _, fw in row) + GAP * (len(row) - 1)
        x = 540 - rw / 2
        cy = y + (r - (len(rows) - 1) / 2) * LINE_H
        for w, im, fw in row:
            k = (t - (w['s'] - .08)) / .24
            if k <= 0:
                x += fw + GAP; continue
            k = clamp(k)
            theta = (1 - back(k)) * math.radians(88)     # flips up, overshoots a touch, settles
            sc = 1 + .22 * (1 - ease_out(k))
            act = clamp((t - w['s']) / .06) * (1 - clamp((t - w['e'] - .05) / .12))
            sc *= 1 + .1 * act
            lift = -10 * act
            if ex > 0:
                theta -= math.radians(80) * ease_in(ex); sc *= 1 - .1 * ex
            a = clamp(k * 3) * (1 - ex)
            if a <= 0:
                x += fw + GAP; continue
            img = im
            if abs(sc - 1) > .005:
                img = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.BICUBIC)
            img = rotate_x(img, theta)
            if a < 1:
                img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * a)))
            # face centre of this word, scaled about its middle
            fx = x + fw / 2; fy = cy + lift
            frame.alpha_composite(img, (int(fx - img.width / 2 + DEPTH * .3 * sc), int(fy - img.height / 2 + DEPTH * .3 * sc)))
            x += fw + GAP


def render(lines, bands, total, out):
    allc = load(lines)
    band = lambda t: next((y for a, b, y in bands if a <= t < b), 1300)
    n = round(total * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'qtrle', '-pix_fmt', 'argb', out], stdin=subprocess.PIPE)
    blank = bytes(OW * OH * 4)
    for i in range(n):
        t = i / FPS
        live = [(c, e) for c, e in allc if c[0]['s'] - .08 <= t <= c[0]['chunk_end'] + c[0]['exit']]
        if not live:
            ff.stdin.write(blank); continue
        fr = Image.new('RGBA', (OW, OH), (0, 0, 0, 0))
        y = band(t)
        for c, e in live:
            draw_chunk(fr, t, c, e, y)
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    return out


if __name__ == '__main__':
    # preview: a few moments on a grey card
    allc = load([(0, 'hook'), (4, 'mguh'), (10, 'zero'), (14, 'gone')])
    ts = [.5, 2.5, 3.0, 5.3, 8.6, 10.3, 12.1, 15.9]
    sheet = Image.new('RGB', (540 * 4, 480 * 2), (60, 70, 80))
    for i, t in enumerate(ts):
        fr = Image.new('RGBA', (OW, 960), (40, 52, 64, 255))
        for c, e in allc:
            draw_chunk(fr, t, c, e, 480)
        sheet.paste(fr.convert('RGB').resize((540, 480)), ((i % 4) * 540, (i // 4) * 480))
    sheet.save(sys.argv[1] if len(sys.argv) > 1 else 'subs_sheet.jpg')
