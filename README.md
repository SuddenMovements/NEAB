# NEAB

## A Neuro Evolving Agar.io Bot

A bot trained to play agar.io using neuro evolution and multi-agent leagues.

To install the custom gym environment, cd into the gym-agario folder and run `pip install -e .`

## Todo

Server.js line 494, look at quadtree implementation and maybe remove, depending how slow the server runs with lots of connected clients

In the real game there is some input lag between player mouse movement and cell response. Need to simulate this on the client side for training and then remove this limitation in the future
