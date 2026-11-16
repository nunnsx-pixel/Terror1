import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
from common import *
from textures import Tex

BIG = 1e9
_ix = (np.arange(W, dtype=np.float32) + 0.5 - W / 2) / FOCAL
_iy = (H / 2 - (np.arange(H, dtype=np.float32) + 0.5)) / FOCAL
BX = np.broadcast_to(_ix[None, :], (H, W)).astype(np.float32)
BY = np.broadcast_to(_iy[:, None], (H, W)).astype(np.float32)
BASE = np.stack([BX, BY, np.ones_like(BX)], -1).reshape(-1, 3)
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.55 * (((_xx - W / 2) / (W * 0.75)) ** 2 + ((_yy - H / 2) / (H * 0.72)) ** 2)).clip(0.15, 1)[..., None].astype(np.float32)

# normais das 6 superficies: 0 parede esq, 1 parede dir, 2 chao, 3 teto, 4 fundo (z=ze), 5 entrada (z=z0)
NORMALS = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, -1], [0, 0, 1]], np.float32)


def rot(yaw, pitch, roll):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], np.float32)
    Rx = np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]], np.float32)
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]], np.float32)
    return Ry @ Rx @ Rz


class World:
    def __init__(self, hw, ch, z0, ze, left, right, floor, ceil, end, back, tube_z, tube_color=(1.0, 0.86, 0.5)):
        self.hw, self.ch, self.z0, self.ze = hw, ch, z0, ze
        self.tex = [left, right, floor, ceil, end, back]
        self.tube_z = list(tube_z)
        self.tube_color = np.array(tube_color, np.float32)
        self.set_end = None


def light_at(P, N, lights, fog_ambient=0.0):
    """P,N: (n,3). lights: list of dicts. retorna irradiancia (n,3)"""
    out = np.zeros(P.shape, np.float32) + fog_ambient
    for L in lights:
        pos = np.array(L["pos"], np.float32)
        v = P - pos
        d2 = (v * v).sum(-1, keepdims=True)
        d = np.sqrt(d2) + 1e-4
        vh = v / d
        ndl = np.clip(-(vh * N).sum(-1, keepdims=True), 0, 1)
        col = np.array(L["color"], np.float32) * L["i"]
        if L["kind"] == "tube":
            lam = 0.10 + 0.90 * ndl
            att = 1.0 / (0.7 + d2 * L.get("fall", 0.55))
            out += col * lam * att
        elif L["kind"] == "point":
            lam = 0.25 + 0.75 * ndl
            att = 1.0 / (0.15 + d2 * L.get("fall", 1.2))
            out += col * lam * att
        else:  # spot
            dirv = np.array(L["dir"], np.float32)
            dirv = dirv / (np.linalg.norm(dirv) + 1e-9)
            cosang = (vh * dirv).sum(-1, keepdims=True)
            ci, co = math.cos(L["inner"]), math.cos(L["outer"])
            cone = np.clip((cosang - co) / (ci - co + 1e-6), 0, 1)
            cone = cone * cone * (3 - 2 * cone)
            lam = 0.35 + 0.65 * ndl
            att = 1.0 / (0.25 + d2 * L.get("fall", 0.28))
            out += col * cone * lam * att
    return out


