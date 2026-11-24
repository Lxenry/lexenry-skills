#!/usr/bin/env bash
# mix.sh —— 口播 + 音效 + BGM 混音（原片定稿参数：成片约 -15 LUFS，真峰值 ≤ -1.5 dBTP）
# 用法：bash mix.sh voice.wav sfx.wav bgm.wav out.wav
#   voice.wav = 已剪好的口播（念完最后一个字后 0.1 秒切掉）
#   bgm.wav   = 暗色电子/低频氛围类 BGM（自己有版权的），会自动压到 -32 LUFS 并在人声处避让
# 人声链：85Hz 高通 → 250Hz -1dB（去闷）→ 3.5kHz +1.75dB（清晰度）→ 8kHz 高架 +1dB → 压缩 3.2:1 → -14.5 LUFS
# BGM 链：3.5kHz -2.5dB（给人声让位）→ -32 LUFS → 侧链压缩（人声说话时压低）
# 注意：alimiter 一定要 level=0，否则它会把音量自动拉满
set -e
V=$1; S=$2; B=$3; OUT=${4:-mix.wav}
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
ffmpeg -y -loglevel error -i "$V" -i "$S" -i "$B" -filter_complex "\
[0]aresample=48000,highpass=f=85,equalizer=f=250:t=q:w=1.2:g=-1,equalizer=f=3500:t=q:w=1.0:g=1.75,highshelf=f=8000:g=1,\
acompressor=threshold=-21dB:ratio=3.2:attack=5:release=110:makeup=1,loudnorm=I=-14.5:TP=-1.5:LRA=8,apad,atrim=0:$D,asplit=2[v][sc];\
[2]aresample=48000,equalizer=f=3500:t=q:w=1.2:g=-2.5,loudnorm=I=-32:TP=-9,apad,atrim=0:$D[b0];\
[b0][sc]sidechaincompress=threshold=0.03:ratio=3:attack=20:release=350[b];\
[1]aresample=48000,apad,atrim=0:$D,volume=0.92[s];\
[v][s][b]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.79:level=0,\
afade=t=out:st=$(python3 -c "print(max(0,$D-0.04))"):d=0.04[o]" -map "[o]" -ar 48000 "$OUT"
# 检查响度：目标 I≈-15 LUFS
ffmpeg -hide_banner -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | tail -2
