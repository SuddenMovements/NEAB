import socketio
import random
import time
import cv2
import numpy as np
import sys
from matplotlib.colors import hex2color
import math

socket = socketio.Client()

gameWidth = 0
gameHeight = 0
screenWidth = 600
screenHeight = 600
running = True

cv2.namedWindow("agario")
cv2.resizeWindow("agario", screenWidth, screenHeight)


def mouse_callback(event, x, y, flags, param):
    global target
    if event == cv2.EVENT_MOUSEMOVE:
        target["x"] = x - screenWidth / 2
        target["y"] = y - screenHeight / 2


cv2.setMouseCallback("agario", mouse_callback)


@socket.event
def connect():
    print("connection established")
    name = "player" + str(random.randint(10, 1000000))
    player = {"name": name, "id": name, "target": {}}
    socket.emit("gotit", player)


@socket.event
def playerJoin(name):
    print(name, "joined")


@socket.event
def gameSetup(dimensions):
    gameWidth = dimensions["gameWidth"]
    gameHeight = dimensions["gameHeight"]
    socket.emit("windowResized", {"screenWidth": screenWidth, "screenHeight": screenHeight})


@socket.event
def welcome(currentPlayer):
    print("welcome", currentPlayer)


def move(target):
    # target needs properties x and y
    socket.emit("0", target)


def fire():
    print("fire")
    socket.emit("1")


def split():
    print("split")
    socket.emit("2", False)


@socket.event
def virusSplit(splitCell):
    print("got virusSplit")
    socket.emit("2", splitCell)


cells = []
food = []
mass = []
viruses = []
ratio = 1
playerMass = 10
playerCoords = {"x": 0, "y": 0}


def ratio_from_mass(x):
    # this function is a manual approximation for the number of grid cells you can see
    # in the actual agario at various different masses
    # the data cen be seen inside sizes.txt
    """Gets the percentage scale of the whole screen relative to a mass x"""
    y = 1400 * (x + 150) ** -1 + 7.2
    return y / 15.95


def udpate_screen_size_from_mass():
    global ratio
    global playerMass
    ratio = ratio_from_mass(playerMass)
    ratio = screenWidth / 600 * ratio


@socket.event
def serverTellPlayerMove(visibleCells, visibleFood, visibleMass, visibleVirus, playerInfo):
    if False:
        print("visibleCells", visibleCells, len(visibleCells))
        print("visibleFood", visibleFood, len(visibleFood))
        print("visibleMass", visibleMass, len(visibleMass))
        print("visibleVirus", visibleVirus, len(visibleVirus))
        print("=" * 20)

    global playerMass
    global playerCoords
    global ratio
    if playerInfo["totalMass"] != playerMass:
        playerMass = playerInfo["totalMass"]
        udpate_screen_size_from_mass()
    playerCoords["x"] = playerInfo["x"]
    playerCoords["y"] = playerInfo["y"]

    for entity in visibleCells + visibleFood + visibleMass + visibleVirus:
        entity["x"] -= playerInfo["x"]
        entity["y"] -= playerInfo["y"]
        entity["x"] *= ratio
        entity["y"] *= ratio
        if "radius" in entity:
            entity["radius"] *= ratio

        if "cells" in entity:
            for subcell in entity["cells"]:
                subcell["x"] -= playerInfo["x"]
                subcell["y"] -= playerInfo["y"]
                subcell["x"] *= ratio
                subcell["y"] *= ratio
                subcell["radius"] *= ratio

    global cells, food, mass, viruses
    cells = visibleCells
    food = visibleFood
    mass = visibleMass
    viruses = visibleVirus


i = 0


def render():
    global screenWidth
    global ratio
    global playerCoords
    frame = np.full((screenHeight, screenWidth, 3), 255, np.uint8)

    default_grid = 37
    grid_col = (100, 100, 100)
    x = math.floor((playerCoords["x"] - screenWidth / ratio) / default_grid) * default_grid
    while x < playerCoords["x"] + screenWidth / ratio:
        x += default_grid
        frame = cv2.line(frame, (int((x - playerCoords["x"]) * ratio), 0), (int((x - playerCoords["x"]) * ratio), screenHeight), grid_col, thickness=1)

    y = math.floor((playerCoords["y"] - screenWidth / ratio) / default_grid) * default_grid
    while y < playerCoords["y"] + screenWidth / ratio:
        y += default_grid
        frame = cv2.line(frame, (0, int((y - playerCoords["y"]) * ratio)), (screenWidth, int((y - playerCoords["y"]) * ratio)), grid_col, thickness=1)

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    for entity in food + mass:
        x = int(entity["x"] + screenWidth / 2)
        y = int(entity["y"] + screenWidth / 2)
        r = int(entity["radius"])
        col = (entity["hue"], 255, 255)
        frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    for cell in cells:
        for subcell in cell["cells"]:
            x = int(subcell["x"] + screenWidth / 2)
            y = int(subcell["y"] + screenHeight / 2)
            r = int(subcell["radius"])
            stroke_col = (cell["hue"], 255, 150)
            stroke_weight = 7
            frame = cv2.circle(frame, (x, y), r + stroke_weight, stroke_col, cv2.FILLED)

            col = (cell["hue"], 255, 255)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    for v in viruses:
        x = int(v["x"] + screenWidth / 2)
        y = int(v["y"] + screenWidth / 2)
        r = int(v["radius"])
        col = hex2color(v["fill"])
        stroke_col = hex2color(v["stroke"])
        col = list(map(lambda x: int(x * 255), col))
        stroke_col = list(map(lambda x: int(x * 255), stroke_col))
        stroke_weight = int(v["strokeWidth"])
        spikes = 60
        frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)
        for i in range(spikes):
            cv2.ellipse(frame, (x, y), (int(r), int(r / 10)), i / spikes * 360, -3 / spikes * 360, 3 / spikes * 360, stroke_col, stroke_weight)

        # frame = cv2.circle(frame, (x, y), r, stroke_col, stroke_weight)
        # frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    cv2.imshow("agario", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        global running
        running = False
    if key == ord("w"):
        fire()
    if key == ord(" "):
        split()


i = 0
target = {"x": 0, "y": 0}

socket.connect("http://localhost:3000")
while running:
    move(target=target)
    i += 1
    render()
    # time.sleep(0.2)

socket.disconnect()
