#!/usr/bin/env python3
"""Capture immutable source, original-module and historical error evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CROSS = Path("/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = ROOT / "evidence" / "source_review"
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "scope": "Offline source/binary review; historical board log, no live board execution", "sources": {}, "files": {}, "commands": []}

    def command(name, argv, cwd=None):
        result = subprocess.run(argv, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        logfile = output / (name + ".log")
        logfile.write_bytes(result.stdout)
        manifest["commands"].append({"argv": argv, "cwd": str(cwd) if cwd else None,
            "returncode": result.returncode, "log": str(logfile.relative_to(ROOT)), "sha256": sha(logfile)})
        if result.returncode:
            raise RuntimeError("Evidence command failed: " + name)
        return result.stdout.decode("utf-8", errors="replace")

    for tree in ("linux-xlnx", "meta-xilinx", "XRT", "XRT_baseline", "XRT_patched"):
        path = ROOT / "sources" / tree
        manifest["sources"][tree] = {
            "commit": command(tree + "-head", ["git", "rev-parse", "HEAD"], path).strip(),
            "remote": command(tree + "-remote", ["git", "remote", "get-url", "origin"], path).strip(),
            "tracked_status": command(tree + "-status", ["git", "status", "--short", "--untracked-files=no"], path)}
    command("candidate-patch", ["git", "diff", "--binary"], ROOT / "sources" / "XRT_patched")
    command("candidate-diff-check", ["git", "diff", "--check"], ROOT / "sources" / "XRT_patched")
    relative_files = {
        "linux-xlnx": ["drivers/base/bus.c", "drivers/base/platform.c", "drivers/base/core.c", "drivers/of/platform.c", "drivers/of/dynamic.c", "drivers/of/overlay.c"],
        "meta-xilinx": ["meta-xilinx-core/recipes-xrt/xrt/xrt.inc", "meta-xilinx-core/recipes-xrt/zocl/zocl_git.bb",
                        "meta-xilinx-core/recipes-kernel/linux/linux-xlnx_2022.2.bb", "meta-xilinx-core/recipes-bsp/dfx-mgr/dfx-mgr_1.0.bb",
                        "meta-xilinx-core/recipes-bsp/libdfx/libdfx_1.0.bb"],
        "XRT_baseline": ["src/runtime_src/core/edge/drm/zocl/" + x for x in ("include/zocl_drv.h", "zocl_drv.c", "cu.c", "zocl_sk.c", "zocl_ospi_versal.c", "Makefile")],
        "XRT_patched": ["src/runtime_src/core/edge/drm/zocl/" + x for x in ("include/zocl_drv.h", "zocl_drv.c", "cu.c")],
    }
    for tree, files in relative_files.items():
        for relative in files:
            source = ROOT / "sources" / tree / relative
            target = output / "files" / tree / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest["files"][str(target.relative_to(ROOT))] = {"source": str(source.relative_to(ROOT)), "bytes": target.stat().st_size, "sha256": sha(target)}

    module = ROOT / "evidence" / "image_files" / "zocl.ko"
    manifest["image_zocl_sha256"] = sha(module)
    command("image-modinfo", ["/sbin/modinfo", str(module)])
    command("image-undefined-symbols", [str(CROSS) + "nm", "-u", str(module)])
    command("image-elf", [str(CROSS) + "readelf", "-h", "-S", str(module)])
    assembly = command("image-disassembly", [str(CROSS) + "objdump", "-dr", str(module)])
    headers = list(re.finditer(r"^[0-9a-f]+ <([^>]+)>:\s*$", assembly, re.M))
    functions = {}
    wanted = {"zocl_find_pdev", "subdev_create_cu", "cu_probe", "cu_remove", "zocl_drm_platform_remove", "configure_irq", "user_manage_irq"}
    for index, match in enumerate(headers):
        if match[1] not in wanted:
            continue
        end = headers[index + 1].start() if index + 1 < len(headers) else len(assembly)
        body = assembly[match.start():end]
        (output / ("image-function-" + match[1] + ".log")).write_text(body)
        functions[match[1]] = re.findall(r"R_AARCH64_(?:CALL26|JUMP26)\s+(\S+)", body)
    manifest["image_function_calls"] = functions
    lib = ROOT / "evidence" / "image_files" / "libxrt_core.so.2.14.0"
    strings = subprocess.check_output(["strings", str(lib)], text=True)
    manifest["image_xrt_version_strings"] = [s for s in strings.splitlines() if "43926231f7183688add2dccfd391b36a1f000bea" in s or "2022-10-07 05:12:02" in s]

    historical = Path("/home/ghmd/kv260-dpu41-control-20261001/evidence/candidate_board_20261002/14-restored-verification.kernel_after_restore.output")
    shutil.copy2(historical, output / "historical-kernel-after-restore.output")
    manifest["historical_errors"] = {"source": str(historical), "sha256": sha(historical),
        "matching_lines": [line for line in historical.read_text().splitlines() if "expected refcount 1 instead of" in line]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "copied_files": len(manifest["files"]), "historical_node_errors": len(manifest["historical_errors"]["matching_lines"]), "functions": list(functions)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
