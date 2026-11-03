#!/usr/bin/env python3
"""Build a source-only RAR layout catalog; never gather or compress business files."""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "rar_source_layout.md"
BUDGETS = [
    ("source", "实际业务和硬件源码", "src/board/;src/host/;src/common/;src/ui/;src/tools/;src/scripts/;src/fpga/;src/native/;src/hardware/;src/requirements*", 20000000),
    ("build_dependencies", "构建与必要上游源码", "build/;src/third_party/", 8000000),
    ("deployment_config", "部署与配置", "board/;src/config/", 2000000),
    ("model_data", "模型输入、适配与小数据", "src/models/;src/data/", 45000000),
    ("assets", "最小测试资源与资源约定预算（不含全量旧帧/可再生RGB565）", "src/assets/", 15000000),
    ("simulation_tests", "测试与仿真", "sim/;src/tests/", 5000000),
    ("docs_evidence", "Skill、精选证据与说明", "skill/;report/;data/;src/docs/;根文件", 5000000),
]

REQUIREMENTS = [
    ("r01", "器件、平台与工具版本", "3.3.3.1-2", "build/env.json;README.md;report/design_report.md", "填写实际型号与2022.2等工具版本的选择依据"),
    ("r02", "完整实际源码及运行根", "3.3.5.1", "src/board/;src/host/;src/common/;src/tools/;src/ui/;src/fpga/", "src对应原aura根；实际版本按最终发布清单回收"),
    ("r03", "必要设计输入", "3.3.5.1;老师补充", "src/fpga/constraints/;src/fpga/bd/;src/fpga/ip/;src/third_party/", "实际约束、BD/IP、头文件和初始化按真实名字收齐，不能漏隐藏引用"),
    ("r04", "可复现构建脚本", "3.3.5.1", "build/reproduce.py;build/build.tcl;build/env.json;README.md", "从已交源码和固定依赖重建；历史DCP/旧bundle及隐藏引用仍待实际验收"),
    ("r05", "仿真与正确性", "3.3.5.1", "sim/rtl/tb_nominal.sv;sim/rtl/tb_wide.sv;sim/rtl/tb_pulse_guard.sv;sim/rtl/tb_servo.sv;src/tests/;src/data/golden/;report/validation_summary.md", "四份真实bench，result.json由本轮重跑生成，不携历史PASS充当前置输入"),
    ("r06", "综合实现、时钟与资源指标", "3.3.5.1", "report/validation_summary.md;data/metrics.csv;build/build.tcl", "关键原报告片段及来源随摘要，完整报告由构建再生成"),
    ("r07", "上板运行与实测对照", "3.3.5.1", "board/deploy.json;board/install.sh;data/metrics.csv;report/validation_summary.md", "部署定义与实测关键点，预编译工件重建；Windows/板级运行单独验收"),
    ("r08", "性能与资源优化及判断依据", "3.3.4;3.3.5.3", "data/metrics.csv;report/design_report.md;report/validation_summary.md", "同条件、版本、样本、方法和未通过项分别说明"),
    ("r09", "真实AI协作及自我纠错", "3.3.3.1;3.3.5.3", "report/ai_collaboration.md;data/metrics.csv", "真实关键问答及验证摘录，数值表登记原记录来源和SHA"),
    ("r10", "Skill复用及失败边界", "3.3.5.2", "skill/README.md;skill/pynq-contract-testgen/;skill/pynq-contract-testgen/evidence/", "Skill提交属于指南要求；本方案选现有PYNQ包，数量按实际"),
    ("r11", "设计原理、接口和复现说明", "3.3.5.3", "report/design_report.md;README.md;src/common/", "正式模板报告PDF另交；包内源稿含七类内容及完整步骤"),
    ("r12", "依赖、配置、模型与资源闭包", "完整工程复现;老师补充", "src/config/runtime.sim.json;src/config/model_manifest.json;src/models/;src/assets/;src/data/;third_party_notices.md;board/system/image_manifest.json", "必要运行输入在src内；主配置保留有效嵌套结构；公开主配置按真实文件名"),
    ("r13", "英文命名及推荐目录对照", "3.3.5.4", "README.md", "推荐七目录及根README全部保留；正文可中文"),
    ("r14", "源码许可与开源信息", "3.3.3.3", "license;third_party_notices.md;README.md", "正式仓库URL/tag/commit及许可按最终发布填写"),
    ("r15", "通用PYNQ Skill方向", "3.3.2;3.3.5.2", "skill/pynq-contract-testgen/;skill/pynq-contract-testgen/readme.md;skill/pynq-contract-testgen/examples/;skill/pynq-contract-testgen/evidence/", "PYNQ方向可选加分；已有离线初版，真实PYNQ/跨板/非作者复用未验证"),
]


