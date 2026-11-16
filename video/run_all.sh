#!/usr/bin/env bash
# Pipeline completo: TTS -> render das 2 partes -> áudio -> montagem.
# Requer: python3 (venv com requirements.txt), ffmpeg (com rubberband e libx264). Rode dentro de video/.
set -euo pipefail
mkdir -p tts build frames output
python gen_tts.py                      # vozes pt-BR (edge-tts, precisa de internet)
python render_video.py 1 build/part1_video.mp4
python render_video.py 2 build/part2_video.mp4
python audio_mix.py 1
python audio_mix.py 2
./mux.sh output
