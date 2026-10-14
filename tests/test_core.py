from datetime import date

from tqk.core import answer, commitments, load_library, load_questions

LIB = load_library("samples/library.json")
ROWS = {r["id"]: r for r in answer(load_questions("samples/questionnaire.csv"), LIB, date(2026, 10, 14))}


def test_reworded_questions_match():
    assert ROWS["1"]["answer_id"] == "AC-01"
    assert ROWS["2"]["answer_id"] == "EN-01"
    assert ROWS["5"]["answer_id"] == "CP-01"
    assert ROWS["6"]["answer_id"] == "AI-01"


def test_unknown_question_goes_to_human():
    assert ROWS["7"]["status"].startswith("NEEDS REVIEW: no approved")


def test_stale_answer_flagged():
    assert "last reviewed 2025-03-10" in ROWS["3"]["status"]


def test_commitments_tracked():
    c = commitments(list(ROWS.values()), "Acme CPA")
    assert any("72 hours" in x["commitment"] for x in c)
    assert any("train AI" in x["commitment"] for x in c)
