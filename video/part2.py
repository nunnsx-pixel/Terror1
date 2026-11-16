import numpy as np, math
from PIL import Image, ImageFilter, ImageDraw
from common import *
from engine import *
from sprites import *
import world as worldmod
from part1 import kf

WORLD = None
SP = {}
DOOR_T = 41.7          # porta de ferro bate e lacra
FALL_T = 49.8          # camera escorrega das maos
HAND_T0, HAND_T1 = 52.5, 53.9
FACE_T = 54.3
END_T = 59.62          # corte seco para o preto
ZEND = 22.5


def init():
    global WORLD, SP
    WORLD = worldmod.build_world2()
    WORLD.ze = ZEND
    SP = dict(
        huddle_down=clara_huddle(False), huddle_up=clara_huddle(True),
        marcos_body=person("marcos", "torn", view="back", head=False, possessed=True),
        mh_back=head_sprite("marcos", "back", True), mh_front=head_sprite("marcos", "front", True),
        clara_back=person("clara", "neutral", view="back"),
        clara_poss=person("clara", "neutral", possessed=True, tilt=11),
        lucas=lucas_close(), hand=pale_hand(),
        cables=[cable(i + 10) for i in range(6)],
    )


# ------------------------------------------------------------------------------------ camera
PUNCHES = [44.55, 45.45, 46.15, 47.0, 47.65, 48.4, 49.05]


def camera(t):
    x, y, z = 0.15, 1.35, 11.0
    yaw = kf(t, [(0, 0.0), (4.0, -0.10), (7.0, -0.40), (14.0, -0.38), (17.0, 0.0)])
    pitch = kf(t, [(0, -1.25), (3.5, -1.20), (6.5, -0.45), (9.5, -0.18), (15.5, -0.12), (18.0, -0.05)])
    zoom = 1.0
    if t < 15:
        # respiracao ofegante
        pitch += math.sin(2 * math.pi * 0.95 * t) * 0.022
        yaw += math.sin(2 * math.pi * 0.47 * t + 1) * 0.012
        y = 1.15
    if 15 <= t < 35.3:
        z = kf(t, [(15, 11.0), (24, 15.6), (30, 16.8)])
        y = 1.35
        pitch = -0.05
        yaw = 0.0 + math.sin(t * 0.5) * 0.01
        zoom = kf(t, [(22.5, 1.0), (27.8, 2.0), (35.0, 2.0)])
        if t < 17.0:
            z, y = 11.0 + 0.0, 1.30
            yaw = kf(t, [(14, -0.38), (17.0, 0.0)])
            pitch = kf(t, [(14, -0.14), (17.0, -0.05)])
        elif t < 24:
            z = kf(t, [(15, 11.0), (24, 15.6)])
    if t >= 35.3:
        zoom = kf(t, [(35.3, 2.0), (35.5, 1.0)])
        z = 16.8
        yaw = kf(t, [(35.3, 0.0), (36.0, math.pi)])
        pitch = -0.06
        if t >= 36.0:
            z = 16.8 - kf(t, [(36.0, 0.0), (41.6, 14.2)]) * 1.0
            z = max(z, 2.6)
            yaw = math.pi
            y = 1.35
        if t >= DOOR_T:
            z = 2.55
    # corrida desgovernada
    if 35.4 <= t < DOOR_T:
        k = min(1.0, (t - 35.4) / 0.5)
        sh = shake(t, 5.5 * k, 2.4, 3)
        b = bob(t, 1.5, 2.6 * k)
        yaw, pitch, roll_b = yaw + sh[0] + b[3], pitch + sh[1] + b[1], sh[2] + b[2]
        x, y = x + sh[3] * 3, y + b[0]
    else:
        roll_b = 0.0
        amp = 0.6 if t < 49.6 else 0.0
        sh = shake(t, amp + (1.2 if (t < 15) else 0.0), 1.0, 9)
        yaw, pitch, roll_b, x, y = yaw + sh[0], pitch + sh[1], roll_b + sh[2], x + sh[3], y + sh[4]
    # porta bate: solavanco
    yaw += impulse(t, DOOR_T, 0.18, 6.0) * math.cos(28 * (t - DOOR_T))
    pitch += impulse(t, DOOR_T, 0.18, 6.0)
    roll_b += impulse(t, DOOR_T, 0.12, 5.0)
    # socos na porta
    if DOOR_T + 2.2 < t < FALL_T:
        z = 2.55
        for pt in PUNCHES:
            z -= impulse(t, pt, 0.0, 9.0)
            pitch += impulse(t, pt, 0.07, 14.0) * math.cos(32 * (t - pt))
            yaw += impulse(t, pt, 0.04 * (-1 if int(pt * 10) % 2 else 1), 12.0) * math.cos(25 * (t - pt))
            y += impulse(t, pt, -0.04, 12.0)
        sh = shake(t, 2.0, 2.2, 21)
        yaw, pitch, roll_b = yaw + sh[0], pitch + sh[1], roll_b + sh[2]
        x = 0.1 + sh[3] * 2
    # queda do celular: voa, gira e para olhando pro teto
    if t >= FALL_T:
        yaw = math.pi + kf(t, [(FALL_T, 0.0), (FALL_T + 0.6, 0.9)]) * math.exp(-(t - FALL_T) * 1.2)
        y = kf(t, [(FALL_T, 1.35), (FALL_T + 0.34, 0.07), (FALL_T + 0.46, 0.14), (FALL_T + 0.6, 0.07)])
        pitch = kf(t, [(FALL_T, -0.1), (FALL_T + 0.35, 0.9), (FALL_T + 0.8, 1.38)])
        roll_b = kf(t, [(FALL_T, 0.0), (FALL_T + 0.3, 2.4), (FALL_T + 0.7, 0.32)])
        z = 2.50 + 0.12 * kf(t, [(FALL_T, 0), (FALL_T + 0.5, 1)])
        x = 0.1 + 0.3 * kf(t, [(FALL_T, 0), (FALL_T + 0.5, 1)])
        if t > FALL_T + 1.0:
            roll_b = 0.32 + math.sin(t * 0.9) * 0.01
            pitch = 1.38 + math.sin(t * 0.7) * 0.01
        yaw += impulse(t, FALL_T + 0.35, 0.05, 20.0)
    return dict(x=x, y=y, z=z, yaw=yaw, pitch=pitch, roll=roll_b, zoom=zoom)


