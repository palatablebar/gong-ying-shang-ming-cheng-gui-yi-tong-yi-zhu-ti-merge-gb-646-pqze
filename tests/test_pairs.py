"""M4 相似判定：权重公式、阈值边界、规则优先级与硬冲突。"""
from __future__ import annotations

from decimal import Decimal

from app import store
from app.config import AUTO_THRESHOLD, REVIEW_THRESHOLD
from app.modules.m4_pairs import conflict, service, similarity, threshold
from tests.fixtures import expected as EXP


def test_dice_and_score_identical():
    scored = similarity.score("华远物流", "华远物流")
    assert scored["dice"] == Decimal("1.000000")
    assert scored["ratio"] == Decimal("1.000000")
    assert scored["score"] == Decimal("1.000000")


def test_score_weight_formula():
    scored = similarity.score("华远物流", "华远物流服务")
    expected = (scored["dice"] * Decimal("0.55")
                + scored["ratio"] * Decimal("0.45")).quantize(Decimal("0.000001"))
    assert scored["score"] == expected
    assert Decimal("0") < scored["score"] < Decimal("1")


def test_threshold_bands():
    assert threshold.band(Decimal("0.920000")) == "auto"
    assert threshold.band(Decimal("0.919999")) == "review"
    assert threshold.band(Decimal("0.800000")) == "review"
    assert threshold.band(Decimal("0.799999")) == "reject"
    assert threshold.describe()["auto"] == str(AUTO_THRESHOLD)
    assert threshold.describe()["review"] == str(REVIEW_THRESHOLD)


def test_tax_conflict_pair(run):
    """TRAP-19 多项命中：名称完全相同但税号不同，硬冲突优先，禁止合并。"""
    service.ensure_pairs(run["run_id"])
    pair = store.get_pair(run["run_id"], EXP.PAIR_TAX_CONFLICT)
    assert pair["left_id"] == "S-0003"
    assert pair["right_id"] == "S-0038"
    assert Decimal(pair["score"]) == Decimal("1.000000")
    assert pair["verdict"] == "reject"
    assert pair["reason_code"] == "P_TAX_CONFLICT"


def test_tax_match_beats_score(run):
    service.ensure_pairs(run["run_id"])
    pair = store.get_pair(run["run_id"], EXP.PAIR_TAX_MATCH)
    assert Decimal(pair["score"]) == EXP.PAIR_TAX_MATCH_SCORE
    assert Decimal(pair["score"]) < AUTO_THRESHOLD
    assert pair["verdict"] == "auto"
    assert pair["reason_code"] == "P_TAX_MATCH"


def test_city_mismatch_downgrades_auto(run):
    service.ensure_pairs(run["run_id"])
    pair = store.get_pair(run["run_id"], EXP.PAIR_CITY_MISMATCH)
    assert pair["verdict"] == "review"
    assert pair["reason_code"] == "P_CITY_MISMATCH"


def test_review_band_pair(run):
    service.ensure_pairs(run["run_id"])
    pair = store.get_pair(run["run_id"], EXP.PAIR_REVIEW)
    assert Decimal(pair["score"]) == EXP.PAIR_REVIEW_SCORE
    assert pair["verdict"] == "review"
    assert pair["reason_code"] == "P_REVIEW"


def test_rule_order_independent(monkeypatch):
    """TRAP-19 规则顺序不应影响结论：按名字取规则、按 rank 决胜。"""
    left = {"tax_id": "", "city": "重庆"}
    right = {"tax_id": "", "city": "成都"}
    baseline = conflict.decide(left, right, Decimal("1.000000"))
    monkeypatch.setattr(conflict, "RULES", tuple(reversed(conflict.RULES)))
    again = conflict.decide(left, right, Decimal("1.000000"))
    assert baseline["verdict"] == "review"
    assert again["verdict"] == baseline["verdict"]
    assert again["reason_code"] == baseline["reason_code"]

    tax_left = {"tax_id": "91110108MA01C7X21", "city": "北京"}
    tax_right = {"tax_id": "91110108MA02K3L4M", "city": "北京"}
    assert conflict.decide(tax_left, tax_right, Decimal("1.000000"))["verdict"] == "reject"


def test_verdict_stats(run):
    stats = service.ensure_pairs(run["run_id"])
    assert stats["total"] == EXP.PAIRS
    assert stats["auto"] == EXP.PAIRS_AUTO
    assert stats["review"] == EXP.PAIRS_REVIEW
    assert stats["reject"] == EXP.PAIRS_REJECT
    assert stats["total"] == stats["auto"] + stats["review"] + stats["reject"]


def test_pairs_api_filter(client):
    response = client.get("/api/pairs", params={"verdict": "reject", "limit": 200})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert all(item["verdict"] == "reject" for item in body["items"])
    assert body["stats"]["total"] == EXP.PAIRS
