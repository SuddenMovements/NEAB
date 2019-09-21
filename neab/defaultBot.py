from noise import pnoise2
from math import inf, tau, sin, cos, ceil
import random

def move_perlin(index, step):
    action = {}
    mag = (pnoise2(index, step * 0.01) + 1) * 200
    theta = (pnoise2(index, step * 0.01) + 1) * tau
    action["x"] = mag * cos(theta)
    action["y"] = mag * sin(theta)

    action["fire"] = random.random() > 0.999
    action["split"] = random.random() > 0.999
    return action
