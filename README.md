# NEAB

## A Neuro Evolving Agar.io Bot

A bot trained to play agar.io using neuro evolution and multi-agent leagues.
To install the custom gym environment, cd into the gym-agario folder and run `pip install -e .`

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