def render_world(world, cam, lights, t, tube_state, emis_gain=1.0, ambient=0.012):
    """raycast do corredor. cam: dict x,y,z,yaw,pitch,roll. tube_state: lista de intensidades por tubo"""
    R = rot(cam["yaw"], cam["pitch"], cam["roll"])
    zm = cam.get("zoom", 1.0)
    d = ((BASE * np.array([1 / zm, 1 / zm, 1], np.float32)) @ R.T).astype(np.float32)
    dx, dy, dz = d[:, 0], d[:, 1], d[:, 2]
    cx, cy, cz = cam["x"], cam["y"], cam["z"]

    def safe(a):
        return np.where(np.abs(a) < 1e-6, 1e-6, a)
    sx, sy_, sz = safe(dx), safe(dy), safe(dz)
    ts = np.full((6, d.shape[0]), BIG, np.float32)
    ts[0] = np.where(dx < 0, (-world.hw - cx) / sx, BIG)
    ts[1] = np.where(dx > 0, (world.hw - cx) / sx, BIG)
    ts[2] = np.where(dy < 0, (0 - cy) / sy_, BIG)
    ts[3] = np.where(dy > 0, (world.ch - cy) / sy_, BIG)
    ts[4] = np.where(dz > 0, (world.ze - cz) / sz, BIG)
    ts[5] = np.where(dz < 0, (world.z0 - cz) / sz, BIG)
    ts[ts <= 0] = BIG
    sid = ts.argmin(0)
    tt = ts.min(0)
    tt = np.minimum(tt, 60.0)
    P = np.stack([cx + tt * dx, cy + tt * dy, cz + tt * dz], -1)
    dl = np.sqrt(dx * dx + dy * dy + dz * dz)
    dist = tt * dl
    Nrm = NORMALS[sid]
    ndv = np.abs((d * Nrm).sum(-1)) / (dl + 1e-9)
    foot = dist / (FOCAL * zm) / np.clip(ndv, 0.12, 1)

    alb = np.zeros((d.shape[0], 3), np.float32)
    emis = np.zeros((d.shape[0], 3), np.float32)
    hw, ch = world.hw, world.ch
    for s in range(6):
        m = sid == s
        if not m.any():
            continue
        px, py, pz = P[m, 0], P[m, 1], P[m, 2]
        tx = world.tex[s]
        if tx is None:
            continue
        if s in (0, 1):
            u, v = pz, ch - py
        elif s in (2, 3):
            u, v = pz, px + hw
        elif s == 4:
            u, v = px + hw, ch - py
        else:
            u, v = hw - px, ch - py
        if s in (2, 3):   # texturas de chao/teto: eixo u=z (colunas), v=x (linhas)
            alb[m] = tx.sample(u, v, foot[m])
        else:
            alb[m] = tx.sample(u, v, foot[m])
        if tx.emis is not None:
            emis[m] = tx.emis.sample(u, v, foot[m]) * emis_gain
    # iluminacao
    tube_lights = []
    for k, zk in enumerate(world.tube_z):
        inten = tube_state[k] if k < len(tube_state) else 1.0
        if inten > 0.01 and abs(zk - cz) < 24:
            tube_lights.append(dict(kind="tube", pos=(0, ch - 0.12, zk), color=world.tube_color, i=inten * 1.45))
    irr = light_at(P, Nrm, tube_lights + list(lights), ambient)
    col = alb * irr
    # tubos emissivos no teto
    mt = sid == 3
    if mt.any():
        for k, zk in enumerate(world.tube_z):
            inten = tube_state[k] if k < len(tube_state) else 1.0
            sel = mt & (np.abs(P[:, 0]) < 0.20) & (np.abs(P[:, 2] - zk) < 0.62)
            if sel.any() and inten > 0.01:
                col[sel] = world.tube_color * (1.5 * inten)
    col = col + emis
    fog = np.exp(-dist * 0.045)[:, None]
    col = col * fog
    return col.reshape(H, W, 3).astype(np.float32), dict(R=R, cam=cam)


# ------------------------------------------------------------------------------------ sprites
def project(R, cam, pos):
    pc = R.T @ (np.array(pos, np.float32) - np.array([cam["x"], cam["y"], cam["z"]], np.float32))
    return pc


