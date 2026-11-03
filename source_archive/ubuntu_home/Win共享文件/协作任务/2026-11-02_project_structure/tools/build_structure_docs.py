#!/usr/bin/env python3
"""Generate design catalog and validate this document, without reading a code archive."""

import csv
import hashlib
import io
import json
import re
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "project_structure.md"
GUIDE = Path("/home/ghmd/Win共享文件/参赛资料/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf")
UPLOAD = Path("/home/ghmd/下载/2026FPGA创新设计赛道作品上传要求.pdf")
PROJECT_ZIP = Path("/home/ghmd/下载/项目.zip")


REQUIREMENTS = [
    ("r01", "初级组资格与队伍最高年级", "3.3.1.1", "22", "官方要求", "README.md;docs/feature_scope.md", "声明报名组别；人员资格按后台审核，目录不证明资格"),
    ("r02", "目标器件具体型号与实际可板测的平台", "3.3.3.2", "23", "官方要求", "hardware/bom.csv;build/manifests/platform.json;docs/hardware.md", "填写最终实物型号、revision 和验证条件"),
    ("r03", "实际采用的 RTL、HLS、PS 源码与完整工程", "3.3.5.1", "24", "官方要求", "src/fpga/;src/kv260/;src/windows/;src/common/;third_party/", "Windows 是本作品实际组成；HLS 只在确实采用时提供"),
    ("r04", "仿真或验证结果及功能正确性依据", "3.3.5.1", "24", "官方要求", "sim/;tests/;data/reference/;board/evidence/", "分别保留 RTL、软件、模型、板端与实物验证范围"),
    ("r05", "综合实现与资源报告", "3.3.5.1", "24", "官方要求", "build/reports/baseline/synthesis.rpt;build/reports/baseline/utilization.rpt", "原始工具报告与构建输入、build_id 绑定"),
    ("r06", "时钟频率、时序和关键性能指标", "3.3.5.1", "24", "官方要求", "build/reports/baseline/timing_summary.rpt;build/reports/baseline/clocks.rpt;report/metrics.csv", "区分实际频率、setup/hold、应用指标及其条件"),
    ("r07", "上板工程、运行脚本与实测输出", "3.3.3.2;3.3.5.1", "23-24", "官方要求", "board/firmware/;board/scripts/;board/config/;board/evidence/", "固件和软件必须配套；保存实际加载与运行记录"),
    ("r08", "实测结果与参考结果比对", "3.3.5.1", "24", "官方要求", "data/input/;data/reference/;data/results/baseline/comparison.csv", "固定输入、参考来源、误差容限和失败样例"),
    ("r09", "可复现构建脚本", "3.3.5.1", "24", "官方要求", "build/scripts/;build/manifests/dependency_sources.json;docs/reproduction.md", "包含必要 IP/参考输入、固定来源与 SHA，避免只引用旧电脑路径"),
    ("r10", "其他工具版本说明与脚本复现", "3.3.3.1", "23", "官方要求", "docs/platform_lock.md;build/manifests/toolchain.json", "采用 2022.2 时说明配套原因和实测环境，不宣称必须升级"),
    ("r11", "真实大模型协作问答和自我纠错", "3.3.3.1;3.3.5.3", "23-24", "官方要求", "report/ai_collaboration/raw/;report/ai_collaboration/prompts.md;report/ai_collaboration/responses.md;report/ai_collaboration/corrections.md", "保留原始提示、回答与修正来源；缺失明确登记"),
    ("r12", "提炼并提交可复用 Skill", "3.3.3.1;3.3.5.2", "23-24", "官方要求", "skill/README.md;skill/command_guard_validation/;skill/dpu_workflow_validation/;skill/voice_runtime_optimization/", "至少有实际可复用内容；三主题是本方案建议，非官方数量要求"),
    ("r13", "Skill 适用范围、用法和失效条件", "3.3.5.2", "24", "官方要求", "skill/README.md;skill/command_guard_validation/readme.md;skill/dpu_workflow_validation/readme.md;skill/voice_runtime_optimization/readme.md", "逐项写前提、输入、操作、输出、失败与边界"),
    ("r14", "Skill 真实失败来源和已验证效果", "3.3.5.2", "24", "官方要求", "skill/command_guard_validation/case_studies.md;skill/command_guard_validation/evidence/;skill/dpu_workflow_validation/evidence/;skill/voice_runtime_optimization/evidence/", "公开小样、反例、原始日志和复用条件；不把模拟写成真板"),
    ("r15", "设计报告：选题背景、应用与创新", "3.3.5.3", "24", "官方要求", "report/design_report.md;report/design_report.pdf", "实际问题、相关工作、差异和证据"),
    ("r16", "设计报告：原理与功能框图", "3.3.5.3", "24", "官方要求", "report/figures/system_architecture.svg;report/figures/fpga_architecture.svg;report/design_report.md", "标明 PS/PL/Windows 和真实数据流"),
    ("r17", "设计报告：软硬件划分与接口", "3.3.5.3", "24", "官方要求", "docs/architecture.md;docs/protocol.md;docs/motion_contract.md;src/common/", "解释划分依据、数据格式、时钟、期限和错误"),
    ("r18", "设计报告：优化前后性能和资源对照", "3.3.4;3.3.5.3", "23-24", "官方要求", "data/results/;report/metrics.csv;docs/measurement_methods.md", "同条件基线、原始数据、统计与判断依据"),
    ("r19", "设计报告：AI 协作和智能体工作流（如有）", "3.3.5.3", "24", "官方要求", "report/ai_collaboration/;report/design_report.md", "智能体流程只在实际使用时说明；问答须真实"),
    ("r20", "设计报告：Skill 提炼、验证与边界", "3.3.5.3", "24", "官方要求", "skill/;report/ai_collaboration/case_index.csv;report/design_report.md", "将失败观察、代码修正、验证和 Skill 对应起来"),
    ("r21", "设计报告：他人从零复现步骤", "3.3.4;3.3.5.3", "23-24", "官方要求", "README.md;docs/reproduction.md;docs/windows_setup.md;docs/kv260_setup.md", "包括源码取得、依赖、模型、构建、部署、运行、结果和局限"),
    ("r22", "英文文件/目录命名与目录对照", "3.3.5.4", "24-25", "命名有要求；结构为推荐", "README.md;tools/validate_layout.py", "自建路径采用英文小写数字下划线/连字符；README.md 沿用官方示例"),
    ("r23", "GitHub/Gitee 开源及允许再分发的许可", "3.3.3.3", "23", "原文强烈要求", "license;third_party_notices.md;third_party/manifest.csv;report/submission/repository.txt", "确定原创许可范围，保留上游声明并提供固定 tag/commit"),
    ("r24", "PYNQ 实现路线", "3.3.2", "22-23", "推荐；非强制", "docs/feature_scope.md;docs/platform_lock.md", "无须为初级组改写现有 Linux/RTL 路线"),
    ("r25", "通用 PYNQ Skill", "3.3.2;3.3.5.2", "22-24", "可选加分", "skill/pynq_contract_testgen/", "实际提交才建设，模拟/真板/跨板/他人复用分开"),
    ("r26", "一页英文 AMD 模板海报和 A4 彩印", "第六部分", "28", "进入决赛后的条件要求", "report/poster/poster_en.pptx;report/poster/poster_en.pdf", "按 AMD 模板，不含队伍信息；初赛上传字段另核对"),
    ("u01", "作品视频格式与内容", "作品上传要求第一项", "1", "上传要求", "report/demo/demo.mp4;report/demo/storyboard.md;report/submission/checklist.csv", "MP4/AVC(H264)，建议3分钟内、300M内，以真实作品演示为重点"),
    ("u02", "设计报告格式、模板和体积", "作品上传要求第二项", "1", "上传要求", "report/design_report.docx;report/design_report.pdf;report/submission/checklist.csv", "PDF/50M内，按实际上传页模板组织，单栏时合并 AMD 补充"),
    ("u03", "全部代码压缩格式与体积", "作品上传要求第三项", "1", "上传要求", "tools/export_submission.py;report/submission/checklist.csv;checksums.sha256", "导出工程外的 RAR，200M内；所列工具是待实现设计"),
    ("u04", "作品承诺及使用授权书", "作品上传要求第四项", "1", "上传要求", "report/submission/authorization_template.pdf;report/submission/readme.md", "下载官方表单并签署；签名等个人信息另行交付"),
    ("u05", "工程仓库链接", "作品上传要求第五项", "1", "按企业要求开源", "report/submission/repository.txt;license;third_party_notices.md", "后台原文为 github 链接，实际字段与所选企业指南核对"),
    ("u06", "作品全局和开发板高清照片", "作品上传要求第六项", "2", "上传要求", "report/photos/overall_front.jpg;report/photos/board_closeup.jpg", "提供真实实物；角色渲染图和电路示意不能替代"),
    ("u07", "作品海报", "作品上传要求第七项", "2", "按企业要求", "report/poster/;report/submission/checklist.csv", "结合 AMD 决赛条件与后台实际通知"),
    ("u08", "截止和最终提交回执", "作品上传要求第八项;指南3.3.6", "2;25", "以后续公告和后台为准", "report/submission/checklist.csv;report/submission/readme.md", "上传原件列2026-11-04 18时，未注明时区；提交后才填写回执"),
    ("p01", "本作品电气、供电与机械资料", "工程完整性；赛事技术文档实际需要", "", "本项目整理建议", "hardware/;report/photos/;docs/hardware.md", "不是所有作品都必须设计 PCB；保留实际做过的电路和机构原件"),
    ("p02", "本作品模型、素材和运行环境闭包", "工程完整性和从零复现", "", "本项目整理建议", "models/;assets/;third_party/;board/system/;config/", "完整输入、来源和校验；LLM权重继续放共享目录外"),
    ("p03", "完整工程与公开个人运行数据分开", "本地共享目录规则；交付边界", "", "本项目整理约定", ".gitignore;docs/runtime_layout.md;docs/reproduction.md", "代码/迁移/公开样例入档，个人SQLite/模板/录音与密钥留本设备"),
]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    document = DOC.read_text(encoding="utf-8")
    trees = re.findall(r"```text\n(.*?)\n```", document, re.S)
    assert len(trees) == 4, "expected project, kv260, windows and delivery trees"
    tree = trees[0]
    assert tree.splitlines()[0] == "auar_xuefei/"
    rows = []
    stack = []
    pattern = re.compile(r"^((?:│   |    )*)(?:├── |└── )(.*)$")
    for line in tree.splitlines()[1:]:
        if line.replace("│", "").strip() == "":
            continue
        match = pattern.fullmatch(line)
        assert match, "unparsed tree line: " + line
        level = len(match.group(1)) // 4
        content = match.group(2)
        parts = re.split(r"\s+#\s*", content, maxsplit=1)
        item = parts[0].strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        assert level <= len(stack), "indentation skipped parent: " + line
        stack = stack[:level]
        directory = item.endswith("/")
        name = item.rstrip("/")
        path = "/".join(stack + [name]) + ("/" if directory else "")
        condition = "按实际采用" if "[条件]" in description else "按最终实现整理"
        rows.append({
            "path": path,
            "type": "目录" if directory else "文件",
            "subsystem": path.split("/")[0],
            "purpose": description or "见所属子系统说明；按实际实现填写",
            "condition": condition,
            "state": "设计项；本次未创建业务内容",
        })
        if directory:
            stack.append(name)

    paths = {r["path"] for r in rows}
    assert len(paths) == len(rows), "duplicate project path"
    special_names = []
    non_ascii = []
    for row in rows:
        for part in row["path"].rstrip("/").split("/"):
            if not part.isascii():
                non_ascii.append(row["path"])
            if part != "README.md" and not re.fullmatch(r"[a-z0-9_.-]+", part):
                special_names.append(row["path"])
        parent_parts = row["path"].rstrip("/").split("/")[:-1]
        if parent_parts:
            assert "/".join(parent_parts) + "/" in paths
    assert not non_ascii and not special_names
    required_top = ["src/", "sim/", "build/", "board/", "data/", "skill/", "report/", "README.md"]
    assert all(p in paths for p in required_top)

    matrix = []
    for rid, title, section, pages, strength, targets, notes in REQUIREMENTS:
        missing = [target for target in targets.split(";") if target not in paths]
        assert not missing, (rid, missing)
        matrix.append({
            "id": rid,
            "requirement": title,
            "source_section": section,
            "pdf_page": pages,
            "strength": strength,
            "planned_paths": targets,
            "state": "结构已覆盖；内容待重新整理或验证",
            "notes": notes,
        })

    (ROOT / "project_tree.txt").write_text(
        "AUAR·雪妃：建议项目结构\n"
        "本文件是设计清单，不是当前文件存在清单；[条件]项按最终采用情况建立。\n"
        "程序和脚本仅建议命名，本次没有生成这些业务内容。\n\n"
        + tree + "\n",
        encoding="utf-8-sig",
    )
    write_csv(ROOT / "directory_catalog.csv", list(rows[0]), rows)
    write_csv(ROOT / "requirements_matrix.csv", list(matrix[0]), matrix)

    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    for source, target, page_args in [
        (GUIDE, "amd_open_topic_excerpt.txt", ["-f", "22", "-l", "25"]),
        (GUIDE, "amd_final_poster_excerpt.txt", ["-f", "28", "-l", "28"]),
        (UPLOAD, "upload_requirements_excerpt.txt", []),
    ]:
        result = subprocess.run(
            ["pdftotext", "-layout"] + page_args + [str(source), "-"],
            check=True, stdout=subprocess.PIPE,
        )
        (evidence / target).write_bytes(result.stdout)

    inputs = []
    for source in [GUIDE, UPLOAD,
                   ROOT / "evidence/teacher_submission_guidance.txt",
                   ROOT.parent / "2026-11-02_pynq_skill/readme.md",
                   ROOT.parent / "2026-11-02_pynq_skill/validation/archive_reproduction.json",
                   ROOT / "evidence/scheme_a_source_audit.json",
                   Path("/home/ghmd/Win共享文件/AGENTS.md"),
                   Path("/home/ghmd/Win共享文件/语言模型分析/README.md"),
                   Path("/home/ghmd/AMD_Smart/logs/daily/2026-11-02.md")]:
        inputs.append({"path": str(source), "bytes": source.stat().st_size, "sha256": sha(source)})
    with zipfile.ZipFile(PROJECT_ZIP) as archive:
        for member in [
            "项目/README.md",
            "项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md",
            "项目/方案/AURA_当前现状三人分工_2026-10-02.md",
            "项目/aura_fpga/docs/submission_matrix.csv",
        ]:
            payload = archive.read(member)
            inputs.append({"path": str(PROJECT_ZIP), "member": member,
                           "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})

    source_index = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "全新目录设计的规则与范围依据；不用于判断当前实板是否通过",
        "archive_layout_used": False,
        "runtime_access": False,
        "official_basis": "用户指定本地AMD指南、本机上传要求及用户提供的赛事方老师补充口径；未登录比赛后台",
        "sources": inputs,
    }
    (ROOT / "source_index.json").write_text(json.dumps(source_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    links = []
    for source in [DOC, ROOT / "readme.md"]:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                resolved = (source.parent / target).resolve()
                # validation.json is emitted immediately after this check.
                assert resolved.exists() or resolved == ROOT / "validation.json", (source.name, target)
                links.append({"from": source.name, "target": target})

    stats = {
        "status": "PASS",
        "scope": "文档和结构静态校验；没有运行工程或模型测试",
        "project_entries": len(rows),
        "directories": sum(r["type"] == "目录" for r in rows),
        "files": sum(r["type"] == "文件" for r in rows),
        "top_level_directories": sorted(r["path"] for r in rows if r["type"] == "目录" and r["path"].count("/") == 1),
        "subsystem_entries": dict(sorted(Counter(r["subsystem"] for r in rows).items())),
        "requirement_rows": len(matrix),
        "requirement_paths_all_in_design": True,
        "official_recommended_entries_covered": required_top,
        "ascii_names": True,
        "custom_names_lowercase": True,
        "official_example_exception": "README.md",
        "duplicate_paths": 0,
        "invalid_parent_paths": 0,
        "csv_encoding": "utf-8-sig",
        "local_links_checked": len(links),
        "code_archive_used": False,
        "created_business_files": 0,
        "board_or_model_access": False,
    }
    (ROOT / "validation.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
