# NEAB

## A Neuro Evolving Agar.io Bot

A bot trained to play agar.io using neuro-evolution and multi-agent leagues.


## Running Screenshot

First install and launch the node server.

```
npm install
node server
```

Then we can generate a new screenshot by executing

```
python3 screenshot_generator.py --total-bot-count 5 \
  --recording-bot-count 3 \
  --total-frames 1000 \
  --frame-size 128
```

Building and Running Docker image

```
docker build -t neab/server-node .
docker run -p 127.0.0.1:3000:3000 -d neab/server-node
```

Checking Logger

```
# Getting Container ID
docker ps
docker logs <container id>
```
