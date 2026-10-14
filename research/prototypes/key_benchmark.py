"""Score a key detector against human key labels for electronic dance music (GiantSteps).

whatstheID's key ensemble was tuned and judged on 17 tracks against Serato, which is a reference, not
an oracle. The two GiantSteps key datasets are human-labelled Beatport previews (2 min each):

  GiantSteps Key       604 tracks   https://github.com/GiantSteps/giantsteps-key-dataset
  GiantSteps-MTG Key  1486 tracks   https://github.com/GiantSteps/giantsteps-mtg-key-dataset

Clone one, run its `audio_dl.sh` (it fetches the previews and checks their md5), then:

  python key_benchmark.py DATASET_DIR --whatstheid PATH/TO/whatstheid --genres techno,tech-house,minimal

Not a baseline: the MTG set's `beatport_metadata.txt` has a "BP KEY" column, but 1,317 of its 1,349
usable rows say "major" while the human labels are 68 % minor, so the column has lost the mode.

Scores: MIREX weighted score (1 exact, 0.5 fifth either way, 0.3 relative, 0.2 parallel; checked
against mir_eval.key.weighted_score on all 576 key pairs, where mir_eval 0.8.2 credits only the fifth
above and its main branch adds allow_descending_fifths=True for MIREX's rule), exact %, and "mixable" %
(exact + fifth + relative: what Camelot calls same, neighbour and relative). When the detector reports
an uncertainty flag (whatstheID's `key_uncertain`), it also says how many misses the flag caught.

Results are cached one JSON line per track (`--cache`), so a stopped run resumes. CPU only, ~11 s a
track with whatstheID's analyser: run it when you aren't playing.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys

NOTES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Camelot number -> pitch class, for the minor (A) and major (B) wheels
CAMELOT_MINOR = {1: 8, 2: 3, 3: 10, 4: 5, 5: 0, 6: 7, 7: 2, 8: 9, 9: 4, 10: 11, 11: 6, 12: 1}
CAMELOT_MAJOR = {n: (pc + 3) % 12 for n, pc in CAMELOT_MINOR.items()}


def parse_key(s) -> tuple[int, str] | None:
    """'C minor', 'D# major', 'Eb min', 'Am', 'F#m', 'C', '8A', '11B' -> (pitch class, 'major'|'minor').

    Anything ambiguous ('A minor / D major', 'A# major / minor', '-', '') is None: a label the
    annotators couldn't agree on scores nothing either way."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s or "/" in s:
        return None
    m = re.fullmatch(r"(\d{1,2})\s*([ABab])", s)
    if m:
        n = int(m.group(1))
        if not 1 <= n <= 12:
            return None
        return (CAMELOT_MINOR[n], "minor") if m.group(2).upper() == "A" else (CAMELOT_MAJOR[n], "major")
    m = re.fullmatch(r"([A-Ga-g])\s*([#♯b♭]?)\s*(.*)", s)
    if not m:
        return None
    pc = NOTES[m.group(1).upper()] + {"#": 1, "♯": 1, "b": -1, "♭": -1}.get(m.group(2), 0)
    rest = m.group(3).strip().lower()
    if rest in ("", "maj", "major"):
        mode = "major"
    elif rest in ("m", "min", "minor"):
        mode = "minor"
    else:
        return None
    return pc % 12, mode


def relation(ref, est) -> str:
    """exact | fifth | relative | parallel | other | none (est missing)."""
    if est is None:
        return "none"
    (rk, rm), (ek, em) = ref, est
    if rk == ek and rm == em:
        return "exact"
    if rm == em and (ek - rk) % 12 in (5, 7):
        return "fifth"
    if rm == "major" and em == "minor" and (ek - rk) % 12 == 9:
        return "relative"
    if rm == "minor" and em == "major" and (ek - rk) % 12 == 3:
        return "relative"
    if rm != em and rk == ek:
        return "parallel"
    return "other"


WEIGHT = {"exact": 1.0, "fifth": 0.5, "relative": 0.3, "parallel": 0.2, "other": 0.0, "none": 0.0}


def load_giantsteps(root: str) -> list[dict]:
    """Tracks with a usable label. Both datasets keep annotations/key/<id>.LOFI.key and
    annotations/genre/<id>.LOFI.genre; audio lands in audio/<id>.LOFI.mp3. The MTG set also has a
    confidence (2 = sure), in annotations.txt and after the key in each .key file."""
    key_dir = os.path.join(root, "annotations", "key")
    conf = {}
    ann = os.path.join(root, "annotations", "annotations.txt")
    if os.path.exists(ann):
        for line in open(ann, encoding="utf-8").read().splitlines()[1:]:
            cols = line.split("\t")
            if len(cols) >= 3 and cols[2].strip().isdigit():
                conf[cols[0].strip()] = int(cols[2])
    out = []
    for name in sorted(os.listdir(key_dir)):
        if not name.endswith(".key"):
            continue
        stem = name[:-4]
        tid = stem.split(".")[0]
        fields = open(os.path.join(key_dir, name), encoding="utf-8").read().strip().split("\t")
        label = fields[0].strip()  # the MTG set writes "d minor<TAB>2<TAB>": key, then confidence
        if len(fields) > 1 and fields[1].strip().isdigit():
            conf.setdefault(tid, int(fields[1]))
        ref = parse_key(label)
        if ref is None:
            continue
        gpath = os.path.join(root, "annotations", "genre", stem + ".genre")
        genre = open(gpath, encoding="utf-8").read().strip().lower().replace(" ", "-") if os.path.exists(gpath) else ""
        out.append({"id": tid, "label": label, "ref": ref, "genre": genre, "confidence": conf.get(tid),
                    "audio": os.path.join(root, "audio", stem + ".mp3")})
    return out


