import gym
from gym import error, spaces, utils
from gym.utils import seeding

from neab.client import AgarioClient
from neab.utils import safe_create_folder, safe_delete_folder

import warnings
from cv2 import imwrite

class AgarioEnv(gym.Env):
    """
    An agar.io client environment using OpenAI gym
    (Might be more useful if we use single env per
    agent for more performance)

    Args:
        num_agents (int): number of agents we want to spawn.
        screen_size (int): image width and height
    """

    metadata = {"render.modes": ["human", "rgb_array"]}
    reward_range = (-float("inf"), float("inf"))

    action_space = None
    observation_space = None

    def __init__(self, num_agents, screen_size, save_folder="render"):
        self.num_agents = num_agents
        self.screen_size = screen_size
        self.save_folder = save_folder

        self.clients = [
            AgarioClient(index, screen_size, False)
            for index in range(num_agents)
        ]
        self.global_step = 0
        for c in self.clients:
            c.start()

        safe_delete_folder(self.save_folder)

        super().__init__()

    def reset(self):
        # Disconnect and Reconnect

        obs = [c.render() for c in self.clients]
        return obs

    def close(self):
        for c in self.clients:
            c.stop()

    def step(self, actions):
        if len(actions) != self.num_agents:
            raise ValueError("The number of actions and the corresponding agent should have the same size")
        # obs, reward, done, info
        obs = []
        for a, c in zip(actions, self.clients):
            c.take_action(a)
            obs.append(c.render())

        self.global_step += 1
        return obs, None, False, {}

    def render(self, mode="rgb_array"):
        if mode == "human":
            warnings.warn("Human Spectator isn't implemented yet")
        elif mode == "rgb_array":
            for c in self.clients:
                root_folder = f"{self.save_folder}/agent_{c.index}"
                safe_create_folder(root_folder)
                frame = c.render()
                imwrite(f"{root_folder}/{self.global_step:03d}.png", frame * 255)
