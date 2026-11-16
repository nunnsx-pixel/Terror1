import sys, subprocess, math, os
import numpy as np
from scipy import signal
from scipy.io import wavfile
import cues

SR = 44100
rng = np.random.default_rng(7)
T = lambda n: np.arange(n) / SR


# ---------------------------------------------------------------- utilidades
def load(k, path=None):
    sr, x = wavfile.read(path or f"tts/{k}.wav")
    x = x.astype(np.float32) / 32768
    return x if x.ndim == 1 else x.mean(1)


def filt(x, kind, fc, order=4):
    if kind == "bp":
        fc = [max(20, fc[0]), min(SR / 2 - 100, fc[1])]
    sos = signal.butter(order, fc, btype={"lp": "low", "hp": "high", "bp": "band"}[kind], fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def noise(n):
    return rng.standard_normal(n).astype(np.float32)


def pink(n):
    w = noise(n)
    return signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400], w).astype(np.float32) * 3


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)) + 1e-9)


def norm(x, target=0.10):
    return x * (target / rms(x))


def reverb(x, rt60=1.2, wet=0.2, pre=0.012, lp=5500, tail=True):
    n = int(rt60 * SR)
    ir = noise(n) * np.exp(-6.9 * np.arange(n) / (rt60 * SR))
    ir = filt(ir, "lp", lp, 2)
    ir[:int(pre * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    y = signal.fftconvolve(x, ir).astype(np.float32)
    out = np.zeros(len(y), np.float32)
    out[:len(x)] += x * (1 - wet * 0.5)
    out += y * wet * 1.6
    return out if tail else out[:len(x)]


def whisper(x):
    f, t, Z = signal.stft(x, SR, nperseg=1024, noverlap=768)
    Z2 = np.abs(Z) * np.exp(1j * rng.uniform(0, 2 * np.pi, Z.shape))
    _, y = signal.istft(Z2, SR, nperseg=1024, noverlap=768)
    y = y[:len(x)].astype(np.float32)
    y = filt(y, "hp", 250, 2)
    return y * (rms(x) / rms(y))


def tremolo(x, hz, depth):
    return x * (1 - depth + depth * np.sin(2 * np.pi * hz * T(len(x))))


def ringmod(x, hz, mix=0.3):
    return x * (1 - mix) + x * np.sin(2 * np.pi * hz * T(len(x))) * mix * 1.6


def distort(x, g):
    return np.tanh(x * g) / np.tanh(g)


def comb(x, ms, fb=0.4, n=3):
    y = x.copy()
    d = int(ms * SR / 1000)
    for i in range(1, n + 1):
        y[d * i:] += x[:len(x) - d * i] * (fb ** i)
    return y


def pan_gains(p):
    a = (p + 1) * np.pi / 4
    return math.cos(a), math.sin(a)


def place(buf, x, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= len(buf) or len(x) == 0:
        return
    i1 = min(len(buf), i0 + len(x))
    gl, gr = pan_gains(pan)
    seg = x[:i1 - i0] * gain
    buf[i0:i1, 0] += seg * gl
    buf[i0:i1, 1] += seg * gr


def place_st(buf, x, t0, gain=1.0):
    i0 = int(t0 * SR)
    i1 = min(len(buf), i0 + len(x))
    buf[i0:i1] += x[:i1 - i0] * gain


# ---------------------------------------------------------------- sintese de efeitos
def thump(f0=60, dur=0.5, tau=0.12, drop=0.8):
    t = T(int(dur * SR))
    return (np.sin(2 * np.pi * f0 * (1 + drop * np.exp(-t / 0.03)) * t) * np.exp(-t / tau)).astype(np.float32)


def nburst(dur, lo, hi, tau):
    n = int(dur * SR)
    return (filt(noise(n), "bp", (lo, hi), 2) * np.exp(-T(n) / tau)).astype(np.float32)


def metal(freqs, dur, tau, amp=1.0):
    t = T(int(dur * SR))
    y = np.zeros_like(t)
    for i, f in enumerate(freqs):
        y += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (tau * (1 - 0.1 * i))) / (1 + 0.3 * i)
    return (y * amp).astype(np.float32)


def step(level=1.0, hard=0.6, f=95):
    n = int(0.16 * SR)
    t = T(n)
    body = np.sin(2 * np.pi * f * (1 + 0.6 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.035)
    click = filt(noise(n), "lp", 2600, 2) * np.exp(-t / 0.008) * hard
    return ((body * 0.8 + click * 0.5) * level).astype(np.float32)


def crash():
    n = int(2.2 * SR)
    y = np.zeros(n, np.float32)
    y[:int(0.9 * SR)] += thump(52, 0.9, 0.28, 1.2) * 1.0
    y[:int(0.5 * SR)] += nburst(0.5, 150, 4200, 0.13) * 1.1
    y[:int(1.5 * SR)] += metal([310, 570, 1130, 1790, 2610, 3400], 1.5, 0.35, 0.55)
    for _ in range(38):
        s = int(rng.uniform(0.12, 1.5) * SR)
        c = nburst(0.03, 3000, 11000, 0.006) * rng.uniform(0.15, 0.5)
        y[s:s + len(c)] += c
    return distort(y, 1.6) * 0.9


def glass_shatter(dur=1.2):
    n = int(dur * SR)
    y = np.zeros(n, np.float32)
    for k in range(70):
        s = int((rng.uniform(0, 1) ** 1.8) * (dur - 0.05) * SR)
        c = nburst(0.04, 2500 + rng.uniform(0, 3000), 12000, 0.008) * rng.uniform(0.1, 0.5) * (1 - s / n * 0.7)
        y[s:s + len(c)] += c
    return y


def drip():
    t = T(int(0.35 * SR))
    f = rng.uniform(900, 1700)
    return (np.sin(2 * np.pi * f * t * (1 + 0.4 * np.exp(-t / 0.01))) * np.exp(-t / 0.05)).astype(np.float32)


def creak(dur=1.2, f0=210):
    n = int(dur * SR)
    t = T(n)
    f = f0 * (1 + 0.35 * np.sin(2 * np.pi * 0.9 * t) + 0.2 * np.sin(2 * np.pi * 3.1 * t + 1))
    ph = np.cumsum(f) / SR * 2 * np.pi
    y = signal.sawtooth(ph) * 0.5
    y = filt(y.astype(np.float32), "bp", (300, 1800), 2)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (y * env * (0.6 + 0.4 * noise(n) * 0.2)).astype(np.float32)


def radio_static(dur, level=1.0, squeal=True):
    n = int(dur * SR)
    t = T(n)
    w = filt(noise(n), "bp", (700, 8500), 2)
    chop = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 13 * t + 3 * np.sin(2 * np.pi * 0.7 * t)))
    y = w * (0.6 + 0.4 * chop)
    # varredura de dial
    f = 900 + 2600 * np.abs(np.sin(2 * np.pi * 0.37 * t)) + 400 * np.sin(2 * np.pi * 7 * t)
    y += np.sin(np.cumsum(f) / SR * 2 * np.pi) * 0.12
    if squeal:
        env = np.clip(t / (dur * 0.7), 0, 1) ** 2
        fb = 2650 + 40 * np.sin(2 * np.pi * 0.6 * t)
        y += distort(np.sin(np.cumsum(fb) / SR * 2 * np.pi) * env * 1.4, 2.5) * 0.18
        y += np.sin(np.cumsum(fb * 1.5) / SR * 2 * np.pi) * env * 0.07
    return (y * level).astype(np.float32)


def breath_hyper(dur, rate=1.8, level=0.05):
    n = int(dur * SR)
    t = T(n)
    env = np.clip(np.sin(2 * np.pi * rate * t), 0, 1) ** 1.5
    return (filt(noise(n), "bp", (450, 3800), 2) * env * level).astype(np.float32)


def sob(level=0.2, dur=0.7, f0=340):
    dur = max(dur, 0.7)
    n = int(dur * SR)
    t = T(n)
    f = f0 * (1 - 0.22 * (t / dur)) * (1 + 0.025 * np.sin(2 * np.pi * 7 * t))
    src = signal.sawtooth(np.cumsum(f) / SR * 2 * np.pi).astype(np.float32)
    y = filt(src, "bp", (500, 900), 2) * 1.0 + filt(src, "bp", (1000, 1700), 2) * 0.6 + filt(src, "bp", (2400, 3200), 2) * 0.25
    inhale = np.zeros(n, np.float32)
    ni = int(0.13 * SR)
    inhale[:ni] = filt(noise(ni), "bp", (700, 4000), 2) * np.sin(np.pi * np.arange(ni) / ni) * 0.35
    env = np.zeros(n, np.float32)
    s0, s1 = int(0.16 * SR), int(0.62 * SR)
    env[s0:s1] = np.sin(np.pi * np.arange(s1 - s0) / (s1 - s0)) ** 0.7
    return ((y * env * 0.8 + inhale) * level).astype(np.float32)


def final_norm(buf, peak=0.92, drive=2.3):
    y = np.tanh(buf * drive) / np.tanh(drive)
    m = np.max(np.abs(y))
    return (y * (peak / m)).astype(np.float32) if m > peak else y.astype(np.float32)


def room_tone(n, level=0.012, lowfreq=900):
    return filt(pink(n), "lp", lowfreq, 2) * level


def drone(n, f=48.0, level=0.03, lfo=0.13):
    t = T(n)
    y = np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * (f * 1.5 + 0.7) * t) + 0.4 * np.sin(2 * np.pi * (f * 2.01) * t)
    return (y * (0.7 + 0.3 * np.sin(2 * np.pi * lfo * t)) * level).astype(np.float32)


