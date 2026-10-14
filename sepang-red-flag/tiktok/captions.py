"""Render caption cards (transparent 1080-wide PNGs) in the explainer's type style.

A caption is a list of lines: (text, size, colour[, weight]) where weight is 'black' | 'light'.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WHITE, RED, AMBER, TEAL = (245, 247, 250), (255, 48, 64), (255, 168, 40), (64, 214, 230)
FONTS = {
    'black': '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf',
    'light': '/usr/share/fonts/opentype/inter/InterDisplay-Light.otf',
    'semi': '/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf',
}


def font(weight, size):
    return ImageFont.truetype(FONTS[weight], size)


def render(lines, path, width=1080, align='center', margin=70, gap=10, bar=None, track=0.0):
    """bar: colour of a short accent rule drawn above the first line (or None)."""
    pad = 60
    metrics = []
    for ln in lines:
        text, size, col = ln[:3]
        f = font(ln[3] if len(ln) > 3 else 'black', size)
        sp = track * size
        w = sum(f.getlength(ch) for ch in text) + sp * max(0, len(text) - 1)
        asc, desc = f.getmetrics()
        metrics.append((text, f, col, w, asc, size, sp))
    bar_h = 26 if bar else 0
    H = pad * 2 + bar_h + sum(m[4] + gap for m in metrics) + 18
    img = Image.new('RGBA', (width, int(H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = pad
    if bar:
        bx = (width - 90) / 2 if align == 'center' else margin
        d.rectangle([bx, y, bx + 90, y + 6], fill=bar + (255,)); y += bar_h
    for text, f, col, w, asc, size, sp in metrics:
        x = (width - w) / 2 if align == 'center' else margin
        for ch in text:
            d.text((x, y), ch, font=f, fill=col + (255,)); x += f.getlength(ch) + sp
        y += asc + gap
    # soft shadow for legibility over bright footage
    a = img.split()[3]
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(a.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, int(v * 1.6))))
    sh2 = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh2.putalpha(a.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * .7)))
    out = Image.alpha_composite(Image.alpha_composite(sh, sh2), img)
    out.save(path)
    return out.size


def lower_third(title, sub, colour, path, width=760):
    """team/driver tag: colour bar + bold name + team line (team names in their colours, no logos)"""
    ft, fs = font('black', 60), font('semi', 32)
    H = 170
    img = Image.new('RGBA', (width, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle([20, 22, 32, 22 + 118], fill=colour + (255,))
    d.text((56, 18), title, font=ft, fill=WHITE + (255,))
    if sub:
        d.text((58, 92), sub, font=fs, fill=(235, 235, 240, 255))
    a = img.split()[3]
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(a.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .8)))
    Image.alpha_composite(sh, img).save(path)
