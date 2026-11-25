# Flow recipes
Frames are at 20-24 fps. MEASURED/SEEN = taken from real edits; values marked (t) come from tutorial panels; every After Effects build is an equivalent and has not been tested in After Effects. Names in the last column are the edits a move was seen in (frame numbers).

## Base rig, every shot
1. Precomp each clip (move all attributes). Time Remap: fast, slow, fast. The slow part sits on the key action for 4-9 f at 0.3-1.5 % of frame width per frame.
2. Arrival null: position + roll + small zoom, 4-6 f, exponential. Measured speeds to aim at: 12.1 7.9 5.5 2.0 1.8 / 7.3 6.1 2.7 2.4. Roll example: -9.0 -2.3 -0.9 -0.7 degrees per frame.
3. Exit null: 1-4 f, hidden until late: 1.3 1.7 2.2 3.3 6.8 8.4. Bezier (t): exit .90 .02 1 .10-.15, entry .20 .90 .10 .98.
4. One null per move; a second move gets its own parent null that starts in the middle of the first, so nothing stops dead.
5. Motion Tile, mirror edges, 200-270 %. Layer motion blur on; S_Shake motion blur off.
6. Exposure key on arrival: -2 stops to 0 in 4-6 f, together with the luma reveal.

## Carriers
| Carrier | Build | out / in | Seen in |
|---|---|---|---|
| whip | Nulls above, same way both sides, directional blur spike 50-120 (t) back to 0 in 3-6 f. B arrives already blurred; its lamps streak | 2-4 / 4-6 | Wicked 12-14, 123-127, Moscow 206-208 |
| match | Scale and place B's shape on A's: same xy, size, axis. 1-4 f each in runs, 10-13 pictures in 30 f | 0-1 | F1 119-150, True Detective 105-109, CRUSH 693-706 |
| black | Crush A to highlights, 1-2 f black (violet rgb 4,2,5), luma reveal of B. One light or the title survives the black | 1-2 / 1-6 | Wicked 51, 154-155, Moscow 172-173 |
| reveal | Levels input black 180 to 0 over 4-6 f (up to 12) + exposure -2 to 0, or S_Hotspots threshold .3-.7 to 0 in 1-4 f (tutorials say 9-15; the real cuts are shorter) | 0 / 4-12 | Wicked 14-18, 30-34, 91-100, Moscow 178-182 |
| light | Extract of B (highlights) on Screen, placed at its final xy, 1-6 f before the cut; or A's lights left burning over B | 3-6 overlap | Wicked 83-89, MARVEL 55, 265-272, Zone 265-271 |
| flash | A blooms 2-3 f, 1 f of the grade's own white, B over-exposed and falling back 3-4 f | 2 / 3-4 | DUNE 499-503, IZXA all |
| slit | 1-2 f: thin horizontal strips shifted (Displacement Map from stretched Fractal Noise), or Minimax Max, Just Horizontal/Vertical, 60-260 (t) keyed 0, peak, 0 | 1-2 | Wicked 71, 142, DUNE 705 |
| cover | Push into a head, hand, train or dark object until it fills the frame, cut inside the dark, B continues the push | 2-3 / 2-3 | Wicked 102-106, 115-117, DUNE 33.7 s |
| tiles / panel | 2-5 panels arrive one per sub-beat, one becomes the next full shot | 2 f each | DUNE 183-206, 434-472 |
| hue | Last 5 f of A and first 5 f of B tinted to one hue, tint lifts | 3-5 / 4-6 | erenvisu 380-384, Tonaru 492-500 |
| dissolve | Mirrored or time-shifted copy of the SAME shot, 3-5 f | 4 | Wicked 44-47 |
| strobe | picture, black, picture, black, next; 1 f each | 4-6 | osMh 90-96, Nights Like This 363-371 |
| jump | Same person, new pose, covered by 1-2 f hot or negative | 1-2 | POP OUT 372-375 |
| still | Nothing. Hard cut on a sound; the composition carries | 0 | Moscow 261-507 |

## Streaks made from the footage's own lights
Duplicate the shot. Top copy: Extract/Levels above about 70 % luma. Move it 2-3 times the arrival move. Echo (Maximum, 12-20 echoes) or S_BlurMotion along the path. Screen over the base. A low sample count gives the stepped comb, which furys keeps. Curved streaks = the same with roll.

## Treatment frames (1 f each, never twice in a row)
crush to highlights · threshold · invert/negative · duotone or tritone · solid colour of the block · blue solarise (S_Solarize) · slit · pixel rain (thin strip, scale Y over 1000 %) · depth silhouette (roto, grey, thin outline) · body filled with a colour (roto) · RGB split · halftone (S_HalfTone) · find edges + invert · 1 f of the next shot, 2-3 f early · black. Package for anime-type cuts: crush, threshold, white or solid + radial blur, new shot +10-15 % hot, then 5-7 f of exposure and hue decay.

## Light on arrival (IZXA)
Club: f0 2-3 times the settled luma, f1 1.1-1.5, normal by f2-4. Travel: 1.5 times, decaying over 7-10 f. Peak on the first frame, exponential out. 40-60 % of shots get one light event, not all four kinds. The flash solid uses the film's own highlight hex, never pure white.

## Type
Wide-tracked light caps, 20-25 % of the width, on the empty side. Letters arrive out of order, one change per frame, and leave the same way. A micro caption (8-14 px at 1080) grows a word per shot across cuts. Text survives cuts and black, then is destroyed (ticks, slit, blur), not faded. Check that it reads on a phone.

## Sound
Four shapes (from the isolated Wicked Games layer): noise climbing 10-13 f to the cut and down in 5 f · swell gated hard on a black frame · sub hit 30-150 Hz on black or freeze, decay 5-12 f · mono 8-15 kHz tick of 1-2 f on a treatment frame. A low bed between. 1-1.6 per second. Peaks on kicks, claps stay clean. Section filters open and close on a cut. -14 LUFS integrated, true peak -1 dB is a safe target.

## More moves (builds are guesses)
- **Bokeh wipe:** 3-5 soft lens discs grow to full white, new shot underneath; 4 f up, 1-2 full, 4 f down. Cheap.
- **Light-only plate:** Levels until only the lamps remain, hold 8-12 f, release.
- **Long push:** one 83 f push through street, car, driver, into a ring; its highlights become the flash, then smoke. Works for a car film in B&W plus one colour.
- **Person first, place later** · **colour enters on the drop** · **print swap inside one object** (liveries, jerseys) · **passing plates** like train pillars.

## Mistakes that break it (seen in the weaker edits)
One transition for every cut · effect between unrelated shots · 17 f of texture with no picture · cutting straight to the final grade · shake only after the cut · white as a tic · everything moves, no rest · too dark with no bright shape · loops of half the clips.
