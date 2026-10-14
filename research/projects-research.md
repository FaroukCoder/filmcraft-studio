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
| 2 | Measure Laya's routing accuracy, then fine-tune and calibrate it on labelled logs | Hermes + Laya | 2 h, then 1–2 days | high |
| 3 | Serve vision/structured-output models with llama.cpp, not Ollama, and bound the JSON | Reel Brain, Creative Studio | 0.5–1 day | medium |
| 4 | Move Hermes to llama.cpp with MoE expert offload and turn on Tool Search | Hermes | 0.5–1 day | medium |
| 5 | Measure 40 reference clips and turn "Boiler Room style" into numbers | Creative Studio | 1 day | high |
| 6 | One GPU broker with a DJ-mode guard, plus a clock cap and thermal check | all | 1–2 days | medium |
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
- **Do:** (1) hand-check 200 logged routes and compute accuracy per route; (2) label 2–3k logged messages with a strong teacher (your best local model overnight, or Claude) plus your own corrections, so the labels are not Laya's own guesses; (3) fine-tune with Laya's notebook on **Kaggle's free 2×T4** (≈4–5 h for 30k questions per the README; keeps your GPU free) or its CPU/MPS script; (4) fit temperatures on held-out data and gate on `answer_confidence`; (5) A/B against the cheap baseline: EmbeddingGemma-300M embeddings + logistic regression on the same labels. Keep whichever wins.
- **Pitfalls named in the README:** don't use `true`/`false` or `yes`/`no` as `choice` labels (the model follows the label word); negated requests can flip (e.g. "don't cancel" → `cancel_account` at p=0.9998); more than ~20 options per question get truncated, so split coarse/fine.
- **Confidence: high** for "measure and fine-tune" (it is what the project's own maintainers say); medium on how much it gains on *your* routes.
- **Could fail if:** labels are too few or too noisy, or your messages mix Arabic and English in ways the multilingual checkpoint reads poorly. Kaggle means uploading your messages to Google: strip anything private first, or train on CPU.
- **First step:** export 200 recent routing decisions with the message text and mark each right or wrong. One evening.

### 3. Serve vision and structured output with llama.cpp, not Ollama
- **Why:** Ollama issue [#14493](https://github.com/ollama/ollama/issues/14493) (open, comments into Sep 2026) reports that Ollama's Go runner, which newer models such as Qwen 3.5 run on, **silently ignores `repeat_penalty`, `presence_penalty` and `frequency_penalty`**, and that the `qwen3-vl` renderer is affected by a missing-generation-prompt bug. Separate issues show Qwen3-VL repetition loops in Ollama and LM Studio ([QwenLM/Qwen3-VL#1611](https://github.com/QwenLM/Qwen3-VL/issues/1611)), garbage when image tokens exceed `num_ctx` ([ollama#13084](https://github.com/ollama/ollama/issues/13084)), and broken JSON with thinking + `format` ([ollama#10929](https://github.com/ollama/ollama/issues/10929)). That is a close match to "broken or looping JSON".
- **Do:** run the VLM with `llama-server --jinja -m <model>.gguf --mmproj <mmproj>.gguf`, pass a JSON schema (`response_format`/`json_schema`), keep penalties on, and design the schema so it cannot loop: `maxItems` on every array, `maxLength` on strings, enums where possible, thinking off, `n_predict` capped. Validate with Pydantic; on failure retry once at a different temperature, then fall back to "free text → second small call that only formats JSON".
- **Confidence: medium.** The Ollama bug is documented; that it causes *your* loops is inferred. Grammar-constrained decoding can loop in llama.cpp too, which is why the schema bounds matter.
- **Could fail if:** the loops come from the frames (too many image tokens) rather than sampling. Test that first: halve the frame count and see if loops drop.
- **First step:** take the 20 reels that failed most recently, run them through llama-server with the bounded schema, and log the valid-JSON rate against Ollama.

### 4. Move Hermes to llama.cpp with expert offload; turn on Tool Search
- **Why:** Hermes now ships a managed llama.cpp runtime that places MoE expert weights in system RAM first and keeps attention and KV cache on the GPU, with a guaranteed ≥64K context and 15-minute idle unload ([local-models docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/local-models.md)). On a 12 GB RTX 3060, Qwen3.6-35B-A3B with `--n-cpu-moe 24` measured ~36 tok/s at 16K context ([DEV guide](https://dev.to/donald_lee_707b59c456e304/how-to-pick-n-cpu-moe-in-llamacpp-qwen36-35b-a3b-on-12-16-and-24-gb-gpus-43f3)); your 3080 Ti has ~2.5× the memory bandwidth. Hermes also has **Tool Search** (MCP tools hidden behind `tool_search`/`tool_describe`/`tool_call`) and `hermes prompt-size`; its own docs say prefill of the system prompt plus tool schemas dominates first-token time on local models.
- **Model:** Qwen3.6-35B-A3B (Apache-2.0, April 2026) if you have ≥32 GB RAM; otherwise Qwen3.5-9B (Apache-2.0, dense, hybrid attention so long context is cheap) fully on GPU.
- **Confidence: medium.** Docs read directly; speed numbers are from a slower card; tool-calling reliability for Qwen 3.5/3.6 is reported as stack-dependent.
- **Could fail if:** RAM is 16 GB, or the Qwen3.6 tool-call template misbehaves. Keep your current Qwen3-Coder-30B config as a fallback profile.
- **First step:** `hermes prompt-size` today to see how many tokens your MCP tools cost per turn; then `hermes model` → Local models and compare against Ollama on 20 of your own logged requests.

### 5. Measure 40 reference clips
- **Why:** I found **no published description** of how Boiler Room, BCCO or HÖR cut their shorts. Guessing produces the "stock" look. Your own whatstheID notes show the method that works for you: measure, then build.
- **Do:** collect ~40 clips (analysis only, never re-published). Run shot detection (PySceneDetect, BSD-3, or FilmCraft's `clip.sceneEditDetection`) and beat tracking (Beat This) on each. Output: cuts per clip, shot length in beats, % of cuts on a downbeat/bar/phrase line, where the drop sits, how long the first shot holds, when text appears and what it says.
- **Hypothesis to test:** many of these clips are one or two fixed-camera shots where the edit is mostly *selection* (start a few bars before the drop, end on the reaction) plus a track-ID caption, not rapid cutting. If true, alternating crowd/DJ cuts is the wrong default.
- **Confidence: high** that it pays off; the numbers it finds are unknown by definition.
- **First step:** a 50-line script over a folder of clips → CSV; look at the medians.

### 6. One GPU broker with a DJ-mode guard
- **Why:** every project competes for one 12 GB GPU and the PC has crashed on long runs. A single broker turns that into scheduling, not luck.
- **Do:** a tiny local service (SQLite lease table, FastAPI or plain socket): each job asks for a lease with priority and an estimated VRAM; the broker unloads idle LLMs (Ollama `keep_alive: 0`, or llama-swap TTLs) before granting a large job; it **refuses all GPU jobs while `Serato DJ Pro.exe` / `Serato DJ Lite.exe` / `Ableton Live*.exe` is running** (psutil); every job checkpoints so a refused or killed job resumes.
- **Hardware side:** on RTX 30-series, crashes under load are often millisecond transients that a power cap does not stop. Cheap things to try: cap the core clock (`nvidia-smi -lgc 210,1700` as admin, or an Afterburner curve), and watch **GDDR6X memory junction temperature** in HWiNFO during a long LLM or Whisper run (memory-bound work behaves like mining; 3080-class cards reach 104–110 °C there). If junction temps are high, thermal pads; if crashes persist at a capped clock, suspect the PSU.
- **Confidence: medium.** The broker is standard engineering; the crash diagnosis is from forum reports, not your logs.
- **First step:** log `nvidia-smi --query-gpu=power.draw,clocks.gr,temperature.gpu,memory.used --format=csv -l 1` plus HWiNFO memory junction during the next long Reel Brain batch.

### 7. Beat grids for your own sets from your own track files
- **Why:** blind beat tracking on a 150 BPM mix fights overlapping kicks in transitions, pitch riding and breakdowns. You have better information. **Serato DJ 4 logs every load** in `master.sqlite` → `history_entry` (artist, title, BPM, key, deck, `start_time`, `played`; verified in the [whats-now-playing reader](https://github.com/whatsnowplaying/whats-now-playing/blob/main/nowplaying/serato/reader.py)). Your library files carry Serato's beat grid (`Serato BeatGrid` GEOB). Align each played track to the set recording (your cross-correlation code plus whatstheID's speed ladder), then transform that track's grid into set time. This is the published "DJ-mix reverse engineering" approach (Schwarz & Fourer; Kim et al., ISMIR 2020).
- **Fallback:** Beat This ([CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT, ~78 MB model, pip install, no madmom needed) for tracks you don't own. Evidence it suits your genre: a user benchmark on Giant Steps (664 Beatport electronic tracks) in [issue #13](https://github.com/CPJKU/beat_this/issues/13) got **89.3 % strict / 95.0 % octave-tolerant** tempo accuracy, 90.9 / 96.4 % with an ensemble of the *small* models (which did better than the big ones on near-constant tempo). The maintainers confirmed in [issue #16](https://github.com/CPJKU/beat_this/issues/16) that the MIT licence covers the weights. Add an octave-correction prior (120–160 BPM for techno).
- **Recording note:** the MC4000 unlocks **Serato DJ Lite**, which has a History panel but no built-in mix recorder (Pro has one). If your recordings come from OBS or the controller, alignment is the same; only the clock you seed it with differs. On Serato 3.x the history is the older binary `_Serato_/History/Sessions/*.session` format (also parsed by whats-now-playing) instead of `master.sqlite`.
- **Precedent on real mixes:** Kim et al. (ISMIR 2020, [djmix-analysis](https://github.com/mir-aidj/djmix-analysis)) aligned tracks to 1,557 real 1001Tracklists mixes with subsequence DTW, worked example a Boiler Room set; they report DJs rarely change tempo or key much, which keeps stretch ratios small. Their repo has no licence file: read it, don't copy it.
- **Confidence: medium.** The history fields are verified from code; alignment through heavy EQ/filter/FX is not tested on your sets.
- **Could fail if:** the DJ rides the pitch so the stretch ratio drifts inside a track (fit it piecewise) or the track was played from a streaming service (no file).
- **First step:** open your `master.sqlite` (read-only copy) and list the last session's `history_entry` rows next to your set recording's start time.

### 8. Encode one house look per client
- **Why:** "stock AI" is mostly the absence of decisions: default type, eased slides, a new colour per scene. A look that is written down as rules can be checked by your existing motion-graphics QA step; taste that lives in a prompt cannot.
- **Do:** per client, one `look.md` (also the Inspiration Canvas format, see 2.5): one display face and one text face from libre foundries (Velvetyne, Collletttivo; check each font's licence), a type scale, a palette sampled from *their* footage (dominant colours + one accent), and a **motion grammar on the bar grid**: things appear and hold on downbeats, move only across bar lines, hard-cut on the drop, no ease-in-out slides. Then run [motionmaxxing](https://github.com/Tejashmakwana/motionmaxxing)'s list of tells (Apache-2.0: "everything is a slide", typed-out headline with a caret, a new flat colour per scene) as a rubric in your QA step.
- **Also:** set Arabic text in the HTML layer, not in FilmCraft: upstream reports Arabic titles broken ([storytold/filmcraft#395](https://github.com/storytold/filmcraft/issues/395), open; a fix PR for fallback fonts and captions is linked but unmerged as of 2026-10-11). Browsers shape Arabic correctly.
- **Evidence it is more than opinion:** motionmaxxing's rules come from 53 frame-accurate professional motion moments decoded into ~150 rules, with lint gates (corner labels, deck layouts, typed headlines, >3 dead frames in a row) and one striking count: pros used **3,392 transform keyframes against 584 opacity fades**, i.e. things move and cut, they rarely fade. It is an early release built on brand/product films, not club footage.
- **Confidence: low.** Taste is the least verifiable claim in this report; the rules are measured on brand films, not on your audience or on club clips.
- **Could fail if:** the rules are followed and the result is merely tidy. The reference measurements (Top 10 #5) and a human eye on every first clip of a series are the backstop.
- **First step:** write `look.md` for the collective you want to pitch, using their existing flyers as the source.

### 9. Reframe from body pose + an L1-optimal camera path
- **Why:** YuNet finds faces; a DJ looks down at the controller under strobes, so faces drop out exactly when it matters. A real operator frames the body and hands, holds still, then pans deliberately.
- **Do:** detect people and keypoints with RTMPose via [rtmlib](https://github.com/Tau-J/rtmlib) (Apache-2.0, ONNX, light) and keep YuNet as one signal. Choose the subject per shot, then solve the crop path offline as an L1-optimal path (Grundmann et al., "Auto-Directed Video Stabilization with Robust L1 Optimal Camera Paths", the method behind YouTube's stabiliser): the L1 objective produces static holds, constant pans and smooth ease-ins, like a camera operator. Google's AutoFlip (polynomial L2 fit) is the obvious off-the-shelf alternative, but MediaPipe lists it as a legacy solution whose support ended on 2023-03-01. I found MATLAB re-implementations of the L1 paper but no maintained Python one; the linear program is small enough to write with `scipy.optimize.linprog` (HiGHS, BSD) or cvxpy.
- **Avoid:** Ultralytics YOLO (AGPL-3.0) anywhere near the FilmCraft fork.
- **Confidence: medium.** Both pieces are established; the combination on club footage is untested.
- **First step:** run rtmlib on one 60-second DJ clip and plot face-detection vs body-detection coverage per frame.

### 10. Write Serato grids and cues with rb2serato's encoders
- **Why:** [rb2serato](https://github.com/SM4RTENHEIMER/rb2serato) (MIT, Sep 2026) writes `Serato Markers2`, `Serato Markers_` and **locked** `Serato BeatGrid` tags whose bytes match what Serato writes, verified on a 9,600-track library, with undo logs and audio-byte checks. It also documents Serato 4's import quirks (crate header must be exactly `1.0/Serato ScratchLive Crate`, WAV typed `wave`, Serato closed while writing). That is the risky half of whatstheID's 4c plan, already done.
- **Confidence: medium.** Tested on macOS only; its shell wrapper and APFS-clone safety step need Windows equivalents.
- **First step:** vendor its encoder module into whatstheID, write a grid to a *copy* of one track, load it in Serato, confirm.

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

**Shot picking from two synced angles (proposal)**
1. Per shot window (aligned to bars): sharpness (Laplacian variance), exposure, motion energy, face/pose visibility, hands-up count (wrists above head from pose), strobe flashes.
2. Hard rules from the measured benchmark (Top 10 #5): minimum shot length in bars, change angle only on bar or phrase lines, crowd angle at the drop plus ~1 bar (crowd reaction lags the drop).
3. Learn your taste: label ~200 shots keep/skip, train a logistic head on frozen SigLIP embeddings (Apache-2.0). An IEEE paper on autonomous multi-camera editing learned an editor's preferences from 33 scenes with CLIP + SVM (79.7 % of scenes judged "usable"; publication date not confirmed).
4. The LLM only chooses among pre-scored candidates and writes the plan as JSON; it does not watch video.

**Planner and judge in 12 GB**
- Planner: Qwen3.5-9B (Apache-2.0, natively multimodal) or your Hermes model; constrained JSON via llama.cpp.
- **Don't let a model judge taste.** Timeline-Bench (arXiv 2609.35143, Sep 2026) gave agents 56 realistic raw-footage editing tasks: the best resolved 26.8 %, the average 14 %, and most failed runs failed *only* the quality test, which the authors attribute to agents judging footage through stills and transcripts rather than craft. Pairwise LLM judges still flip with presentation order in up to 20 % of cases (J1, 2025). Use the VLM as a **defect checker** with yes/no questions on contact sheets (text over a face? cut mid-word? black or frozen frames? drop missing? first frame dark?) and keep the taste pick for yourself or for Trial Reels.
- **Write the plan as OpenTimelineIO.** FilmCraft imports and exports OTIO (`crates/interchange`); a plan in OTIO plus a sidecar JSON for effects decouples Creative Studio from FilmCraft's command IDs, which change fast (upstream merged hundreds of PRs in October), and gives you a fallback editor if a FilmCraft build misbehaves on Windows. Pin the fork to a release tag (latest: v0.7.2) rather than tracking `main`.

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
| Beats/downbeats | Beat This `final0` | MIT | < 1 GB |
| Planner / judge | Qwen3.5-9B Q5 + mmproj | Apache-2.0 | ~7–8 GB |
| Pose | RTMPose (rtmlib, ONNX) | Apache-2.0 | < 1 GB |
| Taste head | SigLIP base + logistic | Apache-2.0 | < 1 GB |
| Stills (commercial) | FLUX.2 klein 4B / Z-Image-Turbo | Apache-2.0 | ~8–13 GB / ~6–10 GB quantized |
| Video gen (personal) | MiniMax H3 Q4 GGUF | MiniMax community licence | ~11.6 GB file + offload |
| Egyptian Arabic / code-switched speech | [QwenCleo-ASR](https://github.com/MohammedAly22/qwencleo-asr) (Qwen3-ASR-1.7B fine-tune) or Cohere Transcribe Arabic (2B, 2026-07) | Apache-2.0 / Apache-2.0 | ~4–6 GB |
| English speech + word timings | faster-whisper / whisperX large-v3 | MIT / BSD-2 | ~3–5 GB |

**Auto-posting: what the platforms allow**
- **Instagram:** the Instagram API with Instagram Login publishes reels from a professional account without a Facebook Page; the cap is 50 or 100 API posts per 24 h depending on which Meta page you read (query `GET /<IG_ID>/content_publishing_limit` for the live value); the video must sit at a public URL when you publish.
- **TikTok:** an unaudited Content Posting API client can only post **private** videos from private accounts, up to 5 users a day; the audit reportedly takes 2–4 weeks and needs a demo video. Until then, "auto-post to TikTok" means "upload as draft/private". (Creator Rewards is not available in Egypt anyway.)
- **YouTube:** uploads from an unverified API project created after 2020-07-28 are locked to **private** until the project passes a compliance audit.
- **Postiz** (AGPL-3.0, self-hosted scheduler for 30+ platforms) is fine to run as a separate service, but it inherits all of the above approvals; it does not get around them.

**Open risks**
- FilmCraft upstream's own gap list: Windows runtime is under-tested (G9), no PR CI (G4), and **10-bit / 4:2:2 H.264/HEVC does not decode on Windows without hardware support** (G3). If your camera records 10-bit 4:2:2, transcode to 8-bit 4:2:0 before ingest or the import fails.
- **Arabic text:** FilmCraft's title engine has harfrust + bidi, but Arabic titles are reported broken upstream (#395, open). Render Arabic captions in the HTML layer.
- **Noisy low-light footage** is a bigger "cheap" signal than any graphic. Try ffmpeg's `nlmeans`/`hqdn3d` as an external pre-pass first; DaVinci Resolve Studio's temporal noise reduction ($295 one-time) is the standard paid fix if that is not enough.
- **Client work: deliver, don't auto-post.** A collective will want to approve posts and will not hand you its account; keep auto-posting for your own channels.
- Copyright: club clips carry other artists' tracks. Instagram mutes or limits; plan captions and track IDs (Serato history gives you artist and title for free), and keep originals.

### 2.2 Hermes + Laya

**Adopt**
- Hermes' managed llama.cpp runtime or your own `llama-server` (`providers.llamacpp.base_url`), Top 10 #4.
- **Tool Search** for MCP tools; `hermes prompt-size` and `hermes tools` to cut the fixed prompt.
- **Kanban** (built in, SQLite `~/.hermes/kanban.db`, per-task model override, durable handoffs, retries, circuit breaker) for multi-agent work instead of a new orchestrator. Hermes' own docs position it as the reliable alternative to in-process subagent swarms.
- **Memory:** keep Hermes' built-in `MEMORY.md`/`USER.md` small and make the Obsidian vault the knowledge store, reached through one MCP server (see Shared pieces). Of the memory plugins, only Holographic (local SQLite + FTS5) and ByteRover (local) are local-only; RetainDB and ByteRover leave Hermes core on 2026-10-15.

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

**Open risks:** Qwen 3.5/3.6 tool-call templates are fragile across servers (Ollama issue above; use `--jinja` and the `qwen3_coder` parser where offered). Hermes' 48k open issues/PRs means fast churn: pin a version.

### 2.3 Reel Brain

**Adopt**
- llama.cpp for the VLM with bounded schemas (Top 10 #3).
- **Try Qwen3.5-9B against Qwen3-VL-8B** on 30 reels: Qwen says 3.5's early-fusion training beats Qwen3-VL on visual understanding (vendor claim). MiniCPM-V 4.5 (8.7B, reports 73.5 on Video-MME, llama.cpp support since b6282) is the video-specialised alternative.
- Linear probe + top-3 classification; repo verification with a "no repo" outcome (below).
- Port ideas from juspay/dopamine: link resolver that remembers failed lookups, verifier, project mapper with "avoid".
- Run batches through the GPU broker with per-item checkpoints (SQLite job table) so a crash costs one reel, not the run.

**Classification and repo linking**
- **Why:** kNN at 63 % is a weak baseline. A logistic-regression "linear probe" on the same embeddings usually beats kNN once you have ~1,000 labels; showing the top 3 turns a 63 % top-1 into a much higher hit rate for one click. For repos, a published study (SONAD) found LLMs over-accept candidates (precision 68 %, recall 97 %) while a feature-based verifier reached 82 % precision.
- **Do:** (a) re-label 50 random reels blind to find your own consistency ceiling; (b) linear probe + top-3 + LLM rerank only when the top-2 margin is small; (c) for repos: candidates from GitHub/Hugging Face search, then score exact name match, owner, README similarity to the reel's context and stars, and allow "no repo". Your whatstheID `verify.py` already encodes the right rules (empty is a refusal, exact-match preference, word-level coverage × precision).
- **Borrow:** [juspay/dopamine](https://github.com/juspay/dopamine) (MIT, active) is the same pipeline on Gemini; its project mapper (embedding prefilter + judge with an "avoid" field per project) is what your per-project ranking needs.
- **Confidence: medium.**
- **First step:** the 50-item blind re-label.

**Drop or avoid**
- instagrapi for collecting saves (Dopamine uses it; it logs into your account through a private API and risks a ban). Use Instagram's own "Download your information" export (JSON) for the list of saved items, then fetch only what you need.

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
- rb2serato encoders for grids and cues (Top 10 #10). [serato-tools](https://pypi.org/project/serato-tools/) (Python ≥3.12) is an alternative; **pyserato is AGPL-3.0**, avoid if you ever distribute.
- **Rekordbox:** [pyrekordbox](https://github.com/dylanljones/pyrekordbox) (MIT, active) and Rekordbox XML, whose `TEMPO` entries carry variable grids (tempo changes).
- **Grid quality:** fit the grid to the **kick attack**, not the energy peak (onset of the low band's envelope rise), per beat, then least-squares the tempo. rb2serato measured Serato's grid a median 8 ms ahead of Rekordbox's on 1,563 MP3s: check your offset against Serato on your own files.
- **Downbeats/phrases:** score each of the 4 bar phases (and 8/16-bar phrase phases) by how well novelty peaks (energy, new elements, breakdown edges) land on them. Half-time D&B: prefer 170–176 over 85–88 by genre prior.
- **IDs in long mixes:** segment first (novelty), then query the middle of each segment where one track plays alone, instead of a fixed 60 s grid; keep the speed ladder.
- **Reference rbxport** ([rbxport.com](https://rbxport.com/)): a free Rekordbox library manager (not open source) by Chris Le, who also wrote [serato-connect](https://github.com/chrisle/serato-connect) (MIT). Its grid analysis is "tuned for electronic music"; I could not read details (site unreachable).
- **Visualiser:** drive shaders from beat/bar/phrase *phase* from your analysis, not raw FFT amplitude: visuals lock to the music's structure. Butterchurn (MIT, Milkdrop in WebGL) is a reference; Hydra is AGPL.

**Avoid:** Panako and Olaf (both AGPL-3.0) as code; read their papers for the tempo-invariant ideas.

**Soulseek-first downloads (not on `main` yet):** slskd is AGPL-3.0; calling its HTTP API from whatstheID as a separate process does not make whatstheID AGPL, but bundling or modifying slskd would. For a tool you share with other DJs, automated P2P downloading is also the part most likely to draw complaints: keep it a user-configured option, not a default.

**Sharing it with other DJs: the field is not empty.** TrackSniff (web, free 50 IDs/month, $9–19/month; mixed accuracy in one academy's test), Mixprism, audioscout.io and AudD (says it handles hours-long mixes; $2–5 per 1,000 requests after 300 free) already do "paste a mix, get a tracklist". What none of them do is what whatstheID already does: **fingerprint against the DJ's own library** (your `fingerprint.py` notes that Shazam named 0 of 6 underground records and AudD 3) and write grids back to Serato. Lead with that; treat cloud ID as a fallback.

### 2.5 Inspiration Canvas (idea stage)

**Recommendation: do not build a canvas app yet. Build the board format first, inside your Obsidian vault.**
- Store boards as **JSON Canvas** (`.canvas`, open spec, MIT, what Obsidian Canvas uses): nodes for images/videos/notes/links, edges for relations. Any LLM can read and write it; Obsidian renders it for free.
- A "look pack" = a folder with the images, a `look.md` (palette, type, motion rules, what to avoid) and a `.canvas` board. Creative Studio reads `look.md`.
- Imports: Instagram via the official data export (same as Reel Brain); Pinterest via its data export or API v5 Trial access (reading your own boards and pins is allowed on Trial; approval is reported as slow).
- If you later want a real app: tldraw needs a licence key in production but runs free in development mode on `localhost`; Excalidraw is MIT. A FilmCraft extension would mean egui work in a Rust app whose Windows runtime is already the weak spot: no.
- **The paid option that may simply win:** Eagle (eagle.cool), a local image/video reference manager with a browser extension and plugin system, **$34.95 one-time for two devices**, 30-day trial. If what you want is "collect and tag fast", it already does that; a small exporter from Eagle's library folder to `.canvas` + `look.md` gives Claude the read access.

---

## 3. Cross-project shared pieces

1. **GPU broker with DJ-mode guard** (Top 10 #6): every project.
2. **One local model server** (llama.cpp / llama-swap, MIT) instead of Ollama + Hermes runtime + ComfyUI each loading their own copy: one place to unload, one place to measure.
3. **One vault access layer:** a single MCP server over the Obsidian vault (read/write notes, search by text and embeddings) used by Hermes, Claude Code, Reel Brain and the canvas. You already write to the vault via `learn-to-vault` / claude-obsidian (Karpathy LLM-wiki pattern); don't add a second memory database that drifts from it.
4. **One verification module** for "does this search hit really match": whatstheID's `verify.py` rules reused for Reel Brain's tool→repo links.
5. **Shared audio analysis:** whatstheID's comb-filter tempo and key code, Beat This, and Serato readers serve both whatstheID and Creative Studio.
6. **Shared embeddings:** EmbeddingGemma for Laya, Reel Brain and canvas search.

---

## 4. Money (round 1, unverified for Egypt in detail)

1. **Event clip packs for Cairo collectives** (Geeza, MOSHTRQ, INTG, BackSpin, Analog Room are active per SceneNoise). Paid locally in EGP (InstaPay/bank). First test: offer one collective a free 3-clip pack from their next night in exchange for a testimonial and access; price the second.
2. **Arabic/English podcast and founder clips** (tools to start from: [Cutcast](https://github.com/BoazCohenJ/Cutcast), MIT, Windows, syncs cameras by audio and cuts to the active speaker; [podcast-editor](https://github.com/vamshicreates/podcast-editor), MIT; [FunClip](https://github.com/modelscope/FunClip), MIT, transcript-driven clipping) on Upwork: a May 2026 Upwork post paid **$50 fixed** for one 30–45 s Arabic clip with animated captions and drew 10–15 proposals. AI tools make generic clipping cost ~$1/episode, so compete on Arabic captions and taste, not volume. The technical edge is real: on an Egyptian + code-switching test set of 3,699 utterances, QwenCleo-ASR reports **19.9 % WER against 63.9 % for Whisper large-v3** (self-reported by its author; test it on your own audio before believing it). Most clipping tools run Whisper. Payout from Egypt: Payoneer is the usual route; PayPal withdrawals in Egypt are EGP-only with a markup; Wise is limited for Egyptian residents.
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
