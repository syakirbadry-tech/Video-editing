"""Build the 1080x1920 Sepang red-flag TikTok edit (voice-over led, ~64 s).

  cd sepang-red-flag && python3 tiktok/build.py            # full build
  python3 tiktok/build.py 0 5                               # just re-render segments 0 and 5
  python3 tiktok/build.py --mix                             # reuse rendered segments, redo audio + mux
  VO=path/to/voiceover.wav python3 tiktok/build.py          # mix a recorded voice-over in (placed at 0)
  (without VO, the AI stand-in lines from tiktok/voice.py in out/vo/ are placed per segment - see each 'vo' list -
   and tiktok/subs3d.py lays 3D word-by-word subtitles over the edit from their word timings; SUBS=0 turns them off)

Inputs (gitignored; tiktok/prep.sh makes them):
  sdr/<clip>.mp4           tone-mapped 1080x1920 30 fps footage
  out/aud/<clip>.wav       each clip's live audio (real trackside F1 sound)
  out/ham44.mp4            Hamilton #44 zoom -> punch into the engine cover (tiktok/hamilton_zoom.py)
  out/engine.mp4           real power unit taken apart, MGU-H, lock-out (tiktok/engine_mg.py)
  out/vo/*.wav             AI voice-over lines (tiktok/voice.py)
  chunks/p/*.mp4           portrait explainer renders (real Sepang map, power unit, red flag, telemetry HUD)

Music is written for the edit (tiktok/music.py, rendered on every build): each segment with a 'mus' key
starts a section of the cue on its cut.

Race footage gets the teal-orange LUT; explainer renders keep their own palette so the red flag stays red.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import captions as C  # noqa: E402
import music  # noqa: E402
import sound  # noqa: E402
import stills  # noqa: E402
import subs3d  # noqa: E402

OUT = os.path.join(ROOT, 'out')
SEG, CAP = os.path.join(OUT, 'seg'), os.path.join(OUT, 'cap')
FPS, W, H = 30, 1080, 1920
LUT = os.path.join(HERE, 'teal_orange.cube')
aud = lambda clip: os.path.join(OUT, 'aud', clip + '.wav')

# ------------------------------------------------------------------ captions: lines, anchor
WH, RD, AM, TL = C.WHITE, C.RED, C.AMBER, C.TEAL
CAPS = {
    'hook':      ([('SEPANG · 04.10.2026', 34, AM, 'semi'), ('THE DAY F1 CARS', 84, WH), ('JUST STOPPED.', 108, RD)], 'top'),
    'bahrain':   ([('BAHRAIN GP', 100, WH), ('…MOVED TO SEPANG', 60, TL, 'light')], 'top'),
    'monsoon':   ([('THEN THE', 60, WH, 'light'), ('MONSOON HIT', 108, WH)], 'mid'),
    'losedrive': ([('CARS LOSE', 72, WH, 'light'), ('DRIVE', 120, RD)], 'mid'),
    'footdown':  ([('FOOT DOWN.', 96, WH), ('NOTHING.', 104, RD)], 'mid'),
    'untested':  ([('A COMBO NOBODY', 76, WH), ('HAD EVER TESTED', 76, TL)], 'mid'),
    'redflag':   ([('RED FLAG', 170, RD)], 'top'),
    'suspended': ([('SESSION', 64, WH, 'light'), ('SUSPENDED', 104, RD)], 'mid'),
    'raceon':    ([('FIA PUSHES A SOFTWARE FIX', 40, TL, 'semi'), ('RACE ON', 132, WH)], 'mid'),
    'payoff':    ([('A SOFTWARE BUG', 72, WH), ('STOPPED IT.', 72, WH), ('A SOFTWARE FIX', 72, TL), ('RESTARTED IT.', 72, TL)], 'mid'),
    'outro':     ([('WERE YOU', 72, WH, 'light'), ('AT SEPANG?', 112, AM), ('TELL ME IN THE COMMENTS', 36, WH, 'semi')], 'mid'),
}
# team tags: names in team colours (no logos)
LABELS = {
    'merc':    ('MERCEDES', 'MERCEDES-AMG PETRONAS', (0, 210, 190)),
    'ham44':   ('#44 HAMILTON', 'SCUDERIA FERRARI', (220, 0, 24)),
    'ant12':   ('#12 ANTONELLI', 'MERCEDES-AMG PETRONAS', (0, 210, 190)),
    'lec16':   ('#16 LECLERC', 'SCUDERIA FERRARI', (220, 0, 24)),
    'rb6':     ('RED BULL #6', 'ORACLE RED BULL RACING', (40, 80, 255)),
    'sc':      ('SAFETY CAR', 'FIA · MERCEDES-AMG', (255, 196, 0)),
    'medical': ('MEDICAL CAR', 'FIA · MERCEDES-AMG', (255, 196, 0)),
}


# ------------------------------------------------------------------ edit decision list
def foot(clip, src, dur, cap=None, **o): return dict(kind='foot', clip=clip, src=src, dur=dur, cap=cap, **o)
def render(f, dur, e, cap=None, **o): return dict(kind='render', file=f, src=0, dur=dur, e=e, cap=cap, **o)  # e = explainer time of frame 0
def clip(f, dur, cap=None, **o): return dict(kind='clip', file=f, src=0, dur=dur, cap=cap, **o)
def photo(f, dur, kb, cap=None, **o): return dict(kind='photo', file=f, src=0, dur=dur, kb=kb, cap=cap, **o)  # kb = (z0, z1, c0, c1)


EDL = [
    # hook: Mercedes blasts past, slow-mo at the closest point, freeze + glitch on "stopped"
    foot('IMG_3134', 7.0, 3.2, 'hook', ramp=[(0, 1.4, 1), (1.4, 2.0, .5)], freeze=.6, label=('merc', .2, 1.3),
         zoom=(1.08, .5, .45), vol=1.0, vo=[('hook', .15)],
         sfx=[('rev_whoosh', .4, .35), ('sub_drop', 1.4, .9), ('glitch', 2.6, .55), ('powerdown', 2.6, .5)], mus='hook'),
    render('chunks/p/map.mp4', 3.2, 6.4, 'bahrain', flash='white', sfx=[('hit', 0, .6)], vo=[('bahrain', .35)], mus='bahrain'),
    foot('IMG_3136', 2.0, 1.4, flash='white', strike=1.1, sfx=[('thunder', 1.12, .9)], vo=[('monsoon', .1)], mus='monsoon'),
    photo('photos/safety_car_spray.jpg', 1.0, (1.12, 1.3, (520, 1150), (480, 1170)), hold=True, label=('sc', 0, 1.0),
          live=[('IMG_3136', 3.4, 0, 1.0, 1, .5)], vo=[('losedrive', .5)]),
    foot('IMG_3188', 0.9, 1.8, zoom=(1.1, .5, .5)),
    foot('IMG_3137', 0.3, 2.9, zoom=(1.15, .45, .62), hud='chunks/p/hud.mp4', mus='footdown'),
    # zoom into Hamilton's #44 -> punch to the engine cover (real 5585 audio, tape slow-mo)
    clip('out/ham44.mp4', 50 / 30, live=[('IMG_5585', 3.35, 0, 40 / 30, .5, 1.0)], vo=[('inside', .2)],
         sfx=[('riser', -.9, .35), ('whoosh', 1.2 - .6, .5), ('hit', 1.2, .9), ('whoosh', 1.667 - .5, .4)], mus='ham'),
    # the real power unit, taken apart: MGU-H -> 2026 removes it -> lazy turbo -> wet mode -> energy lock-out
    clip('out/engine.mp4', 31.0, grade=False, sub_y=1410,
         vo=[('unit', 1.5), ('mguh', 6.8), ('gone', 12.1), ('lazy', 15.0), ('wet', 21.2), ('lock', 24.3), ('zero', 28.15)],
         sfx=[('hit', 0, .5), ('clank', 1.75, .5), ('clank', 2.35, .4), ('clank', 2.45, .35), ('clank', 3.45, .55), ('whoosh', 4.0, .3),
              ('hit', 5.75, .9), ('sub_drop', 5.75, .6), ('whoosh', 6.15, .5), ('zap', 7.4, .3), ('zap', 9.0, .3), ('hit', 10.85, .7),
              ('sub_drop', 12.0, .45), ('hit', 13.85, .8), ('glitch', 13.85, .45), ('powerdown', 13.9, .35), ('rev_whoosh', 14.0, .35),
              ('clank', 15.0, .5), ('powerdown', 15.6, .25), ('zap', 17.6, .25), ('tick', 24.7, .15), ('tick', 25.05, .15),
              ('tick', 25.4, .15), ('tick', 25.75, .15), ('hit', 26.3, .8), ('glitch', 26.3, .35), ('sub_drop', 28.1, .9),
              ('glitch', 28.1, .55), ('powerdown', 28.1, .5), ('hit', 29.35, .7)], mus='engine'),
    foot('IMG_3136', 8.1, 2.7, flash='white', vo=[('untested', .05)], mus='untested'),
    render('chunks/p/flag.mp4', 3.0, 41.0, 'redflag', flash='red', vo=[('redflag', .35)], mus='redflag'),
    foot('IMG_3186', 0.0, 1.0, vol=.6, vo=[('suspended', .05)]),
    photo('photos/medical_car.jpg', 1.4, (1.2, 1.38, (520, 820), (470, 800)), hold=True, label=('medical', 0, 1.4),
          live=[('IMG_3186', 1.0, 0, 1.4, 1, .6)], vo=[('raceon', .6)], mus='raceon'),
    # "...and we went racing": team montage from the trackside photos, a cut on every beat
    foot('IMG_5585', 2.3, 2.0, flash='white', label=('ham44', 0, 2.0), vol=.9, sfx=[('hit', 0, .8)], mus='montage'),
    photo('photos/ant12_close.jpg', .5, (1.05, 1.2, (600, 1060), (560, 1040)), hold=True, label=('ant12', 0, .5),
          live=[('IMG_5761', .3, 0, .5, 1, .9)], sfx=[('whoosh', -.35, .4)]),
    photo('photos/lec16_side.jpg', .5, (1.1, 1.25, (700, 1150), (640, 1150)), hold=True, label=('lec16', 0, .5),
          live=[('IMG_5761', 2.6, 0, .5, 1, .9)], sfx=[('whoosh', -.35, .4)]),
    photo('photos/rb6_wet.jpg', .5, (1.15, 1.3, (780, 1450), (720, 1460)), hold=True, label=('rb6', 0, .5),
          live=[('IMG_3337', 2.4, 0, .5, 1, .9)], sfx=[('whoosh', -.35, .4)]),
    foot('IMG_3337', 3.0, 1.0, hold=True, vol=.9, sfx=[('whoosh', -.35, .4)]),
    foot('IMG_5762', 0.3, 4.0, vol=.5, vo=[('payoff', .15)], mus='payoff'),  # music resolves into the outro
    foot('IMG_5766', 2.5, 2.8, fadeout=.8, vol=.6, vo=[('outro', .25)], mus='outro'),
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'ffmpeg failed: {" ".join(cmd)}\n{r.stderr[-3000:]}')


def png(key, kind):
    p = os.path.join(CAP, f'{kind}_{key}.png')
    if not os.path.exists(p):
        if kind == 'cap':
            C.render(CAPS[key][0], p)
        else:
            C.lower_third(*LABELS[key], p)
    return p


def sdr60(clip, src, dur):
    """60 fps tone-mapped extract for speed ramps (cached)"""
    p = os.path.join(OUT, f'sdr60_{clip}_{src}.mp4')
    if not os.path.exists(p):
        run(['ffmpeg', '-y', '-v', 'error', '-ss', str(src), '-t', str(dur + .5), '-i', os.path.join(ROOT, 'footage', clip + '.MOV'), '-an',
             '-vf', 'zscale=w=1080:h=1920:filter=spline36:tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=100,format=gbrpf32le,'
             'zscale=p=bt709,tonemap=tonemap=hable:desat=0:peak=6,zscale=t=bt709:m=bt709:r=tv,format=yuv420p',
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', p])
    return p


def flash_src(colour, dur, at=0.0, peak=.6, decay=.3, label='flash'):
    col = {'white': '0xE8F0FF', 'red': '0xFF2030'}[colour]
    fin = f'fade=in:st={at - .03:.3f}:d=0.03:alpha=1,' if at > 0 else ''
    return (f'color=c={col}:s={W}x{H}:r={FPS}:d={dur:.3f},format=rgba,colorchannelmixer=aa={peak},'
            f'{fin}fade=out:st={at:.3f}:d={decay}:alpha=1[{label}]')


def build_segment(i, s):
    out = os.path.join(SEG, f'{i:02d}.mp4')
    dur, ins, fc = s['dur'], [], []

    def add(*args):
        ins.extend(args); return sum(1 for a in ins if a == '-i') - 1

    grade = f'lut3d={LUT}:interp=tetrahedral,vignette=angle=PI/3.2,unsharp=5:5:0.35,noise=alls=5:allf=t'
    if s['kind'] == 'foot':
        z, cx, cy = s.get('zoom', (1.0, .5, .5))
        zw, zh = round(W * z / 2) * 2, round(H * z / 2) * 2
        frame = f'scale={zw}:{zh}:flags=lanczos,crop={W}:{H}:{(zw - W) * cx:.0f}:{(zh - H) * cy:.0f}'
        if s.get('ramp'):
            v = add('-i', sdr60(s['clip'], s['src'], dur))
            n = len(s['ramp'])
            fc.append(f'[{v}:v]split={n}' + ''.join(f'[s{k}]' for k in range(n)))  # one copy per trimmed piece
            parts = []
            for k, (a, b, sp) in enumerate(s['ramp']):
                fc.append(f'[s{k}]trim={a}:{b},setpts=(PTS-STARTPTS)/{sp}[r{k}]'); parts.append(f'[r{k}]')
            frz = s.get('freeze', 0)
            fc.append(f'{"".join(parts)}concat=n={len(parts)}:v=1,fps={FPS},tpad=stop_mode=clone:stop_duration={frz},'
                      f'{frame},{grade}' + (f",hue=s=0:enable='gte(t,{dur - frz:.3f})',"
                                            f"rgbashift=rh=-14:bh=14:enable='between(t,{dur - frz:.3f},{dur - frz + .2:.3f})'" if frz else '')
                      + '[base0]')
        else:
            v = add('-ss', str(s['src']), '-t', str(dur), '-i', os.path.join(ROOT, 'sdr', s['clip'] + '.mp4'))
            fc.append(f'[{v}:v]setpts=PTS-STARTPTS,{frame},{grade}[base0]')
    elif s['kind'] in ('clip', 'photo'):
        f = os.path.join(ROOT, s['file'])
        if s['kind'] == 'photo':
            z0, z1, c0, c1 = s['kb']
            name = os.path.splitext(os.path.basename(f))[0]
            kb = os.path.join(OUT, f'kb_{name}_{s["dur"]}_{z0}_{z1}_{c0[0]}_{c0[1]}_{c1[0]}_{c1[1]}.mp4')
            if not os.path.exists(kb):
                stills.kenburns(f, kb, s['dur'], z0, z1, c0, c1)
            f = kb
        v = add('-i', f)
        fc.append(f'[{v}:v]setpts=PTS-STARTPTS,{grade if s.get("grade", True) else "noise=alls=3:allf=t"}[base0]')
    else:  # explainer render: its own palette, light grain only
        v = add('-ss', str(s['src']), '-t', str(dur), '-i', os.path.join(ROOT, s['file']))
        fc.append(f'[{v}:v]setpts=PTS-STARTPTS,scale={W}:{H},noise=alls=3:allf=t[base0]')
    last = 'base0'
    if s.get('hud'):  # explainer telemetry screen-blended over real footage, on a darkened card
        h = add('-i', os.path.join(ROOT, s['hud']))
        fc.append(f'[{last}]drawbox=x=40:y=210:w=1000:h=560:color=black@0.5:t=fill,format=gbrp[hb]')
        fc.append(f'[{h}:v]setpts=PTS-STARTPTS,scale={W}:{H},format=gbrp[hh]')
        fc.append('[hb][hh]blend=all_mode=screen:shortest=1[hud]'); last = 'hud'
    fc.append(f'[{last}]format=rgba[b]'); last = 'b'
    if s.get('cap'):
        lines, anchor = CAPS[s['cap']]
        c = add('-loop', '1', '-t', f'{dur}', '-i', png(s['cap'], 'cap'))
        hold = s.get('hold', False)
        fin = '' if hold else 'fade=in:st=0:d=0.18:alpha=1,'
        rise = '' if hold else '+28*pow(max(0,1-t/0.25),2)'
        y0 = {'top': 190, 'mid': 1150}[anchor]
        fc.append(f'[{c}:v]format=rgba,{fin}fade=out:st={dur - .15:.3f}:d=0.15:alpha=1[cap]')
        fc.append(f"[{last}][cap]overlay=0:'{y0}{rise}':format=auto[c1]"); last = 'c1'
    if s.get('label'):
        key, a, b = s['label']
        lb = add('-loop', '1', '-t', f'{dur}', '-i', png(key, 'lt'))
        fd = min(.2, (b - a) / 5)
        fc.append(f'[{lb}:v]format=rgba,fade=in:st={a}:d={fd:.3f}:alpha=1,fade=out:st={b - fd:.3f}:d={fd:.3f}:alpha=1[lt]')
        fc.append(f"[{last}][lt]overlay='40-60*pow(max(0,1-(t-{a})/0.3),3)':1580:format=auto[l1]"); last = 'l1'
    if s.get('flash'):
        fc.append(flash_src(s['flash'], dur)); fc.append(f'[{last}][flash]overlay=0:0[f1]'); last = 'f1'
    if s.get('strike') is not None:
        fc.append(flash_src('white', dur, at=s['strike'], peak=.45, decay=.25, label='lt2'))
        fc.append(f'[{last}][lt2]overlay=0:0[f2]'); last = 'f2'
    if s.get('fadeout'):
        fc.append(f'[{last}]fade=out:st={dur - s["fadeout"]:.3f}:d={s["fadeout"]}[f3]'); last = 'f3'
    # exact frame count per segment so the concatenated picture never drifts from the audio mix
    fc.append(f'[{last}]format=yuv420p,fps={FPS},tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={round(dur * FPS)}[v]')
    run(['ffmpeg', '-y', '-v', 'error', *ins, '-filter_complex', ';'.join(fc), '-map', '[v]', '-an',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-r', str(FPS), '-video_track_timescale', '15360', out])
    return out


def audio_events(timeline):
    ev = []
    for t0, s in timeline:
        dur = s['dur']
        if s['kind'] == 'foot':  # live trackside audio (speed-ramped like the picture)
            vol = s.get('vol', .55)
            if s.get('ramp'):
                at = t0
                for a, b, sp in s['ramp']:
                    ev.append(dict(wav=aud(s['clip']), src=s['src'] + a, dur=(b - a) / sp, rate=sp, at=at, gain=vol, hp=80))
                    at += (b - a) / sp
            else:
                ev.append(dict(wav=aud(s['clip']), src=s['src'], dur=dur, at=t0, gain=vol, hp=80))
        for c, src, at, d, rate, g in s.get('live', []):
            ev.append(dict(wav=aud(c), src=src, dur=d, rate=rate, at=t0 + at, gain=g, hp=60))
        for name, at, g in s.get('sfx', []):
            ev.append(dict(sfx=name, at=t0 + at, gain=g))
        if s.get('cap') and not s.get('hold'):
            ev.append(dict(sfx='tick', at=t0 + .02, gain=.12))
        if t0 > 0 and s.get('flash'):  # whoosh into flashed cuts
            ev.append(dict(sfx='whoosh', at=t0 - .6, gain=.35))
    return ev


def ai_voice(timeline, total):
    """stand-in voice-over: the tiktok/voice.py lines (out/vo/<id>.wav) placed where each segment's vo list says"""
    import numpy as np
    import wave
    buf = np.zeros(int((total + 1) * sound.SR), np.float32)
    for t0, s in timeline:
        for line, at in s.get('vo', []):
            x = sound.load(os.path.join(OUT, 'vo', line + '.wav'))[:, 0]
            i = int((t0 + at) * sound.SR); buf[i:i + len(x)] += x[:len(buf) - i]
    p = os.path.join(OUT, 'vo_track.wav')
    with wave.open(p, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sound.SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype('<i2').tobytes())
    return p


