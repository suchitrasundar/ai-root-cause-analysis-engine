"""Offline baseline triager (no LLM): ranks files by traceback frames, keyword overlap and recent changes.

It exists to (1) work without an API key, (2) give the agent something to beat in the evaluation.
It can point at the likely file but cannot explain *why* the bug happens.
"""
from __future__ import annotations

import re
from pathlib import Path

from .grounding import apply_grounding
from .models import Evidence, Triage
from .tools import RepoTools

FRAME = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')
WORD = re.compile(r"[a-z][a-z0-9]{3,}")
STOP = {"that", "with", "from", "this", "have", "when", "only", "should", "still", "since", "every", "each", "never",
        "some", "than", "then", "into", "after", "about", "also", "instead", "shows", "show", "made", "make", "bug",
        "example", "nothing", "changed", "side", "according", "yesterday", "deploy", "release", "last", "reproduced",
        "twice", "other", "report", "customer", "support", "were", "they", "their", "there", "which", "would", "could",
        "traceback", "recent", "most", "call", "line", "file"}


def stem(word: str) -> str:
    return word[:-1] if word.endswith("s") and len(word) > 4 else word


def keywords(text: str) -> list[str]:
    seen = []
    for w in WORD.findall(text.lower()):
        s = stem(w)
        if w not in STOP and s not in STOP and s not in seen:
            seen.append(s)
    return seen


def enclosing_function(lines: list[str], lineno: int) -> str | None:
    for i in range(min(lineno, len(lines)) - 1, -1, -1):
        m = re.match(r"\s*def (\w+)", lines[i])
        if m:
            return m.group(1)
    return None


def triage_baseline(bug_text: str, tools: RepoTools) -> Triage:
    kws = keywords(bug_text)
    files = tools.list_files()
    by_name = {Path(f).name: f for f in files}
    frames = [(by_name.get(Path(p).name), int(n), fn) for p, n, fn in FRAME.findall(bug_text)]
    frames = [f for f in frames if f[0]]

    scores = {f: 0.0 for f in files}
    reasons: dict[str, list[str]] = {f: [] for f in files}
    for i, (f, _, fn) in enumerate(frames):
        scores[f] += 5 if i == len(frames) - 1 else 2
        reasons[f].append(f"appears in the stack trace (function `{fn}`)")
    for f in files:
        content = "\n".join(tools.file_lines(f)).lower()
        stem_name = Path(f).stem.lower()
        hits = [k for k in kws if k in content]
        name_hits = [k for k in kws if k in stem_name or stem_name in k]
        scores[f] += 2 * len(name_hits) + 0.5 * min(len(hits), 6)
        if name_hits:
            reasons[f].append(f"file name matches report terms: {', '.join(name_hits)}")
        if hits:
            reasons[f].append(f"contains report terms: {', '.join(hits[:5])}")
        if scores[f] == 0:
            continue  # recent changes only boost files the report already points at; they never create a candidate
        for c in tools.recent_changes(f):
            shared = [k for k in kws if k in c["title"].lower()]
            scores[f] += 1.0 if shared else 0.5
            reasons[f].append(f"recent change {c['id']} \"{c['title']}\" touched it")

    ranked = sorted(files, key=lambda f: -scores[f])
    top = ranked[0] if ranked else None
    if not top or scores[top] == 0:
        return Triage("No candidate file found.", "Unknown", confidence="low", source="baseline",
                      missing_info=["Bug report has no terms or stack trace matching the code."])
    runner_up = scores[ranked[1]] if len(ranked) > 1 else 0.0
    lines = tools.file_lines(top)
    frame_line = next((ln for f, ln, _ in reversed(frames) if f == top), None)
    if frame_line:
        picks = [frame_line]
    else:
        picks = [n for n, line in enumerate(lines, 1) if any(k in line.lower() for k in kws) and line.strip()][:3]
    evidence = [Evidence(top, n, n, lines[n - 1].strip()) for n in picks if 1 <= n <= len(lines)]
    fn = enclosing_function(lines, picks[0]) if picks else None
    where = f"`{top}`" + (f", function `{fn}`" if fn else "")
    triage = Triage(
        summary=bug_text.strip().splitlines()[0].lstrip("# ").strip(),
        root_cause=f"Most likely located in {where}. The baseline cannot explain why the behaviour is wrong.",
        evidence=evidence,
        causal_chain=reasons[top],
        confidence="medium" if scores[top] >= 1.5 * max(runner_up, 0.1) else "low",
        verification_steps=[f"Read {where} and compare it with the expected behaviour in the report.",
                            "Write a failing test from the report's example, then fix and re-run."],
        component=Path(top).stem,
        missing_info=["Run agent mode for a causal explanation."],
        source="baseline",
    )
    return apply_grounding(triage, tools)
