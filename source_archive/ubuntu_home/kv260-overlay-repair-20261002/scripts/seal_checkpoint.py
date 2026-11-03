#!/usr/bin/env python3
"""Preserve already completed work when the user requests a pause."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    name = "kv260-zocl-reference-repair-20261002"
    bundle = ROOT / "bundle" / name
    bundle.mkdir(parents=True, exist_ok=False)
    review = json.loads((ROOT / "evidence/module_review/review.json").read_text())
    if not review["host_review_passed"]:
        raise RuntimeError("Cannot label the existing candidate host-reviewed")
    shutil.copy2(ROOT / "artifacts/patched/zocl.ko", bundle / "zocl.ko")
    shutil.copy2(ROOT / "evidence/source_review/candidate-patch.log", bundle / "fix.patch")
    shutil.copy2(ROOT / "docs/BOARD_VALIDATION_PLAN.md", bundle / "BOARD_VALIDATION_PLAN.md")
    metadata = {"state": "paused_at_user_request", "board_verified": False,
        "kernel_commit": "19984dd147fa7fbb7cb14b17400263ad0925c189",
        "xrt_commit": "43926231f7183688add2dccfd391b36a1f000bea",
        "patch_sha256": sha(bundle / "fix.patch"), "candidate": review["modules"]["patched"],
        "offline_original": review["modules"]["image"], "host_checks": review["checks"],
        "baseline_section_comparison": review["baseline_section_comparison"],
        "module_loading_scope": "Temporary candidate on identified spare card after live inventory; no board action performed"}
    (bundle / "BUILD.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    (bundle / "README.md").write_text("# KV260 ZOCL 修复候选\n\n状态：主机编译及核验通过，板端验证未执行；已按用户要求暂停。\n\n"
        "`zocl.ko` 为本轮新编译候选。完整源码基底 commit、补丁摘要和兼容性证据见 BUILD.json；fix.patch 可应用于固定 XRT commit。\n\n"
        "先核对 SHA256SUMS，接续方案见 BOARD_VALIDATION_PLAN.md。保持磁盘原驱动及原固件，先完成实时身份核验和原状态备份；候选只从独立 staging 临时加载。\n\n"
        "主机核验不能替代板端卸载、推理及恢复验收。没有安装脚本或自动切换入口。\n")
    files = sorted(p for p in bundle.iterdir() if p.is_file())
    (bundle / "SHA256SUMS").write_text("".join(sha(p) + "  " + p.name + "\n" for p in files))
    files = sorted(p for p in bundle.iterdir() if p.is_file())
    archive = bundle.parent / (name + ".tar.gz")
    with archive.open("xb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for file in files:
                    info = tarfile.TarInfo(name + "/" + file.name)
                    info.size, info.mode, info.mtime = file.stat().st_size, 0o644, 0
                    with file.open("rb") as contents:
                        tar.addfile(info, contents)
    members = []
    with tarfile.open(str(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise RuntimeError("Unexpected archive member")
            data = tar.extractfile(member).read()
            corresponding = bundle / Path(member.name).name
            if hashlib.sha256(data).hexdigest() != sha(corresponding):
                raise RuntimeError("Archive content differs from saved candidate")
            members.append({"path": member.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    archive_info = {"path": str(archive.relative_to(ROOT)), "bytes": archive.stat().st_size, "sha256": sha(archive), "verified_regular_members": members,
                    "board_verified": False, "paused_at_user_request": True}
    (bundle.parent / "archive_manifest.json").write_text(json.dumps(archive_info, indent=2, ensure_ascii=False) + "\n")
    checkpoint = ROOT / "evidence/checkpoint"
    checkpoint.mkdir(exist_ok=False)
    state = {"status": "paused_at_user_request", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "completed": ["source/binary defect identified", "kernel dependencies compiled", "baseline and patched ZOCL compiled", "8 host checks passed", "candidate archive saved"],
        "remaining": ["live board identity/config/hash review", "temporary repaired module load", "official app inference and overlay removal validation", "original module/app recovery"],
        "blocker": "User has no board available; board is at the laboratory", "board_actions_performed_this_turn": False,
        "resume": "Wait for user to reconnect the test card and UART and explicitly request continuation"}
    (checkpoint / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    indexed = {ROOT / "README.md", ROOT / "OVERLAY_REPAIR_REPORT.md"}
    for directory in ("scripts", "docs", "evidence", "artifacts", "bundle"):
        indexed.update(p for p in (ROOT / directory).rglob("*") if p.is_file() and not p.is_symlink())
    indexed.update(ROOT / "build/kernel" / f for f in (".config", "Module.symvers", "System.map", "vmlinux", "prepared.json"))
    index = ROOT / "EVIDENCE.sha256"
    hashes = [(p, sha(p)) for p in sorted(indexed)]
    index.write_text("".join(digest + "  " + str(path.relative_to(ROOT)) + "\n" for path, digest in hashes))
    # Verify preservation only, without invoking a new build or any board work.
    for path, expected in hashes:
        if sha(path) != expected:
            raise RuntimeError("Saved evidence changed: " + str(path))
    print(json.dumps({"status": state["status"], "archive": archive_info["path"], "archive_bytes": archive_info["bytes"],
        "archive_sha256": archive_info["sha256"], "regular_members": len(members), "preserved_entries": len(hashes), "board_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
