import numpy as np, math
from PIL import Image, ImageFilter
from common import *
import hud as H_
from lines import LINES
import cues

_caps = {}
def captions(part):
    if part in _caps: return _caps[part]
    lst = cues.PART1 if part == 1 else cues.PART2
    out = []
    for (k, st, spk) in lst:
        d = cues.dur(k)
        txt = LINES[k][1]
        for (a, b, c) in H_.chunk_caption(txt, st, d):
            out.append((a, b + 0.05, spk, c))
    _caps[part] = out
    return out

def active_caption(part, t):
    for (a, b, spk, c) in captions(part):
        if a - 0.02 <= t <= b:
            fade = min(1.0, (t - a + 0.02) / 0.08, (b - t) / 0.08 + 0.2)
            return spk, c, max(0.0, min(1.0, fade))
    return None

def compose(part, mod, t, fidx):
    scene, extra = mod.render(t, fidx)
    img = Image.fromarray((scene * 255).astype(np.uint8))
    if extra.get("blur", 0) > 0.1:
        img = img.filter(ImageFilter.GaussianBlur(extra["blur"]))
    img = img.resize((OW, OH), Image.BICUBIC).convert("RGBA")
    st = mod.hud(t)
    img.alpha_composite(H_.draw_hud(st, t))
    if part == 1 and st["live"] == "live":
        img.alpha_composite(H_.draw_chat(cues.CHAT1, t))
    ac = active_caption(part, t)
    if ac and not extra.get("no_caption"):
        img.alpha_composite(H_.draw_caption(ac[0], ac[1], ac[2]))
    if part == 1 and t > 55.0:
        img.alpha_composite(H_.draw_endcard(min(1.0, (t - 55.0) / 0.35)))
    if extra.get("black", 0) > 0:
        img = Image.blend(img, Image.new("RGBA", img.size, (0, 0, 0, 255)), min(1.0, extra["black"]))
    return img.convert("RGB")
