import math
from PIL import Image, ImageDraw, ImageFont
from common import OW, OH

FB = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FX = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FM = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
_f = {}


def font(path, size):
    k = (path, size)
    if k not in _f:
        _f[k] = ImageFont.truetype(path, size)
    return _f[k]


RED = (235, 40, 40, 255)


def tsize(d, text, f):
    b = d.textbbox((0, 0), text, font=f)
    return b[2] - b[0], b[3] - b[1]


def text_shadow(d, xy, text, f, fill, shadow=(0, 0, 0, 200), off=3, anchor="la"):
    d.text((xy[0] + off, xy[1] + off), text, font=f, fill=shadow, anchor=anchor)
    d.text(xy, text, font=f, fill=fill, anchor=anchor)


def battery(d, x, y, pct, red=False, blink=False, scale=1.0):
    w, h = int(78 * scale), int(36 * scale)
    col = (235, 50, 45, 255) if red else (245, 245, 245, 255)
    if red and blink:
        col = (120, 20, 20, 255)
    d.rounded_rectangle([x, y, x + w, y + h], radius=int(8 * scale), outline=col, width=4)
    d.rectangle([x + w + 3, y + h * .3, x + w + 9, y + h * .7], fill=col)
    fw = max(4, int((w - 10) * pct / 100))
    d.rounded_rectangle([x + 5, y + 5, x + 5 + fw, y + h - 5], radius=int(4 * scale), fill=col)


