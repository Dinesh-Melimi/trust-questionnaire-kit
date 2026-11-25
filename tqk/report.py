"""Single-file HTML audit-readiness report (no external assets, safe to attach to a ticket)."""
from html import escape

CSS = """:root{--bg:#f7f7f5;--fg:#1d1d1b;--mute:#6b6b66;--card:#fff;--line:#e3e2dc;--p0:#b42318;--p1:#b54708;--p2:#5d6b82;--ok:#067647}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe6;--mute:#a3a29b;--card:#1f1f1d;--line:#33322e;--p0:#f97066;--p1:#fdb022;--p2:#98a2b3;--ok:#47cd89}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 8px}
.mute{color:var(--mute)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.card b{display:block;font-size:26px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px}th{color:var(--mute);font-weight:600}
.tag{font-weight:700;font-size:12px;padding:2px 7px;border-radius:99px;border:1px solid currentColor;white-space:nowrap}
.P0,.fail{color:var(--p0)}.P1{color:var(--p1)}.P2,.review{color:var(--p2)}.pass{color:var(--ok)}
.wrap{overflow-x:auto}ul{margin:6px 0 0 18px;padding:0}"""


def _tag(t):
    return f'<span class="tag {escape(t)}">{escape(t.upper())}</span>'


def render(results, queue, fw_view, campaign, flags, removals, retention, qrows, run_date, company):
    n = {s: sum(r["status"] == s for r in results) for s in ("pass", "fail", "review")}
    p = {k: sum(f["priority"] == k for f in queue) for k in ("P0", "P1", "P2")}
    h = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>Audit Readiness</title><style>{CSS}</style></head><body><main>",
         f"<h1>Audit readiness: {escape(company)}</h1><div class=mute>Snapshot {escape(run_date)} · "
         f"{len(results)} controls mapped to SOC 2, ISO 27001 and HIPAA</div>",
         "<div class=cards>",
         f"<div class=card><b class=pass>{n['pass']}</b>controls passing</div>",
         f"<div class=card><b class=fail>{n['fail']}</b>controls failing</div>",
         f"<div class=card><b class=P0>{p['P0']}</b>P0 · data exposed now</div>",
         f"<div class=card><b class=P1>{p['P1']}</b>P1 · control gaps</div>",
         f"<div class=card><b class=P2>{p['P2']}</b>P2 · noise / accepted</div></div>",
         "<h2>Work queue (fix in this order)</h2><div class=wrap><table><tr><th>Priority</th><th>Control</th><th>Owner</th><th>Finding</th></tr>"]
    for f in queue:
        h.append(f"<tr><td>{_tag(f['priority'])}</td><td>{escape(f['control'])}</td><td>{escape(f['owner'])}</td><td>{escape(f['message'])}</td></tr>")
    h.append("</table></div><h2>Controls</h2><div class=wrap><table><tr><th>ID</th><th>Control</th><th>Status</th><th>SOC 2</th><th>ISO 27001</th><th>HIPAA</th></tr>")
    for r in results:
        fw = r["frameworks"]
        h.append(f"<tr><td>{escape(r['id'])}</td><td>{escape(r['title'])}</td><td>{_tag(r['status'])}</td>"
                 f"<td>{escape(fw.get('SOC 2', '-'))}</td><td>{escape(fw.get('ISO 27001', '-'))}</td><td>{escape(fw.get('HIPAA', '-'))}</td></tr>")
    h.append("</table></div><h2>Framework readiness</h2><div class=cards>")
    for name, items in fw_view.items():
        ok = sum(i["status"] != "fail" for i in items)
        h.append(f"<div class=card><b>{ok}/{len(items)}</b>{escape(name)} requirements met</div>")
    h.append("</div><h2>Security questionnaire draft</h2><div class=wrap><table><tr><th>#</th><th>Question</th><th>Status</th></tr>")
    for r in qrows:
        cls = "pass" if r["status"] == "Ready" else ("P0" if r["status"].startswith("HOLD") else "P1")
        h.append(f"<tr><td>{escape(r['id'])}</td><td>{escape(r['question'])}</td><td class={cls}>{escape(r['status'])}</td></tr>")
    h.append("</table></div><h2>“Is all our data deleted within "
             f"{retention['asked']} days?”</h2><div class=card><b style='font-size:16px'>{escape(retention['verdict'])}</b><ul>")
    h += [f"<li>{escape(x)}</li>" for x in retention["breakdown"]]
    h.append("</ul></div><h2>Access review</h2><div class=cards>")
    for mgr, items in campaign.items():
        h.append(f"<div class=card><b>{len(items)}</b>to review: {escape(mgr)}</div>")
    h.append("</div><div class=wrap><table><tr><th>Account</th><th>Flagged before review</th></tr>")
    h += [f"<tr><td>{escape(f['email'])}</td><td>{escape(f['issue'])}</td></tr>" for f in flags]
    h.append("</table></div><p></p><div class=wrap><table><tr><th>Revoke decision</th><th>App</th><th>Verified in Okta</th></tr>")
    for r in removals:
        cls = "pass" if r["verified"] == "removed" else "P1"
        h.append(f"<tr><td>{escape(r['email'])}</td><td>{escape(r['app'])}</td><td class={cls}>{escape(r['verified'])}</td></tr>")
    h.append("</table></div><p class=mute>Evidence for every control is saved under evidence/&lt;control&gt;/&lt;date&gt;.json "
             "with SHA-256 hashes in evidence/manifest.json.</p></main></body></html>")
    return "\n".join(h)