def budget_group(path):
    for prefix, group in [
        ("src/third_party", "build_dependencies"),
        ("src/config", "deployment_config"),
        ("src/models", "model_data"),
        ("src/data", "model_data"),
        ("src/assets", "assets"),
        ("src/tests", "simulation_tests"),
        ("src/docs", "docs_evidence"),
    ]:
        if path.rstrip("/") == prefix or path.startswith(prefix + "/"):
            return group
    top = path.split("/")[0]
    if top == "src":
        return "source"
    if top == "build":
        return "build_dependencies"
    if top == "board":
        return "deployment_config"
    if top == "sim":
        return "simulation_tests"
    return "docs_evidence"


def main():
    doc = DOC.read_text(encoding="utf-8")
    trees = re.findall(r"```text\n(.*?)\n```", doc, re.S)
    assert len(trees) == 1
    tree = trees[0]
    assert tree.splitlines()[0] == "auar_xuefei/"
    rows = []
    stack = []
    for line in tree.splitlines()[1:]:
        if line.replace("│", "").strip() == "":
            continue
        match = re.fullmatch(r"((?:│   |    )*)(?:├── |└── )(.*)", line)
        assert match, line
        level = len(match.group(1)) // 4
        assert level <= len(stack), line
        parts = re.split(r"\s+#\s*", match.group(2), maxsplit=1)
        item = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else "见模块说明，收齐实际源文件"
        directory = item.endswith("/")
        name = item.rstrip("/")
        stack = stack[:level]
        path = "/".join(stack + [name]) + ("/" if directory else "")
        rows.append({
            "path": path,
            "entry_type": "目录" if directory else "文件",
            "purpose": description,
            "collection_scope": "实际源码/输入完整子树；剔除生成物" if directory else "实际对应文件；不生成空占位",
            "required_if": "最终实际使用时" if "[条件]" in description else "按最终实际实现收齐",
            "budget_group": budget_group(path),
            "submission_state": "目录设计；实际内容未收集或打包",
        })
        if directory:
            stack.append(name)

    paths = {row["path"] for row in rows}
    assert len(paths) == len(rows)
    prohibited = (".xpr", ".dcp", ".xsa", ".hwh", ".bit", ".bit.bin", ".dtbo", ".xclbin", ".so", ".o", ".pyc", ".xmodel", ".gguf", ".safetensors", ".whl", ".mp4")
    for row in rows:
        parts = row["path"].rstrip("/").split("/")
        for name in parts:
            assert name == "README.md" or re.fullmatch(r"[a-z0-9_.-]+", name), row["path"]
        if len(parts) > 1:
            assert "/".join(parts[:-1]) + "/" in paths
        if row["entry_type"] == "文件":
            source_hwh_fixture = row["path"].startswith("skill/pynq-contract-testgen/examples/") and row["path"].endswith("metadata_fixture.hwh")
            assert source_hwh_fixture or not row["path"].lower().endswith(prohibited), row["path"]
    required = ["README.md", "src/", "sim/", "build/", "board/", "data/", "skill/", "report/"]
    assert all(path in paths for path in required)
    runtime_required = ["src/board/", "src/host/", "src/common/", "src/ui/", "src/config/", "src/models/", "src/assets/", "src/data/", "src/hardware/", "src/tests/", "src/tools/"]
    assert all(path in paths for path in runtime_required)
    assert not any(path.startswith(("src/kv260/", "src/windows/", "src/common/aura_contracts/")) for path in paths)
    assert not any(path.endswith(("tb_registers.sv", "tb_pwm.sv", "tb_command_guard.sv", "result.json")) for path in paths)
    assert sum(row[3] for row in BUDGETS) == 100000000

    with (ROOT / "rar_source_requirements.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "requirement", "basis", "planned_paths", "notes", "state"])
        for rid, requirement, basis, targets, notes in REQUIREMENTS:
            assert all(target in paths for target in targets.split(";")), (rid, targets)
            writer.writerow([rid, requirement, basis, targets, notes, "目录覆盖；实际实现与复现未由本次验证"])

    with (ROOT / "rar_source_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (ROOT / "rar_source_budget.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "content", "paths", "collection_budget_bytes", "basis", "measured"])
        for group, content, prefixes, size in BUDGETS:
            writer.writerow([group, content, prefixes, size, "未压缩收集额度，非压缩后实测", "否"])
    (ROOT / "rar_source_tree.txt").write_text(
        "AUAR·雪妃：RAR源码复现包定稿结构（方案A）\n"
        "src/对应原aura运行根，旧拆分布局不再使用。\n"
        "按用户提供的赛事方老师说明：完整源码＋重建脚本＋精简关键说明。\n"
        "以下是设计；目录应收齐实际源码，所有脚本均为建议目标。\n"
        "未收集真实源码，未生成业务占位文件，未制作RAR。\n\n" + tree + "\n",
        encoding="utf-8-sig",
    )

    links = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", doc):
        resolved = (ROOT / target).resolve()
        assert resolved.exists() or resolved == ROOT / "rar_source_validation.json", target
        links.append(target)
    result = {
        "status": "PASS",
        "layout_version": "scheme_a_runtime_root",
        "scope": "只校验目录设计、命名、覆盖、预算算术和文档链接",
        "teacher_guidance_applied": True,
        "layout_entries": len(rows),
        "directories": sum(row["entry_type"] == "目录" for row in rows),
        "files": sum(row["entry_type"] == "文件" for row in rows),
        "top_level_directories": sorted(row["path"] for row in rows if row["entry_type"] == "目录" and row["path"].count("/") == 1),
        "budget_groups": dict(sorted(Counter(row["budget_group"] for row in rows).items())),
        "collection_budget_bytes": 100000000,
        "actual_rar_hard_limit_bytes_exclusive": 200000000,
        "actual_rar_bytes": None,
        "rar_created": False,
        "actual_business_files_collected": 0,
        "build_or_board_validation_run": False,
        "declared_input_dependency_to_resolve": "历史DCP/旧bundle、IP头文件绝对路径、XCLBIN及base DTB来源；未完整重建验证",
        "generated_artifacts_listed_as_inputs": 0,
        "duplicate_paths": 0,
        "invalid_parents": 0,
        "names_ascii": True,
        "recommended_official_entries_covered": required,
        "source_submission_requirement_rows": len(REQUIREMENTS),
        "requirement_paths_in_source_layout": True,
        "runtime_root": "src/",
        "runtime_inputs_keep_original_relative_positions": runtime_required,
        "real_rtl_bench_names_in_design": ["tb_nominal.sv", "tb_wide.sv", "tb_pulse_guard.sv", "tb_servo.sv"],
        "historical_rtl_result_not_listed_as_build_input": True,
        "local_links_checked": len(links),
        "document_sha256": hashlib.sha256(DOC.read_bytes()).hexdigest(),
    }
    (ROOT / "rar_source_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
