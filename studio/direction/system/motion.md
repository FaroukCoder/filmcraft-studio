# Motion: measured values only

Never invent a curve. These come from motionmaxxing's frame-by-frame measurements of 53 pro
motion moments (`runtime/motion.js`, `references/motion.md`, `slop.md`), the animate skill, and
the owner's whatstheID tokens. CSS names live in `packs/*.css`.

## Curves
| token | CSS | use |
|---|---|---|
| `--ease-land` | `cubic-bezier(.16,1,.3,1)` | every arrival (motionmaxxing *softLand*; = the owner's `--ease-liquid`): 60-72 % of the travel in the first 4-5 frames, then a long tail, no bounce |
| `--ease-leave` | `cubic-bezier(.5,0,.75,0)` | every exit (*accelExit*): starts slow, leaves fast, 6-13 frames |
| `--ease-move` | `cubic-bezier(.77,0,.175,1)` | something travelling on screen (strong ease-in-out) |
| `--ease-drift` | `linear` | living holds: drift, push-in, grain |

## Durations at 30 fps
- A move: median **10 frames (0.33 s)**. Entrances 8-15 f with the tail; exits 6-13 f.
- Words: whole words, **2-4 f apart** on a fast hook, **4-6 f** in a headline, **8-12 f** with voice.
  Uneven gaps (3,2,2,2), never a metronome.
- Reading hold: about **1.2 s per 20 characters**, 0.5-1.2 s per line. Payoff hold 0.8-1.0 s.
- A designed breath before a payoff: 0.6-1.5 s, with a reason.
- Cuts every 0.3-2.3 s; in DJ clips, cuts sit on bar lines (already true in `plan.plan_dj_clip`).
- End hold **0.6-1.4 s**, final shot at most 25 % of the film.

## Grammar
- **Arrive by moving or unmasking.** A word rises out of a mask (overflow hidden) or drops in from
  0.03-0.08 H with 3-6 px blur clearing in 4-8 f. No opacity ramp on headlines.
- **Arrival decelerates from oversize.** A name lands from ~1.6-3x and shrinks to rest; never from 0.
- **Exits are new motion**, not the entrance reversed: faster, accelerating, overlapping the next
  entrance by ~2 frames.
- **No dead frame.** A held frame keeps one living thing: the phrase drifts ~2-7 % W over its life,
  the camera pushes in slowly.
- **Camera snap on the hit** (DJ clips): one-frame snap in (+6-9 % scale) on the drop, then a
  9-18 f settle. Once per clip, or once per 4-bar phrase at most.
- **One accent, one meaning.** In the house pack pink means "attention / unresolved"; it is used
  once per video, not as decoration.
- Human-made films change on average **6.8/255 luma per frame** (IQR 4.4-9.8). `look.py` prints
  ours; v1 promo was 0.4 (a slideshow).
