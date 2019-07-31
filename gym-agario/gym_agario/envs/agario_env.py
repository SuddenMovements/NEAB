import gym
from gym import error, spaces, utils
from gym.utils import seeding


class AgarioEnv(gym.Env):
    """An agar.io environment for OpenAI gym"""

    metadata = {"render.modes": ["human"]}

    def __init__(self, game_size, screen_size, blobs):
        ...

    def step(self):
        ...

    def reset(self):
        ...

    def render(self, mode="human"):
        ...

    def close(self):
        ...