# ---------------------------------------------------------------- vozes
def room_voice(x, wet=0.18, rt=1.1, lp=6800):
    return reverb(filt(x, "lp", lp, 2), rt, wet)


def voice(k, mode):
    x = load(k)
    if mode == "close":              # Lucas (microfone do celular, bem perto)
        x = filt(x, "hp", 90, 2)
        return norm(reverb(x, 0.7, 0.07), 0.12)
    if mode == "near":               # Clara/Marcos a ~3 m
        x = filt(x, "hp", 110, 2)
        return norm(room_voice(x, 0.2), 0.09)
    raise ValueError(mode)


# ====================================================================== PARTE 1
def mix_part1():
    import part1
    L = 60 * SR
    buf = np.zeros((L, 2), np.float32)
    n = L
    t = T(n)
    # ---- tubos fluorescentes: zumbido ligado ao piscar do video
    tg = np.arange(0, 60.0, 0.005)
    amp = np.array([np.mean(part1.tubes(x)) for x in tg], np.float32)
    env = np.interp(t, tg, amp).astype(np.float32)
    hum = sum(np.sin(2 * np.pi * 100 * h * t + h) / h for h in (1, 2, 3, 5)) * 0.018
    buzz = (hum * env).astype(np.float32)
    place(buf, buzz, 0, 1.0, 0)
    place(buf, room_tone(n, 0.010), 0, 1.0, 0)
    # ---- chiado estatico sutil de fundo (cortado pelo estrondo)
    st = filt(noise(int(3.0 * SR)), "hp", 2200, 2) * 0.006
    st *= (0.5 + 0.5 * (rng.random(len(st)) > 0.985))
    place(buf, st, 0, 1.0, 0)
    # ---- passos apressados (Lucas) nos primeiros 4.2s
    k = 0
    tt = 0.12
    while tt < 4.4:
        v = part1.speed(tt) / 1.7
        if v > 0.25:
            place(buf, step(0.95 * v + 0.15, 0.7), tt, 1.0, (-0.08 if k % 2 else 0.08))
        tt += 0.263 + (1 - v) * 0.15
        k += 1
    # ---- passos de alguem CORRENDO atras (apos o estrondo)
    for i in range(10):
        ts = 3.7 + i * 0.205 + rng.uniform(-0.01, 0.01)
        x = reverb(step(0.55 + 0.04 * i, 0.9, 80), 1.0, 0.3)
        place(buf, x, ts, 1.0, 0.55 - i * 0.09)
    # ---- estrondo do armario
    c = crash()
    place(buf, c, part1.SLAM - 0.012, 0.95, -0.25)
    place(buf, reverb(c[:int(0.8 * SR)], 1.4, 0.35), part1.SLAM, 0.5, 0.25)
    place(buf, glass_shatter(1.4), part1.SLAM + 0.35, 0.85, 0.3)
    # ---- sussurro aveludado colado no microfone ESQUERDO
    w = load("p1_whisper")
    w = whisper(w) * 0.55 + w * 0.45
    w = filt(w, "hp", 180, 2)
    w = reverb(norm(w, 0.10), 1.6, 0.25)
    wb = np.zeros((len(w), 2), np.float32)
    wb[:, 0] = w * 1.0
    wb[:, 1] = w * 0.10
    place_st(buf, wb, 3.35, 1.0)
    # ---- falas
    spec = {"p1_lucas1": ("close", 0.0, 1.05), "p1_clara1": ("near", 0.14, 0.95), "p1_marcos1": ("near", -0.2, 0.95),
            "p1_lucas2": ("close", 0.0, 1.0), "p1_marcos2": ("near", -0.2, 0.95), "p1_lucas3": ("close", 0.0, 1.0),
            "p1_marcos3": ("near", 0.30, 0.95)}
    for (k_, st_, spk) in cues.PART1:
        if k_ == "p1_whisper":
            continue
        mode, pan, g = spec[k_]
        x = voice(k_, mode)
        if k_ == "p1_lucas1":
            x = distort(x * 1.6, 1.8) * 0.8            # grito de adrenalina
        if k_ == "p1_clara1":
            x = tremolo(x, 6.0, 0.10)
        place(buf, x, st_, g, pan)
    # ---- drone de tensao crescente + rangidos + gotas
    dr = drone(n, 48, 1.0) * np.interp(t, [0, 5, 35, 50, 50.9, 60], [0.0, 0.015, 0.05, 0.08, 0.0, 0.0])
    place(buf, dr.astype(np.float32), 0, 1.0, 0)
    for ts in (12.2, 24.0, 31.3, 38.5, 42.0):
        place(buf, creak(rng.uniform(0.9, 1.6), rng.uniform(150, 260)), ts, 0.18, rng.uniform(-0.6, 0.6))
    for ts in np.cumsum(rng.uniform(1.8, 3.6, 22)) + 5:
        if ts < 50.8:
            place(buf, reverb(drip(), 1.5, 0.3, tail=False), ts, 0.08, rng.uniform(-0.8, 0.8))
    # ---- seção C: passos lentos e cautelosos (36.6 -> 45)
    tt = 36.8
    while tt < 45.0:
        place(buf, step(0.30, 0.5, 90), tt, 1.0, 0.05)
        tt += 0.78 + 0.2 * rng.random()
    # ---- porta pesada bate no fundo do corredor (50.85) + solavanco
    D = part1.DOORSLAM
    boom = np.zeros(int(2.4 * SR), np.float32)
    boom += thump(42, 1.1, 0.30, 1.4)[:len(boom)] * 1.1 if False else 0
    b = np.pad(thump(42, 1.1, 0.30, 1.4), (0, int(1.3 * SR))) * 1.2
    b += np.pad(nburst(0.4, 90, 1800, 0.10), (0, len(b) - int(0.4 * SR))) * 0.9
    b += np.pad(metal([210, 480, 920, 1400], 1.4, 0.30, 0.35), (0, len(b) - int(1.4 * SR)))
    place(buf, distort(reverb(b, 1.8, 0.35), 1.4), D, 0.95, 0.25)
    # ---- O som ambiente CORTA: silencia tudo que vem antes (exceto estrondo) e entra a estatica
    cut = int((D + 0.12) * SR)
    fade = np.ones(L, np.float32)
    fade[cut:] = 0
    keep = buf[int(D * SR):int((D + 0.9) * SR)].copy()
    buf *= fade[:, None]
    # reinsere a pancada da porta (já aplicada) sem a ambientacao: o proprio 'b' foi adicionado antes do corte -> recoloca
    place(buf, distort(reverb(b, 1.8, 0.35), 1.4), D, 0.95, 0.25)
    # ---- estatica estridente de radio analogico + microfonia, ecoando nas caixas do hospital
    sdur = 60 - (D + 0.45)
    rs = radio_static(sdur, 1.0, True)
    rs = rs + 0.0
    echo = np.zeros(len(rs) + int(0.5 * SR), np.float32)
    echo[:len(rs)] += rs
    for dly, g in ((0.17, 0.42), (0.34, 0.22)):
        d = int(dly * SR)
        echo[d:d + len(rs)] += rs * g
    amp_env = np.interp(T(len(echo)), [0, 0.2, 2.0, sdur], [0.15, 0.45, 0.75, 0.9]).astype(np.float32)
    echo = filt(echo, "hp", 300, 2) * amp_env
    pl, pr = echo, np.roll(echo, int(0.011 * SR))
    st2 = np.stack([pl, pr], 1)
    place_st(buf, st2, D + 0.45, 0.30)
    out = final_norm(buf, 0.9)
    return out


