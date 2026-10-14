"""Match questionnaire questions to an approved answer library.

No external services: matching is TF-IDF cosine similarity in pure Python, so customer
questionnaires and internal evidence never leave the machine.
"""
import csv
import json
import math
import re
from collections import Counter
from datetime import date, timedelta

STOP = set(["a", "an", "the", "of", "to", "and", "or", "for", "in", "on", "is", "are", "be", "do", "does", "your", "you", "we", "our", "with", "by", "any", "how", "what", "which", "please", "describe", "provide", "have", "has", "it", "that", "this", "as", "at", "from", "all", "if", "there"])
SYN = {"mfa": "multifactor", "2fa": "multifactor", "multi": "multifactor", "factor": "multifactor",
       "encrypted": "encryption", "encrypt": "encryption", "pentest": "penetration", "pen": "penetration",
       "soc2": "soc", "vulnerabilities": "vulnerability", "logs": "logging", "log": "logging",
       "backups": "backup", "incidents": "incident", "breach": "incident", "breaches": "incident",
       "notify": "notification", "notifying": "notification", "notified": "notification", "employees": "personnel", "staff": "personnel"}


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        w = SYN.get(w, w)
        if w not in STOP and len(w) > 1:
            out.append(w)
    return out


class Library:
    def __init__(self, entries):
        self.entries = entries
        docs = [Counter(tokens(" ".join(e["questions"]) + " " + " ".join(e.get("tags", [])))) for e in entries]
        df = Counter(t for d in docs for t in d)
        n = len(docs)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, counts):
        v = {t: c * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def match(self, question):
        q = self._vec(Counter(tokens(question)))
        scored = [(sum(q.get(t, 0) * w for t, w in v.items()), e) for v, e in zip(self.vecs, self.entries)]
        return max(scored, key=lambda s: s[0]) if scored else (0.0, None)


def stale(entry, today, max_age_days=365):
    reviewed = date.fromisoformat(entry["last_reviewed"])
    return (today - reviewed) > timedelta(days=max_age_days)


def answer(questions, library, today, threshold=0.35):
    rows = []
    for q in questions:
        score, e = library.match(q["question"])
        if e is None or score < threshold:
            rows.append({**q, "answer": "", "evidence": "", "confidence": round(score, 2),
                         "status": "NEEDS REVIEW: no approved answer", "commitment": ""})
            continue
        status = "Ready"
        if stale(e, today):
            status = f"NEEDS REVIEW: answer last reviewed {e['last_reviewed']}"
        elif score < 0.55:
            status = "Check match"
        rows.append({**q, "answer": e["answer"], "evidence": e.get("evidence", ""),
                     "confidence": round(score, 2), "status": status, "commitment": e.get("commitment", ""),
                     "answer_id": e["id"]})
    return rows


def commitments(rows, customer):
    """Promises made in this questionnaire that must stay true (feeds the post-sale follow-up list)."""
    return [{"customer": customer, "answer_id": r["answer_id"], "commitment": r["commitment"]}
            for r in rows if r.get("commitment")]


def load_library(path):
    with open(path) as f:
        return Library(json.load(f))


def load_questions(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
