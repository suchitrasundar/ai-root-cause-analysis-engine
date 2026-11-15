from __future__ import annotations

import argparse
import os

from . import loaders
from .engine import investigate
from .models import Incident


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="rca")
    p.add_argument("--logs", required=True, help="JSON-lines log file")
    p.add_argument("--metrics", required=True, help="CSV with ts,metric,value")
    p.add_argument("--changes", required=True, help="JSON list of recent changes")
    p.add_argument("--start", required=True, help="Incident start, ISO 8601")
    p.add_argument("--end", required=True, help="Incident end, ISO 8601")
    p.add_argument("--agent", action="store_true", help="Also run the Claude tool-use agent (needs ANTHROPIC_API_KEY)")
    p.add_argument("--model", default=os.environ.get("RCA_MODEL", "claude-sonnet-5-5"))
    a = p.parse_args(argv)

    incident = Incident(loaders.parse_ts(a.start), loaders.parse_ts(a.end), loaders.load_logs(a.logs),
                        loaders.load_metrics(a.metrics), loaders.load_changes(a.changes))
    print(investigate(incident).to_markdown())
    if a.agent:
        import anthropic  # optional dependency
        from .agent import run_agent
        print("\n# Agent analysis\n" + run_agent(incident, anthropic.Anthropic(), a.model))


if __name__ == "__main__":
    main()
