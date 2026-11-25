"""Write audit evidence the way auditors sample it: one folder per control, timestamped, hashed.

Every run adds a dated snapshot instead of overwriting, so a SOC 2 Type II period has evidence
for the whole window. manifest.json lists a SHA-256 for each file so nobody can quietly edit it later.
"""
import hashlib
import json
import os


def write_pack(results, out_dir, run_date):
    manifest = []
    for r in results:
        folder = os.path.join(out_dir, "evidence", r["id"])
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{run_date}.json")
        body = {"control": r["id"], "title": r["title"], "frameworks": r["frameworks"], "owner": r["owner"],
                "collected": run_date, "status": r["status"], "findings": r["findings"]}
        data = json.dumps(body, indent=1, sort_keys=True).encode()
        with open(path, "wb") as f:
            f.write(data)
        manifest.append({"file": os.path.relpath(path, out_dir), "sha256": hashlib.sha256(data).hexdigest()})
    with open(os.path.join(out_dir, "evidence", "manifest.json"), "w") as f:
        json.dump({"run": run_date, "files": manifest}, f, indent=1)
    return manifest


def framework_view(results):
    """One control set, many frameworks: status per SOC 2 / ISO / HIPAA requirement."""
    view = {}
    for r in results:
        for fw, ref in r["frameworks"].items():
            view.setdefault(fw, []).append({"ref": ref, "control": r["id"], "status": r["status"]})
    return view
