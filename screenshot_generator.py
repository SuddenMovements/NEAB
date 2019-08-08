from multiprocessing import Pool, Process
from client import AgarioClient
from noise import pnoise2
from random import random
from math import tau
from time import sleep
import os
from shutil import rmtree
from cv2 import imwrite


def move_perlin(index, step):
    action = {}
    action["r"] = (pnoise2(index, step * 0.01) + 1) * 200
    action["theta"] = (pnoise2(index, step * 0.01) + 1) * tau
    action["fire"] = False
    action["split"] = False
    if random() > 0.999:
        action["fire"] = True
    if random() > 0.999:
        action["split"] = True

    return action


def screenshot_bot(index, screen_size, display_window):
    step = 0
    client = AgarioClient(index, screen_size, display_window, False)
    while client.alive:
        action = move_perlin(index, step)
        client.take_action(action)
        frame = client.render()
        mass = client.playerMass
        if step % 5 == 0:
            imwrite("./game_screenshots/" + str(index) + "/" + str(int(step)) + "_" + str(mass) + ".png", frame)
        step += 1


if __name__ == "__main__":
    if os.path.isdir("./game_screenshots"):
        rmtree("./game_screenshots")
    bot_count = 10
    for i in range(bot_count):
        os.makedirs("./game_screenshots/" + str(i))
    clients = [(i, 600, False) for i in range(bot_count)]
    for i in range(len(clients)):
        Process(target=screenshot_bot, args=clients[i]).start()
    AgarioClient(bot_count, 600, True, True, True)