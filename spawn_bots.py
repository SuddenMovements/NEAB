from client import AgarioClient
from math import inf, tau, sin, cos
from noise import pnoise2
from random import random
from time import sleep
from cv2 import imwrite
from os import path, makedirs
from shutil import rmtree
from screenshot_generator import move_smarter


def bot(index, screen_size):
    client = AgarioClient(index, screen_size, False)

    def on_game_update(step):
        # action = move_perlin(index, step)
        action = move_smarter(index, screen_size, step, client.playerCoords, client.food, client.cells)
        client.take_action(action)
        step += 1

    client.register_callback("gameUpdate", on_game_update)
    client.start()


def spawn(count):
    for i in range(count):
        bot(i, 600)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("bot_count")
    args = parser.parse_args()
    spawn(int(args.bot_count))
