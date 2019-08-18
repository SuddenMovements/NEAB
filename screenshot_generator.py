from client import AgarioClient
from math import inf, tau, sin, cos, ceil
from noise import pnoise2
from random import random
from time import sleep
from cv2 import imwrite
from os import path, makedirs
from shutil import rmtree


def move_smarter(index, step, client):
    action = {"x": 0, "y": 0, "fire": False, "split": False}

    best_food = None
    best_food_dist = inf
    for f_id in client.food:
        f = client.food[f_id]
        dist = (f["x"] - client.playerCoords["x"]) ** 2 + (f["y"] - client.playerCoords["y"]) ** 2
        if dist < best_food_dist:
            best_food_dist = dist
            best_food = f

    best_smaller_cell = None
    best_cell_dist = inf
    for c in client.cells:
        if c["mass"] < client.playerMass and c["playerID"] != client.playerID:
            dist = (c["x"] - client.playerCoords["x"]) ** 2 + (c["y"] - client.playerCoords["y"]) ** 2
            if dist < best_cell_dist:
                best_cell_dist = dist
                best_smaller_cell = c

    if best_food != None and best_smaller_cell != None:
        if best_food_dist * 10 < best_cell_dist:
            action["x"] = best_food["x"] - client.playerCoords["x"]
            action["y"] = best_food["y"] - client.playerCoords["y"]
        else:
            action["x"] = best_smaller_cell["x"] - client.playerCoords["x"]
            action["y"] = best_smaller_cell["y"] - client.playerCoords["y"]
    else:
        if best_food != None:
            action["x"] = best_food["x"] - client.playerCoords["x"]
            action["y"] = best_food["y"] - client.playerCoords["y"]
        elif best_smaller_cell != None:
            action["x"] = best_smaller_cell["x"] - client.playerCoords["x"]
            action["y"] = best_smaller_cell["y"] - client.playerCoords["y"]

    action["x"] *= 2
    action["y"] *= 2

    action["x"] += pnoise2(index * 10, step * 0.01) * 4 * client.playerMass
    action["y"] += pnoise2(index * 10, -step * 0.01) * 4 * client.playerMass

    action["fire"] = random() > 0.95
    action["split"] = random() > 0.95

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
        action = move_smarter(index, step, client)
        client.take_action(action)

    client.register_callback("gameUpdate", on_game_update)
    client.start()


def spawn(total_bot_count, recording_bot_count, total_frames):
    print("generating a target {} frames with {} recording bots".format(total_frames, recording_bot_count))
    print("will run until step {}".format(ceil(total_frames / recording_bot_count)))
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
