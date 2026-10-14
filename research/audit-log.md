# Audit log — projects research

Session started 2026-10-14 01:48 UTC. Report: `projects-research.md` (same folder).

## Context gathered before round 1 (from your repos)
- **whatstheID** (private repo, `main` @ 8f88cc5): already has shazamio + AudD fallback, a self-built landmark
  fingerprinter against your own library with a query-side speed ladder (±4% pitch), a librosa-based
  comb-filter tempo estimator (0.01 BPM MAE vs Serato on 17 tracks), a key ensemble (53% exact / 94% mixable),
  a read-only Serato `database V2` / `.crate` parser, and a hand-written WebGL2 engine ("Needlepoint").
  Not built: Serato write-back (crates, cue points, beat grids), Soulseek downloads (no slskd code on `main`).
- **FilmCraft fork** (`FaroukCoder/filmcraft-studio`, public): tracks upstream; no Creative Studio code in it.
  Upstream already ships multicam commands (`multicam.cutToCamera`, `clip.createMulticam`), scene edit
  detection, heuristic `auto_reframe`, colour match, Whisper (feature-gated, off in releases).
  Upstream's own gap list: Windows runtime under-tested (G9), no PR CI (G4), 10-bit / 4:2:2 H.264/HEVC
  does not decode on Windows without hardware (G3).
- **claude-config** (private): ECC plugin + ~110 skills; `learn-to-vault` writes to an Obsidian vault built on
  the Karpathy "LLM wiki" pattern (`claude-obsidian` fork). So a vault memory layer already exists.
- Creative Studio, Hermes/Laya and Reel Brain code is not on GitHub; judged from your description only.

## Round 1 — breadth (01:48–02:12 UTC)

**Searched:** auto-editing and beat-sync tools, beat/downbeat trackers, multicam selection research, reframing,
motion-graphics renderers, image/video model licences, local models for 12 GB, Hermes docs (sparse clone of
`NousResearch/hermes-agent`), Ollama issues, VLMs for short video, structured output, entity linking, Serato/Rekordbox
formats (read rb2serato and whats-now-playing source), fingerprinting for DJ mixes, canvases, payments from Egypt,
clipping prices, Cairo scene.

**Things that changed the plan before the draft was even written**
- Qwen-Image 2.1 is reported as research-only (Qwen Research License, 2026-09-20). Moved to Top 10 #1 because it
  blocks paid work.
- Ollama's Go runner ignores repetition penalties (issue #14493, still open) → likely cause of Reel Brain's looping
  JSON. Became Top 10 #2.
- Hermes now has a managed llama.cpp runtime with expert offload, Tool Search and Kanban. Recommending a separate
  orchestrator framework would have duplicated what Hermes already ships.
- Serato DJ 4 history (`master.sqlite` → `history_entry`) is verified from code. That reframes "BPM accuracy on fast
  techno" for *your own* sets as an alignment problem, not a tracking problem.
- All-In-One (allin1) looked like the obvious structure analyser; last commit 2023-10-10 and NATTEN must be built
  from source on Windows. Demoted to "avoid for production".
- OpenMontage (68k stars) looked like the obvious auto-editing base; it is AGPL-3.0. Ideas only.

**Tool problems:** WebFetch could not resolve several hosts (huggingface.co, blog.comfy.org, transactions.ismir.net,
rbxport.com). Worked around with web search summaries and by cloning repos to read source. Hugging Face model cards
remain unread: every licence claim that depends on one is marked medium confidence.

**Open questions for round 2 (Creative Studio audit)**
- Does Beat This handle 2-hour files and 150 BPM techno without octave errors?
- Is the L1 camera-path idea implementable in your stack (Python cvxpy? Rust?), and is there an open implementation?
- HyperFrames vs your existing HTML→alpha renderer: what does it actually add?
- Verify MiniMax H3 licence and 12 GB feasibility claims; verify the IEEE CLIP+SVM paper date.
- Find evidence (not opinion) on how reference clips are cut.

