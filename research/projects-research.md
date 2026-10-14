# Projects research: what to build, adopt or drop

**Status:** round 1 draft (breadth pass). Every later round rewrites this file; `audit-log.md` keeps the history.
**Written for:** a solo dev and techno DJ in Cairo with one Windows 10 PC (RTX 3080 Ti, 12 GB VRAM, 300 W cap), local-first.
**Date of research:** 2026-10-14. Repo stats (stars, last commit, licence) were checked on that date.

> One unknown changes several answers: **how much system RAM you have.** Mixture-of-experts models with
> expert offload (the fastest way to run a 30B-class model on 12 GB) need roughly 32 GB of RAM, ideally 64 GB.
> Wherever that matters, both options are given.

---

## 1. Top 10 moves (ranked by impact ÷ effort)

| # | Move | Project | Effort | Confidence |
|---|---|---|---|---|
| 1 | Take client-facing image generation off Qwen-Image 2.1 (research-only licence) | Creative Studio | 2–3 h | medium |
| 2 | Serve vision/structured-output models with llama.cpp, not Ollama, and bound the JSON | Reel Brain, Creative Studio | 0.5–1 day | medium |
| 3 | Move Hermes to llama.cpp with MoE expert offload and turn on Tool Search | Hermes | 0.5–1 day | medium |
| 4 | Measure 40 reference clips and turn "Boiler Room style" into numbers | Creative Studio | 1 day | high |
| 5 | One GPU broker with a DJ-mode guard, plus a clock cap and thermal check | all | 1–2 days | medium |
| 6 | Get your sets' beat grids from your own track files and Serato's history | Creative Studio, whatstheID | 2–4 days | medium |
| 7 | Reframe from body pose + an L1-optimal camera path, not faces alone | Creative Studio | 2–3 days | medium |
| 8 | Replace the virality score with Trial Reels and your own results log | Creative Studio | 2 h | medium |
| 9 | Write Serato grids and cues with rb2serato's MIT encoders | whatstheID | 2–3 days | medium |
| 10 | Reel Brain: linear probe + top-3 + "no repo" verification instead of free LLM picks | Reel Brain | 1–2 days | medium |