def whatstheid_detector(repo: str):
    """whatstheID's own analyser (backend/app/analyze.py), imported from your checkout."""
    sys.path.insert(0, os.path.join(repo, "backend"))
    analyze = importlib.import_module("app.analyze")

    def detect(path: str) -> dict:
        r = analyze._analyze_sync(path)
        return {"key": r.get("key_camelot"), "uncertain": r.get("key_uncertain"),
                "confidence": r.get("key_confidence")}
    return detect


def module_detector(spec: str):
    """'module:function'; the function takes an audio path and returns a key string or a dict with 'key'."""
    mod, _, fn = spec.partition(":")
    f = getattr(importlib.import_module(mod), fn)

    def detect(path: str) -> dict:
        r = f(path)
        return r if isinstance(r, dict) else {"key": r}
    return detect


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    rel = [r["relation"] for r in rows]
    count = {k: rel.count(k) for k in WEIGHT}
    out = {"n": n, "weighted": round(100 * sum(WEIGHT[x] for x in rel) / n, 1),
           "exact_pct": round(100 * count["exact"] / n, 1),
           "mixable_pct": round(100 * (count["exact"] + count["fifth"] + count["relative"]) / n, 1),
           "counts": count}
    flagged = [r for r in rows if r.get("uncertain") is not None]
    if flagged:
        miss = [r for r in flagged if r["relation"] not in ("exact", "fifth", "relative")]
        caught = [r for r in miss if r["uncertain"]]
        alarms = [r for r in flagged if r["uncertain"] and r not in miss]
        out["uncertain_flag"] = {"misses": len(miss), "caught": len(caught), "false_alarms": len(alarms),
                                 "flagged": sum(1 for r in flagged if r["uncertain"])}
    return out


def run(tracks, detect, cache_path=None, limit=0, log=print) -> list[dict]:
    done = {}
    if cache_path and os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            try:
                row = json.loads(line)
                done[row["id"]] = row
            except (ValueError, KeyError):
                continue
    rows = []
    for i, t in enumerate(tracks):
        if limit and i >= limit:
            break
        if t["id"] in done:
            row = done[t["id"]]
        else:
            if not os.path.exists(t["audio"]):
                log(f"missing audio, skipped: {t['audio']}")
                continue
            try:
                res = detect(t["audio"])
            except Exception as e:  # one bad file must not end a two-hour run
                log(f"{t['id']}: detector failed: {e}")
                continue
            row = {"id": t["id"], "est": res.get("key"), "uncertain": res.get("uncertain")}
            if cache_path:
                with open(cache_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
        row = {**row, "label": t["label"], "genre": t["genre"],
               "relation": relation(t["ref"], parse_key(row.get("est")))}
        rows.append(row)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dataset")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--whatstheid", help="path to your whatstheID checkout")
    src.add_argument("--detector", help="module:function returning a key for an audio path")
    ap.add_argument("--genres", default="", help="comma list, e.g. techno,tech-house,minimal (default: all)")
    ap.add_argument("--min-confidence", type=int, default=0, help="MTG set: 2 keeps only labels the annotator was sure of")
    ap.add_argument("--cache", default="", help="JSON-lines cache so a stopped run resumes")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    tracks = load_giantsteps(args.dataset)
    if args.genres:
        want = {g.strip().lower() for g in args.genres.split(",") if g.strip()}
        tracks = [t for t in tracks if t["genre"] in want]
    if args.min_confidence:
        tracks = [t for t in tracks if (t["confidence"] or 0) >= args.min_confidence]
    detect = whatstheid_detector(args.whatstheid) if args.whatstheid else module_detector(args.detector)
    rows = run(tracks, detect, args.cache or None, args.limit, log=lambda m: print(m, file=sys.stderr))
    report = {"all": summarise(rows)}
    for g in sorted({r["genre"] for r in rows}):
        report[g] = summarise([r for r in rows if r["genre"] == g])
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        for name, s in report.items():
            if s.get("n"):
                extra = ""
                if "uncertain_flag" in s:
                    u = s["uncertain_flag"]
                    extra = f"  flag caught {u['caught']}/{u['misses']} misses, {u['false_alarms']} false alarms"
                print(f"{name:22s} n={s['n']:4d}  weighted {s['weighted']:5.1f}  exact {s['exact_pct']:5.1f}%  "
                      f"mixable {s['mixable_pct']:5.1f}%{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
