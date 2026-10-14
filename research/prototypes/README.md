# Prototypes for the first week

Small, standalone Python scripts behind the Top 10 moves in `../projects-research.md`.
Each has a test that builds synthetic input (no GPU, no model downloads) and checks
the result; `test_plan_to_filmcraft.py` also needs ffmpeg and a `filmcraft-cli` built from your fork
(set `FILMCRAFT_CLI`), and prints SKIP without one. They were written and tested in a Linux container on 2026-10-14; they
use only cross-platform calls (pathlib, `subprocess` with argument lists, no shell)
and should run on Windows, but **nobody has run them on Windows yet**.

| Script | Top 10 | What it does | Test result (synthetic) |
|---|---|---|---|
| `analyze_reference_clips.py` | #6 | Cuts vs beats/bars/8-bar phrases, shot length in beats, drop position, for a folder of reference clips; `--strobe-safe` rejects strobe flashes; librosa beats shifted onto the kick transients (they sat 19–31 ms late on a recorded loop, which counts a cut one frame early as off-beat) | 150 BPM clip, 7 known cuts: BPM 150.02, 7/7 cuts, on-beat 85.7 %, on-bar 71.4 %, drop at 16.02 s (true 16.0). Same clip with strobes inside one shot: plain detector 9 cuts, `--strobe-safe` 7 |
| `vlm_json_guard.py` | #4 | Downscaled frames, token budget vs `num_ctx`, Qwen's recommended sampling, bounded schema (every list item too), an output cap computed from the schema's worst case, loop detection, retry, two-pass fallback; Ollama or OpenAI-compatible API | Fake server that loops, then returns invalid JSON: recovered a valid note via the fallback on both APIs; 8 frames at 360×640 ≈ 1.9k tokens vs > 16k at full resolution. Schema run through a real llama.cpp converter build: all bounds enforced; output cap 2,167 tokens (the old 700 would truncate long valid notes); raw Pydantic schema flagged for its unbounded list items |
| `downbeat_phase.py` | whatstheID (2.4), #8 | Which beat is "one" on a 4/4 grid: backbeat claps + bar-level novelty; reports when it can't tell beat 1 from beat 3; 8-bar phrase starts from the track's first bar, with novelty as a flagged second opinion | Synthetic 150 BPM techno, 6 seeds × 3 versions: right phase every time with structure; claps-only always flagged ambiguous. Recorded 125 BPM loop: phase 0, phrases at 0 and 15.36 s; the old "after the biggest change" rule was a bar late there (now a flagged disagreement) |
| `serato_set_grid.py` | #8 | Reads Serato 4 `master.sqlite` history; aligns a track you own inside your set recording (offset + stretch ratio) and maps its grid into set time | Track played 3 % fast with its bass cut for a 30 s blend and noise on top: ratio 1.030 (true 1.03), offset 50.015 s (true 50.0) |
| `key_benchmark.py` | whatstheID (2.4) | Scores a key detector (whatstheID's analyser by default) against the GiantSteps human key labels: MIREX weighted score, exact %, mixable %, and misses caught by `key_uncertain`; per genre, cached and resumable | Both datasets' annotation layouts parsed (604 + 1,349 usable labels); scoring identical to mir_eval on all 576 key pairs (allowing descending fifths, as MIREX does); whatstheID's real analyser on 4 synthetic tracks: 4/4 mixable, 2 exact. Real GiantSteps audio not run (blocked here) |
| `l1_reframe_path.py` | #9 | L1-optimal (Grundmann et al.) 9:16 crop path from noisy subject positions | 20 s DJ, 15 px jitter, 10 % missed detections: 83.6 % of frames static, 0 direction changes, subject in frame 100 %; an EMA follow: 11.5 % static, 189 direction changes. Solves 600 frames in 0.2 s |
| `collections_probe.py` | Reel Brain (2.3) | kNN vs logistic-regression probe vs probe top-3 on your own embeddings and folders (5-fold CV), an ask-me-when-unsure rule, per-folder accuracy, most-confused pairs; top-3 predictions for new reels | Synthetic 1,000 "reels", 8 imbalanced folders, two overlapping: kNN 0.75–0.81, probe 0.86, top-3 0.999; overlapping pair tops the confusions |
| `repo_linker.py` | Reel Brain (2.3) | Tool name → GitHub/HF repo or "no repo": explicit mentions verified first, then search candidates scored on exact name, context fit, owner, stars, fork/archived | Offline fake resolver: OCR typo falls back to search, fork loses to original, "lang chain" → LangChain, substring and SaaS cases → no repo, near-ties → ambiguous, prose slashes ignored |
| `gpu_queue.py` | #2 (shared) | Crash-safe batch queue: one SQLite row per item, waits while the DJ lock is set, retries with backoff, parks repeat failures, resumes after a crash | Fake clock: 9 done / 1 parked, transient failure retried once, two waits for the DJ lock; a worker killed mid-item (`os._exit`) costs exactly that item on restart |
| `dj_guard.py` | #2 | While Serato or Ableton runs: switches llama-swap to a `dj` profile (every model 404s), unloads everything, re-unloads anything that sneaks in; `gpu_allowed()` for batch jobs | Fake llama-swap: profile on, unload, re-unload, profile cleared. **Real llama-swap** (built from source, committed config, stand-in model servers): exclusive swap, 404s in DJ mode, a ComfyUI job unloaded again, service restored (`test_dj_guard_llama_swap.py`, SKIP without the binary) |
| `laya_eval.py` | #3 | Accuracy per route, confusions, calibration (ECE), confidence gate, a cheap baseline on the same labels; exports a CSV for `laya-train` or Laya's JSONL cases | Router right 41 % at ~0.9 confidence: ECE 0.49 flagged; TF-IDF baseline 100 % on the learnable synthetic routes |
| `beat_lint.py` | Creative Studio (2.1, house look) | Lints a HyperFrames composition against the beat grid (clip starts/ends, bar-line titles, relative starts, GSAP tween positions) and flags in-out slides and typed-out text | Synthetic composition at 150 BPM: off-beat clip reported 150 ms after its beat, bar miss, off-beat tween, in-out slide and typewriter found; on-grid clips, an opt-out and an out-eased move pass. Sub-compositions linted on the absolute timeline; `.set(` cuts and Prettier's trailing commas read; computed/relative positions reported as `unchecked_positions`. On HyperFrames' own chat example (`packages/producer/tests/chat`): 1 tween 62 ms off, 10 positions unchecked |
| `shot_picker.py` | Creative Studio (2.1) | Which synced camera angle per bar: sharpness, exposure, motion, strobes per bar; dynamic programming with cuts only on bar lines, min/soft-max shot length, crowd on the drop; writes a plan for `plan_to_filmcraft.py` | Two synthetic offset angles at 150 BPM (one dark 4 bars, one blurred 6): avoids both, crowd on the drop, offsets mapped; equal scores give 4-bar shots |
| `serato_writeback.py` | #10 (whatstheID) | Cues merged into your existing Serato cues (free slots only; loops, colour, lock kept; Flip data refused), grids only when asked; grid anchor + BPM fitted to every kick transient (refuses drifting tempo); rb2serato's encoders; **FLAC** Vorbis-comment writer (neither rb2serato nor serato-tools writes FLAC); copy → tag → audio-hash check → replace, Windows-safe; MP3 offset option; `compare` vs Serato's own grids | Recorded 125 BPM techno loop (Essentia test audio, not committed): anchor 0.9 ms after the transient, 124.9997 BPM, 0.6 ms rms (librosa `beat_track`: 123.05). Synthetic 180 s at 132.004 BPM analysed as 132.0: 132.0042, ~2 ms fixed bias; 0.05 BPM/min drift refused. MP3/FLAC/WAV: audio unchanged, grid and 3 cues read back by our decoder and serato-tools (MP3, FLAC); hand-set cues/loop/colour/lock/grid survive a cues-only write (MP3, FLAC); Flip tag refused untouched; damaging write refused; NaN/0/1000 BPM refused |
| `track_id_captions.py` | Creative Studio, #8 | Serato history (or aligned track times) → "ID: Artist – Title" SRT for a clip's window; unplayed loads skipped, slivers dropped | Unit test on a 5-track history; also part of the end-to-end test below |
| `test_pipeline_e2e.py` | #5 | The chain: fake Serato history → ID captions; two synced angles → `shot_picker` → plan → `plan_to_filmcraft` → MP4 | Against upstream v0.7.2: 1080×1920, 19.2 s, cuts on bar lines (frames 0/192/288), both ID captions burned in, audio present. SKIP without a build |
| `plan_to_filmcraft.py` | #5 | Edit plan (JSON) → your FilmCraft fork, headless over MCP: 9:16 sequence, cuts from two cameras, L1 reframe written as Motion anchor keyframes, set audio, captions, H.264 export; refuses sources FilmCraft can't decode (10-bit H.264, 4:2:2) before import | Real `filmcraft-cli` build, two synthetic cameras, noisy gappy detections: cuts on the planned frames (90/135/225), subject fully in frame 100 % of reframed frames (centre crop: 34 %), 8–14 keyframes per shot, captions burned in, audio present. Test prints SKIP without a build. Codec check (ffmpeg only): 10-bit H.264 and 4:2:2 HEVC refused, 8-bit H.264 and 10-bit 4:2:0 HEVC accepted, matching what v0.7.2 actually decoded |
| `filmcraft_arabic_captions.jsonl` | #5 | Headless FilmCraft run: import an Arabic SRT, set an Arabic caption font, export with captions burned in | Built the fork's `filmcraft-cli` (Linux): default font gives "NO GLYPH" boxes; with Noto Sans Arabic named, joined letters in correct right-to-left order |
| `llama-swap.example.yaml` | #2 | One exclusive GPU group: agent, small agent, the Gemma 4 12B challenger, two VLMs, Egyptian-Arabic ASR, ComfyUI; a `dj` profile | `llama-swap -validate` passes; served by a real llama-swap build in the test above |

**Licences:** every dependency in `requirements.txt` is permissive (numpy, scipy, scikit-learn, soundfile, psutil,
httpx: BSD; librosa: ISC; PySceneDetect: BSD-3; OpenCV: Apache-2.0; pydantic, PyYAML: MIT), so these scripts can live
in the MIT/Apache fork. The one exception is `serato_writeback.py`: its write path imports mutagen (GPL-2.0-or-later)
at run time. It contains no mutagen code, mutagen is not in `requirements.txt`, and its anchor half runs without it, but
the script belongs in whatstheID (which already uses mutagen and isn't distributed): copy it there and delete it from the
fork if you want the fork free of GPL dependencies too. serato-tools is MIT but needs mutagen as well; rb2serato's
`seratotags.py`, which it loads for the tag bytes, is MIT and stdlib-only.

## Setup (Windows, PowerShell, one command per line)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
winget install ffmpeg
```

Optional: `pip install beat-this` (pulls PyTorch) to use Beat This instead of librosa in
`analyze_reference_clips.py`; `pip install sentence-transformers` for an
EmbeddingGemma baseline in `laya_eval.py`.

## Run the tests

```powershell
python run_tests.py
```

## Honest limits

- Synthetic tests prove the code does what it says on clean, known input. They do not
  prove it works on your footage, your sets or your routes; the first-week plan in the
  report says what to measure on real data.
- `dj_guard.py` matches process names by pattern (`Serato DJ Pro*`, `Serato DJ Lite*`, `Ableton Live*`); I could not
  confirm Serato's exact executable name. Run `python dj_guard.py --once` with Serato open and add the name from
  Task Manager → Details with `--watch` if it isn't found.
- `serato_set_grid.py` reads the Serato 4 schema as the open-source whats-now-playing
  project reads it. Serato 3.x history (`.session` files) is not handled.
- `analyze_reference_clips.py` counts phrases in 8-bar steps from the detected drop,
  because club tracks start a phrase on the drop. If its drop detection is wrong, the
  phrase column is wrong; the beat and bar columns don't depend on it.
