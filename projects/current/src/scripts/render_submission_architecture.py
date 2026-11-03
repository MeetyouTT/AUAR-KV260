#!/usr/bin/env python3
"""Render the complete competition architecture and create documented slots.

Read-only with respect to runtime, devices, firmware and original evidence.
Generated files are marked; an unmarked existing file is never overwritten.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import textwrap
from urllib.parse import quote
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/architecture"
STAGE = ROOT / "submission/aura_junior"
MARKER = "aura-architecture-generated"


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.suffix in (".md", ".html") and MARKER not in path.read_text(encoding="utf-8"):
        raise ValueError("Refusing to replace unmarked document: " + str(path))
    path.write_text(value, encoding="utf-8")


def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def table(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    write(path, stream.getvalue())


def source_path(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def validate(data):
    assert data["schema_version"] == "aura-junior-architecture-1"
    assert data["physical_actuation_enabled"] is False
    modules = {m["id"]: m for m in data["modules"]}
    assert len(modules) == len(data["modules"])
    assert len({m["planned_path"] for m in modules.values()}) == len(modules)
    groups = {g["id"] for g in data["groups"]}
    missing = []
    covered = set()
    for m in modules.values():
        assert m["group"] in groups and m["status"] in data["statuses"]
        assert m["input"] and m["output"] and m["remaining"]
        assert re.fullmatch(r"[a-z0-9_/-]+", m["planned_path"])
        assert ".." not in Path(m["planned_path"]).parts
        for name in m["existing"]:
            if not source_path(name).exists():
                missing.append({"module": m["id"], "source": name})
    if missing:
        raise ValueError("Unavailable declared sources: " + json.dumps(missing, ensure_ascii=False))
    for d in data["diagrams"]:
        assert re.fullmatch(r"[a-z0-9_]+", d["id"])
        nodes = [n for c in d["clusters"] for n in c["nodes"]]
        assert len(nodes) == len(set(nodes)) and set(nodes) <= modules.keys()
        assert d.get("node_overrides", {}).keys() <= set(nodes)
        for key, override in d.get("node_overrides", {}).items():
            assert display_module(d, modules[key])["status"] in data["statuses"]
        covered.update(nodes)
        for e in d["edges"]:
            assert e["from"] in nodes and e["to"] in nodes
    assert covered == modules.keys(), "Unrepresented modules: " + str(modules.keys() - covered)
    return modules


def label(m, data):
    title = "\n".join(textwrap.wrap(m["name"], width=23, break_long_words=False, break_on_hyphens=False))
    return m["group"] + " | " + title + "\n" + m["placement"] + " · " + m["owner"] + "\n[" + data["statuses"][m["status"]]["label"] + "]"


def display_module(d, m):
    return {**m, **d.get("node_overrides", {}).get(m["id"], {})}


def dot_source(d, modules, data):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    heading = d["title"] + "\n" + d["subtitle"] + "\n" + "颜色表示证据层级；灰色虚线框为待做；所有节点另附文字状态。"
    lines = ["// " + MARKER, "digraph architecture {",
             'graph [rankdir=' + d["direction"] + ', newrank=true, compound=true, bgcolor="white", pad="0.35", nodesep="0.35", ranksep="0.72", fontname="Noto Sans CJK SC", fontsize=20, labelloc=t, label=' + q(heading) + '];',
             'node [shape=box, style="rounded,filled", margin="0.15,0.11", fontname="Noto Sans CJK SC", fontsize=12, fontcolor="#0f172a", penwidth=1.4];',
             'edge [fontname="Noto Sans CJK SC", fontsize=10, color="#475569", arrowsize=0.75];']
    for index, c in enumerate(d["clusters"]):
        lines.append("subgraph cluster_" + str(index) + " {")
        lines.append('label=' + q(c["title"]) + '; fontsize=15; fontcolor="#334155"; color="#cbd5e1"; style="rounded";')
        for key in c["nodes"]:
            m = display_module(d, modules[key])
            state = data["statuses"][m["status"]]
            style = "rounded,filled,dashed" if m["status"] in ("PLAN", "WAIT") else "rounded,filled"
            lines.append(key + " [label=" + q(label(m, data)) + ', fillcolor=' + q(state["color"]) + ', color=' + q(state["border"]) + ', style=' + q(style) + "];")
        if d.get("column_layout"):
            for first, second in zip(c["nodes"], c["nodes"][1:]):
                lines.append(first + " -> " + second + " [style=invis, weight=100];")
        lines.append("}")
    if d.get("column_layout"):
        first_nodes = [c["nodes"][0] for c in d["clusters"]]
        # Do not chain these headers: Graphviz 2.43 can crash with newrank.
        lines.append("{rank=same; " + "; ".join(first_nodes) + ";}")
    for e in d["edges"]:
        attrs = ["label=" + q(e["label"])]
        if d.get("column_layout"):
            attrs.append("constraint=false")
        if e["kind"] in ("feedback", "reference", "planned"):
            attrs += ['style="dashed"', 'constraint=false']
        if e["kind"] == "planned":
            attrs.append('color="#94a3b8"')
        lines.append(e["from"] + " -> " + e["to"] + " [" + ", ".join(attrs) + "];")
    return "\n".join(lines + ["}", ""])


def mermaid_source(d, modules, data):
    lines = ["%% " + MARKER, "flowchart " + d["direction"]]
    for index, c in enumerate(d["clusters"]):
        lines.append('    subgraph section_' + str(index) + '["' + c["title"] + '"]')
        for key in c["nodes"]:
            text = label(display_module(d, modules[key]), data).replace('"', "'").replace("\n", "<br/>")
            lines.append('        ' + key + '["' + text + '"]')
        lines.append("    end")
    for e in d["edges"]:
        arrow = "-.->" if e["kind"] in ("feedback", "reference", "planned") else "-->"
        extra = '|' + e["label"].replace("|", "/") + '|' if e["label"] else ""
        lines.append("    " + e["from"] + " " + arrow + extra + " " + e["to"])
    for key in {n for c in d["clusters"] for n in c["nodes"]}:
        s = data["statuses"][display_module(d, modules[key])["status"]]
        lines.append("    style " + key + " fill:" + s["color"] + ",stroke:" + s["border"] + ",color:#0f172a")
    return "\n".join(lines) + "\n"


def render(data, modules):
    if not shutil.which("dot"):
        raise RuntimeError("Graphviz dot is needed for SVG/PNG/PDF export")
    rendered = []
    for d in data["diagrams"]:
        stem = OUT / "figures" / d["id"]
        write(stem.with_suffix(".dot"), dot_source(d, modules, data))
        write(stem.with_suffix(".mmd"), mermaid_source(d, modules, data))
        for fmt in ("svg", "png", "pdf"):
            result = subprocess.run(["dot", "-Gdpi=120", "-T" + fmt, str(stem.with_suffix(".dot")), "-o", str(stem.with_suffix("." + fmt))], capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(d["id"] + " format=" + fmt + " returncode=" + str(result.returncode) + ": " + result.stderr)
        svg = ET.parse(stem.with_suffix(".svg")).getroot()
        node_count = sum(1 for g in svg.iter() if g.attrib.get("class") == "node")
        expected = sum(len(c["nodes"]) for c in d["clusters"])
        if node_count != expected:
            raise ValueError("Rendered node mismatch: " + d["id"])
        raw = stem.with_suffix(".png").read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", raw[16:24])
        assert stem.with_suffix(".pdf").read_bytes().startswith(b"%PDF-")
        rendered.append({"id": d["id"], "nodes": node_count, "png_width": width, "png_height": height,
                         "graphviz_warnings": result.stderr.strip(), "formats": ["dot", "mmd", "svg", "png", "pdf"]})
    if shutil.which("pdfunite"):
        subprocess.run(["pdfunite"] + [str(OUT / "figures" / (d["id"] + ".pdf")) for d in data["diagrams"]] + [str(OUT / "framework_diagrams.pdf")], check=True, timeout=60, capture_output=True)
    return rendered


WP_MAP = {
    "A": ["platform", "dpu", "vsrv", "axi_commit clock_map", "axi_commit", "output_gate", "source_guard", "output_gate servo", "hardware_build implementation", "motion vsrv", "platform devices", "servo", "board_verify implementation", "release skill_a"],
    "B": ["cpu_vision person", "camera", "person model_build", "person", "tracking target", "snapshot", "face id_cpu id_dpu", "face identity", "identity", "enrollment identity", "scheduler", "target motion speaker", "datasets experiments", "release skill_b"],
    "C": ["devices avatar", "mcp_capture mcp_play", "mcp_capture mcp_play", "media_session transport", "asr vlm tts", "snapshot vlm", "media_session mcp_play", "ui avatar hdmi", "asd", "av_sync", "speaker", "devices fsm", "board_verify experiments", "release skill_c"]
}


def project_tables(data, modules):
    sources = json.loads((OUT / "requirement_sources.json").read_text(encoding="utf-8"))
    requirements = sources["official_mapping"]
    packages = []
    for original in sources["work_packages"]:
        key, title = original["id"], original["title"]
        ids = WP_MAP[key[0]][int(key[1:]) - 1].split()
        packages.append({"id": key, "title": title, "owner": key[0], "modules": " ".join(ids),
                         "current_evidence_levels": " / ".join(sorted({data["statuses"][modules[i]["status"]]["label"] for i in ids})),
                         "acceptance": "整项验收待复核；相关模块已有证据单独列出"})
    assert len(packages) == 42 and len({p["id"] for p in packages}) == 42
    cases = []
    for original in sources["acceptance_cases"]:
        key = original["id"]
        ids = [m["id"] for m in modules.values() if key in m["tests"]]
        cases.append({**original, "modules": " ".join(ids),
                      "status": "NOT_APPLICABLE_REMOVED" if key in ("T13", "T14") else "FINAL_UNIFIED_RELEASE_NOT_ACCEPTED"})
    assert len(cases) == 30 and len({p["id"] for p in cases}) == 30
    map_ids = {
        "r01": "platform", "r02": "hardware_build model_build reproduction", "r03": "release",
        "r04": "rtl_verify software_verify datasets", "r05": "implementation", "r06": "board_verify",
        "r07": "hardware_build model_build reproduction", "r08": "ai_records", "r09": "skill_a skill_b skill_c",
        "r10": "design_report", "r11": "experiments implementation", "r12": "reproduction",
        "r13": "release", "r14": "release", "r15": "skill_a", "r16": "design_report", "r17": "release"
    }
    notes = {
        "r01": "KV260/K26 参考已有；具体器件、队员最高学历及报名审核待确认",
        "r02": "采用已有 2022.2，须写明配套参考与选择理由；最终脚本从零执行待验",
        "r03": "已有源码建立目录映射；未来模块留位，不能把空位算完整工程",
        "r04": "现有框架测试与参考 RTL 测试分层；新期限监督和最终系统待验",
        "r05": "历史同片报告已有；最终新设计资源/时序/约束报告待补",
        "r06": "已有有限模块板测；最终统一工件、参考比对与整机实测待补",
        "r07": "旧构建与软件打包入口已有；最终硬件/模型/镜像构建待整合",
        "r08": "已有真实工程日志；原始可见交互与验证关联仍需整理",
        "r09": "三项 Skill 目录与说明框架已创建；完整脚本/失败/效果/外队复用待补",
        "r10": "本次创建全项目框图与报告框架；最终实验与结论待填",
        "r11": "G0–G5 定义已有；真实优化前后数据未完成",
        "r12": "核心软件新目录启动通过；非作者完整工程复现待完成",
        "r13": "按原文强烈要求准备开源与第三方许可；本次不发布仓库",
        "r14": "本次 submission/aura_junior 新文件使用英文路径；原开发目录另给对照",
        "r15": "可选加分方向，非当前必交；未经跨板验证不主张通用 PYNQ Skill",
        "r16": "决赛条件项；待入围和正式模板，不生成虚构队伍信息",
        "r17": "在线企业仓库入口可访问，指南 blob 未取到；没有确认更晚上传字段/时间"
    }
    for r in requirements:
        r["module_ids"] = map_ids[r["id"]]
        r["current_status"] = notes[r["id"]]
        r.pop("status", None)
    table(OUT / "work_packages.csv", packages, list(packages[0]))
    table(OUT / "acceptance_matrix.csv", cases, list(cases[0]))
    table(OUT / "requirements_matrix.csv", requirements, list(requirements[0]))
    table(OUT / "module_matrix.csv", [{**m, "status": data["statuses"][m["status"]]["label"], "existing": " ; ".join(m["existing"]), "tests": " ".join(m["tests"])} for m in modules.values()], list(data["modules"][0]))
    return packages, cases, requirements


def inventory(modules):
    result = subprocess.run(["rg", "--files", "--hidden", "-g", "!.venv/**", "-g", "!.git/**", "-g", "!.pytest_cache/**", "-g", "!**/__pycache__/**", "-g", "!report/architecture/**", "-g", "!submission/**"], cwd=ROOT, capture_output=True, text=True, check=True)
    rows = []
    for name in sorted(result.stdout.splitlines()):
        p = ROOT / name
        if p.is_file() and not p.is_symlink():
            rows.append({"path": name, "category": name.split("/")[0] if "/" in name else "root", "bytes": p.stat().st_size})
    table(OUT / "project_file_inventory.csv", rows, ["path", "category", "bytes"])
    references = []
    for m in modules.values():
        for name in m["existing"]:
            p = source_path(name)
            row = {"module": m["id"], "path": name, "exists": p.exists(), "kind": "directory" if p.is_dir() else "file",
                   "location": "external_ubuntu_reference" if Path(name).is_absolute() else "main_repository"}
            if p.is_file():
                row["bytes"] = p.stat().st_size
                if row["bytes"] <= 1024 * 1024:
                    row["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            references.append(row)
    dump(OUT / "source_references.json", references)
    return {"main_repository_files_listed": len(rows), "declared_source_references": len(references),
            "external_references_embedded": False, "inventory_scope": "FILENAMES_AND_SIZES_EXCLUDING_ENVIRONMENTS_CACHES_AND_GENERATED_ARCHITECTURE"}


def scaffold(data, modules, packages, cases, requirements):
    intro = "<!-- " + MARKER + " -->\n"
    locations = {
        "src": "实际采用的 RTL、PS、主机和 UI 源码；当前按 source_references.json 回收，开发仍在原主仓。",
        "sim": "自检查 RTL 仿真、软件验证、输入/预期/实际、失败波形；新源期限监督验证尚待执行。",
        "build": "固定版本构建脚本、综合/实现报告与模型量化编译记录；参考工程不等于最终工件。",
        "board": "匹配固件、部署/运行脚本、平台清单、实际输出与参考比对；本次不连接设备。",
        "data": "标定、独立测试、黄金参考及原始指标；合成小样与真实场景数据分别标注。",
        "skill": "三个比赛技能包的适用范围、步骤、失效条件、真实失败与已验证效果；不是插件安装。",
        "report": "设计报告、功能框图、软硬件接口、优化对照、AI 协作和从零复现材料。"
    }
    for name, meaning in locations.items():
        write(STAGE / name / "README.md", intro + "# " + name + "\n\n" + meaning + "\n\n本目录目前是完整参赛框架位置，待按实际版本填入最终交付材料。参见根目录 README.md 的源码位置与证据范围。\n")
    for m in modules.values():
        folder = STAGE / m["planned_path"]
        sources = "\n".join("- `" + p + "`" for p in m["existing"]) or "- 尚无实现；仅预留结构。"
        text = (intro + "# " + m["name"] + "\n\n模块：" + m["group"] + " / `" + m["id"] + "`；负责人：" + m["owner"] + "；目标位置：" + m["placement"] + "。\n\n"
                + "当前证据层级：**" + data["statuses"][m["status"]]["label"] + "**。\n\n输入：" + m["input"] + "。\n输出：" + m["output"] + "。\n\n"
                + "现有源码/证据来源：\n\n" + sources + "\n\n待补：" + m["remaining"] + "。\n\n"
                + "关联内部验收：" + ("、".join(m["tests"]) or "后续扩展单独定义") + "。\n\n"
                + "这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。\n")
        write(folder / "README.md", text)
        dump(folder / "interface.json", {"schema_version": "aura-module-description-1", "module_id": m["id"], "input_description": m["input"],
                                          "output_description": m["output"], "description_is_not_frozen_runtime_abi": True,
                                          "evidence_status": m["status"], "remaining": m["remaining"], "existing_sources": m["existing"]})
    manifest = {"schema_version": "aura-junior-submission-framework-1", "status": "FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE",
                "source_repository": "../..", "module_count": len(modules), "physical_actuation_enabled": False,
                "board_model_exact_part": None, "team_eligibility_verified": False, "final_release_id": None,
                "final_hardware_hash": None, "final_model_hashes": [], "reproduction_by_non_author": False,
                "modules": list(modules.values()), "excluded": data["excluded"]}
    dump(STAGE / "manifest.json", manifest)
    dump(STAGE / "board/manifest.json", {"status": "FINAL_UNIFIED_RELEASE_PENDING", "physical_actuation_enabled": False,
                                         "reference_manifest": "../../../hardware/platform/platform_manifest.json",
                                         "current_board_identity": None, "actual_pin_map": None, "new_source_deadline_supported": False})
    for name in ("work_packages.csv", "acceptance_matrix.csv", "requirements_matrix.csv", "module_matrix.csv", "source_references.json", "provenance.json"):
        shutil.copyfile(OUT / name, STAGE / "report" / name)
    figure_folder = STAGE / "report/figures"
    figure_folder.mkdir(parents=True, exist_ok=True)
    report_index = intro + "# 设计报告与完整功能框图\n\n本目录已经包含全部框图及可编辑源；实际实验结论与最终整机交付仍待完成。\n\n"
    report_index += "[设计报告框架](design_report.md) · [接口说明](interface_contracts.md) · [AI 协作记录](ai_collaboration.md) · [从零复现框架](reproducibility.md)\n\n"
    if (OUT / "framework_diagrams.pdf").exists():
        shutil.copyfile(OUT / "framework_diagrams.pdf", STAGE / "report/framework_diagrams.pdf")
        report_index += "[八页 PDF 图册](framework_diagrams.pdf)\n\n"
    for d in data["diagrams"]:
        for fmt in ("dot", "mmd", "svg", "png", "pdf"):
            name = d["id"] + "." + fmt
            shutil.copyfile(OUT / "figures" / name, figure_folder / name)
        report_index += "## " + d["title"] + "\n\n" + d["subtitle"] + "。\n\n![" + d["title"] + "](figures/" + d["id"] + ".svg)\n\n"
        report_index += "源文件：`figures/" + d["id"] + ".dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。\n\n"
    write(STAGE / "report/README.md", report_index)
    templates = {
        "design_report.md": "report/design_report.md",
        "interface_contracts.md": "report/interface_contracts.md",
        "reproducibility.md": "report/reproducibility.md",
        "ai_collaboration.md": "report/ai_collaboration.md",
        "optimization_results.csv": "data/metrics/optimization_results.csv",
        "build_plan.json": "build/build_plan.json",
        "skill_index.md": "skill/README.md",
        "skill_command_guard.md": "skill/command-guard-validation/README.md",
        "skill_freshness.md": "skill/perception-freshness-benchmark/README.md",
        "skill_async.md": "skill/async-result-validation/README.md"
    }
    for source, destination in templates.items():
        write(STAGE / destination, (OUT / "templates" / source).read_text(encoding="utf-8"))
    index = intro + "# AURA·汐蓝自主选题初级组提交框架\n\n此目录按官方推荐的 `src/sim/build/board/data/skill/report` 建立，覆盖 M1–M8、全部 42 工作包和 T01–T30，含当前未做模块。状态是 **FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE**。\n\n"
    index += "先看 [目录细分与依据](report/structure_detail.html) 和 [完整结构说明](report/structure_detail.md)，包含目录职责、共享资源所有者、原 I01–I07、现有源码及静态依赖。\n\n本目录内的完整框图：[报告与框图](report/README.md) · [八页 PDF](report/framework_diagrams.pdf)。主开发仓的交互入口：[图册与状态页](../../report/architecture/index.html)。目录和源码映射见本目录 `manifest.json`、`report/module_matrix.csv` 与 `report/source_references.json`。\n\n"
    index += "开发目录与目标交付职责对照（不按旧文件夹名称机械搬迁）：\n\n| 目标位置 | 现有开发来源 / 边界 |\n|---|---|\n| src/shared | common；host/model_service/protocol.py 等双端合同 |\n| src/rtl | hardware/rtl 中旧 VSRV 参考；新运动监督待实现 |\n| src/platform | 原 FPGA 工程的官方 DPU 集成、BD/XDC、系统配置输入 |\n| src/ps | board 中板端业务；host/model_service/client.py 实际也是板端客户端 |\n| src/host | host 中模型流水线；board/runtime/audio/selected_voice.py 等主机模型代码 |\n| src/ui | board/interaction 与选定 PC 基线；ui JSON/素材归 data/assets |\n| src/config / src/third_party | config 与固定依赖/来源/许可；最终版本待逐项核对 |\n| sim | tests 与原 RTL testbench；软件监督实现本身在 src/ps/motion |\n| build | 构建与打包脚本、工具锁和实现报告；原绝对路径脚本仍需参数化 |\n| board | 匹配部署工件、运行脚本和板测证据；不是主仓 board 源码的直接副本 |\n| data | 标定/独立测试/黄金参考、模型、素材、分析；原始板测按 run_id 引用 |\n| skill | 三个当前预留技能目录及已有验证代码 |\n| report | 框图、接口登记、矩阵、报告、协作和复现记录 |\n\n"
    index += "本次没有搬走或覆盖既有工程；源码引用分为主仓相对位置和 Ubuntu 外部来源。最终发布时回收经核验源码与许可允许的资源，固定版本和哈希；不依赖开发者个人绝对路径。\n\n"
    index += "现有 Python 导入与配置/素材路径依赖原包结构；src/ps 等是目标职责位置。真正重排源文件前必须解决包入口与资源定位，并执行隔离复现，不能把目录框架称为可运行的最终源码副本。\n\n"
    index += "三包是比赛 Skill 的说明/接口位置，完整脚本、真实失败、验证效果和非作者复用尚待补齐；未创建 Codex 自动执行技能。PYNQ 适配为可选，不改变既定 Linux/DPU 路线。机构标定等待 3D 模型。\n"
    write(STAGE / "README.md", index)


def md_docs(data, modules, packages, cases, requirements):
    lines = ["<!-- " + MARKER + " -->", "# AURA·汐蓝完整竞赛框图与提交框架", "",
             "日期：2026-10-09。范围是初级组自主选题整件作品，包含当前已做与未做内容。图表示最终目标结构，每个框明确证据层级。", "",
             "入口：[离线图册与可筛选状态](index.html)；[目录细分与依据](structure_detail.html)；[完整结构说明](structure_detail.md)。图册 PDF：`framework_diagrams.pdf`（本机支持合并时生成）。", "",
             "## 官方依据与范围", "",
             "以资料包内 AMD 2026 指南 PDF 第 22–25 页 / 第 3.3 节为依据；设计报告第 3.3.5.3 要求功能框图、软硬件划分、接口、优化对照、AI 协作、Skill 与复现。工程包另需源码、验证、综合实现、上板与构建脚本。", "",
             "[企业赛道入口](https://gitee.com/Vickyiii/fpgachina26-amd)已在线定位；分赛道指南正文抓取失败。本次不推断更晚上传字段、截止日期或报告页数。官方原件在用户资料 ZIP 内，规则与计划来源的哈希见 `provenance.json`，源码与实测引用见 `source_references.json`。", "",
             "`src/sim/build/board/data/skill/report` 是官方推荐组织；采用其他结构要给目录对照。新提交框架使用英文文件名，旧开发资料保留原件。2022.2 的采用理由须写明并实际复现；不额外要求迁移 PYNQ、HLS 或其他赛道 AI PC。", "",
             "## 状态图例", "", "| 图中状态 | 实际含义 |", "|---|---|"]
    lines += ["| " + s["label"] + " | " + s["note"] + " |" for s in data["statuses"].values()]
    lines += ["", "## 八张框图", ""]
    for d in data["diagrams"]:
        lines += ["### " + d["title"], "", d["subtitle"] + "。", "", "![" + d["title"] + "](figures/" + d["id"] + ".svg)", "", "可编辑源：`figures/" + d["id"] + ".dot` / `.mmd`；另有 `.png` 与 `.pdf`。", ""]
    lines += ["## 全部模块的对应位置", "", "| ID | 模块 / 负责人 | 当前层级 | 提交位置 | 待完成内容 |", "|---|---|---|---|---|"]
    for m in modules.values():
        lines.append("| " + m["group"] + "/" + m["id"] + " | " + m["name"] + " / " + m["owner"] + " | " + data["statuses"][m["status"]]["label"] + " | `" + m["planned_path"] + "` | " + m["remaining"] + " |")
    lines += ["", "## 工作包、验收与正式提交对应", "", "- `work_packages.csv`：原三人总包全部 42 项，挂接到当前框图模块；整项放行尚待复核。",
              "- `acceptance_matrix.csv`：当前无声源定位方案全部 T01–T30；目标是内部验收建议，不是官方阈值。T13/T14 保留并明确不适用。",
              "- `requirements_matrix.csv`：r01–r17 对应官方工程包、Skill、报告、版本、开源、命名与条件项。",
              "- `project_file_inventory.csv`：现有主仓文件名/大小清单，排除环境/缓存与本次生成框图。",
              "- `source_references.json`：每个模块的现有来源是否存在、主仓/Ubuntu 位置、小文件 SHA。",
              "- `../../submission/aura_junior/`：七个官方推荐目录、每个模块的 README 与接口说明、未完成工件清单。", "",
              "## 尚未完成的内容已放在哪里", "",
              "新 DPU 检测/身份、ByteTrack 实际运行、真实质量/登记页、MCP01 采录播放、跨机媒体、ASD 同窗和模型、新 PL 绝对期限/时钟映射/ABI、仪器波形、机构标定、G0–G5 实验、三项完整 Skill、最终报告/视频/从零复现均已画出并建立目录位置。", "",
              "当前 CPU 人脸/IoU、SFace 静态参考、DPU+相对租约有限共存、HDMI、汐蓝 PC 素材/声线分别引用已有证据；本次没有重新运行这些板测或 Windows 模型。新运行时的 41 项软件测试属于此前软件框架验证。", "",
              "机构继续等待 3D 模型。本次只读取资料并生成图、矩阵、说明与目录，没有硬件操作。已有相对租约 RTL 不被标成新的源绝对期限 RTL。", "",
              "## 维护与导出", "", "```bash", "python3 -s scripts/render_submission_architecture.py", "```", "",
              "修改 `report/architecture/architecture.json` 后再导出；这是所有图、模块表和目录接口说明共同的来源。原方案、原源码和实测记录保持可追溯。生成器拒绝覆盖未标记的 Markdown/HTML 文档。"]
    write(OUT / "framework.md", "\n".join(lines) + "\n")


def html_page(data, modules, packages, cases, requirements):
    esc = html.escape
    intro = '<!-- ' + MARKER + ' -->'
    style = """body{margin:0;font:15px/1.7 'Noto Sans CJK SC','Microsoft YaHei',sans-serif;background:#f6f8fb;color:#182338}header,main{max-width:1440px;margin:auto;padding:30px}header{padding-bottom:12px}h1{font-size:30px;margin:0}h2{font-size:21px}p{max-width:1050px}nav{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}a{color:#1d4ed8}nav a,.tag{padding:5px 10px;border-radius:6px;background:white;border:1px solid #dae0e9}section{background:white;border:1px solid #d9e1ec;border-radius:12px;padding:24px;margin:22px 0}.figure{overflow:auto;border:1px solid #e2e8f0;background:white;padding:12px;max-height:760px}.figure svg{display:block;width:100%;height:auto;min-width:1000px}button,input,select{font:inherit;padding:6px 10px;border:1px solid #cbd5e1;border-radius:5px;background:white}.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:12px 0}.tags{display:flex;gap:10px;flex-wrap:wrap}.tag{border-width:2px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;vertical-align:top;border-bottom:1px solid #e2e8f0}th{background:#f1f5f9;position:sticky;top:0}code{font-size:12px;overflow-wrap:anywhere}details{margin:4px 0}.status{white-space:nowrap;font-weight:600}.meta{color:#526174}.stats{display:flex;gap:22px;flex-wrap:wrap}.stats b{font-size:24px}.print{margin-left:auto}@media print{body{background:white}header,main{padding:0}nav,.controls{display:none}section{break-before:page;border:0;padding:0}.figure{overflow:visible;max-height:none;border:0}.figure svg{min-width:0;width:100%}.scroll{overflow:visible}th{position:static}}"""
    page = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>", intro,
            "<title>AURA·汐蓝完整参赛框架图</title><style>" + style + "</style><body><header><h1>AURA·汐蓝 · 完整参赛框架图</h1>",
            "<p>AMD 自主选题初级组 · 2026-10-09 · 以整个作品的提交要求组织已有成果、待实现模块与验证材料。</p>",
            "<p class='meta'>图中的连线表示最终目标数据流。颜色与文字状态标记当前证据层级；框图完整不代表所有功能已完成。单独框架包含图册与目录说明，已有源码链接需在原主仓内使用。</p>",
            "<div class='stats'><span><b>8</b> 核心模块</span><span><b>" + str(len(modules)) + "</b> 模块位置</span><span><b>" + str(len(data["diagrams"])) + "</b> 框图</span><span><b>42</b> 工作包</span><span><b>30</b> 内部验收项</span><span><b>17</b> 提交对应项</span></div><nav>"]
    for d in data["diagrams"]:
        page.append('<a href="#' + d["id"] + '">' + esc(d["title"]) + '</a>')
    page += ['<a href="structure_detail.html">目录细分与依据</a><a href="#modules">模块与目录</a><a href="#requirements">官方提交对应</a><a href="#work">三人工作包</a><a href="#tests">验收</a><a href="framework.md">完整说明</a><a href="framework_diagrams.pdf">PDF 图册</a></nav><div class="tags">']
    for s in data["statuses"].values():
        page.append('<span class="tag" style="background:' + s["color"] + ';border-color:' + s["border"] + '">' + esc(s["label"]) + '</span>')
    page += ['</div></header><main>']
    for d in data["diagrams"]:
        svg = (OUT / "figures" / (d["id"] + ".svg")).read_text(encoding="utf-8")
        svg = svg[svg.index("<svg"):]
        svg = re.sub(r'\bid="([^"]+)"', lambda match: 'id="' + d["id"] + '_' + match.group(1) + '"', svg)
        page += ['<section id="' + d["id"] + '"><h2>' + esc(d["title"]) + '</h2><p>' + esc(d["subtitle"]) + '</p>',
                 '<div class="controls"><button onclick="zoom(this,1.25)">放大</button><button onclick="zoom(this,0.8)">缩小</button><button onclick="resetZoom(this)">适合页面</button>']
        for fmt in ("svg", "png", "pdf", "dot", "mmd"):
            page.append('<a href="figures/' + d["id"] + '.' + fmt + '" target="_blank" rel="noopener">' + fmt.upper() + '</a>')
        page += ['</div><div class="figure">' + svg + '</div></section>']
    page += ['<section id="modules"><h2>全部模块、已有源码与未做内容</h2><div class="controls"><input id="query" placeholder="搜索模块、负责人、代码或待做内容" oninput="filterModules()"><select id="state" onchange="filterModules()"><option value="">全部状态</option>']
    for key, s in data["statuses"].items():
        page.append('<option value="' + key + '">' + esc(s["label"]) + '</option>')
    page += ['</select><a href="module_matrix.csv">模块 CSV</a><a href="project_file_inventory.csv">现有文件清单</a><a href="../../submission/aura_junior/README.md">提交目录</a></div><div class="scroll"><table><thead><tr><th>模块</th><th>位置 / 负责人</th><th>当前状态</th><th>输入 → 输出</th><th>已有来源</th><th>框架位置 / 尚未完成</th></tr></thead><tbody>']
    for m in modules.values():
        state = data["statuses"][m["status"]]
        search = json.dumps(m, ensure_ascii=False)
        page.append('<tr class="module-row" data-state="' + m["status"] + '" data-search="' + esc(search, quote=True) + '"><td><b>' + m["group"] + ' / ' + esc(m["id"]) + '</b><br>' + esc(m["name"]) + '</td><td>' + esc(m["placement"]) + '<br>' + esc(m["owner"]) + '</td><td class="status" style="color:' + state["border"] + '">' + esc(state["label"]) + '</td><td>' + esc(m["input"]) + '<br>↓<br>' + esc(m["output"]) + '</td><td>')
        for name in m["existing"]:
            if Path(name).is_absolute():
                page.append('<details><summary>Ubuntu 原件</summary><code>' + esc(name) + '</code></details>')
            else:
                page.append('<div><a href="../../' + quote(name, safe="/") + '"><code>' + esc(name) + '</code></a></div>')
        page.append('</td><td><a href="../../submission/aura_junior/' + m["planned_path"] + '/README.md"><code>' + esc(m["planned_path"]) + '</code></a><p>' + esc(m["remaining"]) + '</p></td></tr>')
    page += ['</tbody></table></div></section><section id="requirements"><h2>官方提交要求与当前对应</h2><p>来源为用户资料包 AMD 2026 指南第 3.3 节与原提交矩阵。<a href="https://gitee.com/Vickyiii/fpgachina26-amd">企业赛道入口</a>；未据此补造更晚上传字段、时间或统一 FPS 阈值。</p><a href="requirements_matrix.csv">CSV</a><div class="scroll"><table><tr><th>ID / 条款</th><th>要求与强度</th><th>当前对应</th></tr>']
    for r in requirements:
        page.append('<tr><td>' + r["id"] + '<br>' + esc(r["source_section"]) + '</td><td>' + esc(r["requirement"]) + '<br>' + esc(r["strength"]) + '</td><td>' + esc(r["current_status"]) + '</td></tr>')
    page += ['</table></div></section><section id="work"><h2>A / B / C 共 42 工作包</h2><p>原 10 月 2 日总包标题原样挂接；整项验收需要最终证据，不按相关文件存在就标完成。</p><a href="work_packages.csv">CSV</a><div class="scroll"><table><tr><th>编号</th><th>任务</th><th>当前关联模块</th><th>证据层级</th></tr>']
    for p in packages:
        page.append('<tr><td>' + p["id"] + '</td><td>' + esc(p["title"]) + '</td><td><code>' + p["modules"] + '</code></td><td>' + esc(p["current_evidence_levels"]) + '</td></tr>')
    page += ['</table></div></section><section id="tests"><h2>T01–T30 内部验收框架</h2><p>这些目标来自现行项目方案，是内部建议，不能写成官方统一标准或已有成绩。T13/T14 保留删除说明；其余全部仍待最终统一版本验收。</p><a href="acceptance_matrix.csv">CSV</a><div class="scroll"><table><tr><th>ID / 测试</th><th>内部目标</th><th>要保留的证据</th></tr>']
    for c in cases:
        page.append('<tr><td>' + c["id"] + ' / ' + esc(c["test"]) + '</td><td>' + esc(c["internal_target_not_official"]) + '</td><td>' + esc(c["required_evidence"]) + '</td></tr>')
    page += ['</table></div></section><p>机构按用户安排等待 3D 模型。本次是资料、图与目录搭建；没有访问板卡、启动真实模型、输出舵机动作或发布网站。</p></main>',
             "<script>function zoom(b,f){let s=b.closest('section').querySelector('svg');s.style.width=(parseFloat(s.style.width)||100)*f+'%'}function resetZoom(b){b.closest('section').querySelector('svg').style.width='100%'}function filterModules(){let q=document.getElementById('query').value.toLowerCase(),s=document.getElementById('state').value;document.querySelectorAll('.module-row').forEach(r=>r.hidden=!(r.dataset.search.toLowerCase().includes(q)&&(!s||r.dataset.state===s)))}</script></body></html>"]
    write(OUT / "index.html", "".join(page))


