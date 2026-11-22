#!/usr/bin/env python3
"""Turno da Noite - vídeo POV vertical 9:16 para TikTok (~70s).
Renderiza frames com PIL, sintetiza áudio (narração espeak-ng + SFX) e monta com ffmpeg.
Uso: python3 render.py [saida.mp4]
"""
import math, random, subprocess, sys, wave, os, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 540, 960, 24
DUR = 70.0
OUT = sys.argv[1] if len(sys.argv) > 1 else "turno_da_noite.mp4"
BLACK = (12, 10, 16)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(sz): return ImageFont.truetype(FONT, sz)
random.seed(7)

# ---------------- roteiro (narração + legendas) ----------------
# (inicio, fim, texto narrado, legenda, palavra-chave em destaque)
LINES = [
    (1.0, 6.0,  "Turno da noite. Duas da manhã. O mercado está vazio.", "TURNO DA NOITE. 2H DA MANHÃ.", "2H"),
    (7.0, 11.5, "Falta pouco pra acabar... só repor essas latas.", "FALTA POUCO PRA ACABAR...", "ACABAR"),
    (13.5, 18.0, "De repente, as luzes piscam. E apagam.", "AS LUZES APAGARAM.", "APAGARAM"),
    (19.0, 24.5, "Lá fora, a rua está deserta. Mas aquela luz... não é normal.", "AQUELA LUZ NÃO É NORMAL.", "LUZ"),
    (26.0, 31.0, "O gerente aparece correndo. Tranca a porta da frente.", "O GERENTE TRANCOU A PORTA.", "TRANCOU"),
    (32.0, 39.5, "Todo mundo pros fundos! Não olhem pra rua! E não façam barulho!", "NÃO OLHEM PRA RUA!", "RUA"),
    (41.0, 46.0, "Nos fundos, o alarme da entrada dispara sozinho.", "O ALARME DISPAROU SOZINHO.", "ALARME"),
    (47.0, 52.5, "Meu celular vibra. Uma foto. Tirada de dentro da loja.", "UMA FOTO. DE DENTRO DA LOJA.", "DENTRO"),
    (53.0, 57.5, "O gerente sussurra: ignora. Fica quieto.", "\"IGNORA. FICA QUIETO.\"", "IGNORA"),
    (59.0, 64.0, "A porta da frente... está logo ali. E agora?", "E AGORA?", "AGORA"),
]
SCENES = [(0, 12.5, 1), (12.5, 25.5, 2), (25.5, 40.5, 3), (40.5, 58.5, 4), (58.5, DUR, 5)]
def scene_at(t):
    for a, b, s in SCENES:
        if a <= t < b: return s, (t - a) / (b - a), t - a
    return 5, 1.0, t

# ---------------- utilidades de desenho ----------------
def poly(d, pts, fill, w=5): d.polygon(pts, fill=fill, outline=BLACK, width=w)
def rect(d, box, fill, w=5): d.rectangle(box, fill=fill, outline=BLACK, width=w)
def ell(d, box, fill, w=5): d.ellipse(box, fill=fill, outline=BLACK, width=w)
def mix(c1, c2, k): return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

def shake(t, amp=3):
    return (math.sin(t * 7.3) * amp, math.cos(t * 5.1) * amp * 0.8 + math.sin(t * 1.6) * amp)

