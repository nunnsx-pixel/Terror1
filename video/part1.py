import numpy as np, math
from PIL import Image, ImageFilter
from common import *
from engine import *
from sprites import *
import world as worldmod

WORLD = None
SP = {}
SLAM = 3.0           # armario bate na parede
DOORSLAM = 50.85     # porta bate no fundo -> bateria cai


def init():
    global WORLD, SP
    WORLD = worldmod.build_world1()
    SP = dict(clara=person("clara", "crossed"), marcos_n=person("marcos", "neutral"), marcos_neck=person("marcos", "neck"),
              marcos_pt=person("marcos", "point"), cabinet=cabinet(), arm=marcos_arm(),
              cables=[cable(i) for i in range(6)])


def kf(t, keys):
    """interpolacao suave por keyframes [(t,v),...]"""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


# integral da velocidade de caminhada (parte A)
_ts = np.linspace(0, 6, 1801)
_v = 1.7 * (1 - smoothstep(3.0, 4.8, _ts))
_z = 0.3 + np.cumsum(_v) * (_ts[1] - _ts[0])


def speed(t):
    return float(1.7 * (1 - smoothstep(3.0, 4.8, t))) if t < 6 else 0.0


def camera(t):
    zA = float(np.interp(t, _ts, _z))
    z_rest = float(_z[-1])
    z = zA if t < 6 else z_rest
    if t > 36.3:
        z = z_rest + kf(t, [(36.3, 0), (45.0, 6.8), (50.8, 7.9)])
    yaw = kf(t, [(5.0, 0.0), (7.3, math.pi + 0.10)]) if t < 20 else math.pi + 0.10
    yaw += math.sin(t * 0.37) * 0.03 if 7.3 < t < 34 else 0
    if t > 34.0:
        yaw = kf(t, [(34.0, math.pi + 0.10), (36.6, 2 * math.pi)])
    pitch = -0.03
    pitch += kf(t, [(21.0, 0), (22.6, -0.30), (27.8, -0.30), (29.4, 0.0)])
    pitch += kf(t, [(41.0, 0), (44.5, -0.09)])
    x = -0.15 * math.sin(t * 0.8) if t < 5 else 0.0
    x += kf(t, [(36.3, 0), (46.0, 0.30)])
    y = 1.38
    # balanco de caminhada
    sp = speed(t) / 1.7 if t < 6 else 0.0
    if t > 36.3:
        sp = max(sp, 0.45 * (1 - smoothstep(44.0, 46.0, t)))
    b = bob(t, 1.9, 1.0)
    yaw += b[3] * sp
    pitch += b[1] * sp
    roll = b[2] * sp
    y += b[0] * sp
    dyaw, dpit, drol, dx, dy = shake(t, 0.9 + 1.2 * (1 if t < 5 else 0.3), 1.0)
    yaw, pitch, roll, x, y = yaw + dyaw, pitch + dpit, roll + drol, x + dx, y + dy
    # pancada do armario: salto brusco para a direita
    yaw += impulse(t, SLAM, 0.34, 4.2) * math.cos(8 * (t - SLAM)) * 0.3 + impulse(t, SLAM, 0.28, 5.0)
    pitch += impulse(t, SLAM, 0.10, 6.0)
    roll += impulse(t, SLAM, 0.12, 5.0)
    # porta batendo no fundo: solavanco mecanico
    yaw += impulse(t, DOORSLAM, -0.22, 7.0) * math.cos(30 * (t - DOORSLAM))
    pitch += impulse(t, DOORSLAM, 0.16, 6.0)
    roll += impulse(t, DOORSLAM, -0.10, 5.0)
    z -= impulse(t, DOORSLAM, 0.35, 5.0)
    return dict(x=x, y=y, z=z, yaw=yaw, pitch=pitch, roll=roll)


def tubes(t):
    p = 1.0
    if SLAM <= t < SLAM + 0.16:
        p = 0.0                                   # apagao no impacto
    if DOORSLAM <= t < DOORSLAM + 0.22:
        p = 0.0
    st = [flicker(k, t + 0.0) * p for k in range(4)]
    if t > DOORSLAM + 0.22:                        # estrobo instavel no fim
        st = [flicker(k, t * 2.2) * (0.55 + 0.45 * math.sin(t * 40 + k)) * p for k in range(4)]
    return st


