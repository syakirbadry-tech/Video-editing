"""Hamilton #44 push-in -> cut to the trackside photo -> punch into the engine cover -> x-ray scan.

  python3 -I tiktok/hamilton_zoom.py <frames_dir> <out.mp4> [--photo photos/ham44_side.jpg] [--xray] [--debug dbg.jpg]

<frames_dir> holds the 4K (2160x3840) tone-mapped 60 fps frames of IMG_5585 from 3.35 s
(see tiktok/prep.sh). The photo is the side-on shot of #44 taken from the grandstand.
Output: 1080x1920 30 fps, ungraded (the build grades it).

  A  slow-mo track on the video (each 60 fps frame becomes one 30 fps frame = 2x slow), push 1.0 -> 1.7
  B  white-flash cut to the sharp photo, punch into the engine cover, radial zoom blur
  C  (--xray only) x-ray: a scan line sweeps down, the bodywork becomes a cyan edge render, then callouts
     mark where the power-unit parts sit (illustrative positions) with the MGU-K highlighted.
     The edit now cuts from B straight into the photo-based power-unit graphic (tiktok/engine_mg.py).
"""
import glob
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OW, OH, FPS = 1080, 1920, 30
A_N, B_N, C_N = 36, 14, 36
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
FONT_S = '/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf'


def ease_io(k): return 4 * k ** 3 if k < .5 else 1 - (-2 * k + 2) ** 3 / 2
def ease_in(k): return k ** 3
def ease_out(k): return 1 - (1 - k) ** 3


def track(img, car_w=300):
    """Ferrari = densest run of saturated red, car_w px wide (at 540 px), in the band between the STING
    boards and the F1 board. A fixed-width window ignores the red kerbs and tyre wall beside the car."""
    a = np.asarray(img.resize((540, 960), Image.BILINEAR)).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 120) & (r - g > 70) & (r - b > 60)
    m[:int(960 * .61)] = False; m[int(960 * .76):] = False
    col = m.sum(0).astype(float)
    if col.sum() < 30:
        return None
    win = np.convolve(col, np.ones(car_w), mode='valid')
    x0 = int(np.argmax(win)); rows = np.nonzero(m[:, x0:x0 + car_w].any(1))[0]
    return np.array([x0 + car_w / 2, np.median(rows), car_w]) * 4  # centre x, centre y, length (4K px)


def smooth(v, k=7):
    v = np.asarray(v, float); pad = np.pad(v, ((k, k), (0, 0)), mode='edge')
    w = np.hanning(2 * k + 1); w /= w.sum()
    return np.stack([np.convolve(pad[:, j], w, mode='valid') for j in range(v.shape[1])], 1)


def crop(img, cx, cy, z):
    """1080x1920 window at zoom z (1 = full 2160x3840 frame) centred on (cx, cy), clamped to the frame."""
    W, H = img.size; w, h = W / z, H / z
    cx = min(max(cx, w / 2), W - w / 2); cy = min(max(cy, h / 2), H - h / 2)
    return img.transform((OW, OH), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BICUBIC)


def crop916(img, cx, cy, z):
    """9:16 window from a photo of any aspect (z = 1 is full height), centred on (cx, cy), clamped"""
    W, H = img.size; h = H / z; w = h * OW / OH
    cx = min(max(cx, w / 2), W - w / 2); cy = min(max(cy, h / 2), H - h / 2)
    return img.transform((OW, OH), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BICUBIC), (cx - w / 2, cy - h / 2, w, h)


# where the power-unit parts sit under #44's bodywork in photos/ham44_side.jpg (illustrative)
# (name, sub, photo xy, colour, label anchor in the 1080x1920 frame)
PU_SPOTS = [('V6 ICE', 'COMBUSTION ENGINE', (745, 1310), (240, 240, 245), (430, 640)),
            ('TURBO', None, (885, 1335), (255, 176, 32), (730, 800)),
            ('BATTERY', 'ENERGY STORE', (565, 1415), (64, 214, 255), (60, 1470)),
            ('MGU-K', 'ELECTRIC MOTOR', (655, 1380), (64, 214, 255), (60, 860))]