def aisle(d, light, t, red=0.0):
    """corredor em perspectiva com prateleiras"""
    cx, cy = W // 2, 470
    floor = mix((90, 96, 120), (40, 30, 40), 1 - light)
    wall = mix((190, 200, 220), (60, 40, 55), 1 - light)
    rect(d, (0, 0, W, H), wall, 0)
    # teto e piso
    poly(d, [(0, 0), (W, 0), (cx + 60, cy - 90), (cx - 60, cy - 90)], mix((220, 225, 235), (30, 25, 40), 1 - light))
    poly(d, [(0, H), (W, H), (cx + 60, cy + 90), (cx - 60, cy + 90)], floor)
    # prateleiras laterais
    for side in (-1, 1):
        x0 = 0 if side < 0 else W
        xi = cx - 60 if side < 0 else cx + 60
        for lvl in range(4):
            y0 = 120 + lvl * 190
            yi = cy - 80 + lvl * 50
            col = mix((70, 130, 220), (230, 90, 70), (lvl + (0 if side < 0 else 1)) % 2)
            col = mix(col, (30, 20, 40), 1 - light)
            poly(d, [(x0, y0), (xi, yi), (xi, yi + 40), (x0, y0 + 90)], col)
            # produtos
            for k in range(7):
                f = 0.08 + k * 0.13
                px = x0 + (xi - x0) * f
                py = y0 + (yi - y0) * f
                s = 38 * (1 - f * 0.8)
                pc = [(255, 200, 60), (240, 80, 90), (90, 200, 120), (240, 240, 240)][(k + lvl) % 4]
                pc = mix(pc, (35, 25, 45), 1 - light * 0.9)
                rect(d, (px - s / 2, py + 20 - s, px + s / 2, py + 20), pc, 3)
    # luzes de teto
    for k in range(5):
        f = k / 5
        y = cy - 90 - f * 0 + (1 - f) * -0
        yy = 40 + (cx and (1 - f)) * 0
    for k in range(4):
        f = (k + 1) / 5
        yy = 90 + (cy - 90 - 90) * f * 0.85
        w = 90 * (1 - f * 0.8)
        lc = mix((255, 255, 240), (80, 80, 90), 1 - light)
        rect(d, (cx - w, yy, cx + w, yy + 10 * (1 - f * .6)), lc, 3)
    if red > 0:
        pass

