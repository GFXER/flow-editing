# flow-editing

A Claude Code skill for flow edits (the furys / IZXA kind of car, film and music edit), with the scripts it uses: a plan checker, a renderer and two measuring tools.

![14 s car edit made with flow_render.py, muted](docs/preview.gif)

The preview is phone footage of one car in daylight. The plan, the night grade, the matched wheels and lamps, the light streaks and the 1-frame looks all come from `flow_render.py`.

![every 23rd frame](docs/sheet.jpg)

## Install

```sh
git clone https://github.com/GFXER/flow-editing
cp -r flow-editing/skills/flow-editing ~/.claude/skills/
pip install -r flow-editing/requirements.txt
```

You also need ffmpeg. The scripts use the `FFMPEG` variable if it is set, otherwise the first `ffmpeg` on your `PATH`.

Then in Claude Code: `/flow-editing`, or say "make a flow edit from these clips".

## What's inside

| File | What it does |
|---|---|
| `SKILL.md` | the method: ten rules and the steps |
| `references/RECIPES.md` | 14 ways to carry a cut, with frame counts |
| `references/LOOKS.md` | four looks with measured numbers |
| `scripts/flowplan.py` | prints the shot table and checks the plan (repeated transitions, missing rests, flashes per second) |
| `scripts/flow_render.py` | renders the picture from a JSON plan and your clips |
| `scripts/flow_measure.py` | measures any edit: cuts, ramps, light, cuts against sound |
| `scripts/flow_sync.py` | scores a remake against a reference, 0 to 100 |

```sh
python3 scripts/flowplan.py plan.json
python3 scripts/flow_render.py plan.json draft.mp4 --scale 0.5
python3 scripts/flow_measure.py edit.mp4 out/ --sheet
python3 scripts/flow_sync.py reference.mp4 remake.mp4
```

Run `python3 tests/smoke.py` to check the install. It draws its own clips, so no footage is needed.

## Where the numbers come from

About 400 public edits by furys, IZXA, Tonaru, erenvisu, jrvyFX and others went through `flow_measure.py`, and a few dozen were read frame by frame. Nobody listened to them: the sound notes are measurements. This repo contains none of their footage, sounds, presets or project files, and none of them had a part in it. If you like the style, follow them.

## Not tested, not done

- The After Effects builds in RECIPES have not been run in After Effects.
- `flow_render.py` was used on one real edit (14 s, 24 fps, 1080x1920) and on synthetic clips. It makes no sound.
- `hide` covers plates and faces with a tracked soft box. Check every frame.
- `flow_measure.py` counts flashes as cuts and misses cuts hidden in black.

Fast flashes can harm people with photosensitive epilepsy. The checker warns above 3 in a second.

MIT licence. Made by cheats1337.
