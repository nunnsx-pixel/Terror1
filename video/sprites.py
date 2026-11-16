import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter

SS = 3  # supersample


def _canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def _fin(im, w, h, blur=0.0):
    im = im.resize((w, h), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def S(*v):
    return [x * SS for x in v]


def limb(d, p0, p1, w0, w1, fill, outline=None):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) + 1e-6
    nx, ny = -dy / L, dx / L
    poly = [(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
            (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]
    d.polygon([(a * SS, b * SS) for a, b in poly], fill=fill)
    for (x, y, w) in ((x0, y0, w0), (x1, y1, w1)):
        d.ellipse([(x - w / 2) * SS, (y - w / 2) * SS, (x + w / 2) * SS, (y + w / 2) * SS], fill=fill)


def ell(d, cx, cy, rx, ry, fill, outline=None, width=0):
    if len(fill) == 4 and fill[3] < 255:        # ImageDraw nao mistura alpha em RGBA: usa camada + alpha_composite
        im = d._image
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill)
        im.alpha_composite(layer)
        return
    d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill, outline=outline, width=width * SS)


def plaid(size, base=(150, 22, 24), line=(18, 12, 12), step=26):
    w, h = size
    im = Image.new("RGBA", (w * SS, h * SS), base + (255,))
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(0, w, step):
        d.rectangle([x * SS, 0, (x + step * 0.28) * SS, h * SS], fill=line + (190,))
    for y in range(0, h, step):
        d.rectangle([0, y * SS, w * SS, (y + step * 0.28) * SS], fill=line + (190,))
    for x in range(step // 2, w, step):
        d.line([(x * SS, 0), (x * SS, h * SS)], fill=(220, 60, 50, 90), width=SS)
    return im


def paste_masked(base, src, maskfn):
    """cola 'src' em 'base' usando mascara desenhada por maskfn(draw)"""
    m = Image.new("L", base.size, 0)
    maskfn(ImageDraw.Draw(m))
    base.paste(src, (0, 0), m)


# ------------------------------------------------------------------------------------ rostos
SKIN = (212, 170, 146)
SKIN_POS = (150, 156, 154)


def face(d, cx, cy, rx, ry, mode, female=False, glasses=False, crooked=0.0, skin=SKIN):
    ell(d, cx, cy, rx, ry, skin)
    # sombra lateral
    ell(d, cx + rx * 0.45, cy + ry * 0.1, rx * 0.55, ry * 0.9, tuple(int(c * 0.86) for c in skin))
    ex = rx * 0.42
    ey = cy - ry * 0.1
    er_x, er_y = rx * 0.26, ry * 0.15
    poss = mode in ("possessed",)
    for sx in (-1, 1):
        x = cx + sx * ex
        if poss:
            ell(d, x, ey, er_x * 1.15, er_y * 1.2, (228, 232, 236))
            ell(d, x, ey, er_x * 0.7, er_y * 0.8, (236, 240, 244))
            d.arc([(x - er_x * 1.15) * SS, (ey - er_y * 1.2) * SS, (x + er_x * 1.15) * SS, (ey + er_y * 1.2) * SS], 0, 360, fill=(120, 130, 140, 255), width=SS)
        else:
            wide = 1.25 if mode in ("scared", "cry") else 1.0
            ell(d, x, ey, er_x * wide, er_y * wide * 1.15, (240, 238, 232))
            ell(d, x + (sx * -0.0), ey, er_x * 0.52 * wide, er_y * 0.9 * wide, (36, 24, 18))
            ell(d, x - er_x * 0.15, ey - er_y * 0.2, er_x * 0.14, er_y * 0.2, (255, 255, 255))
            if mode == "cry":
                ell(d, x, ey, er_x * wide * 1.15, er_y * wide * 1.4, (200, 70, 70, 70))
        # sobrancelha
        by = ey - ry * (0.24 if mode in ("scared", "cry") else 0.19)
        tilt = (-0.14 if mode in ("scared", "cry") else 0.05) * ry
        d.line([((x - er_x * 1.2) * SS, (by - (tilt if sx > 0 else -tilt) * -1) * SS), ((x + er_x * 1.2) * SS, (by - tilt * sx * -1 * -1) * SS)],
               fill=(30, 20, 16, 255), width=int(SS * (2.2 if female else 3.4)))
    # nariz
    d.line([(cx * SS, (cy - ry * .02) * SS), ((cx + rx * .08) * SS, (cy + ry * .24) * SS)], fill=tuple(int(c * 0.7) for c in skin) + (255,), width=SS * 2)
    # boca
    my = cy + ry * 0.52
    if mode == "scared":
        ell(d, cx, my, rx * 0.2, ry * 0.12, (60, 20, 22))
    elif mode == "cry":
        ell(d, cx, my, rx * 0.26, ry * 0.18, (60, 20, 22))
        ell(d, cx, my + ry * .06, rx * 0.15, ry * 0.06, (150, 70, 70))
    elif mode == "nervous":
        d.arc([(cx - rx * .34) * SS, (my - ry * .20) * SS, (cx + rx * .34) * SS, (my + ry * .16) * SS], 10, 170, fill=(70, 30, 30, 255), width=SS * 3)
        d.chord([(cx - rx * .3) * SS, (my - ry * .1) * SS, (cx + rx * .3) * SS, (my + ry * .13) * SS], 0, 180, fill=(235, 232, 225, 255))
    elif poss:
        # sorriso vazio e macabro: largo, fino, cantos subindo
        d.arc([(cx - rx * .62) * SS, (my - ry * .42) * SS, (cx + rx * .62) * SS, (my + ry * .30) * SS], 12, 168, fill=(25, 12, 14, 255), width=int(SS * 3.2))
        d.chord([(cx - rx * .55) * SS, (my - ry * .22) * SS, (cx + rx * .55) * SS, (my + ry * .22) * SS], 15, 165, fill=(18, 8, 10, 255))
        for i in range(-4, 5):
            tx = cx + i * rx * 0.11
            d.rectangle([(tx - rx * .04) * SS, (my + ry * .02) * SS, (tx + rx * .04) * SS, (my + ry * .1) * SS], fill=(200, 205, 200, 255))
    else:
        d.line([((cx - rx * .2) * SS, my * SS), ((cx + rx * .2) * SS, my * SS)], fill=(80, 40, 40, 255), width=SS * 2)
    if glasses:
        gy = ey
        for sx in (-1, 1):
            x = cx + sx * ex
            d.rounded_rectangle([(x - er_x * 1.7) * SS, (gy - er_y * 2.0 + sx * crooked * ry) * SS, (x + er_x * 1.7) * SS, (gy + er_y * 2.0 + sx * crooked * ry) * SS],
                                radius=3 * SS, outline=(10, 10, 10, 255), width=int(SS * 3.2))
        d.line([((cx - ex + er_x * 1.7) * SS, (gy - crooked * ry) * SS), ((cx + ex - er_x * 1.7) * SS, (gy + crooked * ry) * SS)], fill=(10, 10, 10, 255), width=SS * 3)
    if female:
        d.line([((cx - ex - er_x * 1.2) * SS, (ey - er_y * 0.6) * SS), ((cx - ex - er_x * 1.5) * SS, (ey - er_y * 1.0) * SS)], fill=(20, 14, 12, 255), width=SS * 2)


# ------------------------------------------------------------------------------------ cabeça (para animar giro)
def head_sprite(who, view, possessed=False, w=220, h=300):
    """who: marcos|clara. view: front|back. retorna RGBA (pescoço incluso)"""
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    skin = SKIN_POS if possessed else SKIN
    cx, cy = w / 2, h * 0.42
    rx, ry = w * 0.30, h * 0.30
    limb(d, (cx, cy + ry * 0.7), (cx, h - 2), w * 0.20, w * 0.26, tuple(int(c * 0.9) for c in skin) + (255,))
    if view == "back":
        ell(d, cx, cy, rx, ry, skin + (255,))
        if who == "marcos":
            ell(d, cx, cy - ry * 0.25, rx * 1.02, ry * 0.8, (34, 24, 18, 255))
            ell(d, cx, cy + ry * 0.55, rx * 0.95, ry * 0.45, tuple(int(c * 0.78) for c in skin) + (255,))  # laterais raspadas
            ell(d, cx, cy - ry * 0.55, rx * 0.9, ry * 0.45, (40, 30, 22, 255))
        else:
            ell(d, cx, cy, rx * 1.04, ry * 1.02, (26, 20, 20, 255))
            limb(d, (cx, cy - ry * 0.7), (cx + rx * 0.25, cy + ry * 1.5), rx * 0.34, rx * 0.16, (26, 20, 20, 255))  # rabo de cavalo alto caindo
        for sx in (-1, 1):
            ell(d, cx + sx * rx * 0.98, cy + ry * 0.1, rx * 0.16, ry * 0.2, skin + (255,))   # orelhas
    else:
        face(d, cx, cy, rx, ry, "possessed" if possessed else "scared", female=(who == "clara"),
             glasses=(who == "marcos"), crooked=0.1 if possessed else 0.0, skin=skin)
        if who == "marcos":
            ell(d, cx, cy - ry * 0.78, rx * 0.95, ry * 0.4, (34, 24, 18, 255))
            d.rectangle([(cx - rx) * SS, (cy - ry * 0.45) * SS, (cx + rx) * SS, (cy - ry * 0.1) * SS], fill=None)
        else:
            ell(d, cx, cy - ry * 0.82, rx * 1.08, ry * 0.45, (26, 20, 20, 255))
            d.rectangle([(cx - rx * 1.08) * SS, (cy - ry * 0.85) * SS, (cx - rx * 0.78) * SS, (cy + ry * 0.2) * SS], fill=(26, 20, 20, 255))
            d.rectangle([(cx + rx * 0.78) * SS, (cy - ry * 0.85) * SS, (cx + rx * 1.08) * SS, (cy + ry * 0.2) * SS], fill=(26, 20, 20, 255))
            limb(d, (cx + rx * 0.4, cy - ry * 1.0), (cx + rx * 1.15, cy - ry * 1.5), rx * 0.30, rx * 0.16, (26, 20, 20, 255))  # rabo alto
            ell(d, cx + rx * 0.42, cy - ry * 1.0, rx * 0.14, rx * 0.14, (200, 60, 80, 255))
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ corpo em pé
CW, CHH = 480, 1100


def person(who, pose="neutral", view="front", head=True, possessed=False, tilt=0.0):
    """who: marcos|clara. pose: neutral|neck|point|crossed|torn. head=False -> sem cabeça (para animar separado)"""
    im = _canvas(CW, CHH)
    d = ImageDraw.Draw(im, "RGBA")
    skin = (SKIN_POS if possessed else SKIN) + (255,)
    cx = CW / 2
    jeans = (36, 50, 84, 255) if who == "marcos" else (48, 52, 44, 255)
    shoe = (205, 205, 200, 255) if who == "marcos" else (30, 30, 30, 255)
    # pernas
    for sx in (-1, 1):
        limb(d, (cx + sx * 42, 600), (cx + sx * 50, 1030), 98, 66, jeans)
        limb(d, (cx + sx * 50, 1030), (cx + sx * 54 + 4, 1072), 66, 72, shoe)
        ell(d, cx + sx * 56 + 6, 1076, 46, 18, shoe)
    if who == "clara":
        for sx in (-1, 1):  # bolsos cargo
            d.rounded_rectangle([(cx + sx * 56 - 24) * SS, 760 * SS, (cx + sx * 56 + 24) * SS, 840 * SS], radius=6 * SS, outline=(25, 28, 24, 255), width=3 * SS)
    # tronco
    if who == "marcos":
        torso_col = (228, 228, 222, 255)
        d.polygon([(a * SS, b * SS) for a, b in [(cx - 118, 222), (cx + 118, 222), (cx + 98, 640), (cx - 98, 640)]], fill=torso_col)
        # camisa xadrez aberta (faixas laterais)
        pl = plaid((CW, CHH))
        def mk(md, cx=cx):
            md.polygon([(a * SS, b * SS) for a, b in [(cx - 130, 218), (cx - 34, 226), (cx - 40, 700), (cx - 112, 700)]], fill=255)
            md.polygon([(a * SS, b * SS) for a, b in [(cx + 130, 218), (cx + 34, 226), (cx + 40, 700), (cx + 112, 700)]], fill=255)
        if view == "back":
            d.polygon([(a * SS, b * SS) for a, b in [(cx - 124, 218), (cx + 124, 218), (cx + 106, 700), (cx - 106, 700)]], fill=(150, 22, 24, 255))
            def mk(md, cx=cx):
                md.polygon([(a * SS, b * SS) for a, b in [(cx - 124, 218), (cx + 124, 218), (cx + 106, 700), (cx - 106, 700)]], fill=255)
        paste_masked(im, pl, mk)
        if pose == "torn" or possessed:    # ombro rasgado
            d.polygon([(a * SS, b * SS) for a, b in [(cx - 128, 220), (cx - 74, 228), (cx - 90, 300), (cx - 118, 284), (cx - 104, 260)]], fill=(60, 44, 40, 255))
            d.polygon([(a * SS, b * SS) for a, b in [(cx - 118, 232), (cx - 84, 240), (cx - 96, 280)]], fill=skin)
    else:
        jacket = (138, 168, 208, 255)
        d.polygon([(a * SS, b * SS) for a, b in [(cx - 112, 222), (cx + 112, 222), (cx + 94, 600), (cx - 94, 600)]], fill=(236, 236, 232, 255))
        if view == "front":
            for y in range(250, 560, 14):   # regata canelada
                d.line([((cx - 34) * SS, y * SS), ((cx + 34) * SS, y * SS)], fill=(190, 190, 186, 255), width=SS * 2)
            d.polygon([(a * SS, b * SS) for a, b in [(cx - 118, 218), (cx - 30, 226), (cx - 38, 620), (cx - 104, 620)]], fill=jacket)
            d.polygon([(a * SS, b * SS) for a, b in [(cx + 118, 218), (cx + 30, 226), (cx + 38, 620), (cx + 104, 620)]], fill=jacket)
            d.line([((cx - 34) * SS, 226 * SS), ((cx - 40) * SS, 620 * SS)], fill=(88, 116, 160, 255), width=SS * 3)
            d.line([((cx + 34) * SS, 226 * SS), ((cx + 40) * SS, 620 * SS)], fill=(88, 116, 160, 255), width=SS * 3)
        else:
            d.polygon([(a * SS, b * SS) for a, b in [(cx - 118, 218), (cx + 118, 218), (cx + 100, 620), (cx - 100, 620)]], fill=jacket)
    # braços
    sleeve = (150, 22, 24, 255) if who == "marcos" else (138, 168, 208, 255)
    arm_w0, arm_w1 = 62, 50
    shL, shR = (cx - 118, 246), (cx + 118, 246)
    def sleeve_limb(p0, p1, w0, w1):
        if who == "marcos":
            tmp = _canvas(CW, CHH)
            td = ImageDraw.Draw(tmp, "RGBA")
            limb(td, p0, p1, w0, w1, (255, 255, 255, 255))
            m = tmp.split()[3]
            im.paste(plaid((CW, CHH)), (0, 0), m)
        else:
            limb(d, p0, p1, w0, w1, sleeve)
    if pose == "crossed":
        sleeve_limb(shL, (cx - 100, 420), arm_w0, arm_w1)
        sleeve_limb(shR, (cx + 100, 420), arm_w0, arm_w1)
        sleeve_limb((cx - 100, 420), (cx + 70, 372), arm_w1, 44)
        sleeve_limb((cx + 100, 420), (cx - 70, 382), arm_w1, 44)
        ell(d, cx + 74, 372, 24, 20, skin)
        ell(d, cx - 74, 382, 24, 20, skin)
    elif pose == "neck":
        sleeve_limb(shL, (cx - 124, 470), arm_w0, arm_w1)
        ell(d, cx - 128, 520, 26, 30, skin)
        sleeve_limb(shR, (cx + 150, 250), arm_w0, arm_w1)
        sleeve_limb((cx + 150, 250), (cx + 52, 102), arm_w1, 44)   # mão na nuca
        ell(d, cx + 40, 100, 24, 24, skin)
    elif pose == "point":
        sleeve_limb(shL, (cx - 124, 470), arm_w0, arm_w1)
        ell(d, cx - 128, 520, 26, 30, skin)
        sleeve_limb(shR, (cx + 140, 440), arm_w0, arm_w1)
        sleeve_limb((cx + 140, 440), (cx + 120, 590), arm_w1, 46)
        ell(d, cx + 118, 614, 26, 28, skin)
        d.rounded_rectangle([(cx + 112) * SS, 600 * SS, (cx + 142) * SS, 700 * SS], radius=8 * SS, fill=(28, 28, 30, 255))
        ell(d, cx + 127, 704, 17, 10, (235, 245, 255, 255))
    else:
        sleeve_limb(shL, (cx - 130, 470), arm_w0, arm_w1)
        sleeve_limb((cx - 130, 470), (cx - 120, 600), arm_w1, 44)
        ell(d, cx - 118, 622, 26, 28, skin)
        sleeve_limb(shR, (cx + 130, 470), arm_w0, arm_w1)
        sleeve_limb((cx + 130, 470), (cx + 122, 600), arm_w1, 44)
        ell(d, cx + 120, 622, 26, 28, skin)
        if pose == "neutral" and who == "marcos":
            d.rounded_rectangle([(cx + 108) * SS, 612 * SS, (cx + 138) * SS, 700 * SS], radius=8 * SS, fill=(28, 28, 30, 255))
    # cinto / detalhes
    if who == "marcos":
        d.line([((cx - 96) * SS, 610 * SS), ((cx + 96) * SS, 610 * SS)], fill=(20, 14, 10, 255), width=SS * 5)
    # pescoço + cabeça
    if head:
        hs = head_sprite(who, view, possessed)
        if tilt:
            hs = hs.rotate(tilt, expand=True, resample=Image.BICUBIC, center=(hs.width / 2, hs.height * 0.9))
        im_small = _fin(im, CW, CHH)
        im_small.alpha_composite(hs, (int(cx - hs.width / 2), int(222 - hs.height * 0.86)))
        return im_small
    return _fin(im, CW, CHH)


# ------------------------------------------------------------------------------------ Clara encolhida
def clara_huddle(up=False, w=720, h=620):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    jacket = (138, 168, 208, 255)
    pants = (46, 50, 44, 255)
    hair = (26, 20, 20, 255)
    skin = SKIN + (255,)
    # canto (sombra)
    # pernas dobradas: joelhos pra cima
    limb(d, (w * .52, h * .88), (w * .46, h * .42), 150, 120, pants)
    limb(d, (w * .60, h * .92), (w * .56, h * .40), 150, 120, pants)
    ell(d, w * .50, h * .93, 120, 30, (30, 30, 30, 255))
    # tronco inclinado
    limb(d, (w * .30, h * .90), (w * .38, h * .48), 190, 160, jacket)
    d.polygon([(a * SS, b * SS) for a, b in [(w * .34, h * .52), (w * .44, h * .50), (w * .40, h * .86), (w * .28, h * .86)]], fill=(236, 236, 232, 255))
    # braços envolvendo joelhos
    limb(d, (w * .36, h * .56), (w * .52, h * .36), 70, 58, jacket)
    ell(d, w * .55, h * .35, 30, 26, skin)
    if not up:
        ell(d, w * .46, h * .30, 86, 80, hair)   # cabeça baixa, só cabelo
        limb(d, (w * .40, h * .28), (w * .22, h * .12), 38, 24, hair)  # rabo de cavalo
        ell(d, w * .22, h * .12, 24, 26, hair)
        limb(d, (w * .50, h * .42), (w * .60, h * .34), 70, 58, jacket)
    else:
        face(d, w * .42, h * .24, 66, 78, "cry", female=True)
        ell(d, w * .42, h * .14, 74, 44, hair)
        d.rectangle([(w * .42 - 74) * SS, (h * .14) * SS, (w * .42 - 54) * SS, (h * .30) * SS], fill=hair)
        d.rectangle([(w * .42 + 54) * SS, (h * .14) * SS, (w * .42 + 74) * SS, (h * .30) * SS], fill=hair)
        limb(d, (w * .36, h * .12), (w * .2, h * .02), 34, 20, hair)
        ell(d, w * .2, h * .04, 22, 26, hair)
        # braço apontando pro fundo do corredor (direita)
        limb(d, (w * .50, h * .46), (w * .86, h * .30), 62, 44, jacket)
        ell(d, w * .90, h * .285, 24, 20, skin)
        limb(d, (w * .91, h * .28), (w * .99, h * .26), 12, 9, skin)
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ Lucas (close-up final)
def lucas_close(w=900, h=1200):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    cx = w / 2
    # capuz preto
    ell(d, cx, h * 1.02, w * .72, h * .30, (14, 14, 16, 255))
    ell(d, cx, h * .86, w * .46, h * .16, (20, 20, 22, 255))
    d.polygon([(a * SS, b * SS) for a, b in [(cx - w * .5, h), (cx - w * .26, h * .78), (cx + w * .26, h * .78), (cx + w * .5, h)]], fill=(16, 16, 18, 255))
    # pescoço
    limb(d, (cx, h * .70), (cx, h * .82), w * .30, w * .34, SKIN_POS + (255,))
    # corrente de prata
    d.arc([(cx - w * .2) * SS, (h * .76) * SS, (cx + w * .2) * SS, (h * .93) * SS], 20, 160, fill=(200, 205, 212, 255), width=SS * 4)
    # rosto
    fcx, fcy, rx, ry = cx, h * .44, w * .30, h * .29
    face(d, fcx, fcy, rx, ry, "possessed", skin=SKIN_POS)
    # olheiras fundas
    for sx in (-1, 1):
        ell(d, fcx + sx * rx * .42, fcy - ry * .02 + ry * .17, rx * .3, ry * .10, (92, 98, 102, 200))
    # sombras de bochecha
    ell(d, fcx, fcy + ry * .2, rx * .9, ry * .8, (90, 96, 98, 28))
    # cabelo cacheado/ondulado caindo na testa
    rng = np.random.default_rng(3)
    ell(d, fcx, fcy - ry * .78, rx * 1.12, ry * .52, (18, 14, 14, 255))
    for i in range(34):
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        r = rng.uniform(.55, 1.12)
        x = fcx + math.cos(a) * rx * r
        y = fcy - ry * .45 + math.sin(a) * ry * r * 0.9
        ell(d, x, y + ry * rng.uniform(0.0, 0.28), rx * rng.uniform(.10, .18), ry * rng.uniform(.10, .2), (20, 15, 15, 255))
    for sx in (-1, 1):
        for k in range(4):
            ell(d, fcx + sx * rx * (0.95 - k * 0.04), fcy - ry * .25 + k * ry * .15, rx * .12, ry * .13, (20, 15, 15, 255))
    # franja ondulada sobre a testa
    for i in range(10):
        x = fcx - rx * .8 + i * rx * .18
        ell(d, x, fcy - ry * .58 + (i % 3) * ry * .04, rx * .12, ry * .13, (20, 15, 15, 255))
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ mão pálida de dedos longos
def pale_hand(w=900, h=1100):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    skin = (176, 182, 184, 255)
    dark = (120, 126, 130, 255)
    cx = w / 2
    # antebraço
    limb(d, (cx, h * 1.05), (cx, h * .70), w * .34, w * .26, skin)
    # palma
    d.polygon([(a * SS, b * SS) for a, b in [(cx - w * .20, h * .76), (cx + w * .20, h * .76), (cx + w * .23, h * .50), (cx - w * .23, h * .50)]], fill=skin)
    ell(d, cx, h * .50, w * .23, h * .06, skin)
    # dedos longos (4) + polegar
    fingers = [(-0.19, .50, -0.22, .10), (-0.065, .48, -0.07, .02), (0.065, .48, 0.07, .04), (0.19, .50, 0.23, .14)]
    for (x0, y0, x1, y1) in fingers:
        p0, p1 = (cx + w * x0, h * y0), (cx + w * x1, h * y1)
        pm = ((p0[0] + p1[0]) / 2 + w * 0.01, (p0[1] + p1[1]) / 2)
        limb(d, p0, pm, w * .105, w * .088, skin)
        limb(d, pm, p1, w * .088, w * .064, skin)
        ell(d, pm[0], pm[1], w * .048, w * .03, dark)                                           # nó dos dedos
        ell(d, p1[0], p1[1] - 6, w * .034, h * .02, (28, 22, 24, 255))                           # unha escurecida
    limb(d, (cx - w * .22, h * .66), (cx - w * .40, h * .44), w * .11, w * .075, skin)          # polegar
    ell(d, cx - w * .405, h * .435, w * .036, h * .02, (28, 22, 24, 255))
    # veias
    for k in range(5):
        d.line([((cx - w * .1 + k * w * .05) * SS, h * .9 * SS), ((cx - w * .08 + k * w * .04) * SS, h * .6 * SS)], fill=(110, 120, 150, 120), width=SS * 3)
    return _fin(im, w, h, blur=0.6)


# ------------------------------------------------------------------------------------ braço do Marcos entrando na tela
def marcos_arm(w=700, h=260):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    tmp = _canvas(w, h)
    td = ImageDraw.Draw(tmp, "RGBA")
    limb(td, (w * 1.02, h * .62), (w * .46, h * .52), 150, 92, (255, 255, 255, 255))
    pl = plaid((w, h))
    im.paste(pl, (0, 0), tmp.split()[3])
    skin = SKIN + (255,)
    ell(d, w * .40, h * .50, 54, 44, skin)
    # dedos estendidos para a esquerda
    for i, dy in enumerate((-34, -12, 10, 30)):
        limb(d, (w * .40, h * .50 + dy * .6), (w * (.17 - 0.01 * abs(i - 1.5)), h * .46 + dy), 26, 18, skin)
    limb(d, (w * .42, h * .62), (w * .26, h * .80), 26, 18, skin)
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ armário metálico enferrujado
def cabinet(w=300, h=820):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle(S(8, 8, w - 8, h - 8), fill=(96, 52, 30, 255), outline=(40, 22, 14, 255), width=SS * 4)
    rng = np.random.default_rng(4)
    for k in range(4):
        y0 = 22 + k * (h - 44) // 4
        y1 = y0 + (h - 44) // 4 - 8
        d.rectangle(S(20, y0, w - 20, y1), fill=(110, 62, 36, 255), outline=(48, 26, 16, 255), width=SS * 3)
        d.rectangle(S(w * .36, y0 + 18, w * .64, y0 + 30), fill=(28, 24, 22, 255))
        d.rectangle(S(w * .30, y0 + 52, w * .70, y0 + 82), fill=(150, 140, 120, 255), outline=(30, 26, 22, 255), width=SS * 2)
        for _ in range(14):   # ferrugem
            rx = rng.uniform(20, w - 20)
            ry = rng.uniform(y0, y1)
            r = rng.uniform(4, 22)
            ell(d, rx, ry, r, r * rng.uniform(.5, 1.6), (140, 66, 26, int(rng.uniform(80, 200))))
        d.line(S(rng.uniform(30, w - 30), y0, rng.uniform(30, w - 30), y1), fill=(30, 18, 12, 200), width=SS * 2)
    # amassados
    for _ in range(6):
        ell(d, rng.uniform(30, w - 30), rng.uniform(40, h - 40), rng.uniform(18, 40), rng.uniform(22, 50), (30, 18, 12, 90))
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ fios pendurados
def cable(seed=0, w=120, h=420):
    im = _canvas(w, h)
    d = ImageDraw.Draw(im, "RGBA")
    rng = np.random.default_rng(seed)
    for k in range(rng.integers(2, 4)):
        x0 = w * rng.uniform(.35, .65)
        pts = []
        for i in range(0, 41):
            t = i / 40
            pts.append((x0 + math.sin(t * rng.uniform(2, 5) + k) * w * rng.uniform(.08, .22) * t * 2, t * h * rng.uniform(.65, 1.0)))
        wd = int(SS * rng.uniform(5, 9))
        d.line([(x * SS, y * SS) for x, y in pts], fill=(14, 14, 15, 255), width=wd)
        d.line([((x + 2) * SS, y * SS) for x, y in pts], fill=(52, 54, 58, 255), width=max(1, wd // 3))
    return _fin(im, w, h)


# ------------------------------------------------------------------------------------ corrente enferrujada (screen-space)
def draw_chain(img_draw, p0, p1, grow, link=26, color=(86, 62, 44), hi=(150, 120, 90)):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    n = int(L / link * grow)
    ang = math.atan2(y1 - y0, x1 - x0)
    for i in range(n):
        px, py = x0 + math.cos(ang) * link * (i + .5), y0 + math.sin(ang) * link * (i + .5)
        rx, ry = (link * .62, link * .34) if i % 2 == 0 else (link * .38, link * .30)
        pts = []
        for a in range(0, 360, 15):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            ex, ey = ca * rx, sa * ry
            pts.append((px + ex * math.cos(ang) - ey * math.sin(ang), py + ex * math.sin(ang) + ey * math.cos(ang)))
        img_draw.polygon(pts, outline=color + (255,), fill=None)
        img_draw.line(pts + [pts[0]], fill=color + (255,), width=max(3, int(link * .22)))
        img_draw.line(pts[:6], fill=hi + (255,), width=max(1, int(link * .07)))
