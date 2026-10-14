"""Is Laya earning its place in front of every message? (Top 10 #3)

Reads your logged routing decisions with a correct label added by hand (or by a
stronger teacher model), one JSON object per line:

    {"text": "...", "laya": "coding", "confidence": 0.91, "label": "coding"}

and reports: accuracy overall and per route, what gets confused with what, how well
the confidence is calibrated (ECE), the accuracy you would get by only trusting
Laya above a confidence threshold (and how many messages that leaves to the LLM),
and a cheap baseline trained on the same labels (TF-IDF + logistic regression by
default; `--embed google/embeddinggemma-300m` uses sentence-transformers if installed).

    python laya_eval.py routes.jsonl
    python laya_eval.py routes.jsonl --embed google/embeddinggemma-300m
    python laya_eval.py routes.jsonl --export-csv routes.csv
    python laya_eval.py routes.jsonl --export-rows train_rows.jsonl --questions router_question.json --qid route

Then fine-tune on your own GPU or CPU with Laya's `laya-train` (laya >= 0.4):

    laya-train --data routes.csv --text-column text --label-column label --base multilingual --out laya-routes --dry-run

`--export-csv` writes `text,label` rows (the label becomes a choice question over its distinct
values). `--export-rows` writes Laya's JSONL case format, one line per message:
{"state": <message>, "questions": <your question set>, "expected": {<qid>: <label>}};
use it when your question has written criteria per option. (Laya's `gold` field is for teacher
probabilities, not plain labels.) The same rows, with a `language` tag added, are what Laya's own
evaluation harness reads, so before and after a fine-tune:

    laya-evals run train_rows.jsonl --model ./laya-routes --slice language --max-ece 0.1 --json after.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict

import numpy as np


def load(path: str) -> list[dict]:
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            r = json.loads(line)
            if r.get("label") is not None:
                rows.append(r)
    return rows


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(total)


def baseline_accuracy(texts: list[str], labels: list[str], embed: str | None, folds: int = 5) -> float | None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    counts = Counter(labels)
    if len(counts) < 2 or min(counts.values()) < folds:
        return None
    if embed:
        from sentence_transformers import SentenceTransformer  # type: ignore

        X = SentenceTransformer(embed).encode(texts, normalize_embeddings=True)
        clf = LogisticRegression(max_iter=2000)
    else:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import make_pipeline

        X = texts
        # char n-grams cope with Arabic, English and code-switching without a tokenizer
        clf = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2),
                            LogisticRegression(max_iter=2000))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
    return float(np.mean(cross_val_score(clf, X, labels, cv=cv)))


def report(rows: list[dict], embed: str | None = None) -> dict:
    y = [r["label"] for r in rows]
    p = [r["laya"] for r in rows]
    conf = np.array([float(r.get("confidence", np.nan)) for r in rows])
    correct = np.array([a == b for a, b in zip(y, p)], dtype=float)
    per_route = {}
    for lab in sorted(set(y)):
        m = np.array([v == lab for v in y])
        per_route[lab] = {"n": int(m.sum()), "accuracy": round(float(correct[m].mean()), 3)}
    confusions = Counter((a, b) for a, b in zip(y, p) if a != b).most_common(8)
    out = {
        "n": len(rows),
        "accuracy": round(float(correct.mean()), 3),
        "majority_class_baseline": round(Counter(y).most_common(1)[0][1] / len(y), 3),
        "per_route": per_route,
        "top_confusions": [f"{a} -> {b}: {c}" for (a, b), c in confusions],
    }
    if not np.isnan(conf).all():
        ok = ~np.isnan(conf)
        out["ece"] = round(ece(conf[ok], correct[ok]), 3)
        out["mean_confidence"] = round(float(conf[ok].mean()), 3)
        gate = []
        for t in (0.5, 0.6, 0.7, 0.8, 0.9):
            m = ok & (conf >= t)
            if m.any():
                gate.append({"threshold": t, "kept_pct": round(100 * m.mean(), 1),
                             "accuracy_when_kept": round(float(correct[m].mean()), 3)})
        out["confidence_gate"] = gate
    base = baseline_accuracy([r["text"] for r in rows], y, embed)
    if base is not None:
        out["baseline_cv_accuracy"] = round(base, 3)
    return out


def language(text: str) -> str:
    """'ar', 'en' or 'mixed' by script share, so laya-evals can report Arabic and English
    separately (`--slice language`): a router can be fine on one and poor on the other."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    ar = sum("\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f" for c in letters) / len(letters)
    return "ar" if ar > 0.7 else "en" if ar < 0.1 else "mixed"


def export_rows(rows: list[dict], questions: dict, qid: str, out_path: str) -> int:
    if qid not in questions:
        raise SystemExit(f"question id {qid!r} not in the questions file")
    allowed = set((questions[qid].get("criteria") or {}).keys())
    n = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for r in rows:
            if allowed and r["label"] not in allowed:
                continue  # a label your question doesn't offer can't be learned
            fh.write(json.dumps({"state": r["text"], "questions": questions, "expected": {qid: r["label"]},
                                 "language": language(r["text"])}, ensure_ascii=False) + "\n")
            n += 1
    return n


def export_csv(rows: list[dict], out_path: str) -> int:
    import csv

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["text", "label"])
        for r in rows:
            w.writerow([r["text"], r["label"]])
    return len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("jsonl")
    ap.add_argument("--embed", help="sentence-transformers model id for the baseline")
    ap.add_argument("--export-csv", help="write text,label rows for laya-train here")
    ap.add_argument("--export-rows", help="write Laya JSONL cases (state, questions, expected) here")
    ap.add_argument("--questions", help="JSON file with your Laya question set (as passed to predict)")
    ap.add_argument("--qid", default="route", help="which question the labels answer")
    args = ap.parse_args(argv)
    rows = load(args.jsonl)
    if not rows:
        print("no labelled rows", file=sys.stderr)
        return 1
    if args.export_csv:
        print(f"wrote {export_csv(rows, args.export_csv)} rows to {args.export_csv}")
    if args.export_rows:
        questions = json.load(open(args.questions, encoding="utf-8"))
        n = export_rows(rows, questions, args.qid, args.export_rows)
        print(f"wrote {n} training rows to {args.export_rows}")
    print(json.dumps(report(rows, args.embed), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
