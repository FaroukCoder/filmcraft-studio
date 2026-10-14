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

## Round 22 — Reel Brain: repo linking built and tested (03:48–03:52 UTC)

**Attack:** the report's three-tier repo linking was prose. Built it (`prototypes/repo_linker.py`) with an offline
test of the failure modes that produce false matches.

**What the test caught:** my first weighting (name 0.45, owner 0.15, description fit 0.30) let a closed SaaS through:
"Gamma" (slides) matched `gamma-ray/gamma` on name + owner with nothing in common with the reel. That is the exact
false-match pattern Reel Brain has. Reweighted so the description fit carries a match (name 0.35, owner 0.10, fit
0.45, stars 0.10, accept 0.55): name + owner alone can't pass. Owner matching also needed a length guard.

**Covered:** explicit links (trailing punctuation, OCR typos fall back to search), Hugging Face links, `owner/repo`
only next to a cue word ("24/7", "and/or", "50/50" ignored), `pip install` / `npm i` captured, forks lose to
originals, Whisper-split names ("lang chain"), substrings rejected ("Rez" ≠ "Rez Band"), empty names refused,
near-ties returned as "ambiguous".

**Not verified:** live GitHub/HF API calls (blocked from this container); precision on your reels (the first step
now measures it on the same 50 reels as the blind re-label).

**Confidence changes:** Reel Brain repo linking stays medium (logic tested, real-data precision unknown).

## Round 23 — the two licence claims nobody had read at the source (03:52–03:53 UTC)

**Attack:** Top 10 #1 rested on secondary write-ups because Hugging Face is blocked from my fetch tool. Searched for
the primary text instead; the search index quotes the official pages.
- **Qwen-Image 2.1:** the official model card says "This model is licensed under the Qwen Research License
  Agreement"; the LICENSE file says "FOR NON-COMMERCIAL PURPOSES ONLY", with commercial licences by request to Qwen.
  The 2.1-Turbo and prompt-rewriter (PE-T2I / PE-I2I) checkpoints carry the same licence. Top 10 #1: medium → **high**;
  its first step no longer needs you to read the card. Removed from "Still uncertain".
- **MiniMax H3:** model cards confirm the territory clause (worldwide except the EU, UK, South Korea and the US), so
  Egypt is inside it. The commercial terms (a US$20 M revenue cap, a duty to show "MiniMax H3" in commercial
  products) appear only in secondary sources; the uncertainty row now names exactly that.

**Confidence changes:** Top 10 #1 medium → high.

## Round 24 — re-rank the Top 10 (03:53–03:57 UTC)

**Attack:** the brief's rule: a low-confidence top-10 item gets verified or demoted. #8 (house look per client) had
been low since round 2 and can't be verified without you. Meanwhile two items gained tested evidence.

**Changes (old → new number):** 1 → 1; GPU sharing 6 → **2** (it enforces a hard constraint of yours and is now tested
against the real binary); Laya 2 → 3; VLM JSON 3 → 4; **new #5: wire the planner to the fork headless and build it
with craft-fonts** (the tested seam from round 18, 1 day, high for the mechanics); reference clips 5 → 6; Hermes on
llama.cpp 4 → 7; set grids 7 → 8; reframe 9 → 9; Serato write-back 10 → 10. **House look demoted** to a paragraph in
2.1 (content kept; still low confidence). The Arabic-caption finding moved into #5. Every "Top 10 #N" reference in
the report, the first-week plan and the prototypes (README table, docstrings, YAML) was renumbered; the old numbers
in earlier audit-log entries are left as written.

**Also fixed:** the report's status line still said "round 1 draft"; the blunt version now says what's tested (the
FilmCraft seam, the GPU guard). Day 5 gains the fork build; it uses a git worktree, because checking out the v0.7.2
tag would hide `research/` (it only exists on this branch).

**Open:** the seam was tested on the fork's own base (0.6.0 lineage), not on v0.7.2, which the report tells you to
sync to. A v0.7.2 build is running to re-test it.

## Round 25 — canvas imports, Cairo prices, and the bounded schema that wasn't (03:57–03:59 UTC)

- **Inspiration Canvas:** found **EaglePack Importer**, an Obsidian community plugin that turns an Eagle `.eaglepack`
  into one note per item (image embedded) plus a gallery note. Added as a lead, not a recommendation: its source
  repository and licence could not be found. Eagle's on-disk layout (`images/<id>.info/metadata.json` beside the file)
  noted from a third-party description, so your own exporter stays a small fallback.
- **Money, local prices:** searched in Arabic and English for Cairo event-reel prices in EGP. Nothing new: Khamsat
  listings stay at $5–40 per reel, and the "Cairo videographer prices" pages are a US agency's SEO pages in dollars,
  not local rates. No change; path 1's first test (three local quotes) stays the evidence.