def torch_on(t):
    if t < 50.5:
        return 1.0
    if t < 50.62:
        return 0.0
    if t < 51.1:
        return 1.0
    if t < 51.2:
        return 0.0
    if t < 51.5:
        return 0.75 if int(t * 40) % 2 == 0 else 0.1
    return 0.0


def tubes(t):
    return [0.0, 0.0, 0.10 * flicker(5, t * 1.4) * (1 if math.sin(t * 2.3) > -0.4 else 0.0), 0.20 * flicker(3, t * 1.1)]


# ------------------------------------------------------------------------------------ marcos: giro de cabeça
def head_angle(t):
    # 0 = de costas, pi = de frente. movimento truncado, mecanico
    base = kf(t, [(24.0, 0.0), (25.2, 0.55), (26.0, 0.55), (27.4, 2.2), (27.8, 2.2), (28.6, math.pi)])
    return base


def marcos_sprites(t, info_cam):
    out = []
    mz = 21.55
    sway = math.sin(t * 0.7) * 0.004
    out.append(dict(img=SP["marcos_body"], pos=(0.0 + sway, 0.0, mz), h=1.76, light_gain=1.0))
    th = head_angle(t)
    if th < math.pi / 2:
        hs, wf = SP["mh_back"], max(0.30, math.cos(th))
    else:
        hs, wf = SP["mh_front"], max(0.30, abs(math.cos(th)))
    img = hs.resize((max(2, int(hs.width * wf)), hs.height), Image.BILINEAR)
    tilt = 0.0
    if th > 2.2:
        tilt = -12 * smoothstep(2.2, math.pi, th)
    out.append(dict(img=img, pos=(0.0 + sway, 1.337, mz), h=0.48, rot=tilt, light_gain=1.35))
    return out


