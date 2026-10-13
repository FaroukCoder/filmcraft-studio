# Graphics library

Every reusable graphic, what it's for, and when to reach for it. Check here before building
anything new; add a row when something new is approved (the motion-library loop in `CLAUDE.md`).
Code: `studio/mograph.py` `TEMPLATES` (overlays) and `studio/promo.py` (full-frame scenes).

| name | what it does | use it when | params |
|---|---|---|---|
| `name` | The DJ's name lands once on the drop: from 2.2x oversize and blurred, decelerating, keeps shrinking slightly while it holds, leaves upward fast | DJ clip, the drop, when we know the DJ | `text`, `y` (17 %), `size`, `out` |
| `credit` | Track title, then artist, rise out of masks lower left, drift, drop back | DJ clip, only when the track is known (Serato history / the DJ) | `text` (title), `sub` (artist), `y` (64 %), `out` |
| `kinetic-title` | A short statement word by word out of masks, uneven onsets, sentence case | talking-head emphasis, a promo overlay on footage | `text`, `y`, `size`, `out` |
| promo `words` / `title` / `list` / `stat` / `image` / `cta` | Full-frame scenes on the pack's field or a footage plate; hard cuts mid-motion | template promos (see `jobs/promo.md` for when to go to a directed film instead) | storyboard JSON |

## Retired 2026-10-13 (do not bring back)
`track-id` ("TRACK ID?" slam + shake + yellow underline), old `kinetic-title` (caps, bounce pop,
yellow last word), `lower-third` (yellow bar). Reasons in `taste/verdicts.md`.

## Wanted (pitch as stills first)
- A **tracklist strip** for a set recap: the real Serato history, time-coded, set in the pack.
- A **phrase counter** that ticks per bar during a build-up (only if it reads as music, not HUD).
- The **house-pack sting** for the owner's channel: the whatstheID core as a 3D object
  (motionmaxxing `runtime/hero3d`), arriving by cause.
