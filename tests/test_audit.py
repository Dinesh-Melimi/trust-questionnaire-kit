import json
import os
from datetime import date

from tqk import access_review, checks, evidence, retention
from tqk.core import answer, load_library, load_questions

ENV = checks.load("samples/env.json")
TODAY = date(2026, 11, 25)
RESULTS = checks.run(checks.load("samples/controls.json"), ENV, TODAY)
BY_ID = {r["id"]: r for r in RESULTS}
QUEUE = checks.triage(RESULTS)


def test_exposure_sorted_before_gaps_and_noise():
    pri = [f["priority"] for f in QUEUE]
    assert pri == sorted(pri)
    assert pri[0] == "P0" and pri[-1] == "P2"


def test_leaver_with_prod_access_is_p0():
    f = BY_ID["AC-2"]["findings"]
    assert any(x["priority"] == "P0" and x["user"] == "sam@acmevoice.ai" for x in f)
    assert not any(x["user"] == "jay@acmevoice.ai" for x in f)  # already disabled


def test_service_account_and_accepted_exception_are_noise_not_failures():
    assert all(x["priority"] == "P2" for x in BY_ID["VM-1"]["findings"] if x["vuln"] == "CVE-2026-0450")
    assert any(x["priority"] == "P2" and "service account" in x["message"] for x in BY_ID["AC-1"]["findings"])


def test_public_website_bucket_is_not_a_failure():
    msgs = [x for x in BY_ID["EN-2"]["findings"] if x["resource"] == "marketing-site-assets"]
    assert msgs and msgs[0]["priority"] == "P2"


def test_passing_controls_pass():
    for cid in ("LG-1", "CM-1", "VD-2"):
        assert BY_ID[cid]["status"] == "pass", cid


def test_revoke_not_proven_until_access_gone():
    v = access_review.verify_removals(ENV)
    assert v == [{**v[0], "verified": "still has access"}]
    assert BY_ID["AC-3"]["status"] == "fail"


def test_manager_lists_skip_leavers_and_flag_them():
    lists, flags = access_review.build_campaign(ENV)
    assert all(i["email"] != "sam@acmevoice.ai" for items in lists.values() for i in items)
    assert any(f["email"] == "sam@acmevoice.ai" for f in flags)
    assert any("service account" in f["issue"] for f in flags)


def test_retention_answer_is_honest_about_backups_and_vendors():
    r = retention.answer_retention(ENV, 30)
    assert r["verdict"].startswith("Not fully")
    where = {g["where"] for g in r["gaps"]}
    assert where == {"call-exports-temp", "db-backups-prod", "Analytics warehouse"}
    assert retention.answer_retention(ENV, 90)["verdict"].startswith("Not fully")  # temp bucket keeps data forever


def test_questionnaire_holds_answers_tied_to_failing_controls():
    status = {r["id"]: r["status"] for r in RESULTS}
    rows = {r["id"]: r for r in answer(load_questions("samples/questionnaire.csv"), load_library("samples/library.json"),
                                       TODAY, control_status=status)}
    assert rows["1"]["status"].startswith("HOLD")      # MFA question while AC-1 fails
    assert rows["8"]["status"].startswith("HOLD")      # 30-day deletion while RT-1 fails
    assert rows["6"]["status"] == "Ready"              # AI training: VD-2 passes
    assert rows["8"]["answer_id"] == "RT-01" and rows["9"]["answer_id"] == "SP-01" and rows["10"]["answer_id"] == "AR-01"


def test_evidence_pack_is_hashed(tmp_path):
    m = evidence.write_pack(RESULTS, str(tmp_path), "2026-11-25")
    assert len(m) == len(RESULTS) and all(len(x["sha256"]) == 64 for x in m)
    assert json.load(open(os.path.join(tmp_path, "evidence", "manifest.json")))["run"] == "2026-11-25"


def test_one_control_set_maps_to_three_frameworks():
    v = evidence.framework_view(RESULTS)
    assert set(v) == {"SOC 2", "ISO 27001", "HIPAA"}
