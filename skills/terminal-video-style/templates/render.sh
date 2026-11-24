#!/usr/bin/env bash
# render.sh —— 帧序列 + 音频 → 成片
# 用法：bash render.sh <帧目录> <输出.mp4> [混好的音频.wav]
#   不给音频时，用音效事件文件合成音效轨（示范用）：默认 events_demo.json，清单体示范用 EVENTS=events_demo_list.json
#   出 4K 母版：SIZE=2160:2880 bash render.sh ...（默认 1080:1440 预览）
set -e
FR=$1; OUT=$2; AUD=$3; SIZE=${SIZE:-1080:1440}
if [ -z "$AUD" ]; then
  N=$(ls "$FR"/*.png | wc -l); D=$(python3 -c "print($N/30)")
  python3 sfx.py "${EVENTS:-events_demo.json}" "$D"; AUD=sfx.wav
fi
D=$(python3 -c "import soundfile as sf;print(sf.info('$AUD').duration)")
# 末尾 40ms 淡出防爆音（念完最后一个字就结束，不留尾巴）
ffmpeg -y -loglevel error -framerate 30 -i "$FR/%04d.png" -i "$AUD" \
  -af "afade=t=out:st=$(python3 -c "print(max(0,$D-0.04))"):d=0.04" \
  -vf "scale=$SIZE:flags=lanczos" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
ls -la "$OUT"
