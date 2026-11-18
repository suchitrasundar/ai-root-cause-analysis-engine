"""Tests for the skill's standalone grounding checker (skill/grounded-bug-triage/scripts/verify_evidence.py)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "grounded-bug-triage" / "scripts" / "verify_evidence.py"


def run(tmp_path, evidence):
    f = tmp_path / "triage.json"
    f.write_text(json.dumps({"summary": "s", "confidence": "high", "evidence": evidence}))
    proc = subprocess.run([sys.executable, str(SCRIPT), str(f), "--repo", str(ROOT)], capture_output=True, text=True)
    return proc, json.loads(f.read_text())


def test_grounded_evidence_passes(tmp_path):
    proc, out = run(tmp_path, [
        {"file": "sample_app/inventory.py", "start_line": 13, "end_line": 13, "quote": "STOCK[sku.lower()] = qty"},
        {"file": "sample_app/inventory.py", "start_line": 18, "end_line": 18, "quote": "return   sku.strip().upper()"},
    ])
    assert proc.returncode == 0
    assert out["confidence"] == "high" and out["ungrounded"] == []


def test_ungrounded_evidence_caps_confidence(tmp_path):
    proc, out = run(tmp_path, [
        {"file": "sample_app/inventory.py", "start_line": 13, "end_line": 13, "quote": "STOCK[sku.upper()] = qty"},
        {"file": "sample_app/missing.py", "start_line": 1, "end_line": 1, "quote": "x"},
        {"file": "../outside.py", "start_line": 1, "end_line": 1, "quote": "x"},
        {"file": "sample_app/inventory.py", "start_line": 900, "end_line": 901, "quote": "x"},
    ])
    assert proc.returncode == 1
    assert out["confidence"] == "low"
    assert len(out["ungrounded"]) == 4


def test_no_evidence_fails(tmp_path):
    proc, out = run(tmp_path, [])
    assert proc.returncode == 1 and out["confidence"] == "low"
