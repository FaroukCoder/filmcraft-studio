# Job: DJ drop clip

**In:** the DJ's camera file + the clean Serato recording of the same set; the DJ's name (and
handle); optionally the Serato history (real track names) and the DJ's pack.
**Out:** per chosen drop, 3 variants (1080x1920, 30 fps, -14 LUFS), a contact sheet, the gate
numbers, a report. Run: `python -m studio.job dj <camera> <audio> --dj "<name>" [--pack club]`.
**Who checks:** `qa.py` + `look.py` (automatic), then the owner on the blind page, then the DJ.

## What a good clip is
- **The drop is the hook.** It lands in the first second (the flash-forward tease), the clip cuts
  back on a bar line to the build-up, and pays off again. No caption has to sell it.
- **Footage first.** Graded with the pack's grade: dark club footage lifted, grain felt not seen.
  The crop follows the DJ (reframe) and never slices a name, a logo or a face.
- **Text is small, real and rare.** The DJ's name lands once on the drop, from oversize, and
  leaves. A track credit appears only when we *know* the track (Serato history or the DJ), set
  small in the lower third, clear of the hands. No "TRACK ID?" bait: the comments will ask anyway.
- **One bold moment.** The camera snaps in on the drop (+7 %, 1 frame) and settles over ~15 f.
  That is the only effect.
- **Variants differ in structure**, not in decoration: tease length, how much build-up, which
  graphic (name / credit / none).

## Never (on top of `system/never.md`)
- A caption on screen for the whole clip. A burned-in outlined caption track.
- A graphic that sits over the decks or the DJ's hands.
- A clip that opens on the build-up with nothing happening for 2 s.
