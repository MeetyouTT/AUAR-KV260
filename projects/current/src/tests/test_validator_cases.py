# -*- coding: utf-8 -*-
"""Validator 正反例集参数化单测（A4 · 9/24「Validator 至少 100 组正反例」）—— 人3

数据源：`tests/data/validator_cases.json`（声明式用例集，当前 173 组正反例）
执行器：`scripts/validator_cases.py`（与出「校验报告」共用同一实现，保证
「单测结论 == 报告结论」，避免两套判据漂移）
被测：`board/runtime/validator/`（Schema → Semantic → Policy 三层）

环境标签：**PC / SIMULATED**（本机 pytest，不含板端实测）。
"""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.validator_cases import CASES_PATH, load_cases, run_all, run_case  # noqa: E402

_DATA = load_cases()
_CASES = _DATA["cases"]
_KINDS = ("response", "request", "scene")
_ONLY = (None, "schema", "semantic", "policy")
# 三条红线必须被反例覆盖（A1 报告 §五 验收门槛：伪造视觉事实/过期/越权 100% 拒绝）
_REDLINE_CODES = (
    "policy.visual_claim_ungrounded",
    "policy.unknown_fact",
    "policy.control_denied",
    "policy.emotion_not_allowed",
    "policy.avatar_not_allowed",
    "semantic.request_id_mismatch",
    "semantic.scene_expired",
    "semantic.track_not_found",
    "semantic.stale_audio_generation",
    "schema.missing_field",
    "schema.enum_violation",
)


def _base_names(kind: str) -> set:
    key = {"response": "response_bases", "request": "request_bases", "scene": "scene_bases"}[kind]
    return set(_DATA[key])


@pytest.mark.parametrize("case", _CASES, ids=[c.get("id", "case") for c in _CASES])
def test_validator_case(case):
    """每条用例：整体通过性 / 短路层 / 错误码必须与期望一致。"""
    result = run_case(case, _DATA)
    assert result["passed"], (
        "用例 %s（%s）不符期望：expect_ok=%s 实际 ok=%s layer=%s codes=%s missing=%s"
        % (result["id"], result["desc"], result["expect_ok"], result["ok"],
           result["layer"], result["codes"], result["missing_codes"]))


class TestCaseSetIntegrity:
    """用例集自身的元检查：防止用例缩水 / 重复 / 期望缺失。"""

    def test_case_count_at_least_100(self):
        assert len(_CASES) >= 100, "用例数 %d，未达 9/24 节点要求的 100 组" % len(_CASES)

    def test_ids_unique_and_non_empty(self):
        ids = [c.get("id") for c in _CASES]
        assert all(ids), "存在空 id 用例"
        duplicates = {i for i in ids if ids.count(i) > 1}
        assert not duplicates, "重复 id: %s" % sorted(duplicates)

    def test_required_fields_and_enums(self):
        for case in _CASES:
            assert case.get("desc"), "用例 %s 缺 desc" % case.get("id")
            assert isinstance(case.get("expect_ok"), bool), "用例 %s 缺 expect_ok" % case.get("id")
            assert case.get("kind") in _KINDS, "用例 %s kind 非法" % case.get("id")
            assert case.get("only") in _ONLY, "用例 %s only 非法" % case.get("id")
            assert ("base" in case) or ("raw" in case), "用例 %s 既无 base 也无 raw" % case.get("id")

    def test_referenced_bases_exist(self):
        for case in _CASES:
            if "base" in case:
                assert case["base"] in _base_names(case["kind"]), \
                    "用例 %s 引用不存在的 base=%s" % (case.get("id"), case["base"])
            if case.get("base_ctx"):
                assert case["base_ctx"] in _DATA["ctx_presets"], \
                    "用例 %s 引用不存在的 ctx=%s" % (case.get("id"), case["base_ctx"])

    def test_positive_and_negative_ratio(self):
        positive = [c for c in _CASES if c.get("expect_ok")]
        negative = [c for c in _CASES if not c.get("expect_ok")]
        assert len(positive) >= 20, "正例仅 %d 组" % len(positive)
        assert len(negative) >= 60, "反例仅 %d 组" % len(negative)

    def test_negative_cases_declare_expectations(self):
        for case in _CASES:
            if not case.get("expect_ok"):
                assert case.get("expect_codes"), "反例 %s 未声明 expect_codes" % case.get("id")
            else:
                assert not case.get("expect_codes"), "正例 %s 不应声明 expect_codes" % case.get("id")
                assert not case.get("expect_layer"), "正例 %s 不应声明 expect_layer" % case.get("id")

    def test_three_layers_are_covered(self):
        layers = {}
        for result in run_all()["results"]:
            layers[result["layer"]] = layers.get(result["layer"], 0) + 1
        for layer in ("schema.response", "schema.request", "schema.scene",
                      "semantic.response", "semantic.scene", "policy.response"):
            assert layers.get(layer, 0) >= 1, "层 %s 无用例覆盖" % layer

    def test_redline_error_codes_covered(self):
        covered = set()
        for result in run_all()["results"]:
            covered.update(result["all_codes"])
        missing = [code for code in _REDLINE_CODES if code not in covered]
        assert not missing, "红线错误码未被任何用例触发: %s" % missing

    def test_report_matches_test_suite(self):
        """出报告的口径必须与单测一致：全量跑一遍要求 0 失败。"""
        report = run_all()
        assert report["total"] == len(_CASES)
        assert report["failed"] == 0, "失败用例: %s" % report["failed_cases"]
        assert os.path.isfile(CASES_PATH)
