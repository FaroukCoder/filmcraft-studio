# Never ship

A render with any of these is not finished: delete the element, don't justify it. Sources: the
owner's own design language (whatstheID `DESIGN.md`), the motionmaxxing slop file (measured on 53
pro moments and ~30 blind-judged AI films), the frontend-design and design-taste skills, and the
owner's 2026-10-13 verdict on v1 ("very AI slop... the text, the motion, the colour choice").

## Copy
- **Bait captions.** "TRACK ID?", "WAIT FOR IT", "WHO MADE THIS?", "POV:", "watch till the end". The
  drop is the hook. If there is text, it is real information (the DJ's name, the real track).
- **Slogan shapes.** "Not just X. It's Y.", "No X. Just Y.", one-word triplets ("Fast. Local. Free."),
  "Unlock", "Meet X", "the future of", "elevate", "seamless", "next-level".
- **Invented proof.** No number, track, venue or quote that isn't real and sourced. Say what was
  measured ("9 clips from one 62-min set"), never a precise-looking guess.
- **Em dashes and en dashes** anywhere on screen. Use a period, a comma, or a line break.

## Type
- **All caps** for headlines or labels. Sentence case or lowercase (the owner's voice is lowercase).
- **The accent word**: one word of a headline in another colour, weight or italic.
- **Default faces**: Segoe UI Black, Arial Black, Inter, Montserrat, Impact. Use the pack's faces.
- **Outlined white text** (stroke + drop shadow) as the readability fix. Fix the placement or the
  grade instead; a soft local shade under the words is fine.
- **Letter-by-letter typing** on anything that isn't a real input field.
- **Text over the action**: never over the DJ's hands or face, never in the Reels UI zones
  (top 12 %, bottom 22 %, right 12 %).

## Motion
- **Fade-ins.** Words and objects arrive by moving, unmasking or cutting, not by opacity ramps.
- **Bounce / overshoot pops** (`cubic-bezier(.2,1.6,...)`), shakes, wobbles. One spring per film at most.
- **`ease-in` entrances, linear entrances, built-in `ease-out`.** Use the curves in `system/motion.md`.
- **Scale from 0.** Arrivals decelerate *from oversize* or from 0.95, never grow from nothing.
- **Uniform stagger** (every word 0.09 s apart). Gaps follow speech or uneven frames (3,2,2,2).
- **Dead frames**: a held frame with nothing alive. Something always drifts.
- **Crossfades between scenes.** Hard cut, mid-motion; the next scene starts already moving.

## Picture
- **Premium pastiche**: near-black void + radial glow + vignette + lens flare. The ground is a real
  surface (footage, the brand's field, a lit material), not a glow on black.
- **A deck**: a held headline block, a kicker above a headline, a bullet list with dots, a centred
  big number over a small label (stat slide), three equal cards.
- **HUD chrome**: corner names, timecodes, BPM/FPS text, "01 / 04" counters, progress bars, brackets.
- **A web-footer ending**: logo + tagline + button + URL, or any end card held past 1.4 s.
- **A third hue** in the house pack (violet structure + pink attention only; never green).
- **Pure `#fff` text** in the house pack (use the pack's `--t-hi`).
- **Dark, muddy club footage left as shot.** Every DJ clip goes through the pack's grade.
- **A name cut off by the crop** (v1 showed "SARA" sliced at the frame edge).

## Process
- **A render nobody looked at.** Every delivery has a contact sheet and the scripted gate numbers.
- **Self-certifying.** The report quotes `look.py` / `lint.mjs` numbers; it never says "clean".
