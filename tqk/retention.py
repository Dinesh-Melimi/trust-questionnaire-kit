"""Answer "Is all our data deleted within N days?" from what systems actually do, not from the policy.

Policy and reality drift: backups roll off later than primary data, a temp export bucket has no
lifecycle rule, a vendor keeps transcripts for 90 days. This builds the per-data-type answer
a customer should get, and says plainly where the honest answer is "not yet".
"""


def retention_facts(env):
    facts = []
    for b in env["aws"]["buckets"]:
        if b["data"] in ("recordings", "transcripts", "backups"):
            facts.append({"where": b["name"], "data": b["data"], "days": b["lifecycle_days"], "type": "our storage"})
    for s in env["subprocessors"]:
        for d in s["data"]:
            facts.append({"where": s["name"], "data": d, "days": s["deletion_days"], "type": "sub-processor"})
    return facts


def answer_retention(env, asked_days):
    facts = retention_facts(env)
    gaps = [f for f in facts if f["days"] is None or f["days"] > asked_days]
    lines = []
    for f in facts:
        days = "no deletion rule" if f["days"] is None else ("not stored" if f["days"] == 0 else f"{f['days']} days")
        lines.append(f"{f['data']} in {f['where']} ({f['type']}): {days}")
    if not gaps:
        verdict = f"Yes. All call data, including backups and sub-processor copies, is deleted within {asked_days} days."
    else:
        verdict = (f"Not fully today. Primary recordings and transcripts follow a {asked_days}-day rule, but "
                   f"{len(gaps)} location(s) keep data longer. Do not answer 'Yes' until these are fixed or the "
                   "answer is approved by Legal with the real timeline.")
    return {"verdict": verdict, "breakdown": lines, "gaps": gaps}
