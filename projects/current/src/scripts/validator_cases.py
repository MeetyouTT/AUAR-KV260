# -*- coding: utf-8 -*-
"""Validator 正反例集加载器 / 执行器 / 校验报告（A4 · 9/24「Validator 至少 100 组正反例」）

用途
----
1. `tests/test_validator_cases.py` 用它做参数化单测（数据驱动，用例在
   `tests/data/validator_cases.json`）；
2. 命令行出「校验报告」证据：
   `python scripts/validator_cases.py --json evidence_shots/validator_cases_report.json`

用例格式（JSON，紧凑声明式，避免 100+ 组用例重复抄写整个报文）
------------------------------------------------------------
```
"response_bases" / "request_bases" / "scene_bases"   命名基座报文
"scene_presets"                                      命名 SceneState
"ctx_presets"                                        命名校验上下文（可引用 scene_presets）
"cases"                                              用例数组
```
单条 case 字段：

| 字段 | 说明 |
|---|---|
| `id` | 唯一编号（`R-###` 响应 / `Q-###` 请求 / `S-###` 场景） |
| `kind` | `response` / `request` / `scene` |
| `desc` | 中文说明（打印与报告用） |
| `base` | 基座名；省略时用 `raw` |
| `base_ctx` | `ctx_presets` 名，默认 `default` |
| `set` | 覆盖：`{"resp.<path>": v, "ctx.<field>": v, "scene.<path>": v}` |
| `del` | 删除：`["resp.<path>", "scene.<path>"]` |
| `fill` | 重复填充：`{"resp.visual_claims": {"template": {...}, "times": 9}}` |
| `raw` | 直接给出被校验对象（任意 JSON 值，用于非对象输入） |
| `expect_ok` | 期望整体是否通过（**正例必须无任何 issue**） |
| `expect_layer` | 期望短路所在层（可选，仅反例） |
| `expect_codes` | 期望命中的错误码（全部必须出现） |

环境标签：**PC / SIMULATED**（本机 pytest / 工具执行，不含板端实测）。
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import re
import sys
import typing

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from board.runtime.validator import ValidationChain, ValidationContext      # noqa: E402

CASES_PATH = os.path.join(_ROOT, "tests", "data", "validator_cases.json")
ENV_LABEL = "PC / SIMULATED"

_TOKEN_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _tokens(path: str) -> typing.List[typing.Any]:
    """把 "a.b[0].c" 解析为 ["a", "b", 0, "c"]。"""
    out: typing.List[typing.Any] = []
    for name, index in _TOKEN_RE.findall(path):
        out.append(int(index) if index != "" else name)
    return out


def deep_get(obj: typing.Any, path: str) -> typing.Any:
    cur = obj
    for token in _tokens(path):
        cur = cur[token]
    return cur


def deep_set(obj: typing.Any, path: str, value: typing.Any) -> None:
    tokens = _tokens(path)
    cur = obj
    for token in tokens[:-1]:
        cur = cur[token]
    cur[tokens[-1]] = value


def deep_del(obj: typing.Any, path: str) -> None:
    tokens = _tokens(path)
    cur = obj
    for token in tokens[:-1]:
        cur = cur[token]
    del cur[tokens[-1]]



# ---------------------------------------------- 值级引用（避免重复抄写长报文）
#   "$scene.<name>"                              → scene_presets 里的场景（深拷贝）
#   {"$repeat": {"char": "很", "times": 501}}     → 重复字符（造超长串）
#   {"$list":  {"template": {...}, "times": 9}}  → 重复元素（造超长数组）
def expand_refs(value: typing.Any, data: typing.Dict) -> typing.Any:
    if isinstance(value, str) and value.startswith("$scene."):
        return copy.deepcopy(data["scene_presets"][value[len("$scene."):]])
    if isinstance(value, dict):
        if "$repeat" in value and len(value) == 1:
            spec = value["$repeat"]
            return str(spec.get("char", "x")) * int(spec["times"])
        if "$list" in value and len(value) == 1:
            spec = value["$list"]
            return [copy.deepcopy(spec["template"]) for _ in range(int(spec["times"]))]
        return {key: expand_refs(item, data) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_refs(item, data) for item in value]
    return value


# ---------------------------------------------------------------- 用例装配
def load_cases(path: typing.Optional[str] = None) -> typing.Dict:
    """读取用例集 JSON（默认 `tests/data/validator_cases.json`），并展开值级引用。"""
    with open(path or CASES_PATH, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return expand_refs(raw, raw)


def build_ctx(case: typing.Dict, data: typing.Dict) -> ValidationContext:
    """按 `ctx_presets` + 用例覆盖构造 ValidationContext。"""
    name = case.get("base_ctx") or "default"
    preset = copy.deepcopy(data["ctx_presets"][name])
    scene_name = preset.pop("scene", None)
    scene = copy.deepcopy(data["scene_presets"][scene_name]) if scene_name else None
    ctx = ValidationContext(
        request_id=preset.get("request_id", ""),
        scene_state=scene,
        scene_seq=preset.get("scene_seq", 0),
        audio_generation_id=preset.get("audio_generation_id", 0),
        request_audio_generation_id=preset.get("request_audio_generation_id"),
        allowed_emotions=tuple(preset.get("allowed_emotions") or ()),
        allowed_avatar_actions=tuple(preset.get("allowed_avatar_actions") or ()),
        max_reply_len=preset.get("max_reply_len", 200),
        now_ms=preset.get("now_ms", 0),
        ttl_ms=preset.get("ttl_ms", 30000),
    )
    for path, value in (case.get("set") or {}).items():
        if path.startswith("ctx."):
            field = path[len("ctx."):]
            if field in ("allowed_emotions", "allowed_avatar_actions"):
                value = tuple(value)
            setattr(ctx, field, value)
        elif path.startswith("scene."):
            if not isinstance(ctx.scene_state, dict):
                raise ValueError("用例 %s 覆盖 scene.* 但 ctx 无场景" % case.get("id"))
            deep_set(ctx.scene_state, path[len("scene."):], copy.deepcopy(value))
    for path in case.get("del") or []:
        if path.startswith("scene."):
            if not isinstance(ctx.scene_state, dict):
                raise ValueError("用例 %s 删除 scene.* 但 ctx 无场景" % case.get("id"))
            deep_del(ctx.scene_state, path[len("scene."):])
    return ctx


def build_target(case: typing.Dict, data: typing.Dict, kind: str) -> typing.Any:
    """按基座 + 覆盖/删除/填充构造被校验对象。

    `raw` 优先（用于非对象输入），且 `raw` 同样支持 set / del / fill 覆盖
    ——否则「引用预设场景 + 局部改坏」的用例无法生效。
    """
    if "raw" in case:
        target = copy.deepcopy(case["raw"])
    else:
        bases_key = {"response": "response_bases", "request": "request_bases",
                     "scene": "scene_bases"}[kind]
        base_name = case.get("base")
        if not base_name:
            raise ValueError("用例 %s 既无 base 也无 raw" % case.get("id"))
        target = copy.deepcopy(data[bases_key][base_name])
    for path, value in (case.get("set") or {}).items():
        if path.startswith("resp."):
            deep_set(target, path[len("resp."):], copy.deepcopy(value))
    for path in case.get("del") or []:
        if path.startswith("resp."):
            deep_del(target, path[len("resp."):])
    for path, spec in (case.get("fill") or {}).items():
        if path.startswith("resp."):
            items = [copy.deepcopy(spec["template"]) for _ in range(int(spec["times"]))]
            deep_set(target, path[len("resp."):], items)
    return target


def run_case(case: typing.Dict, data: typing.Dict,
             chain: typing.Optional[ValidationChain] = None) -> typing.Dict:
    """执行单条用例 → 结构化结果（含是否与期望一致）。

    `only` 字段可指定「只跑某一层」（schema / semantic / policy），用于覆盖
    被上游层拦截、单靠串行链走不到的用例（如 people_count 为负的语义判定）。
    默认不填 = 走完整三层链（短路语义）。
    """
    chain = chain or ValidationChain()
    kind = case.get("kind", "response")
    only = case.get("only")
    if only not in (None, "schema", "semantic", "policy"):
        raise ValueError("未知 only=%r（用例 %s）" % (only, case.get("id")))
    ctx = build_ctx(case, data)
    target = build_target(case, data, kind)
    if kind == "response":
        if only == "schema":
            res = chain.schema.validate_response(target)
        elif only == "semantic":
            res = chain.semantic.validate_response(target, ctx)
        elif only == "policy":
            res = chain.policy.validate_response(target, ctx)
        else:
            res = chain.validate_response(target, ctx)
        full = chain.validate_response_all(target, ctx)
    elif kind == "request":
        if only in (None, "schema"):
            res = chain.validate_request(target)
        else:
            raise ValueError("用例 %s：request 只支持 schema 层" % case.get("id"))
        full = res
    elif kind == "scene":
        if only == "schema":
            res = chain.schema.validate_scene_state(target)
        elif only == "semantic":
            res = chain.semantic.validate_scene_state(target, ctx)
        else:
            res = chain.validate_scene_state(target, ctx)
        full = res
    else:
        raise ValueError("未知 kind=%r（用例 %s）" % (kind, case.get("id")))

    codes = [issue.code for issue in res.issues]
    expect_ok = bool(case.get("expect_ok"))
    expect_layer = case.get("expect_layer")
    expect_codes = list(case.get("expect_codes") or [])
    missing = [code for code in expect_codes if code not in codes]
    passed = (res.ok == expect_ok) and not missing
    if expect_ok:
        passed = passed and not codes              # 正例必须零 issue
    if expect_layer:
        passed = passed and res.layer == expect_layer
    return {
        "id": case.get("id", ""),
        "kind": kind,
        "desc": case.get("desc", ""),
        "expect_ok": expect_ok,
        "expect_layer": expect_layer,
        "expect_codes": expect_codes,
        "ok": res.ok,
        "layer": res.layer,
        "codes": codes,
        "all_codes": sorted({issue.code for issue in full.issues}),
        "missing_codes": missing,
        "passed": passed,
    }


# ---------------------------------------------------------------- 校验报告
def run_all(cases_path: typing.Optional[str] = None,
            chain: typing.Optional[ValidationChain] = None) -> typing.Dict:
    """跑完整用例集 → 校验报告 dict（失败用例 + 错误码分布 + 逐条明细）。"""
    data = load_cases(cases_path)
    chain = chain or ValidationChain()
    results = []
    for case in data.get("cases", []):
        try:
            results.append(run_case(case, data, chain))
        except Exception as exc:      # 用例本身写错 → 记为执行器错误（不算通过）
            results.append({
                "id": case.get("id", ""), "kind": case.get("kind", ""),
                "desc": case.get("desc", ""), "expect_ok": bool(case.get("expect_ok")),
                "expect_layer": case.get("expect_layer"), "expect_codes": [],
                "ok": None, "layer": "harness.error", "codes": ["harness.error"],
                "all_codes": ["harness.error"], "missing_codes": [],
                "passed": False, "error": "%s: %s" % (type(exc).__name__, exc),
            })
    failed = [r for r in results if not r["passed"]]
    positives = [r for r in results if r["expect_ok"]]
    negatives = [r for r in results if not r["expect_ok"]]
    by_kind: typing.Dict[str, int] = {}
    by_layer: typing.Dict[str, int] = {}
    code_counts: typing.Dict[str, int] = {}
    for result in results:
        by_kind[result["kind"]] = by_kind.get(result["kind"], 0) + 1
        by_layer[result["layer"]] = by_layer.get(result["layer"], 0) + 1
        for code in result["all_codes"]:
            code_counts[code] = code_counts.get(code, 0) + 1
    return {
        "tool": "scripts/validator_cases.py",
        "env_label": ENV_LABEL,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "cases_path": os.path.relpath(cases_path or CASES_PATH, _ROOT).replace("\\", "/"),
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "positive_total": len(positives),
        "positive_passed": sum(1 for r in positives if r["passed"]),
        "negative_total": len(negatives),
        "negative_passed": sum(1 for r in negatives if r["passed"]),
        "by_kind": by_kind,
        "by_layer": by_layer,
        "code_counts": dict(sorted(code_counts.items())),
        "failed_cases": [{"id": r["id"], "desc": r["desc"], "layer": r["layer"],
                          "codes": r["codes"], "missing_codes": r["missing_codes"]}
                         for r in failed],
        "results": results,
    }


def write_report(report: typing.Dict, path: str) -> str:
    """把校验报告写盘（utf-8，中文不转义）。"""
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return path


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="执行 Validator 正反例集并出校验报告（环境标签：%s）" % ENV_LABEL)
    parser.add_argument("--cases", default=CASES_PATH, help="用例集 JSON 路径")
    parser.add_argument("--json", default="", help="报告输出路径（例如 evidence_shots/validator_cases_report.json）")
    parser.add_argument("--verbose", action="store_true", help="打印每条用例结果")
    args = parser.parse_args(argv)

    report = run_all(args.cases)
    print("[validator-cases] env=%s total=%d passed=%d failed=%d (positive %d/%d, negative %d/%d)"
          % (report["env_label"], report["total"], report["passed"], report["failed"],
             report["positive_passed"], report["positive_total"],
             report["negative_passed"], report["negative_total"]))
    print("[validator-cases] by_kind=%s" % report["by_kind"])
    print("[validator-cases] code_counts=%s" % report["code_counts"])
    if args.verbose:
        for result in report["results"]:
            print("  %-8s %-6s expect_ok=%-5s ok=%-5s layer=%-18s codes=%s"
                  % (result["id"], result["kind"], result["expect_ok"], result["ok"],
                     result["layer"], ",".join(result["codes"]) or "-"))
    if report["failed"]:
        print("[validator-cases] FAILED:")
        for item in report["failed_cases"]:
            print("  %s %s layer=%s codes=%s missing=%s"
                  % (item["id"], item["desc"], item["layer"], item["codes"], item["missing_codes"]))
    if args.json:
        print("[validator-cases] report -> %s" % write_report(report, args.json))
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