def marcos_pose(t):
    if t < 20.0:
        return "marcos_n"
    if t < 24.8:
        return "marcos_neck"
    return "marcos_pt"


def state(t):
    """parametros de render/HUD para o tempo t"""
    cam = camera(t)
    cz = cam["z"]
    lights = []
    sprites = []
    flare = []
    # lanternas dos amigos (5600K, azul frio)
    cool = (0.78, 0.9, 1.0)
    if 5.0 <= t < 36.6:
        jit = math.sin(t * 9.0) * 0.015
        lights.append(dict(kind="spot", pos=(-0.45, 1.15, 4.9), dir=(0.12 + jit, -0.30, 1), inner=0.10, outer=0.34, color=cool, i=2.2))
        mdir = (0.0, -0.28, 1) if t < 24.8 else (-0.18 + jit, -0.80, 1)
        lights.append(dict(kind="spot", pos=(0.55, 1.0, 4.7), dir=mdir, inner=0.10, outer=0.34, color=cool, i=(2.2 if t < 24.8 else 1.25)))
        flare = [((-0.45, 1.15, 4.9), 1.0), ((0.55, 1.0, 4.7), 1.0)]
    if t >= 34.0:
        k = smoothstep(34.0, 36.5, t)
        tgt = np.array([0.35, 1.15, 17.0])
        for (ox, oy, oz) in ((0.85, 1.25, -0.5), (-0.55, 1.2, -1.1)):
            p = np.array([cam["x"] + ox, oy, cz + oz])
            d = tgt - p
            lights.append(dict(kind="spot", pos=tuple(p), dir=tuple(d), inner=0.10, outer=0.34, color=cool, i=3.0 * k))
    # personagens (so aparecem com a camera virada pra tras)
    if 4.5 < t < 36.0:
        tremble = math.sin(t * 17.0) * 0.012
        breathe = 1.0 + math.sin(t * 2.4) * 0.004
        sprites.append(dict(img=SP["clara"], pos=(-0.25 + tremble, 0.0, 4.95), h=1.62 * breathe))
        sprites.append(dict(img=SP[marcos_pose(t)], pos=(0.38, 0.0, 4.75), h=1.76))
    # armario de arquivo
    if t < 6.2:
        if t < SLAM:
            cx_ = -0.58
        else:
            u = min(1.0, (t - SLAM) / 0.10)
            cx_ = -0.58 + (-1.04 + 0.58) * u * u
            if t > SLAM + 0.10:
                cx_ += 0.05 * math.exp(-9 * (t - SLAM - 0.10)) * math.cos(40 * (t - SLAM))
        rot = 0.0 if t < SLAM else 6 * math.exp(-8 * (t - SLAM)) * math.sin(30 * (t - SLAM))
        sprites.append(dict(img=SP["cabinet"], pos=(cx_, 0.0, 8.2), h=1.62, rot=rot))
    # fios pendurados
    for i, (zc, xc, hm) in enumerate([(2.2, -0.5, 1.2), (4.9, 0.7, 0.9), (7.4, -0.2, 1.4), (10.8, 0.6, 1.1), (12.7, -0.7, 1.3), (15.0, 0.1, 0.9)]):
        sw = math.sin(t * 1.3 + i) * 3.0
        sprites.append(dict(img=SP["cables"][i], pos=(xc, 3.0 - hm, zc), h=hm, rot=sw, light_gain=0.9))
    return cam, lights, sprites, flare


