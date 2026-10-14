from datetime import date

from tqk.core import answer, load_library, load_questions
from tqk.kb import coverage, gap_drafts, review_queue

TODAY = date(2026, 10, 14)


def _rows():
    return answer(load_questions("samples/questionnaire.csv"), load_library("samples/library.json"), TODAY)


def test_gap_drafts_for_unanswered_only():
    d = gap_drafts(_rows(), "dinesh", TODAY)
    assert d and all(x["status"] == "draft" and x["owner"] == "dinesh" for x in d)
    assert any("SBOM" in x["questions"][0] for x in d)
    assert d[0]["id"] == "DRAFT-001"


def test_gap_drafts_dedupes():
    rows = [{"question": "Do you have an SBOM?", "status": "NEEDS REVIEW: no approved answer"}] * 2
    assert len(gap_drafts(rows, today=TODAY)) == 1


def test_review_queue_overdue_and_upcoming():
    entries = [{"id": "A", "last_reviewed": "2025-03-10"}, {"id": "B", "last_reviewed": "2025-10-30"},
               {"id": "C", "last_reviewed": "2026-08-01"}]
    q = review_queue(entries, TODAY)
    assert [x["id"] for x in q] == ["A", "B"]
    assert q[0]["overdue"] and not q[1]["overdue"]


def test_soc2_coverage():
    c = coverage(load_library("samples/library.json").entries)
    assert "AC-01" in c["CC6"]
