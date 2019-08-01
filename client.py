import socketio
import random
import time
import cv2
import numpy as np
import sys
from matplotlib.colors import hex2color

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
    if event == cv2.EVENT_LBUTTONDOWN:
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


@socket.event
def serverTellPlayerMove(visibleCells, visibleFood, visibleMass, visibleVirus, playerCoords):
    if False:
        print("visibleCells", visibleCells, len(visibleCells))
        print("visibleFood", visibleFood, len(visibleFood))
        print("visibleMass", visibleMass, len(visibleMass))
        print("visibleVirus", visibleVirus, len(visibleVirus))
        print("=" * 20)
    for cell in visibleCells:
        cell["x"] -= playerCoords["x"]
        cell["y"] -= playerCoords["y"]
        for subcell in cell["cells"]:
            subcell["x"] -= playerCoords["x"]
            subcell["y"] -= playerCoords["y"]

    for f in visibleFood:
        f["x"] -= playerCoords["x"]
        f["y"] -= playerCoords["y"]

    for m in visibleMass:
        m["x"] -= playerCoords["x"]
        m["y"] -= playerCoords["y"]

    for virus in visibleVirus:
        virus["x"] -= playerCoords["x"]
        virus["y"] -= playerCoords["y"]
    global cells, food, mass, viruses
    cells = visibleCells
    food = visibleFood
    mass = visibleMass
    viruses = visibleVirus


i = 0


def render():
    frame = np.full((screenHeight, screenWidth, 3), 255, np.uint8)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    for cell in cells:
        for subcell in cell["cells"]:
            x = int(subcell["x"] + screenWidth / 2)
            y = int(subcell["y"] + screenHeight / 2)
            r = int(subcell["radius"])
            col = (cell["hue"], 255, 255)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    for f in food:
        x = int(f["x"] + screenWidth / 2)
        y = int(f["y"] + screenWidth / 2)
        r = int(f["radius"])
        col = (f["hue"], 255, 255)
        frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    for m in mass:
        x = int(m["x"] + screenWidth / 2)
        y = int(m["y"] + screenWidth / 2)
        r = int(m["radius"])
        col = (m["hue"], 255, 255)
        frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

    frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

    for v in viruses:
        x = int(v["x"] + screenWidth / 2)
        y = int(v["y"] + screenWidth / 2)
        r = int(v["radius"])
        col = hex2color(v["fill"])
        col = list(map(lambda x: int(x * 255), col))
        stroke = v["stroke"]
        frame = cv2.rectangle(frame, (x - r, y - r), (x + r, y + r), col, cv2.FILLED)

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
