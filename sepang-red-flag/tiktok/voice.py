"""AI voice-over (stand-in until the real recording): Kokoro-82M TTS, run locally with onnxruntime.

  python3 -I tiktok/voice.py                 # every line -> out/vo/<id>.wav + <id>.json (word timings)
  python3 -I tiktok/voice.py hook mguh       # just these lines
  VOICE=am_michael python3 -I tiktok/voice.py

Needs KOKORO_DIR (default ~/tts_dl) holding v11/kokoro-v1.0.onnx + voices-v1.0.bin (github.com/thewh1teagle/
kokoro-onnx release model-files-v1.1 - that export also outputs per-phoneme durations, used for the
subtitle timings), kokoro-src/ (that repo, for the vocab) and piper/ (rhasspy/piper release: espeak-ng
binary + data, used as the phonemiser).

Line markup: [shown|spoken] puts different words on screen than in the voice ("[MGU-H|M G U H]"),
*word* marks a word the subtitles colour in the line's accent.

Kokoro has no emotion control, so each line carries a delivery: the text is punctuated for the prosody
(! ? …), and the delivery sets speed, pitch and level - excited lines run quicker and higher, sad ones
slower and lower, confused ones hang on a rising question.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

KD = os.path.expanduser(os.environ.get('KOKORO_DIR', '~/tts_dl'))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(ROOT, 'out', 'vo')
SR_K, SR = 24000, 48000

# delivery: speed, pitch (semitones), level
EMO = {
    'hype':     (1.16, 1.6, 1.00),
    'excited':  (1.10, 1.0, .95),
    'curious':  (1.04, .5, .90),
    'tense':    (.98, -.4, .90),
    'confused': (.94, .4, .85),
    'sad':      (.86, -1.3, .75),
    'warm':     (1.04, .3, .90),
}
LINES = {  # id: (text, delivery)
    'hook':     ('We were at *Sepang*... the day F1 cars just... *stopped.*', 'excited'),
    'bahrain':  ('The *Bahrain* Grand Prix, moved to *Malaysia!*', 'hype'),
    'monsoon':  ('Then... the *monsoon* hit.', 'tense'),
    'losedrive': ('On the formation lap, cars just *lost* *drive.*', 'tense'),
    'footdown': ('Foot down... *nothing?!*', 'confused'),
    'inside':   ("So what *happened?* Let's look inside the *power* *unit.*", 'curious'),
    'unit':     ('A [1.6-litre|one point six litre] *V6.* A *turbo.* And hidden on the shaft... the *[MGU-H!|M G U H!]*', 'excited'),
    'mguh':     ('It turned hot exhaust into *electricity,* and spun the turbo up *instantly.* *Zero* *lag!*', 'hype'),
    'gone':     ("But for [2026...|twenty twenty-six...] it's *gone.*", 'sad'),
    'lazy':     ('In the rain, the turbo goes *lazy...* so the car leans on the *[MGU-K.|M G U K.]* The electric motor.', 'tense'),
    'wet':      ('But *wet* *mode* caps how much power the battery can give.', 'tense'),
    'lock':     ('Then the energy limit kicked in, and the software *locked* it *out.*', 'tense'),
    'zero':     ('*Zero* kilowatts. Throttle... *ignored?!*', 'confused'),
    'untested': ('A combination *nobody* had ever tested.', 'confused'),
    'redflag':  ('*Red* *flag.*', 'sad'),
    'suspended': ('Session... *suspended.*', 'sad'),
    'raceon':   ('The [FIA|F I A] sent new *software* to every team... and we went *racing!*', 'hype'),
    'payoff':   ('A software *bug* stopped F1. A software *fix* restarted it.', 'warm'),
    'outro':    ('Were *you* at *Sepang?* Tell me in the comments!', 'excited'),
}

_ESPEAK = os.path.join(KD, 'piper')


def espeak(words):
    r = subprocess.run([os.path.join(_ESPEAK, 'espeak-ng'), f'--path={_ESPEAK}', '-q', '--ipa', '-v', 'en-us', words],
                       capture_output=True, text=True, env={**os.environ, 'LD_LIBRARY_PATH': _ESPEAK}, check=True)
    return ' '.join(r.stdout.split())


def units(text):
    """[(shown, spoken, punctuation, emphasis)] - one per on-screen word"""
    out = []
    for tok in re.findall(r'\*?\[[^\]]+\][^\s]*|\S+', text):
        emph = '*' in tok; tok = tok.replace('*', '')
        if tok.startswith('['):
            shown, spoken = tok[1:tok.index(']')].split('|')
        else:
            shown = spoken = tok
        m = re.search(r'[.,!?;:…]+$', spoken)
        punct = m.group(0) if m else ''
        out.append((re.sub(r'[.,;:]+$', '', shown), spoken[:len(spoken) - len(punct)], punct.replace('...', '…'), emph))
    return out


def phonemize(us, vocab):
    """Kokoro tokens for the whole line + the token range [a, b) of each unit's sounds.

    The line is phonemised a phrase at a time (as a sentence - isolated words come out slow and over-
    stressed), then each unit's own phonemes are aligned onto that string to find where it sits."""
    phrases, cur = [], []
    for u in us:
        cur.append(u)
        if u[2]:
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    S, I, iso = '', '', []
    for ph in phrases:
        S += espeak(' '.join(u[1] for u in ph)) + ph[-1][2] + ' '
        for u in ph:
            a = len(I); I += espeak(u[1]); iso.append((a, len(I))); I += ' '
    S = S.strip()
    # monotone map from positions in I to positions in S
    sm = difflib.SequenceMatcher(None, I, S, autojunk=False)
    xs, ys = [0], [0]
    for blk in sm.get_matching_blocks():
        if blk.size:
            xs += [blk.a, blk.a + blk.size]; ys += [blk.b, blk.b + blk.size]
    xs.append(len(I)); ys.append(len(S))
    m = lambda i: int(round(np.interp(i, xs, ys)))
    keep = [c in vocab for c in S]
    before = np.concatenate([[0], np.cumsum(keep)])            # char index in S -> token index
    toks = [vocab[c] for c in S if c in vocab]
    spans = [(int(before[m(a)]), int(before[m(b)])) for a, b in iso]
    return toks, spans


