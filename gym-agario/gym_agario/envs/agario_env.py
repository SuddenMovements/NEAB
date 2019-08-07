import gym
from gym import error, spaces, utils
from gym.utils import seeding


class AgarioEnv(gym.Env):
    """An agar.io environment for OpenAI gym"""

    metadata = {"render.modes": ["human"]}

    def __init__(self, num_blobs, screen_size):
        self.num_blobs = num_blobs
        self.screen_size = screen_size
        self.blobs = []

    def step(self, actions):
        assert len(actions) == len(self.blobs)
        for i in range(len(actions)):
            if not self.blobs[i].isAlive:
                continue
            self.blobs[i].take_action(actions[i])

    def reset(self):
        for blob in self.blobs:
            blob.disconnect()
            del blob
        self.blobs = []

        # initialise num_blobs clients to connect to the server
        for i in range(num_blobs):
            # TODO replace this with client object class
            new_client = "blob_replace_me"
            blobs.append(new_client)

    def render(self, mode="human"):
        for blob in self.blobs:
            if not blob.alive:
                continue
            # render the last frame we saw
            blob.render()

        # we can use the 'spectator' mode built into the server to use with the render function
        # TODO add spectator render function so we can observe the blobs learning

    def close(self):
        for blob in self.blobs:
            blob.disconnect()
            del blob

