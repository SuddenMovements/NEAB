from client import AgarioClient
from math import inf, tau, sin, cos, ceil
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


def screenshot_bot(index, screen_size, record=True, target_frame_count=0):
    client = AgarioClient(index, screen_size, False)

    def on_game_update(step):
        if step == target_frame_count:
            print("on target step {}, stopping client".format(step))
            client.stop()
            return
        if record:
            frame = client.render()
            imwrite("./game_screenshots/" + str(index) + "/" + str(step) + ".png", frame)
            del frame
            if step % 100 == 0:
                print(index, "on step", step)
        # action = move_perlin(index, step)
        action = move_smarter(index, screen_size, step, client.playerCoords, client.food, client.cells)
        client.take_action(action)

    client.register_callback("gameUpdate", on_game_update)
    client.start()


def spawn(total_bot_count, recording_bot_count, total_frames):
    if path.isdir("./game_screenshots"):
        rmtree("./game_screenshots")
    i = 0
    while i < recording_bot_count:
        makedirs("./game_screenshots/" + str(i))
        screenshot_bot(i, 512, record=True, target_frame_count=ceil(total_frames / recording_bot_count) + 1)
        i += 1
    while i < total_bot_count:
        screenshot_bot(i, 512, record=False, target_frame_count=ceil(total_frames / recording_bot_count) + 1)
        i += 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("total_bot_count")
    parser.add_argument("recording_bot_count")
    parser.add_argument("total_frames")
    args = parser.parse_args()
    assert int(args.total_bot_count) >= int(args.recording_bot_count)
    spawn(int(args.total_bot_count), int(args.recording_bot_count), int(args.total_frames))
