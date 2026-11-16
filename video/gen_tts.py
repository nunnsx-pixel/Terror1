import asyncio, certifi, subprocess, sys, os
certifi.where = lambda: "/root/.ccr/ca-bundle.crt"
import edge_tts
from lines import LINES
async def one(k, voice, text, rate):
    out = f"tts/{k}.mp3"
    if os.path.exists(out) and os.path.getsize(out) > 1000: return
    c = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%")
    await c.save(out)
async def main():
    await asyncio.gather(*[one(k, v, t, r) for k, (v, t, r, p) in LINES.items()])
asyncio.run(main())
for k, (v, t, r, p) in LINES.items():
    wav = f"tts/{k}.wav"
    # converte p/ 44.1k mono, remove silêncio inicial/final, aplica pitch (rubberband)
    trim = "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.04"
    af = f"{trim},areverse,{trim},areverse"
    if abs(p) > 0.01:
        af += f",rubberband=pitch={2**(p/12):.4f}:formant=preserved"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"tts/{k}.mp3","-ar","44100","-ac","1","-af",af,wav],check=True)
    d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",wav]).decode())
    print(f"{k:12s} {d:5.2f}s  {len(t.split())} palavras")
