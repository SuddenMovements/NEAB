from neab.agarioEnv import AgarioEnv
from neab.utils import safe_create_folder, safe_delete_folder
from neab.defaultBot import move_perlin

import numpy as np
import matplotlib.pyplot as plt

if __name__ == '__main__':
    safe_create_folder('game_screenshots')
    safe_delete_folder('render')
    env = AgarioEnv(3, 512)
    all_obs = env.reset()

    for i in range(100):
        actions = [move_perlin(a, i) for a in range(3)]
        print(actions)
        obs, _, _, _ = env.step(actions)
        env.render(mode="rgb_array")

    env.close()
