import subprocess, functools
from lines import LINES


@functools.lru_cache(None)
def dur(k):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"tts/{k}.wav"]).decode())


# (id, inicio_s, personagem)
PART1 = [
    ("p1_whisper", 3.35, "???"),
    ("p1_lucas1", 4.45, "LUCAS"),
    ("p1_clara1", 9.60, "CLARA"),
    ("p1_marcos1", 20.70, "MARCOS"),
    ("p1_lucas2", 27.00, "LUCAS"),
    ("p1_marcos2", 28.00, "MARCOS"),
    ("p1_lucas3", 35.40, "LUCAS"),
    ("p1_marcos3", 43.80, "MARCOS"),
]
PART2 = [
    ("p2_lucas1", 0.60, "LUCAS"),
    ("p2_clara1", 8.40, "CLARA"),
    ("p2_lucas2", 16.20, "LUCAS"),
    ("p2_marcos1", 28.60, "MARCOS"),
    ("p2_lucas3", 44.30, "LUCAS"),
    ("p2_clara2", 47.00, "CLARA"),
    ("p2_final", 53.70, "ELES"),
]

CHAT1 = [
    (0.4, "dani_k", "vai la lucas"),
    (1.6, "rafa.dev", "esse corredor ta mto escuro"),
    (3.5, "lele", "AAAAA O QUE FOI ISSO"),
    (4.3, "gabs", "o armario mexeu SOZINHO"),
    (6.0, "m4theus", "kkkk ta fake"),
    (8.4, "bia_sz", "SAI DAI AGORA"),
    (13.5, "vinicius", "o bloco c é real gente"),
    (19.0, "tata", "clara tem razao vamo embora"),
    (23.5, "ana.p", "olha o chao!!"),
    (28.0, "juju", "pegadas?? fresquinhas??"),
    (33.0, "thi", "n abre essa porta pfv"),
    (39.5, "leo_", "o cadeado foi arrombado por DENTRO"),
    (44.5, "carol", "sangue???"),
    (48.5, "dan", "lucas SAI DE LA"),
]


def viewers1(t):
    v = 3200 + 9200 * min(1, t / 50.0) ** 1.5
    return f"{v / 1000:.1f} mil".replace(".", ",")
