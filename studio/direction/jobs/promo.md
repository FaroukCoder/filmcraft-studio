# Job: motion-graphics video

**In:** a brief (what is true, for whom, what to do after watching) or a storyboard JSON; the pack
(`house` for the owner's channel); real footage or screenshots when there are any.
**Out:** an MP4 (1080x1920), the HTML page that made it, the gate numbers, a contact sheet.
Run: `python -m studio.job promo "<brief>" [--pack house]` or `promo - --storyboard board.json` (a board may set `"plate"`: footage behind the text).
**Who checks:** `look.py` + `lint.mjs` (automatic), then the owner.

## Two tiers
1. **Templates (`promo.py`)**: fast, deterministic, for simple explainers. The grammar is fixed to
   `system/motion.md`: words rise out of masks, scenes cut hard mid-motion, the phrase always
   drifts, no stat slides, no bullet dots, no accent word.
2. **Directed films (`claude -p` + the motionmaxxing skill)**: for anything that should be a film,
   not a page. Run from this folder so it reads `CLAUDE.md`; it storyboards, shows 3 stills, then
   builds with its GSAP runtime and gates its own render. Needs the owner's Claude login.

## Copy rules (the storyboard prompt enforces them)
- Specific and true: "62 minutes in, 9 clips out" beats "Raw footage in. Reels out."
- Plain verbs, sentence case or lowercase, max ~6 words a scene. No slogans (see `never.md`).
- Show it, then say it: a claim is followed by the real thing (a clip, a screenshot).
- End small: the handle once, held 0.6-1.4 s, no tagline + button + URL lockup.
