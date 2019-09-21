from math import inf, tau, sin, cos, ceil
from noise import pnoise2
from random import random
from time import sleep
from cv2 import imwrite
from shutil import rmtree
import time
import os

from neab.client import AgarioClient
from neab.defaultBot import move_perlin


"""Screenshot generator script used to collect datasets for VAE training.
To get started, run the server.js file inside server/ and then run this script."""


def move_smarter(index, step, client):
    """
    Bot is moved using perlin noise.
    """
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


def screenshot_bot(index, screen_size, record=True, target_frame_count=0):
    client = AgarioClient(index, screen_size, False)

    def on_game_update(step):
        if step == target_frame_count:
            print("on target step {}, stopping client".format(step))
            client.stop()
            return
        if record:
            frame = client.render()
            imwrite(f"./game_screenshots/{index}/{step}.png", frame)
            del frame
            if step % 100 == 0:
                print(index, "on step", step)
        # action = move_perlin(index, step)
        action = move_smarter(index, step, client)
        client.take_action(action)

    client.register_callback("gameUpdate", on_game_update)
    client.start()


def spawn(total_bot_count, recording_bot_count, total_frames, frame_size):
    print("generating a target {} frames with {} recording bots on a game with {} bots".format(total_frames, recording_bot_count, total_bot_count))
    print("will run until step {}".format(ceil(total_frames / recording_bot_count)))

    if os.path.exists("game_screenshots"):
        rmtree("game_screenshots")

    os.mkdir("game_screenshots")
    i = 0
    while i < recording_bot_count:
        print(i)
        os.mkdir(f"game_screenshots/{i}/")
        screenshot_bot(i, frame_size, record=True, target_frame_count=ceil(total_frames / recording_bot_count) + 1)
        i += 1
        time.sleep(0.1)

    # Continue Making not record bot
    while i < total_bot_count:
        screenshot_bot(i, frame_size, record=False, target_frame_count=ceil(total_frames / recording_bot_count) + 1)
        i += 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generating Screenshot for training vision model")
    parser.add_argument("--total-bot-count", type=int, default=5, help="number of bots in the environment")
    parser.add_argument("--recording-bot-count", type=int, default=3, help="number of bot observations we want to record")
    parser.add_argument("--total-frames", type=int, default=1000, help="number of frames we would like to observe (per bot)")
    parser.add_argument("--frame-size", type=int, default=512, help="size of recorded frame")
    args = parser.parse_args()

    if args.total_bot_count < args.recording_bot_count:
        raise ValueError("The number of recording bot has to be less than the total number of bots")

    spawn(args.total_bot_count, args.recording_bot_count, args.total_frames, args.frame_size)
