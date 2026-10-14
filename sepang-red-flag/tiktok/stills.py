"""Ken Burns moves on trackside photos -> 1080x1920 30 fps clips (ungraded; the build grades them).

kenburns(photo, out, dur, z0, z1, c0, c1)
  z = 1 shows the photo's full height in a 9:16 window; c0 -> c1 are the window centres in photo pixels.
  The push eases out (fast start, settles), like a camera punch that lands on the car.
"""
import subprocess

from PIL import Image

OW, OH, FPS = 1080, 1920, 30


def _window(img, cx, cy, z):
    W, H = img.size; h = H / z; w = h * OW / OH
    if w > W:  # photo narrower than 9:16 at this zoom: fit width instead
        w = W / z * 1.0; h = w * OH / OW
    cx = min(max(cx, w / 2), W - w / 2); cy = min(max(cy, h / 2), H - h / 2)
    return img.transform((OW, OH), Image.EXTENT, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), Image.BICUBIC)


def kenburns(photo, out, dur, z0, z1, c0, c1):
    img = Image.open(photo).convert('RGB')
    n = round(dur * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(n):
        k = 1 - (1 - i / max(1, n - 1)) ** 2.2
        z = z0 + (z1 - z0) * k
        cx, cy = c0[0] + (c1[0] - c0[0]) * k, c0[1] + (c1[1] - c0[1]) * k
        ff.stdin.write(_window(img, cx, cy, z).tobytes())
    ff.stdin.close(); ff.wait()
    return out
