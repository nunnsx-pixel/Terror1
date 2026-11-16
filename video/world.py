import numpy as np, time
from textures import *
from engine import World
from common import *

def build_world1():
    L = 17.0
    tube_z = [2.5, 6.5, 10.5, 14.5]
    ldoors = [(4.2, "broken", "C-04"), (9.0, "dark", "C-07"), (13.0, "plain", "C-09")]
    rdoors = [(2.8, "dark", "C-03"), (7.0, "plain", "C-06"), (11.5, "dark", "C-08")]
    left = Tex(make_wall(L, 3, doors=ldoors), 90)
    right = Tex(make_wall(L, 4, doors=rdoors), 90)
    prints = []
    z, k = 15.2, 0
    rng = np.random.default_rng(5)
    while z > 3.2:
        prints.append((z, 0.05 + (0.20 if k % 2 else -0.20) + rng.normal(0, 0.05), 180 + rng.normal(0, 8), "L" if k % 2 else "R"))
        z -= 0.55; k += 1
    floor = Tex(make_floor(L, 7, prints=prints), 90)
    ceil = Tex(make_ceiling(L, 8, fixtures=tube_z), 90)
    end = Tex(make_iron_door_wall(40, claws=True, padlock=True), 300)
    a, e = make_entrance(60)
    back = Tex(a, 150, emis=e)
    return World(1.3, 3.0, 0.0, L, left, right, floor, ceil, end, back, tube_z)

def build_world2():
    L = 24.0
    tube_z = [3.0, 8.0, 13.0, 18.0]
    ldoors = [(5.5, "dark", "C-21"), (11.0, "broken", "C-23"), (17.0, "dark", "C-25")]
    rdoors = [(4.0, "dark", "C-20"), (9.5, "plain", "C-22"), (15.0, "dark", "C-24")]
    left = Tex(make_wall(L, 13, doors=ldoors, mold=1.4, tone=(0.5, 0.53, 0.5)), 90)
    right = Tex(make_wall(L, 14, doors=rdoors, mold=1.4, tone=(0.5, 0.53, 0.5)), 90)
    floor = Tex(make_floor(L, 17), 90)
    ceil = Tex(make_ceiling(L, 18, fixtures=tube_z), 90)
    end = Tex(make_brick_wall(50), 300)
    back_closed = Tex(make_iron_door_wall(70, claws=False, padlock=False, state="closed"), 300)
    back_ajar = Tex(make_iron_door_wall(70, claws=False, padlock=False, state="ajar"), 300)
    w = World(1.3, 3.0, 0.0, L, left, right, floor, ceil, end, back_ajar, tube_z, tube_color=(0.75, 0.85, 1.0))
    w.back_closed, w.back_ajar = back_closed, back_ajar
    return w
