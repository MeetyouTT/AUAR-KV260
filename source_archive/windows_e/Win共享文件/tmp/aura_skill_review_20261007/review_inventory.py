"""Read-only project inventory; emit compact evidence for the skill planning review."""
from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(r"E:\项目")
OUT = ROOT / "tmp" / "aura_skill_review_20261007"
SKIP = {".git", ".venv", ".venv-live", "__pycache__", ".pytest_cache", ".verysync", "node_modules", "tmp"}

counts = collections.Counter()
extensions = collections.defaultdict(collections.Counter)
skill_entries = []
for parent, directories, files in os.walk(ROOT):
    directories[:] = [d for d in directories if d not in SKIP]
    for filename in files:
        path = Path(parent) / filename
        relative = path.relative_to(ROOT)
        group = relative.parts[0] if len(relative.parts) > 1 else "root_files"
        counts[group] += 1
        extensions[group][path.suffix.lower() or "<none>"] += 1
        if filename.lower() in {"skill.md", "agents.md"}:
            skill_entries.append(str(relative))

sources = [
    "README.md",
    "方案/amd_kv260_20day_3person_execution_plan_v2.md",
    "aura_fpga/docs/fpga_framework.md",
    "aura_fpga/contracts/platform_manifest.json",
    "共享文件夹/aura/README.md",
    "共享文件夹/aura/requirements-dev.txt",
    "共享文件夹/aura/requirements-live.txt",
    "共享文件夹/aura/scripts/validator_cases.py",
    "共享文件夹/aura/tests/data/validator_cases.json",
    "共享文件夹/aura/board/runtime/validator/semantic_validator.py",
    "共享文件夹/aura/tools/realtime_controller.py",
    "共享文件夹/aura/tools/realtime_audio.py",
    "共享文件夹/aura/tests/test_realtime_audio_protocol.py",
    "共享文件夹/项目/aura_fpga/host/model_service/protocol.py",
    "共享文件夹/项目/aura_fpga/host/model_service/pipeline.py",
    "共享文件夹/项目/aura_fpga/host/model_service/tests/test_protocol.py",
    "共享文件夹/项目/aura_fpga/host/model_service/tests/test_pipeline.py",
    "共享文件夹/deliverables/2026-10-06_xilan_live/移机交接_汐蓝实时演示.md",
    "共享文件夹/deliverables/2026-10-06_xilan_live/latest_verification.json",
    "output/aura_single_innovation_direction_20261007.md",
]
fingerprints = []
for relative in sources:
    path = ROOT / relative
    fingerprints.append({"path": relative, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

cases = json.loads((ROOT / "共享文件夹/aura/tests/data/validator_cases.json").read_text(encoding="utf-8"))["cases"]
report = {
    "review_date_label": "2026-10-07",
    "scope": "Directory inventory including archived snapshots; content review focuses on current source, plans, contracts, tests and proof records. Virtual environments, caches, sync state and tmp are not included in counts. Binary weights/assets were not interpreted as text.",
    "counts_by_top_level": dict(counts),
    "extensions_by_top_level": {k: dict(v) for k, v in extensions.items()},
    "skill_and_agents_entries": skill_entries,
    "current_skill_directory_exists": {
        "共享文件夹/aura/skill": (ROOT / "共享文件夹/aura/skill").is_dir(),
        "共享文件夹/项目/aura_fpga/skill": (ROOT / "共享文件夹/项目/aura_fpga/skill").is_dir(),
        "aura_fpga/skill": (ROOT / "aura_fpga/skill").is_dir(),
    },
    "legacy_validator_case_inventory": {"total": len(cases), "positive": sum(bool(c.get("expect_ok")) for c in cases), "negative": sum(not bool(c.get("expect_ok")) for c in cases), "is_execution_result": False},
    "source_fingerprints": fingerprints,
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "project_inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("counts_by_top_level", "skill_and_agents_entries", "current_skill_directory_exists", "legacy_validator_case_inventory")}, ensure_ascii=False, indent=2))
