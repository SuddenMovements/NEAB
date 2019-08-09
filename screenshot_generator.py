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
import numpy as np

frame_save_count = 100
frame_save_step_interval = 5


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
    frames = []
    save_iteration = 0
    while client.alive:
        step += 1
        action = move_smarter(index, step, screen_size, client.food, client.cells)
        client.take_action(action)
        if step % frame_save_step_interval == 0:
            frame = client.render()
            mass = client.playerMass
            frames.append((frame, mass))
            # imwrite("./game_screenshots/" + str(index) + "/" + str(int(step)) + "_" + str(int(mass)) + ".png", frame)
            if step % (frame_save_step_interval * frame_save_count) == 0:
                np.savez_compressed("./game_screenshots/" + str(index) + "_" + str(save_iteration), *frames)
                del frames
                frames = []
                save_iteration += 1
        else:
            sleep(0.2)


prev_image_count = 0


def count_images():
    image_count = 0
    global prev_image_count
    for dir, subdir, files in os.walk("./game_screenshots"):
        image_count += len(files) * frame_save_count
    if image_count == prev_image_count:
        sleep(5)
        count_images()
    else:
        print("got", image_count, "screenshots")
        prev_image_count = image_count
        count_images()


if __name__ == "__main__":
    if os.path.isdir("./game_screenshots"):
        rmtree("./game_screenshots")
    os.mkdir("./game_screenshots")
    bot_count = 25
    # for i in range(bot_count):
    #     os.makedirs("./game_screenshots/" + str(i))
    clients = [(i, 600, False) for i in range(bot_count)]
    for i in range(len(clients)):
        Process(target=screenshot_bot, args=clients[i]).start()
    Process(target=count_images).start()
    # AgarioClient(bot_count, 600, True, True, True)
