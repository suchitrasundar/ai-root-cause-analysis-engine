"""Evaluate a triager on the scenarios: did the first cited file match the known root-cause file?"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rca import loaders

from .baseline import triage_baseline
from .tools import RepoTools

ROOT = Path(__file__).resolve().parent.parent


def load_scenario(d: Path) -> tuple[str, RepoTools, dict]:
    tools = RepoTools(ROOT / "sample_app", loaders.load_changes(d / "changes.json"), loaders.load_logs(d / "logs.jsonl"))
    return (d / "bug.md").read_text(), tools, json.loads((d / "truth.json").read_text())


def evaluate(triager, scenarios_dir: Path = ROOT / "scenarios") -> list[dict]:
    results = []
    for d in sorted(p for p in scenarios_dir.iterdir() if p.is_dir()):
        bug, tools, truth = load_scenario(d)
        t = triager(bug, tools)
        first = t.evidence[0].file if t.evidence else None
        results.append({"scenario": d.name, "expected": truth["root_cause_file"], "got": first,
                        "hit": first == truth["root_cause_file"], "grounded": not t.ungrounded, "confidence": t.confidence})
    return results


def main() -> None:
    res = evaluate(triage_baseline)
    for r in res:
        print(f"{'PASS' if r['hit'] else 'FAIL'}  {r['scenario']}: expected {r['expected']}, got {r['got']} "
              f"(grounded={r['grounded']}, confidence={r['confidence']})")
    print(f"baseline root-cause file accuracy: {sum(r['hit'] for r in res)}/{len(res)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
