from pathlib import Path

import pytest

from rca import loaders
from triage.tools import RepoTools

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "sample_app"
SC = ROOT / "scenarios"


def tools(scenario="02_checkout_keyerror"):
    return RepoTools(APP, loaders.load_changes(SC / scenario / "changes.json"), loaders.load_logs(SC / scenario / "logs.jsonl"))


def test_list_files_skips_caches():
    files = tools().list_files()
    assert "coupons.py" in files and not any("__pycache__" in f for f in files)


def test_read_file_is_numbered_and_bounded():
    out = tools().read_file("inventory.py", 20, 22)
    assert out.splitlines()[0].startswith("20: ")
    assert len(out.splitlines()) == 3


@pytest.mark.parametrize("bad", ["../README.md", "../../etc/passwd", "/etc/passwd"])
def test_paths_cannot_escape_repo(bad):
    with pytest.raises((ValueError, FileNotFoundError)):
        tools().read_file(bad)


def test_search_code_and_changes_and_logs():
    t = tools()
    assert any("normalize_sku" in h for h in t.search_code("normalize_sku"))
    assert t.recent_changes("inventory.py")[0]["id"] == "b71c9d0"
    assert t.recent_changes("coupons.py") == []
    assert len(t.search_logs("KeyError")) == 2