def main():
    parser = argparse.ArgumentParser(description="生成完整初级组参赛框图、模块矩阵与目录位置")
    parser.add_argument("--bundle", action="store_true", help="另外打包本次框架材料，不是最终工程发布")
    args = parser.parse_args()
    data = json.loads((OUT / "architecture.json").read_text(encoding="utf-8"))
    modules = validate(data)
    rendered = render(data, modules)
    packages, cases, requirements = project_tables(data, modules)
    inventory_result = inventory(modules)
    scaffold(data, modules, packages, cases, requirements)
    md_docs(data, modules, packages, cases, requirements)
    html_page(data, modules, packages, cases, requirements)
    structure_process = subprocess.run([sys.executable, "-s", str(ROOT / "scripts/render_structure_review.py")],
                                       capture_output=True, text=True, timeout=60)
    if structure_process.returncode:
        raise RuntimeError("Structure review failed: " + structure_process.stderr)
    structure_result = json.loads(structure_process.stdout)
    paths = [p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()]
    assert all(all(part == "README.md" or re.fullmatch(r"[a-z0-9_.-]+", part) for part in Path(p).parts) for p in paths)
    assert all((STAGE / m["planned_path"] / "README.md").is_file() for m in modules.values())
    result = {"schema_version": "aura-architecture-export-validation-1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "passed": True, "modules": len(modules), "core_groups": 8, "diagrams": len(rendered),
              "work_packages": len(packages), "acceptance_cases": len(cases), "official_mapping_rows": len(requirements),
              "all_modules_represented_in_figures": True, "all_declared_sources_exist": True,
              "all_module_slots_created": True, "submission_paths_use_english": True, "stage_file_count": len(paths),
              "inventory": inventory_result, "rendered": rendered, "structure_review": structure_result, "physical_actuation": False,
              "scope": "ARCHITECTURE_AND_SUBMISSION_FRAMEWORK_NOT_RUNTIME_OR_BOARD_ACCEPTANCE"}
    dump(OUT / "export_validation.json", result)
    if args.bundle:
        destination = ROOT / "artifacts/releases"
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / ("aura-junior-architecture-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6] + ".zip")
        bundle_files = [p for folder in (OUT, STAGE) for p in folder.rglob("*") if p.is_file() and p != OUT / "bundle_result.json"]
        bundle_files.append(Path(__file__).resolve())
        bundle_files.append(ROOT / "scripts/render_structure_review.py")
        hashes = []
        with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(bundle_files):
                relative = p.relative_to(ROOT).as_posix()
                raw = p.read_bytes()
                archive.writestr("aura/" + relative, raw)
                hashes.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            archive.writestr("aura/architecture_bundle_manifest.json", json.dumps({"scope": "ARCHITECTURE_FRAMEWORK_NOT_FINAL_SOURCE_PACKAGE", "files": hashes}, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(path) as archive:
            assert len(archive.namelist()) == len(hashes) + 1
            for entry in hashes:
                raw = archive.read("aura/" + entry["path"])
                assert len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"]
        result["bundle"] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
                            "files_verified": len(hashes), "contains_full_source_or_firmware": False}
        dump(OUT / "bundle_result.json", result["bundle"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
