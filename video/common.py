import numpy as np, math

FPS = 30
W, H = 540, 960          # resolução interna de render (sobe 2x -> 1080x1920)
OW, OH = 1080, 1920
FOCAL = 0.95 * W


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def _h(n, seed):
    return (np.sin((n + seed * 17.13) * 12.9898) * 43758.5453) % 1.0 * 2 - 1


def vnoise1(t, seed=0, freq=1.0):
    """ruido suave 1D em [-1,1]"""
    x = t * freq
    i = math.floor(x)
    f = x - i
    a, b = _h(i, seed), _h(i + 1, seed)
    u = f * f * (3 - 2 * f)
    return a * (1 - u) + b * u


def flicker(k, t, rate=0.9):
    """intensidade (0..1) da lampada fluorescente k no tempo t (pisca ritmico + instavel)"""
    ph = (t * rate + 0.173 * k) % 1.0
    v = 1.0
    if 0.76 < ph < 0.805:
        v = 0.06
    elif 0.86 < ph < 0.885:
        v = 0.30
    v *= 0.9 + 0.1 * vnoise1(t, k, 23.0)
    if math.sin(t * 3.1 + k * 7.7) * math.sin(t * 11.3 + k * 2.1) > 0.9:
        v *= 0.15
    return max(0.0, v)


def shake(t, amp=1.0, speed=1.0, seed=0):
    """tremor de mao: (dyaw, dpitch, droll, dx, dy) em rad/m"""
    s = speed
    dyaw = (vnoise1(t, seed + 1, 1.7 * s) * 0.012 + vnoise1(t, seed + 2, 5.3 * s) * 0.006) * amp
    dpit = (vnoise1(t, seed + 3, 1.9 * s) * 0.012 + vnoise1(t, seed + 4, 6.1 * s) * 0.006) * amp
    drol = (vnoise1(t, seed + 5, 1.3 * s) * 0.018 + vnoise1(t, seed + 6, 4.1 * s) * 0.006) * amp
    dx = vnoise1(t, seed + 7, 2.1 * s) * 0.012 * amp
    dy = vnoise1(t, seed + 8, 2.7 * s) * 0.012 * amp
    return dyaw, dpit, drol, dx, dy


def bob(t, freq=1.9, amp=1.0):
    """balanco de caminhada: (dy, dpitch, droll, dyaw)"""
    w = 2 * math.pi * freq * t
    return (math.sin(2 * w) * 0.018 * amp, math.sin(2 * w + 0.6) * 0.012 * amp,
            math.sin(w) * 0.020 * amp, math.sin(w + 1.1) * 0.010 * amp)


def impulse(t, t0, amp, decay=6.0, freq=0.0):
    """pancada com decaimento exponencial"""
    if t < t0:
        return 0.0
    d = t - t0
    v = amp * math.exp(-decay * d)
    if freq:
        v *= math.cos(2 * math.pi * freq * d)
    return v