def render(t, fidx):
    cam, lights, sprites, flare = state(t)
    ts = tubes(t)
    frame, info = render_world(WORLD, cam, lights, t, ts, ambient=0.018)
    tube_lights = []
    for k, zk in enumerate(WORLD.tube_z):
        if ts[k] > 0.01 and abs(zk - cam["z"]) < 24:
            tube_lights.append(dict(kind="tube", pos=(0, WORLD.ch - 0.12, zk), color=WORLD.tube_color, i=ts[k] * 1.45))
    # sprites ordenados por profundidade
    sprites.sort(key=lambda s: -project(info["R"], cam, s["pos"])[2])
    for sp in sprites:
        draw_sprite(frame, sp, info, lights, tube_lights, ambient=0.03)
    # brilho das lanternas (lente) + feixe
    for (pos, k) in flare:
        pc = project(info["R"], cam, pos)
        if pc[2] > 0.3:
            s = FOCAL / pc[2]
            sx, sy_ = W / 2 + pc[0] * s, H / 2 - pc[1] * s
            glow(frame, sx, sy_, 46, (0.75, 0.9, 1.0), 0.85)
    # flash do impacto
    if SLAM <= t < SLAM + 0.5:
        fl = math.exp(-(t - SLAM) * 14)
        frame += fl * np.array([0.9, 0.85, 0.75], np.float32) * 0.9
        pc = project(info["R"], cam, (-0.9, 1.0, 8.2))
        if pc[2] > 0.3:
            s = FOCAL / pc[2]
            glow(frame, W / 2 + pc[0] * s, H / 2 - pc[1] * s, 260, (1.0, 0.9, 0.75), 1.6 * fl)
    # braco do Marcos entrando no quadro (tenta tocar a borda da porta e recua)
    if 44.8 < t < 49.6:
        u = kf(t, [(44.8, 0.0), (46.9, 1.0), (47.6, 1.0), (48.2, 0.15), (49.6, 0.0)])
        tr = math.sin(t * 38) * 4
        arm = SP["arm"]
        scale = 0.95
        aw, ah = int(arm.width * scale), int(arm.height * scale)
        a2 = arm.resize((aw, ah), Image.BILINEAR)
        x0 = int(W - 40 - (aw - 80) * u * 0.7 - 160 * u + tr)
        y0 = int(H * 0.50 + tr * 0.6)
        arr = np.asarray(a2, np.float32) / 255
        xs0, xs1 = max(0, x0), min(W, x0 + aw)
        ys0, ys1 = y0, y0 + ah
        if xs1 > xs0:
            a = arr[:, xs0 - x0:xs1 - x0]
            lit = a[..., :3] * np.array([0.95, 0.88, 0.85], np.float32) * (0.62 + 0.2 * np.sin(t * 12))
            frame[ys0:ys1, xs0:xs1] = frame[ys0:ys1, xs0:xs1] * (1 - a[..., 3:4]) + lit * a[..., 3:4]
    # ---- parametros de pos-processamento
    p = dict(grain=0.050, exposure=1.9, rgb_shift=1, tint=(1.0, 1.0, 1.0), glitch=0.0, static=0.0, saturation=0.95)
    if t >= DOORSLAM:
        k = (t - DOORSLAM) / (60 - DOORSLAM)
        p["glitch"] = 0.35 + 0.65 * min(1, k * 1.6) * (0.6 + 0.4 * abs(math.sin(t * 9)))
        p["static"] = 0.04 + 0.55 * k ** 1.3
        p["grain"] = 0.07 + 0.1 * k
    elif t > 3.0 and t < 3.4:
        p["glitch"] = 0.25 * math.exp(-(t - 3.0) * 6)
    # blackout no apagao
    if SLAM <= t < SLAM + 0.1 or DOORSLAM <= t < DOORSLAM + 0.15:
        p["exposure"] = 0.5
        p["blackout"] = 0.8
    out = post(frame, fidx, **p)
    # rack focus ao focalizar no cadeado
    r = kf(t, [(39.6, 0.0), (40.2, 4.0), (41.2, 2.2), (42.4, 0.0)]) if 39.6 < t < 42.4 else 0.0
    if t > 36.6 and t < 39.6:
        r = 0.0
    return out, dict(blur=r)


def hud(t):
    st = dict(clock="02:43 AM", battery=100, live="live", viewers="12,4 mil")
    from cues import viewers1
    st["viewers"] = viewers1(t)
    if t >= DOORSLAM:
        d = t - DOORSLAM
        if d < 0.5:
            st["battery"] = [100, 62, 100, 18, 40, 1][min(5, int(d * 12))]
            st["bat_red"] = d > 0.1
            st["bat_blink"] = int(d * 20) % 2 == 0
        else:
            st["battery"] = 1
            st["bat_red"] = True
            st["bat_blink"] = int(t * 2.5) % 2 == 0
        if d > 0.6:
            st["live"] = "off"
    return st