def draw_hud(st, t):
    """st: dict(clock, battery, bat_red, live ('live'|'off'), viewers, rec_blink)"""
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # cantos do visor
    c = (255, 255, 255, 150)
    m, L = 46, 70
    for (x, y, sx, sy) in ((m, 150, 1, 1), (OW - m, 150, -1, 1), (m, OH - 420, 1, -1), (OW - m, OH - 420, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=c, width=4)
        d.line([(x, y), (x, y + sy * L)], fill=c, width=4)
    # ---- topo direito: hora + REC
    f = font(FB, 44)
    blink = (int(t * 1.0) % 2 == 0)
    rx = OW - 52
    text_shadow(d, (rx, 168), "REC", font(FX, 44), (255, 255, 255, 255), anchor="ra")
    bw = tsize(d, "REC", font(FX, 44))[0]
    if blink or st.get("rec_solid"):
        d.ellipse([rx - bw - 52, 170, rx - bw - 18, 204], fill=RED)
    clock = st["clock"]
    text_shadow(d, (rx - bw - 68, 168), clock, f, (255, 255, 255, 255), anchor="ra")
    # bateria + %
    by = 232
    pct = st["battery"]
    red = st.get("bat_red", False)
    bl = st.get("bat_blink", False)
    battery(d, rx - 78 - 10, by, pct, red, bl)
    pc = f"{int(pct)}%"
    text_shadow(d, (rx - 78 - 24, by - 2), pc, font(FB, 38), RED if red else (255, 255, 255, 255), anchor="ra")
    # ---- topo esquerdo: badge AO VIVO / SEM CONEXAO
    if st["live"] == "live":
        d.rounded_rectangle([52, 160, 52 + 176, 160 + 54], radius=10, fill=(235, 30, 60, 255))
        d.text((52 + 88, 187), "AO VIVO", font=font(FX, 28), fill=(255, 255, 255, 255), anchor="mm")
        # olhinho + espectadores
        ex, ey = 52 + 176 + 22, 187
        d.ellipse([ex, ey - 11, ex + 34, ey + 11], outline=(255, 255, 255, 255), width=3)
        d.ellipse([ex + 12, ey - 5, ex + 22, ey + 5], fill=(255, 255, 255, 255))
        text_shadow(d, (ex + 46, ey - 18), st.get("viewers", "12,4 mil"), font(FB, 34), (255, 255, 255, 255))
    else:
        d.rounded_rectangle([52, 160, 52 + 286, 160 + 54], radius=10, fill=(60, 60, 64, 220))
        d.text((52 + 143, 187), "SEM CONEXÃO", font=font(FX, 28), fill=(255, 150, 150, 255), anchor="mm")
        tri = [(52 + 18, 200), (52 + 36, 172), (52 + 54, 200)]
    return im


CHAT_COLORS = [(255, 170, 120), (150, 220, 255), (190, 255, 160), (255, 150, 200), (255, 230, 120), (190, 160, 255)]


def draw_chat(msgs, t, x=44, ybottom=1330):
    """msgs: lista (t0, user, text). mostra as ultimas 5 visiveis"""
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    vis = [(i, m) for i, m in enumerate(msgs) if m[0] <= t]
    vis = vis[-5:]
    y = ybottom
    f1, f2 = font(FB, 30), font(FM, 30)
    for i, (t0, user, text) in reversed(vis):
        age = t - t0
        a = int(255 * max(0.0, min(1.0, (1 - max(0, (age - 7.0) / 3.0)) * min(1.0, age / 0.25))))
        if a <= 0:
            continue
        col = CHAT_COLORS[i % len(CHAT_COLORS)]
        wu = tsize(d, user + " ", f1)[0]
        wt = tsize(d, text, f2)[0]
        d.rounded_rectangle([x, y - 46, x + wu + wt + 36, y + 2], radius=22, fill=(0, 0, 0, int(a * 0.45)))
        d.text((x + 18, y - 42), user, font=f1, fill=col + (a,))
        d.text((x + 18 + wu, y - 42), text, font=f2, fill=(255, 255, 255, a))
        y -= 62
    return im


SPK = {"LUCAS": (255, 255, 255), "CLARA": (150, 205, 255), "MARCOS": (255, 175, 140), "???": (255, 60, 60), "ELES": (255, 60, 60)}


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if tsize(d, trial, f)[0] <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_caption(speaker, text, a=1.0, ybottom=1500, size=60):
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(FX, size)
    lines = wrap(d, text, f, 900)
    lh = int(size * 1.18)
    y = ybottom - lh * len(lines)
    al = int(255 * a)
    col = SPK.get(speaker, (255, 255, 255))
    if speaker:
        fl = font(FB, 30)
        tw = tsize(d, speaker, fl)[0]
        d.rounded_rectangle([OW / 2 - tw / 2 - 18, y - 52, OW / 2 + tw / 2 + 18, y - 8], radius=12, fill=col + (int(220 * a),))
        d.text((OW / 2, y - 30), speaker, font=fl, fill=(10, 10, 12, al), anchor="mm")
    for i, ln in enumerate(lines):
        d.text((OW / 2, y + i * lh), ln, font=f, fill=(255, 255, 255, al), anchor="ma", stroke_width=7, stroke_fill=(0, 0, 0, al))
    return im


def draw_endcard(a=1.0, text="CONTINUA NA PARTE 2", y=1440):
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(FX, 62)
    tw = tsize(d, text, f)[0]
    total = tw + 90
    x0 = OW / 2 - total / 2
    d.rounded_rectangle([x0 - 34, y - 40, x0 + total + 34, y + 62 + 36], radius=24, fill=(0, 0, 0, int(190 * a)))
    d.text((x0, y), text, font=f, fill=(255, 255, 255, int(255 * a)), stroke_width=3, stroke_fill=(0, 0, 0, int(255 * a)))
    px = x0 + tw + 22                                     # triangulo de play
    d.polygon([(px, y + 4), (px, y + 62), (px + 52, y + 33)], fill=(235, 40, 40, int(255 * a)))
    return im


def chunk_caption(text, start, dur, max_chars=34):
    """quebra a fala em blocos curtos (estilo TikTok) com tempo proporcional ao no de caracteres"""
    words = text.split()
    chunks, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) > max_chars and cur:
            chunks.append(cur)
            cur = w
        else:
            cur = trial
        if cur.endswith(("...", "?", "!", ".")) and len(cur) > 16:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    tot = sum(len(c) + 3 for c in chunks)
    out, t0 = [], start
    for c in chunks:
        dd = dur * (len(c) + 3) / tot
        out.append((t0, t0 + dd, c))
        t0 += dd
    return out