def hands(d, t, mode="stock", off=0):
    """mãos do protagonista (POV)"""
    bob = math.sin(t * 2.2) * 6
    skin = (240, 190, 150)
    sleeve = (30, 40, 70)
    for side in (-1, 1):
        bx = W // 2 + side * 150
        rect(d, (bx - 55, H - 190 + bob, bx + 55, H + 20), sleeve, 5)
        ell(d, (bx - 50, H - 270 + bob + off, bx + 50, H - 170 + bob), skin, 5)
        for f in range(4):
            fx = bx - 36 + f * 24
            ell(d, (fx, H - 305 + bob + off + (f % 2) * 8, fx + 22, H - 250 + bob), skin, 4)
    if mode == "stock":
        can_y = H - 330 + bob - 20 * math.sin(t * 1.5)
        for dx in (-150, 150):
            rect(d, (W // 2 + dx - 28, can_y - 40, W // 2 + dx + 28, can_y + 45), (230, 70, 70), 5)
            rect(d, (W // 2 + dx - 28, can_y - 10, W // 2 + dx + 28, can_y + 12), (245, 245, 245), 3)

def person(d, x, y, sc, shirt, face=(240, 190, 150), mood="calm", hair=(40, 30, 30), apron=False, look=0):
    """personagem estilizado, contorno grosso. y = base do tronco"""
    s = sc
    rect(d, (x - 70 * s, y - 40 * s, x + 70 * s, y + 260 * s), shirt, 6)
    if apron: rect(d, (x - 50 * s, y + 20 * s, x + 50 * s, y + 260 * s), (210, 60, 60), 5)
    rect(d, (x - 18 * s, y - 75 * s, x + 18 * s, y - 35 * s), face, 5)
    ell(d, (x - 62 * s, y - 230 * s, x + 62 * s, y - 60 * s), face, 6)
    d.pieslice((x - 66 * s, y - 238 * s, x + 66 * s, y - 100 * s), 180, 360, fill=hair, outline=BLACK, width=5)
    ey = y - 150 * s
    for ex in (-26, 26):
        ell(d, (x + (ex - 15) * s, ey - 17 * s, x + (ex + 15) * s, ey + 17 * s), (255, 255, 255), 4)
        px = x + (ex + look * 7) * s
        r = (4 if mood in ("shock", "tense") else 7) * s
        ell(d, (px - r, ey - r, px + r, ey + r), BLACK, 0)
    if mood == "shock":
        ell(d, (x - 14 * s, y - 108 * s, x + 14 * s, y - 80 * s), (90, 30, 40), 4)
        d.line((x - 48 * s, ey - 38 * s, x - 10 * s, ey - 50 * s), fill=BLACK, width=5)
        d.line((x + 10 * s, ey - 50 * s, x + 48 * s, ey - 38 * s), fill=BLACK, width=5)
    elif mood == "tense":
        d.line((x - 20 * s, y - 95 * s, x + 20 * s, y - 100 * s), fill=BLACK, width=6)
        d.line((x - 48 * s, ey - 46 * s, x - 10 * s, ey - 32 * s), fill=BLACK, width=6)
        d.line((x + 10 * s, ey - 32 * s, x + 48 * s, ey - 46 * s), fill=BLACK, width=6)
    else:
        d.arc((x - 22 * s, y - 115 * s, x + 22 * s, y - 85 * s), 20, 160, fill=BLACK, width=5)

def tint(img, color, a):
    if a <= 0: return img
    ov = Image.new("RGB", img.size, color)
    return Image.blend(img, ov, min(a, 1))

def vignette(img, strength=0.55):
    mask = vig_mask()
    dark = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(img, dark, mask)
_vm = None
def vig_mask():
    global _vm
    if _vm is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        a = np.clip(1.15 - r * 0.45, 0, 1) * 255
        _vm = Image.fromarray(a.astype("uint8"), "L")
    return _vm

# ---------------- cenas ----------------
def scene1(d, u, t):
    aisle(d, 1.0, t)
    person(d, 400 + math.sin(t) * 6, 560, 0.62, (60, 140, 90), mood="calm", look=-1)
    hands(d, t, "stock")

def scene2(d, u, t, img_holder):
    # 0-0.35 piscando, depois vitrine com rua lá fora
    if u < 0.3:
        flick = 1.0 if int(t * 9) % 3 else 0.15
        if u > 0.2: flick = 0.1
        aisle(d, flick, t)
        person(d, 400, 560, 0.62, (60, 140, 90), mood="tense", look=-1)
        hands(d, t, "stock")
        img_holder["tint"] = ((40, 0, 0), 0.25 * (1 - flick))
    else:
        # montra
        rect(d, (0, 0, W, H), (22, 25, 40), 0)
        pulse = 0.6 + 0.4 * math.sin(t * 3)
        # rua
        rect(d, (30, 200, W - 30, 700), mix((15, 18, 30), (60, 30, 20), pulse * 0.25), 8)
        poly(d, [(30, 640), (W - 30, 640), (W - 30, 700), (30, 700)], (40, 40, 50))
        for k in range(6):
            d.line((60 + k * 80, 655, 90 + k * 80, 655), fill=(160, 150, 120), width=4)
        # poste anormal
        px = W // 2 + 60
        glow = Image.new("RGB", (W, H), (0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((px - 160, 150, px + 160, 470), fill=(int(255 * pulse), int(150 * pulse), 20))
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        img_holder["add"] = glow
        rect(d, (px - 7, 260, px + 7, 650), (30, 28, 34), 4)
        ell(d, (px - 28, 235, px + 28, 290), (255, 210, 90), 5)
        # reflexo do protagonista / colega no vidro
        ell(d, (60, 330, 150, 420), (50, 55, 80), 3)
        rect(d, (45, 410, 165, 640), (45, 50, 75), 3)
        # colega imóvel olhando (silhueta lado)
        person(d, 150, 700, 0.5, (40, 90, 60), mood="shock", look=1)
        # moldura da porta
        d.line((W // 2, 200, W // 2, 700), fill=BLACK, width=10)
        rect(d, (0, 0, W, 200), (14, 14, 22), 0); rect(d, (0, 700, W, H), (14, 14, 22), 0)
        hands(d, t, None)
        # LED verde de emergência
        ell(d, (W - 90, 90, W - 50, 130), (60, 255, 120), 4)
    img_holder["tint"] = img_holder.get("tint", ((10, 140, 80), 0.18 if u > 0.3 else 0.0))

def scene3(d, u, t, img_holder):
    # gerente em primeiro plano; depois corredor dos fundos
    if u < 0.45:
        rect(d, (0, 0, W, H), (24, 20, 34), 0)
        # porta de vidro com tranca
        rect(d, (60, 120, W - 60, 520), (30, 50, 80), 8)
        d.line((W // 2, 120, W // 2, 520), fill=BLACK, width=8)
        lock = (0.5 + 0.5 * min(1, max(0, (u - 0.1) * 4)))
        ell(d, (W // 2 - 26, 330, W // 2 + 26, 382), (230, 200, 70) if lock > 0.9 else (150, 150, 160), 5)
        mx = 140 + 120 * min(1, u * 3)
        person(d, mx + math.sin(t * 9) * 4, 620, 1.05, (28, 28, 40), mood="tense", hair=(30, 30, 30), apron=False, look=1)
        # gravata
        poly(d, [(mx - 12, 650), (mx + 12, 650), (mx + 8, 760), (mx - 8, 760)], (180, 40, 50), 4)
        hands(d, t, None, off=-20)
        img_holder["tint"] = ((200, 20, 20), 0.14)
    else:
        v = (u - 0.45) / 0.55
        # corredor estreito dos fundos, avanço
        rect(d, (0, 0, W, H), (18, 14, 24), 0)
        cx, cy = W // 2, 430
        for k in range(8):
            f = (k + v * 1.0) % 8 / 8
            s = 0.1 + f ** 1.8 * 1.9
            a = 18 + int(60 * (1 - f))
            col = (a + 10, a, a + 24)
            half_w = 230 * s; half_h = 380 * s
            rect(d, (cx - half_w, cy - half_h, cx + half_w, cy + half_h), col, max(2, int(5 * s)))
            for sx in (-1, 1):
                for r in range(3):
                    bx = cx + sx * (half_w * 0.62)
                    by = cy - half_h * 0.4 + r * half_h * 0.4
                    bw = half_w * 0.25
                    pc = [(180, 70, 60), (70, 120, 180), (200, 170, 60)][r]
                    rect(d, (bx - bw, by - half_h * 0.12, bx + bw, by + half_h * 0.12), mix(pc, (20, 18, 28), 0.6), max(2, int(4 * s)))
        # sombra longa
        sh = Image.new("RGB", (W, H), (0, 0, 0))
        img_holder["add"] = None
        # silhueta do gerente na frente
        poly(d, [(60, 960), (110, 520), (200, 520), (250, 960)], (8, 8, 14), 5)
        ell(d, (110, 400, 200, 520), (8, 8, 14), 5)
        hands(d, t, None)
        img_holder["tint"] = ((20, 140, 90), 0.12)

def scene4(d, u, t, img_holder):
    rect(d, (0, 0, W, H), (16, 14, 24), 0)
    # estoque
    for sx in (60, 380):
        rect(d, (sx, 180, sx + 100, 760), (40, 34, 50), 6)
        for r in range(5):
            rect(d, (sx + 8, 210 + r * 110, sx + 92, 290 + r * 110), [(140, 90, 60), (90, 120, 150), (150, 130, 70)][r % 3], 4)
    alarm = int(t * 4) % 2 == 0 and u > 0.05
    img_holder["tint"] = ((255, 20, 20), 0.35 if alarm else 0.08)
    # gerente + colega agachados
    person(d, 270, 560, 0.72, (28, 28, 40), mood="tense", look=-1)
    person(d, 120, 640, 0.5, (40, 90, 60), mood="shock")
    # celular em primeiro plano
    ph_y = 330 - 60 * min(1, max(0, (u - 0.28) * 5))
    vib = math.sin(t * 60) * (4 if u > 0.28 else 0)
    px0 = W // 2 - 150 + vib
    if u > 0.28:
        rect(d, (px0, ph_y + 180, px0 + 300, ph_y + 720), (10, 10, 14), 8)
        rect(d, (px0 + 14, ph_y + 206, px0 + 286, ph_y + 690), (30, 40, 70), 4)
        # notificação
        rect(d, (px0 + 26, ph_y + 230, px0 + 274, ph_y + 300), (240, 240, 245), 4)
        d.text((px0 + 38, ph_y + 240), "Desconhecido", font=font(17), fill=BLACK)
        d.text((px0 + 38, ph_y + 266), "Nova foto recebida", font=font(15), fill=(200, 30, 40))
        if u > 0.45:
            # foto: corredor da loja com vulto
            rect(d, (px0 + 26, ph_y + 330, px0 + 274, ph_y + 600), (20, 20, 30), 4)
            poly(d, [(px0 + 40, ph_y + 600), (px0 + 90, ph_y + 400), (px0 + 210, ph_y + 400), (px0 + 260, ph_y + 600)], (45, 40, 60), 3)
            ell(d, (px0 + 120, ph_y + 380, px0 + 180, ph_y + 450), (6, 6, 10), 3)
            for ex in (140, 160):
                ell(d, (px0 + ex, ph_y + 408, px0 + ex + 8, ph_y + 416), (255, 40, 40), 0)
    hands(d, t, None, off=-30 if u > 0.28 else 0)
    # ícone de alarme
    if alarm:
        d.text((W // 2 - 90, 90), "! ALARME !", font=font(44), fill=(255, 60, 60))

def scene5(d, u, t, img_holder):
    # aproximação do corredor para a porta da frente, depois tela final
    if u < 0.5:
        v = u / 0.5
        rect(d, (0, 0, W, H), (14, 12, 22), 0)
        cx, cy = W // 2, 430
        s = 0.25 + v * 1.6
        # porta
        rect(d, (cx - 110 * s, cy - 190 * s, cx + 110 * s, cy + 220 * s), (50, 44, 60), max(3, int(6 * s)))
        rect(d, (cx - 80 * s, cy - 150 * s, cx + 80 * s, cy + 60 * s), (255, 150 + int(40 * math.sin(t * 5)), 30), max(3, int(5 * s)))
        ell(d, (cx + 70 * s, cy + 90 * s, cx + 92 * s, cy + 112 * s), (200, 200, 210), 3)
        # luz âmbar por baixo
        gl = Image.new("RGB", (W, H), (0, 0, 0)); gd = ImageDraw.Draw(gl)
        gd.rectangle((cx - 120 * s, cy + 190 * s, cx + 120 * s, cy + 240 * s), fill=(255, 140, 20))
        img_holder["add"] = gl.filter(ImageFilter.GaussianBlur(30))
        # paredes
        poly(d, [(0, 0), (cx - 110 * s, cy - 190 * s), (cx - 110 * s, cy + 220 * s), (0, H)], (24, 20, 34))
        poly(d, [(W, 0), (cx + 110 * s, cy - 190 * s), (cx + 110 * s, cy + 220 * s), (W, H)], (24, 20, 34))
        hands(d, t, None)
        img_holder["tint"] = ((20, 20, 20), 0.0)
    else:
        v = (u - 0.5) / 0.5
        rect(d, (0, 0, W, H), (10, 8, 16), 0)
        # fundo: pulso âmbar
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        d.text((W // 2, 140), "O QUE VOCÊ", font=font(58), fill=(255, 255, 255), anchor="mm")
        d.text((W // 2, 210), "FARIA?", font=font(88), fill=(255, 200, 40), anchor="mm")
        for i, (label, col, y) in enumerate([("A", (230, 60, 60), 360), ("B", (60, 130, 230), 650)]):
            a = min(1, max(0, (v - i * 0.25) * 4))
            if a <= 0: continue
            off = int((1 - a) * 400)
            rect(d, (40 + off, y, W - 40 + off, y + 230), mix((20, 20, 30), col, 0.85), 8)
            ell(d, (60 + off, y + 20, 140 + off, y + 100), (255, 255, 255), 6)
            d.text((100 + off, y + 60), label, font=font(54), fill=BLACK, anchor="mm")
            txt = ["Ir ver o que\ndisparou na frente", "Continuar escondido\nnos fundos"][i]
            d.multiline_text((W // 2 + 30 + off, y + 130), txt, font=font(28), fill=(255, 255, 255), anchor="mm", align="center", spacing=8)
        d.text((W // 2, 920), "COMENTA A / B", font=font(30), fill=(255, 200, 40), anchor="mm")
        img_holder["tint"] = ((0, 0, 0), 0.0)

# ---------------- legendas / HUD ----------------
def draw_subs(img, t):
    d = ImageDraw.Draw(img)
    for a, b, _, sub, key in LINES:
        if a <= t <= b + 0.4:
            f = font(40 if len(sub) < 22 else 33)
            words = sub.split(" ")
            lines, cur = [], ""
            for w in words:
                test = (cur + " " + w).strip()
                if d.textlength(test, font=f) > W - 60 and cur:
                    lines.append(cur); cur = w
                else: cur = test
            lines.append(cur)
            y = 780 - (len(lines) - 1) * 24
            for ln in lines:
                x = W // 2 - d.textlength(ln, font=f) / 2
                for wd in ln.split(" "):
                    col = (255, 215, 40) if key and key in wd else (255, 255, 255)
                    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
                        d.text((x + ox, y + oy), wd, font=f, fill=BLACK)
                    d.text((x, y), wd, font=f, fill=col)
                    x += d.textlength(wd + " ", font=f)
                y += 50
            break

def hud(img, t):
    d = ImageDraw.Draw(img)
    if int(t * 1.5) % 2 == 0:
        ell(d, (22, 22, 38, 38) if False else (22, 24, 40, 40), (230, 30, 30), 0)
    d.text((48, 22), "REC", font=font(20), fill=(255, 255, 255))
    d.text((W - 150, 22), "02:%02d AM" % (int(t // 60) + 3), font=font(20), fill=(255, 255, 255))

# ---------------- renderização de frame ----------------
def render_frame(t):
    s, u, lt = scene_at(t)
    img = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(img)
    hold = {}
    if s == 1: scene1(d, u, t); hold["tint"] = ((0, 0, 0), 0)
    elif s == 2: scene2(d, u, t, hold)
    elif s == 3: scene3(d, u, t, hold)
    elif s == 4: scene4(d, u, t, hold)
    else: scene5(d, u, t, hold)
    if hold.get("add") is not None:
        arr = np.clip(np.asarray(img, dtype=np.int16) + np.asarray(hold["add"], dtype=np.int16) // 2, 0, 255).astype("uint8")
        img = Image.fromarray(arr)
    c, a = hold.get("tint", ((0, 0, 0), 0))
    img = tint(img, c, a)
    # câmera tremida
    dx, dy = shake(t, 3 if s != 5 or u < 0.5 else 1)
    img = img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), resample=Image.BILINEAR)
    img = vignette(img)
    # tremida de glitch no final da cena 4
    if s == 4 and int(t * 12) % 7 == 0:
        arr = np.asarray(img).copy()
        arr[:, :, 0] = np.roll(arr[:, :, 0], 6, axis=1)
        img = Image.fromarray(arr)
    draw_subs(img, t)
    hud(img, t)
    # fade in / out entre cenas
    for a_, b_, _ in SCENES:
        if abs(t - a_) < 0.15 and a_ > 0:
            k = abs(t - a_) / 0.15
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, k)
    return img

# ---------------- áudio ----------------
SR = 44100
def tone(f, dur, vol=0.3, kind="sine"):
    n = int(SR * dur); x = np.arange(n) / SR
    if kind == "square": return vol * np.sign(np.sin(2 * np.pi * f * x))
    return vol * np.sin(2 * np.pi * f * x)
def add(track, t0, sig):
    i = int(t0 * SR); e = min(len(track), i + len(sig))
    if i < len(track): track[i:e] += sig[:e - i]
def noise(dur, vol=0.2): return vol * np.random.uniform(-1, 1, int(SR * dur))
def env(sig, a=0.01, r=0.1):
    n = len(sig); e = np.ones(n)
    na = int(a * SR); nr = int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] = np.linspace(1, 0, nr)
    return sig * e

def build_audio(path):
    total = int(DUR * SR)
    bed = np.zeros(total)
    # zumbido de lâmpada (cenas 1-2 inicial), some quando apaga
    hum = tone(120, 13.5, 0.05) + tone(240, 13.5, 0.03) + noise(13.5, 0.01)
    add(bed, 0, hum)
    # drone grave e tenso após 13.5s
    n = total - int(13.5 * SR); x = np.arange(n) / SR
    drone = 0.10 * np.sin(2 * np.pi * 48 * x + 3 * np.sin(2 * np.pi * 0.25 * x)) + 0.05 * np.sin(2 * np.pi * 51 * x)
    add(bed, 13.5, drone)
    # estalo da lâmpada apagando
    for tt in (13.7, 14.1, 14.4):
        add(bed, tt, env(noise(0.12, 0.35), 0.001, 0.1))
    # som metálico ao longe
    for tt in (19.5, 23.0):
        add(bed, tt, env(tone(70, 1.4, 0.35) * np.exp(-np.arange(int(1.4 * SR)) / SR * 2), 0.01, 0.4))
    # clique de fechadura
    for tt in (28.0, 28.4):
        add(bed, tt, env(noise(0.04, 0.6) + tone(900, 0.04, 0.3, "square"), 0.001, 0.03))
    # passos
    for tt in np.arange(33.0, 40.0, 0.45):
        add(bed, tt, env(tone(80, 0.12, 0.3) + noise(0.12, 0.08), 0.002, 0.1))
    # alarme
    for k in range(10):
        add(bed, 41.0 + k * 0.5, env(tone(1500 if k % 2 == 0 else 1100, 0.4, 0.22, "square"), 0.005, 0.05))
    # vibração + notificação do celular
    for k in range(6):
        add(bed, 47.0 + k * 0.12, env(tone(180, 0.08, 0.35, "square"), 0.001, 0.02))
    add(bed, 47.8, env(tone(1320, 0.12, 0.3) , 0.003, 0.08)); add(bed, 47.95, env(tone(1760, 0.2, 0.3), 0.003, 0.15))
    # riser antes da escolha
    rdur = 6.0; n = int(rdur * SR); x = np.arange(n) / SR
    f = 80 + 600 * (x / rdur) ** 2
    ris = 0.28 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (x / rdur)
    add(bed, 58.5, ris)
    add(bed, 64.5, env(tone(55, 1.2, 0.5), 0.005, 0.8))
    bed *= 0.85
    # narração
    narr = np.zeros(total)
    tmp = tempfile.mkdtemp()
    for i, (a, b, text, _, _) in enumerate(LINES):
        wav = os.path.join(tmp, f"n{i}.wav")
        subprocess.run(["espeak-ng", "-v", "pt-br+m3", "-s", "140", "-p", "28", "-a", "180", text, "-w", wav], check=True)
        with wave.open(wav) as w:
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
            sr = w.getframerate()
        # reamostra para 44.1k
        idx = np.linspace(0, len(raw) - 1, int(len(raw) * SR / sr))
        sig = np.interp(idx, np.arange(len(raw)), raw)
        # se maior que janela, acelera um pouco
        maxlen = (b - a + 0.5) * SR
        if len(sig) > maxlen:
            idx = np.linspace(0, len(sig) - 1, int(maxlen))
            sig = np.interp(idx, np.arange(len(sig)), sig)
        add(narr, a, sig * 0.9)
    mix_ = bed + narr
    mix_ = np.clip(mix_ / max(1.0, np.abs(mix_).max()) * 0.95, -1, 1)
    pcm = (mix_ * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ---------------- main ----------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    wav = os.path.join(here, "audio.wav")
    print("áudio..."); build_audio(wav)
    n = int(DUR * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=lanczos,noise=alls=8:allf=t", "-c:v", "libx264", "-preset", "medium",
           "-crf", "30", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(render_frame(i / FPS).tobytes())
        if i % 120 == 0: print(f"frame {i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    print("ok ->", OUT)

if __name__ == "__main__":
    main()
