# Projects research: what to build, adopt or drop

**Status:** round 1 draft (breadth pass). Every later round rewrites this file; `audit-log.md` keeps the history.
**Written for:** a solo dev and techno DJ in Cairo with one Windows 10 PC (RTX 3080 Ti, 12 GB VRAM, 300 W cap), local-first.
**Date of research:** 2026-10-14. Repo stats (stars, last commit, licence) were checked on that date.

> One unknown changes several answers: **how much system RAM you have.** Mixture-of-experts models with
> expert offload (the fastest way to run a 30B-class model on 12 GB) keep ~12–13 GB of weights in RAM: 32 GB is
> comfortable, 16 GB has been reported to work with nothing else open. Wherever that matters, both options are given.

## The blunt version

- **Creative Studio is the right top priority, and the LLM is not where its quality comes from.** In a September 2026 benchmark of agents editing raw footage, the best resolved 27 % of tasks, failing mostly on craft. Your edge is signal (beats, drops, phrases, pose, Serato's own logs) plus your taste. Use the model to fill in a plan, not to judge one.
- **Laya, as shipped, is close to a coin toss.** Its own README says the base checkpoints are near chance zero-shot. Fine-tune and calibrate it on your labels, or take it out of the path.
- **A 12 GB local agent will not be as reliable as Claude Code.** Expect a few percent of tool turns to need a retry. Use Hermes for routing, automation and vault work; keep heavy coding on Claude Code.
- **Don't build the Inspiration Canvas app.** Store boards as JSON Canvas in your vault (or buy Eagle for $35) and spend the time on Creative Studio.
- **Don't take whatstheID public.** The "paste a mix, get a tracklist" space is crowded and the download features carry legal risk. Finish the Serato write-back; it is the part nobody else does.
- **Generated video (MiniMax H3) and generated stills (Qwen-Image 2.1) don't belong in paid club clips,** for licence reasons and because the product is that it was real.
- **Five projects plus a FilmCraft fork is too many for one person.** The first week touches Creative Studio, Hermes/Laya, the shared GPU setup, and Reel Brain's looping JSON only because it shares the GPU and the vision model; whatstheID and the canvas wait.

---

## 1. Top 10 moves (ranked by impact ÷ effort)

| # | Move | Project | Effort | Confidence |
|---|---|---|---|---|
| 1 | Take client-facing image generation off Qwen-Image 2.1 (research-only licence) | Creative Studio | 2–3 h | medium |
| 2 | Measure Laya's routing accuracy, then fine-tune and calibrate it on labelled logs | Hermes + Laya | 2 h, then 1–2 days | high |
| 3 | Fix the looping vision JSON at the source: frame-token budget, sampling, quant, bounded schema | Reel Brain, Creative Studio | 0.5 day | medium |
| 4 | Move Hermes to llama.cpp with MoE expert offload; trim tools by hand (Tool Search breaks Qwen) | Hermes | 0.5–1 day | medium |
| 5 | Measure 40 reference clips and turn "Boiler Room style" into numbers | Creative Studio | 1 day | high |
| 6 | Put every GPU server behind llama-swap, add a DJ-mode guard, cap clocks and check VRAM temps | all | 0.5–1 day | medium |
| 7 | Get your sets' beat grids from your own track files and Serato's history | Creative Studio, whatstheID | 2–4 days | medium |
| 8 | Encode one house look per client: type, motion grammar on the bar grid, grade from footage | Creative Studio | 2–3 days | low |
| 9 | Reframe from body pose + an L1-optimal camera path, not faces alone | Creative Studio | 2–3 days | medium |
| 10 | Write Serato grids and cues with rb2serato's MIT encoders | whatstheID | 2–3 days | medium |

### 1. Take client-facing image generation off Qwen-Image 2.1
- **Why:** several independent write-ups (dated after 2026-09-20) say Qwen-Image 2.1 ships under a *Qwen Research License*: research and evaluation only, commercial use by separate agreement. The original Qwen-Image was Apache-2.0; 2.1 is not. Anything you sell (the collective's clips) cannot use it.
- **Instead:** FLUX.2 [klein] **4B** (Apache-2.0; the 9B is non-commercial) or Z-Image-Turbo (Apache-2.0, 6B, 8 steps). Both fit 12 GB quantized. If you want to stay in the Qwen family, Qwen-Image-2512 (Dec 2025) was released under Apache-2.0 per the [Qwen-Image repo](https://github.com/QwenLM/Qwen-Image) (heavier: ~20B). Keep Qwen-Image 2.1 for personal experiments only.
- **Confidence: medium.** Many secondary sources agree; I could not open the official model card (Hugging Face was unreachable from my tools). The GitHub repo's README still says "Qwen-Image is licensed under Apache 2.0" but its last commit (2026-02-10) predates 2.1, so it does not cover 2.1's weights. Settle it on the Hugging Face card.
- **Could fail if:** Qwen re-licenses (it happened in the other direction before) or your outputs are judged "not commercial". Unlikely to matter: switching costs hours.
- **First step:** open the official Qwen-Image-2.1 model card, read the licence block, then build one ComfyUI workflow on FLUX.2 klein 4B and compare 10 prompts from your direction folder.

### 2. Measure Laya, then fine-tune and calibrate it
- **Why:** your router is [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) (Apache-2.0, v0.4.6, last commit 2026-10-12). Its own README is blunt: **the base checkpoints are near chance zero-shot** on typed decisions (0.362 and 0.352 against a 0.318 random and 0.461 majority-class baseline); fine-tuning on the benchmark's training split took the same decisions to **0.766**. They are also **over-confident as shipped** (mean ECE 0.466 → 0.081 after fitting one temperature per question type), and `laya-multilingual` ships with **no fitted temperatures**, so its confidences mean little until you fit them. On CPU, torch's default threading gave a p50 of 9.4 s on a busy laptop; pinning threads (`torch.set_num_threads(<physical cores>)`, `set_num_interop_threads(1)`) brought it to 0.4–0.8 s. Every Hermes message goes through this.
- **Do:** (1) hand-check 200 logged routes and compute accuracy per route; (2) label 2–3k logged messages with a strong teacher (your best local model overnight, or Claude) plus your own corrections, so the labels are not Laya's own guesses; (3) fine-tune with **`laya-train`** (in the package since 0.4): one command from a `text,label` CSV, on one device (your 3080 Ti when you're not DJing, or CPU with `--freeze-encoder`), and it holds out a calibration slice, fits the temperatures and per-option abstention thresholds (`--target-error`, default 10 %) by itself. No Kaggle needed, so your messages never leave the PC; the 2×T4 notebook is still there for big runs. Use `--loss soft-ce` (0.790 vs 0.772 for the default on Laya's own benchmark) and `--shuffle-options` if a question has many options; (4) A/B against the cheap baseline: EmbeddingGemma-300M embeddings + logistic regression on the same labels. Keep whichever wins.
- **Pitfalls named in the README and open issues:** don't use `true`/`false` or `yes`/`no` as `choice` labels (the model follows the label word); negated requests can flip (e.g. "don't cancel" → `cancel_account` at p=0.9998); more than ~20 options per question get truncated, so split coarse/fine; the fixed 4-epoch default gives a small dataset **too few optimizer updates, and the head collapses to the class prior** ([#963](https://github.com/NandhaKishorM/laya/issues/963), open until early stopping merges): read the update budget `laya-train --dry-run` prints (the default run on Laya's 6,000-decision benchmark is 352 updates; 1,100 items give only 72), raise `--epochs` to get near it (the reporter's useful epoch was 17–31), repeat with two or three `--seed`s (6 of 15 identical runs never left the plateau), and use the "positive control" in Laya's `docs/finetune.md` if a run stays at chance. Serving your fine-tune is solved: `Router(models=...)` / `Router.register(...)` take custom checkpoints since 0.3.28 and `laya-serve` reads `LAYA_EXTRA_MODELS` since 0.4.1; only routing *by content* to a checkpoint is still open ([#919](https://github.com/NandhaKishorM/laya/issues/919)).
- **Confidence: high** for "measure and fine-tune" (it is what the project's own maintainers say); medium on how much it gains on *your* routes.
- **Could fail if:** labels are too few or too noisy, or your messages mix Arabic and English in ways the multilingual checkpoint reads poorly. Training on your own card avoids uploading anything; if you use Kaggle for a big run, strip anything private first.
- **First step:** export 200 recent routing decisions with the message text and mark each right or wrong. One evening. Score them with [`prototypes/laya_eval.py`](prototypes/laya_eval.py) (accuracy per route, calibration, a confidence gate, and a cheap baseline on the same labels); it also exports the CSV `laya-train` reads.

### 3. Fix Reel Brain's looping JSON at the source: image-token budget, sampling, quant, bounded schema
- **Why:** two open issues match your stack closely. Ollama [#13084](https://github.com/ollama/ollama/issues/13084): Qwen3-VL 4B/8B on **Windows with an RTX 3080** produces "highly unsorted contents" or repeats short sentences once the prompt exceeds `num_ctx`; the reporter's images were 3236×2160 and the logs said "truncating input prompt". [QwenLM/Qwen3-VL#1611](https://github.com/QwenLM/Qwen3-VL/issues/1611): Qwen3-VL loops across runtimes (Transformers, Ollama, LM Studio, llama.cpp), more with **greedy decoding** and **low (4-bit) quants**; the same author ran GLM-4.6V-Flash on 500 cases with zero loops. A Qwen-VL image costs roughly `h × w / (32 × 32)` tokens, so a full-resolution 1080×1920 frame is ~2,000 tokens and eight of them ~16,000. **And on a card under 24 GB, Ollama's default context is 4K tokens** ([Ollama docs](https://docs.ollama.com/context-length)): unless Reel Brain sets `num_ctx` on every request (its code isn't on GitHub, so I couldn't check), three full-resolution frames already overflow it, which is exactly the truncation in #13084. Check this first.
- **Do:** (1) downscale frames to ≤ 640 px on the long side (~300–400 tokens each), cap at 6–8 per reel, set `num_ctx` explicitly and log prompt tokens per request; (2) use Qwen's recommended Instruct sampling (temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5), not temperature 0; (3) Q6_K or Q8_0 instead of Q4 if it fits (an 8B at Q8 is ~8.5 GB plus the projector); (4) a schema that cannot run away: `maxItems` on every array, `maxLength` on strings, enums, thinking off, a hard cap on output tokens; validate with Pydantic, retry once, then fall back to "free text → a second small call that only formats JSON"; (5) A/B GLM-4.6V-Flash (9B, MIT per model listings, GGUF available) on the same 20 reels.
- **Correction from round 8:** earlier drafts blamed Ollama ignoring repetition penalties. That bug was real ([#15783](https://github.com/ollama/ollama/issues/15783)) but was **closed in July 2026 as obsoleted by Ollama 0.30.0, which moved its engine onto llama.cpp**. It only matters if your Ollama is older than 0.30: check `ollama --version`, and update if so. But the closing comment only says "obsoleted by the switch to llama-server"; the older umbrella issue [#14493](https://github.com/ollama/ollama/issues/14493) is still open and nobody there has confirmed penalties on 0.30+. So run the diagnosis on Ollama (Day 2), then rerun the same reels on plain llama-server behind llama-swap (Day 3) to rule Ollama out; keep whichever loops less.
- **Confidence: medium.** The issues match your hardware and model; nobody has run your prompts.
- **Could fail if:** the prompts themselves invite open-ended lists or the model needs thinking to read the frames. The bounded schema and the GLM A/B cover those.
- **First step:** record your Ollama version and the prompt-token count for the 20 reels that failed most recently, then rerun them with downscaled frames and the recommended sampling. [`prototypes/vlm_json_guard.py`](prototypes/vlm_json_guard.py) does all of that against Ollama or any OpenAI-compatible server.

### 4. Move Hermes to llama.cpp with expert offload, and cut the tool list by hand
- **Why:** Hermes now ships a managed llama.cpp runtime that places MoE expert weights in system RAM first and keeps attention and KV cache on the GPU, with a guaranteed ≥64K context and 15-minute idle unload ([local-models docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/local-models.md)). On a 12 GB RTX 3060 users report Qwen3.6-35B-A3B generating at **~35–45 tok/s** with expert offload: InsiderLLM (32 GB DDR4, Q4_K_M) found `--n-cpu-moe 24` fastest at 38.9 tok/s, flat to 8K context, and retracted an earlier "20 is fastest"; [one user](https://x.com/DogukanUrker/status/2077472690156511643) reports ~45 tok/s at `--n-cpu-moe 26` with UD-Q4_K_XL, 150K context and **only 16 GB of RAM**, the key being `-np 1` (one server slot). Treat the May 2026 r/LocalLLaMA figure of 46.8 tok/s at `-ncmoe 18` with suspicion: by my arithmetic 22 layers of Q4_K_M experts don't fit in 12 GB, so it was a smaller quant or llama-bench's tiny context. Your 3080 Ti has ~2.5× the 3060's memory bandwidth, but the offloaded experts run at your system RAM's speed, so expect a similar number, not 2.5× it. Hermes' own docs say prefill of the system prompt plus tool schemas dominates first-token time on local models, so the fixed prompt is the first thing to shrink: `hermes prompt-size` shows it, `hermes tools` and per-profile toolsets cut it.
- **Run your own `llama-server` behind llama-swap, not Hermes' managed runtime**, so one process owns the GPU (trade-off in #6). And don't move Qwen3.5/3.6 onto Ollama instead: its stock Qwen 3.5 renderer still misses tool calls in reports from June–September 2026 (a v0.30.7 tester got 2 of 5 relay calls, 4 of 5 with a `qwen3-coder` renderer override; [#14493](https://github.com/ollama/ollama/issues/14493), open). Your current Qwen3-Coder-30B on Ollama uses a different renderer, which is why it can stay as the fallback.
- **Do not turn on Tool Search with Qwen models yet.** Its bridge tool is literally named `tool_call`, which collides with the `<tool_call>` tag in Qwen chat templates; Qwen models call the bridge malformed five times and the guardrail halts the turn ([#110442](https://github.com/NousResearch/hermes-agent/issues/110442), open; the rename to `invoke_tool` is in an unmerged PR). The documented workaround is `hermes config set tools.tool_search.enabled off`.
- **Known Qwen3.6 + llama.cpp issues in Hermes, with workarounds:** pass `--chat-template-file` with the right Qwen template, not only `--jinja`, or output can be garbage ([#29677](https://github.com/NousResearch/hermes-agent/issues/29677)); leave `capabilities.answer_in_reasoning` unset, because a tool call stranded inside `<think>` still happened in **1 of 23 tool-call turns** ([#129440](https://github.com/NousResearch/hermes-agent/issues/129440)); `search_files` can loop when the model passes a glob as a regex ([#66129](https://github.com/NousResearch/hermes-agent/issues/66129)). Expect a few percent of turns to need a retry: "reliable" at 12 GB means "recovers well", not "never fails".
- **Model:** Qwen3.6-35B-A3B (Apache-2.0, April 2026) if you have ≥32 GB RAM (16 GB has been reported to work, but not with Serato, Chrome and ComfyUI also open); it scores 81.2 on TAU2 agentic tool use against 68.2 for Gemma 4 26B-A4B (vendor-adjacent numbers). Otherwise Qwen3.5-9B (Apache-2.0, dense, hybrid attention so long context is cheap) fully on GPU.
- **Also:** be on ≥ v0.21.2: v0.21.0's session-store rewrite made `state.db` fragile and v0.21.2 closed 44 issues about it. Run `hermes backup` nightly (the docs say never to copy `state.db` alone).
- **Confidence: medium.** Docs and issues read directly; speed numbers are from a slower card; the failure rates are single reports.
- **Could fail if:** RAM is 16 GB, or your MCP tool set is so large that the eager schema blows the context. Keep your current Qwen3-Coder-30B/Ollama config as a fallback profile until the new one has a week of clean logs.
- **First step:** `hermes prompt-size` and `hermes tools` today; then start `llama-server` with Qwen3.6-35B-A3B (behind llama-swap, Top 10 #6, so it shares the card politely) and replay 20 of your logged requests against both setups.

### 5. Measure 40 reference clips
- **Why:** I found **no published description** of how Boiler Room, BCCO or HÖR cut their shorts. Guessing produces the "stock" look. Your own whatstheID notes show the method that works for you: measure, then build.
- **Do:** collect ~40 clips (analysis only, never re-published). Run shot detection (PySceneDetect, BSD-3, or FilmCraft's `clip.sceneEditDetection`) and beat tracking (Beat This) on each. Output: cuts per clip, shot length in beats, % of cuts on a downbeat/bar/phrase line, where the drop sits, how long the first shot holds, when text appears and what it says.
- **Hypothesis to test:** many of these clips are one or two fixed-camera shots where the edit is mostly *selection* (start a few bars before the drop, end on the reaction) plus a track-ID caption, not rapid cutting. If true, alternating crowd/DJ cuts is the wrong default.
- **Confidence: high** that it pays off; the numbers it finds are unknown by definition.
- **First step:** run [`prototypes/analyze_reference_clips.py`](prototypes/analyze_reference_clips.py) `--strobe-safe` over a folder of ~40 clips; look at the medians. Use `--strobe-safe` on club footage: in the synthetic test, strobes inside one shot turned 7 real cuts into 9 for a plain detector.

### 6. Put every GPU server behind llama-swap, plus a small DJ-mode guard
- **Why:** every project competes for one 12 GB GPU and the PC has crashed on long runs. You do not need to write a broker: [llama-swap](https://github.com/mostlygeek/llama-swap) (MIT, active, WinGet package for Windows) already starts and stops GPU servers on demand and keeps only one group loaded. It handles llama-server (LLM and VLM), whisper.cpp, stable-diffusion.cpp, audio.cpp and **ComfyUI** (a dedicated `/comfyui/` endpoint and a reserved `comfyui_auto` model ID so the browser websocket doesn't pin the GPU), plus `/upstream/<model>/` passthrough for anything else HTTP. `groups` with `exclusive: true` give the "only one big thing at a time" rule; `POST /api/models/unload` empties the card; `ttl` frees idle models.
- **Do:** (1) define each GPU workload as a llama-swap model (agent LLM, VLM, ASR, ComfyUI) in one exclusive group; (2) point Hermes (`providers.llamacpp.base_url`), Reel Brain, Creative Studio and ComfyUI clients at llama-swap instead of their own servers; (3) a small **DJ guard** that polls for `Serato DJ Pro.exe` / `Serato DJ Lite.exe` / `Ableton Live*.exe` (psutil) and, while they run, switches llama-swap to a `dj` profile whose pins are all null (every model answers 404 instead of loading: `PUT /api/profiles/active`), unloads everything (`POST /api/models/unload`), and re-unloads anything that starts anyway, because llama-swap's `/comfyui/` route ignores profiles; on exit it clears the profile. No service restarts needed; (4) make every batch job checkpoint per item and retry on connection refused, so the guard costs a pause, not a lost run. Hermes cron's no-agent mode can drain the queue at night.
- **Trade-off:** Hermes' managed runtime sizes context and expert offload for you; behind llama-swap you set `--n-cpu-moe`, `-c` and the chat template yourself in the YAML. That is ten lines, once.
- **Why the DJ guard matters beyond VRAM:** NVIDIA driver DPC-latency spikes of 3–10 ms are a known cause of audio dropouts on Windows; heavy CUDA work makes it worse. Run LatencyMon once with a GPU job active and once without, while Serato plays.
- **Hardware side:** on RTX 30-series, crashes under load are often millisecond transients that a power cap does not stop. Cheap things to try: cap the core clock (`nvidia-smi -lgc 210,1700` as admin, or an Afterburner curve), and watch **GDDR6X memory junction temperature** in HWiNFO during a long LLM or Whisper run (memory-bound work behaves like mining; 3080-class cards reach 104–110 °C there). If junction temps are high, thermal pads; if crashes persist at a capped clock, suspect the PSU.
- **Tested (round 19):** I built llama-swap from source and ran the committed config with stand-in servers: asking for `vlm` unloads `agent` (one GPU owner), `/comfyui/` loads ComfyUI, transcription requests reach the QwenCleo entry, and the guard's DJ mode returns 404 for every model, empties the card, unloads a ComfyUI job that sneaks in, and restores service afterwards ([`test_dj_guard_llama_swap.py`](prototypes/test_dj_guard_llama_swap.py)). The first version of the guard freed ComfyUI *through* llama-swap, which started ComfyUI: DJ mode ended with it loaded. Only running the real binary showed that.
- **Confidence: medium.** The mechanics are tested against the real binary (on Linux); the Windows run, driver DPC behaviour and your card's thermals are not. The crash diagnosis is from forum reports, not your logs.
- **First step:** install llama-swap with [`prototypes/llama-swap.example.yaml`](prototypes/llama-swap.example.yaml) as the starting config, run [`prototypes/dj_guard.py`](prototypes/dj_guard.py), move one workload (the VLM) behind it, and log `nvidia-smi --query-gpu=power.draw,clocks.gr,temperature.gpu,memory.used --format=csv -l 1` plus HWiNFO memory-junction temperature during the next long Reel Brain batch.

### 7. Beat grids for your own sets from your own track files
- **Why:** blind beat tracking on a 150 BPM mix fights overlapping kicks in transitions, pitch riding and breakdowns. You have better information. **Serato DJ 4 logs every load** in `master.sqlite` → `history_entry` (artist, title, BPM, key, deck, `start_time`, `played`; verified in the [whats-now-playing reader](https://github.com/whatsnowplaying/whats-now-playing/blob/main/nowplaying/serato/reader.py)). Your library files carry Serato's beat grid (`Serato BeatGrid` GEOB). Align each played track to the set recording (your cross-correlation code plus whatstheID's speed ladder), then transform that track's grid into set time. This is the published "DJ-mix reverse engineering" approach (Schwarz & Fourer; Kim et al., ISMIR 2020).
- **Fallback:** Beat This ([CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT, ~78 MB model, pip install, no madmom needed) for tracks you don't own. Evidence it suits your genre: a user benchmark on Giant Steps (664 Beatport electronic tracks) in [issue #13](https://github.com/CPJKU/beat_this/issues/13) got **89.3 % strict / 95.0 % octave-tolerant** tempo accuracy, 90.9 / 96.4 % with an ensemble of the *small* models (which did better than the big ones on near-constant tempo). The maintainers confirmed in [issue #16](https://github.com/CPJKU/beat_this/issues/16) that the MIT licence covers the weights. Add an octave-correction prior (120–160 BPM for techno).
- **Recording note:** the MC4000 unlocks **Serato DJ Lite**, which has a History panel but no built-in mix recorder (Pro has one). If your recordings come from OBS or the controller, alignment is the same; only the clock you seed it with differs. On Serato 3.x the history is the older binary `_Serato_/History/Sessions/*.session` format (also parsed by whats-now-playing) instead of `master.sqlite`.
- **Precedent on real mixes:** Kim et al. (ISMIR 2020, [djmix-analysis](https://github.com/mir-aidj/djmix-analysis)) aligned tracks to 1,557 real 1001Tracklists mixes with subsequence DTW, worked example a Boiler Room set; they report DJs rarely change tempo or key much, which keeps stretch ratios small. Their repo has no licence file: read it, don't copy it.
- **Confidence: medium.** The history fields are verified from code; alignment through heavy EQ/filter/FX is not tested on your sets.
- **Could fail if:** the DJ rides the pitch so the stretch ratio drifts inside a track (fit it piecewise) or the track was played from a streaming service (no file).
- **First step:** list the last session with [`prototypes/serato_set_grid.py`](prototypes/serato_set_grid.py) `history`, then `align` three tracks you own against the recording. In a synthetic mix (track 3 % fast, bass cut for a 30 s blend, crowd noise) it recovered the ratio exactly and the offset to 15 ms.

### 8. Encode one house look per client
- **Why:** "stock AI" is mostly the absence of decisions: default type, eased slides, a new colour per scene. A look that is written down as rules can be checked by your existing motion-graphics QA step; taste that lives in a prompt cannot.
- **Do:** per client, one `look.md` (also the Inspiration Canvas format, see 2.5): one display face and one text face from libre foundries (Velvetyne, Collletttivo; check each font's licence), a type scale, a palette sampled from *their* footage (dominant colours + one accent), and a **motion grammar on the bar grid**: things appear and hold on downbeats, move only across bar lines, hard-cut on the drop, no ease-in-out slides. Then run [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing)'s list of tells (Apache-2.0: "everything is a slide", typed-out headline with a caret, a new flat colour per scene) as a rubric in your QA step.
- **Arabic captions work in FilmCraft if you name the font (tested in round 17).** I built your fork's `filmcraft-cli` and burned an Egyptian code-switched caption ("…استعدوا للـ drop") into a headless export. With the default caption font (Inter) every Arabic letter came out as a "NO GLYPH" box, even with an Arabic font installed, because the fallback ignores installed fonts (upstream [#1475](https://github.com/storytold/filmcraft/issues/1475), fix PR [#1478](https://github.com/storytold/filmcraft/pull/1478) open). Two ways that rendered correctly (joined letters, right-to-left order, the English word at the left end): naming an Arabic face on the track (`captions.setStyle {"track": "C1", "font": "Noto Sans Arabic"}`), or building the fork with `CRAFT_FONTS_DIR` set (craft-fonts carries Noto Sans Arabic, so the default font falls back to it; FilmCraft's own CLAUDE.md already tells you to build that way) (reproduce with [`prototypes/filmcraft_arabic_captions.jsonl`](prototypes/filmcraft_arabic_captions.jsonl); the two frames are attached to the hand-back, not committed, because the fork's asset gate requires a licence sidecar for every image). On Windows, set the track font to an Arabic-capable face (Noto Sans Arabic, OFL; Segoe UI ships with Windows). [#395](https://github.com/storytold/filmcraft/issues/395)'s merged fix (#1140) only covered the editor UI. Pick the house Arabic face per client in `look.md`; the HTML layer remains the place for animated Arabic type.
- **Evidence it is more than opinion:** motionmaxxing's rules come from 53 frame-accurate professional motion moments decoded into ~150 rules, with lint gates (corner labels, deck layouts, typed headlines, >3 dead frames in a row) and one striking count: pros used **3,392 transform keyframes against 584 opacity fades**, i.e. things move and cut, they rarely fade. It is an early release built on brand/product films, not club footage.
- **Confidence: low.** Taste is the least verifiable claim in this report; the rules are measured on brand films, not on your audience or on club clips.
- **Could fail if:** the rules are followed and the result is merely tidy. The reference measurements (Top 10 #5) and a human eye on every first clip of a series are the backstop.
- **First step:** write `look.md` for the collective you want to pitch, using their existing flyers as the source.

### 9. Reframe from body pose + an L1-optimal camera path
- **Why:** YuNet finds faces; a DJ looks down at the controller under strobes, so faces drop out exactly when it matters. A real operator frames the body and hands, holds still, then pans deliberately.
- **Do:** detect people and keypoints with RTMPose via [rtmlib](https://github.com/Tau-J/rtmlib) (Apache-2.0, ONNX, light) and keep YuNet as one signal. Choose the subject per shot, then solve the crop path offline as an L1-optimal path (Grundmann et al., "Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths", the method behind YouTube's stabiliser): the L1 objective produces static holds, constant pans and smooth ease-ins, like a camera operator. Google's AutoFlip (polynomial L2 fit) is the obvious off-the-shelf alternative, but MediaPipe lists it as a legacy solution whose support ended on 2023-03-01. I found MATLAB re-implementations of the L1 paper but no maintained Python one; the linear program is small enough to write with `scipy.optimize.linprog` (HiGHS, BSD) or cvxpy.
- **Avoid:** Ultralytics YOLO (AGPL-3.0) anywhere near the FilmCraft fork.
- **Into FilmCraft, tested:** Motion's `anchor` is in source pixels, so the solved path goes in as anchor keyframes at the path's corners (Douglas–Peucker, ≤ 3 px error). [`prototypes/plan_to_filmcraft.py`](prototypes/plan_to_filmcraft.py) does it against a real build of your fork: on a subject sweeping across the frame with noisy, gappy detections, the subject stayed fully in the 9:16 frame on 100 % of reframed frames (a centre crop: 34 %) with 8–14 keyframes per 3-second shot. **Pitfall the test caught:** the L1 path keeps the subject's *centre* inside its safe zone, so the margin must be at least half the subject's width (a DJ's body, not a face) or the edges leave the frame; at the old 60 px margin only 91 % of frames kept the whole subject.
- **Confidence: medium.** The path and the FilmCraft side are tested on synthetic footage; detection quality on dark, strobing club footage is not.
- **First step:** run rtmlib on one 60-second DJ clip and plot face-detection vs body-detection coverage per frame; feed the body centres to [`prototypes/l1_reframe_path.py`](prototypes/l1_reframe_path.py). On a synthetic swaying DJ with 15 px jitter and 10 % missed detections, its path held still 84 % of the time with no direction changes, where a moving-average follow changed direction 189 times.

### 10. Write Serato grids and cues with rb2serato's encoders
- **Why:** [rb2serato](https://github.com/SM4RTENHEIMER/rb2serato) (MIT, Sep 2026) writes `Serato Markers2`, `Serato Markers_` and **locked** `Serato BeatGrid` tags whose bytes match what Serato writes, verified on a 9,600-track library, with undo logs and audio-byte checks. It also documents Serato 4's import quirks (crate header must be exactly `1.0/Serato ScratchLive Crate`, WAV typed `wave`, Serato closed while writing). That is the risky half of whatstheID's 4c plan, already done.
- **Portability, checked in the source:** the encoders live in `src/rb2serato/seratotags.py`, which imports only `base64`, `struct` and `dataclasses` and says its output was verified byte-for-byte against files written by Serato DJ Pro 2.x–4.x; `encode_beatgrid` takes a list of markers, so multi-marker (tempo-change) grids are supported. The macOS-specific parts are elsewhere: `tagwriter.py` (APFS clone-and-swap) and `seratolib.py` (`/Volumes` paths). On Windows, vendor `seratotags.py` only and write your own safe writer with mutagen: copy → write tags → verify the audio payload is byte-identical → replace.
- **Confidence: medium.** The encoder code reads well and claims byte-for-byte verification, but rb2serato has **1 star and 0 forks**: it is one author's month-old project, and nobody else has confirmed the 9,600-track claim. The more-used alternative, [serato-tools](https://pypi.org/project/serato-tools/) (MIT, Python ≥3.12, 31 stars, can write beat grids and cues), has no stated Serato 4 support. Round-trip every write through two parsers (rb2serato's decoder and serato-tools) and Serato itself before trusting either.
- **The untested case that decides this item:** rb2serato's flow is for tracks Serato 4 imports *fresh*: Serato 4 keeps its library in SQLite but re-imports the old `database V2` and crate files at start-up when they changed, and it overwrites them on quit, so Serato must be closed while you write. Nobody I found documents whether Serato 4 re-reads a rewritten `Serato BeatGrid` tag on a track **it already knows** (serato-tools edits `database V2` precisely so that metadata changes show up without "Reload ID3 Tags", which suggests caching). Your use is exactly that case.
- **First step:** back up `_Serato_` and `%LOCALAPPDATA%\Serato`, vendor `seratotags.py`, then with Serato closed (a) write a grid to a *copy* of a track and (b) rewrite the grid of a track already in the library; reopen Serato, load both, and check the grid moved. If (b) fails, the write-back needs a re-import step, which changes the 2–3 day estimate.

---

## 1b. The first week, day by day

Tested helper scripts for most days are in [`prototypes/`](prototypes/README.md) (each passes a synthetic test;
none has run on Windows yet). Your PowerShell doesn't take `&&`, so every command is on its own line.

**Day 0 (15 minutes): the four facts that change the plan**
```powershell
(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB   # >= 32 → Qwen3.6-35B-A3B; else Qwen3.5-9B
ollama --version                                                                  # < 0.30 → penalties were ignored; update
hermes --version                                                                  # < 0.21.2 → update before anything else
```
Serato: Help → About (Lite or Pro? 3.x or 4.x?). 4.x keeps history in `%LOCALAPPDATA%\Serato\Library\master.sqlite`.

**Day 1 (Laya, Top 10 #2, one evening).** Export 200 recent routing decisions as JSON lines
(`{"text", "laya", "confidence", "label"}`), fill `label` by hand, then:
```powershell
cd research\prototypes
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python laya_eval.py routes.jsonl
```
If accuracy is near the majority-class baseline or ECE is above ~0.2: start labelling toward 2–3k rows (your corrections plus a
teacher model overnight), then:
```powershell
python laya_eval.py routes.jsonl --export-csv routes.csv
pip install -U laya
laya-train --data routes.csv --text-column text --label-column label --base multilingual --out laya-routes --dry-run
laya-train --data routes.csv --text-column text --label-column label --base multilingual --out laya-routes --loss soft-ce --epochs 16 --seed 1
```
Read the optimizer-update budget the dry run prints and set `--epochs` so it lands near a few hundred updates (Laya #963: the
4-epoch default collapses on small data); run a second `--seed` before trusting the result. (`laya` 0.4.6 on PyPI installs the `laya-train` command.)

**Day 2 (Reel Brain loops, Top 10 #3).** Pick the 20 reels that failed most recently:
```powershell
python vlm_json_guard.py C:\reels\failed\reel01.mp4 --api ollama --model qwen3-vl:8b --num-ctx 8192 --context (Get-Content C:\reels\failed\reel01.txt -Raw)
```
It downscales frames to ≤ 640 px, refuses requests that overflow `num_ctx`, uses Qwen's recommended sampling, and logs each
attempt. Count valid notes out of 20 before and after. If loops remain, run the same reels against GLM-4.6V-Flash (LM Studio
lists it; or a GGUF behind llama-swap, Day 3).

**Day 3 (one GPU, Top 10 #6).**
```powershell
winget install llama-swap
```
Download a CUDA build of llama.cpp (`llama-b<N>-bin-win-cuda-…-x64.zip` from its GitHub releases), copy
[`prototypes/llama-swap.example.yaml`](prototypes/llama-swap.example.yaml), fix the paths, then:
```powershell
llama-swap --config llama-swap.yaml --listen 127.0.0.1:8080
python dj_guard.py --llama-swap http://127.0.0.1:8080
```
Rerun Day 2's reels against llama-server to rule Ollama out:
```powershell
python vlm_json_guard.py C:\reels\failed\reel01.mp4 --api openai --url http://127.0.0.1:8080 --model vlm --context (Get-Content C:\reels\failed\reel01.txt -Raw)
```
Once the VLM lives in llama-swap, quit Ollama (or point the guard's `--stop` at it) so two servers don't share the card.
Start Serato and confirm the guard logs "DJ mode on" and `nvidia-smi` shows the card empty. Then run one long Reel Brain batch
with HWiNFO logging GPU memory-junction temperature and `nvidia-smi --query-gpu=power.draw,clocks.gr,temperature.gpu,memory.used --format=csv -l 1 > gpu.csv`.
If junction temperature passes ~100 °C, cap clocks (`nvidia-smi -lgc 210,1700` in an admin shell) and plan new thermal pads.

**Day 4 (Hermes, Top 10 #4).**
```powershell
hermes update
hermes backup
hermes prompt-size
hermes tools
hermes config set tools.tool_search.enabled off
hermes config set local_runtime.enabled false
hermes config set providers.llamacpp.base_url http://127.0.0.1:8080/v1
hermes config set providers.llamacpp.model agent
hermes config set model.provider llamacpp
hermes config set model.default agent
hermes config set model.context_length 65536
```
(Key names from Hermes' `local-models.md`, `tool-search.md` and CLI reference; `local_runtime.enabled false` stops Hermes
starting its own llama.cpp, so llama-swap stays the only GPU owner. Hermes probes `:8080` for a llama-server by default,
which is where the example llama-swap listens.) Keep the old Ollama setup as a second profile (`hermes profile`), replay 20
logged requests on both, and keep the one with fewer failed tool turns.

**Day 5 (reference clips, Top 10 #5).** Collect ~40 clips you think are the target (analysis only):
```powershell
yt-dlp -o "refs\%(id)s.%(ext)s" -f "bv*[height<=1080]+ba/b" --batch-file refs.txt
python analyze_reference_clips.py refs --strobe-safe --out refs_stats
```
Write the medians (cuts per 10 s, shot length in beats, % of cuts on bar lines, first-shot length, drop position) into your
direction folder as `style-sheet.md`, and make the planner's constraints come from it.

**Day 6 (your own set's grid, Top 10 #7).**
```powershell
python serato_set_grid.py history --db "$env:LOCALAPPDATA\Serato\Library\master.sqlite" --recording-start "2026-10-10 23:41:05"
python serato_set_grid.py align --mix set.wav --track "D:\Music\track.mp3" --near 1830 --bpm 148.0 --first-downbeat 0.112
```
Check three tracks by ear against the recording. If the offsets hold, this replaces blind beat tracking for your own sets.

**Day 7 (licence + first money test, Top 10 #1 and money path 1).** In ComfyUI, build one FLUX.2 [klein] 4B workflow (official
ComfyUI tutorial: `flux-2-klein-4b-fp8.safetensors` in `models/diffusion_models`, `qwen_3_4b.safetensors` in
`models/text_encoders`, `flux2-vae.safetensors` in `models/vae`; accept Black Forest Labs' licence on Hugging Face first) and
rerun ten prompts from your direction folder. Then message one collective with the next-morning clip offer.

**Windows install pitfalls (checked in round 11), so a lost evening doesn't look like a bad idea**

| Piece | What breaks | Do this |
|---|---|---|
| Everything Python | One torch build per environment; QwenCleo pins torch 2.5.1 (cu121), others want newer | One venv per heavy stack (`prototypes`, `qwencleo`, `comfyui`); Python 3.12 everywhere (serato-tools needs ≥ 3.12) |
| llama.cpp | The `llama-b<N>-bin-win-cuda-…-x64.zip` has no CUDA runtime | Unzip the matching `cudart-llama-bin-win-cuda-…-x64.zip` into the same folder. Builds exist for CUDA 12.4 and 13.x; 13.x needs an R580-or-newer driver, so take 12.4 if your driver is older |
| llama.cpp memory | `--fit` (on by default in recent builds) sizes offload to *free* VRAM; Windows' desktop holds some | `--fit-target 1536` for margin, `-np 1` for one slot; read the log line that reports the offload |
| Ollama | Default context is 4K tokens on cards under 24 GB ([docs](https://docs.ollama.com/context-length)) | Set `num_ctx` per request or `OLLAMA_CONTEXT_LENGTH` on the server, not on `ollama run` |
| Hermes | Refuses a local endpoint serving < 64K context; terminal tool runs through Git Bash | `-c 65536` in llama-swap and the same `context_length` in Hermes; install Git for Windows. Native Windows 10 is a Tier 1 platform via `install.ps1` (the MSIX app needs Windows 11 22H2) |
| faster-whisper / whisperX | Needs cuBLAS + cuDNN 9 for CUDA 12; pip doesn't supply them on Windows | Its README points to Purfview's whisper-standalone-win archive of NVIDIA DLLs; put them on `PATH` ([README](https://github.com/SYSTRAN/faster-whisper)) |
| QwenCleo-ASR | Streaming needs vLLM nightly, which doesn't run on native Windows | Use the chunked transformers path (its own FastAPI server, `asr-eg` in the llama-swap example); vLLM only under WSL2 |
| rtmlib (pose) | `onnxruntime-gpu` needs CUDA + cuDNN DLLs; PyPI GPU wheels are built for CUDA 13 from ORT 1.27 | Start on CPU `onnxruntime` (offline pose on a few clips is fine on CPU); if too slow, `pip install onnxruntime-gpu[cuda,cudnn]` and keep its cuDNN in step with torch's in the same process |
| Beat This | `torchaudio.load` hands decoding to TorchCodec from torchaudio 2.9, which needs FFmpeg's *shared* DLLs on Windows | Feed it WAV (the reference-clip script already extracts WAV); Beat This falls back to soundfile, which reads WAV/FLAC/AIFF/MP3 but not M4A |
| FLUX.2 klein 4B | fp8 files save VRAM on a 3080 Ti but don't run faster (FP8 math needs RTX 40/50); NVFP4 files target RTX 50 | Use the fp8 or GGUF files and the official ComfyUI template |
| DJ guard | Serato's process name on Windows is unverified (installers carry version numbers) | With Serato open: `python dj_guard.py --once`; if `dj_apps` is empty, add the name from Task Manager → Details with `--watch` |

**Week 2 candidates:** your first real clip end to end: a hand-written plan (cuts from the Day 5 style sheet, the Day 6 grid,
rtmlib body centres) through [`plan_to_filmcraft.py`](prototypes/plan_to_filmcraft.py) into the fork, built with
`CRAFT_FONTS_DIR` so Arabic captions work (Top 10 #9 and #8); then the house
`look.md` for the collective (#8), Serato grid write-back to copies (#10).

---

## 2. Per project

### 2.1 Creative Studio (top priority)

**Adopt**
- **Beat This** ([CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT, last commit 2026-05-28): beat + downbeat without madmom's DBN; CLI and Python; runs on Windows (pure PyTorch). Training code is public, so you can fine-tune on your own library's grids later.
- **Your own sets:** Serato history + track alignment (Top 10 #7).
- **Shot detection:** PySceneDetect (BSD-3, active) or FilmCraft's own scene edit detection. TransNetV2 (MIT) is unmaintained since 2021.
- **Pose/person:** rtmlib (Apache-2.0). SAM 2 (Apache-2.0, last commit Dec 2024) for click-to-track a subject when needed.
- **Motion graphics renderer:** [HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen, Apache-2.0, active, Node ≥22, Windows covered in its troubleshooting guide): HTML/CSS → deterministic video, MOV/ProRes or transparent WebM, Claude Code plugin, MCP guide, a `/music-to-video` beat-synced workflow and `/embedded-captions`. Use the renderer; **skip its component catalog** ("glass-shard-title", "gooey-split"…): a shared catalog is a template library, which is the look you are trying to escape. **Export overlays for FilmCraft as ProRes 4444 MOV, not WebM:** FilmCraft's Matroska reader skips BlockAdditions, which is where VP9 alpha lives, while its ProRes decoder handles 4444 alpha bit-exactly. Remotion has its own licence (paid above small companies); Motion Canvas and Revideo are MIT but slower-moving.
- **Taste checklist:** [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing) (Apache-2.0) lists the tells of AI motion graphics ("everything is a slide", typed-out headlines with a caret, a new flat colour per scene) and its counter-rules (one idea, light and texture, measured motion, cut on motion). Use it as a QA rubric for your existing motion-graphics QA step.
- **Type that doesn't look default:** libre foundries Velvetyne (OFL/GPL per font), Collletttivo (free for commercial use), Use & Modify (curated list; check each licence). Pick one display face and one text face per client and never change them mid-series.
- **Multicam in FilmCraft:** upstream already has `clip.createMulticam` and `multicam.cutToCamera`; drive those from the plan instead of building cuts by hand.
- **The planner → FilmCraft seam, built and tested:** [`plan_to_filmcraft.py`](prototypes/plan_to_filmcraft.py) takes the plan JSON and drives `filmcraft-cli mcp`: a 1080×1920 sequence, cuts from two cameras laid end to end, Motion scale to fill, the reframe path as anchor keyframes, the Serato recording on A1, captions from an SRT (Arabic font named), H.264 export. Its test runs a real build of your fork on synthetic cameras: cuts on the planned frames, subject in frame on every reframed frame, captions burned in, audio present. Things only testing showed: `effects.setKeyframe` edits existing keyframes, so create them with `effects.setParam {"keyframe": true, "time": …}`; `time` is sequence ticks (254 016 000 000 per second); a static `run` script can't use returned IDs, so drive the MCP server and read each result.
- **Drive FilmCraft headless, not through its window:** `filmcraft-cli mcp --project p.fcproj` serves MCP on stdio with an in-process session (`command_run`, `command_batch`, `render_frame`, `sequence_inspect`), which sidesteps the under-tested Windows UI (G9). One `file.exportMedia` call covers delivery: `{"format": "h264", "width": 1080, "height": 1920, "bitrateMode": "crf", "crf": 20, "loudnessLufs": <target>, "burnCaptions": true, "hardwareEncoding": "auto", "wait": true}` (parameters from `crates/engine/src/commands.rs`). Plan in OTIO → `file.import` → effects by command → export.
- **Talking-head / podcast path:** [FunClip](https://github.com/modelscope/FunClip) (MIT, 6.4k stars) for transcript-driven clipping; for active-speaker multicam, [Cutcast](https://github.com/BoazCohenJ/Cutcast) (MIT, Windows, syncs cameras by audio and cuts to whoever talks) and [podcast-editor](https://github.com/vamshicreates/podcast-editor) (MIT) show the method (per-mic RMS dominance, cross-correlation sync), but both have 0–1 stars: read them, don't depend on them. Your existing cross-correlation sync already covers half of it.

**The open-source auto-editing landscape (what exists, and what to take from it)**

| Project | Stars | Licence | What it does | Take |
|---|---|---|---|---|
| [OpenMontage](https://github.com/calesthio/OpenMontage) | 68.0k | AGPL-3.0 | Agentic production system, 12 pipelines, a `music-to-video` skill on a beat grid | Ideas only (AGPL); its skill files are worth reading |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | 62.9k | Apache-2.0 | HTML → video for agents; `/music-to-video`, `/embedded-captions` | The renderer, not the catalog |
| [FunClip](https://github.com/modelscope/FunClip) | 6.4k | MIT | Transcript-driven clipping with LLM picks | Podcast path |
| [auto-editor](https://github.com/WyattBlue/auto-editor) | 5.5k | Unlicense | Cuts silence/dead air by loudness or motion | Talking-head cleanup |
| [podcli](https://github.com/nmbrthirteen/podcli) | 79 | AGPL-3.0 (+ commercial) | Podcast clipper: face tracking, captions, MCP server, multicam | Ideas only |
| [beat-synced-edit](https://github.com/ZiadAbdelkarim/beat-synced-edit) | 13 | MIT | librosa beats + energy peaks matched to scored scenes, anti-repetition | Readable reference for energy-matched cutting |
| Cutcast / podcast-editor | 1 / 0 | MIT | Active-speaker multicam (per-mic RMS, cross-correlation sync) | Reference only |
| [markus](https://github.com/joshchoi4881/markus) `dropspace-dj-clipper` | 9 | MIT | **DJ-set clipper** (Claude Code / Manus skill, Node + ffmpeg): energy peaks, 30–60 s transition clips, centre crop to 9:16, track names from Shazam every 30 s or Whisper lyric matching | The closest thing to Creative Studio; read it for the clip-selection logic. Its weak spots are yours to win: centre crop, Shazam on underground techno, lyrics in techno |
| SendShort "DJ mix" | – | paid SaaS (~$15–79/month, third-party listings) | Audio mix → waveform-visual vertical clips with captions | Not footage editing; sets the price floor for "automatic" |

DJ-set clipping exists, but nothing I found uses Serato's history for track IDs, keeps the DJ in frame, or cuts on the bar grid. That is Creative Studio's ground (and money path 3).

**Shot picking from two synced angles (proposal)**
1. Per shot window (aligned to bars): sharpness (Laplacian variance), exposure, motion energy, face/pose visibility, hands-up count (wrists above head from pose), strobe flashes.
2. Hard rules from the measured benchmark (Top 10 #5): minimum shot length in bars, change angle only on bar or phrase lines, crowd angle at the drop plus ~1 bar (crowd reaction lags the drop).
3. Learn your taste: label ~200 shots keep/skip, train a logistic head on frozen SigLIP embeddings (Apache-2.0). An IEEE paper on autonomous multi-camera editing learned an editor's preferences from 33 scenes with CLIP + SVM (79.7 % of scenes judged "usable"; publication date not confirmed).
4. The LLM only chooses among pre-scored candidates and writes the plan as JSON; it does not watch video.

**Planner and judge in 12 GB**
- **Planner: the Hermes agent model, not a third model.** Qwen3.6-35B-A3B reads images too (its GGUF ships a vision projector; Qwen3.5 projectors don't fit it), and with 16 GB RAM the fallback Qwen3.5-9B is multimodal as well. Constrained JSON via llama.cpp. Defect checks use whichever VLM wins Reel Brain's A/B (Top 10 #3). Every extra model is another swap on one card.
- **Don't let a model judge taste.** Timeline-Bench (arXiv 2609.35143, Sep 2026) gave agents 56 realistic raw-footage editing tasks: the best resolved 26.8 %, the average 14 %, and most failed runs failed *only* the quality test, which the authors attribute to agents judging footage through stills and transcripts rather than craft. Pairwise LLM judges still flip with presentation order in up to 20 % of cases (J1, 2025). Use the VLM as a **defect checker** with yes/no questions on contact sheets (text over a face? cut mid-word? black or frozen frames? drop missing? first frame dark?) and keep the taste pick for yourself or for Trial Reels.
- **Keep the planner's output tool-neutral.** The plan should be a small JSON of cuts (source, in, duration), subject samples, captions and export settings, not FilmCraft command IDs, which change fast (upstream merged hundreds of PRs in October). [`plan_to_filmcraft.py`](prototypes/plan_to_filmcraft.py) is the FilmCraft back end for exactly that shape (tested, 2.1 above). For a fallback editor, FilmCraft's `file.exportOtio` writes the built timeline as OpenTimelineIO, which Resolve imports, so a FilmCraft build that misbehaves on Windows costs a day, not a rewrite. Pin the fork to a release tag (latest: v0.7.2, 2026-10-12) rather than tracking `main`; your fork's `main` was 433 commits behind upstream on 2026-10-13 and predates v0.7.2, so sync to that tag before building Creative Studio on it.

**Virality score → real tests**
- **Why:** predicting engagement from content alone explains roughly 20–30 % of variance in a 2026 study (R² 0.21–0.29); the best VQualA 2025 challenge entry reached SROCC 0.71 on its own dataset. A local score ranking three of your variants is mostly noise.
- **Do:** keep a cheap pre-filter (hook in first 2 s, drop present, no black frames), then publish variants as **Instagram Trial Reels** (shown to non-followers only) and log views, 3-second holds and shares per variant. After ~30 posts, fit your own ranking on your own data.
- **Confidence: medium.** The research is solid; Trial Reels availability for your account in Egypt is unverified (eligibility has been limited to professional accounts).
- **First step:** check whether the "Trial" toggle appears when you share a reel from a professional account.

**Drop or avoid**
- Qwen-Image 2.1 for anything paid (licence).
- A virality model as the ranking signal (see "Virality score → real tests" above).
- Ultralytics YOLO in anything that touches the MIT/Apache fork (AGPL).
- **MiniMax H3 for client work, for now:** its community licence reportedly bars local deployment in the US, EU, UK and South Korea (Egypt not listed), local weights top out around 768p, and on 12 GB community guides put the floor at ~0.4 MP with heavy offload and 32–64 GB RAM. Generated video also undercuts what a club clip sells: that it was real. Use it for abstract background plates at most.
- All-In-One music structure analyser for production use: MIT but last commit 2023-10-10 and needs NATTEN built from source on Windows.

**Models (12 GB)**
| Job | Model | Licence | VRAM (approx.) |
|---|---|---|---|
| Beats/downbeats | Beat This `small0` (the small models did better on constant tempo in the Giant Steps run) | MIT | < 1 GB |
| Planner | Hermes' agent model (Qwen3.6-35B-A3B + mmproj, or Qwen3.5-9B) | Apache-2.0 | shared with Hermes |
| Defect checker | The Reel Brain VLM that wins the A/B | per model | shared with Reel Brain |
| Pose | RTMPose (rtmlib, ONNX) | Apache-2.0 | < 1 GB |
| Taste head | SigLIP base + logistic | Apache-2.0 | < 1 GB |
| Stills (commercial) | FLUX.2 klein 4B / Z-Image-Turbo | Apache-2.0 | ~8–13 GB / ~6–10 GB quantized |
| Video gen (personal) | MiniMax H3 Q4 GGUF | MiniMax community licence | ~11.6 GB file + offload |
| Egyptian Arabic / code-switched speech | [QwenCleo-ASR](https://github.com/MohammedAly22/qwencleo-asr) (Qwen3-ASR-1.7B fine-tune; 19 stars, self-reported benchmark) or Cohere Transcribe Arabic (2B, 2026-07); paid: ElevenLabs Scribe (~$0.40/audio hour, word timings) | Apache-2.0 / Apache-2.0 / paid API | ~4–6 GB / cloud |
| English speech + word timings | faster-whisper / whisperX large-v3 | MIT / BSD-2 | ~3–5 GB |
| Arabic word timings (for animated captions) | [ctc-forced-aligner](https://github.com/MahmoudAshraf97/ctc-forced-aligner) + `jonatasgrosman/wav2vec2-large-xlsr-53-arabic` | BSD-2 code; check the model card | ~1–2 GB |

**Egyptian-Arabic captions need a second model for timing.** QwenCleo returns text only, and Qwen's own forced
aligner (Qwen3-ForcedAligner-0.6B) covers 11 languages, **not Arabic** ([qwen-asr on PyPI](https://pypi.org/project/qwen-asr/)).
Word-by-word captions (what the Upwork Arabic clip jobs ask for) therefore need: QwenCleo text → a CTC forced
aligner. ctc-forced-aligner (BSD-2, 2026-09) does it, but **its default MMS model is CC BY-NC 4.0** (its README
says so), so for paid clips pass an Arabic wav2vec2 model instead; whisperX uses
`jonatasgrosman/wav2vec2-large-xlsr-53-arabic` for Arabic (I couldn't open its card; the author's models are
usually Apache-2.0). Pitfall: English words inside Egyptian speech are not in an Arabic character vocabulary, so
expect to interpolate their times; check ten code-switched lines by eye before selling this. Cohere Transcribe
Arabic's timestamp support is reported both ways; check its model card before counting on it.

**The paid option that may simply win for client captions:** [ElevenLabs Scribe](https://elevenlabs.io/speech-to-text/arabic)
returns word-level timestamps in Arabic, lists Egyptian among the accents it covers, and costs about **$0.40 per
audio hour** (about a cent per clip). Nobody has published an Egyptian-dialect error rate for it. Run the same ten
minutes of your Egyptian audio through both QwenCleo + aligner and Scribe and score them by hand: if Scribe is within a
few points, use it for paid clips (a day of aligner work saved) and keep QwenCleo for private material.

**Auto-posting: what the platforms allow**
- **Instagram:** the Instagram API with Instagram Login publishes reels from a professional account without a Facebook Page; the cap is 50 or 100 API posts per 24 h depending on which Meta page you read (query `GET /<IG_ID>/content_publishing_limit` for the live value); the video must sit at a public URL when you publish.
- **TikTok:** an unaudited Content Posting API client can only post **private** videos from private accounts, up to 5 users a day; the audit reportedly takes 2–4 weeks and needs a demo video. Until then, "auto-post to TikTok" means "upload as draft/private". (Creator Rewards is not available in Egypt anyway.)
- **YouTube:** uploads from an unverified API project created after 2020-07-28 are locked to **private** until the project passes a compliance audit.
- **Postiz** (AGPL-3.0, self-hosted scheduler for 30+ platforms) is fine to run as a separate service, but it inherits all of the above approvals; it does not get around them.

**Open risks**
- FilmCraft upstream's own gap list: Windows runtime is under-tested (G9), no PR CI (G4), and **10-bit / 4:2:2 H.264/HEVC does not decode on Windows without hardware support** (G3). If your camera records 10-bit 4:2:2, transcode to 8-bit 4:2:0 before ingest or the import fails.
- **Arabic text:** burned-in Arabic captions render correctly in a build with craft-fonts, or once the caption track's font is an Arabic face (both tested; see 1. #8). In a plain build with the default font they come out as empty boxes (upstream #1475, fix #1478 open). Graphics-layer titles have the same fallback, so name an Arabic font there too.
- **Fallback renderer:** DaVinci Resolve Studio 21.1 ($295 one-time) now has a native MCP server; with the plan kept in OTIO it is a one-day switch if FilmCraft blocks you on Windows (see 5b).
- **Noisy low-light footage** is a bigger "cheap" signal than any graphic. Try ffmpeg's `nlmeans`/`hqdn3d` as an external pre-pass first; DaVinci Resolve Studio's temporal noise reduction ($295 one-time) is the standard paid fix if that is not enough.
- **Client work: deliver, don't auto-post.** A collective will want to approve posts and will not hand you its account; keep auto-posting for your own channels.
- Copyright: club clips carry other artists' tracks. Instagram mutes or limits; plan captions and track IDs (Serato history gives you artist and title for free), and keep originals.

### 2.2 Hermes + Laya

**Adopt**
- Hermes' managed llama.cpp runtime or your own `llama-server` (`providers.llamacpp.base_url`), Top 10 #4.
- `hermes prompt-size` and `hermes tools` to cut the fixed prompt; **Tool Search only once the `tool_call` → `invoke_tool` rename ships** (Top 10 #4).
- **Acting on plans:** `/goal` (judge-driven loop in one session), cron (including **no-agent mode**: a script on a schedule with zero LLM calls, ideal for queue drains and nightly batches), and Kanban cards created with `--goal` for multi-step work. A plan note in the vault becomes Kanban cards; cron jobs read the vault and report back to Telegram.
- **Kanban** (built in, SQLite `~/.hermes/kanban.db`, per-task model override, durable handoffs, retries, circuit breaker) for multi-agent work instead of a new orchestrator. Hermes' own docs position it as the reliable alternative to in-process subagent swarms.
- **Memory:** keep Hermes' built-in `MEMORY.md`/`USER.md` small and make the Obsidian vault the knowledge store, reached through one MCP server: [MCPVault](https://github.com/bitbonsai/mcpvault) (MIT, active, works on the files directly, no Obsidian process needed, confined to the vault root). Alternatives: cyanheads/obsidian-mcp-server (Apache-2.0, needs the Local REST API plugin), Basic Memory (AGPL-3.0, fine as a separate process, but it imposes its own note conventions on top of your LLM-wiki structure). Note that the Smart Connections plugin moved to a proprietary "Smart Plugins License". Of Hermes' memory plugins, only Holographic (local SQLite + FTS5) and ByteRover (local) are local-only; RetainDB and ByteRover leave Hermes core on 2026-10-15.

**Laya (router)** — see Top 10 #2 for the evidence.
- Labels have to come from outside Laya: your corrections (a "wrong route" button in Telegram), implicit signals (you re-ask, you switch model by hand, the task fails), and a teacher model labelling logged messages overnight. Fine-tuning on Laya's own logged guesses teaches it nothing.
- Route by calibrated `answer_confidence`; below the threshold, fall back to the main LLM and queue the message for labelling.
- Keep the EmbeddingGemma-300M + logistic-regression baseline running in shadow mode: it costs milliseconds on CPU and tells you whether Laya's fine-tune is earning its 0.4–0.8 s.
- Question design: one coarse question (which agent/tool family) then a fine one, ≤ ~20 options each, opaque labels (`A`/`B`) rather than yes/no words.

**Drop or avoid**
- A second orchestrator framework (CrewAI, LangGraph) on top of Hermes: Kanban plus delegation covers it.
- Gemma 4 31B (Hermes' docs call it the most reliable local tool-caller) on 12 GB: ~20 GB, will not fit.

**Models**
| Use | Model | VRAM / RAM |
|---|---|---|
| Daily driver (≥32 GB RAM) | Qwen3.6-35B-A3B Q4 + `--n-cpu-moe ~24` | ~11 GB VRAM + ~12 GB RAM |
| Daily driver (16 GB RAM) | Qwen3.5-9B Q5/Q6 | ~7–9 GB VRAM |
| Router | Laya (`laya` 421M ModernBERT-large / `laya-multilingual` 322M mmBERT-base), fine-tuned | CPU, 0.4–0.8 s with pinned threads |
| Router baseline | EmbeddingGemma-300M + logistic regression | CPU, milliseconds |

**Open risks:** Qwen 3.5/3.6 tool-call templates are fragile across servers (Ollama [#14493](https://github.com/ollama/ollama/issues/14493), Hermes #29677; on llama-server pass `--jinja` plus the right `--chat-template-file`). Hermes' 48k open issues/PRs means fast churn: pin a version.

### 2.3 Reel Brain

**Adopt**
- Frame-token budget, Qwen's recommended sampling, a higher quant and bounded schemas for the VLM (Top 10 #3). Try **GLM-4.6V-Flash** (9B, MIT per listings) beside Qwen3-VL-8B.
- **Add the agent model to the A/B.** If Qwen3.6-35B-A3B with its projector matches the best VLM on the 20 failing reels, use it for everything: Hermes, planner and Reel Brain then share one loaded model and never swap. It will be slower per reel (prompt processing runs partly on CPU experts), which a night batch can afford.
- **Try Qwen3.5-9B against Qwen3-VL-8B** on 30 reels: Qwen says 3.5's early-fusion training beats Qwen3-VL on visual understanding (vendor claim). MiniCPM-V 4.5 (8.7B, reports 73.5 on Video-MME, llama.cpp support since b6282) is the video-specialised alternative; its weights have historically been under the custom MiniCPM Model License (commercial use after a registration form), which is fine for a personal pipeline.
- Linear probe + top-3 classification; repo verification with a "no repo" outcome (below).
- Port ideas from juspay/dopamine: link resolver that remembers failed lookups, verifier, project mapper with "avoid".
- Run batches through llama-swap with per-item checkpoints (SQLite job table) so a crash costs one reel, not the run.
- **Do less GPU work per reel.** Classify and summarise from caption + transcript + OCR first (CPU or a small model), and call the VLM only when the frames carry information the text does not (screen recordings, UI demos, diagrams). On talking-head reels the transcript is the content.

**Classification and repo linking**
- **Why:** kNN at 63 % is a weak baseline. A logistic-regression "linear probe" on the same embeddings usually beats kNN once you have ~1,000 labels; showing the top 3 turns a 63 % top-1 into a much higher hit rate for one click. For repos, a published study (SONAD) found LLMs over-accept candidates (precision 68 %, recall 97 %) while a feature-based verifier reached 82 % precision.
- **Do:** (a) re-label 50 random reels blind to find your own consistency ceiling; (b) linear probe + top-3 + LLM rerank only when the top-2 margin is small; (c) for repos, three tiers: **first** regex the OCR text, caption and transcript for explicit `github.com/owner/repo`, `owner/repo` and Hugging Face `org/model` strings and confirm they exist (tech reels very often show the repo page on screen); **then** candidates from GitHub/Hugging Face search, scored on exact name match, owner, README similarity to the reel's context and stars; **else** "no repo" (many tools in reels are closed SaaS products). Your whatstheID `verify.py` already encodes the right rules (empty is a refusal, exact-match preference, word-level coverage × precision).
- **Borrow ideas from:** [juspay/dopamine](https://github.com/juspay/dopamine) (MIT, active, but **1 star**: a fresh repo, not a proven tool), the same pipeline on Gemini; its project mapper (embedding prefilter + judge with an "avoid" field per project) is the shape your per-project ranking needs.
- **Confidence: medium.**
- **First step:** the 50-item blind re-label.

**How others build "save → second brain"**: Dopamine (above, Gemini, MIT); a ColdIQ guide (hourly Mac job → enriched Obsidian notes, behind an email gate, uses Apify + instagrapi); [Karakeep](https://github.com/karakeep-app/karakeep) (AGPL-3.0, self-hosted bookmark manager with AI tagging through Ollama, good as a capture inbox); your own claude-obsidian / LLM-wiki vault. None does per-project ranking against your own project list as well as Dopamine's mapper, and none runs fully local on a 12 GB card; yours is already ahead on that axis.

**Drop or avoid**
- instagrapi for collecting saves (Dopamine uses it; it logs into your account through a private API and risks a ban). Use Instagram's own "Download your information" export (JSON) for the list of saved items, then fetch only what you need. If yt-dlp needs your cookies to fetch a reel, throttle it like a person (`--sleep-requests 2 --sleep-interval 5 --max-sleep-interval 20`) and run the backlog over several nights rather than one: a burst of hundreds of logged-in requests is what gets accounts checkpointed.

**Models**
| Use | Model | VRAM |
|---|---|---|
| Transcript (English) | faster-whisper large-v3 (MIT) int8 | ~3–5 GB |
| Transcript (Egyptian Arabic / mixed) | QwenCleo-ASR 1.7B (Apache-2.0) | ~4–6 GB |
| Frames → notes | Qwen3-VL-8B or Qwen3.5-9B Q5 + mmproj | ~7–8 GB |
| Collections | EmbeddingGemma-300M + logistic head | CPU |

### 2.4 whatstheID

What you already have (from the repo): shazamio + AudD, your own landmark fingerprinter with a query-side speed ladder, comb-filter tempo (0.01 BPM MAE vs Serato on 17 tracks), a key ensemble, a read-only Serato parser, a hand-written WebGL2 engine. Not on `main`: Serato write-back, Soulseek.

**Adopt**
- **Beat/downbeat trackers for electronic music, with the numbers that exist:**

| Tracker | Licence | Evidence on electronic music | Verdict |
|---|---|---|---|
| Your comb-filter tempo (`analyze.py`) | yours | 0.01 BPM mean error vs Serato on 17 tracks, 15/17 exact | Keep for tempo |
| [Beat This](https://github.com/CPJKU/beat_this) | MIT (code + weights) | Giant Steps (664 Beatport tracks): 89.3 % strict / 95.0 % octave-tolerant tempo; small-model ensemble 90.9 / 96.4 % | Use for beat and downbeat positions |
| madmom | BSD code, CC BY-NC-SA models | Raveform (TISMIR 2026): competitive on EDM beats, "lags significantly" on downbeats (not trained on EDM) | Avoid (licence + downbeats) |
| All-In-One | MIT | Uses madmom-style DBN; last commit 2023-10-10; NATTEN build on Windows | Avoid |
| librosa `beat_track` | ISC | Tempo snaps to its frame grid (your own notes: 6 BPM steps near 125; my test: 150 read as 152) | Fallback only, with regression on beat times |
| Raveform models | MIT repo (empty) | Trained on 1,423 EDM tracks with metrical + functional (section) annotations, per the paper | Watch: GitHub repo was only a licence file on 2026-10-14 |

- rb2serato encoders for grids and cues (Top 10 #10). [serato-tools](https://pypi.org/project/serato-tools/) (Python ≥3.12) is an alternative; it also writes multi-marker "dynamic" grids from a librosa analysis (MIT source), which constant-tempo techno doesn't need and your comb filter beats, and it edits Serato 3's `database V2`, not Serato 4's SQLite; **pyserato is AGPL-3.0**, avoid if you ever distribute.
- **Rekordbox:** [pyrekordbox](https://github.com/dylanljones/pyrekordbox) (MIT, active): its XML writer has `Track.add_tempo(Inizio, Bpm, Metro, Battito)`, one `TEMPO` element per grid section, which is how Rekordbox XML carries tempo changes; it also reads Rekordbox's own ANLZ beat grids.
- **Cue points and phrases:** [CUE-DETR](https://github.com/ETH-DISCO/cue-detr) (MIT code, 2024) detects DJ cue points as objects on a spectrogram and ships the EDM-CUE dataset (4,710 tracks, ~21k cues placed by professional DJs). Its authors found most training tracks use **16-bar phrases, then 8-bar**, so don't hard-code 32. Check the checkpoint/dataset licence before shipping anything built on them.
- **Don't rebuild conversion:** Lexicon (paid DJ library manager) has had a **free plan for importing and converting libraries between DJ apps** since v1.9 (Sep 2025) and supports Serato 4's database since v1.10. whatstheID's grid analysis tuned for techno is the part worth building; app-to-app conversion is solved.
- **Grid quality:** fit the grid to the **kick attack**, not the energy peak (onset of the low band's envelope rise), per beat, then least-squares the tempo. rb2serato measured Serato's grid a median 8 ms ahead of Rekordbox's on 1,563 MP3s: check your offset against Serato on your own files.
- **Downbeats/phrases:** score each of the 4 bar phases (and 8/16-bar phrase phases) by how well novelty peaks (energy, new elements, breakdown edges) land on them. Half-time D&B: prefer 170–176 over 85–88 by genre prior.
- **IDs in long mixes:** segment first (novelty), then query the middle of each segment where one track plays alone, instead of a fixed 60 s grid; keep the speed ladder.
- **Replace shazamio with AudD's enterprise endpoint as the cloud fallback** (see 5b): documented, takes hours-long files, bills per 12 s processed, roughly $0.12–0.30 per two-hour mix at one sample per 2 minutes; your own notes already measured it naming 3 of 6 underground records to Shazam's 0.
- **Reference rbxport** ([rbxport.com](https://rbxport.com/)): a free Rekordbox library manager (not open source) by Chris Le, who also wrote [serato-connect](https://github.com/chrisle/serato-connect) (MIT). Its grid analysis is "tuned for electronic music"; I could not read details (site unreachable).
- **Visualiser:** drive shaders from beat/bar/phrase *phase* from your analysis, not raw FFT amplitude: visuals lock to the music's structure. Butterchurn (MIT, Milkdrop in WebGL) is a reference; Hydra is AGPL.

**Avoid:** Panako and Olaf (both AGPL-3.0) as code; read their papers for the tempo-invariant ideas. PeakNetFP ([code](https://github.com/guillemcortes/peaknetfp), ISMIR-era 2025, BMAT/Deezer/UPF) reports >90 % top-1 for time-stretch factors from 50 % to 200 %, but its repository is **CC BY-NC-SA 4.0**: personal use only, never in something you sell or share commercially. Your query-side speed ladder already covers the ±8 % a techno DJ realistically uses.

**Licences in your current whatstheID stack (checked on PyPI, round 20):** fastapi, uvicorn, pydantic (MIT/BSD), yt-dlp (Unlicense), shazamio (MIT), librosa (ISC) are permissive; **mutagen, which `app/tags.py` uses, is GPL-2.0-or-later**, and serato-tools requires it too. For a personal tool that changes nothing. If you share whatstheID with other DJs as a download, license it GPL-compatible (simplest: GPL-3.0) or replace mutagen; nothing from it can go into the MIT/Apache FilmCraft fork.

**Soulseek-first downloads (not on `main` yet):** slskd is AGPL-3.0; calling its HTTP API from whatstheID as a separate process does not make whatstheID AGPL, but bundling or modifying slskd would. For a tool you share with other DJs, automated P2P downloading is also the part most likely to draw complaints: keep it a user-configured option, not a default.

**Sharing it with other DJs: the field is not empty.** TrackSniff (web, free 50 IDs/month, $9–19/month; mixed accuracy in one academy's test), Mixprism, audioscout.io and AudD (says it handles hours-long mixes; $2–5 per 1,000 requests after 300 free) already do "paste a mix, get a tracklist". What none of them do is what whatstheID already does: **fingerprint against the DJ's own library** (your `fingerprint.py` notes that Shazam named 0 of 6 underground records and AudD 3) and write grids back to Serato. Lead with that; treat cloud ID as a fallback.

### 2.5 Inspiration Canvas (idea stage)

**Recommendation: do not build a canvas app yet. Build the board format first, inside your Obsidian vault.**
- Store boards as **JSON Canvas** (`.canvas`, open spec v1.0, MIT, what Obsidian Canvas uses): `file` nodes for images and videos, `text`, `link` and `group` nodes, edges for relations ([spec](https://github.com/obsidianmd/jsoncanvas/blob/main/spec/1.0.md)). Any LLM can read and write it; Obsidian renders it for free; Kinopio imports and exports it; there are Python (PyJSONCanvas), TypeScript and Rust (`jsoncanvas` crate) libraries if you ever build your own viewer.
- A "look pack" = a folder with the images, a `look.md` (palette, type, motion rules, what to avoid) and a `.canvas` board. Creative Studio reads `look.md`.
- Imports: Instagram via the official data export (same as Reel Brain); Pinterest via its data export or API v5 Trial access (reading your own boards and pins is allowed on Trial; approval is reported as slow).
- If you later want a real app: tldraw needs a licence key in production but runs free in development mode on `localhost`; Excalidraw is MIT. A FilmCraft extension would mean egui work in a Rust app whose Windows runtime is already the weak spot: no.
- **The paid option that may simply win:** Eagle (eagle.cool), a local image/video reference manager with a browser extension and plugin system, **$34.95 one-time for two devices**, 30-day trial. If what you want is "collect and tag fast", it already does that; a small exporter from Eagle's library folder to `.canvas` + `look.md` gives Claude the read access.

---

## 3. Cross-project shared pieces

1. **llama-swap in front of every GPU server, plus the DJ guard** (Top 10 #6): one place to load, unload and measure, instead of Ollama, Hermes' runtime and ComfyUI each holding their own copy of the card.
2. **One small labelled set per project, kept in the vault:** 200 Laya routes, 20 failing reels + 50 blind re-labels, 40 reference clips + your keep/skip shot labels, 17+ Serato reference grids (you already have these). Every change gets measured against them, which is how whatstheID got its tempo error to 0.01 BPM.
3. **One vault access layer:** a single MCP server over the Obsidian vault (read/write notes, search by text and embeddings) used by Hermes, Claude Code, Reel Brain and the canvas. You already write to the vault via `learn-to-vault` / claude-obsidian (Karpathy LLM-wiki pattern); don't add a second memory database that drifts from it.
4. **One verification module** for "does this search hit really match": whatstheID's `verify.py` rules reused for Reel Brain's tool→repo links.
5. **Shared audio analysis:** whatstheID's comb-filter tempo and key code, Beat This, and Serato readers serve both whatstheID and Creative Studio.
6. **Shared embeddings:** EmbeddingGemma for the Laya baseline, Reel Brain's collections and canvas search.
7. **One vision-language model where possible:** the Hermes agent model doubles as Creative Studio's planner, and if it wins Reel Brain's A/B it does that job too (2.3). Fewer models means fewer swaps on one card.
8. **One security rule across the vault (round 17).** Reel Brain writes text that strangers wrote (captions, transcripts, on-screen text) into the vault, and Hermes reads the vault with a shell, MCP tools and a Telegram front door. That is the classic indirect prompt-injection path. Cheap defences, all built in: `TELEGRAM_ALLOWED_USERS` set to your ID only; Hermes' `approvals.mode` left at `smart` or `manual` (never `/yolo` on the gateway) and `cron_mode: deny` (the default) for night jobs; give agents that only need to read the vault a second [MCPVault](https://github.com/bitbonsai/mcpvault) instance started with `--read-only`; keep reel notes in their own folder and write "untrusted content from a saved reel" at the top of each one. A repo found in a reel is a lead, not an install: installing it is always your decision, never a plan step an agent acts on alone.

---

## 4. Money (checked for Egypt in round 7)

**What the platforms allow from Egypt (verified as far as I could):**
- **YouTube Partner Program:** Egypt is on Google's list of countries where the expanded programme is available. Ad revenue needs 1,000 subscribers plus 4,000 watch hours in 12 months or 10 M Shorts views in 90 days. Club clips full of other artists' tracks will mostly be Content-ID claimed, so the revenue goes to the rights holders.
- **TikTok Creator Rewards:** not available in Egypt (your note). **Instagram creator monetisation:** I found no evidence Egypt is eligible (one undated post says it isn't). **Facebook Content Monetization:** invitation-only; Egypt had the older creator programme, current status unconfirmed.
- **Getting paid from abroad:** Payoneer is the standard rail: ~1 % on marketplace receipts plus ~1.85–2 % FX into EGP, so ~3 % all-in, and a $29.95 annual fee if you receive under $2,000 in 12 months. PayPal withdrawals in Egypt are EGP-only at a marked-up rate. Wise is limited for Egyptian residents. Upwork charges a variable 0–15 % fee (≈10 % typical) and $0.99 per Direct-to-Local-Bank withdrawal (EGP availability: check in your Get Paid settings). Fiverr takes 20 % and pays out via Payoneer or "bank transfer powered by Payoneer" ($1 fee, $20 minimum).
- **Local clients:** InstaPay (EGP, instant). The last published caps I found were EGP 70k per transaction / 120k per day / 400k per month (may have changed).
- **Selling software from Egypt is awkward:** a Gumroad codebase mirror lists Egypt among countries excluded from PayPal payouts; Lemon Squeezy's bank-payout list could not be checked for Egypt. Sell services first.

**Paths, best first**

1. **Next-morning clip packs for Cairo collectives and venues.** Geeza, MOSHTRQ, INTG, BackSpin and Analog Room are active (per SceneNoise); Cairo Jazz Club hosts several. The pitch is not "AI clips", it is **speed**: three finished vertical clips with track IDs by the next morning, while the night is still being talked about. That is exactly what your pipeline is for. Paid in EGP, no FX, no platform fee. Be realistic about the price: I found **no published EGP prices for event reels**, but the local anchors are low. On Khamsat (the Arabic freelance marketplace) reel-editing services sit at **$5–50**, typically $20–25 for a reel under 60 s; an Egyptian creator reported **100 EGP** as the cheapest short-video edit he found; one Cairo agency's reel *shooting* packages start at **EGP 3,000**; Upwork lists Cairo videographers at $20–45/hour asking rates. Locally this is a portfolio-and-relationships play that pays modestly; the dollars are in paths 2–3 and in retainers. Your own clip channel is portfolio, not income: Content ID and Egypt's platform availability block most monetisation of DJ clips. *First test (one week):* offer one collective a free pack from their next night in exchange for footage access, a testimonial and their post stats (cut it by hand in whatever editor is fastest for you if the pipeline isn't ready: this tests demand, not automation); ask three local videographers for a quote on the same job so you know the market; quote the second night.
2. **Egyptian-Arabic and code-switched podcast/founder clips on Upwork.** Demand exists but is cheap: one May 2026 job paid **$50 fixed** for a 30–45 s Arabic clip with animated captions and drew 10–15 proposals; Arabic documentary editing posts at **$10–25/hour**; a Saudi EdTech post wants an Arabic motion editor on a monthly retainer after a paid test. Generic clipping is a race to the bottom (Fiverr's podcast-shorts gigs start at **$10–45 per clip**, ~736 services in one category; AI tools cost ~$1/episode). Your edge is caption accuracy in Egyptian dialect (QwenCleo-ASR's reported 19.9 % vs Whisper's 63.9 % WER) and Arabic typography that is shaped correctly. Animated word-by-word captions also need word timings, which QwenCleo doesn't give: budget a day for the forced-alignment step in 2.1. **Your claimed edge has not been measured against what a client can do alone:** Submagic and Opus Clip both sell Arabic auto-captions, and no independent test of either on Egyptian dialect exists. Before pitching "better Egyptian captions", run one 2-minute code-switched clip through Submagic's free tier and through your pipeline and count errors; if theirs is close, sell typography and speed instead. *First test:* that comparison, three portfolio clips from a podcaster who agrees to it (or your own talk), then ten proposals to Arabic clip jobs in a week; track replies, not just wins.
3. **Set-to-clips packs for DJs abroad (Fiverr, Contra).** Send me your set video, get five vertical clips by the next day: beat-locked cuts, the DJ kept in frame, and **correct track IDs** (from the DJ's Serato history or your library fingerprinter, where the off-the-shelf clippers rely on Shazam, which named none of your six underground test records). Demand evidence is thin but real: one Fiverr seller edits DJ live sets for **$50–100** a project with reviews; beginner short-form editors charge $25–75 a clip; the automatic competition is SendShort's DJ-mix tool (~$15–79/month by third-party listings, waveform videos from audio, not footage) and an MIT Claude Code skill (markus' dj-clipper: energy peaks, centre crop, Shazam every 30 s). Fiverr pays out from Egypt via Payoneer and keeps 20 %. *First test (one week):* a gig with three sample clips cut from your own sets, plus 20 direct messages to DJs who post full sets with no clips; count replies and one paid order.
4. **Agent setup (Hermes/OpenClaw + Obsidian) gigs.** Fiverr already has OpenClaw/Hermes setup gigs at **$50–200**, mostly with few reviews; freelance guides quote $150–400 per client. Demand evidence is thin and promotional. Your config is the product, and it is cheap to try. *First test:* one gig, one public write-up of your setup, count inquiries after a week.
5. **whatstheID as a product: not yet.** The tracklist space is crowded (TrackSniff $9–19/month, AudD, Mixprism), Lexicon's free tier converts libraries, and payouts for software sales from Egypt are unclear. Open-source the Serato grid writer for reputation if you like; sell analysis or setup as a service later.

**Hidden costs of running all this from Cairo (round 13)**

| Cost | Size | Note |
|---|---|---|
| **Data quota** for the first two weeks of downloads | **≈ 100 GB** | Qwen3.6-35B-A3B Q4_K_M ≈ 21 GB, each 8–9B VLM at Q8 ≈ 9–10 GB (three in the A/B ≈ 30 GB), FLUX.2 klein 4B + its Qwen3-4B text encoder ≈ 12 GB, Z-Image-Turbo ≈ 12 GB, QwenCleo + Whisper ≈ 7 GB, one torch install per venv ≈ 3 GB × 3, CUDA DLL archives ≈ 2 GB, 40 reference clips ≈ 1–2 GB (sizes are file-size arithmetic, ±20 %). WE home tiers reportedly run 140 GB (EGP 230) to 1 TB (EGP 1,400) a month (aggregator, March 2026; check te.eg). On a 140 GB plan, cut the VLM A/B to two candidates and skip Z-Image until FLUX.2 klein disappoints. |
| **Electricity** for night batches | ≈ 100 kWh/month if the PC runs ~450 W for 7–8 h every night | ≈ EGP 170–240/month at the 1.72–2.18 EGP/kWh brackets a household with air-conditioning is likely in after the August 2026 increase (reported rates; verify on your bill). More if it pushes the household into the next bracket. Run batches when there is a queue, not every night. |
| **Upwork Connects** for money path 2's test | ≈ $10–25 | $0.15 per Connect; a proposal costs about 2–16 Connects depending on the job; they aren't refunded when you lose. Needs a card that pays abroad. |
| Payoneer | $29.95/year | Only if you receive under $2,000 in 12 months |
| Paid tools, only if they win | $295 Resolve Studio, $34.95 Eagle, ~$0.12–0.30 per mix AudD | None is needed in the first week |
| **Your time** | the real budget | Five projects plus a fork; every number in the Top 10's "effort" column comes out of the same evenings |

## 5. What I got wrong along the way

The biggest calls the audits killed or reversed (details and dates in `audit-log.md`):

1. **"Ollama ignores repetition penalties, so switch servers to stop the looping JSON."** True once, fixed in Ollama 0.30.0 (July 2026). The likelier causes on your exact stack are image tokens overflowing `num_ctx` (an open issue reproduced on an RTX 3080 under Windows), greedy decoding and 4-bit quants. *Watch for:* bug reports age fast; check the closing comment, not just the title.
2. **"Turn on Hermes Tool Search to shrink the prompt."** It breaks Qwen models: the bridge tool is named `tool_call`, the same word as Qwen's template tag. *Watch for:* features that work with the vendor's default model and not with yours.
3. **"Let a local VLM judge rank the three variants."** Agents judging edits from stills fail mostly on craft (Timeline-Bench), and pairwise judges flip with presentation order. Demoted to a defect checker. *Watch for:* using a model to grade taste.
4. **"Write a GPU broker", then "free ComfyUI through llama-swap when Serato starts".** llama-swap already does the brokering, ComfyUI included. And my DJ guard's ComfyUI call went through llama-swap's `/comfyui/` route, which *starts* ComfyUI: in a test against the real binary, DJ mode ended with ComfyUI on the GPU. The guard now uses a `dj` profile plus re-unloading. *Watch for:* building infrastructure before searching for it, and trusting glue code you haven't run against the real thing.
5. **"Replace Laya with embeddings + logistic regression."** Written before I knew what Laya was. Laya is built to be fine-tuned; the real problem is that it runs zero-shot. *Watch for:* advice about a component nobody has looked at.
6. **"rb2serato is verified on 9,600 tracks, use its encoders."** Still the best code I found, but it has one star and one author. *Watch for:* confident READMEs with no users.
7. **"The collective is the first income."** Local reel editing goes for as little as 100 EGP; it is a portfolio play. The dollars are in Arabic-dialect clips for remote clients.
8. **"Qwen3.6 runs at ~36 tok/s on a 12 GB card", then "up to 47 tok/s at `--n-cpu-moe 18`".** The first was untraceable; the second used a setting that can't hold Q4_K_M experts in 12 GB, and my example config's `--n-cpu-moe 22` would probably have run out of VRAM too. Now ~35–45 tok/s from two traceable reports, with llama.cpp's `--fit` choosing the offload. *Watch for:* benchmark numbers without the quant and context they were run at.
9. **"FilmCraft can't do Arabic; set Arabic in the HTML layer."** Based on an upstream bug title. I built the fork and burned an Egyptian caption into an export: with the caption font set to an Arabic face it renders correctly; only the default font fails. (Smaller catch in the same area: FilmCraft drops VP9 alpha, so overlays go in as ProRes 4444, not WebM.) *Watch for:* bug titles standing in for a test.
10. **"QwenCleo-ASR covers the Egyptian-Arabic caption job."** It covers the words, not their timing: Qwen's forced aligner skips Arabic, and the obvious substitute's default model is non-commercial. Word-by-word captions need a second, commercially licensed aligner. *Watch for:* a benchmark on the easy half of a job (WER) standing in for the whole job (timed captions).

## 5b. Steelman: one rejected option per project, argued for

- **Creative Studio: render in DaVinci Resolve Studio instead of FilmCraft.** *For:* Resolve 21.1 (September 2026) ships a **native MCP server** that Blackmagic says lets Claude and Codex drive Resolve Studio through its official scripting API; community servers on Glama list 53 to 295+ tools (e.g. [resolve-mcp](https://glama.ai/mcp/servers/irstone-source/resolve-mcp), MIT) covering timelines, import, grading and rendering. Resolve is proven on Windows, decodes 10-bit 4:2:2 camera files, has temporal noise reduction and AI reframing, and imports OTIO. *Against:* $295 one-time; closed source; 21.1 also **moved Python scripting out of the free edition**, so automation means Studio; the MCP server is weeks old. *Verdict:* not instead, but as the fallback. Keep the plan in OTIO (Top 10 tip in 2.1) so that if FilmCraft blocks you on Windows (crashes, 10-bit footage, Arabic text), switching renderers costs a day and $295, not a rewrite.
- **Hermes + Laya: drop Laya entirely and let the main model route.** *For:* zero-shot Laya is near chance by its own README; Qwen3.6 at ~40 tok/s can classify a message in a second or two and is probably more accurate than an untuned 400M encoder; one less moving part. *Against:* every message would wake the GPU model (contention with ComfyUI and Reel Brain), and Laya is free to run on CPU. *Verdict:* it wins **if you won't label 2–3k messages**. If you will, the fine-tuned Laya is cheaper per message and keeps the GPU free.
- **Reel Brain: send the backlog to a cloud video model.** *For:* your saved reels are public content, so privacy is not the usual objection; a hosted Gemini-class model reads video and audio natively, returns schema-constrained JSON, and takes the 1,000-reel backlog off your GPU entirely (no loops on your card, no crashes). Dopamine does exactly this. *Against:* I could not confirm the current free-tier video limits or that Google AI Studio's free tier is offered in Egypt; paying needs a card that works abroad; it breaks your local-first rule. *Verdict:* worth one afternoon's test on 50 reels **if** AI Studio works from your account; keep the local pipeline for new saves.
- **whatstheID: pay AudD for long mixes instead of relying on shazamio.** *For:* shazamio is an unofficial Shazam client that can break any day; AudD is a paid, documented API whose enterprise endpoint takes hours-long files and bills per 12 s of audio processed, with a `skip`/`every` option for one request per 120 s. At $2–5 per 1,000 units that is roughly **$0.12–0.30 per two-hour mix** at one sample per 2 minutes. Your own notes measured AudD naming 3 of 6 underground records where Shazam named none. *Against:* paid, card from Egypt, and your library fingerprinter still beats both on records you own. *Verdict:* **it wins as the cloud fallback** behind your own fingerprinter. Swap it in for shazamio when you next touch `recognize.py`.
- **Inspiration Canvas: build it, on tldraw's agent starter kit.** *For:* tldraw ships an MIT agent starter kit (`npm create tldraw@latest -- --template agent`) where a model reads the canvas (screenshots plus shape data) and edits it through validated actions; that is "Claude reads my taste board" out of the box, and the SDK runs without a licence key on `localhost`. *Against:* it is a new app to maintain, and Obsidian Canvas + Eagle already cover collecting and reading. *Verdict:* still no, for now. If the vault-plus-Eagle setup proves too static after a month of use, this is the starting point.

## 6. Still uncertain (and what would settle it)

| Claim | Why uncertain | What settles it |
|---|---|---|
| Qwen-Image 2.1 is research-only | Many secondary sources; Hugging Face card unreadable from my tools | The licence block on the official model card |
| MiniMax H3 bars local use in the US/EU/UK/South Korea, not Egypt | Secondary reports; licence text on Hugging Face unread | Read `LICENSE` on the H3 model card |
| Laya's gain on your routes | Its README benchmarks are on other tasks | Your 200 hand-checked routes before and after fine-tuning |
| Your RAM is ≥ 32 GB | Unknown | Task Manager → Performance → Memory |
| Trial Reels available to your account | Eligibility reports conflict; nothing Egypt-specific | The "Trial" toggle when you share a reel |
| Instagram's API publishes reels with their own audio | One third-party claim says no | One API test post |
| Upwork Direct-to-Local-Bank in EGP | Official list truncated; 2020 forum evidence only | Upwork → Settings → Get Paid |
| What a Cairo collective will pay | No published prices | Money path 1's first test |
| Timeline-Bench agreement figures | Read via search snippets; arXiv blocked to my fetch tool | The paper's judge section |
| Serato 4 re-reads a rewritten grid on a track it already knows | rb2serato documents fresh imports only | Top 10 #10's first step, case (b) |
| Serato history `start_time` precision | Integer seconds in the schema; unit not documented | Compare one session's rows with your recording |
| QwenCleo-ASR's 19.9 % WER | Self-reported by a 19-star repo on its own test set | 10 minutes of your own Egyptian audio, scored by hand |
| Instagram's export lists each saved reel with its URL | Third-party guides only; contents vary by account and selected categories | Request the export with "Saved" ticked and open the saved-items file |
| Reel Brain sets `num_ctx` | Its code isn't on GitHub; Ollama's default is 4K on 12 GB | `grep num_ctx` in Reel Brain, or the prompt-token log from Day 2 |
| An Arabic aligner you can use commercially, and how it handles English words | Model card unread; Arabic vocabularies lack Latin letters | Licence on `jonatasgrosman/wav2vec2-large-xlsr-53-arabic`'s card; ten code-switched lines aligned and checked by eye |
| Your Egyptian captions beat Submagic / Opus Clip / ElevenLabs Scribe | No independent Egyptian-dialect test of any of them | One 2-minute code-switched clip through each, errors counted by hand |
| `--fit` picks a good expert offload on Windows | One anecdote that it works; Windows' desktop VRAM varies | The llama-server log line plus tok/s against a fixed `--n-cpu-moe 24` |

## 7. Sources

### Repo facts (checked 2026-10-14)
Stars from the GitHub page; last commit and licence from a shallow clone. "Win / 12 GB" is my read of fit.

| Repo | Stars | Last commit | Licence | Win / 12 GB | Used for |
|---|---|---|---|---|---|
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 253.5k | 2026-10-13 | MIT | yes | agent |
| [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) | 32.8k | 2026-10-12 | Apache-2.0 | yes (CPU) | router |
| [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) | 5.9k | 2026-10-12 | MIT | yes (WinGet) | GPU sharing |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 62.9k | 2026-10-13 | Apache-2.0 | yes (Node ≥22) | motion graphics |
| [Tejashmakwana/motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing) | 401 | 2026-10-06 | Apache-2.0 | yes | QA rubric |
| [CPJKU/beat_this](https://github.com/CPJKU/beat_this) | 421 | 2026-05-28 | MIT (weights too) | yes, < 1 GB | beats |
| [mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one) | 860 | 2023-10-10 | MIT | NATTEN from source | avoid |
| [CPJKU/madmom](https://github.com/CPJKU/madmom) | 1.7k | 2024-08-25 | BSD code, non-commercial models | old Python | avoid |
| [Tau-J/rtmlib](https://github.com/Tau-J/rtmlib) | 684 | 2026-08-03 | Apache-2.0 | yes (ONNX) | pose |
| [Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | 5.2k | 2026-10-12 | BSD-3 | yes, CPU | shot detection |
| [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | 20.0k | 2024-12-15 | Apache-2.0 | yes | click-to-track |
| [ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) | – | 2026-10-14 | AGPL-3.0 | yes | avoid near the fork |
| [modelscope/FunClip](https://github.com/modelscope/FunClip) | 6.4k | 2026-10-08 | MIT | yes | podcast clipping |
| [BoazCohenJ/Cutcast](https://github.com/BoazCohenJ/Cutcast) | 1 | 2026-10-12 | MIT | Windows | reference only |
| [vamshicreates/podcast-editor](https://github.com/vamshicreates/podcast-editor) | 0 | 2026-09-30 | MIT | yes | reference only |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 68.0k | 2026-10-12 | AGPL-3.0 | yes | ideas only |
| [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor) | 5.5k | 2026-10-12 | Unlicense | yes | silence cutting |
| [joshchoi4881/markus](https://github.com/joshchoi4881/markus) | 9 | 2026-06-26 | MIT | Node + ffmpeg | DJ-set clipper reference |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 25.8k | 2026-10-10 | MIT | yes, 3–5 GB | English ASR |
| [m-bain/whisperX](https://github.com/m-bain/whisperX) | 24.5k | 2026-09-26 | BSD-2 | yes | word timings |
| [MohammedAly22/qwencleo-asr](https://github.com/MohammedAly22/qwencleo-asr) | 19 | 2026-06-17 | Apache-2.0 | yes (no vLLM), ~4–6 GB | Egyptian ASR |
| [MahmoudAshraf97/ctc-forced-aligner](https://github.com/MahmoudAshraf97/ctc-forced-aligner) | 569 | 2026-09-07 | BSD-2 (default model CC BY-NC 4.0) | yes | Arabic word timings |
| [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) | 37.2k | 2026-10-12 | AGPL-3.0 | Docker | scheduling |
| [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) | 9.9k | 2026-08-15 | MiniMax H3 Community | 12 GB floor, 768p | personal only |
| [QwenLM/Qwen-Image](https://github.com/QwenLM/Qwen-Image) | 8.4k | 2026-02-10 | Apache-2.0 (code; 2.1 weights reportedly research-only) | GGUF Q4 | stills |
| [juspay/dopamine](https://github.com/juspay/dopamine) | 1 | 2026-10-14 | MIT | Node + Gemini | ideas only |
| [bitbonsai/mcpvault](https://github.com/bitbonsai/mcpvault) | 1.7k | 2026-10-09 | MIT | yes (Node) | vault MCP |
| [cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server) | 695 | 2026-10-05 | Apache-2.0 | yes | vault MCP alt. |
| [basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | 4.2k | 2026-10-12 | AGPL-3.0 | yes | memory alt. |
| [SM4RTENHEIMER/rb2serato](https://github.com/SM4RTENHEIMER/rb2serato) | 1 | 2026-09-27 | MIT | macOS-tested | Serato encoders |
| [serato-tools](https://pypi.org/project/serato-tools/) ([repo](https://github.com/bvandercar-vt/serato-tools)) | 31 | 2026-10-04 | MIT | yes (Py ≥3.12) | Serato tags |
| [Holzhaus/serato-tags](https://github.com/Holzhaus/serato-tags) | 93 | 2020-08-20 | MIT | – | format docs |
| [chrisle/serato-connect](https://github.com/chrisle/serato-connect) | 7 | 2026-09-27 | MIT | – | Serato reader |
| [whatsnowplaying/whats-now-playing](https://github.com/whatsnowplaying/whats-now-playing) | 100 | 2026-09-29 | MIT | yes | Serato history reader |
| [dylanljones/pyrekordbox](https://github.com/dylanljones/pyrekordbox) | 495 | 2026-10-08 | MIT | yes | Rekordbox |
| [ETH-DISCO/cue-detr](https://github.com/ETH-DISCO/cue-detr) | 32 | 2024-08-19 | MIT (code) | yes | cue points |
| [guillemcortes/peaknetfp](https://github.com/guillemcortes/peaknetfp) | 14 | 2025-12-05 | CC BY-NC-SA 4.0 | yes | personal only |
| [JorenSix/Panako](https://github.com/JorenSix/Panako) | 269 | 2026-09-17 | AGPL-3.0 | Java | ideas only |
| [mir-aidj/djmix-analysis](https://github.com/mir-aidj/djmix-analysis) | 62 | 2020-10-21 | none | – | ideas only |
| [jberg/butterchurn](https://github.com/jberg/butterchurn) | 2.0k | 2026-04-19 | MIT | WebGL | visualiser ref. |
| [obsidianmd/jsoncanvas](https://github.com/obsidianmd/jsoncanvas) | 3.7k | 2026-07-24 | MIT | – | board format |
| [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw) | 133.8k | 2026-10-12 | MIT | web | canvas alt. |
| [tldraw/tldraw](https://github.com/tldraw/tldraw) | 50.9k | 2026-10-13 | tldraw licence (key in production) | web | canvas alt. |

### Papers and studies
- Beat This!: [arXiv 2407.21658](https://arxiv.org/abs/2407.21658); Giant Steps run: [beat_this#13](https://github.com/CPJKU/beat_this/issues/13); weights licence: [beat_this#16](https://github.com/CPJKU/beat_this/issues/16)
- Raveform (EDM in DJ mixes): [TISMIR](https://transactions.ismir.net/articles/10.5334/tismir.288)
- Kim et al., mix-to-track alignment: [arXiv 2008.10267](https://arxiv.org/abs/2008.10267)
- Schwarz & Fourer, DJ-mix reverse engineering: [HAL](https://hal.archives-ouvertes.fr/hal-02172427); multi-pass NMF: [arXiv 2410.04198](https://arxiv.org/pdf/2410.04198)
- Grundmann et al., L1-optimal camera paths: [Google Research](https://research.google/pubs/pub37041/); AutoFlip: [Google blog](https://opensource.googleblog.com/2020/02/autoflip-open-source-framework-for.html), legacy status: [MediaPipe guide](https://ai.google.dev/mediapipe)
- Timeline-Bench (agents editing raw footage): [arXiv 2609.35143](https://arxiv.org/abs/2609.35143)
- LLM-judge position bias: [J1, arXiv 2505.10320](https://arxiv.org/pdf/2505.10320); [Judging the Judges](https://arxiv.org/html/2406.07791v7)
- Engagement prediction limits: [Frontiers 2026](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2026.1896199/full); [VQualA 2025](https://www.researchgate.net/publication/395244316_VQualA_2025_Challenge_on_Engagement_Prediction_for_Short_Videos_Methods_and_Results)
- Editor-preference learning (CLIP + SVM): [IEEE 11418344](https://ieeexplore.ieee.org/document/11418344/)
- SONAD, software-mention linking: [UPM](https://oa.upm.es/90236/)
- CUE-DETR / EDM-CUE: [arXiv 2407.06823](https://arxiv.org/abs/2407.06823); PeakNetFP: [arXiv 2506.21086](https://arxiv.org/abs/2506.21086)

### Issues and docs that carry the key claims
- Ollama: [#13084](https://github.com/ollama/ollama/issues/13084), [#15783](https://github.com/ollama/ollama/issues/15783), [#14493](https://github.com/ollama/ollama/issues/14493), [#10929](https://github.com/ollama/ollama/issues/10929); 0.30.0 engine change: [InsiderLLM](https://insiderllm.com/guides/ollama-0-30-0-whats-new/)
- Qwen3-VL loops: [QwenLM/Qwen3-VL#1611](https://github.com/QwenLM/Qwen3-VL/issues/1611); recommended sampling: [Unsloth guide](https://unsloth.ai/docs/models/tutorials/qwen3-how-to-run-and-fine-tune/qwen3-vl-how-to-run-and-fine-tune); image-token formula: [Alibaba Model Studio](https://help.aliyun.com/en/model-studio/vision-model/); GLM-4.6V-Flash: [listing](https://llmrun.dev/model/zai-org-glm-4-6v-flash)
- Hermes: [local models](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/local-models.md), [memory providers](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory-providers.md), [tool search](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/tool-search.md), [kanban](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md), [goals](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md), [cron](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md), [fallback providers](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/fallback-providers.md); issues [#110442](https://github.com/NousResearch/hermes-agent/issues/110442), [#129440](https://github.com/NousResearch/hermes-agent/issues/129440), [#29677](https://github.com/NousResearch/hermes-agent/issues/29677), [#66129](https://github.com/NousResearch/hermes-agent/issues/66129), [#107125](https://github.com/NousResearch/hermes-agent/issues/107125); v0.21 releases: [releases.sh](https://releases.sh/nousresearch/hermes-agent.md)
- Laya: [README](https://github.com/NandhaKishorM/laya), [#963](https://github.com/NandhaKishorM/laya/issues/963), [#919](https://github.com/NandhaKishorM/laya/issues/919)
- Qwen3.6 on 12 GB: [r/LocalLLaMA sweep (snapshot)](https://reddit.sentinel-team.org/posts/1t7l56a/snapshots/2026-05-15T23%3A40%3A01.25497Z), [InsiderLLM 3060 test](https://insiderllm.com/pdfs/qwen3-6-35b-a3b-gtx-1650-4gb-vs-rtx-3060.pdf); TAU2 comparison: [regolo.ai](https://regolo.ai/gemma-4-31b-vs-qwen3-6-35b-a3b-when-to-use-which/); Qwen3.6 licence: [noze.it](https://www.noze.it/en/insights/qwen-3-6/); Qwen3.5 family: [The Batch](https://www.deeplearning.ai/the-batch/alibabas-latest-flagship-models-are-open-weights-moe-performers-in-sizes-from-less-than-1b-parameters)
- Serato: history reader [whats-now-playing reader.py](https://github.com/whatsnowplaying/whats-now-playing/blob/main/nowplaying/serato/reader.py); MC4000 → Lite: [Serato](https://serato.com/dj/hardware/denon-dj-mc4000); Lite has no recorder: [djgear2k](https://djgear2k.com/serato-dj-lite-vs-serato-dj-pro/); Lite 4.0 History panel: [release notes](https://serato.com/dj/lite/downloads/4.0.0/releasenotes); Serato 4 library location: [MixGoat](https://mixgoat.com/guides/export-serato-crates-and-library)
- FilmCraft: gap list `docs/gaps.md` in this repo; Arabic [#395](https://github.com/storytold/filmcraft/issues/395), [#1475](https://github.com/storytold/filmcraft/issues/1475), [PR #1478](https://github.com/storytold/filmcraft/pull/1478); caption fonts [PR #708](https://github.com/storytold/filmcraft/pull/708); burn-in test: `prototypes/filmcraft_arabic_captions.jsonl`
- Licences: Qwen-Image 2.1 [latenode](https://latenode.com/ai-trends/qwen-image-2-1-commercial-licence), [techaiwire](https://techaiwire.com/articles/qwen-research-license-explained/); FLUX.2 klein [VentureBeat](https://venturebeat.com/technology/black-forest-labs-launches-open-source-flux-2-klein-to-generate-ai-images-in); Z-Image-Turbo [ComfyUI wiki](https://comfyui-wiki.com/en/models/z-image/z-image-turbo); MiniMax H3 [mer.vin](https://mer.vin/news/minimax-h3-open-weight-video-model-blocked-us-eu-uk/), [12 GB guide](https://runaihome.com/blog/minimax-h3-comfyui-gguf-workflow-tutorial-2026/); Cohere Transcribe Arabic [Cohere](https://cohere.com/blog/transcribe-arabic); tldraw [licence key](https://tldraw.dev/sdk-features/license-key)
- Publishing: [Instagram content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing); [TikTok content sharing guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines); [YouTube unverified-app uploads](https://www.ayrshare.com/solutions/google-api-error-403-unverified-app-how-to-fix-the-audit-pipeline/); [Trial Reels](https://www.lindseygamble.com/blog/instagram-launches-trial-reels-giving-creators-the-ability-to-share-reels-with-non-followers-before-sharing-with-everyone)
- GPU and audio: ComfyUI free endpoint [RunComfy docs](https://docs.runcomfy.com/serverless/instance-proxy-endpoints); DPC latency [Blue Cat Audio](https://www.bluecataudio.com/Blog/?p=4390); 3080 Ti transients [Level1Techs](https://forum.level1techs.com/t/think-i-have-a-dud-3080ti-you-tell-me/190443); GDDR6X pads [Igor's Lab](https://www.igorslab.de/en/simple-pad-mod-for-the-force-rtx-3080-founders-edition-slowers-the-gddr6x-temperature-by-a-whopping-8-degrees/); clock locking [Zivid](https://support.zivid.com/support/unstable-capture-time-windows.html)
- Resolve 21.1: [MCP and presets (Digital Production)](https://digitalproduction.com/2026/09/08/resolve-21-1-adds-mcp-and-finally-gets-presets/), [scripting moved to Studio (Puget Systems)](https://www.pugetsystems.com/blog/2026/09/10/how-davinci-resolve-free-v21-1-scripting-changes-affect-puget-bench/), [community resolve-mcp](https://glama.ai/mcp/servers/irstone-source/resolve-mcp); tldraw [agent starter kit](https://tldraw.dev/starter-kits/agent); AudD [enterprise endpoint docs](https://docs.audd.io/enterprise.md)
- DJ tools: [Lexicon 1.10](https://www.digitaldjtips.com/lexicon-1-10-brings-serato-4-0-support-track-timeline-play-history/); [TrackSniff](https://www.digitaldjtips.com/tracksniff-shazam-alternative/); [AudD](https://audd.io/); [rbxport](https://rbxport.com/); slskd licence [AUR](https://aur.archlinux.org/pkgbase/slskd-bin)
- Canvas: [JSON Canvas spec](https://github.com/obsidianmd/jsoncanvas/blob/main/spec/1.0.md); [Eagle store](https://eagle.cool/store); [Pinterest access tiers](https://developers.pinterest.com/docs/key-concepts/access-tiers/); [Instagram export guide](https://takeoutday.org/guides/how-to-export-instagram-data); type foundries [Velvetyne FAQ](https://velvetyne.alwaysdata.net/about/faq/), [Collletttivo](https://collletttivo.it/journal/open-source-hyper-capitalism)

### Money
- [YouTube Partner Program countries](https://support.google.com/youtube/answer/13429240); Facebook creator programme in Egypt: [Nation](https://nation.africa/kenya/business/technology/ruto-facebook-instagram-to-start-paying-kenyan-content-creators-4461870)
- Payouts: [Payoneer vs Wise in Egypt](https://xpay.app/blog/wise-or-payoneer-egypt), [Payoneer alternatives](https://www.cenoa.com/blog/payoneer-alternatives-egypt-2026-guide-freelancers), [PayPal in Egypt](https://xpay.app/blog/paypal-egypt-alternatives), [Upwork local bank](https://support.upwork.com/hc/en-us/articles/211063888), [Upwork fees](https://golance.com/blogs/upwork-fees-explained-2026), [Fiverr in Egypt](https://www.raenest.com/blog/how-to-receive-fiverr-payments-in-egypt), [InstaPay limits](https://enterpriseam.com/egypt/?p=609939), [Gumroad PayPal exclusions](https://www.mintlify.com/antiwork/gumroad/payments/paypal), [Lemon Squeezy countries](https://docs.lemonsqueezy.com/help/getting-started/supported-countries), [Egyptian card limits](https://techpoint.africa/2024/01/17/egyptian-banks-impose-card-limits/)
- Prices and demand: [Upwork Arabic clip job ($50)](https://www.upwork.com/jobs/~022063317379875817148), [Arabic doc editor ($10–25/h)](https://www.upwork.com/freelance-jobs/apply/Arabic-and-English-storytelling-video-editor-Mini-documentary-seroes_~022069460820553864681/), [Saudi EdTech retainer](https://www.upwork.com/freelance-jobs/apply/Arabic-Video-Editor-Motion-Graphics-Designer-Long-Term-Weekly-Work-Saudi-EdTech_~022082945813408227255/), [Fiverr podcast shorts](https://block.fiverr.com/gigs/podcast-shorts), [Khamsat reels editing](https://khamsat.com/services/%D9%85%D9%88%D9%86%D8%AA%D8%A7%D8%AC-%D8%B1%D9%8A%D9%84%D8%B2), [podcast clipping prices](https://openclip.app/clipping/podcast-clipping), [OpenClaw setup gig](https://fiverr.com/customer1995/help-you-set-up-openclaw), [Upwork Cairo videographers](https://www.upwork.com/hire/videographers/eg/cairo/)
- DJ clip demand: [Fiverr DJ live-set editing ($50–100)](https://fiverr.com/richieseye/edit-your-dj-live-set), [short-form editing rates 2026](https://adsnipper.com/?p=2494), [SendShort DJ mix tool](https://sendshort.ai/tools/dj-mix/), [SendShort pricing (FluxNote)](https://fluxnote.io/guides/sendshort-pricing-breakdown-2026), [markus dj-clipper skill](https://github.com/joshchoi4881/markus/tree/main/frameworks/claude-code/dropspace-dj-clipper)
- Hidden costs: [WE home tiers (aggregator)](https://subger.com/en/ie/service/we-home-internet), [electricity, August 2026 increase (Ahram)](https://english.ahram.org.eg/News/573852.aspx), [2026 bracket rates (Reslink)](https://www.reslink.org/blogs/electricity-tariffs-just-rose-again-solar-payback-is-now-under-5-years/), [Upwork Connects 2026](https://aiproposer.com/learn/upwork/upwork-connect-price-2026)
- Cairo scene: [SceneNoise on Geeza](https://scenenoise.com/Features/How-Geeza-is-NOT-So-Quietly-Reimagining-Cairo-s-Underground-Clubbing), [MOSHTRQ](https://scenenoise.com/News/Underground-Collective-MOSHTRQ-hosts-massive-takeover-event-on-May-14), [INTG](https://scenenoise.com/News/Cairo-s-INTG-Party-Series-to-Launch-with-All-Live-DJ-Showcase-Aug-25)
