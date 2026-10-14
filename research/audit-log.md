# Audit log — projects research

Session started 2026-10-14 01:48 UTC. Report: `projects-research.md` (same folder).

## Context gathered before round 1 (from your repos)
- **whatstheID** (private repo, `main` @ 8f88cc5): already has shazamio + AudD fallback, a self-built landmark
  fingerprinter against your own library with a query-side speed ladder (±8 % in 1 % steps; corrected in round 16 from "±4 %"), a librosa-based
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

## Round 2 — Creative Studio audit (02:10–02:16 UTC)

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

## Round 3 — Hermes + Laya audit (02:16–02:19 UTC)

**Attacked:** the llama.cpp move, Tool Search, model choice, memory layer, "acting on plans", Laya fine-tuning,
GPU scheduling between agents. Read Hermes issues directly on GitHub.

**Killed or reversed**
- **"Turn on Tool Search"** (round 1 Top 10 #3, now #4) → reversed for Qwen models. Its bridge tool is named
  `tool_call`, which collides with Qwen's `<tool_call>` template tag; the turn halts after five malformed calls
  (hermes-agent #110442, open; fix PR unmerged). Workaround: Tool Search off, trim tools by hand.
- **"Local Qwen3.6 gives reliable tool use"** → softened. Open issues show a tool call stranded in reasoning in
  1 of 23 turns (#129440), corrupted output without the right chat template (#29677), and a glob/regex loop
  (#66129). The honest target is "recovers well", not "never fails".

**Added**
- Hermes v0.21.0 made `state.db` fragile; v0.21.2 fixed it (44 issues). Use `hermes backup`.
- `/goal`, cron no-agent mode and Kanban `--goal` cards cover "acting on plans" without new code.
- MCPVault (MIT) as the single vault MCP server; Smart Connections plugin is now under a proprietary licence.
- Laya fine-tuning pitfalls from open issues: 4-epoch default collapses on small datasets (#963); custom
  checkpoints not yet servable through the Router (#919).
- GPU broker: concrete unload endpoints (Ollama `keep_alive: 0`, ComfyUI Manager `POST /api/free`), and the
  DPC-latency reason the DJ guard matters.

**Confidence changes:** Top 10 #4 stays medium but the item now carries its failure rates. Top 10 #2 (Laya) stays
high for "measure and fine-tune"; how much it gains on your routes is unknown.

**Open:** TAU2 numbers (81.2 vs 68.2) are vendor-adjacent; no independent Hermes-specific benchmark of local models.

## Round 4 — Reel Brain + Inspiration Canvas audit (02:19–02:21 UTC)

**Attacked:** the Ollama-penalty explanation for looping JSON, frame budgets, VLM licences, repo linking,
GPU load per reel, the Instagram export path, JSON Canvas as a storage format.

**Strengthened:** a second Ollama issue (#15783) confirms the Go sampler drops all three penalties
(`repeat_penalty: 5.0` ≡ `1.0`), and Ollama runs Qwen3-VL on that engine since 0.12.7.

**Added a likelier, cheaper cause:** image-token overflow. ~2,000 tokens per full-resolution vertical frame; Ollama
#13084 shows Qwen3-VL producing garbage past `num_ctx`. The first step of Top 10 #3 is now "log prompt tokens,
downscale frames", before switching servers.

**Changed:** repo linking gets a first tier that reads explicit `owner/repo` strings from OCR/caption/transcript
before any search. Reel Brain gets "call the VLM only when frames add information". MiniCPM-V 4.5 weights are under
a custom licence (registration for commercial use): fine for personal use.

**Unverified:** the exact file name of saved posts in Instagram's JSON export (no source found; inspect the ZIP).
JSON Canvas spec confirmed by reading it (file/text/link/group nodes).

## Round 5 — whatstheID audit (02:21–02:23 UTC)

**Attacked:** rb2serato on Windows, Rekordbox dynamic grids, phrase/cue detection, stretch-robust fingerprinting,
whether sharing the tool makes sense, competitors.

**Verified in source code**
- rb2serato's encoders (`seratotags.py`) are pure Python and support multi-marker grids; only the file-swap and path
  helpers are macOS-specific. Top 10 #10's risk is now narrowly "write a Windows-safe writer".
- pyrekordbox writes Rekordbox XML `TEMPO` elements (`Track.add_tempo`), i.e. tempo-change grids.

**Added**
- CUE-DETR (MIT) + EDM-CUE dataset: phrases are mostly 16 then 8 bars, not 32. Useful for auto-cues in whatstheID and
  for drop/phrase priors in Creative Studio.
- PeakNetFP is CC BY-NC-SA 4.0: personal use only.
- Lexicon's free tier already converts libraries between DJ apps: don't rebuild that.

**Killed:** nothing this round. The weakest whatstheID item is still the visualiser advice (design opinion, no
evidence), and "share it with other DJs" (crowded field, legal exposure from downloading). Both stay low priority.

## Round 6 — cross-project audit (02:23–02:24 UTC)

**Attacked:** whether the shared GPU broker needs custom code, how the pieces fit together, and my own bias toward
adding things.

**Killed or reversed**
- **"Write a GPU broker (SQLite lease table, FastAPI)"** → replaced by llama-swap (MIT, WinGet), which already
  manages llama-server, whisper.cpp, stable-diffusion.cpp and ComfyUI (dedicated `/comfyui/` endpoint) in exclusive
  groups, with an unload API and TTLs. Only the DJ guard (~30 lines) is new code. Effort 1–2 days → 0.5–1 day.

**Bias check.** Every round so far added tools. The thing most likely to sink these projects is not a missing tool
but spread: five projects plus a fork of a fast-moving editor, one person, one GPU. Added "The blunt version" at the
top of the report with the stop/start calls (no canvas app, no public whatstheID, no generated footage in paid
clips, Laya fixed or removed, heavy coding stays on Claude Code).

**Added:** one small labelled set per project, kept in the vault, as the shared measuring stick.

**Consistency fix:** Hermes (Top 10 #4) now points at llama-swap so it doesn't hold the card outside the shared
scheduler.

## Round 7 — money audit (02:24–02:26 UTC)

**Checked:** YouTube Partner Program country list (Egypt included), Instagram/Facebook monetisation (Egypt not
confirmed for either), Payoneer fees (~1 % + ~1.85–2 % FX), Upwork fees (variable 0–15 %, $0.99 local bank
withdrawal), Fiverr (20 %, Payoneer-powered bank payout), InstaPay caps, Gumroad/Lemon Squeezy payouts, card limits
for paying for cloud tools, competitor prices on Fiverr, Upwork, Khamsat and a Cairo agency (Arabic searches).

**Killed or reversed**
- **"Event clip packs for the collective" as the first *income*** → kept as path 1 but reframed. Local reel editing
  is priced at $5–50 on Khamsat and as low as 100 EGP; shoot packages from EGP 3,000. It is a portfolio and network
  play that pays modestly. The pitch changed from "AI clips" to "next-morning delivery", the thing automation buys.
- **"Sell whatstheID / a DJ tool"** → demoted to last. Gumroad's PayPal payouts reportedly exclude Egypt, Lemon
  Squeezy's bank list for Egypt is unverified, Lexicon's free tier already converts libraries, and the tracklist
  space is crowded.
- **"Your own clip channel as income"** → portfolio only. Content ID claims on other artists' tracks plus no
  TikTok/Instagram creator payouts in Egypt.

**Added:** Fiverr podcast-shorts gigs at $10–45 per clip (~736 services in one category): generic clipping is a
race to the bottom; Egyptian-dialect captions are the differentiator. Agent-setup gigs ($50–200) as a cheap test.

**Unverified:** Upwork Direct-to-Local-Bank in EGP for 2026; current InstaPay caps; Instagram creator monetisation in
Egypt; any real price a Cairo collective has paid for clips (no source exists; the first test produces it).

## Round 8 — link and claim check (02:26–02:32 UTC)

**Method:** extracted every URL from the report; opened GitHub pages for stars and issue states (WebFetch works for
github.com, not for most other hosts); shallow-cloned repos for last-commit dates and licence files; read PyPI JSON
for licence expressions; re-searched any number I could not trace.

**Killed or reversed**
- **Top 10 #3's premise.** Ollama #15783 (penalties ignored) was **closed in July 2026, "obsoleted by the switch to
  llama-server in 0.30.0"**. The move is now "fix the looping JSON at the source": image-token overflow (Ollama
  #13084, open, reproduced on an RTX 3080 under Windows, the same card family and OS as yours), greedy decoding and
  4-bit quants (QwenLM/Qwen3-VL#1611), plus a GLM-4.6V-Flash A/B. Ollama's #10929 (thinking + format) is also closed.
- **"~36 tok/s at --n-cpu-moe 24 on a 3060"**: could not trace it to a source. Replaced with traceable reports
  (28–47 tok/s on a 3060 with 32 GB DDR4).
- **Adoption reality check** (stars): rb2serato **1**, juspay/dopamine **1**, Cutcast **1**, podcast-editor **0**,
  QwenCleo-ASR **19**, CUE-DETR **32**, serato-tools **31**. Each now carries that caveat; rb2serato's confidence
  text was rewritten ("one author's month-old project; round-trip every write through two parsers").

**Confirmed**
- Beat This weights MIT (#16); Giant Steps numbers (#13); Hermes issues #110442, #129440, #29677 as described;
  whats-now-playing's `history_entry` query; JSON Canvas node types; Hermes local-models doc text.
- madmom: BSD code but **CC BY-NC-SA 4.0 models** (read the LICENSE file).
- serato-tools: MIT via PyPI `license_expression`, Python ≥ 3.12.

**Restored:** links to FunClip, Cutcast and podcast-editor that the round-7 money rewrite had dropped.

**Added:** a repo-facts table (stars, last commit, licence, Windows/12 GB fit) and a full source list to the report.

**Still unverifiable from here:** Hugging Face model cards (Qwen-Image 2.1, MiniMax H3, GLM-4.6V-Flash, MiniCPM-V
4.5), arXiv full texts, dev.to. Claims that depend on them are marked in the "Still uncertain" table.

## Round 9 — deep dive, prototypes, first-week plan, steelman (02:33–02:48 UTC)

**Built and tested six prototypes** in `research/prototypes/` (synthetic tests, all pass):
reference-clip analyser, VLM JSON guard, Serato set grid (history + alignment), L1 reframing path, DJ guard, Laya
evaluator/exporter; plus a llama-swap config that parses.

**What building them caught (each would have been a wrong instruction in the report)**
- **librosa's tempo is quantised to its frame grid**: a 150 BPM test clip read as 152. Least-squares over beat
  numbers fixed it, but only after a second bug: numbering beats from the first one with the quantised period drifts
  a whole beat in under a minute. Number interval by interval. (Same trap whatstheID's notes describe.)
- **Kick-band features can't align a track inside a mix**: a four-on-the-floor kick is periodic, and DJs cut the
  incoming bass anyway. Alignment now uses 150 Hz–8 kHz onsets; it recovered a 3 % speed-up exactly and the offset
  to 15 ms through a bass-cut blend with noise.
- **Strobes are cuts to a content detector, and PySceneDetect's adaptive detector didn't fix it**: my first
  "strobe-safe" mode still found 17 cuts for 7. A before/after persistence check (a flash returns to the same
  picture) fixed it: plain detector 9, strobe-safe 7. Without this, the reference measurements on club footage would
  have counted strobes as edits.
- **Phrase position needs an anchor.** Counting 8-bar phrases from the first detected beat is arbitrary; counting from
  the drop is what club tracks do.
- **L1 path works as claimed on synthetic data**: 84 % static, 0 direction changes, subject always in frame; a
  moving-average follow changed direction 189 times.

**Steelman results:** AudD's enterprise endpoint **wins** as whatstheID's cloud fallback (documented, ~$0.12–0.30 per
mix, measured better than Shazam on your records) and moves into the report. Resolve Studio 21.1 (native MCP, $295)
becomes the named fallback renderer, not the primary. Dropping Laya wins only if you won't label. A cloud video model
for the Reel Brain backlog is a conditional test. A tldraw canvas app stays rejected.

**New facts:** Resolve 21.1 moved Python scripting to Studio and added a native MCP server; FLUX.2 klein 4B file
layout from the ComfyUI tutorial (gated download, accept BFL licence); GLM-4.6V-Flash is listed by LM Studio with
vision and tools; Laya's training rows are `{state, questions, gold}` (corrected in round 15: `gold` is teacher probabilities; plain labels go in `expected`).


## Round 10 — coverage check against the brief (02:48–02:55 UTC)

**Attack:** re-read the brief line by line and asked "which research bullet did the report skip?"

**Gaps found and filled**
- Creative Studio had no view of **what already exists** in open-source auto-editing. Added a landscape table
  (OpenMontage, HyperFrames, FunClip, auto-editor, podcli, beat-synced-edit, Cutcast/podcast-editor) with stars and
  licences. Finding: nothing edits DJ-set footage from Serato data, so Creative Studio is not duplicating a project.
- whatstheID's beat-tracker advice was scattered. Added one comparison table with the only numbers that exist for
  electronic music (your comb filter, Beat This on Giant Steps, madmom's downbeat weakness on EDM per Raveform,
  All-In-One, librosa's quantisation).
- Reel Brain lacked "how do others build save → second brain". Added a paragraph (Dopamine, a ColdIQ guide,
  Karakeep, your own vault pattern).

**Kills:** none. **New watch item:** Raveform's GitHub repo held only a licence file on 2026-10-14; the paper's
models are not usable yet.

**Confidence changes:** none.

## Round 11 — fit, VRAM and Windows install pitfalls (02:55–03:01 UTC)

**Attack:** for every recommended piece, "what happens the first evening you install it on Windows 10 with 12 GB?"
Read install docs and source (Hermes platform pages, faster-whisper README, QwenCleo README and server, qwen-asr on
PyPI, Beat This preprocessing, rtmlib, ctc-forced-aligner, whisperX alignment table, llama.cpp releases,
llama-swap config reference) and redid the VRAM arithmetic for Qwen3.6-35B-A3B.

**What broke**
- **Egyptian-Arabic captions had no timing step.** QwenCleo returns text only; Qwen3-ForcedAligner covers 11
  languages and Arabic is not one. Money path 2 (animated Arabic captions) silently depended on it. Added a
  forced-alignment step: ctc-forced-aligner (BSD-2) with an Arabic wav2vec2 model, because **its default MMS
  model is CC BY-NC 4.0** (stated in its README). Code-switched English words will need interpolated times.
- **The example llama-swap config would probably have run out of VRAM.** By arithmetic (40 layers, ~0.49 GB of
  Q4_K_M experts per layer, ~1.5 GB non-expert weights, ~1.3 GB KV at 64K because only 10 layers are full
  attention, ~0.5 GB logits buffer for a 248K vocabulary), `--n-cpu-moe 22` needs ~12.5 GB. Measured reports
  agree: InsiderLLM's best on a 3060 was 24 (38.9 tok/s) after retracting "20 is fastest"; a user ran 26 with
  UD-Q4_K_XL at ~45 tok/s. Config now uses llama.cpp's `--fit` (default on) with a 1.5 GB margin and `-np 1`.
- **The 46.8 tok/s at `-ncmoe 18` figure** from the May r/LocalLLaMA sweep can't be a Q4_K_M on 12 GB; demoted.
  Speed range is now ~35–45 tok/s. The 3080 Ti's bandwidth advantage doesn't apply to experts in system RAM.
- **"Needs 32 GB RAM" was too strong**: one user reports 16 GB working with `-np 1`. Softened to "32 GB
  comfortable; 16 GB only with nothing else open".

**Strengthened**
- Top 10 #3: Ollama's documented default context on cards under 24 GB is **4K tokens**; three full-resolution
  frames overflow it. If Reel Brain doesn't set `num_ctx`, this alone explains the loops. Confidence stays medium
  only because Reel Brain's code isn't on GitHub.
- Hermes runs natively on Windows 10 (Tier 1, `install.ps1`) and refuses local endpoints under 64K context, so the
  Ollama 4K default can't bite Hermes, only Reel Brain.

**Added:** a Windows install-pitfalls table in 1b (cudart zip, CUDA 13 driver floor, `--fit`, Ollama 4K default,
Hermes 64K floor and Git Bash, faster-whisper DLLs, QwenCleo without vLLM, onnxruntime-gpu CUDA 13 wheels,
torchaudio → TorchCodec, FP8 on Ampere, DJ guard process names); `asr-eg` (QwenCleo's FastAPI server) as a
llama-swap model; ctc-forced-aligner in the sources table; three rows in "Still uncertain".

**Kills:** the fixed `--n-cpu-moe 22`; the 46.8 tok/s figure; "QwenCleo covers captions".

**Confidence changes:** Top 10 #4 stays medium (speed evidence better, `--fit` on Windows untested).
Money path 2 gets one more day of work before the first proposal.

## Round 12 — contradictions (03:01–03:03 UTC)

**Attack:** read the report against itself: same component, different advice in two places.

**What broke**
- **Round 8 over-corrected on Ollama.** #15783 (penalties ignored) was closed as "obsoleted by the switch to
  llama-server in 0.30.0", which doesn't confirm penalties work. The umbrella issue
  [#14493](https://github.com/ollama/ollama/issues/14493) is **still open**, with June–September 2026 reports that
  Ollama's stock Qwen 3.5 renderer misses tool calls (v0.30.7: 2/5 relay calls, 4/5 with a `qwen3-coder`
  renderer override). Fix: Day 2 diagnoses on Ollama, Day 3 reruns the same reels on llama-server to rule Ollama
  out; Top 10 #4 now says not to move Qwen3.5/3.6 onto Ollama.
- **Top 10 #4 led with Hermes' managed llama.cpp runtime while #6 put every GPU server behind llama-swap.** Two
  runtimes would mean two GPU owners. Now explicit: your own llama-server behind llama-swap.
- **Three models where one or two would do.** Creative Studio's planner was Qwen3.5-9B, Hermes ran
  Qwen3.6-35B-A3B, Reel Brain a separate VLM. Qwen3.6-35B-A3B has its own vision projector, so the planner is now
  the agent model, the defect checker is Reel Brain's VLM, and the agent model joins Reel Brain's A/B: if it ties,
  one loaded model serves all three and nothing swaps. Added as cross-project piece 7; the YAML has a commented
  `--mmproj` line.
- **Beat This:** the models table said `final0`, the prototype and the Giant Steps evidence say small models; now
  `small0` everywhere.
- **"The first week touches only Creative Studio, Hermes/Laya and the GPU setup"**, while Day 2 is Reel Brain and
  Day 6 is a set grid. Reworded.
- Leftovers: "GPU broker" (killed in round 6) still appeared in Reel Brain; "Ollama issue above" pointed at
  nothing; EmbeddingGemma was listed as Laya's model (it's the baseline).

**Kills:** the separate planner model; the managed runtime as the recommended path.

**Confidence changes:** Top 10 #3 stays medium; the Ollama-vs-llama-server rerun on Day 3 now settles the server
question within the first week.

## Round 13 — money: hidden costs and demand evidence (03:03–03:06 UTC)

**Attack:** "what does this cost you in Cairo that the report never priced?" and "is there evidence anyone pays
for DJ clips, or did I assume it?"

**What broke**
- **No hidden-cost accounting.** Added a table: ≈ 100 GB of downloads in the first two weeks (against WE home
  tiers of 140 GB–1 TB/month, aggregator data), ≈ 100 kWh/month if night batches run every night (≈ EGP 170–240 at
  the post-August-2026 brackets), Upwork Connects ≈ $10–25 for path 2's test, Payoneer's annual fee, paid tools only
  if they win, and your time.
- **Round 10's "Creative Studio is not duplicating an existing project" was too strong.** DJ-set clippers exist:
  markus' `dropspace-dj-clipper` (MIT, 9 stars; energy peaks, centre crop, Shazam every 30 s, Whisper lyric matching)
  and SendShort's paid DJ-mix tool (audio → waveform clips). Neither uses Serato history, keeps the DJ in frame or
  cuts on bars, so the differentiation holds, but the sentence now says so precisely.
- **Money paths missed the most direct sale of Creative Studio's output:** clip packs for DJs abroad. Evidence is
  thin (one Fiverr DJ-set editor at $50–100 with reviews; beginner short-form rates $25–75 per clip; no dedicated
  DJ-clip service found), so it enters as path 3 with a one-week test, replacing "your own channel" (folded into
  path 1 as a portfolio note).

**Still weak:** no Reddit/forum thread where DJs say they'd pay for clips (search returned none). The first test is
the evidence.

**Kills:** "own clip channel" as a separate money path.

**Confidence changes:** money path 3 enters at low (demand thin); hidden-cost figures medium (aggregator and news
sources, not bills).

## Round 14 — bias check (03:06–03:08 UTC)

**Attack:** "where does the report agree with you, or with me, for reasons other than evidence?" Five biases
checked:
1. **Verification bias** (favouring what I can read on GitHub). Commercial tools were under-weighted. For Arabic
   captions, **ElevenLabs Scribe** returns Arabic word timings, lists Egyptian among its accents and costs
   ~$0.40/audio hour; it may beat a day of aligner work for paid clips. Added as a paid A/B. **Submagic and Opus
   Clip** sell Arabic auto-captions to the same clients money path 2 targets; the report claimed an Egyptian-dialect
   edge it had never measured against them. Added a one-clip comparison as the first step of path 2.
2. **Sunk cost toward your stack** (FilmCraft fork, Hermes, Laya). Tested FilmCraft's fit instead of assuming it:
   `filmcraft-cli mcp` runs headless with an in-process session, and `file.exportMedia` already takes h264, any
   width/height, CRF, loudness target, burned-in captions and hardware encoding. FilmCraft earns its place; the
   report now says to drive it headless, which sidesteps the Windows UI risk (G9). Laya was steelmanned in round 9.
3. **Automation bias** (building before selling). Money path 1's first test now says to cut the first free pack by
   hand if the pipeline isn't ready: the test is demand, not automation.
4. **Recency bias.** Several picks are months old with few users (rb2serato 1 star, QwenCleo 19, markus 9,
   GLM-4.6V-Flash new). Each already carries a low-star warning and a fallback; no change.
5. **Measurement bias** (always "measure first"). Each measurement step is ≤ 1 day and the first week ends with a
   pitch, so it doesn't stall shipping; no change.

**Kills:** none. **Additions:** Scribe row in the models table; headless FilmCraft export recipe; competitor check
in path 2; an uncertainty row on the caption edge.

**Confidence changes:** money path 2 moves from medium to low until the competitor comparison is done.

## Round 15 — second link and claim check (03:08–03:16 UTC)

**Attack:** every link added since round 8, and re-read the issues the top 10 leans on.

**Links:** all 49 GitHub repos resolve (`git ls-remote`); every GitHub blob/tree path checked against a clone;
new non-GitHub links came from today's search results. One failed: the "DigitalWorkflowCompany/resolve-mcp, 88
tools" listing could not be found again; replaced with a Glama listing that exists (irstone-source/resolve-mcp,
MIT, 295+ tools) and the range "53 to 295+ tools" across listings. Puget's and Digital Production's Resolve 21.1
articles, AudD's enterprise docs and tldraw's agent kit all confirmed.

**What broke (Laya, Top 10 #2, two errors including one backwards)**
- **Epochs: I said "fewer epochs on small data"; the issue says the opposite.** Laya #963: the fixed 4-epoch
  default gives a small dataset too few optimizer updates and the head collapses to the class prior; the reporter's
  useful epoch was 17–31, and 6 of 15 identical runs never left the plateau. Fixed: read the update budget from
  `--dry-run`, raise `--epochs`, repeat with seeds, use the positive control from `docs/finetune.md`.
- **Router: I said custom checkpoints can't be served through the Router (#919).** They can since 0.3.28
  (`Router(models=...)`, `Router.register`) and `laya-serve` reads `LAYA_EXTRA_MODELS` since 0.4.1; only routing by
  content is still open.
- **Missed tool:** Laya 0.4 ships `laya-train`, a one-command fine-tune from a CSV on one device (CUDA, CPU, MPS)
  that also fits calibration and abstention thresholds. Kaggle is no longer needed, so messages never leave the PC.
  `--loss soft-ce` beat the default on Laya's own benchmark (0.790 vs 0.772). Confirmed `laya` 0.4.6 on PyPI.
- **Prototype bug:** `laya_eval.py --export-rows` wrote `gold: {qid: label}`; in Laya's format `gold` is teacher
  probabilities and plain labels go in `expected`. Fixed, added `--export-csv` for `laya-train`, test extended
  (CSV row count, Arabic text survives); all six prototype tests pass.

**Confirmed unchanged:** Hermes #110442 (rename PR #110452 still open), #129440 (1 of 23 figure is in it, one
install over ~1 day), #29677 (open; workaround from a commenter, not a maintainer), Ollama #14493 (open).

**Confidence changes:** Top 10 #2 stays high and gets cheaper (no Kaggle, no export format to hand-build).

## Round 16 — whatstheID and Inspiration Canvas (03:16–03:19 UTC)

**Attack:** does Top 10 #10 (Serato write-back) work for *your* case, and are the canvas import routes real?

**What broke**
- **Top 10 #10 only covered tracks Serato imports fresh.** rb2serato's flow relies on Serato 4 re-importing
  `database V2` and crates at start-up (Serato closed while writing). Nobody documents whether Serato 4 re-reads a
  rewritten `Serato BeatGrid` tag on a track already in its library; serato-tools edits `database V2` precisely so
  metadata changes appear "without Reload ID3 Tags", which suggests caching. whatstheID's use is exactly that case.
  First step now tests both (a copy, and a known track) on a backed-up library.
- serato-tools: dynamic (multi-marker) grids from a librosa analysis (source MIT, heyitsmass/audio); it edits
  Serato 3's `database V2`, not Serato 4's SQLite. Noted.
- **Audit-log context said the fingerprint speed ladder is ±4 %; the code says ±8 % in 1 % steps.** Fixed (the
  report already said ±8 %).
- **Reel Brain:** the "use Instagram's export" advice is unverified at field level (third-party guides only) and the
  fetch step needs throttling if yt-dlp uses your cookies. Added both.

**Kills:** none. **Confidence changes:** Top 10 #10 stays medium but its effort estimate is now conditional.

## Round 17 — security, and FilmCraft's Arabic captions tested (03:16–03:21 UTC)

**Attack 1, security:** Reel Brain writes strangers' text (captions, transcripts, OCR) into the vault; Hermes reads
the vault with a shell, MCP tools and a Telegram front door. Added cross-project piece 8: `TELEGRAM_ALLOWED_USERS`,
`approvals.mode` smart/manual (never `/yolo` on the gateway), `cron_mode: deny`, a `--read-only` MCPVault instance
for agents that only read, reel notes in their own folder marked untrusted, and "a repo from a reel is a lead, not
an install". All of these are documented features (Hermes `security.md`, MCPVault README).

**Attack 2, test instead of trusting a bug title:** built the fork's `filmcraft-cli` (release, 5 min) and burned an
Egyptian code-switched caption into a headless export.
- Default caption font (Inter): every Arabic letter is a "NO GLYPH" box, **even with Noto Sans Arabic installed**:
  the fallback only searches bundled/craft-fonts/already-loaded faces. Matches upstream #1475 (open; fix PR #1478).
- `captions.setStyle {"font": "Noto Sans Arabic"}`: correct output (joined letters, right-to-left order, the Latin
  word at the left end).
- **Reversed:** "render Arabic in the HTML layer because FilmCraft can't" (from #395's title; its merged fix #1140
  was UI-only). Now: name an Arabic face on the caption track. Committed the run script as
  `prototypes/filmcraft_arabic_captions.jsonl` (re-run from that file: identical output). The two frames are not
  committed (the fork's asset gate requires licence sidecars for images); they go with the hand-back.
- Also confirmed: `file.exportMedia` takes h264 / width / height / CRF / `loudnessLufs` / `burnCaptions` /
  hardware encoding, and `filmcraft-cli run` executes a JSONL command script headless. The fork is 433 commits behind
  upstream as of 2026-10-13.

**Confidence changes:** Arabic captions in FilmCraft: low → high (tested). Top 10 #8 unchanged (still low: taste).

## Round 18 — Creative Studio deep dive: the planner → FilmCraft seam, built and tested (03:22–03:35 UTC)

**Attack:** the report told you to have an LLM plan drive the FilmCraft fork, but nothing had shown the fork can
take a plan and produce a 9:16 clip with cuts, reframe, captions and audio. Built it instead of asserting it.

**Built:** `prototypes/plan_to_filmcraft.py`: an MCP client for `filmcraft-cli mcp` (stdio JSON-RPC) that turns a
plan JSON into a sequence and an export. `test_plan_to_filmcraft.py` runs it against the real release build of
your fork with two synthetic cameras, a set recording, noisy and gappy subject detections and an Arabic/English SRT.
Result: 1080×1920, 270 frames, cuts on frames 90/135/225 exactly, audio present, captions burned in, subject
fully in frame on 100 % of reframed frames (centre crop: 34 %), 8–14 keyframes per shot.

**What testing found that reading didn't**
- Motion `anchor` is in source pixels and `position` in sequence pixels: a reframe is anchor keyframes, nothing else.
- `effects.setKeyframe` only edits existing keyframes; `effects.setParam {"keyframe": true, "time": ticks}` creates
  them. A static `filmcraft-cli run` script can't use the IDs commands return, so drive the MCP server.
- **My keyframe reducer was wrong:** keeping only frames where the slope jumps gave a smooth curve two keyframes
  and the subject left the frame mid-shot. Replaced with Douglas–Peucker (≤ 3 px error).
- **My L1 prototype's default margin was wrong for bodies:** the path constrains the subject's centre, so a 60 px
  margin let a 160 px-wide subject clip the frame edge on 9 % of frames. Margin now = half the subject's width +
  20 px (`--subject-width`, default 200 px), in both scripts.
- The test runner now accepts SKIP (no FilmCraft build on the machine); all seven tests pass here.

**Report changes:** Top 10 #9 gets the FilmCraft side and the margin pitfall; 2.1 gets the seam as an adopted
piece; "write the plan as OTIO" became "keep the plan tool-neutral JSON; use FilmCraft's `file.exportOtio` for the
Resolve fallback" (OTIO can't carry the keyframes and captions the plan needs); week 2 starts with a real clip end
to end.

**Confidence changes:** "an LLM plan can drive the fork" from assumed to tested on synthetic footage (medium →
high for the mechanics; footage quality still untested).

## Round 19 — GPU sharing tested against the real llama-swap (03:35–03:44 UTC)

**Attack:** Top 10 #6 and Day 3 rest on a config and a guard that had never met a running llama-swap (the binary
couldn't be downloaded in round 9). Built llama-swap from source (Go toolchain in the container) instead.

**Confirmed:** `-validate` passes on the committed config; with stand-in servers in place of llama.cpp/ComfyUI:
the exclusive group keeps one model loaded (asking for `vlm` unloads `agent`), `/comfyui/` loads `comfyui_auto`,
`POST /api/models/unload` empties it, `/v1/audio/transcriptions` with `model=asr-eg` reaches the QwenCleo entry.

**What broke**
- **The DJ guard made things worse in one case.** Pointing its ComfyUI "free" call at llama-swap's `/comfyui/`
  route *started* ComfyUI, so DJ mode ended with ComfyUI on the GPU. (The flag's help said "outside llama-swap",
  but nothing stopped the obvious misuse, and I made it myself.)
- **Nothing stopped a model reloading mid-set.** Unload alone lasts until the next Hermes message or batch item.
  The report said the guard "stops the llama-swap service", but Day 3 ran it without stop commands.
- **Fix, tested:** a `dj` profile in the llama-swap config with every pin null (models answer 404 while it is
  active; found in llama-swap's config reference), switched by `PUT /api/profiles/active`; the guard re-unloads
  anything that loads anyway (the `/comfyui/` route ignores profiles), and clears the profile on exit. No service
  stop/start needed. New `test_dj_guard_llama_swap.py` runs all of it against the real binary (SKIP without it);
  the fake-server unit test covers the same calls.
- Test hygiene: a leftover llama-swap held the port and silently answered a later test; the real-binary test now
  picks a free port and tears everything down.

**Confidence changes:** Top 10 #6 stays medium (Windows, DPC latency and thermals untested) but its mechanics are
now tested rather than read.

## Round 20 — whatstheID: Serato tag format and licences (03:44–03:46 UTC)

**Attack:** before writing a Serato grid writer, check that the encoder you'd vendor writes what Serato and the
other parser expect, and what licences the write path drags in.

- **Footer byte:** Holzhaus' format notes and serato-tools describe a one-byte footer after the `Serato BeatGrid`
  markers; rb2serato's `encode_beatgrid` writes none, yet claims byte-for-byte fidelity. Checked its real Serato MP3
  fixture: 14 bytes, one marker, **no footer**, so rb2serato matches at least that Serato version, and serato-tools'
  parser tolerates a missing footer. No change; noted so it doesn't surprise you in a hex dump.
- **Licences (PyPI metadata):** mutagen is **GPL-2.0-or-later**; whatstheID's `app/tags.py` uses it and serato-tools
  requires it. Everything else in whatstheID's requirements is permissive (yt-dlp Unlicense, shazamio MIT, librosa
  ISC, FastAPI/uvicorn/pydantic MIT/BSD). Added to the report: fine for personal use; share whatstheID under a
  GPL-compatible licence or replace mutagen; keep tag-writing code out of the MIT/Apache fork. For the same reason I
  did not add a Serato writer prototype to `research/prototypes/` (it would need mutagen); it belongs in whatstheID.
- Prototypes' own dependencies checked: all permissive; stated in the prototypes README.

**Kills:** the plan to add a Serato grid writer prototype to the fork. **Confidence changes:** none.

## Round 21 — Hermes + Laya: what the tools already ship (03:46–03:48 UTC)

**Attack:** "your router logs decisions for later fine-tuning", so does Laya or Hermes already ship that loop, and
can a route actually change anything inside Hermes?

- **Laya ships the loop.** `docs/staged-adoption.md`: shadow with prediction hooks (`Router(hooks=[...])`,
  `on_predict_end`), compare against the incumbent, set the threshold from held-out data, promote one route at a
  time. `laya-evals run … --slice language --max-ece … --json` plus `laya-evals compare --baseline` records the
  checkpoint, dataset hash and thresholds, so a before/after is honest. Its dataset rows are the
  `{state, questions, expected}` rows `laya_eval.py` exports; the export now adds a `language` tag (ar / en / mixed),
  so Arabic and English routing are scored separately. Test extended; passes.
- **Hermes can't switch models from a plugin.** `pre_llm_call` only injects context and `pre_tool_call` only
  blocks/approves (plugin docs). A route has to act in front of Hermes. Added the payoff that matters on 12 GB:
  route to Hermes profiles with trimmed toolsets, since the fixed prompt's prefill dominates the first turn on
  low-VRAM setups (Hermes' local-setup guide, now quoted exactly) and recurs after every llama-swap swap.
- **Hermes' auxiliary slots** (compression, vision, approval scoring, MCP routing, titles, skill search, curator)
  default to the main model; keep them there so side-jobs don't swap models.
- **Claim tightened:** "prefill dominates first-token time on local models" was a paraphrase; the source says "the
  first turn" on CPU-only or low-VRAM setups. Both mentions now say that.

**Kills:** none. **Confidence changes:** Top 10 #2 stays high; it now ends in a measured promotion step instead of
"keep whichever wins".
