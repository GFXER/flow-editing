---
name: flow-editing
description: |
  Plan, build and check a flow edit: clips chosen in chains, one carrier per cut, light that arrives before the picture, speed ramps, 1-frame treatments, dark grade, small type. Use when the user says "flow edit", "flow editing", "furys style", "IZXA style", "visualizer edit", "/flow-editing", wants a car, travel, film or music edit in that look, wants a reference flow edit remade, or asks how flow works. Do NOT use for talking-heads, subtitles, plain beat cuts or a single named fix.
---
# flow-editing

Numbers come from measuring public edits frame by frame (furys, IZXA and others, 2026): about 400 videos through the measuring tool, a few dozen looked at frame by frame. The After Effects builds in RECIPES are equivalents and were not tested in After Effects. `flow_render.py` was tested on one 14 s car edit.

## The idea
The eye never has to search. The last thing it holds in shot A is the first thing it finds in shot B: same place, same light, same shape or same direction. Effects only polish that. Matching the camera direction alone is close to chance in the measured edits.

## Ten rules
1. Chain first. Choose 3-7 shots that share one thing (wheels, backs of heads, lamps) before any effect.
2. One carrier per cut, named in the plan. In 8 furys edits counted by hand: whip 59, shape match 57, black hinge 56, luma reveal 40, light carry 27, flash 25.
3. Light before picture. B starts as highlights, then mids, then colour, over 4-6 frames.
4. Dark is the glue. Median luma 10-30 of 255, with strong lights.
5. Ramp: slow middle, fast ends. Out 2-4 f, in 4-6 f (1, .48, .34, .23, .19, .14). Peak on the cut.
6. Dirty edges, clean middle. 1-3 odd frames per edge, all different, about 70 % of the shot clean.
7. Treatment frames last 1 f, never the same twice in a row, and they hide a time jump.
8. Rest. After 3-5 busy cuts one hold of 15-26 f.
9. Sound first. Cut on the first frame at or after the sound. Not every cut sits on a beat.
10. Bookend. The first motif returns at the end.

## Steps
1. Ask what's missing: footage, song, length, look (`references/LOOKS.md`).
2. Tempo: never trust one beat tracker. Use the waveform repeat lag, then claps and kicks. Write them as frames.
3. Footage sheet: for each clip note direction, brightest shape and its xy, darkest edge, what crosses the lens, dominant hue. If fewer than half the clips have a carrier, say so.
4. Write `flowplan.json` (fields in `scripts/flowplan.py`, plus the render fields in `scripts/flow_render.py`). One file serves both.
5. `python3 scripts/flowplan.py flowplan.json`. Fix every FAIL, explain each WARN that stays.
6. Show the table and 3 stills. Wait for the OK.
7. Draft: `python3 scripts/flow_render.py flowplan.json draft.mp4 --scale 0.5`. Look at every frame around each cut. Then full size, or build it in the user's editor with `references/RECIPES.md`.
8. Sound: noise climbing 10-13 f to a cut, a swell gated on a black frame, low hits on black or freeze frames, 1-2 f ticks on treatment frames. Peaks on kicks, claps stay clean. Mux with ffmpeg.
9. Check: `flow_measure.py` for shot length, ramps and cuts against sound; for a remake `flow_sync.py ref.mp4 render.mp4`.

## Remaking a reference
Same size and fps. Place cuts by frame number, put the speed peak on its fastest frame, then match luma per frame. `flow_sync.py` scores luma, level, speed and cut timing: a file against itself is 100, one frame late about 50. It knows nothing about picture content, colour, type or sound. With other clips, say that plainly.

## Care
- More than 3 full-frame flashes in a second can harm people with photosensitive epilepsy. Full-frame red flashes are a known extra risk; thin them out.
- No negatives or white flashes in serious pieces.
- Use your own or licensed footage, music and overlays. The reference edits are for study.
- Cover plates and faces that shouldn't be seen (`hide` in the plan), and check every frame: the tracker can slip.

## Limits
Nobody listened to the references, sound findings are measured. Plugin values in RECIPES marked (t) were read from tutorial screens. The measuring tool miscounts flashes as cuts and misses cuts hidden in black.
