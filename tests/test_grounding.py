from rca import loaders
from triage.grounding import apply_grounding, check_evidence
from triage.models import Evidence, Triage
from triage.tools import RepoTools
from tests.test_tools import APP


def make(evidence, conf="high"):
    return Triage("s", "r", evidence, confidence=conf)


def test_real_evidence_passes():
    t = RepoTools(APP)
    tri = make([Evidence("catalog.py", 7, 7, "end = start + per_page - 1")])
    assert check_evidence(tri, t) == []
    assert apply_grounding(tri, t).confidence == "high"


def test_fabricated_quote_is_flagged_and_confidence_capped():
    t = RepoTools(APP)
    bad =apply_grounding(make([Evidence("catalog.py", 7, 7, "return items[start:end + 1]")]), t)
    assert bad.confidence == "low" and bad.ungrounded


def test_missing_file_bad_range_and_empty_evidence():
    t = RepoTools(APP)
    assert "file not found" in check_evidence(make([Evidence("nope.py", 1, 1, "x")]), t)[0]
    assert "outside the file" in check_evidence(make([Evidence("catalog.py", 1, 999, "x")]), t)[0]
    assert check_evidence(make([]), t) == ["no evidence cited"]