def zoom_blur(img, amount, n=6):
    """radial blur: average of progressively upscaled copies about the centre"""
    if amount < .003:
        return img
    acc = np.asarray(img, float)
    for i in range(1, n):
        s = 1 + amount * i / (n - 1)
        w, h = OW / s, OH / s
        acc += np.asarray(img.transform((OW, OH), Image.EXTENT, ((OW - w) / 2, (OH - h) / 2, (OW + w) / 2, (OH + h) / 2), Image.BILINEAR), float)
    return Image.fromarray(np.uint8(acc / n))


def xray(img):
    g = np.asarray(img.convert('L'), float) / 255
    e = np.asarray(img.convert('L').filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.2)), float) / 255
    e = np.clip(e * 5.5, 0, 1) ** .8
    base = (1 - g) * .2 + g * .04                       # inverted, dim body
    out = np.stack([base * .25 + e * .55, base * .75 + e * 1.0, base * 1.0 + e * 1.0], -1)
    yy, xx = np.mgrid[0:OH, 0:OW]
    grid = ((xx % 60 < 2) | (yy % 60 < 2)) * .10
    out += grid[..., None] * np.array([.2, .8, 1.0])
    glow = Image.fromarray(np.uint8(np.clip(out, 0, 1) * 255)).filter(ImageFilter.GaussianBlur(6))
    out = np.clip(out + np.asarray(glow, float) / 255 * .6, 0, 1)
    return Image.fromarray(np.uint8(out * 255))


def label(draw, x, y, k, lines):
    """lower-third: team colour bar + driver line, slides in with k in [0,1]"""
    if k <= 0:
        return
    dx = (1 - ease_out(k)) * -60
    draw.rectangle([x + dx, y, x + dx + 10, y + 128], fill=(220, 0, 24, int(255 * k)))
    fy = y - 6
    for txt, size, col, f in lines:
        draw.text((x + dx + 28, fy), txt, font=ImageFont.truetype(f, size), fill=col + (int(255 * k),)); fy += size + 8


