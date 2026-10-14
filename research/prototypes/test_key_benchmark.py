"""Tests for key_benchmark.py: key parsing, MIREX relations, both GiantSteps layouts, caching, and
(when WHATSTHEID_REPO points at a whatstheID checkout) its real analyser on synthetic tracks in known keys."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import key_benchmark as kb  # noqa: E402

CALLS = []


def fake_detect(path: str) -> dict:
    CALLS.append(os.path.basename(path))
    name = os.path.basename(path)
    if name.startswith("3."):
        raise RuntimeError("corrupt mp3")
    return {"1.LOFI.mp3": {"key": "8A", "uncertain": False},     # A minor: exact
            "2.LOFI.mp3": {"key": "C major", "uncertain": True},  # ref D minor: other (a miss, flagged)
            "4.LOFI.mp3": {"key": "9B", "uncertain": True}}[name]  # 9B = G major, ref C major: fifth (flag false alarm)


def synth(path: str, tonic: int, minor: bool, seconds: float = 40.0, sr: int = 22050) -> None:
    """Four-on-the-floor loop at 128 BPM: kick, a bass on the tonic, and a sustained tonic triad with a
    bar of iv (subdominant) every fourth bar, so the key is in the harmony, not just one note."""
    import numpy as np
    n = int(seconds * sr)
    t = np.arange(n) / sr
    y = np.zeros(n)
    beat = 60.0 / 128
    for b in np.arange(0, seconds, beat):
        i = int(b * sr)
        k = np.arange(min(int(0.25 * sr), n - i)) / sr
        y[i:i + len(k)] += 0.8 * np.sin(2 * np.pi * (50 + 120 * np.exp(-k * 30)) * k) * np.exp(-k * 12)
    third = 3 if minor else 4
    bar = 4 * beat
    for j, start in enumerate(np.arange(0, seconds, bar)):
        root = tonic + (5 if j % 4 == 3 else 0)
        i0, i1 = int(start * sr), min(int((start + bar) * sr), n)
        tt = t[i0:i1] - start
        for st, amp in ((0, 0.25), (third, 0.2), (7, 0.2), (12, 0.12)):
            f = 261.63 * 2 ** ((root + st) / 12)
            y[i0:i1] += amp * np.sin(2 * np.pi * f * tt)
        fb = 65.41 * 2 ** ((root % 12) / 12)
        y[i0:i1] += 0.35 * np.sin(2 * np.pi * fb * tt) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * tt / beat * 2)))
    y /= np.max(np.abs(y)) * 1.05
    wav = path[:-4] + ".wav"
    import soundfile as sf
    sf.write(wav, y.astype("float32"), sr)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-b:a", "192k", path], check=True)
    os.remove(wav)


def main() -> int:
    problems = []
    cases = {"C minor": (0, "minor"), "d minor": (2, "minor"), "Eb major": (3, "major"), "F#m": (6, "minor"),
             "A": (9, "major"), "8A": (9, "minor"), "8B": (0, "major"), "1B": (11, "major"), "12A": (1, "minor"),
             "A minor / D major": None, "A# major / minor": None, "": None, "-": None, "13A": None}
    for s, want in cases.items():
        if kb.parse_key(s) != want:
            problems.append(f"parse_key({s!r}) = {kb.parse_key(s)}, want {want}")
    rel = {((0, "major"), (7, "major")): "fifth", ((0, "major"), (5, "major")): "fifth",
           ((0, "major"), (9, "minor")): "relative", ((9, "minor"), (0, "major")): "relative",
           ((0, "major"), (0, "minor")): "parallel", ((0, "major"), (2, "major")): "other",
           ((0, "major"), None): "none"}
    for (r, e), want in rel.items():
        if kb.relation(r, e) != want:
            problems.append(f"relation({r}, {e}) = {kb.relation(r, e)}, want {want}")

    with tempfile.TemporaryDirectory() as td:
        ds = os.path.join(td, "mtg")
        for sub in ("annotations/key", "annotations/genre", "audio"):
            os.makedirs(os.path.join(ds, sub))
        labels = {"1": ("a minor\t2\t", "techno"), "2": ("d minor\t1\t", "techno"), "3": ("e minor\t2\t", "minimal"),
                  "4": ("c major\t2\t", "tech house"), "5": ("A minor / D major\t0\t", "techno"),
                  "6": ("f minor\t2\t", "techno")}
        for tid, (lab, genre) in labels.items():
            open(os.path.join(ds, "annotations/key", f"{tid}.LOFI.key"), "w").write(lab)
            open(os.path.join(ds, "annotations/genre", f"{tid}.LOFI.genre"), "w").write(genre)
            if tid != "6":  # 6 has a label but no audio: skipped, not a crash
                open(os.path.join(ds, "audio", f"{tid}.LOFI.mp3"), "wb").write(b"x")
        tracks = kb.load_giantsteps(ds)
        if [t["id"] for t in tracks] != ["1", "2", "3", "4", "6"]:
            problems.append(f"ambiguous label should be dropped, the rest kept: {[t['id'] for t in tracks]}")
        if {t["id"]: t["confidence"] for t in tracks}.get("2") != 1 or tracks[3]["genre"] != "tech-house":
            problems.append(f"confidence/genre not read from the MTG layout: {tracks}")
        cache = os.path.join(td, "cache.jsonl")
        logs = []
        rows = kb.run(tracks, fake_detect, cache, log=logs.append)
        s = kb.summarise(rows)
        if s["n"] != 3 or s["counts"]["exact"] != 1 or s["counts"]["fifth"] != 1 or s["counts"]["other"] != 1:
            problems.append(f"scoring: {s}")
        if abs(s["weighted"] - 50.0) > 0.05 or abs(s["mixable_pct"] - 66.7) > 0.05:
            problems.append(f"weighted should be (1 + 0.5 + 0) / 3 = 50.0, mixable 66.7: {s}")
        if s.get("uncertain_flag") != {"misses": 1, "caught": 1, "false_alarms": 1, "flagged": 2}:
            problems.append(f"uncertain flag accounting: {s.get('uncertain_flag')}")
        if not any("corrupt mp3" in m for m in logs) or not any("missing audio" in m for m in logs):
            problems.append(f"a failing detector and missing audio should be logged and skipped: {logs}")
        CALLS.clear()
        again = kb.run(tracks, fake_detect, cache, log=lambda m: None)
        if [c for c in CALLS if not c.startswith("3.")] or len(again) != 3:
            problems.append(f"cached tracks were analysed again: {CALLS}")
        print(f"harness: {s['n']} scored, weighted {s['weighted']}, mixable {s['mixable_pct']}%")

        repo = os.environ.get("WHATSTHEID_REPO")
        if repo and shutil.which("ffmpeg"):
            gs = os.path.join(td, "gs")
            for sub in ("annotations/key", "annotations/genre", "audio"):
                os.makedirs(os.path.join(gs, sub))
            keys = {"10": (9, True, "A minor"), "11": (2, True, "D minor"), "12": (7, False, "G major"),
                    "13": (5, True, "F minor")}
            for tid, (pc, minor, lab) in keys.items():
                open(os.path.join(gs, "annotations/key", f"{tid}.LOFI.key"), "w").write(lab)
                open(os.path.join(gs, "annotations/genre", f"{tid}.LOFI.genre"), "w").write("techno")
                synth(os.path.join(gs, "audio", f"{tid}.LOFI.mp3"), pc, minor)
            out = subprocess.run([sys.executable, os.path.abspath(kb.__file__), gs, "--whatstheid", repo, "--json"],
                                 capture_output=True, text=True)
            try:
                rep = json.loads(out.stdout)["all"]
            except (ValueError, KeyError):
                rep = {}
                problems.append(f"whatstheID run failed: {out.stderr[-800:]}")
            if rep:
                print(f"whatstheID on 4 synthetic tracks: {rep}")
                if rep.get("n") != 4 or rep.get("mixable_pct", 0) < 75:
                    problems.append(f"whatstheID should place at least 3 of 4 plain synthetic keys: {rep}")
            print("PASS" if not problems else "FAIL\n  " + "\n  ".join(problems))
        else:
            print("FAIL\n  " + "\n  ".join(problems) if problems else
                  "PASS (whatstheID end-to-end skipped: set WHATSTHEID_REPO)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