- **What broke — Top 10 #4's "bounded schema":** llama.cpp's grammar docs say `maxItems` / `maxLength` are enforced
  but **nested `$ref`s are broken (#8073) and unsupported parts are skipped silently**. Pydantic emits nested `$ref`s
  for nested models and enums, and `vlm_json_guard.py` was sending exactly that (ReelNote → Tool → ToolKind), so the
  tool list's bounds could silently not apply. Fixed: refs are inlined before the schema goes out; the test now fails
  if any `$ref`/`$defs` remains and checks the enum and `maxItems` survive. Report updated.

**Confidence changes:** Top 10 #4 unchanged (medium), but one of its four fixes would have silently done nothing.

## Round 26 — shot picking built, v0.7.2 re-tested, Gemini in Egypt (03:59–04:07 UTC)

**Shot picking (one of your open problems) was a proposal; now a tested prototype.** `shot_picker.py` scores each
synced angle per bar (sharpness, exposure, motion, strobe flashes; pose/taste scores pluggable) and chooses an angle
per bar by dynamic programming: cuts only on bar lines, minimum shot length, crowd on the drop bar and the next, and
a plan JSON for `plan_to_filmcraft.py`. Its test (two synthetic, offset angles at 150 BPM, one dark for 4 bars, one
out of focus for 6) passes.
- **What the test caught, twice:** with no maximum shot length the cut cost produced two 6- and 12-bar shots (not
  how club clips are cut); with a *hard* 4-bar maximum it cut to the out-of-focus angle just to obey the rule. The
  maximum is now a per-bar cost (shots run long only while the other angle is unusable); with equal scores it falls
  into 4-bar shots, i.e. cuts on phrase lines. The first test assertion was also wrong (it flagged a long shot that
  was covering the dark stretch); it now checks whether the other angle was usable for the extra bars.

**v0.7.2:** built upstream's tag with craft-fonts (8.5 min) and re-ran `test_plan_to_filmcraft.py` and the Arabic
caption script against it: identical results, Arabic renders with the default font. The advice to sync to v0.7.2
no longer rests on an assumption that the seam survives the upgrade.

**Gemini:** Egypt is on Google's official list of regions for the Gemini API and AI Studio. The Reel Brain
steelman's "unconfirmed availability" is settled; free-tier video limits remain unchecked.

**Confidence changes:** Top 10 #5 (seam) now tested on both builds; shot picking from "proposal" to "prototype,
tested on synthetic footage" (medium: real club footage untested).

## Round 27 — steelman the demoted house look; make its rhythm rules checkable (04:07–04:11 UTC)

**Attack (steelman):** round 24 demoted "house look per client" for low confidence, but it is the only item aimed at
your #1 Creative Studio problem ("output looks stock AI"). Is it demoted because it's wrong, or because it's hard
to check?

**Answer:** half of it can be checked. HyperFrames compositions declare timing (`data-start` / `data-duration`,
relative starts like `"intro + 0.5"`) and animate with GSAP timelines (read HyperFrames' composition and lint docs).
Built `prototypes/beat_lint.py`: clip starts/ends on the beat grid, `data-beat="bar"` titles on bar lines, GSAP
tween positions on beats, plus two motionmaxxing tells (in-out eased moves, typed-out text). Exit code 1 on findings,
so it drops into your motion-graphics QA step. Its test composition covers on/off-grid clips, a bar miss, relative
starts, an opt-out, an off-beat tween, an in-out slide vs an out-eased move, and a typewriter.
- **Caught while building:** a regex that stopped at the first `)` (broken by `document.querySelector("#x")`);
  replaced with a bracket-matching scanner. My test's expected offset was also wrong (150 ms, not 50).
- **The taste half stays unverified.** Added a cheap way to settle it: a blind A/B with the collective; if the
  house-look version wins, it returns to the Top 10.

**Verdict:** stays out of the Top 10 (taste is still low confidence), but it now has a tool and a test that could
bring it back.

## Round 28 — the shared batch queue the report kept asking for (04:11–04:12 UTC)

**Attack:** Top 10 #2 and Reel Brain both say "checkpoint every batch per item, retry on connection refused, wait
for the DJ lock", and nothing provided it. Long GPU runs crashing the PC is one of your stated pain points.

**Built:** `prototypes/gpu_queue.py`: SQLite (WAL, synchronous=FULL), one row per item, `running` rows requeued on
start, `dj_guard.gpu_allowed()` checked before each item, exponential backoff, parked failures with their error,
`status` for a nightly report (Hermes cron's no-agent mode can run it). Test: 9 done / 1 parked; a transient
`ConnectionRefusedError` retried once; two waits for the DJ lock; and a real hard crash (a worker process killed
with `os._exit` in the middle of an item) followed by a restart that redoes exactly that one item. Passed first run.

**Confidence changes:** none to the Top 10 (it implements #2's step 4); Reel Brain's crash pain point now has a
concrete, tested mitigation.

## Round 29 — Reel Brain classification: a measuring tool instead of a claim (04:12–04:14 UTC)

**Attack:** the report says a linear probe and top-3 will beat your 63 % kNN. That is general ML experience, not a
measurement on your folders. Built `prototypes/collections_probe.py` so you can measure it on the embeddings you
already have: kNN (1/5/15, cosine), a logistic-regression probe, the probe's top-3, an ask-me-when-unsure margin
rule, per-folder accuracy and the most-confused pairs, all under the same 5-fold CV; `--predict` gives top-3 for new
reels. Synthetic test (1,000 items, 8 imbalanced folders, signal in 16 of 256 dims, two overlapping folders): kNN
0.75–0.81, probe 0.86, top-3 0.999, the rule sends 13 % to you at 91 % on the rest, and the overlapping pair tops
the confusions. The test asserts the tool's behaviour, not that the probe wins: that is the question for your data.

**Confidence changes:** none (Reel Brain classification stays medium until it runs on your data).

## Round 30 — fast-techno downbeats (04:14–04:18 UTC)

**Attack:** "BPM/downbeat accuracy on fast techno" is one of your open problems. Tempo is solved by your comb filter
(0.01 BPM vs Serato); the report's downbeat advice was a sentence.
- **Beat This could not be run here:** its weights are served from JKU's cloud, which this container can't reach.
  Its Giant Steps numbers stay second-hand (from its issue tracker).
- **Built `prototypes/downbeat_phase.py`** (phase of a 4/4 grid from backbeat claps + structure) and tested it on
  synthetic 150 BPM techno with a breakdown, a drop and crashes, in three versions.
- **What broke, and what it taught:** (1) claps alone scored beat 1 and beat 3 identically. That isn't a bug: a
  backbeat on 2 and 4 is the same pattern shifted by two beats, so claps only separate {1,3} from {2,4}. The tool now
  reports `half_bar_ambiguous` instead of guessing, and the report says so. (2) A per-beat change vote was too noisy
  (it picked phase 3 with structure only); replaced with bar-level novelty, the standard structural cue. Result: right
  phase 6/6 seeds with claps + structure and with structure alone; claps-only flagged ambiguous 6/6.
- My first test expectation (claps alone should find the phase) was wrong for the same reason.

**Confidence changes:** whatstheID downbeats from "advice" to "prototype tested on synthetic audio" (medium).

## Round 31 — better alternatives for the agent model (04:18–04:19 UTC)

**Attack:** "search specifically for something newer, simpler or better" on Top 10 #7's model choice.

**Found:** Gemma 4 has a 12B size (Google's docs list five sizes; a guide dates the 12B to June 2026), Apache-2.0,
native function calling, 256K context. Reported ~7.8 GB at 16K context and ~90 tok/s on a 12 GB card, so it runs
entirely on the GPU: no expert offload, no RAM pressure, faster prefill (which matters after every llama-swap swap).
Hermes-specific signals favour the family: issue #29677's title says Qwen/DeepSeek output corrupts where "Gemma works
with same config", and Hermes' local guide names `gemma4:31b` its reliable tool-caller (the 31B doesn't fit 12 GB).
No published tool-calling scores for the 12B (one aggregator's TAU2 figure for the 26B-A4B was unsourced).

**Change:** added as the challenger in Top 10 #7's replay (now three-way: your current setup, Qwen3.6-35B-A3B,
Gemma 4 12B), in the models table and as a comment on `agent-small` in the llama-swap example (still validates).
Not a replacement: no evidence yet that it beats Qwen3.6 on your tools.

**Confidence changes:** Top 10 #7 stays medium; it now has a credible no-offload option if RAM or Qwen templates bite.

## Round 32 — money: can the platforms in path 3 pay you? (04:20–04:20 UTC)

**Attack:** path 3 named "Fiverr, Contra" for DJ clip packs abroad. Fiverr's payout from Egypt was verified in
round 7 (Payoneer); Contra's was never checked, and Contra pays out mainly through Stripe, which historically didn't
support Egypt.

**Found:** Contra's help pages list Stripe bank transfer, PayPal (2 % fee) and, on one page, Payoneer, for 180–200+
countries; Egypt isn't named in anything I could read. Stripe's own changelog (2026-03-25) added Egyptian recipient
bank accounts to Global Payouts, which makes it plausible but not confirmed for Contra.

**Change:** path 3 now says Fiverr is the verified route and Contra needs a test withdrawal first; added a row to
"Still uncertain". **Kills:** none. **Confidence changes:** path 3 stays low (demand evidence is still thin).

## Round 33 — contradictions, second pass: the VLM that wouldn't fit (04:20–04:22 UTC)

**Attack:** read the new material against the old, looking for advice that disagrees with itself.

**What broke**
- **Day 2 used Ollama's `qwen3-vl:8b`, which by its 6.1 GB size is a 4-bit build**, while Top 10 #4 says 4-bit
  quants loop more. Day 2 now says so on purpose (change one thing at a time) and Day 3 brings the higher quant in.
- **The higher quant I recommended doesn't fit.** Arithmetic I hadn't done: Qwen3-VL-8B at Q8_0 (~8.7 GB) +
  projector (~1.2 GB) + KV cache at 16K context (~2.4 GB: 36 layers × 8 KV heads × 128 dims × 2 × 2 bytes per token)
  is over 12 GB, and the example config gave the `vlm` entry exactly 16K at Q8. Now Q6_K at 8K context (~9 GB; 8
  downscaled frames are ~2K tokens) for both VLM entries; `llama-swap -validate` still passes. Top 10 #4 and the
  download-size table (now ≈ 90–100 GB) updated.

**Checked and consistent:** RAM/offload advice across Top 10 #7, the 2.2 models table and the YAML; the shared-VLM
piece; caption timing vs money path 2; Hermes' 64K floor vs the agent's `-c 65536`.

**Confidence changes:** none, but Top 10 #4 would have produced an out-of-memory error on its first Q8 try.

## Round 34 — Hermes already ships the vault layer (04:22–04:23 UTC)

**Attack:** "recommending what you already have is a flaw". The report sent Hermes to the vault through an MCP
server (MCPVault). Read Hermes' bundled skills: `obsidian` (filesystem-first read/search/create/edit, vault path from
`OBSIDIAN_VAULT_PATH`) and `llm-wiki` (Karpathy's LLM-Wiki, your vault's pattern) are installed by default, MIT.
Kanban tasks can run with the vault as their working directory (`dir:<absolute path>`), and Hermes' Kanban docs list
"same profile + shared dir + cron → Obsidian vault" as the long-running-journal pattern.

**Change:** Hermes uses its skills; MCPVault stays the layer for Claude Code and other agents and the `--read-only`
instance for untrusted work. Reason it matters on 12 GB: with Tool Search off (required for Qwen, Top 10 #7) every
MCP tool schema is in every prompt, while a skill is one line in the skills index until loaded. My first wording said
skills cost nothing until used; corrected to "one index line".

**Confidence changes:** none; one less moving part in Hermes' prompt.

## Round 35 — newer VLMs for short video (04:23–04:23 UTC)

**Attack:** "better alternatives" for Reel Brain's VLM at ≤ 12 GB. A broad search found research systems (Tempo,
LLaVA-OneVision-2) without local builds or comparisons: nothing beats the existing candidates with evidence.
**Found instead:** Gemma 4 12B (round 31's agent challenger) takes images in recent llama.cpp with a ~175 MB
projector (third-party model cards; one reports verified OCR), has no llama.cpp video projector yet (irrelevant:
Reel Brain sends frames), and is reportedly not supported by Ollama's projector loader yet. Fully on the card, it is
the best candidate for "one model for Hermes, the planner and Reel Brain", which would remove model swaps entirely.
Added to Reel Brain's A/B and to cross-project piece 7. No benchmark numbers claimed.

## Round 36 — the whole Creative Studio chain, end to end (04:24–04:29 UTC)

**Attack:** each prototype passed its own test, but nothing showed their seams fit (the plan JSON the picker writes,
the SRT the captions tool writes, the plan `plan_to_filmcraft.py` reads).

**Built:** `track_id_captions.py` (Serato history or aligned times → "ID: Artist – Title" SRT for the clip window;
unplayed loads skipped, sub-1.5 s slivers dropped) with a unit test, and `test_pipeline_e2e.py`: a fake Serato
`master.sqlite` → history → ID captions; two synced synthetic angles with file offsets → `shot_picker` (drop at bar
8 forces the crowd) → plan → `plan_to_filmcraft` → MP4, run against the upstream v0.7.2 build. Result: 1080×1920,
576 frames (19.2 s), cuts at frames 0/192/288 (all on the 48-frame bar grid), "ID: A – Opener" then "ID: B – Tool"
burned in, the skipped load ignored, set audio present. Looked at a frame: correct 9:16 crop and caption.
**Caught while building:** testsrc's pure-white areas could have faked the caption check; the test darkens the
synthetic angles so only captions can be pure white.

**Confidence changes:** Top 10 #5's chain is tested end to end on synthetic footage; still medium for real footage.

## Round 37 — third link and claim check (04:30–04:37 UTC)

**Attack:** every link added since round 15, plus every number in the Top 10 that rested on one source.

**Links:** all 50 GitHub repos resolve (`git ls-remote`). Issue/PR states re-read on GitHub: FilmCraft #1475 open
and PR #1478 open (a maintainer asked for per-font coverage caching on 13 Oct, and the author pushed it; note that
#1475 is titled for graphics layers, and our own test is what shows the same fallback hits burned-in captions);
Ollama #14493 open (latest reports Sep 2026, no confirmed fix for registry `qwen3.5` models); Laya #963 open
(early-stopping PR #982 awaits changes; the collapse warning and update-budget print shipped); Hermes #110442 open
(rename PR #110452 open) and #129440 open (the "1 of 23" figure is in it). Stripe's 2026-03-25 changelog does add
Egyptian recipient bank accounts (`eg_bank_account`) to Global Payouts; Egypt is on Google's Gemini API region list;
the Qwen3-ForcedAligner language list (11, no Arabic) was re-read on PyPI. Stars re-read for Laya (32.8k), OpenMontage
(68.0k, AGPL), HyperFrames (63.0k) and llama-swap (5.9k, WinGet package community-maintained). Eagle is still
US$34.95 one-time. FLUX.2 klein 4B (Apache-2.0) vs 9B (non-commercial), Z-Image-Turbo (Apache-2.0) and
Qwen-Image-2512 (Apache-2.0) all re-confirmed. Laya's README does say "the base checkpoints are near chance on
typed-decisions zero-shot" (in its Honest limits section; the top of the README says they "work zero-shot").

**What broke**
- **ElevenLabs Scribe price was stale:** the API pricing page lists Scribe v1/v2 batch at **$0.22/hour** (realtime
  $0.39); my $0.40 came from older pages. Fixed in 2.1 and the models table. Egyptian is listed among its accents;
  still no Egyptian-dialect error rate anywhere.
- **Gemma 4 12B numbers had no source in the report, and one had none anywhere.** The "~7.8 GB at 16K" is a vendor
  VRAM *calculator* (aliteq), not a measurement; the "~90 tok/s" could not be found again in any source and was
  removed. Added ggml-org's GGUF repo and the calculator as sources; the 12B's release (3 June 2026, the "Unified"
  size) is from secondary write-ups.
- **The 38.9 tok/s 3060 figure was measured on a headless card.** InsiderLLM notes a card driving the desktop loses
  ~0.5–1 GB and can OOM at `--n-cpu-moe 24`. Your 3080 Ti drives your monitors, so the report now says to start one
  or two layers higher or let `--fit` (1.5 GB target) choose.
- **The "~45 tok/s on 16 GB RAM" report was only ever read through a search snippet** (X doesn't load here), and
  the audit log never said so. Marked second-hand in the report.
- Timeline-Bench numbers now match two indexes of the arXiv HTML and the project site (26.8 % = 15 of 56, 95 %
  interval 15.8–40.3 %; 562 of 771 failed runs failed only the quality test); the interval was added.
- Audit-log housekeeping: rounds 34–36 had start times later than their end times; corrected from the commit times.

**Confidence changes:** none in the Top 10. #7 gets a Windows-specific caveat; Scribe gets cheaper.

## Round 38 — Serato write-back: what rb2serato doesn't cover, built and tested (04:38–04:53 UTC)

**Attack:** Top 10 #10 said rb2serato is "the risky half of whatstheID's 4c plan, already done". Read its writer and
serato-tools' against whatstheID's own code instead of its README.

**What broke**
- **FLAC isn't covered by either tool.** rb2serato's `tagwriter.py` handles MP3/AIFF/WAV (ID3) and M4A; serato-tools'
  writer handles `.mp3`/`.aiff` and only *reads* FLAC. whatstheID's default export format is FLAC (`config.py`). So
  for most of your files the "already done" half was not done. Serato's FLAC layout is documented in Holzhaus/
  serato-tags (MIT): Vorbis comments `SERATO_BEATGRID` / `SERATO_MARKERS_V2`, unpadded base64 with 72-char lines.
- **whatstheID has no grid anchor.** It stores BPM and cue times, not where a beat falls; `_comb_tempo` computes the
  best phase for every candidate tempo and discards it. And a 0.01 BPM error (its measured mean vs Serato) is ~27 ms
  of drift by the end of a six-minute track.
- **rb2serato's writer can't run on Windows as is:** `subprocess.run(["cp", "-c", ...])` raises FileNotFoundError
  before its copy fallback; its audio digest hashes a whole FLAC (any tag change looks like damage).
- **MP3 timing:** Mixxx's Serato importer (GPL; read for the numbers only) corrects Serato's MP3 cue and grid
  positions by −26 ms at 44.1 kHz / −24 ms at 48 kHz for FFmpeg/libmad decoding (other values under Core Audio,
  mixxx#2119). FLAC and WAV get no offset.

**Built:** `prototypes/serato_writeback.py` + test. Measured first: a comb phase on a librosa onset envelope lands a
constant 31 ms late at hop 512 (22 ms at 256, 18 at 128; ±0.5 ms across 124–148 BPM). So the anchor is refined to
each kick's attack (zero-phase 150 Hz low-pass, 50 % of the rise: −0.15 ms on synthetic kicks) and one line is fitted
through every attack, which corrects the BPM as well. Result on 180 s of synthetic techno at 132.004 BPM with rolling
16th bass, analysed as 132.0: BPM 132.004, anchor −0.04 ms at both ends; +1 BPM/min drift refused (19.7 ms rms).
Write path: rb2serato's `seratotags.py` (loaded from a path, MIT) for the bytes, mutagen for the container, copy →
tag → audio-hash check → `os.replace`, Windows "file open in Serato" handled. MP3, FLAC and WAV: audio unchanged,
grid and three cues read back by our decoder and by **serato-tools** (independent parser) for MP3 and FLAC; a
damaging write refused with the original untouched; NaN/0/1000 BPM and negative anchors refused. All 17 prototype
tests pass (llama-swap one SKIPs without its binary).

**Licence:** the write path imports mutagen (GPL-2.0+), which the prototypes README had promised to keep out of the
fork. Kept as an optional run-time import (no mutagen code, not in `requirements.txt`, anchor half runs without
it), the README now says so plainly, and the report says the script belongs in whatstheID.

**Confidence changes:** #10 stays medium (nothing has been loaded by Serato), but its premise is corrected and its
first step now covers FLAC, a known track, and the MP3 offset. Three new rows in "Still uncertain".

## Round 39 — the grid and phrase code meets a real kick (04:53–05:03 UTC)

**Attack:** rounds 30 and 38 validated `downbeat_phase.py` and `serato_writeback.py` on synthetic audio only. Found
real electronic audio this container can reach: Essentia's test-audio repo on GitHub (`recorded/techno_loop.wav`
and `.mp3`, a 30.72 s, 125 BPM, 16-bar recorded loop). Its licence is not stated, so it was used for measurement only
and is not committed.

**What broke**
- **The kick detector was tuned on sine sweeps and was 23 ms late on a real kick.** A recorded kick's sub body swells
  for ~20 ms after its click, so "150 Hz low-pass, 50 % of the rise" fired late. Swept cutoff × threshold against the
  measured transient start (3.2 ms into the loop): 1 kHz / 20 % lands 0.9 ms after it with 0.6 ms rms. New defaults;
  the test's synthetic kick now has a click and a swelling body, so it would have caught this.
- **Outlier rejection hid a tempo ramp.** After the retune, a +1 BPM/min drifting track passed (0.58 ms rms on the
  299 of 392 beats the fit kept). Added a drift check over *all* detected kicks (median residual per 16-beat block)
  and a minimum kept share; now even 0.05 BPM/min over five minutes is refused. The drift number saturates near the
  search window (~30 ms), so it is a refusal signal, not a measurement; documented.
- **Phrase anchoring was a bar late on the real loop.** "The bar after the biggest change" picked bar 2: the loop's
  first bar is distinct on both sides (looping it twice shows big jumps into and out of it), and a crash on a phrase's
  first bar and a fill on its last are indistinguishable by bar novelty. Phrases now count 8-bar steps from the
  track's first bar (extrapolated back when the beat list starts mid-bar), with novelty as a second opinion that is
  flagged when it disagrees. Real loop: phrases at 0 and 15.36 s, disagreement flagged; synthetic test now also
  asserts that novelty agrees when sections change on phrase lines.
- A test-helper bug: the synthetic bass overran the buffer near the end for some lengths. Fixed.

**Confirmed:** on the real loop the fit gives 124.9997 BPM and librosa's `beat_track` gives 123.05, the exact
lag-grid value (2583.98/21) your own CLAUDE.md diagnosed. WAV and MP3 of the same loop give identical anchors with
both librosa and ffmpeg decoding, so our decoders agree; the ~26 ms Serato offset can only be measured in Serato.
`downbeat_phase` found phase 0 with a clear backbeat. All 17 prototype tests pass, including the real llama-swap one.

**Confidence changes:** none in the Top 10; #10's anchor now rests on one real recording instead of none.

## Round 40 — run the first week's commands against the real tools (05:04–05:17 UTC)

**Attack:** the brief asks for "a first-week plan with exact commands". Days 1, 3 and 4 had been checked against docs;
this round checked them against the tools' own code.

- **Day 1 (Laya):** installed `laya` 0.4.6 from PyPI. `laya-train` has every flag used (`--data`, `--text-column`,
  `--label-column`, `--base`, `--out`, `--dry-run`, `--loss soft-ce`, `--epochs`, `--seed`); `--base multilingual`
  resolves through the same alias table as the Router (`convaiinnovations/laya-multilingual`); the CSV that
  `laya_eval.py --export-csv` writes parses with Laya's own `read_data` into a choice question over the labels, Arabic
  intact. Laya's numbers for the epochs advice: default effective batch 64, so ~2,000 rows give 128 optimizer updates
  at 4 epochs and ~512 at 16. Found in Laya's source: the multilingual checkpoint ships with **no fitted
  temperatures**, so its raw confidences are uncalibrated until laya-train fits them (added to Day 1). Not run: the
  dry run itself, which downloads the tokenizer from Hugging Face (blocked here).
- **Day 3:** llama-swap's Go flags accept `--config`/`--listen`; `dj_guard.py` and `vlm_json_guard.py` flags match the
  plan, and `--url http://127.0.0.1:8080` is right because the script appends `/v1/chat/completions` itself.
- **Day 4 (Hermes):** read `hermes_cli/config.py` and `config_defaults.py` on `main` (2026-10-13; v0.22.0 is tagged).
  Every key exists; `config set` keeps `off` verbatim where the default is a string (`tools.tool_search.enabled`
  defaults to `"auto"`), coerces `false` for the boolean `local_runtime.enabled` (already `false` by default, so that
  line is a guard, now said), converts a plain-string `model` into a section before writing `model.*`, and drops the
  old provider's `base_url` when `model.provider` changes. Correct as written.
- **New pitfall:** Hermes' platform-support page lists **PyPI installs as unsupported**, and PyPI stops at 0.19.0
  while GitHub is at v0.22.0, so a pip-installed Hermes can't reach the 0.21.2 that Day 0 requires. Added to the
  Windows pitfalls table: install with `install.ps1`.

**Confidence changes:** none; Day 1 and Day 4 move from "checked against docs" to "checked against code".

## Round 41 — own bias, second pass: does the Top 10 rank what I could build? (05:17–05:21 UTC)

**Attack:** 8 of the 10 items now have a prototype of mine behind them. Checked each rank against impact ÷ effort as
if no prototype existed, and checked every block against the brief's six fields.

- **Missing fields:** #2, #6, #9 and #10 had no "Could fail if". Added (process-name miss and GPU jobs started outside
  llama-swap; medians over mixed styles and aggregator re-edits; body detection failing in strobes and B2B sets;
  Serato caching, FLAC layout, per-encoder MP3 offsets). All ten blocks now have why, project, effort, confidence
  with a reason, failure mode and first step (checked by script).
- **Ranks that rose because I tested them:** two, both in round 24. The GPU guard (6 → 2) would rank there untested:
  it enforces a "never" in your brief. The FilmCraft seam (new #5) rose partly because the test shrank its effort,
  which is a legitimate impact ÷ effort change; kept, noted here.
- **The real bias was inside #10.** It was framed around *grids* because grid encoding is the hard, testable part.
  But Serato analyses a grid on import and whatstheID's tempo already matches Serato's to 0.01 BPM, so rewriting
  grids mostly duplicates Serato. The value is cue points Serato never sets (intro end, drop, outro, which
  `analyze.py` already finds) and grids only where Serato is wrong (your notes have one). Reframed #10 that way.
- **And a hazard the reframing exposed:** cue points live in `Serato Markers2` together with your hand-set cues,
  loops, track colour and BPM lock; my writer replaced the whole tag, so "write cues everywhere" would have wiped
  your prep. `serato_writeback.py` now merges: your cues keep their slots, new ones fill free slots, a new cue
  within 250 ms of yours is skipped, loops/colour/lock are kept, `--cues-only` leaves the grid alone, and a tag
  holding entry types it can't re-encode (Serato Flip) is refused untouched. Tested on MP3 and FLAC.
- **Checked, not promoted:** vault security (cross-project 8) as a Top 10 candidate. Hermes' defaults already deny
  unknown gateway users and run `smart` approvals with cron/unattended denial (read in its code), so the rule is
  "don't loosen them"; reworded there instead. Track-ID captions folded into #8 (they come free with the history).

**Confidence changes:** none; #10's title and first step changed.

## Round 42 — Reel Brain's labels: does Instagram's export carry your folders? (05:21–05:23 UTC)

**Attack:** `collections_probe.py` and the classification advice assume your collection names are available as
labels, and 2.3 tells you to use Instagram's export instead of instagrapi. Nobody had checked what the export holds.

**Found:** two open-source parsers ([max-lutz/instasaved PR #26](https://github.com/max-lutz/instasaved/pull/26), Kotlin;
[TikTokAnalyzer PR #20](https://github.com/danfox127-dotcom/TikTokAnalyzer/pull/20)) read `saved_posts.json` and
`saved_collections.json`, the latter listing each collection by name with its posts. So the labels exist. Two
pitfalls they both handle and the report didn't mention: **Meta writes UTF-8 bytes as separate characters**, so
Arabic captions and collection names arrive garbled (fix: `s.encode('latin-1').decode('utf-8')`, checked here on
escaped Arabic, with a try/except for strings that were already right); and posts can sit in a collection without
appearing in `saved_posts.json`. Field names weren't confirmed from Meta's own docs (none found): the report says to
check them on your own export.

**Confidence changes:** none; one Reel Brain step now won't silently garble your Arabic collections.

## Round 43 — money, second hostile pass (05:23–05:25 UTC)

**Attack:** re-read section 4 as a client and as a payments clerk would.
- **Payoneer's marketplace fee** was stated as "~1 %"; its own fee page says "varies by marketplace". Now "up to ~1 %".
- **Upwork's EGP withdrawal** was "check your settings"; a 2026 Egypt fee guide lists Direct-to-Local-Bank in EGP at
  $0.99 (Payoneer from Upwork ≈ $2). Still says to confirm in Get Paid.
- **Path 2's edge** quoted QwenCleo's 19.9 % vs 63.9 % WER with no caveat in this section; it is self-reported by a
  19-star repo's author. Caveat added where the money claim is made.
- **Path 3's track IDs for DJs abroad** assumed their Serato history; Serato's History panel exports a session as
  text, CSV or M3U (support article), but I could not confirm the CSV has start times. The path now says to ask for
  the export with the video and to place IDs by ear at transitions if it has only the order.
- **Path 1 gains a bundle:** the next event's flyer or announcement still from FLUX.2 klein 4B (Apache-2.0, so
  sellable), which ties the money path to Top 10 #1 and costs one ComfyUI run.
- **Not changed:** five paths, each (except "not yet" for whatstheID) with a one-week test; Egypt availability
  facts from rounds 7, 13 and 32 still hold (Stripe Global Payouts EG and Gemini regions re-confirmed in round 37).
- **Also decided:** Top 10 #9 can't be tested on real club footage from here (YouTube, Vimeo, Wikimedia and stock
  sites are unreachable; OpenCV's pedestrian sample isn't a DJ booth), so it stays "synthetic only".

**Confidence changes:** none.

## Round 44 — licence flags, every model table (05:25–05:26 UTC)

**Attack:** "Flag every license." The 2.1 model table had a licence column; 2.2 and 2.3 didn't, and two models were
named without one.
- **EmbeddingGemma-300M is not Apache.** It is under the **Gemma Terms of Use** (commercial use allowed, but Google's
  prohibited-use policy applies and can change; a notice is required in derivatives). Gemma 4 moved to Apache-2.0;
  EmbeddingGemma did not. Flagged in both tables and in cross-project piece 6, with "swap in an Apache-2.0 embedder if
  you ever ship it inside something you sell".
- **Cohere Transcribe Arabic** (2B, July 2026) checked: Apache-2.0 per Cohere's own announcement; 25.87 WER on the
  Hugging Face Arabic ASR leaderboard (Cohere's figure). Added to the Reel Brain table beside QwenCleo.
- **Qwen3-VL-8B:** Apache-2.0 per Voxel51's and Roboflow's model pages (official card unreachable here).
- **Contradiction fixed on the way:** the Reel Brain table still said "Q5 + mmproj, ~7–8 GB" for the vision model,
  against Top 10 #4's Q6_K at 8K context (~9 GB, round 33). Now Q6_K, with the A/B candidates named. The agent table
  now says `--n-cpu-moe ~24–26 (or --fit)` and ~10–11 GB, matching #7 after round 37's headless-card caveat.

**Confidence changes:** none.

## Round 45 — Inspiration Canvas: the supported way into Eagle (05:26–05:27 UTC)

**Attack:** 2.5's fallback ("your own exporter is a few dozen lines") rested on a third-party description of Eagle's
on-disk library layout. Looked for the supported interface instead.

**Found:** Eagle documents an official **local Web API** (v2 at `http://localhost:41595/api/v2/`; requests from
localhost/127.0.0.1 are trusted without a token; a playground at `/api/v2/playground`; the older v1 `/api/item/list`
is documented separately). The on-disk `.info/metadata.json` layout is only described by third-party tools. 2.5 now
says to write the exporter against the Web API while Eagle is open, not against the library folder. Response field
names were not confirmed (the docs host is unreachable here): the playground shows them on your machine.

**Confidence changes:** none (2.5 has no Top 10 item).

## Round 46 — the reference-clip analyser on a real kick (05:27–05:30 UTC)

**Attack:** Top 10 #6's analyser had only seen synthetic audio. Ran its beat tracking on the recorded techno loop
from round 39.

**Found:** tempo right (125.005 BPM via its beat-time regression; librosa alone says 123.05), but its librosa beats
sat **19–31 ms after each kick** (the onset-envelope lag again). With the ±60 ms on-beat tolerance, a cut placed one
frame *before* the kick (a common editing habit) reads as ~65 ms off and is counted off-beat, biasing the very
statistic #6 exists to measure. Fixed: the librosa fallback shifts its beats by their median lag to the kick
transients (same 1 kHz / 20 % rule as `serato_writeback.py`; one constant shift, so tempo and spacing are untouched).
Real loop after: within ±10 ms. That broke `bar_phase`, which sampled the onset envelope exactly at each beat; it now
takes the envelope's maximum over the 60 ms after each beat, so it works with either timing. The test now also
asserts beats within 10 ms of the true kicks (22 ms median before the fix). Beat This, when installed, is untouched.

**Confidence changes:** none; #6's statistics lose a systematic bias before you ever run them.

## Round 47 — contradictions and stale text, from an independent hostile read (05:30–05:36 UTC)

**Attack:** a separate reviewer read the whole report cold and listed contradictions, stale references, repetition
and unsupported numbers (14 / 10 / 12 / 10 items). Fixed:
- **Contradictions:** the plan is JSON everywhere (three places still said "plan in OTIO"; OTIO is only the export to
  Resolve); Hermes runs your own `llama-server` behind llama-swap (2.2 still offered the managed runtime as equal);
  Hermes reaches the vault through its bundled skill, other agents through MCPVault; the VLM is Q6_K at 8K (one table
  said Q5); per-frame tokens are ~225 at 360×640, not 300–400; Laya's 0.766 and 0.790/0.772 are separate runs (now
  said); FLUX fits 12 GB with fp8/GGUF files; the RAM need is 11–13 GB with the arithmetic shown; MiniMax's
  territory clause is "confirmed", not "reportedly"; the shared-model candidates are Qwen3.6-35B-A3B or Gemma 4 12B in
  all three places; the replay is three-way in #7, Day 4 and the YAML (new `agent-gemma` entry, config still valid);
  #3's table now says "1 evening" and "high (method), medium (gain)"; Day 5 is labelled as *starting* #5 and #6;
  "generated stills don't belong in paid clips" narrowed so it no longer contradicts the flyer bundle; "17+ Serato
  reference grids" corrected to reference tracks (BPM and key; whatstheID stores no grid).
- **Stale:** round count; a pointer to a "Top 10 tip in 2.1" that didn't exist; three places still framing #10 as
  grid write-back; a "hand-back" reference; Serato 3.x `.session` history now said to be unsupported by Day 6's
  script; `agent-small` gains a commented `--mmproj` (the report said Qwen3.5-9B reads images); three orphan source
  links removed; reader-facing "round N" tags removed (the audit log keeps them); "~200 lines" → ~240.
- **Unsupported numbers:** "48k open issues", "hundreds of PRs in October", "~1,000 labels", MiniCPM's 73.5
  Video-MME and Beat This's "~78 MB" removed or reworded; "104–110 °C" now attributed to forum reports with the pad-mod
  source; `-lgc 210,1700` explained; the ±8 % tied to a Technics-style pitch fader; the $150–400 agent-setup figure
  traced to a promotional OpenClaw income guide (linked, labelled) plus a ~500-yuan on-site figure.
- **What I got wrong** re-picked: Laya's epochs advice (backwards) merged into the Laya item; the rb2serato item
  rewritten around FLAC, the missing anchor, Windows, the grids-vs-cues framing and the synthetic-kick detector;
  the numbers item extended with the untraceable Gemma speed and the stale Scribe price.

**Not yet done:** cutting repetition; the report grew to 19.7k words while fixing. Next round cuts.

## Round 48 — cut the repetition (05:36–05:43 UTC)

**Attack:** "a shorter report that survived 6 audits beats a long one that survived 1." The reviewer's 12 repetition
sites plus my own word counts per section.

**Cut or merged:** #10 (964 → ~640 words: one "what it's worth" + "what rb2serato lacks" + prototype + confidence);
#7 (895 → ~710: one speed paragraph, the model and challenger bullets merged, the 46.8 tok/s aside left to section 5);
#2's second telling of the ComfyUI story; 2.1's seam and headless bullets (now a pointer to #5 plus the three
lessons only testing showed); 2.1's taste and type bullets merged into the house-look block, which itself shrank;
the shot-picking list and paragraph merged; the two Arabic-caption paragraphs tightened; 2.3's five separate
VLM-candidate bullets merged into one A/B list (same 20 reels for every candidate); Dopamine said once instead of
three times; the repo-linker failure list shortened; 2.4's downbeat bullet halved, its grid-quality and AudD
paragraphs turned into pointers; rbxport (unreadable site) and pyrekordbox (you use Serato) dropped with their
source rows; Hermes memory-plugin roster trimmed; money paths 1 and 3 tightened; Day 1/Day 4 "checked against code"
notes shortened; Laya's Do list tightened.

**Result:** 19.7k → 18.4k words with nothing actionable removed. The rest is the brief's required breadth (five
projects, first week, money, sources). All 17 prototype tests pass, including the real llama-swap run against the
config with the new `agent-gemma` entry.

**Confidence changes:** none.
