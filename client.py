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
    def __init__(self, index, screen_size=600, display_window=False, player_control=False, spectator=False):
        self.socket = socketio.Client()
        self.screenWidth = screen_size
        self.screenHeight = screen_size
        self.alive = True
        self.display_window = display_window
        self.player_control = player_control
        self.index = str(index)
        self.spectator = spectator
        if self.display_window:
            cv2.namedWindow("agario" + self.index)
            cv2.resizeWindow("agario" + self.index, self.screenWidth, self.screenHeight)
            if self.player_control:
                cv2.setMouseCallback("agario" + self.index, self.mouse_callback)
        self.frame = np.full((self.screenHeight, self.screenWidth, 3), 255, np.uint8)
        self.target = {"x": 0, "y": 0}

        # variables needed for rendering
        self.cells = []
        self.food = []
        self.mass = []
        self.viruses = []
        self.ratio = 1
        self.playerMass = 10
        self.playerCoords = {"x": 0, "y": 0}

        self.start()

    def start(self):
        self.register_socketio_callbacks()
        self.socket.connect("http://localhost:3000")
        if self.player_control:
            while self.alive:
                # TODO render should actually always happen, just doing this for speed up reasons
                self.render()
                self.move()

    def stop(self):
        self.socket.disconnect()
        cv2.destroyAllWindows()

    def register_socketio_callbacks(self):
        @self.socket.event
        def connect():
            print("connection established")
            name = "player" + str(random.randint(10, 1000000))
            if self.spectator:
                player = {"name": name, "id": name, "target": {}, "type": "spectator"}
            else:
                if self.index:
                    name = "player" + self.index
                player = {"name": name, "id": name, "target": {}, "type": "player"}
            self.socket.emit("gotit", player)

        @self.socket.event
        def playerJoin(name):
            print(name, "joined")

        @self.socket.event
        def gameSetup(dimensions):
            self.socket.emit("windowResized", {"screenWidth": self.screenWidth, "screenHeight": self.screenHeight})

        @self.socket.event
        def welcome(currentPlayer):
            print("welcome", currentPlayer)

        @self.socket.event
        def virusSplit(splitCell):
            print("got virusSplit")
            self.socket.emit("2", splitCell)

        @self.socket.event
        def serverTellPlayerMove(visibleCells, visibleFood, visibleMass, visibleVirus, playerInfo):
            if False:
                print("visibleCells", visibleCells, len(visibleCells))
                print("visibleFood", visibleFood, len(visibleFood))
                print("visibleMass", visibleMass, len(visibleMass))
                print("visibleVirus", visibleVirus, len(visibleVirus))
                print("=" * 20)

            if playerInfo["totalMass"] != self.playerMass:
                self.playerMass = playerInfo["totalMass"]
                self.update_screen_size_from_mass()
            self.playerCoords["x"] = playerInfo["x"]
            self.playerCoords["y"] = playerInfo["y"]

            for entity in visibleCells + visibleFood + visibleMass + visibleVirus:
                entity["x"] -= playerInfo["x"]
                entity["y"] -= playerInfo["y"]
                entity["x"] *= self.ratio
                entity["y"] *= self.ratio
                if "radius" in entity:
                    entity["radius"] *= self.ratio

                if "cells" in entity:
                    for subcell in entity["cells"]:
                        subcell["x"] -= playerInfo["x"]
                        subcell["y"] -= playerInfo["y"]
                        subcell["x"] *= self.ratio
                        subcell["y"] *= self.ratio
                        subcell["radius"] *= self.ratio

            self.cells = visibleCells
            self.food = visibleFood
            self.mass = visibleMass
            self.viruses = visibleVirus

        @self.socket.event
        def RIP():
            self.alive = False
            self.stop()

    def move(self):
        self.socket.emit("0", self.target)

    def fire(self):
        print("fire")
        self.socket.emit("1")

    def split(self):
        print("split")
        self.socket.emit("2", False)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.target["x"] = x - self.screenWidth / 2
            self.target["y"] = y - self.screenHeight / 2

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
        frame = np.full((self.screenHeight, self.screenWidth, 3), 255, np.uint8)

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

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for entity in self.food + self.mass:
            x = int(entity["x"] + self.screenWidth / 2)
            y = int(entity["y"] + self.screenHeight / 2)
            r = int(entity["radius"])
            col = (entity["hue"], 255, 255)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

        for cell in self.cells:
            for subcell in cell["cells"]:
                x = int(subcell["x"] + self.screenWidth / 2)
                y = int(subcell["y"] + self.screenHeight / 2)
                r = int(subcell["radius"])
                stroke_col = (cell["hue"], 255, 150)
                stroke_weight = 7
                frame = cv2.circle(frame, (x, y), r + stroke_weight, stroke_col, cv2.FILLED)

                col = (cell["hue"], 255, 255)
                frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

        for v in self.viruses:
            x = int(v["x"] + self.screenWidth / 2)
            y = int(v["y"] + self.screenHeight / 2)
            r = int(v["radius"])
            col = hex2color(v["fill"])
            stroke_col = hex2color(v["stroke"])
            col = list(map(lambda x: int(x * 255), col))
            stroke_col = list(map(lambda x: int(x * 255), stroke_col))
            stroke_weight = int(v["strokeWidth"])
            spikes = int(v["mass"] / 2)
            frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)
            for i in range(spikes):
                cv2.ellipse(frame, (x, y), (int(r), int(r / 10)), i / spikes * 360, -3 / spikes * 360, 3 / spikes * 360, stroke_col, stroke_weight)

            # frame = cv2.circle(frame, (x, y), r, stroke_col, stroke_weight)
            # frame = cv2.circle(frame, (x, y), r, col, cv2.FILLED)

        if self.display_window:
            cv2.imshow("agario" + self.index, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.alive = False
                self.stop()
            if self.player_control:
                if key == ord("w"):
                    self.fire()
                if key == ord(" "):
                    self.split()

        return frame

    def take_action(self, action):
        self.target["x"] = action["r"] * math.cos(action["theta"])
        self.target["y"] = action["r"] * math.sin(action["theta"])
        self.move()
        if action["fire"]:
            self.fire()

        if action["split"]:
            self.split()