def main():
    for d in (OUT, SEG, CAP):
        os.makedirs(d, exist_ok=True)
    mix_only = '--mix' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--mix']
    only = set(int(x) for x in args) if args else None
    timeline, t, files = [], 0.0, []
    for i, s in enumerate(EDL):
        timeline.append((t, s))
        files.append(os.path.join(SEG, f'{i:02d}.mp4'))
        if not mix_only and (only is None or i in only):
            print(f'seg {i:02d} {s["kind"]:6s} T={t:6.2f} dur={s["dur"]:.2f} {s.get("cap") or s.get("file", "")}', flush=True)
            build_segment(i, s)
        t += s['dur']
    total = t
    if only is not None:
        return
    lst = os.path.join(OUT, 'concat.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{p}'\n" for p in files)
    video = os.path.join(OUT, 'video.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', video])
    ai = not os.environ.get('VO') and os.path.isdir(os.path.join(OUT, 'vo'))
    vo = os.environ.get('VO') or (ai_voice(timeline, total) if ai else None)
    # background music: one cue cut to the picture, each 'mus' segment starts a section (tiktok/music.py)
    marks = {s['mus']: t0 for t0, s in timeline if s.get('mus')}
    score = music.render(marks, total, os.path.join(OUT, 'music.wav'))
    ev = audio_events(timeline) + [dict(wav=score, src=0, dur=total, at=0, gain=.75, bus='music', fade=.02)]
    mixwav = sound.mix(ev, total, os.path.join(OUT, 'mix.wav'), vo=vo)
    # 3D word-by-word subtitles, timed from the AI voice's word timings (a recorded VO needs its own timings)
    subs = []
    if ai and os.environ.get('SUBS', '1') != '0':
        lines = [(t0 + at, line) for t0, s in timeline for line, at in s.get('vo', [])]
        bands = [(t0, t0 + s['dur'], s.get('sub_y', 1300)) for t0, s in timeline]
        subs = ['-i', subs3d.render(lines, bands, total, os.path.join(OUT, 'subs.mov'))]
    final = os.path.join(OUT, 'sepang_red_flag_tiktok.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-i', mixwav, *subs,
         *(['-filter_complex', '[0:v][2:v]overlay=0:0:format=auto,format=yuv420p[v]', '-map', '[v]'] if subs else ['-map', '0:v']), '-map', '1:a',
         '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000', '-c:a', 'aac', '-b:a', '256k',
         # TikTok-friendly delivery: grain makes the intermediates huge, so cap the bitrate (~90 MB for 49 s)
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-maxrate', '15M', '-bufsize', '30M',
         '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
         '-movflags', '+faststart', '-shortest', final])
    print('wrote', final, f'{total:.2f}s')


if __name__ == '__main__':
    main()
