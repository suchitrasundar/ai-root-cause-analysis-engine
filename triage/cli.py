from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from rca import loaders

from .baseline import triage_baseline
from .tools import RepoTools


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="triage", description="Triage a bug report against a codebase")
    p.add_argument("--bug", required=True, help="Bug report text file")
    p.add_argument("--repo", required=True, help="Code directory to investigate")
    p.add_argument("--changes", help="JSON list of recent changes")
    p.add_argument("--logs", help="JSON-lines application logs")
    p.add_argument("--agent", action="store_true", help="Use the Claude agent (needs ANTHROPIC_API_KEY); default is the offline baseline")
    p.add_argument("--model", default=os.environ.get("TRIAGE_MODEL", "claude-sonnet-5-5"))
    p.add_argument("--json", action="store_true", help="Print JSON instead of markdown")
    a = p.parse_args(argv)

    tools = RepoTools(a.repo, loaders.load_changes(a.changes) if a.changes else [], loaders.load_logs(a.logs) if a.logs else [])
    bug = Path(a.bug).read_text()
    if a.agent:
        import anthropic  # optional dependency
        from .agent import run_triage_agent
        triage = run_triage_agent(bug, tools, anthropic.Anthropic(), a.model)
    else:
        triage = triage_baseline(bug, tools)
    print(json.dumps(asdict(triage), indent=2) if a.json else triage.to_markdown())


if __name__ == "__main__":
    main()