def main():
    src, out = sys.argv[1], sys.argv[2]
    dbg = sys.argv[sys.argv.index('--debug') + 1] if '--debug' in sys.argv else None
    photo_path = sys.argv[sys.argv.index('--photo') + 1] if '--photo' in sys.argv else 'photos/ham44_side.jpg'
    files = sorted(glob.glob(f'{src}/f*.jpg'))[:A_N]
    imgs = [Image.open(f).convert('RGB') for f in files]
    raw = [track(im) for im in imgs]
    last = next(r for r in raw if r is not None)
    tr = []
    for r in raw:
        last = r if r is not None else last; tr.append(last)
    tr = smooth(tr)
    if dbg:
        sheet = []
        for i in (0, len(imgs) // 2, len(imgs) - 1):
            im = imgs[i].resize((540, 960)); d = ImageDraw.Draw(im); cx, cy, L = tr[i] / 4
            d.rectangle([cx - L / 2, cy - 25, cx + L / 2, cy + 25], outline='cyan', width=3)
            ex, ey = cx + .16 * L, cy - .05 * L * 4 / 4
            d.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill='yellow'); sheet.append(im)
        s = Image.new('RGB', (540 * 3, 960)); [s.paste(im, (540 * i, 0)) for i, im in enumerate(sheet)]; s.save(dbg); return

    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    put = lambda im: ff.stdin.write(im.convert('RGB').tobytes())
    font_hud = ImageFont.truetype(FONT_S, 30)

    def overlay_label(im, k):
        im = im.convert('RGBA'); lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        label(d, 70, 290, k, [('#44  HAMILTON', 64, (255, 255, 255), FONT), ('SCUDERIA FERRARI', 34, (235, 235, 240), FONT_S)])
        sh = lay.split()[3].filter(ImageFilter.GaussianBlur(10)); shadow = Image.new('RGBA', im.size, (0, 0, 0, 0)); shadow.putalpha(sh.point(lambda v: int(v * .7)))
        return Image.alpha_composite(Image.alpha_composite(im, shadow), lay)

    # A: slow-mo push-in on the car
    for i, im in enumerate(imgs):
        k = ease_io(i / (A_N - 1)); cx, cy, L = tr[i]  # noqa: E741
        z = 1 + .7 * k
        fr = crop(im, cx, cy - 120 * (1 - k), z)
        put(overlay_label(fr, min(1, (i - 6) / 10) if i < A_N - 4 else (A_N - 1 - i) / 3))
    # B: white-flash cut to the sharp photo, punch into the engine cover
    photo = Image.open(photo_path).convert('RGB')
    px0, py0, ex, ey = 700, 1350, 760, 1300
    ZB, ZC = 2.2, 2.35
    for j in range(B_N):
        k = ease_in((j + 1) / B_N); m = ease_io((j + 1) / B_N)
        fr, _ = crop916(photo, px0 + (ex - px0) * m, py0 + (ey - py0) * m, 1 + (ZB - 1) * k)
        fr = zoom_blur(fr, .2 * np.sin(np.pi * min(1, (j + 1) / B_N)) + .03)
        if j < 3:  # flash on the cut
            fr = Image.blend(fr, Image.new('RGB', fr.size, (235, 242, 255)), [.85, .5, .2][j])
        put(fr)
    # C: x-ray scan, then the power-unit callouts
    f_sub = ImageFont.truetype(FONT_S, 26)
    for j in range(C_N if '--xray' in sys.argv else 0):
        k = j / (C_N - 1); z = ZB + (ZC - ZB) * k
        fr, (x0, y0, w, h) = crop916(photo, ex, ey, z); xr = xray(fr)
        line = int(ease_io(min(1, k / .45)) * (OH + 80)) - 40
        mask = Image.new('L', (OW, OH), 0); ImageDraw.Draw(mask).rectangle([0, 0, OW, max(0, line)], fill=255)
        im = Image.composite(xr, fr, mask).convert('RGBA')
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        if 0 <= line < OH:
            for wd, a in ((24, 40), (8, 120), (3, 255)):
                d.rectangle([0, line - wd // 2, OW, line + wd // 2], fill=(80, 230, 255, a))
        txt_a = int(255 * min(1, j / 6))
        d.text((70, 240), 'SCANNING POWER UNIT', font=font_hud, fill=(80, 230, 255, txt_a))
        d.text((70, 280), f'{min(100, int(k / .45 * 100))}%', font=ImageFont.truetype(FONT, 72), fill=(255, 255, 255, txt_a))
        for n, (name, sub, (sx, sy), col, (lx, ly)) in enumerate(PU_SPOTS):
            ka = (j - 15 - n * 4) / 4  # callouts pop in one after another once the scan has passed
            if ka <= 0:
                continue
            ka = min(1, ka); a = int(255 * ka)
            x, y = (sx - x0) / w * OW, (sy - y0) / h * OH
            hero = name == 'MGU-K'
            r = (18 if hero else 10) * (1 + (.3 * np.sin(j * .9) if hero else 0))
            d.ellipse([x - r, y - r, x + r, y + r], outline=col + (a,), width=5 if hero else 4)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=col + (a,))
            fl = ImageFont.truetype(FONT, 64 if hero else 46)
            ty = ly + (fl.size + 6 if ly < y else -14)  # leader line meets the side of the label nearest the spot
            d.line([(x, y), (lx + 20, ty)], fill=col + (a,), width=3)
            d.text((lx, ly), name, font=fl, fill=col + (a,), stroke_width=3, stroke_fill=(0, 10, 20, a))
            if sub:
                d.text((lx + 2, ly + fl.size + 4), sub, font=f_sub, fill=(235, 240, 245, a), stroke_width=2, stroke_fill=(0, 10, 20, a))
        put(Image.alpha_composite(im, lay))
    ff.stdin.close(); ff.wait()
    print('wrote', out, (A_N + B_N + (C_N if '--xray' in sys.argv else 0)) / FPS, 's')


if __name__ == '__main__':
    main()
