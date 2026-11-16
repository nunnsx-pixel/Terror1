import sys, os, subprocess, time, importlib, multiprocessing as mp
import numpy as np
from common import *
import compose

PART = int(sys.argv[1]); OUT = sys.argv[2]
NF = int(60 * FPS)
mod = importlib.import_module(f"part{PART}")
mod.init()

def work(args):
    ci, f0, f1 = args
    out = f"build/p{PART}_chunk{ci:02d}.mp4"
    cmd = ["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{OW}x{OH}","-r",str(FPS),"-i","-",
           "-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p","-g","30","-x264-params","keyint=30:min-keyint=30:scenecut=0", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        im = compose.compose(PART, mod, fi / FPS, fi)
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    return out

if __name__ == "__main__":
    t0 = time.time()
    n = 20
    per = NF // n
    jobs = [(i, i * per, (i + 1) * per if i < n - 1 else NF) for i in range(n)]
    with mp.get_context("fork").Pool(4) as pool:
        outs = []
        for k, o in enumerate(pool.imap(work, jobs)):
            outs.append(o); print(f"chunk {k+1}/{n} done  {time.time()-t0:.0f}s", flush=True)
    lst = f"build/p{PART}_list.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(o)}'\n" for o in outs))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-c","copy",OUT], check=True)
    print("video ok", OUT, f"{time.time()-t0:.0f}s")
