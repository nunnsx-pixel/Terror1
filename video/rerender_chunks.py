import sys, os, subprocess, multiprocessing as mp
import render_video as R
if __name__ == "__main__":
    idx = [int(x) for x in sys.argv[3:]]
    n = 20; per = R.NF // n
    jobs = [(i, i * per, (i + 1) * per if i < n - 1 else R.NF) for i in idx]
    with mp.get_context("fork").Pool(4) as pool:
        for o in pool.imap(R.work, jobs): print("done", o, flush=True)
    outs = [f"build/p{R.PART}_chunk{i:02d}.mp4" for i in range(n)]
    open(f"build/p{R.PART}_list.txt", "w").write("".join(f"file '{os.path.abspath(o)}'\n" for o in outs))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",f"build/p{R.PART}_list.txt","-c","copy",R.OUT], check=True)
    print("video ok", R.OUT)