### 1. Take client-facing image generation off Qwen-Image 2.1
- **Why:** several independent write-ups (dated after 2026-09-20) say Qwen-Image 2.1 ships under a *Qwen Research License*: research and evaluation only, commercial use by separate agreement. The original Qwen-Image was Apache-2.0; 2.1 is not. Anything you sell (the collective's clips) cannot use it.
- **Instead:** FLUX.2 [klein] **4B** (Apache-2.0; the 9B is non-commercial) or Z-Image-Turbo (Apache-2.0, 6B, 8 steps). Both fit 12 GB quantized. Keep Qwen-Image 2.1 for personal experiments only.
- **Confidence: medium.** Many secondary sources agree; I could not open the official model card (Hugging Face was unreachable from my tools). Settle it by reading `LICENSE` in the official repo.
- **Could fail if:** Qwen re-licenses (it happened in the other direction before) or your outputs are judged "not commercial". Unlikely to matter: switching costs hours.
- **First step:** open the official Qwen-Image-2.1 model card, read the licence block, then build one ComfyUI workflow on FLUX.2 klein 4B and compare 10 prompts from your direction folder.

### 2. Serve vision and structured output with llama.cpp, not Ollama
- **Why:** Ollama issue [#14493](https://github.com/ollama/ollama/issues/14493) (open, comments into Sep 2026) reports that Ollama's Go runner, which newer models such as Qwen 3.5 run on, **silently ignores `repeat_penalty`, `presence_penalty` and `frequency_penalty`**, and that the `qwen3-vl` renderer is affected by a missing-generation-prompt bug. Separate issues show Qwen3-VL repetition loops in Ollama and LM Studio ([QwenLM/Qwen3-VL#1611](https://github.com/QwenLM/Qwen3-VL/issues/1611)), garbage when image tokens exceed `num_ctx` ([ollama#13084](https://github.com/ollama/ollama/issues/13084)), and broken JSON with thinking + `format` ([ollama#10929](https://github.com/ollama/ollama/issues/10929)). That is a close match to "broken or looping JSON".
- **Do:** run the VLM with `llama-server --jinja -m <model>.gguf --mmproj <mmproj>.gguf`, pass a JSON schema (`response_format`/`json_schema`), keep penalties on, and design the schema so it cannot loop: `maxItems` on every array, `maxLength` on strings, enums where possible, thinking off, `n_predict` capped. Validate with Pydantic; on failure retry once at a different temperature, then fall back to "free text → second small call that only formats JSON".
- **Confidence: medium.** The Ollama bug is documented; that it causes *your* loops is inferred. Grammar-constrained decoding can loop in llama.cpp too, which is why the schema bounds matter.
- **Could fail if:** the loops come from the frames (too many image tokens) rather than sampling. Test that first: halve the frame count and see if loops drop.
- **First step:** take the 20 reels that failed most recently, run them through llama-server with the bounded schema, and log the valid-JSON rate against Ollama.

### 3. Move Hermes to llama.cpp with expert offload; turn on Tool Search
- **Why:** Hermes now ships a managed llama.cpp runtime that places MoE expert weights in system RAM first and keeps attention and KV cache on the GPU, with a guaranteed ≥64K context and 15-minute idle unload ([local-models docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/local-models.md)). On a 12 GB RTX 3060, Qwen3.6-35B-A3B with `--n-cpu-moe 24` measured ~36 tok/s at 16K context ([DEV guide](https://dev.to/donald_lee_707b59c456e304/how-to-pick-n-cpu-moe-in-llamacpp-qwen36-35b-a3b-on-12-16-and-24-gb-gpus-43f3)); your 3080 Ti has ~2.5× the memory bandwidth. Hermes also has **Tool Search** (MCP tools hidden behind `tool_search`/`tool_describe`/`tool_call`) and `hermes prompt-size`; its own docs say prefill of the system prompt plus tool schemas dominates first-token time on local models.
- **Model:** Qwen3.6-35B-A3B (Apache-2.0, April 2026) if you have ≥32 GB RAM; otherwise Qwen3.5-9B (Apache-2.0, dense, hybrid attention so long context is cheap) fully on GPU.
- **Confidence: medium.** Docs read directly; speed numbers are from a slower card; tool-calling reliability for Qwen 3.5/3.6 is reported as stack-dependent.
- **Could fail if:** RAM is 16 GB, or the Qwen3.6 tool-call template misbehaves. Keep your current Qwen3-Coder-30B config as a fallback profile.
- **First step:** `hermes prompt-size` today to see how many tokens your MCP tools cost per turn; then `hermes model` → Local models and compare against Ollama on 20 of your own logged requests.

### 4. Measure 40 reference clips
- **Why:** I found **no published description** of how Boiler Room, BCCO or HÖR cut their shorts. Guessing produces the "stock" look. Your own whatstheID notes show the method that works for you: measure, then build.
- **Do:** collect ~40 clips (analysis only, never re-published). Run shot detection (PySceneDetect, BSD-3, or FilmCraft's `clip.sceneEditDetection`) and beat tracking (Beat This) on each. Output: cuts per clip, shot length in beats, % of cuts on a downbeat/bar/phrase line, where the drop sits, how long the first shot holds, when text appears and what it says.
- **Hypothesis to test:** many of these clips are one or two fixed-camera shots where the edit is mostly *selection* (start a few bars before the drop, end on the reaction) plus a track-ID caption, not rapid cutting. If true, alternating crowd/DJ cuts is the wrong default.
- **Confidence: high** that it pays off; the numbers it finds are unknown by definition.
- **First step:** a 50-line script over a folder of clips → CSV; look at the medians.

### 5. One GPU broker with a DJ-mode guard
- **Why:** every project competes for one 12 GB GPU and the PC has crashed on long runs. A single broker turns that into scheduling, not luck.
- **Do:** a tiny local service (SQLite lease table, FastAPI or plain socket): each job asks for a lease with priority and an estimated VRAM; the broker unloads idle LLMs (Ollama `keep_alive: 0`, or llama-swap TTLs) before granting a large job; it **refuses all GPU jobs while `Serato DJ Pro.exe` / `Serato DJ Lite.exe` / `Ableton Live*.exe` is running** (psutil); every job checkpoints so a refused or killed job resumes.
- **Hardware side:** on RTX 30-series, crashes under load are often millisecond transients that a power cap does not stop. Cheap things to try: cap the core clock (`nvidia-smi -lgc 210,1700` as admin, or an Afterburner curve), and watch **GDDR6X memory junction temperature** in HWiNFO during a long LLM or Whisper run (memory-bound work behaves like mining; 3080-class cards reach 104–110 °C there). If junction temps are high, thermal pads; if crashes persist at a capped clock, suspect the PSU.
- **Confidence: medium.** The broker is standard engineering; the crash diagnosis is from forum reports, not your logs.
- **First step:** log `nvidia-smi --query-gpu=power.draw,clocks.gr,temperature.gpu,memory.used --format=csv -l 1` plus HWiNFO memory junction during the next long Reel Brain batch.

### 6. Beat grids for your own sets from your own track files
- **Why:** blind beat tracking on a 150 BPM mix fights overlapping kicks in transitions, pitch riding and breakdowns. You have better information. **Serato DJ 4 logs every load** in `master.sqlite` → `history_entry` (artist, title, BPM, key, deck, `start_time`, `played`; verified in the [whats-now-playing reader](https://github.com/whatsnowplaying/whats-now-playing/blob/main/nowplaying/serato/reader.py)). Your library files carry Serato's beat grid (`Serato BeatGrid` GEOB). Align each played track to the set recording (your cross-correlation code plus whatstheID's speed ladder), then transform that track's grid into set time. This is the published "DJ-mix reverse engineering" approach (Schwarz & Fourer; Kim et al., ISMIR 2020).
- **Fallback:** Beat This ([CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT, ~78 MB model, pip install, no madmom needed) for tracks you don't own, with a 120–160 BPM prior to stop half/double errors.
- **Confidence: medium.** The history fields are verified from code; alignment through heavy EQ/filter/FX is not tested on your sets.
- **Could fail if:** the DJ rides the pitch so the stretch ratio drifts inside a track (fit it piecewise) or the track was played from a streaming service (no file).
- **First step:** open your `master.sqlite` (read-only copy) and list the last session's `history_entry` rows next to your set recording's start time.

### 7. Reframe from body pose + an L1-optimal camera path
- **Why:** YuNet finds faces; a DJ looks down at the controller under strobes, so faces drop out exactly when it matters. A real operator frames the body and hands, holds still, then pans deliberately.
- **Do:** detect people and keypoints with RTMPose via [rtmlib](https://github.com/Tau-J/rtmlib) (Apache-2.0, ONNX, light) and keep YuNet as one signal. Choose the subject per shot, then solve the crop path offline as an L1-optimal path (Grundmann et al., "Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths", the method behind YouTube's stabiliser): the L1 objective produces static holds, constant pans and smooth ease-ins, like a camera operator. Google's AutoFlip uses a polynomial (L2) fit, which drifts more.
- **Avoid:** Ultralytics YOLO (AGPL-3.0) anywhere near the FilmCraft fork.
- **Confidence: medium.** Both pieces are established; the combination on club footage is untested.
- **First step:** run rtmlib on one 60-second DJ clip and plot face-detection vs body-detection coverage per frame.

### 8. Replace the virality score with real tests
- **Why:** predicting engagement from content alone explains roughly 20–30 % of variance in a 2026 study (R² 0.21–0.29); the best VQualA 2025 challenge entry reached SROCC 0.71 on its own dataset. A local score ranking three of your variants is mostly noise.
- **Do:** keep a cheap pre-filter (hook in first 2 s, drop present, no black frames), then publish variants as **Instagram Trial Reels** (shown to non-followers only) and log views, 3-second holds and shares per variant. After ~30 posts, fit your own ranking on your own data.
- **Confidence: medium.** The research is solid; Trial Reels availability for your account in Egypt is unverified (eligibility has been limited to professional accounts).
- **First step:** check whether the "Trial" toggle appears when you share a reel from a professional account.

### 9. Write Serato grids and cues with rb2serato's encoders
- **Why:** [rb2serato](https://github.com/SM4RTENHEIMER/rb2serato) (MIT, Sep 2026) writes `Serato Markers2`, `Serato Markers_` and **locked** `Serato BeatGrid` tags whose bytes match what Serato writes, verified on a 9,600-track library, with undo logs and audio-byte checks. It also documents Serato 4's import quirks (crate header must be exactly `1.0/Serato ScratchLive Crate`, WAV typed `wave`, Serato closed while writing). That is the risky half of whatstheID's 4c plan, already done.
- **Confidence: medium.** Tested on macOS only; its shell wrapper and APFS-clone safety step need Windows equivalents.
- **First step:** vendor its encoder module into whatstheID, write a grid to a *copy* of one track, load it in Serato, confirm.

### 10. Reel Brain: stronger classification and repo linking
- **Why:** kNN at 63 % is a weak baseline. A logistic-regression "linear probe" on the same embeddings usually beats kNN once you have ~1,000 labels; showing the top 3 turns a 63 % top-1 into a much higher hit rate for one click. For repos, a published study (SONAD) found LLMs over-accept candidates (precision 68 %, recall 97 %) while a feature-based verifier reached 82 % precision.
- **Do:** (a) re-label 50 random reels blind to find your own consistency ceiling; (b) linear probe + top-3 + LLM rerank only when the top-2 margin is small; (c) for repos: candidates from GitHub/Hugging Face search, then score exact name match, owner, README similarity to the reel's context and stars, and allow "no repo". Your whatstheID `verify.py` already encodes the right rules (empty is a refusal, exact-match preference, word-level coverage × precision).
- **Borrow:** [juspay/dopamine](https://github.com/juspay/dopamine) (MIT, active) is the same pipeline on Gemini; its project mapper (embedding prefilter + judge with an "avoid" field per project) is what your per-project ranking needs.
- **Confidence: medium.**
- **First step:** the 50-item blind re-label.

---

## 2. Per project

### 2.1 Creative Studio (top priority)

**Adopt**
- **Beat This** ([CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT, last commit 2026-05-28): beat + downbeat without madmom's DBN; CLI and Python; runs on Windows (pure PyTorch). Training code is public, so you can fine-tune on your own library's grids later.
- **Your own sets:** Serato history + track alignment (Top 10 #6).
- **Shot detection:** PySceneDetect (BSD-3, active) or FilmCraft's own scene edit detection. TransNetV2 (MIT) is unmaintained since 2021.
- **Pose/person:** rtmlib (Apache-2.0). SAM 2 (Apache-2.0, last commit Dec 2024) for click-to-track a subject when needed.
- **Motion graphics renderer:** [HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen, Apache-2.0, active): HTML/CSS → deterministic video, transparent WebM, made for agents. Worth comparing with your own HTML→alpha step for seek determinism. Remotion has its own licence (paid above small companies); Motion Canvas and Revideo are MIT but slower-moving.
- **Taste checklist:** [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing) (Apache-2.0) lists the tells of AI motion graphics ("everything is a slide", typed-out headlines with a caret, a new flat colour per scene) and its counter-rules (one idea, light and texture, measured motion, cut on motion). Use it as a QA rubric for your existing motion-graphics QA step.
- **Type that doesn't look default:** libre foundries Velvetyne (OFL/GPL per font), Collletttivo (free for commercial use), Use & Modify (curated list; check each licence). Pick one display face and one text face per client and never change them mid-series.
- **Multicam in FilmCraft:** upstream already has `clip.createMulticam` and `multicam.cutToCamera`; drive those from the plan instead of building cuts by hand.

**Shot picking from two synced angles (proposal)**
1. Per shot window (aligned to bars): sharpness (Laplacian variance), exposure, motion energy, face/pose visibility, hands-up count (wrists above head from pose), strobe flashes.
2. Hard rules from the measured benchmark (#4): minimum shot length in bars, change angle only on bar or phrase lines, crowd angle at the drop plus ~1 bar (crowd reaction lags the drop).
3. Learn your taste: label ~200 shots keep/skip, train a logistic head on frozen SigLIP embeddings (Apache-2.0). An IEEE paper on autonomous multi-camera editing learned an editor's preferences from 33 scenes with CLIP + SVM (79.7 % of scenes judged "usable"; publication date not confirmed).
4. The LLM only chooses among pre-scored candidates and writes the plan as JSON; it does not watch video.

**Planner and judge in 12 GB**
- Planner: Qwen3.5-9B (Apache-2.0, natively multimodal) or your Hermes model; constrained JSON via llama.cpp.
- Judge: compare variants **pairwise** on contact sheets (A vs B, then swap order to cancel position bias) rather than scoring each alone.

**Drop or avoid**
- Qwen-Image 2.1 for anything paid (licence).
- A virality model as the ranking signal (Top 10 #8).
- Ultralytics YOLO in anything that touches the MIT/Apache fork (AGPL).
- **MiniMax H3 for client work, for now:** its community licence reportedly bars local deployment in the US, EU, UK and South Korea (Egypt not listed), local weights top out around 768p, and on 12 GB community guides put the floor at ~0.4 MP with heavy offload and 32–64 GB RAM. Generated video also undercuts what a club clip sells: that it was real. Use it for abstract background plates at most.
- All-In-One music structure analyser for production use: MIT but last commit 2023-10-10 and needs NATTEN built from source on Windows.

**Models (12 GB)**
| Job | Model | Licence | VRAM (approx.) |
|---|---|---|---|
| Beats/downbeats | Beat This `final0` | MIT | < 1 GB |
| Planner / judge | Qwen3.5-9B Q5 + mmproj | Apache-2.0 | ~7–8 GB |
| Pose | RTMPose (rtmlib, ONNX) | Apache-2.0 | < 1 GB |
| Taste head | SigLIP base + logistic | Apache-2.0 | < 1 GB |
| Stills (commercial) | FLUX.2 klein 4B / Z-Image-Turbo | Apache-2.0 | ~8–13 GB / ~6–10 GB quantized |
| Video gen (personal) | MiniMax H3 Q4 GGUF | MiniMax community licence | ~11.6 GB file + offload |

**Open risks**
- FilmCraft upstream's own gap list: Windows runtime is under-tested (G9), no PR CI (G4), and **10-bit / 4:2:2 H.264/HEVC does not decode on Windows without hardware support** (G3). If your camera records 10-bit 4:2:2, transcode to 8-bit 4:2:0 before ingest or the import fails.
- Copyright: club clips carry other artists' tracks. Instagram mutes or limits; plan captions and track IDs, and keep originals.

### 2.2 Hermes + Laya

**Adopt**
- Hermes' managed llama.cpp runtime or your own `llama-server` (`providers.llamacpp.base_url`), Top 10 #3.
- **Tool Search** for MCP tools; `hermes prompt-size` and `hermes tools` to cut the fixed prompt.
- **Kanban** (built in, SQLite `~/.hermes/kanban.db`, per-task model override, durable handoffs, retries, circuit breaker) for multi-agent work instead of a new orchestrator. Hermes' own docs position it as the reliable alternative to in-process subagent swarms.
- **Memory:** keep Hermes' built-in `MEMORY.md`/`USER.md` small and make the Obsidian vault the knowledge store, reached through one MCP server (see Shared pieces). Of the memory plugins, only Holographic (local SQLite + FTS5) and ByteRover (local) are local-only; RetainDB and ByteRover leave Hermes core on 2026-10-15.

**Laya (router)**
- Train from your logs: embed each message with EmbeddingGemma-300M (already in your stack; multilingual, <200 MB quantized), fit logistic regression on the labelled decisions, route by confidence, send low-confidence cases to the LLM and to a "label me" queue (Telegram buttons). Retrain weekly. Fine-tune ModernBERT or SetFit only if the linear model plateaus.
- Measure first: accuracy of the current router on 200 hand-checked decisions, and how often a wrong route actually cost you.

**Drop or avoid**
- A second orchestrator framework (CrewAI, LangGraph) on top of Hermes: Kanban plus delegation covers it.
- Gemma 4 31B (Hermes' docs call it the most reliable local tool-caller) on 12 GB: ~20 GB, will not fit.

**Models**
| Use | Model | VRAM / RAM |
|---|---|---|
| Daily driver (≥32 GB RAM) | Qwen3.6-35B-A3B Q4 + `--n-cpu-moe ~24` | ~11 GB VRAM + ~12 GB RAM |
| Daily driver (16 GB RAM) | Qwen3.5-9B Q5/Q6 | ~7–9 GB VRAM |
| Router embeddings | EmbeddingGemma-300M | CPU |

**Open risks:** Qwen 3.5/3.6 tool-call templates are fragile across servers (Ollama issue above; use `--jinja` and the `qwen3_coder` parser where offered). Hermes' 48k open issues/PRs means fast churn: pin a version.

### 2.3 Reel Brain

**Adopt**
- llama.cpp for the VLM with bounded schemas (Top 10 #2).
- **Try Qwen3.5-9B against Qwen3-VL-8B** on 30 reels: Qwen says 3.5's early-fusion training beats Qwen3-VL on visual understanding (vendor claim). MiniCPM-V 4.5 (8.7B, reports 73.5 on Video-MME, llama.cpp support since b6282) is the video-specialised alternative.
- Linear probe + top-3 classification; repo verification with a "no repo" outcome (Top 10 #10).
- Port ideas from juspay/dopamine: link resolver that remembers failed lookups, verifier, project mapper with "avoid".
- Run batches through the GPU broker with per-item checkpoints (SQLite job table) so a crash costs one reel, not the run.

**Drop or avoid**
- instagrapi for collecting saves (Dopamine uses it; it logs into your account through a private API and risks a ban). Use Instagram's own "Download your information" export (JSON) for the list of saved items, then fetch only what you need.

**Models**
| Use | Model | VRAM |
|---|---|---|
| Transcript | faster-whisper large-v3 (MIT) int8 | ~3–5 GB |
| Frames → notes | Qwen3-VL-8B or Qwen3.5-9B Q5 + mmproj | ~7–8 GB |
| Collections | EmbeddingGemma-300M + logistic head | CPU |

### 2.4 whatstheID

What you already have (from the repo): shazamio + AudD, your own landmark fingerprinter with a query-side speed ladder, comb-filter tempo (0.01 BPM MAE vs Serato on 17 tracks), a key ensemble, a read-only Serato parser, a hand-written WebGL2 engine. Not on `main`: Serato write-back, Soulseek.

**Adopt**
- rb2serato encoders for grids and cues (Top 10 #9). [serato-tools](https://pypi.org/project/serato-tools/) (Python ≥3.12) is an alternative; **pyserato is AGPL-3.0**, avoid if you ever distribute.
- **Rekordbox:** [pyrekordbox](https://github.com/dylanljones/pyrekordbox) (MIT, active) and Rekordbox XML, whose `TEMPO` entries carry variable grids (tempo changes).
- **Grid quality:** fit the grid to the **kick attack**, not the energy peak (onset of the low band's envelope rise), per beat, then least-squares the tempo. rb2serato measured Serato's grid a median 8 ms ahead of Rekordbox's on 1,563 MP3s: check your offset against Serato on your own files.
- **Downbeats/phrases:** score each of the 4 bar phases (and 8/16-bar phrase phases) by how well novelty peaks (energy, new elements, breakdown edges) land on them. Half-time D&B: prefer 170–176 over 85–88 by genre prior.
- **IDs in long mixes:** segment first (novelty), then query the middle of each segment where one track plays alone, instead of a fixed 60 s grid; keep the speed ladder.
- **Reference rbxport** ([rbxport.com](https://rbxport.com/)): a free Rekordbox library manager (not open source) by Chris Le, who also wrote [serato-connect](https://github.com/chrisle/serato-connect) (MIT). Its grid analysis is "tuned for electronic music"; I could not read details (site unreachable).
- **Visualiser:** drive shaders from beat/bar/phrase *phase* from your analysis, not raw FFT amplitude: visuals lock to the music's structure. Butterchurn (MIT, Milkdrop in WebGL) is a reference; Hydra is AGPL.

**Avoid:** Panako and Olaf (both AGPL-3.0) as code; read their papers for the tempo-invariant ideas.

### 2.5 Inspiration Canvas (idea stage)

**Recommendation: do not build a canvas app yet. Build the board format first, inside your Obsidian vault.**
- Store boards as **JSON Canvas** (`.canvas`, open spec, MIT, what Obsidian Canvas uses): nodes for images/videos/notes/links, edges for relations. Any LLM can read and write it; Obsidian renders it for free.
- A "look pack" = a folder with the images, a `look.md` (palette, type, motion rules, what to avoid) and a `.canvas` board. Creative Studio reads `look.md`.
- Imports: Instagram via the official data export (same as Reel Brain); Pinterest via its data export or API v5 Trial access (reading your own boards and pins is allowed on Trial; approval is reported as slow).
- If you later want a real app: tldraw needs a licence key in production but runs free in development mode on `localhost`; Excalidraw is MIT. A FilmCraft extension would mean egui work in a Rust app whose Windows runtime is already the weak spot: no.

---

## 3. Cross-project shared pieces

1. **GPU broker with DJ-mode guard** (Top 10 #5): every project.
2. **One local model server** (llama.cpp / llama-swap, MIT) instead of Ollama + Hermes runtime + ComfyUI each loading their own copy: one place to unload, one place to measure.
3. **One vault access layer:** a single MCP server over the Obsidian vault (read/write notes, search by text and embeddings) used by Hermes, Claude Code, Reel Brain and the canvas. You already write to the vault via `learn-to-vault` / claude-obsidian (Karpathy LLM-wiki pattern); don't add a second memory database that drifts from it.
4. **One verification module** for "does this search hit really match": whatstheID's `verify.py` rules reused for Reel Brain's tool→repo links.
5. **Shared audio analysis:** whatstheID's comb-filter tempo and key code, Beat This, and Serato readers serve both whatstheID and Creative Studio.
6. **Shared embeddings:** EmbeddingGemma for Laya, Reel Brain and canvas search.

---

## 4. Money (round 1, unverified for Egypt in detail)

1. **Event clip packs for Cairo collectives** (Geeza, MOSHTRQ, INTG, BackSpin, Analog Room are active per SceneNoise). Paid locally in EGP (InstaPay/bank). First test: offer one collective a free 3-clip pack from their next night in exchange for a testimonial and access; price the second.
2. **Arabic/English podcast and founder clips** on Upwork: a May 2026 Upwork post paid **$50 fixed** for one 30–45 s Arabic clip with animated captions and drew 10–15 proposals. AI tools make generic clipping cost ~$1/episode, so compete on Arabic captions and taste, not volume. Payout from Egypt: Payoneer is the usual route; PayPal withdrawals in Egypt are EGP-only with a markup; Wise is limited for Egyptian residents.
3. **DJ-tool setup and grids** (later): whatstheID polished as a tool other DJs use; sell support or a paid build. Payment platforms for software from Egypt unverified (Lemon Squeezy pays out via PayPal/bank in many countries; Egypt not confirmed).
4. **Hermes/agent setup gigs:** Fiverr already has sellers offering "Hermes Agent + Obsidian memory + Ollama" setups. Your daily-driver config is a product.

---

## 5. What I got wrong along the way
(Filled in by the audit rounds.)

## 6. Still uncertain
- System RAM (decides the Hermes model).
- Qwen-Image 2.1's licence text on the official card.
- Whether Trial Reels are available to your account.
- MiniMax H3 licence text for Egypt.
- Whether Serato's history `start_time` is precise enough to seed alignment.

## 7. Sources
(Consolidated in the final round; links are inline above.)
