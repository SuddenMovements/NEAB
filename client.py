import socketio
import random
import time
import cv2
import numpy as np
import sys
from matplotlib.colors import hex2color
import math
import noise


class AgarioClient:
    def __init__(self, index, screen_size=600, spectator=False):
        self.socket = socketio.Client()
        self.screenWidth = screen_size
        self.screenHeight = screen_size
        self.alive = True
        self.index = str(index)
        self.spectator = spectator
        self.target = {"x": 0, "y": 0}

        # variables needed for rendering
        self.cells = []
        self.food = {}
        self.masses = {}
        self.viruses = {}
        self.ratio = 1
        self.playerMass = 10
        self.playerCoords = {"x": 0, "y": 0}

        self.virusFill = list(map(lambda x: int(x * 255), hex2color("#33ff33")))
        self.virusStroke = list(map(lambda x: int(x * 255), hex2color("#19D119")))
        self.virusStrokeWeight = 4

        self.callbacks = {}

        # self.start()

    def start(self):
        self.register_socketio_callbacks()
        self.socket.connect("http://localhost:3000")
        self.frame_number = 0

        if "start" in self.callbacks:
            self.callbacks["start"]()

    def stop(self):
        self.alive = False
        self.socket.disconnect()
        if "stop" in self.callbacks:
            self.callbacks["stop"]()

    def register_socketio_callbacks(self):
        @self.socket.event
        def handshake():
            playerInfo = {}
            if self.spectator:
                playerInfo["type"] = "spectator"
            else:
                playerInfo["type"] = "player"
            self.socket.emit("handshake", playerInfo)
            if "handshake" in self.callbacks:
                self.callbacks["handshake"]()

        @self.socket.event
        def playerInfo(info):
            self.playerCoords = {"x": info["x"], "y": info["y"]}
            self.playerMass = info["mass"]
            self.update_screen_size_from_mass()
            if "playerInfo" in self.callbacks:
                self.callbacks["playerInfo"]()

        @self.socket.event
        def gameSetup(mapObject):
            print(self.index, "got gamesetup")
            self.cells = mapObject["cells"]
            for f in mapObject["food"]:
                self.food[f["id"]] = f
            for m in mapObject["masses"]:
                self.masses[m["id"]] = m
            for v in mapObject["viruses"]:
                self.viruses[v["id"]] = v
            if "gameSetup" in self.callbacks:
                self.callbacks["gameSetup"]()
            self.move(self.target)  # to give server a move to begin gameUpdate loop

        @self.socket.event
        def gameUpdate(info):
            self.frame_number += 1
            self.playerCoords = info["playerCoords"]
            self.playerMass = info["playerMass"]
            self.update_screen_size_from_mass()
            self.cells = info["cells"]

            for f in info["addFood"].values():
                self.food[f["id"]] = f
            for f in info["deleteFood"]:
                # this check isnt a result of bad gamestate syncing
                # but when clients join an already running server, the server may send info about food pellets that have been eaten
                # before the client even had the food saved clientside
                if f in self.food:
                    del self.food[f]

            for m in info["updateMass"].values():
                self.masses[m["id"]] = m
            for m in info["deleteMass"]:
                if m in self.masses:
                    del self.masses[m]

            for v in info["updateVirus"].values():
                self.viruses[v["id"]] = v
            for v in info["deleteVirus"]:
                if v in self.viruses:
                    del self.viruses[v]

            if "gameUpdate" in self.callbacks:
                self.callbacks["gameUpdate"](self.frame_number)

        @self.socket.event
        def dead():
            print(self.index, "died")
            if "dead" in self.callbacks:
                self.callbacks["dead"]()
            self.socket.emit("respawn")
            # self.stop()

    def move(self, target):
        self.target = target
        self.socket.emit("move", self.target)
        if "move" in self.callbacks:
            self.callbacks["move"]()

    def fire(self):
        self.socket.emit("fire")
        if "fire" in self.callbacks:
            self.callbacks["fire"]()

    def split(self):
        self.socket.emit("split")
        if "split" in self.callbacks:
            self.callbacks["split"]()

    def ratio_from_mass(self, x):
        # this function is a manual approximation for the number of grid cells you can see
        # in the actual agario at various different masses
        # the data cen be seen inside sizes.txt
        """Gets the percentage scale of the whole screen relative to a mass x"""
        y = 1400 * (x + 150) ** -1 + 7.2
        return y / 15.95

    def update_screen_size_from_mass(self):
        if self.spectator:
            self.ratio = 1 / 10
            return
        self.ratio = self.ratio_from_mass(self.playerMass)
        self.ratio = self.screenWidth / 600 * self.ratio

    def render(self):
        def draw_grid(frame):
            default_grid = 37
            grid_col = (100, 100, 100)
            x = math.floor((self.playerCoords["x"] - self.screenWidth / self.ratio) / default_grid) * default_grid
            while x < self.playerCoords["x"] + self.screenWidth / self.ratio:
                x += default_grid
                frame = cv2.line(frame, (int((x - self.playerCoords["x"]) * self.ratio), 0), (int((x - self.playerCoords["x"]) * self.ratio), self.screenHeight), grid_col, thickness=1)

            y = math.floor((self.playerCoords["y"] - self.screenWidth / self.ratio) / default_grid) * default_grid
            while y < self.playerCoords["y"] + self.screenWidth / self.ratio:
                y += default_grid
                frame = cv2.line(frame, (0, int((y - self.playerCoords["y"]) * self.ratio)), (self.screenWidth, int((y - self.playerCoords["y"]) * self.ratio)), grid_col, thickness=1)
            return frame

        frame = np.full((self.screenHeight, self.screenWidth, 3), 255, np.uint8)
        # frame = draw_grid(frame)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for entity in list(self.food.values()) + list(self.masses.values()):
            x = round((entity["x"] - self.playerCoords["x"]) * self.ratio + self.screenWidth / 2)
            y = round((entity["y"] - self.playerCoords["y"]) * self.ratio + self.screenHeight / 2)
            r = round((entity["r"]) * self.ratio)
            if x + r < 0 and x - r > self.screenWidth and y + r < 0 and y - r > self.screenHeight:
                continue
            col = (entity["hue"], 255, 255)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)
            # cv2.putText(frame, entity["id"], (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255)
            # cv2.putText(frame, (str(x) + "," + str(y)), (x, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255)

        for cell in self.cells:
            x = round((cell["x"] - self.playerCoords["x"]) * self.ratio + self.screenWidth / 2)
            y = round((cell["y"] - self.playerCoords["y"]) * self.ratio + self.screenHeight / 2)
            r = round((cell["r"]) * self.ratio)
            if x + r < 0 and x - r > self.screenWidth and y + r < 0 and y - r > self.screenHeight:
                continue
            stroke_col = (cell["hue"], 255, 150)
            stroke_weight = 7
            frame = cv2.circle(frame, (x, y), r + stroke_weight, stroke_col, cv2.FILLED)

            col = (cell["hue"], 255, 255)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

        for virus in list(self.viruses.values()):
            x = round((virus["x"] - self.playerCoords["x"]) * self.ratio + self.screenWidth / 2)
            y = round((virus["y"] - self.playerCoords["y"]) * self.ratio + self.screenHeight / 2)
            r = round((virus["r"]) * self.ratio)
            if x + r < 0 and x - r > self.screenWidth and y + r < 0 and y - r > self.screenHeight:
                continue
            spikes = round(virus["mass"] / 2)
            frame = cv2.circle(frame, (x, y), r, self.virusFill, cv2.FILLED)
            for i in range(spikes):
                cv2.ellipse(frame, (x, y), (round(r), round(r / 10)), i / spikes * 360, -3 / spikes * 360, 3 / spikes * 360, self.virusStroke, self.virusStrokeWeight)
            # cv2.putText(frame, entity["id"], (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255)
            # cv2.putText(frame, (str(virus["x"]) + "," + str(virus["y"])), (x, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 255)

        if "render" in self.callbacks:
            self.callbacks["render"](frame)
        return frame

    def take_action(self, action):
        self.target["x"] = action["x"]
        self.target["y"] = action["y"]
        self.move(self.target)
        if action["fire"]:
            self.fire()

        if action["split"]:
            self.split()
        if "render" in self.callbacks:
            self.callbacks["take_action"]()

    def register_callback(self, event_name, callback):
        """Socket.io callbacks are: handshake, playerInfo, gameSetup, gameUpdate, dead.
        Class callbacks are: start, stop, move, fire, split, render, take_action.
        """
        if not event_name in self.callbacks:
            self.callbacks[event_name] = callback
        else:
            raise KeyError(event_name + " callback already registered!")
