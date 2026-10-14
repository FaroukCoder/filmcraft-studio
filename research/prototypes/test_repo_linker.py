"""Offline checks for repo_linker.py: a fake resolver stands in for GitHub search, with the
failure modes that produce Reel Brain's false matches.

    python test_repo_linker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_linker import Candidate, explicit_mentions, link  # noqa: E402

KARAKEEP = Candidate("karakeep-app/karakeep", description="A self-hostable bookmark-everything app with AI-based tagging and full text search",
                     topics=["bookmarks", "self-hosted", "ollama"], stars=20000)
DB = {
    "karakeep-app/karakeep": KARAKEEP,
    "someone/karakeep": Candidate("someone/karakeep", description="A self-hostable bookmark-everything app with AI-based tagging", stars=3, fork=True),
    "langchain-ai/langchain": Candidate("langchain-ai/langchain", description="Build context-aware reasoning applications with LLMs", topics=["llm", "agents"], stars=100000),
    "lang/chain": Candidate("lang/chain", description="blockchain tools", stars=2),
    "gamma-ray/gamma": Candidate("gamma-ray/gamma", description="Gamma-ray spectroscopy analysis toolkit", stars=40),
    "x/gamma-correction": Candidate("x/gamma-correction", description="image gamma correction", stars=5),
    "rez/rez-band": Candidate("rez/rez-band", description="fan site", stars=1),
    "acme/tracker": Candidate("acme/tracker", description="time tracker for teams", stars=900),
    "beta/tracker": Candidate("beta/tracker", description="habit tracker for teams", stars=850),
}
SEARCH = {
    "karakeep": ["someone/karakeep", "karakeep-app/karakeep"],
    "langchain": ["lang/chain", "langchain-ai/langchain"],
    "gamma": ["gamma-ray/gamma", "x/gamma-correction"],
    "rez": ["rez/rez-band"],
    "tracker": ["acme/tracker", "beta/tracker"],
}


class Fake:
    def __init__(self):
        self.searched = []

    def get(self, kind, ident):
        return DB.get(ident) if kind == "github" else None

    def search(self, tool):
        self.searched.append(tool)
        key = "".join(ch for ch in tool.lower() if ch.isalnum())
        return [DB[i] for i in SEARCH.get(key, [])]


def main() -> int:
    problems = []

    def expect(name, got, want):
        if got != want:
            problems.append(f"{name}: got {got!r}, want {want!r}")

    # regex: real links found (trailing punctuation stripped), slashes in prose ignored
    found = explicit_mentions("check github.com/karakeep-app/karakeep. it's open 24/7 and/or free, 1/2 the price; "
                              "model at huggingface.co/google/embeddinggemma-300m, pip install laya, star it: bitbonsai/mcpvault ⭐")
    expect("explicit mentions", found, [("github", "karakeep-app/karakeep"), ("hf-model", "google/embeddinggemma-300m"),
                                        ("github", "bitbonsai/mcpvault"), ("pypi", "laya")])
    expect("no cue, no repo", explicit_mentions("mix it 50/50 with 3/4 of the crowd"), [])

    f = Fake()
    r = link("Karakeep", "bookmark manager", "repo: github.com/karakeep-app/karakeep", f)
    expect("explicit link wins", (r["status"], r["best"]), ("explicit", "karakeep-app/karakeep"))
    expect("explicit link needs no search", f.searched, [])

    r = link("Karakeep", "self-hosted bookmark manager that tags with AI", "github.com/karakeep-app/karakep", Fake())
    expect("OCR typo falls back to search", (r["status"], r["best"]), ("matched", "karakeep-app/karakeep"))

    r = link("Karakeep", "self-hosted bookmarks with AI tagging", "", Fake())
    expect("fork loses to the original", r["best"], "karakeep-app/karakeep")

    r = link("lang chain", "build LLM agents and reasoning apps", "", Fake())
    expect("Whisper-split name still matches", (r["status"], r["best"]), ("matched", "langchain-ai/langchain"))

    r = link("Gamma", "AI that makes slide decks and presentations", "", Fake())
    expect("closed SaaS -> no repo", r["status"], "no_repo")

    r = link("Rez", "techno record label", "", Fake())
    expect("substring is not a match", r["status"], "no_repo")

    r = link("Tracker", "tracker for teams", "", Fake())
    expect("two close candidates -> ambiguous", r["status"], "ambiguous")

    r = link("", "anything", "", Fake())
    expect("empty tool name is a refusal", r["status"], "no_repo")

    print("FAIL\n  " + "\n  ".join(problems) if problems else "PASS")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
