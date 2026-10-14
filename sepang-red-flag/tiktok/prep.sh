#!/bin/sh
# Prepare every input for tiktok/build.py. Run from sepang-red-flag/ with the Drive clips in footage/.
#   footage/*.MOV  -> sdr/*.mp4       iPhone HLG (and SDR) 4K portrait -> 1080x1920 30 fps SDR, Hable tone-map
#                  -> out/aud/*.wav   live trackside audio (real F1 sound for the mix)
#   main.js        -> chunks/p/*.mp4  portrait renders: real Sepang map, power unit, red flag, telemetry HUD
#   IMG_5585 + photos/ham44_side.jpg -> out/ham44.mp4   Hamilton #44 zoom -> photo punch into the engine cover (tiktok/hamilton_zoom.py)
#   photos/pu/img0.jpeg (power unit) + img1.jpeg (Garrett e-turbo) -> out/engine.mp4 + out/engine_score.wav (tiktok/engine_mg.py)
#   tiktok/voice.py -> out/vo/*.wav   AI stand-in voice-over (Kokoro TTS, needs KOKORO_DIR - see voice.py)
#   photos/*.jpg   your trackside stills (gitignored like footage/), used by build.py via tiktok/stills.py
#   audio.py       -> soundtrack.wav ; teal_orange_lut.py -> tiktok/teal_orange.cube
set -e
mkdir -p sdr chunks/p out/aud out/h44
TM="zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0:peak=6,zscale=t=bt709:m=bt709:r=tv"
for f in footage/*.MOV; do
  b=$(basename "$f" .MOV)
  [ -f "out/aud/$b.wav" ] || ffmpeg -y -v error -i "$f" -map 0:a:0 -ac 1 -ar 48000 "out/aud/$b.wav"
  [ -f "sdr/$b.mp4" ] && continue
  trc=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "$f")
  if [ "$trc" = "arib-std-b67" ]; then vf="fps=30,zscale=w=1080:h=1920:filter=spline36,$TM,format=yuv420p"
  else vf="fps=30,scale=1080:1920:flags=lanczos,format=yuv420p"; fi
  ffmpeg -y -v error -i "$f" -an -vf "$vf" -c:v libx264 -preset fast -crf 14 "sdr/$b.mp4" && echo "sdr/$b.mp4 ($trc)"
done
python3 -I tiktok/teal_orange_lut.py tiktok/teal_orange.cube
[ -f soundtrack.wav ] || python3 audio.py

# portrait explainer renders (frame = explainer time x 30)
r() { [ -f "chunks/p/$3.mp4" ] || PORTRAIT=1 HUD=$4 node render.mjs video "$1" "$2" "chunks/p/$3.mp4"; }
( r 600 840 pu_a; r 192 288 map ) & ( r 840 1080 pu_b; r 1230 1350 flag; r 519 600 hud 1 ) & wait
printf "file 'pu_a.mp4'\nfile 'pu_b.mp4'\n" > chunks/p/pu.txt
ffmpeg -y -v error -f concat -safe 0 -i chunks/p/pu.txt -c copy chunks/p/pu.mp4

# Hamilton #44: 4K 60 fps frames from 3.35 s, then the zoom / x-ray sequence
[ -f out/h44/f001.jpg ] || ffmpeg -y -v error -ss 3.35 -t 0.75 -i footage/IMG_5585.MOV -vf "$TM,format=yuvj444p" -q:v 2 out/h44/f%03d.jpg
[ -f out/ham44.mp4 ] || python3 -I tiktok/hamilton_zoom.py out/h44 out/ham44.mp4

# real power unit taken apart (motion graphic) + its score
[ -f out/engine.mp4 ] || python3 -I tiktok/engine_mg.py out/engine.mp4
[ -f out/engine_score.wav ] || python3 -I tiktok/engine_score.py out/engine_score.wav
# AI voice-over lines (skip if you have your own recording: VO=... python3 tiktok/build.py)
[ -d out/vo ] || python3 -I tiktok/voice.py
