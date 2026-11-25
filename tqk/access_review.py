"""Quarterly access review: short per-manager lists, then proof that removals happened.

The slow part of most reviews is one giant spreadsheet and chasing replies. Here each manager
gets only their own people, leavers and orphan accounts are flagged automatically, and a
revoke decision is only "done" once the source system shows the access is gone.
"""
from collections import defaultdict


def build_campaign(env):
    hr = {p["email"]: p for p in env["hr"]}
    lists = defaultdict(list)
    flags = []
    for acct in env["okta"]:
        if not acct["active"]:
            continue
        person = hr.get(acct["email"])
        if acct.get("service_account"):
            flags.append({"email": acct["email"], "issue": "service account: needs a named owner"})
            continue
        if person is None:
            flags.append({"email": acct["email"], "issue": "no HR record (orphan account)"})
            continue
        if person["status"] == "terminated":
            flags.append({"email": acct["email"], "issue": f"left {person['end_date']}, remove now (do not wait for review)"})
            continue
        for app in acct["apps"]:
            lists[person["manager"]].append({"email": acct["email"], "app": app})
    return dict(lists), flags


def verify_removals(env):
    """Each revoke decision -> 'removed' or 'still has access', checked against Okta right now."""
    okta = {u["email"]: u for u in env["okta"]}
    out = []
    for d in env["access_review"]["decisions"]:
        if d["decision"] != "revoke":
            continue
        still = d["app"] in okta.get(d["email"], {}).get("apps", [])
        out.append({**d, "verified": "still has access" if still else "removed"})
    return out