# ====================================================================== PARTE 2
def mix_part2():
    import part2
    L = 60 * SR
    buf = np.zeros((L, 2), np.float32)
    n = L
    t = T(n)
    END = part2.END_T
    # ---- ambiente: tom de sala escuro, drone, bzz fraquinho do tubo moribundo
    tg = np.arange(0, 60.0, 0.01)
    amp = np.array([part2.tubes(x)[3] + part2.tubes(x)[2] for x in tg], np.float32)
    env = np.interp(t, tg, amp).astype(np.float32)
    buzz = (np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t)) * env * 0.04
    place(buf, buzz.astype(np.float32), 0, 1.0, 0.3)
    place(buf, room_tone(n, 0.014, 700), 0, 1.0, 0)
    # silencio absoluto a partir da queda ate a mao: o drone some
    dgain = np.interp(t, [0, 10, 36, 49.7, 50.3, 52, 53.8, 54.3, 59.5, END], [0.012, 0.03, 0.05, 0.05, 0.0, 0.0, 0.0, 0.04, 0.10, 0.12]).astype(np.float32)
    place(buf, drone(n, 41, 1.0) * dgain, 0, 1.0, 0)
    # ---- respiração hiperventilada de Lucas e choro de Clara (0 -> 24)
    br = breath_hyper(24, 1.7, 0.05) * np.interp(T(24 * SR), [0, 8, 24], [1.0, 0.8, 0.3]).astype(np.float32)
    place(buf, br, 0.0, 1.0, 0.0)
    for ts in (0.35, 1.6, 2.9, 4.2, 5.7, 7.1, 15.0, 16.2, 17.6):
        s = sob(0.20 if ts < 8 else 0.10, rng.uniform(0.6, 0.8), rng.uniform(300, 380))
        place(buf, room_voice(s, 0.25, 1.0, 5000), ts, 1.0, -0.45)
    # ---- falas
    spec = {"p2_lucas1": ("close", 0.0, 0.95), "p2_clara1": ("near", -0.35, 1.0), "p2_lucas2": ("close", 0.0, 1.0),
            "p2_lucas3": ("close", 0.0, 1.0), "p2_clara2": ("near", 0.3, 0.8)}
    for (k_, st_, spk) in cues.PART2:
        if k_ in ("p2_marcos1", "p2_final"):
            continue
        mode, pan, g = spec[k_]
        x = voice(k_, mode)
        if k_ == "p2_lucas1":
            w = whisper(load(k_))
            x = norm(reverb(filt(w * 0.65 + load(k_) * 0.40, "hp", 120, 2), 0.7, 0.08), 0.11)       # sussurro desesperado
            x = tremolo(x, 5.5, 0.12)
        if k_ == "p2_clara1":
            x = tremolo(x, 6.5, 0.16)
        if k_ == "p2_lucas2":
            x = distort(x * 1.3, 1.5) * 0.9 + filt(noise(len(x)), "hp", 1500, 2) * 0.012          # voz rouca, grito baixo
        if k_ == "p2_lucas3":
            x = distort(x * 2.4, 2.8) * 0.75                                                        # voz rasgando a garganta
        if k_ == "p2_clara2":
            x = reverb(filt(x, "lp", 3600, 3), 1.8, 0.45, 0.02)                                      # abafada pelo eco
            x = comb(x, 85, 0.35, 2)
        place(buf, x, st_, g, pan)
    # ---- Marcos: voz possuída (metálica e cavernosa)
    m = load("p2_marcos1")
    m2 = ringmod(m, 38, 0.30)
    deep = np.interp(np.arange(len(m)) * 0.5, np.arange(len(m)), m).astype(np.float32)           # oitava abaixo (mais lenta)
    layer = filt(norm(m2, 0.12), "lp", 7000, 2) + filt(np.pad(deep, (0, len(m) - len(deep)))[:len(m)] * 0.0 + 0, "lp", 500, 2)
    mm = comb(norm(layer, 0.12), 6.5, 0.5, 4) * 0.8 + norm(whisper(m), 0.03)
    mm = reverb(mm, 2.8, 0.42, 0.03, 4500)
    place(buf, mm, 28.6, 1.0, 0.0)
    # sub grave sob a fala
    place(buf, (np.sin(2 * np.pi * 52 * T(int(7 * SR))) * np.hanning(int(7 * SR)) * 0.05).astype(np.float32), 28.4, 1.0, 0)
    # ---- giro da cabeça: estalos de osso + rangido
    for ts, g in ((24.6, 0.5), (25.15, 0.9), (25.9, 0.6), (26.9, 0.5), (27.35, 1.0), (27.85, 0.8), (28.5, 1.0)):
        for j in range(rng.integers(3, 7)):
            c = nburst(0.025, 300, 2400, 0.007) * g * 0.5
            place(buf, c, ts + j * rng.uniform(0.006, 0.03), 1.0, rng.uniform(-0.2, 0.2))
        place(buf, thump(70, 0.25, 0.06, 0.2) * 0.25 * g, ts, 1.0, 0)
    place(buf, creak(4.2, 120), 24.2, 0.22, 0.0)
    # ---- corrida desgovernada (36 -> 41.6): passos rápidos, respiração, objetos
    tt = 35.95
    k = 0
    while tt < part2.DOOR_T - 0.02:
        place(buf, step(0.85, 0.9, 85 + 10 * (k % 2)), tt, 1.0, -0.1 if k % 2 else 0.1)
        place(buf, step(0.7, 0.8, 110), tt + 0.02, 1.0, 0.35 if k % 2 else 0.25)     # Clara correndo ao lado
        tt += 0.333
        k += 1
    for ts in np.arange(36.2, part2.DOOR_T, 0.62):
        place(buf, breath_hyper(0.45, 1.1, 0.13), ts, 1.0, 0)
    place(buf, nburst(0.5, 200, 3000, 0.2) * 0.25, 35.4, 1.0, 0)               # virada brusca
    # ---- a porta de ferro bate e lacra: estrondo + correntes
    D = part2.DOOR_T
    b = np.pad(thump(40, 1.2, 0.34, 1.5), (0, int(1.2 * SR))) * 1.3
    b += np.pad(nburst(0.5, 80, 2200, 0.12), (0, len(b) - int(0.5 * SR))) * 1.0
    b += np.pad(metal([190, 420, 860, 1300, 2100], 1.6, 0.35, 0.45), (0, len(b) - int(1.6 * SR)))
    place(buf, distort(reverb(b, 2.0, 0.35), 1.5), D - 0.015, 1.0, 0)
    for j in range(95):                                                         # correntes brotando: tilintar metálico seco
        ts = D + 0.1 + rng.uniform(0, 1.9) ** 1.2
        f = rng.uniform(1800, 5200)
        c = metal([f, f * 1.43, f * 2.1], 0.22, 0.05, 0.12) * rng.uniform(0.4, 1.0)
        place(buf, c, ts, 1.0, rng.uniform(-0.8, 0.8))
    for j in range(7):
        place(buf, nburst(0.35, 400, 3500, 0.09) * 0.22, D + 0.15 + j * 0.2, 1.0, rng.uniform(-0.7, 0.7))
    # ---- socos na porta
    for i, pt in enumerate(part2.PUNCHES):
        g = 0.75 + 0.25 * (i % 3) / 2
        hit = np.pad(thump(78, 0.5, 0.11, 0.9), (0, int(0.6 * SR))) * 0.95
        hit += np.pad(metal([300, 610, 1180, 1760], 1.0, 0.28, 0.35), (0, len(hit) - int(1.0 * SR))) if len(hit) > int(1.0 * SR) else 0
        place(buf, distort(reverb(hit, 1.2, 0.25), 1.3), pt, g, 0)
        for j in range(5):
            place(buf, metal([rng.uniform(2200, 4800)], 0.18, 0.04, 0.1), pt + 0.02 + j * 0.03, 1.0, rng.uniform(-0.6, 0.6))
    # ---- queda do celular (49.8): impacto plástico + deslize + quiques
    F = part2.FALL_T
    place(buf, nburst(0.25, 100, 2500, 0.05) * 0.7, F + 0.30, 1.0, 0.1)
    place(buf, thump(130, 0.2, 0.05, 0.5) * 1.0, F + 0.33, 1.0, 0.1)
    for dt, g in ((0.46, 0.5), (0.58, 0.3), (0.66, 0.18)):
        place(buf, thump(170, 0.12, 0.03, 0.3) * g, F + dt, 1.0, 0.1)
        place(buf, nburst(0.08, 800, 5000, 0.02) * g * 0.7, F + dt, 1.0, 0.1)
    place(buf, filt(noise(int(0.5 * SR)), "bp", (500, 4500), 2) * np.hanning(int(0.5 * SR)) * 0.15, F + 0.4, 1.0, 0.2)   # arrasto
    # ---- lanterna do celular pisca duas vezes e apaga: estalos elétricos
    for ts in (50.50, 50.62, 51.10, 51.20, 51.28, 51.36, 51.50):
        place(buf, nburst(0.03, 1500, 9000, 0.006) * 0.35, ts, 1.0, 0.05)
        place(buf, thump(120, 0.05, 0.01) * 0.2, ts, 1.0, 0.05)
    # ---- passos pesados e arrastados no silêncio absoluto (50.9 -> 53.6)
    for i, ts in enumerate((51.55, 52.15, 52.65, 53.05, 53.40)):
        g = 0.35 + 0.18 * i
        x = np.pad(thump(58, 0.5, 0.09, 0.4), (0, int(0.4 * SR))) * 0.9
        drag = np.pad(filt(noise(int(0.4 * SR)), "bp", (200, 1400), 2) * np.hanning(int(0.4 * SR)) * 0.35, (int(0.08 * SR), 0))
        x[:len(drag)] += drag[:len(x)]
        place(buf, reverb(x, 1.4, 0.3), ts, g, 0.7 - 0.18 * i)
    # ---- a mão pega o celular (53.6): ruído de manuseio
    place(buf, filt(noise(int(0.5 * SR)), "bp", (300, 3000), 2) * np.hanning(int(0.5 * SR)) * 0.3, 53.55, 1.0, 0)
    place(buf, thump(90, 0.2, 0.05) * 0.5, 53.85, 1.0, 0)
    # ---- voz final: várias vozes metálicas
    fin = load("p2_final")
    lay = []
    for st_, fn, g, pan in ((0.0, None, 1.0, 0.0), (0.035, -5, 0.65, -0.5), (0.060, +3, 0.45, 0.55), (0.09, -9, 0.5, 0.0)):
        if fn is None:
            y = fin
        else:
            y = pitch_shift_cached(fin, fn)
        y = comb(y, rng.uniform(5, 8), 0.5, 3)
        if fn in (-5, -9):
            y = ringmod(y, rng.uniform(45, 75), 0.35)
        lay.append((st_, norm(y, 0.10) * g, pan))
    wh = norm(whisper(fin), 0.07)
    lay.append((0.02, wh, 0.0))
    n_end = max(len(y) for _, y, _ in lay) + int(0.3 * SR)
    sumst = np.zeros((int(n_end + 0.2 * SR), 2), np.float32)
    for off, y, pan in lay:
        gl, gr = pan_gains(pan)
        o = int(off * SR)
        sumst[o:o + len(y), 0] += y * gl
        sumst[o:o + len(y), 1] += y * gr
    rv = np.stack([reverb(sumst[:, 0], 3.0, 0.45, 0.03, 4500, tail=False), reverb(sumst[:, 1], 3.3, 0.45, 0.04, 4500, tail=False)], 1)
    place_st(buf, rv, 53.7, 1.0)
    # corta tudo no preto final
    cut = int(END * SR)
    buf[cut:] = 0
    return final_norm(buf, 0.9)


_cache = {}


def pitch_shift_cached(x, semitones):
    key = (len(x), semitones)
    if key in _cache:
        return _cache[key]
    tmp_in, tmp_out = "build/_ps_in.wav", f"build/_ps_out.wav"
    wavfile.write(tmp_in, SR, (x * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_in, "-af", f"rubberband=pitch={2 ** (semitones / 12):.4f}:formant=preserved", tmp_out], check=True)
    y = load(None, tmp_out)
    _cache[key] = y
    return y


if __name__ == "__main__":
    part = int(sys.argv[1])
    out = mix_part1() if part == 1 else mix_part2()
    wavfile.write(f"build/p{part}_audio.wav", SR, (out * 32767).astype(np.int16))
    print("audio ok", part, "peak", float(np.max(np.abs(out))), "rms", float(np.sqrt(np.mean(out ** 2))), "dur", len(out) / SR)