def draw_sprite(frame, sp, info, lights, tube_lights, ambient=0.02, rim=0.0):
    """billboard com iluminacao (frame float32 HxWx3, modificado in-place)"""
    R, cam = info["R"], info["cam"]
    pos = sp["pos"]
    pc = project(R, cam, pos)
    if pc[2] < 0.2:
        return
    s = FOCAL * cam.get("zoom", 1.0) / pc[2]
    img = sp["img"]
    hp = sp["h"] * s
    wp = hp * img.width / img.height
    if hp < 3 or hp > 6000:
        return
    cxp = W / 2 + pc[0] * s + sp.get("dx", 0) * s
    byp = H / 2 - pc[1] * s
    rw, rh = max(1, int(wp)), max(1, int(hp))
    im = img.resize((rw, rh), Image.BILINEAR if rw > img.width * 0.5 else Image.LANCZOS)
    if sp.get("rot"):
        im = im.rotate(sp["rot"], expand=True, resample=Image.BILINEAR)
        rw, rh = im.size
    roll = cam["roll"]
    if abs(roll) > 0.025:
        im = im.rotate(math.degrees(roll), expand=True, resample=Image.BILINEAR, center=(im.width / 2, im.height))
        rw, rh = im.size
    if sp.get("blur"):
        im = im.filter(ImageFilter.GaussianBlur(sp["blur"] * s * 0.02))
    arr = np.asarray(im, np.float32) / 255.0
    x0 = int(cxp - rw / 2)
    y0 = int(byp - rh)
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x0 + rw), min(H, y0 + rh)
    if xs1 <= xs0 or ys1 <= ys0:
        return
    a = arr[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    rgb, al = a[..., :3], a[..., 3:4] * sp.get("alpha", 1.0)
    # luz no ponto do sprite
    midp = np.array([[pos[0], pos[1] + sp["h"] * 0.55, pos[2]]], np.float32)
    toc = np.array([[cam["x"], cam["y"], cam["z"]]], np.float32) - midp
    Nn = toc / (np.linalg.norm(toc) + 1e-9)
    irr = light_at(midp, Nn, tube_lights + list(lights), ambient)[0]
    irr = np.clip(irr * sp.get("light_gain", 1.0), 0, 2.2)
    # gradiente vertical: pe mais escuro (bounce do chao), cabeca mais iluminada por lanternas altas
    gy = np.linspace(0, 1, rh)[ys0 - y0:ys1 - y0][:, None, None]
    shade = irr[None, None, :] * (0.78 + 0.35 * (1 - gy))
    lit = rgb * shade
    if sp.get("emis") is not None:
        pass
    dist = pc[2]
    fogm = math.exp(-dist * 0.045)
    reg = frame[ys0:ys1, xs0:xs1]
    frame[ys0:ys1, xs0:xs1] = reg * (1 - al) + (lit * fogm + rim * al) * al
    return (cxp, byp - rh, rw, rh)


def glow(frame, x, y, radius, color, strength):
    """glow aditivo (lente de lanterna / tela)"""
    r = int(radius)
    x0, y0, x1, y1 = int(x - r), int(y - r), int(x + r), int(y + r)
    xs0, ys0, xs1, ys1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if xs1 <= xs0 or ys1 <= ys0:
        return
    gy, gx = np.mgrid[ys0:ys1, xs0:xs1].astype(np.float32)
    rr = np.sqrt((gx - x) ** 2 + (gy - y) ** 2) / max(r, 1)
    g = np.clip(1 - rr, 0, 1) ** 2.2 * strength
    frame[ys0:ys1, xs0:xs1] += g[..., None] * np.array(color, np.float32)[None, None, :]


def beam(frame, p0, p1, w0, w1, color, strength):
    """feixe de lanterna em screen-space (poligono suave)"""
    layer = Image.new("L", (W // 2, H // 2), 0)
    d = ImageDraw.Draw(layer)
    x0, y0 = p0[0] / 2, p0[1] / 2
    x1, y1 = p1[0] / 2, p1[1] / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) + 1e-6
    nx, ny = -dy / L, dx / L
    d.polygon([(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2),
               (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2)], fill=int(255 * strength))
    layer = layer.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    a = np.asarray(layer, np.float32)[..., None] / 255.0
    frame += a * np.array(color, np.float32)[None, None, :]


# ------------------------------------------------------------------------------------ pos-processamento
_noise_rng = np.random.default_rng(1234)


def post(frame, fidx, grain=0.05, tint=(1.0, 1.0, 1.0), glitch=0.0, exposure=1.7, rgb_shift=1, blackout=0.0,
         contrast=1.0, saturation=1.0, bloom=0.55, static=0.0, seed=0):
    rng = np.random.default_rng(seed + fidx * 7919)
    f = frame * np.array(tint, np.float32)
    # bloom
    small = f.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
    bright = np.clip(small - 0.7, 0, None)
    bi = Image.fromarray(np.clip(bright * 255 / 2, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
    bl = np.asarray(bi.resize((W, H), Image.BILINEAR), np.float32) / 255 * 2
    f = f + bl * bloom
    # tone map
    f = 1 - np.exp(-f * exposure)
    f = np.power(np.clip(f, 0, 1), 1 / 1.5)
    if saturation != 1.0:
        lum = f.mean(-1, keepdims=True)
        f = lum + (f - lum) * saturation
    if contrast != 1.0:
        f = np.clip((f - 0.5) * contrast + 0.5, 0, 1)
    f = f * VIGN
    # tremor de linhas / tearing
    if glitch > 0.02:
        nb = int(3 + glitch * 14)
        for _ in range(nb):
            y = int(rng.uniform(0, H))
            hh = int(rng.uniform(4, 22 + 60 * glitch))
            sh = int(rng.normal(0, 12 + 55 * glitch))
            f[y:y + hh] = np.roll(f[y:y + hh], sh, axis=1)
        sh2 = int(1 + 5 * glitch)
        f[..., 0] = np.roll(f[..., 0], sh2, axis=1)
        f[..., 2] = np.roll(f[..., 2], -sh2, axis=1)
    elif rgb_shift:
        f[..., 0] = np.roll(f[..., 0], rgb_shift, axis=1)
        f[..., 2] = np.roll(f[..., 2], -rgb_shift, axis=1)
    # ruido de sensor (mais forte no escuro)
    lum = f.mean(-1, keepdims=True)
    sig = grain * (0.4 + 1.6 * (1 - lum))
    n = rng.standard_normal((H, W, 1)).astype(np.float32) * sig
    nc = rng.standard_normal((H, W, 3)).astype(np.float32) * sig * 0.35
    f = f + n + nc
    if static > 0:
        sn = rng.random((H, W, 1)).astype(np.float32)
        f = f * (1 - static) + sn * static * 0.9
    if blackout > 0:
        f = f * (1 - blackout)
    return np.clip(f, 0, 1)
