"""M2 名称归一：全角、括号、后缀、地名、空白、大小写与去重规则。"""
from __future__ import annotations

from app.modules.m2_normalize import rules, service
from tests.fixtures import expected as EXP


def test_fullwidth_and_region_stripped():
    result = rules.normalize("鼎新科技（北京）有限公司")
    assert result.name == "鼎新科技"
    assert result.codes == ["N01", "N04", "N05"]


def test_bracket_unify_rule():
    result = rules.normalize("鼎新科技〔北京〕有限公司")
    assert result.name == "鼎新科技"
    assert "N02" in result.codes


def test_legal_suffix_stripped():
    assert rules.normalize("上海华远物流有限公司").name == "华远物流"
    assert rules.normalize("苏州精工机械制造有限公司").name == "精工机械制造"
    assert rules.normalize("南京金鼎电子科技有限公司").name == "金鼎电子科技"


def test_industry_word_kept():
    """后缀剥离不能吃掉行业词，否则不同主体会被误并。"""
    logistics = rules.normalize("华远物流有限公司").name
    trading = rules.normalize("华远贸易有限公司").name
    assert logistics == "华远物流"
    assert trading == "华远贸易"
    assert logistics != trading


def test_whitespace_removed():
    result = rules.normalize("  鼎新 科技 有限公司 ")
    assert result.name == "鼎新科技"
    assert "N03" in result.codes


def test_latin_lowercase():
    result = rules.normalize("ABC科技有限公司")
    assert result.name == "abc科技"
    assert "N06" in result.codes


def test_short_stem_guard():
    """剥离后主体不足 2 字时保留原文，避免产生空名称。"""
    assert rules.normalize("京公司").name == "京公司"
    assert rules.normalize("甲").name == "甲"


def test_alias_variants_converge():
    variants = ["北京鼎新科技有限公司", "鼎新科技（北京）有限公司",
                "鼎新科技〔北京〕有限公司", "鼎新科技有限公司"]
    names = {rules.normalize(item).name for item in variants}
    assert names == {"鼎新科技"}


def test_service_summary(run):
    summary = service.ensure_normalized(run["run_id"])
    assert summary["total"] == EXP.ACCEPTED
    assert summary["changed"] == EXP.ACCEPTED
    assert summary["empty"] == 0
    assert summary["distinct"] == EXP.DISTINCT_NORMALIZED
    hits = {item["code"]: item["count"] for item in summary["rule_hits"]}
    assert hits["N04"] == EXP.ACCEPTED
    assert hits["N05"] == 57


def test_normalize_idempotent(run):
    first = service.ensure_normalized(run["run_id"])
    second = service.ensure_normalized(run["run_id"])
    assert first == second


def test_preview_api(client):
    response = client.post("/api/normalize/preview", json={"name": "鼎新科技〔北京〕有限公司"})
    assert response.status_code == 200
    body = response.json()
    assert body["normalized"] == "鼎新科技"
    assert body["codes"] == ["N02", "N04", "N05"]
    assert body["changed"] is True


def test_normalize_table_api(client):
    response = client.get("/api/normalize")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == EXP.ACCEPTED
    assert body["summary"]["distinct"] == EXP.DISTINCT_NORMALIZED
