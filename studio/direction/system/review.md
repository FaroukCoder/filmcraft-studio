# Review: how a render is judged

Look honestly, as a stranger scrolling. Numbers first, then eyes, then the owner.

## 1. Scripted gates (every delivery, automatic in `qa.py` when the skill is installed)
```
python ~/.claude/skills/motionmaxxing/scripts/look.py render.mp4 --out look --expect <seconds>
node   ~/.claude/skills/motionmaxxing/scripts/lint.mjs page.html      # promos only (G5 page chrome)
```
- **G0** renders, moves, right length, audio present. **G2** no run of more than 3 flat frames.
- **G3** end hold 0.6-1.4 s, final shot at most 25 % of the film.
- **G5** no page chrome (corner labels, tracked caps, counters, kicker above headline, deck layout).
- **Motion band**: mean luma change per frame vs the human median 6.8 (IQR 4.4-9.8).
- **Cut sync**: share of cuts on a sound onset (pros ~35 %).
A FAIL is fixed, never argued. A PASS is not taste.

## 2. Eye checks on the contact sheet (one sentence each, written in the report)
1. Describe every frame in one sentence. Would any of them pass as a slide or an app screen?
2. Cover the text. Is the picture still doing something?
3. Cover the name. Could this be any DJ's clip, any brand's promo? (Then it's a template.)
4. Is there exactly one hero per frame? Is the text off the hands, the face and the Reels UI?
5. Thumbnail test: at 15 % size, does frame 1 read?
6. Does anything in `system/never.md` appear?

## 3. The owner
Offer the variants side by side (the blind page: `motionmaxxing/scripts/blind_review.py`).
Write each keep / maybe / drop with its reason in `taste/verdicts.md`.
