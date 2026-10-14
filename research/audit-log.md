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

## Round 1 — breadth (01:48–02:15 UTC)

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

