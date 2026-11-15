"""Read-only tools the agent uses to investigate. All file access is confined to the repo root."""
from __future__ import annotations

import re
from pathlib import Path

from rca.models import Change, LogEvent

TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".json", ".txt", ".html", ".cfg", ".toml"}


class RepoTools:
    def __init__(self, root: str | Path, changes: list[Change] | None = None, logs: list[LogEvent] | None = None):
        self.root = Path(root).resolve()
        self.changes = changes or []
        self.logs = logs or []

    def resolve(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(f"path escapes the repository: {path}")
        if not p.is_file():
            raise FileNotFoundError(path)
        return p

    def list_files(self) -> list[str]:
        files = []
        for p in sorted(self.root.rglob("*")):
            rel = p.relative_to(self.root)
            if p.is_file() and p.suffix in TEXT_SUFFIXES and not any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
                files.append(rel.as_posix())
        return files

    def file_lines(self, path: str) -> list[str]:
        return self.resolve(path).read_text().splitlines()

    def read_file(self, path: str, start: int = 1, end: int | None = None, max_lines: int = 200) -> str:
        lines = self.file_lines(path)
        start = max(start, 1)
        end = min(end or len(lines), len(lines), start + max_lines - 1)
        return "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))

    def search_code(self, pattern: str, max_hits: int = 30) -> list[str]:
        rx = re.compile(pattern, re.IGNORECASE)
        hits = []
        for f in self.list_files():
            for n, line in enumerate(self.file_lines(f), 1):
                if rx.search(line):
                    hits.append(f"{f}:{n}: {line.strip()}")
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def recent_changes(self, path: str | None = None) -> list[dict]:
        base = Path(path).name if path else None
        return [{"id": c.id, "ts": c.ts.isoformat(), "author": c.author, "title": c.title, "files": list(c.files)}
                for c in reversed(self.changes) if base is None or any(Path(f).name == base for f in c.files)]

    def search_logs(self, pattern: str, limit: int = 20) -> list[dict]:
        rx = re.compile(pattern, re.IGNORECASE)
        return [{"ts": e.ts.isoformat(), "level": e.level, "service": e.service, "message": e.message}
                for e in reversed(self.logs) if rx.search(e.message)][:limit]
