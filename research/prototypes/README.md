# Prototypes for the first week

Small, standalone Python scripts behind the Top 10 moves in `../projects-research.md`.
Each has a test that builds synthetic input (no GPU, no model downloads) and checks
the result; `test_plan_to_filmcraft.py` also needs ffmpeg and a `filmcraft-cli` built from your fork
(set `FILMCRAFT_CLI`), and prints SKIP without one. They were written and tested in a Linux container on 2026-10-14; they
use only cross-platform calls (pathlib, `subprocess` with argument lists, no shell)
and should run on Windows, but **nobody has run them on Windows yet**.

| Script | Top 10 | What it does | Test result (synthetic) |
|---|---|---|---|
| `analyze_reference_clips.py` | #6 | Cuts vs beats/bars/8-bar phrases, shot length in beats, drop position, for a folder of reference clips; `--strobe-safe` rejects strobe flashes | 150 BPM clip, 7 known cuts: BPM 150.02, 7/7 cuts, on-beat 85.7 %, on-bar 71.4 %, drop at 16.02 s (true 16.0). Same clip with strobes inside one shot: plain detector 9 cuts, `--strobe-safe` 7 |
| `vlm_json_guard.py` | #4 | Downscaled frames, token budget vs `num_ctx`, Qwen's recommended sampling, bounded schema, loop detection, retry, two-pass fallback; Ollama or OpenAI-compatible API | Fake server that loops, then returns invalid JSON: recovered a valid note via the fallback on both APIs; 8 frames at 360×640 ≈ 1.9k tokens vs > 16k at full resolution |
| `serato_set_grid.py` | #8 | Reads Serato 4 `master.sqlite` history; aligns a track you own inside your set recording (offset + stretch ratio) and maps its grid into set time | Track played 3 % fast with its bass cut for a 30 s blend and noise on top: ratio 1.030 (true 1.03), offset 50.015 s (true 50.0) |
| `l1_reframe_path.py` | #9 | L1-optimal (Grundmann et al.) 9:16 crop path from noisy subject positions | 20 s DJ, 15 px jitter, 10 % missed detections: 83.6 % of frames static, 0 direction changes, subject in frame 100 %; an EMA follow: 11.5 % static, 189 direction changes. Solves 600 frames in 0.2 s |
| `repo_linker.py` | Reel Brain (2.3) | Tool name → GitHub/HF repo or "no repo": explicit mentions verified first, then search candidates scored on exact name, context fit, owner, stars, fork/archived | Offline fake resolver: OCR typo falls back to search, fork loses to original, "lang chain" → LangChain, substring and SaaS cases → no repo, near-ties → ambiguous, prose slashes ignored |
| `dj_guard.py` | #2 | While Serato or Ableton runs: switches llama-swap to a `dj` profile (every model 404s), unloads everything, re-unloads anything that sneaks in; `gpu_allowed()` for batch jobs | Fake llama-swap: profile on, unload, re-unload, profile cleared. **Real llama-swap** (built from source, committed config, stand-in model servers): exclusive swap, 404s in DJ mode, a ComfyUI job unloaded again, service restored (`test_dj_guard_llama_swap.py`, SKIP without the binary) |
| `laya_eval.py` | #3 | Accuracy per route, confusions, calibration (ECE), confidence gate, a cheap baseline on the same labels; exports a CSV for `laya-train` or Laya's JSONL cases | Router right 41 % at ~0.9 confidence: ECE 0.49 flagged; TF-IDF baseline 100 % on the learnable synthetic routes |
| `shot_picker.py` | Creative Studio (2.1) | Which synced camera angle per bar: sharpness, exposure, motion, strobes per bar; dynamic programming with cuts only on bar lines, min/soft-max shot length, crowd on the drop; writes a plan for `plan_to_filmcraft.py` | Two synthetic offset angles at 150 BPM (one dark 4 bars, one blurred 6): avoids both, crowd on the drop, offsets mapped; equal scores give 4-bar shots |
| `plan_to_filmcraft.py` | #5 | Edit plan (JSON) → your FilmCraft fork, headless over MCP: 9:16 sequence, cuts from two cameras, L1 reframe written as Motion anchor keyframes, set audio, captions, H.264 export | Real `filmcraft-cli` build, two synthetic cameras, noisy gappy detections: cuts on the planned frames (90/135/225), subject fully in frame 100 % of reframed frames (centre crop: 34 %), 8–14 keyframes per shot, captions burned in, audio present. Test prints SKIP without a build |
| `filmcraft_arabic_captions.jsonl` | #5 | Headless FilmCraft run: import an Arabic SRT, set an Arabic caption font, export with captions burned in | Built the fork's `filmcraft-cli` (Linux): default font gives "NO GLYPH" boxes; with Noto Sans Arabic named, joined letters in correct right-to-left order |
| `llama-swap.example.yaml` | #2 | One exclusive GPU group: agent, small agent, two VLMs, Egyptian-Arabic ASR, ComfyUI; a `dj` profile | `llama-swap -validate` passes; served by a real llama-swap build in the test above |

**Licences:** every dependency in `requirements.txt` is permissive (numpy, scipy, scikit-learn, soundfile, psutil,
httpx: BSD; librosa: ISC; PySceneDetect: BSD-3; OpenCV: Apache-2.0; pydantic, PyYAML: MIT), so these scripts can live
in the MIT/Apache fork. Serato tag writing is deliberately not here: the Python tag libraries (mutagen, and serato-tools
on top of it) are GPL-2.0-or-later, so that code belongs in whatstheID.

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
