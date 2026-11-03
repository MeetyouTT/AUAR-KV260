#!/usr/bin/env python3
"""Portable framework source bundle with per-file SHA256 verification."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "aura/"
TEXT_SUFFIXES = {".py", ".json", ".h", ".c", ".sv"}
CONFIGS = (
    "runtime.sim.json", "runtime.experiment.sim.json", "runtime.reference.json",
    "runtime.kv260.json", "servo_calibration.json", "toolchain_lock.json",
    "model_manifest.json", "source_import_manifest.json", "experiments.json",
)
DOCUMENTS = (
    "PROJECT_FRAMEWORK.md", "FRAMEWORK_STATUS.md", "runtime_architecture.md",
    "LICENSE_MATRIX.md", "MODEL_CARD_KWS.md",
)
PACKAGE_README = """# AURA·汐蓝框架源包

解压后进入 aura，先读 docs/PROJECT_FRAMEWORK.md 和 docs/FRAMEWORK_STATUS.md。
Python 3.8+ 标准库可运行：

    python -s tools/aura_project.py doctor
    python -s tools/aura_project.py demo
    python -s tools/aura_host.py
    python -s -m unittest discover -s tests/framework -v

Windows 也可双击 tools/run_project.bat；Linux 用 bash tools/run_project.sh。
模拟证据不能替代板端结果；默认物理运动禁用。
媒体 fixture 不执行真实 ASR/VLM/TTS；默认源包不含动画素材。
原设备部署、音频模型、个人身份库、bitstream/overlay 和本机环境未打包。
UI 需要既有素材及对应依赖。release_manifest.json 记录每个条目及是否带素材。
源仓旧 README 中的共享目录相邻交付链接属于历史资料，源包未包含那些目录。
"""


def collect(include_assets):
    selected = set()
    for directory in ("board", "common", "host", "hardware", "ui", "tests/framework"):
        for path in (ROOT / directory).rglob("*"):
            if "__pycache__" not in path.parts and path.is_file() and path.suffix in TEXT_SUFFIXES:
                selected.add(path.relative_to(ROOT).as_posix())
    selected.update("config/" + name for name in CONFIGS)
    selected.update("docs/" + name for name in DOCUMENTS)
    selected.update((
        "README.md", "tests/__init__.py", "tools/aura_project.py", "tools/aura_host.py",
        "tools/dialogue_host_ollama.py", "tools/run_project.sh", "tools/run_project.bat",
        "scripts/package_project.py", "host/model_service/README.md", "hardware/README.md",
        "models/vision/README.md", "models/vision/yunet_2022mar.onnx", "models/vision/sface_2021dec.onnx",
        "data/calibration_manifest.json", "data/test_manifest.json", "data/golden/framework_frames.jsonl",
        "requirements.txt", "requirements-dev.txt", "requirements-live.txt",
    ))
    if include_assets:
        for path in (ROOT / "assets").rglob("*"):
            if "__pycache__" not in path.parts and path.is_file():
                selected.add(path.relative_to(ROOT).as_posix())
    for relative in selected:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError("Missing or unsafe bundle source: " + relative)
    return sorted(selected)


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 10000:
            raise ValueError("Duplicate/excessive bundle entries")
        for name in names:
            parts = PurePosixPath(name).parts
            if not name.startswith(PREFIX) or ".." in parts or "\\" in name or name.endswith("/"):
                raise ValueError("Unsafe bundle path")
        if sum(info.file_size for info in archive.infolist()) > 2 * 1024 ** 3:
            raise ValueError("Excessive uncompressed bundle size")
        manifest = json.loads(archive.read(PREFIX + "release_manifest.json"))
        if manifest["schema_version"] != "aura-framework-source-1":
            raise ValueError("Unsupported source manifest")
        expected = {PREFIX + item["path"] for item in manifest["files"]}
        if len(expected) != len(manifest["files"]) or set(names) != expected | {PREFIX + "release_manifest.json"}:
            raise ValueError("Bundle entries differ from source manifest")
        for item in manifest["files"]:
            data = archive.read(PREFIX + item["path"])
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Bundle integrity mismatch: " + item["path"])
    return {"verified": True, "files_verified": len(manifest["files"]),
            "includes_assets": manifest["includes_assets"], "physical_actuation": False,
            "scope": manifest["scope"]}


def build(destination, include_assets=False):
    paths = collect(include_assets)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = destination / ("aura-framework-" + stamp + "-" + uuid.uuid4().hex[:6] + "-source.zip")
    manifest = {"schema_version": "aura-framework-source-1", "created_at_utc": stamp,
                "scope": "FRAMEWORK_SOURCE_BUNDLE_NOT_DEVICE_RELEASE", "includes_assets": include_assets,
                "physical_actuation": False,
                "excluded": ["environments", "personal_identity_databases", "raw_media", "run_logs",
                             "large_speech_and_dpu_models", "bitstream_overlay", "adjacent_deliverables"],
                "files": []}
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in paths:
            data = (ROOT / relative).read_bytes()
            archive.writestr(PREFIX + relative, data)
            manifest["files"].append({"path": relative, "bytes": len(data),
                                      "sha256": hashlib.sha256(data).hexdigest()})
        data = PACKAGE_README.encode("utf-8")
        archive.writestr(PREFIX + "PACKAGE_README.md", data)
        manifest["files"].append({"path": "PACKAGE_README.md", "bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest()})
        archive.writestr(PREFIX + "release_manifest.json",
                         json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    result = verify(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with Path(str(path) + ".sha256").open("x", encoding="utf-8") as handle:
        handle.write(digest + "  " + path.name + "\n")
    result.update({"archive": str(path), "archive_sha256": digest, "archive_bytes": path.stat().st_size})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="打包或校验 AURA 框架源码")
    commands = parser.add_subparsers(dest="command", required=True)
    creation = commands.add_parser("build")
    creation.add_argument("--out", default=str(ROOT / "artifacts/releases"))
    creation.add_argument("--include-assets", action="store_true")
    inspection = commands.add_parser("verify")
    inspection.add_argument("archive")
    args = parser.parse_args(argv)
    try:
        result = build(args.out, args.include_assets) if args.command == "build" else verify(args.archive)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"error": str(exc), "command": args.command}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
