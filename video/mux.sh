#!/usr/bin/env bash
# Junta vídeo + áudio de cada parte e gera o corte completo (Parte 1 + Parte 2 = 2 min).
set -euo pipefail
OUT="${1:-output}"
mkdir -p "$OUT"
for P in 1 2; do
  ffmpeg -y -loglevel error -i "build/part${P}_video.mp4" -i "build/p${P}_audio.wav" \
    -map 0:v -map 1:a -c:v libx264 -preset medium -crf 30 -maxrate 6M -bufsize 12M -pix_fmt yuv420p -c:a aac -b:a 192k -ar 44100 -shortest -movflags +faststart \
    "$OUT/A_Ultima_Live_Parte${P}.mp4"
done
printf "file '%s'\nfile '%s'\n" "$PWD/$OUT/A_Ultima_Live_Parte1.mp4" "$PWD/$OUT/A_Ultima_Live_Parte2.mp4" > build/full_list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i build/full_list.txt -c copy -movflags +faststart "$OUT/A_Ultima_Live_COMPLETO_2min.mp4"
ls -la "$OUT"
