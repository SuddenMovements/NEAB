from multiprocessing import Pool, Process
from client import AgarioClient
from noise import pnoise2
from random import random
from math import tau
from math import inf
from math import atan2
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


def move_smarter(index, step, screen_size, food, cells):
    action = {}

    best_food = None
    best_dist = inf
    for f in food:
        dist = (f["x"]) ** 2 + (f["y"]) ** 2
        if dist < best_dist:
            best_dist = dist
            best_food = f
    if best_food != None:
        action["r"] = 200
        action["theta"] = atan2(best_food["y"], best_food["x"])
    else:
        action["r"] = (pnoise2(index, step * 0.01) + 1) * 200
        action["theta"] = (pnoise2(index, step * 0.01) + 1) * tau
    action["r"] += pnoise2(index, step * 0.01) * 20
    action["theta"] += pnoise2(index, step * 0.01) * 0.5

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
        # action = move_perlin(index, step)
        action = move_smarter(index, step, screen_size, client.food, client.cells)
        client.take_action(action)
        # sleep(0.2)
        frame = client.render()
        mass = client.playerMass
        if step % 5 == 0:
            imwrite("./game_screenshots/" + str(index) + "/" + str(int(step)) + "_" + str(mass) + ".png", frame)
        step += 1


def count_images():
    image_count = 0
    for dir, subdir, files in os.walk("./game_screenshots"):
        image_count += len(files)
    print("got", image_count, "screenshots")
    sleep(5)
    count_images()


if __name__ == "__main__":
    if os.path.isdir("./game_screenshots"):
        rmtree("./game_screenshots")
    bot_count = 25
    for i in range(bot_count):
        os.makedirs("./game_screenshots/" + str(i))
    clients = [(i, 600, False) for i in range(bot_count)]
    for i in range(len(clients)):
        Process(target=screenshot_bot, args=clients[i]).start()
    Process(target=count_images).start()
    # AgarioClient(bot_count, 600, True, True, True)
