"""Control checks run against an exported snapshot of the company's systems.

Each check returns findings. A finding has a priority:
  P0  real exposure of customer data right now -> fix today, before anything else
  P1  real control gap, no data exposed yet      -> ticket with an owner and a due date
  P2  noise or already-accepted risk             -> clean up the check or keep the exception on file
A control passes only when it has no P0 or P1 findings.
"""
import json
from datetime import date, timedelta

SLA_DAYS = {"critical": 15, "high": 30, "medium": 90, "low": 180}
CUSTOMER_DATA = {"recordings", "transcripts", "backups"}


def finding(priority, msg, **detail):
    return {"priority": priority, "message": msg, **detail}


def mfa_enforced(env, today):
    out = []
    for u in env["okta"]:
        if not u["active"] or u["mfa"]:
            continue
        if u.get("service_account"):
            out.append(finding("P2", f"{u['email']} has no MFA but is a service account; confirm it uses key-based auth only", user=u["email"]))
        elif "aws-prod" in u["apps"] or "call-console" in u["apps"]:
            out.append(finding("P0", f"{u['email']} can reach production without MFA", user=u["email"]))
        else:
            out.append(finding("P1", f"{u['email']} has no MFA", user=u["email"]))
    return out


def leavers_deprovisioned(env, today):
    okta = {u["email"]: u for u in env["okta"]}
    out = []
    for p in env["hr"]:
        if p["status"] != "terminated":
            continue
        acct = okta.get(p["email"])
        days = (today - date.fromisoformat(p["end_date"])).days
        if acct and acct["active"]:
            pri = "P0" if any(a in acct["apps"] for a in ("aws-prod", "call-console")) else "P1"
            out.append(finding(pri, f"{p['email']} left {p['end_date']} ({days} days ago) and is still active in Okta "
                               f"with {', '.join(acct['apps'])}", user=p["email"]))
    return out


def access_review_current(env, today):
    ar = env["access_review"]
    out = []
    done = date.fromisoformat(ar["completed"])
    if (today - done).days > 92:
        out.append(finding("P1", f"last access review {ar['completed']} is older than a quarter"))
    okta = {u["email"]: u for u in env["okta"]}
    for d in ar["decisions"]:
        if d["decision"] != "revoke":
            continue
        acct = okta.get(d["email"], {})
        if d["app"] in acct.get("apps", []):
            out.append(finding("P1", f"review said revoke {d['email']} from {d['app']} but access is still there "
                               "(approval is not proof of removal)", user=d["email"]))
    return out


def recording_access_least_privilege(env, today):
    out = []
    for b in env["aws"]["buckets"]:
        if b["data"] not in ("recordings", "transcripts"):
            continue
        humans = [r for r in b["readers"] if r.startswith("role/")]
        for r in humans:
            out.append(finding("P1", f"{r} (a human role) can read {b['name']}; route access through a logged break-glass path",
                               resource=b["name"]))
    return out


def storage_encrypted(env, today):
    return [finding("P0", f"{b['name']} holds {b['data']} without KMS encryption", resource=b["name"])
            for b in env["aws"]["buckets"] if b["data"] in CUSTOMER_DATA and not b["kms"]]


def no_public_buckets(env, today):
    out = []
    for b in env["aws"]["buckets"]:
        if not b["public"]:
            continue
        if b["data"] in CUSTOMER_DATA:
            out.append(finding("P0", f"{b['name']} is public and contains {b['data']}", resource=b["name"]))
        else:
            out.append(finding("P2", f"{b['name']} is public by design ({b['data']}); keep it on the allow-list", resource=b["name"]))
    return out


def audit_logging_on(env, today):
    return [finding("P0" if t["account"] == "prod" else "P1",
                    f"CloudTrail is off in {t['account']}/{t['region']}", resource=f"{t['account']}/{t['region']}")
            for t in env["aws"]["cloudtrail"] if not t["enabled"]]


def retention_enforced(env, today):
    promised = env["promises"]["retention_days"]
    out = []
    for b in env["aws"]["buckets"]:
        if b["data"] not in CUSTOMER_DATA:
            continue
        days = b["lifecycle_days"]
        if days is None:
            out.append(finding("P0", f"{b['name']} has no deletion rule, so that data is kept forever "
                               f"(we promise {promised} days)", resource=b["name"]))
        elif days > promised:
            out.append(finding("P1", f"{b['name']} keeps {b['data']} for {days} days, longer than the {promised}-day promise",
                               resource=b["name"]))
    for s in env["subprocessors"]:
        if s["deletion_days"] > promised:
            out.append(finding("P1", f"{s['name']} keeps {', '.join(s['data'])} for {s['deletion_days']} days "
                               f"(promise is {promised})", vendor=s["name"]))
    return out


def subprocessor_agreements(env, today):
    out = []
    for s in env["subprocessors"]:
        if not s["dpa"]:
            out.append(finding("P0", f"{s['name']} has no DPA", vendor=s["name"]))
        if not s["baa"] and set(s["data"]) & {"recordings", "transcripts"}:
            out.append(finding("P0", f"{s['name']} receives {', '.join(s['data'])} (may contain PHI) without a BAA",
                               vendor=s["name"]))
    return out


def no_training_on_customer_data(env, today):
    out = [finding("P0", f"{s['name']} may train on customer call data", vendor=s["name"])
           for s in env["subprocessors"] if s["trains_on_data"]]
    out += [finding("P0", f"dataset {d['name']} is built from customer calls without opt-in", dataset=d["name"])
            for d in env["training_datasets"] if d["source"] == "customer_calls" and not d["customer_opt_in"]]
    return out


def branch_protection(env, today):
    return [finding("P1", f"{r['repo']} default branch has no required review", resource=r["repo"])
            for r in env["github"] if not r["default_branch_protected"] or r["required_reviews"] < 1]


def vuln_sla(env, today):
    out = []
    for v in env["vulns"]:
        if v["fixed"]:
            continue
        age = (today - date.fromisoformat(v["opened"])).days
        sla = SLA_DAYS[v["severity"]]
        if age <= sla:
            continue
        exc = v.get("exception")
        if exc and date.fromisoformat(exc["expires"]) >= today:
            out.append(finding("P2", f"{v['id']} past SLA but has an approved exception until {exc['expires']} "
                               f"(owner {exc['owner']})", vuln=v["id"]))
        else:
            pri = "P0" if v["severity"] == "critical" else "P1"
            out.append(finding(pri, f"{v['id']} ({v['severity']}) on {v['asset']} open {age} days, SLA {sla}", vuln=v["id"]))
    return out


CHECKS = {f.__name__: f for f in [mfa_enforced, leavers_deprovisioned, access_review_current,
                                   recording_access_least_privilege, storage_encrypted, no_public_buckets,
                                   audit_logging_on, retention_enforced, subprocessor_agreements,
                                   no_training_on_customer_data, branch_protection, vuln_sla]}


def run(controls, env, today):
    results = []
    for c in controls:
        fs = CHECKS[c["check"]](env, today)
        status = "fail" if any(f["priority"] in ("P0", "P1") for f in fs) else ("review" if fs else "pass")
        results.append({**c, "status": status, "findings": fs})
    return results


def triage(results):
    """Flatten findings into one work queue: exposure first, then gaps, then noise."""
    q = [{**f, "control": r["id"], "owner": r["owner"]} for r in results for f in r["findings"]]
    return sorted(q, key=lambda f: (f["priority"], f["control"]))


def load(path):
    with open(path) as f:
        return json.load(f)