# ------------------------------------------------------------------------------------ cena
def render(t, fidx):
    if t >= END_T:
        return np.zeros((H, W, 3), np.float32), dict(black=1.0, no_caption=True)
    WORLD.tex[5] = WORLD.back_closed if t >= DOOR_T else WORLD.back_ajar
    face_shot = t >= FACE_T
    if face_shot:
        cam = dict(x=0.0, y=1.4, z=5.0, yaw=0.0, pitch=-0.02, roll=0.0, zoom=1.0)
    else:
        cam = camera(t)
    R = rot(cam["yaw"], cam["pitch"], cam["roll"])
    fwd = R[:, 2]
    cpos = np.array([cam["x"], cam["y"], cam["z"]], np.float32)
    lights = []
    tor = torch_on(t) if not face_shot else 0.0
    if t < 50.5 or (50.5 <= t < 51.6):
        pass
    screen_i = 0.55 * (1.0 if t < FACE_T else 1.0)
    if not face_shot:
        lights.append(dict(kind="point", pos=tuple(cpos + np.array([0, -0.05, 0.1], np.float32)), color=(0.40, 0.58, 1.0), i=screen_i, fall=2.2))
        if tor > 0:
            lights.append(dict(kind="spot", pos=tuple(cpos), dir=tuple(fwd), inner=0.18, outer=0.62, color=(0.62, 0.78, 1.0), i=2.1 * tor * (0.40 + 0.60 * smoothstep(3.0, 8.0, t)), fall=0.20))
    else:
        lights.append(dict(kind="point", pos=(0.1, 1.2, 5.6), color=(0.40, 0.58, 1.0), i=0.9, fall=1.4))
        lights.append(dict(kind="point", pos=(0.4, 1.6, 6.2), color=(0.55, 0.7, 1.0), i=1.5, fall=2.5))
    ts = tubes(t)
    frame, info = render_world(WORLD, cam, lights, t, ts, ambient=0.006)
    tube_lights = []
    for k, zk in enumerate(WORLD.tube_z):
        if ts[k] > 0.01:
            tube_lights.append(dict(kind="tube", pos=(0, WORLD.ch - 0.12, zk), color=WORLD.tube_color, i=ts[k] * 1.45))
    sprites = []
    if not face_shot:
        # Clara
        if t < 36.1:
            sprites.append(dict(img=SP["huddle_up"] if t >= 9.6 else SP["huddle_down"], pos=(-0.92, 0.0, 13.0), h=0.98 if t >= 9.6 else 0.94, light_gain=0.62))
        else:
            run = 1.0 if t < DOOR_T else 0.0
            cz = min(13.0, cam["z"] - 1.45)
            if t >= DOOR_T:
                cz = 1.15
            bounce = abs(math.sin(t * 2 * math.pi * 1.5)) * 0.07 * run
            sprites.append(dict(img=SP["clara_back"], pos=((-0.45 if t < DOOR_T else -0.75) + math.sin(t * 9) * 0.03 * run, bounce, cz), h=1.62, rot=math.sin(t * 2 * math.pi * 1.5) * 3 * run, light_gain=0.7))
        # Marcos (parado de costas diante da parede de tijolos)
        if t < 36.5:
            sprites += marcos_sprites(t, cam)
    else:
        # Clara possuida ao fundo, desfocada
        sprites.append(dict(img=SP["clara_poss"], pos=(0.62, 0.0, 7.0), h=1.62, light_gain=1.7))
    sprites.sort(key=lambda s: -project(info["R"], cam, s["pos"])[2])
    for sp in sprites:
        draw_sprite(frame, sp, info, lights, tube_lights, ambient=0.012)
    # luz da lanterna de Marcos / brilho de tela
    # correntes enferrujadas brotando das paredes
    if DOOR_T + 0.1 <= t < FALL_T + 0.45 and not face_shot:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        anchors = [((-1.3, 0.5, 1.5), (-0.30, 0.7, 0.03)), ((-1.3, 1.4, 1.9), (-0.15, 1.35, 0.03)), ((-1.3, 2.4, 1.3), (-0.05, 2.0, 0.03)),
                   ((1.3, 0.8, 1.7), (0.30, 0.9, 0.03)), ((1.3, 1.7, 1.2), (0.15, 1.5, 0.03)), ((1.3, 2.5, 1.8), (0.10, 2.1, 0.03)),
                   ((-0.4, 3.0, 1.1), (-0.10, 2.2, 0.03)), ((0.5, 0.0, 1.4), (0.15, 0.3, 0.03))]
        for i, (a, b) in enumerate(anchors):
            grow = smoothstep(DOOR_T + 0.1 + i * 0.07, DOOR_T + 0.9 + i * 0.07, t)
            if grow <= 0:
                continue
            pa, pb = project(info["R"], cam, a), project(info["R"], cam, b)
            if pa[2] < 0.2 or pb[2] < 0.2:
                continue
            sa, sb = FOCAL * cam.get("zoom", 1) / pa[2], FOCAL * cam.get("zoom", 1) / pb[2]
            p0 = (W / 2 + pa[0] * sa, H / 2 - pa[1] * sa)
            p1 = (W / 2 + pb[0] * sb, H / 2 - pb[1] * sb)
            draw_chain(ld, p0, p1, grow, link=max(10, int(0.07 * (sa + sb) / 2)))
        arr = np.asarray(layer, np.float32) / 255
        lit = arr[..., :3] * np.array([0.55, 0.62, 0.8], np.float32) * (0.55 + 0.45 * tor_ok(t))
        frame[...] = frame * (1 - arr[..., 3:4]) + lit * arr[..., 3:4]
    # flash na pancada da porta
    if DOOR_T <= t < DOOR_T + 0.4:
        fl = math.exp(-(t - DOOR_T) * 12)
        frame += fl * np.array([0.5, 0.6, 0.85], np.float32) * 0.9
    # ----- mao pálida pegando o celular
    if HAND_T0 <= t < FACE_T and not face_shot:
        u = smoothstep(HAND_T0, HAND_T1, t)
        h_px = int(H * (0.18 + 1.65 * u ** 1.6))
        hw_px = int(h_px * SP["hand"].width / SP["hand"].height)
        im = SP["hand"].resize((hw_px, h_px), Image.BILINEAR)
        if u > 0.0:
            im = im.rotate(-14 * (1 - u) + math.sin(t * 25) * 0.6, expand=True, resample=Image.BILINEAR, center=(im.width / 2, im.height))
        arr = np.asarray(im, np.float32) / 255
        x0 = int(W * (0.30 + 0.2 * u) - arr.shape[1] / 2)
        y0 = int(H - arr.shape[0] * (0.30 + 0.70 * u) + 40 * (1 - u))
        ys0, ys1 = max(0, y0), min(H, y0 + arr.shape[0])
        xs0, xs1 = max(0, x0), min(W, x0 + arr.shape[1])
        if ys1 > ys0 and xs1 > xs0:
            a = arr[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
            lit = a[..., :3] * np.array([0.38, 0.52, 0.80], np.float32) * (0.5 + 0.5 * u)
            frame[ys0:ys1, xs0:xs1] = frame[ys0:ys1, xs0:xs1] * (1 - a[..., 3:4]) + lit * a[..., 3:4]
    # ----- rosto de Lucas possuído (enquadramento final)
    if face_shot:
        ib = Image.fromarray(np.clip(frame * 255 * 1.3, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.2))
        frame = np.asarray(ib, np.float32) / 255 / 1.3
        k = (t - FACE_T) / (END_T - FACE_T)
        sc = 1.0 + 0.10 * k
        fw = int(W * 0.82 * sc)
        fh = int(fw * SP["lucas"].height / SP["lucas"].width)
        im = SP["lucas"].resize((fw, fh), Image.BILINEAR)
        sx, sy = math.sin(t * 1.3) * 5, math.sin(t * 0.9) * 4
        x0 = int(W * 0.38 - fw / 2 + sx)
        y0 = int(H * 0.50 - fh * 0.50 + sy + 40)
        arr = np.asarray(im, np.float32) / 255
        ys0, ys1 = max(0, y0), min(H, y0 + fh)
        xs0, xs1 = max(0, x0), min(W, x0 + fw)
        a = arr[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
        yy = np.linspace(0, 1, ys1 - ys0)[:, None, None]
        glow_ = 0.60 + 0.55 * yy          # luz da tela vem de baixo
        lit = a[..., :3] * np.array([0.50, 0.70, 1.0], np.float32) * glow_ * (0.9 + 0.08 * math.sin(t * 31))
        frame[ys0:ys1, xs0:xs1] = frame[ys0:ys1, xs0:xs1] * (1 - a[..., 3:4]) + lit * a[..., 3:4]
        # primeiros frames: lente "cegada" pela mao se afastando
        if t < FACE_T + 0.25:
            frame *= (0.25 + 0.75 * (t - FACE_T) / 0.25)
    # ----- pos
    p = dict(grain=0.085, exposure=3.1, rgb_shift=1, tint=(0.88, 0.97, 1.12), glitch=0.0, static=0.0, saturation=0.75, bloom=0.4)
    p["exposure"] = 3.1 * (0.50 + 0.50 * smoothstep(3.0, 9.0, t))     # abertura: quase no escuro, so a luz fraca da tela
    if t > FALL_T + 0.3:
        p["grain"] = 0.10
    if t >= 15 and t < 36 and zoom_active(t):
        p["grain"] = 0.10
    if FALL_T <= t < FALL_T + 0.8:
        p["glitch"] = 0.45 * math.exp(-(t - FALL_T) * 3)
    if t > FACE_T + 4.2:
        p["glitch"] = 0.12 + 0.2 * smoothstep(FACE_T + 4.2, END_T, t) * abs(math.sin(t * 17))
    if 53.9 <= t < FACE_T:
        p["blackout"] = 1.0
    out = post(frame, fidx, **p)
    return out, dict()


def zoom_active(t):
    return 22.5 < t < 35.4


def tor_ok(t):
    return torch_on(t) if t < 51.6 else 0.0


def hud(t):
    st = dict(clock="03:01 AM", battery=1, bat_red=True, bat_blink=int(t * 2.5) % 2 == 0, live="off")
    return st
