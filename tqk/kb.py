"""Keep the answer library (the security KB) growing and current.

- gap_drafts: turns questions the library could not answer into draft entries with an owner,
  so each new questionnaire improves the KB instead of being answered once in a spreadsheet.
- review_queue: answers that go stale within N days, so reviews happen before a deal is waiting.
- coverage: which SOC 2 criteria the library has approved answers for.
"""
import re
from collections import defaultdict
from datetime import date, timedelta

SOC2 = re.compile(r"\b(CC\d+(?:\.\d+)?|A\d\.\d|C\d\.\d|PI\d\.\d|P\d\.\d)\b")


def gap_drafts(rows, owner="security-team", today=None):
    today = today or date.today()
    drafts, seen = [], set()
    for r in rows:
        if not r["status"].startswith("NEEDS REVIEW: no approved answer"):
            continue
        key = r["question"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        drafts.append({"id": f"DRAFT-{len(drafts) + 1:03d}", "questions": [r["question"].strip()], "tags": [],
                       "answer": "", "evidence": "", "status": "draft", "owner": owner,
                       "requested": today.isoformat()})
    return drafts


def review_queue(entries, today, within_days=30, max_age_days=365):
    due = []
    for e in entries:
        if "last_reviewed" not in e:
            continue
        expires = date.fromisoformat(e["last_reviewed"]) + timedelta(days=max_age_days)
        if expires <= today + timedelta(days=within_days):
            due.append({"id": e["id"], "expires": expires.isoformat(), "overdue": expires < today})
    return sorted(due, key=lambda d: d["expires"])


def coverage(entries):
    by = defaultdict(list)
    for e in entries:
        for crit in SOC2.findall(e.get("evidence", "")):
            by[crit.split(".")[0]].append(e["id"])
    return {k: sorted(set(v)) for k, v in sorted(by.items())}