**Late round-1 additions (after the first commit)**
- **Laya is `NandhaKishorM/laya`** (found via a podcast-editor repo that embeds it). Its README says the base
  checkpoints are near chance zero-shot (0.36 vs 0.32 random) and over-confident (ECE 0.47). My first draft told
  you to "measure first, then maybe replace with EmbeddingGemma + logistic regression" without knowing what Laya was.
  Rewritten: Laya is designed to be fine-tuned; the move is labels → fine-tune (Kaggle 2×T4) → calibrate, with the
  logistic baseline kept in shadow. Promoted to Top 10 #2.
- **FilmCraft Arabic titles are reported broken upstream (#395, open).** Changes where Arabic captions get rendered
  (HTML layer) for the podcast-clip money path.
- **Egyptian Arabic ASR:** QwenCleo-ASR (Apache-2.0) reports 19.9 % WER vs 63.9 % for Whisper large-v3 on an
  Egyptian + code-switching set (self-reported). Added to Creative Studio, Reel Brain and money.
- **Auto-posting:** TikTok unaudited clients and unverified YouTube API projects can only post private videos.
  "Auto-post" needs audits or stays manual on those platforms.
- **whatstheID competitors exist** (TrackSniff, Mixprism, audioscout.io, AudD). Sharing it publicly is only worth
  it on the angle nobody else has: matching against the DJ's own library and writing Serato grids.
- **Inspiration Canvas:** Eagle ($34.95 one-time) added as the paid option that may simply win; Allusion
  (open-source Eagle clone) is dead since 2023.
- Top 10 reshuffled: virality and Reel Brain classification moved into their project sections; Laya (#2) and a
  "house look" move (#8, low confidence) added.

## Round 2 — Creative Studio audit (02:11–02:20 UTC)

**Attacked:** licences of generation models, Beat This on electronic music, Serato history availability, the L1
reframing idea, HyperFrames, the planner/judge design, the "measure reference clips" claim, FilmCraft as the base.

**Killed or reversed**
- **"VLM judge ranks variants pairwise"** → demoted to a defect checker. Timeline-Bench (Sep 2026): best agent
  resolves 26.8 % of raw-footage editing tasks; most failures are quality failures from judging footage through
  stills. Pairwise LLM judges flip with order in up to 20 % of cases (J1). A small local judge choosing between your
  three variants is mostly noise; the taste pick stays human or goes to Trial Reels.
- **"AutoFlip drifts more"**: my own unsupported claim. Removed. AutoFlip is also unsupported since 2023-03-01.
- **HyperFrames as a drop-in**: its transparent WebM would lose alpha in FilmCraft (Matroska reader skips
  BlockAdditions). Now: ProRes 4444 MOV for overlays, and skip its component catalog (templates = the slop look).

**Confidence changes**
- Top 10 #7 (grids from your own tracks): stays medium, but the Beat This fallback is now backed by a Giant Steps
  benchmark (89.3 % / 95.0 %) and the maintainers' statement that the weights are MIT.
- Top 10 #1 (licence): stays medium. GitHub README still says Apache-2.0 but predates 2.1; Hugging Face unreachable.
- Top 10 #8 (look): stays low, now with motionmaxxing's measured basis (53 pro moments; transforms 3,392 vs fades 584).

**Added**
- OTIO as the plan format (FilmCraft imports/exports it); pin the fork to v0.7.2.
- MC4000 unlocks Serato DJ **Lite** (History yes, built-in recording no); Serato 3.x history format differs.
- Precedent for mix-to-track alignment on real mixes (Kim et al., ISMIR 2020); their code has no licence.
- Low-light denoise and "deliver, don't auto-post" for client work.

**Open for later rounds:** Timeline-Bench kappa figure (search snippet only; arXiv unreachable); MiniMax H3 licence
text (HF unreachable); whether Instagram's API path allows reels with their own audio (one third-party claim says no).

