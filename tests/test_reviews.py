"""M6 复核批次：队列、引用一致性、版本乐观锁与半开时间窗。"""
from __future__ import annotations

import pytest

from app.errors import Conflict, DomainError, NotFound
from app.modules.m6_reviews import history, service, version
from tests.fixtures import expected as EXP


def test_queue_items(run):
    items = service.queue_items(run["run_id"])
    assert len(items) == EXP.PAIRS_REVIEW
    assert {item["reason_code"] for item in items} == {"P_CITY_MISMATCH", "P_REVIEW"}
    stats = service.queue_stats(run["run_id"])
    assert stats["pending"] == EXP.PAIRS_REVIEW
    assert stats["decided"] == 0
    assert stats["references"] == 5


def test_queue_sorted_by_score(run):
    items = service.queue_items(run["run_id"])
    scores = [float(item["score"]) for item in items]
    assert scores == sorted(scores, reverse=True)
    assert items[0]["pair_id"] == EXP.PAIR_CITY_MISMATCH


def test_one_sided_reference_flagged(run):
    """TRAP-21 双向引用不一致：自引、断链、成环、指向非主档四种都要检出。"""
    issues = service.reference_issues(run["run_id"])
    codes = {item["reason_code"] for item in issues}
    assert codes == {"X_REF_UNKNOWN", "X_REF_SELF", "X_REF_CYCLE", "X_REF_NOT_MASTER"}
    by_supplier = {item["supplier_id"]: item for item in issues}
    assert by_supplier["S-0053"]["ref_master_id"] == "S-0099"
    assert by_supplier["S-0053"]["reason_code"] == "X_REF_UNKNOWN"
    assert by_supplier["S-0064"]["reason_code"] == "X_REF_SELF"
    assert by_supplier["S-0067"]["reason_code"] == "X_REF_NOT_MASTER"
    assert "S-0065" in by_supplier and "S-0066" in by_supplier


def test_reference_cycle_detail(run):
    issues = {item["supplier_id"]: item for item in service.reference_issues(run["run_id"])}
    assert issues["S-0065"]["detail"] == "S-0065 -> S-0066 -> S-0065"


def test_decision_version_increments(run):
    record = service.decide(run["run_id"], EXP.PAIR_REVIEW, "keep", 0, "王核")
    assert record["version"] == 1
    assert record["expected_version"] == 0
    assert record["operator"] == "王核"
    stats = service.queue_stats(run["run_id"])
    assert stats["decided"] == 1
    assert stats["pending"] == EXP.PAIRS_REVIEW - 1


def test_stale_decision_rejected(run):
    """TRAP-26 陈旧提交：版本不匹配必须拒绝，不能覆盖新决定。"""
    service.decide(run["run_id"], EXP.PAIR_REVIEW, "keep", 0)
    with pytest.raises(Conflict) as error:
        service.decide(run["run_id"], EXP.PAIR_REVIEW, "merge", 0)
    assert error.value.code == "V_STALE_DECISION"
    assert version.current_version(run["run_id"], EXP.PAIR_REVIEW) == 1


def test_merge_on_tax_conflict_rejected(run):
    with pytest.raises(DomainError) as error:
        service.decide(run["run_id"], EXP.PAIR_TAX_CONFLICT, "merge", 0)
    assert error.value.code == "V_BAD_DECISION"
    assert error.value.status == 400


def test_unknown_pair_decision(run):
    with pytest.raises(NotFound) as error:
        service.decide(run["run_id"], "P-99999", "merge", 0)
    assert error.value.code == "V_UNKNOWN_PAIR"


def test_window_half_open(run):
    record = service.decide(run["run_id"], EXP.PAIR_REVIEW, "keep", 0)
    stamp = record["decided_at"]
    inside = history.window_summary(run["run_id"], since=stamp)
    excluded = history.window_summary(run["run_id"], until=stamp)
    assert inside["total"] == 1
    assert excluded["total"] == 0


def test_window_rejects_bad_timestamp(run):
    with pytest.raises(DomainError) as error:
        history.window_summary(run["run_id"], since="2026-13-45")
    assert error.value.code == "V_BAD_WINDOW"


def test_stale_decision_api(client):
    body = {"decision": "keep", "expected_version": 0}
    first = client.post(f"/api/reviews/{EXP.PAIR_REVIEW}/decision", json=body)
    assert first.status_code == 200
    assert first.json()["decision"]["version"] == 1
    second = client.post(f"/api/reviews/{EXP.PAIR_REVIEW}/decision", json=body)
    assert second.status_code == 409
    assert second.json()["reason_code"] == "V_STALE_DECISION"
    invalid = client.post(f"/api/reviews/{EXP.PAIR_REVIEW}/decision",
                          json={"decision": "drop", "expected_version": 1})
    assert invalid.status_code == 400
    assert invalid.json()["reason_code"] == "V_BAD_DECISION"


def test_batches_api(client):
    response = client.get("/api/batches")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert items[0]["run_id"] == EXP.RUN_ID
    assert items[0]["counts"]["accepted"] == EXP.ACCEPTED


def test_reviews_page_api(client):
    response = client.get("/api/reviews")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == EXP.PAIRS_REVIEW
    assert body["stats"]["references"] == 5
