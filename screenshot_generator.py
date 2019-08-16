from client import AgarioClient
from math import inf, tau, sin, cos
from noise import pnoise2
from random import random
from time import sleep
from cv2 import imwrite
from os import path, makedirs
from shutil import rmtree


def move_smarter(index, screen_size, step, playerCoords, food, cells):
    action = {}

    best_food = None
    best_dist = inf
    for f_id in food:
        f = food[f_id]
        dist = (f["x"] - playerCoords["x"]) ** 2 + (f["y"] - playerCoords["y"]) ** 2
        if dist < best_dist:
            best_dist = dist
            best_food = f
    if best_food != None:
        action["x"] = best_food["x"] - playerCoords["x"]
        action["y"] = best_food["y"] - playerCoords["y"]
    else:
        action["x"] = (pnoise2(index, step * 0.01)) * 200
        action["y"] = (pnoise2(index, step * 0.01)) * 200
    # action["x"] += pnoise2(index, step * 0.01) * 10
    # action["y"] += pnoise2(index, -step * 0.01) * 10

    action["x"] = max(min(action["x"], screen_size / 2), -screen_size / 2)
    action["y"] = max(min(action["y"], screen_size / 2), -screen_size / 2)

    action["fire"] = random() > 0.999
    action["split"] = random() > 0.999

    return action


def move_perlin(index, step):
    action = {}
    mag = (pnoise2(index, step * 0.01) + 1) * 200
    theta = (pnoise2(index, step * 0.01) + 1) * tau
    # print(mag, theta)
    action["x"] = mag * cos(theta)
    action["y"] = mag * sin(theta)

    action["fire"] = False
    action["split"] = False
    if random() > 0.999:
        action["fire"] = True
    if random() > 0.999:
        action["split"] = True

    return action


def screenshot_bot(index, screen_size):
    client = AgarioClient(index, screen_size, False)

    def on_game_update(step):
        frame = client.render()
        imwrite("./game_screenshots/" + str(index) + "/" + str(step) + ".png", frame)
        del frame
        # action = move_perlin(index, step)
        action = move_smarter(index, screen_size, step, client.playerCoords, client.food, client.cells)
        client.take_action(action)
        step += 1
        if step % 100 == 0:
            print(index, "on step", step)

    client.register_callback("gameUpdate", on_game_update)
    client.start()


def spawn(count):
    if path.isdir("./game_screenshots"):
        rmtree("./game_screenshots")
    for i in range(count):
        makedirs("./game_screenshots/" + str(i))
        screenshot_bot(i, 600)


if __name__ == "__main__":
    spawn(5)
