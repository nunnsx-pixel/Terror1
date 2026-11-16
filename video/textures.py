import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"


def fbm(h, w, seed, octs=((96, 1.0), (48, .6), (24, .4), (12, .25), (6, .15), (3, .1))):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    tw = 0
    for sc, wt in octs:
        gh, gw = max(2, int(h / sc) + 2), max(2, int(w / sc) + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(im, np.float32) / 255 * wt
        tw += wt
    return acc / tw


def streaks(h, w, seed, sx=6, sy=160):
    rng = np.random.default_rng(seed)
    g = rng.random((max(2, h // sy) + 2, max(2, w // sx) + 2)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255


class Tex:
    def __init__(self, arr, ppm, emis=None):
        self.ppm = ppm
        self.mips = [np.ascontiguousarray(arr)]
        im = Image.fromarray(arr)
        for _ in range(4):
            im = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.BOX)
            self.mips.append(np.asarray(im))
        self.emis = None
        if emis is not None:
            self.emis = Tex(emis, ppm)

    def sample(self, u, v, foot):
        out = np.zeros(u.shape + (3,), np.float32)
        lvl = np.clip(np.log2(np.maximum(foot * self.ppm, 1.0)), 0, 4).astype(np.int8)
        for L in range(5):
            m = lvl == L
            if not m.any():
                continue
            a = self.mips[L]
            s = 2 ** L
            uu = np.clip((u[m] * self.ppm / s).astype(np.int32), 0, a.shape[1] - 1)
            vv = np.clip((v[m] * self.ppm / s).astype(np.int32), 0, a.shape[0] - 1)
            out[m] = a[vv, uu]
        return out / 255.0


def _to_img(a):
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------- paredes
def make_wall(L, seed, ppm=90, ch=3.0, doors=(), mold=1.0, tone=(0.60, 0.62, 0.55)):
    h, w = int(ch * ppm), int(L * ppm)
    n1 = fbm(h, w, seed)
    n2 = fbm(h, w, seed + 1, ((40, 1), (20, .6), (10, .4), (5, .2)))
    base = np.array(tone, np.float32)[None, None, :]
    img = base * (0.50 + 0.50 * n1[..., None])
    yy = (np.arange(h, dtype=np.float32) / ppm)[:, None]          # distancia do teto
    hy = ch - yy                                                   # altura do chao
    # rodape verde escuro
    wains = (hy < 1.25).astype(np.float32)
    wc = np.array([0.16, 0.27, 0.24], np.float32)[None, None, :] * (0.6 + 0.6 * n2[..., None])
    img = img * (1 - wains[..., None]) + wc * wains[..., None]
    line = (np.abs(hy - 1.25) < 0.025).astype(np.float32)[..., None]
    img = img * (1 - line) + np.array([0.08, 0.1, 0.09], np.float32) * line
    # tinta descascando (revela reboco claro e tijolo)
    peel = smooth_thr(fbm(h, w, seed + 2), 0.60, 0.04)[..., None]
    under = np.array([0.52, 0.5, 0.46], np.float32)[None, None, :] * (0.7 + 0.5 * n2[..., None])
    img = img * (1 - peel * 0.85) + under * peel * 0.85
    edge = (smooth_thr(fbm(h, w, seed + 2), 0.60, 0.04) - smooth_thr(fbm(h, w, seed + 2), 0.64, 0.04))[..., None]
    img *= (1 - 0.6 * np.clip(edge, 0, 1))
    deep = smooth_thr(fbm(h, w, seed + 3), 0.70, 0.03)[..., None]
    img = img * (1 - deep * 0.8) + np.array([0.30, 0.17, 0.12], np.float32) * deep * 0.8  # tijolo exposto
    # mofo verde-acinzentado (perto do chao e do teto)
    mm = smooth_thr(fbm(h, w, seed + 4), 0.5, 0.18) * np.clip(1.4 * np.exp(-hy / 0.7) + 1.1 * np.exp(-yy / 0.5), 0, 1)
    mm = np.clip(mm * mold, 0, 1)[..., None]
    img = img * (1 - 0.75 * mm) + np.array([0.20, 0.30, 0.20], np.float32) * 0.75 * mm
    # manchas escorridas
    st = streaks(h, w, seed + 5)
    img *= (1 - 0.35 * smooth_thr(st, 0.55, 0.12)[..., None])
    # conduite / cano no alto
    pipe = ((hy > 2.45) & (hy < 2.55)).astype(np.float32)[..., None]
    img = img * (1 - pipe) + np.array([0.25, 0.14, 0.09], np.float32) * (0.6 + 0.8 * n2[..., None]) * pipe
    pim = _to_img(img)
    d = ImageDraw.Draw(pim)
    rng = np.random.default_rng(seed + 9)
    # rachaduras
    for _ in range(int(L * 0.9)):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h * 0.8)
        pts = [(x, y)]
        for _k in range(rng.integers(5, 14)):
            x += rng.normal(0, 7)
            y += rng.uniform(3, 14)
            pts.append((x, y))
        d.line(pts, fill=(14, 14, 12), width=1)
    # portas
    for (zc, kind, label) in doors:
        x0, x1 = int((zc - 0.55) * ppm), int((zc + 0.55) * ppm)
        y0, y1 = int((ch - 2.25) * ppm), h
        d.rectangle([x0 - 7, y0 - 7, x1 + 7, y1], fill=(34, 24, 18))              # batente
        if kind == "dark":
            d.rectangle([x0, y0, x1, y1], fill=(2, 2, 3))
        elif kind == "broken":
            d.rectangle([x0, y0, x1, y1], fill=(2, 2, 3))
            for i in range(5):                                                      # tabuas apodrecidas pendendo
                bx = x0 + i * (x1 - x0) // 5
                top = y0 + int(rng.uniform(0, 70))
                bot = y0 + int(rng.uniform(100, 180))
                d.polygon([(bx, top), (bx + 14, top + 4), (bx + 11, bot), (bx - 2, bot - 6)], fill=(70, 46, 28))
        else:
            d.rectangle([x0, y0, x1, y1], fill=(74, 56, 40))
            for i in range(1, 6):
                d.line([(x0, y0 + i * (y1 - y0) // 6), (x1, y0 + i * (y1 - y0) // 6)], fill=(40, 30, 22), width=2)
        if label:
            f = ImageFont.truetype(FONT_B, 17)
            d.rectangle([x0 + 12, y0 - 40, x1 - 12, y0 - 14], fill=(120, 120, 108))
            d.text((x0 + 18, y0 - 38), label, font=f, fill=(25, 25, 22))
    arr = np.asarray(pim.filter(ImageFilter.GaussianBlur(0.6)))
    return arr


def smooth_thr(x, thr, w):
    return np.clip((x - thr) / (2 * w) + 0.5, 0, 1).astype(np.float32)


# --------------------------------------------------------------------------- chao
def make_floor(L, seed, ppm=90, width=2.6, tile=0.30, prints=(), mud=False):
    w, h = int(L * ppm), int(width * ppm)           # u = z (colunas), v = x (linhas)
    n1 = fbm(h, w, seed, ((64, 1), (32, .6), (16, .4), (8, .25), (4, .15), (2, .1)))
    tp = int(tile * ppm)
    zi = (np.arange(w) // tp)[None, :]
    xi = (np.arange(h) // tp)[:, None]
    chk = ((zi + xi) % 2).astype(np.float32)
    rng = np.random.default_rng(seed + 11)
    jit = rng.random((h // tp + 2, w // tp + 2)).astype(np.float32)
    tj = jit[xi, zi]
    c1 = np.array([0.46, 0.45, 0.38], np.float32)
    c2 = np.array([0.30, 0.34, 0.30], np.float32)
    col = c1 * chk[..., None] + c2 * (1 - chk[..., None])
    img = col * (0.55 + 0.45 * n1[..., None]) * (0.85 + 0.3 * tj[..., None])
    gz = ((np.arange(w) % tp) < 2)[None, :]
    gx = ((np.arange(h) % tp) < 2)[:, None]
    grout = (gz | gx).astype(np.float32)[..., None]
    img = img * (1 - 0.7 * grout)
    # buracos / azulejos quebrados
    hole = smooth_thr(fbm(h, w, seed + 3), 0.69, 0.02)[..., None]
    img = img * (1 - hole * 0.9) + np.array([0.13, 0.11, 0.09], np.float32) * hole * 0.9
    # sujeira / poeira
    dirt = smooth_thr(fbm(h, w, seed + 4), 0.52, 0.2)[..., None]
    img = img * (1 - 0.45 * dirt) + np.array([0.20, 0.17, 0.12], np.float32) * 0.45 * dirt
    pim = _to_img(img)
    d = ImageDraw.Draw(pim)
    for _ in range(int(L * 1.2)):                                                 # rachaduras no piso
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pts = [(x, y)]
        for _k in range(rng.integers(4, 10)):
            x += rng.uniform(3, 14)
            y += rng.normal(0, 7)
            pts.append((x, y))
        d.line(pts, fill=(10, 10, 9), width=1)
    for _ in range(int(L * 9)):                                                    # cacos de vidro/entulho
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(1, 3.2)
        c = int(rng.uniform(90, 200))
        d.ellipse([x - r, y - r * .6, x + r, y + r * .6], fill=(c, c, int(c * .9)))
    # pegadas descalcas de lama
    for (zc, xc, ang, foot) in prints:
        _bare_print(pim, zc * ppm, (xc + width / 2) * ppm, ang, foot, ppm)
    return np.asarray(pim.filter(ImageFilter.GaussianBlur(0.5)))


def _bare_print(pim, cx, cy, ang, foot, ppm):
    """pegada descalca (comprimento ~0.27m) orientada ao longo de z (colunas)"""
    ln, wd = 0.27 * ppm, 0.10 * ppm
    S = 4
    tile = Image.new("L", (int(ln * 1.4) * S, int(wd * 2) * S), 0)
    td = ImageDraw.Draw(tile)
    cx0, cy0 = tile.width / 2, tile.height / 2
    sgn = 1 if foot == "L" else -1
    td.ellipse([cx0 - ln * .5 * S, cy0 - wd * .5 * S - sgn * wd * .05 * S, cx0 + ln * .2 * S, cy0 + wd * .5 * S - sgn * wd * .05 * S], fill=255)
    td.ellipse([cx0 + ln * .05 * S, cy0 - wd * .55 * S, cx0 + ln * .38 * S, cy0 + wd * .55 * S], fill=255)
    for i in range(5):
        tx = cx0 + ln * (0.38 + 0.06 * (2 - abs(i - 2) * 0.0)) * S
        ty = cy0 + sgn * (i - 2) * wd * 0.22 * S
        r = wd * (0.13 - 0.012 * abs(i - 2)) * S
        td.ellipse([tx - r + (abs(i - 2) * -0.0) * S, ty - r, tx + r + ln * 0.05 * S, ty + r], fill=255)
    tile = tile.resize((tile.width // S, tile.height // S), Image.LANCZOS).rotate(ang, expand=True, resample=Image.BICUBIC)
    mud = Image.new("RGB", tile.size, (38, 22, 12))
    pim.paste(mud, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile.point(lambda v: int(v * 0.9)))


# --------------------------------------------------------------------------- teto
def make_ceiling(L, seed, ppm=90, width=2.6, fixtures=()):
    w, h = int(L * ppm), int(width * ppm)
    n1 = fbm(h, w, seed)
    tp = int(0.6 * ppm)
    zi = (np.arange(w) // tp)[None, :]
    xi = (np.arange(h) // tp)[:, None]
    rng = np.random.default_rng(seed + 5)
    jit = rng.random((h // tp + 2, w // tp + 2)).astype(np.float32)
    img = np.array([0.55, 0.55, 0.5], np.float32) * (0.45 + 0.55 * n1[..., None]) * (0.85 + 0.25 * jit[xi, zi][..., None])
    gz = ((np.arange(w) % tp) < 2)[None, :]
    gx = ((np.arange(h) % tp) < 2)[:, None]
    img *= (1 - 0.6 * (gz | gx).astype(np.float32)[..., None])
    miss = (jit[xi, zi] > 0.93).astype(np.float32)[..., None]                       # placas faltando
    img = img * (1 - miss * 0.92)
    st = smooth_thr(fbm(h, w, seed + 7), 0.58, 0.1)[..., None]
    img = img * (1 - 0.5 * st) + np.array([0.25, 0.2, 0.1], np.float32) * 0.5 * st
    pim = _to_img(img)
    d = ImageDraw.Draw(pim)
    for z in fixtures:                                                               # carcaça das luminárias
        cx = z * ppm
        d.rectangle([cx - 0.7 * ppm, h / 2 - 0.2 * ppm, cx + 0.7 * ppm, h / 2 + 0.2 * ppm], fill=(18, 18, 16))
    return np.asarray(pim)


# --------------------------------------------------------------------------- paredes de fundo
def _wall_bg(wm, hm, ppm, seed):
    arr = make_wall(wm, seed, ppm=ppm, ch=hm, mold=1.0)
    return arr


def make_iron_door_wall(seed=40, ppm=300, claws=True, padlock=True, state="closed", ww=2.6, hh=3.0):
    """parede de fundo com porta de ferro. state: closed | ajar"""
    w, h = int(ww * ppm), int(hh * ppm)
    bg = _wall_bg(ww, hh, ppm // 3, seed)
    pim = Image.fromarray(bg).resize((w, h), Image.BICUBIC)
    n = fbm(h, w, seed + 20, ((120, 1), (60, .6), (30, .4), (12, .25), (5, .12), (2, .08)))
    dw, dh = int(1.15 * ppm), int(2.25 * ppm)
    dx0, dy0 = (w - dw) // 2, h - dh
    # batente
    d = ImageDraw.Draw(pim)
    d.rectangle([dx0 - 28, dy0 - 28, dx0 + dw + 28, h], fill=(24, 22, 20))
    # folha
    door = np.zeros((dh, dw, 3), np.float32)
    col = np.array([0.20, 0.27, 0.24], np.float32)
    dn = n[dy0:dy0 + dh, dx0:dx0 + dw]
    door[:] = col * (0.45 + 0.7 * dn[..., None])
    rust = smooth_thr(fbm(dh, dw, seed + 22), 0.55, 0.12)[..., None]
    door = door * (1 - 0.7 * rust) + np.array([0.33, 0.15, 0.07], np.float32) * (0.4 + 0.8 * dn[..., None]) * 0.7 * rust
    dimg = _to_img(door)
    dd = ImageDraw.Draw(dimg)
    for fy in (0.0, 0.33, 0.66, 1.0):                                                # reforcos horizontais + rebites
        y = int(fy * (dh - 30))
        dd.rectangle([0, y, dw, y + 28], fill=(36, 42, 39))
        for rx in range(18, dw - 10, 46):
            dd.ellipse([rx - 5, y + 9, rx + 5, y + 19], fill=(88, 84, 76))
    dd.rectangle([0, 0, dw - 1, dh - 1], outline=(14, 14, 13), width=6)
    rng = np.random.default_rng(seed + 33)
    if claws:                                                                         # garras: sulcos profundos verticais
        for g in range(7):
            gx = rng.uniform(0.12, 0.88) * dw
            gy = rng.uniform(0.18, 0.55) * dh
            ln = rng.uniform(0.25, 0.5) * dh
            for k in range(4):
                ox = k * rng.uniform(13, 19)
                pts = [(gx + ox + math.sin(i * 0.5 + g) * 4, gy + ln * i / 14) for i in range(15)]
                dd.line(pts, fill=(12, 10, 9), width=5)
                dd.line([(x + 3, y) for x, y in pts], fill=(190, 178, 160), width=2)       # metal exposto
    if padlock:
        hx, hy = int(dw * 0.83), int(dh * 0.50)
        dd.rectangle([hx - 38, hy - 70, hx + 28, hy + 70], fill=(58, 56, 52))             # chapa do trinco
        for ry in (-52, 52):
            dd.ellipse([hx - 22, hy + ry - 6, hx - 10, hy + ry + 6], fill=(130, 124, 112))
        # cadeado estraçalhado: corpo + argola retorcida pra FORA
        dd.rounded_rectangle([hx - 82, hy - 26, hx - 4, hy + 62], radius=12, fill=(70, 70, 66), outline=(20, 20, 18), width=4)
        dd.line([(hx - 70, hy - 20), (hx - 12, hy - 20)], fill=(150, 150, 140), width=4)
        dd.arc([hx - 70, hy - 110, hx - 14, hy - 20], 180, 330, fill=(110, 108, 100), width=11)
        dd.line([(hx - 20, hy - 70), (hx + 36, hy - 118), (hx + 60, hy - 96)], fill=(110, 108, 100), width=11)  # argola dobrada
        dd.polygon([(hx - 82, hy + 62), (hx - 60, hy + 92), (hx - 40, hy + 70), (hx - 4, hy + 62)], fill=(40, 40, 38))
        # sangue seco acumulado no trinco
        bl = Image.new("L", dimg.size, 0)
        bd = ImageDraw.Draw(bl)
        for _ in range(26):
            bx = hx + rng.normal(-20, 28)
            by = hy + rng.normal(10, 30)
            r = rng.uniform(3, 14)
            bd.ellipse([bx - r, by - r, bx + r, by + r], fill=int(rng.uniform(150, 255)))
        for _ in range(7):
            bx = hx + rng.normal(-24, 22)
            by0 = hy + rng.uniform(0, 30)
            bd.line([(bx, by0), (bx + rng.normal(0, 2), by0 + rng.uniform(40, 150))], fill=220, width=int(rng.uniform(3, 7)))
        bl = bl.filter(ImageFilter.GaussianBlur(1.6))
        dimg.paste(Image.new("RGB", dimg.size, (58, 12, 8)), (0, 0), bl.point(lambda v: int(v * 0.95)))
    if state == "ajar":                                                                # entreaberta: fresta de luz fria
        dd.rectangle([dw - 28, 0, dw, dh], fill=(2, 2, 3))
        dd.rectangle([dw - 20, 0, dw - 8, dh], fill=(120, 140, 170))
    pim.paste(dimg, (dx0, dy0))
    return np.asarray(pim.filter(ImageFilter.GaussianBlur(0.7)))


def make_brick_wall(seed=50, ppm=300, ww=2.6, hh=3.0):
    """parede de tijolos maciça que tapou uma porta (contorno fantasma da porta)"""
    w, h = int(ww * ppm), int(hh * ppm)
    rng = np.random.default_rng(seed)
    n = fbm(h, w, seed, ((120, 1), (60, .6), (30, .4), (12, .25), (5, .15), (2, .1)))
    bw, bh = int(0.22 * ppm), int(0.072 * ppm)
    mort = np.array([0.34, 0.33, 0.30], np.float32)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = mort * (0.6 + 0.4 * n[..., None])
    pim = _to_img(img)
    d = ImageDraw.Draw(pim)
    dw, dh = int(1.15 * ppm), int(2.25 * ppm)
    dx0, dy0 = (w - dw) // 2, h - dh
    for r, y in enumerate(range(0, h, bh)):
        off = (bw // 2) if r % 2 else 0
        for x in range(-off, w, bw):
            inside = dx0 <= x + bw // 2 <= dx0 + dw and dy0 <= y + bh // 2 <= h
            base = np.array([0.45, 0.17, 0.10], np.float32) if not inside else np.array([0.52, 0.22, 0.13], np.float32)
            c = base * rng.uniform(0.55, 1.15) * (0.55 + 0.7 * float(n[min(h - 1, y + bh // 2), min(w - 1, max(0, x + bw // 2))]))
            c = tuple(int(255 * v) for v in np.clip(c, 0, 1))
            d.rectangle([x + 3, y + 3, x + bw - 2, y + bh - 2], fill=c)
    # restos do batente de madeira da porta emparedada
    d.rectangle([dx0 - 20, dy0 - 20, dx0 - 4, h], fill=(40, 28, 20))
    d.rectangle([dx0 + dw + 4, dy0 - 20, dx0 + dw + 20, h], fill=(40, 28, 20))
    d.rectangle([dx0 - 20, dy0 - 20, dx0 + dw + 20, dy0 - 4], fill=(40, 28, 20))
    arr = np.asarray(pim).astype(np.float32) / 255
    st = streaks(h, w, seed + 5, 10, 220)
    arr *= (1 - 0.45 * smooth_thr(st, 0.5, 0.15)[..., None])
    mold = smooth_thr(fbm(h, w, seed + 6), 0.5, 0.15) * np.clip(np.exp(-(h - np.arange(h)) / (0.6 * ppm)), 0, 1)[:, None]
    arr = arr * (1 - 0.6 * mold[..., None]) + np.array([0.18, 0.25, 0.17], np.float32) * 0.6 * mold[..., None]
    return np.asarray(_to_img(arr).filter(ImageFilter.GaussianBlur(0.6)))


def make_entrance(seed=60, ppm=150, ww=2.6, hh=3.0):
    """entrada arrombada: abertura com noite azulada. retorna (albedo, emissivo)"""
    w, h = int(ww * ppm), int(hh * ppm)
    wall = Image.fromarray(_wall_bg(ww, hh, ppm // 2, seed)).resize((w, h), Image.BICUBIC)
    em = Image.new("RGB", (w, h), (0, 0, 0))
    ow_, oh_ = int(1.5 * ppm), int(2.3 * ppm)
    x0, y0 = (w - ow_) // 2, h - oh_
    d = ImageDraw.Draw(wall)
    d.rectangle([x0 - 18, y0 - 18, x0 + ow_ + 18, h], fill=(28, 20, 16))
    d.rectangle([x0, y0, x0 + ow_, h], fill=(4, 6, 10))
    # gradiente da noite + silhuetas
    g = np.zeros((oh_, ow_, 3), np.float32)
    yy = np.linspace(0, 1, oh_)[:, None]
    g[..., 0] = 0.10 + 0.07 * yy
    g[..., 1] = 0.15 + 0.08 * yy
    g[..., 2] = 0.28 + 0.1 * yy
    n = fbm(oh_, ow_, seed + 4)
    g *= (0.8 + 0.4 * n[..., None])
    gi = _to_img(g)
    gd = ImageDraw.Draw(gi)
    rng = np.random.default_rng(seed)
    for _ in range(14):                                                               # copas de arvores
        cx, cy, r = rng.uniform(0, ow_), rng.uniform(oh_ * .45, oh_ * .8), rng.uniform(25, 70)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(6, 10, 12))
    gd.rectangle([0, int(oh_ * .78), ow_, oh_], fill=(5, 8, 9))
    # folha da porta arrombada pendurada
    gd.polygon([(0, 0), (int(ow_ * .22), int(oh_ * .05)), (int(ow_ * .2), int(oh_ * .96)), (0, oh_)], fill=(36, 24, 16))
    em.paste(gi, (x0, y0))
    return np.asarray(wall.filter(ImageFilter.GaussianBlur(0.5))), np.asarray(em)
