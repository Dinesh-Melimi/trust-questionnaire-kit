import argparse
import csv
import json
import sys
from datetime import date

from .core import answer, commitments, load_library, load_questions
from .kb import coverage, gap_drafts, review_queue


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draft security questionnaire answers from an approved library.")
    ap.add_argument("--library", required=True)
    ap.add_argument("--questions", required=True, help="CSV with columns id,question")
    ap.add_argument("--customer", default="customer")
    ap.add_argument("--out", help="Write answered CSV")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--drafts", help="Write draft KB entries for unanswered questions (JSON)")
    ap.add_argument("--owner", default="security-team", help="Owner assigned to draft entries")
    ap.add_argument("--kb-report", action="store_true", help="Show review queue and SOC 2 coverage")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today)
    lib = load_library(a.library)
    rows = answer(load_questions(a.questions), lib, today)
    ready = sum(r["status"] == "Ready" for r in rows)
    print(f"{ready}/{len(rows)} answered from the library; {len(rows) - ready} need a human")
    for r in rows:
        if r["status"] != "Ready":
            print(f"  [{r['id']}] {r['status']} (score {r['confidence']}): {r['question'][:70]}")
    c = commitments(rows, a.customer)
    if c:
        print(f"Commitments made to {a.customer}:")
        for x in c:
            print(f"  - {x['commitment']}")
    if a.out:
        with open(a.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "question", "answer", "evidence", "confidence", "status", "commitment"],
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    if a.drafts:
        d = gap_drafts(rows, a.owner, today)
        with open(a.drafts, "w") as fh:
            json.dump(d, fh, indent=1)
        print(f"{len(d)} draft KB entr{'y' if len(d) == 1 else 'ies'} written to {a.drafts} (owner: {a.owner})")
    if a.kb_report:
        q = review_queue(lib.entries, today)
        print(f"Review queue (next 30 days): {len(q)}")
        for x in q:
            print(f"  {x['id']} {'OVERDUE' if x['overdue'] else 'due'} {x['expires']}")
        print("SOC 2 coverage: " + ", ".join(f"{k}({len(v)})" for k, v in coverage(lib.entries).items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
