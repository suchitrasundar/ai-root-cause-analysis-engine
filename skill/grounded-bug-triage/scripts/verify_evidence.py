#!/usr/bin/env python3
"""Verify that every evidence item in a triage JSON file quotes real lines in the repository.

Usage: python verify_evidence.py triage.json --repo /path/to/repo [--no-write]

Exit 0 if all evidence is grounded. Exit 1 if any is not: problems are printed, and
(unless --no-write) the JSON is updated with "confidence": "low" and an "ungrounded" list.
Exit 2 on bad input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def norm(text: str) -> str:
    return " ".join(text.split())


def check(triage: dict, repo: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    evidence = triage.get("evidence") or []
    if not evidence:
        problems.append("no evidence cited")
    repo = repo.resolve()
    for i, e in enumerate(evidence, 1):
        try:
            file, start, end, quote = e["file"], int(e["start_line"]), int(e["end_line"]), str(e.get("quote", ""))
        except (KeyError, TypeError, ValueError):
            problems.append(f"evidence #{i}: needs file, start_line, end_line and quote")
            continue
        label = f"{file}:{start}-{end}"
        path = (repo / file).resolve()
        if repo not in path.parents and path != repo:
            problems.append(f"{label}: path is outside the repository")
            continue
        if not path.is_file():
            problems.append(f"{label}: file not found in repository")
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not (1 <= start <= end <= len(lines)):
            problems.append(f"{label}: line range outside the file ({len(lines)} lines)")
            continue
        if not quote.strip():
            problems.append(f"{label}: empty quote")
        elif norm(quote) not in norm(" ".join(lines[start - 1:end])):
            problems.append(f"{label}: quoted text not found in those lines")
    return problems, len(evidence)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("triage_json", type=Path)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--no-write", action="store_true", help="report only; don't modify the JSON")
    args = ap.parse_args()

    try:
        triage = json.loads(args.triage_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.triage_json}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(triage, dict):
        print("error: triage JSON must be an object", file=sys.stderr)
        return 2

    problems, n = check(triage, args.repo)
    triage["ungrounded"] = problems
    if problems:
        triage["confidence"] = "low"
        print(f"GROUNDING FAILED: {len(problems)} problem(s); confidence capped at low")
        for p in problems:
            print(f"  - {p}")
    else:
        print(f"GROUNDING PASSED: {n} citation(s) verified")
    if not args.no_write:
        args.triage_json.write_text(json.dumps(triage, indent=2) + "\n", encoding="utf-8")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