class Kokoro:
    def __init__(self, voice):
        import onnxruntime as rt
        self.sess = rt.InferenceSession(os.path.join(KD, 'v11', 'kokoro-v1.0.onnx'), providers=['CPUExecutionProvider'])
        self.vocab = json.load(open(os.path.join(KD, 'kokoro-src/src/kokoro_onnx/config.json')))['vocab']
        voices = np.load(os.path.join(KD, 'voices-v1.0.bin'))
        # "a:0.7,b:0.3" blends voices
        self.voice = sum(float(w) * voices[n] for n, w in (v.split(':') if ':' in v else (v, 1) for v in voice.split(',')))
        self.ins = {i.name: i for i in self.sess.get_inputs()}

    def say(self, tok, speed):
        """audio at 24 kHz + the sample offset of every token edge (pad tokens included)"""
        name = 'input_ids' if 'input_ids' in self.ins else 'tokens'
        style = self.voice[min(len(tok), len(self.voice)) - 1]
        out = self.sess.run(None, {name: np.array([[0, *tok, 0]], np.int64), 'style': np.asarray(style, np.float32),
                                   'speed': np.array([speed], np.float32)})
        audio = np.asarray(out[0], np.float32).ravel()
        frames = np.concatenate([[0], np.cumsum(np.asarray(out[1]).ravel())])
        return audio, frames * (len(audio) / frames[-1])


def resample(x, ratio):
    """ratio > 1 shortens and raises pitch (tape speed-up)"""
    n = int(len(x) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x)


def trim(x, thr=.01, pad=.06):
    loud = np.nonzero(np.abs(x) > thr * np.abs(x).max())[0]
    a, b = max(0, loud[0] - int(pad * SR)), min(len(x), loud[-1] + int(pad * 1.5 * SR))
    return x[a:b], a


def polish(x):
    """gentle presence lift + compression, so the TTS sits forward like a close-mic read"""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 + .35 * np.exp(-((f - 3200) / 1500) ** 2) - .5 * (f < 90)
    x = np.fft.irfft(X, len(x))
    env = np.convolve(np.abs(x), np.ones(480) / 480, 'same') + 1e-4
    g = np.minimum(1, (env / env.max() / .25) ** -.35)  # ~3:1 above -12 dB
    return x * g


def make(ids, voice):
    os.makedirs(OUTD, exist_ok=True)
    k = Kokoro(voice); durs = {}
    for i in ids:
        text, emo = LINES[i]; sp, st, lvl = EMO[emo]
        p = 2 ** (st / 12)
        us = units(text); tok, spans = phonemize(us, k.vocab)
        a, edges = k.say(tok, sp / p)                           # render slower, then tape it up to pitch p
        a = resample(a, SR_K / SR)                              # 24 k -> 48 k
        a = resample(a, p)
        a, cut = trim(a); a = polish(a); a = a / (np.abs(a).max() + 1e-9) * .9 * lvl
        sec = lambda e: max(0.0, e / SR_K / p - cut / SR)       # token edge -> seconds in the final wav
        words = [dict(w=shown, s=round(sec(edges[1 + x]), 3), e=round(sec(edges[1 + y]), 3), p=punct, emph=emph)
                 for (shown, _, punct, emph), (x, y) in zip(us, spans)]
        json.dump(dict(text=text, emo=emo, words=words), open(os.path.join(OUTD, f'{i}.json'), 'w'), indent=1)
        with wave.open(os.path.join(OUTD, f'{i}.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(a, -1, 1) * 32767).astype('<i2').tobytes())
        durs[i] = len(a) / SR
        print(f'{i:10s} {durs[i]:5.2f}s  [{emo}]  ' + ' '.join(f"{w['w']}@{w['s']:.2f}" for w in words), flush=True)
    return durs


if __name__ == '__main__':
    make(sys.argv[1:] or list(LINES), os.environ.get('VOICE', 'af_heart'))
