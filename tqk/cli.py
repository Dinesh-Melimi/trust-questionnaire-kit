import argparse
import csv
import sys
from datetime import date

from .core import answer, commitments, load_library, load_questions


def main(argv=None):
    ap = argparse.ArgumentParser(description="Draft security questionnaire answers from an approved library.")
    ap.add_argument("--library", required=True)
    ap.add_argument("--questions", required=True, help="CSV with columns id,question")
    ap.add_argument("--customer", default="customer")
    ap.add_argument("--out", help="Write answered CSV")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args(argv)
    rows = answer(load_questions(a.questions), load_library(a.library), date.fromisoformat(a.today))
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
