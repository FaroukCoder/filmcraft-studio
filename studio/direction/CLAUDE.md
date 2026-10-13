# Studio direction: start here

This folder is how the studio decides what its videos look like. Every planner, template and
`claude -p` run reads from here, and a person reviewing a render checks against it. Code reads
`packs/*.css`; models and people read the markdown.

**New job?** Read `system/never.md` first, then the job's own file in `jobs/`, then the pack.

| You are making | Read, in order |
|---|---|
| a DJ drop clip (`job.py dj`) | `system/never.md` → `jobs/dj-clip.md` → the DJ's pack in `packs/` |
| a motion-graphics video (`job.py promo`) | `system/never.md` → `jobs/promo.md` → `system/motion.md` → the pack |
| a new reusable graphic | `library/INDEX.md` (is it already there?) → `system/motion.md` → add it to the index |
| a review of a render | `system/review.md` (scripted gates, then the eye checks), log the verdict in `taste/verdicts.md` |

## How work flows (the two loops that keep it out of slop)

1. **Ideas before builds.** For anything new (a graphic, a pack, a format), pitch 2-3 directions as
   **stills** first. The owner picks; only then animate. (Josh Blatch's motion-library mod: "nothing
   gets built until I pick".)
2. **Every verdict becomes a rule.** When the owner keeps or drops something, write one line in
   `taste/verdicts.md` with the reason. Repeated verdicts move into `system/never.md` or the pack.
   (Chord's keep / maybe / drop review: "whatever I lock in gets written up as rules".)

## Where the rest lives

| What | Where |
|---|---|
| The rules every video obeys (instant rejects) | `system/never.md` |
| The owner's taste, voice and identity | `system/taste.md` |
| Curves, durations, timing (measured, not invented) | `system/motion.md` |
| How a render is judged (gates, scripts, eye checks) | `system/review.md` |
| Per-identity tokens: fonts, colours, grade | `packs/house.css` (owner's channel), `packs/club.css` (DJ clients, default) |
| Job briefs: in, out, who checks | `jobs/dj-clip.md`, `jobs/promo.md` |
| Built graphics and when to use each | `library/INDEX.md` |
| References and what we take from each | `inspiration/references.md` |
| Keep / drop log | `taste/verdicts.md` |
| Fonts (OFL, licences beside them) | `fonts/` |
| The deep reference behind most rules | `~/.claude/skills/motionmaxxing` (Apache-2.0): `references/slop.md`, `motion.md`, `type.md` |
