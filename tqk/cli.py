import argparse
import csv
import json
import sys
from datetime import date

from .core import answer, commitments, load_library, load_questions
from .kb import coverage, gap_drafts, review_queue


def audit(argv):
    import os
    from . import access_review, checks, evidence, report, retention
    ap = argparse.ArgumentParser(prog="tqk audit", description="Run control checks, triage findings, write evidence and a report.")
    ap.add_argument("--controls", default="samples/controls.json")
    ap.add_argument("--env", default="samples/env.json", help="Exported snapshot of Okta, AWS, GitHub, HR, vendors")
    ap.add_argument("--library", default="samples/library.json")
    ap.add_argument("--questions", default="samples/questionnaire.csv")
    ap.add_argument("--retention-days", type=int, default=30, help="Retention a customer is asking about")
    ap.add_argument("--company", default="Acme Voice (sample)")
    ap.add_argument("--out", default="build")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    env = checks.load(a.env)
    today = date.fromisoformat(a.today or env.get("snapshot_date") or date.today().isoformat())
    results = checks.run(checks.load(a.controls), env, today)
    queue = checks.triage(results)
    status = {r["id"]: r["status"] for r in results}
    qrows = answer(load_questions(a.questions), load_library(a.library), today, control_status=status)
    campaign, flags = access_review.build_campaign(env)
    removals = access_review.verify_removals(env)
    ret = {**retention.answer_retention(env, a.retention_days), "asked": a.retention_days}
    os.makedirs(a.out, exist_ok=True)
    evidence.write_pack(results, a.out, today.isoformat())
    html = report.render(results, queue, evidence.framework_view(results), campaign, flags, removals, ret, qrows,
                         today.isoformat(), a.company)
    with open(os.path.join(a.out, "index.html"), "w") as f:
        f.write(html)
    fails = sum(r["status"] == "fail" for r in results)
    print(f"{len(results) - fails}/{len(results)} controls passing; {len(queue)} findings")
    for f in queue:
        print(f"  {f['priority']} {f['control']:5} {f['message']}")
    held = [r for r in qrows if r["status"].startswith("HOLD")]
    print(f"Questionnaire: {sum(r['status'] == 'Ready' for r in qrows)}/{len(qrows)} ready, {len(held)} held because a linked control is failing")
    print(f"Retention ({a.retention_days} days): {ret['verdict']}")
    print(f"Report: {os.path.join(a.out, 'index.html')}  Evidence: {os.path.join(a.out, 'evidence')}")
    return 1 if any(f["priority"] == "P0" for f in queue) else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "audit":
        return audit(argv[1:])
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
