#!/usr/bin/env python3
"""Read-only KV260 boot-order and runtime preflight; emits JSON to stdout."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config/board_test_config.json").read_text())
PLAN = json.loads((ROOT / "install_plan.json").read_text())


def run(argv):
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=20, check=False)
        return {"rc": p.returncode, "output": p.stdout.strip()}
    except Exception as e:
        return {"rc": None, "output": f"{type(e).__name__}: {e}"}


def read(path):
    try:
        return pathlib.Path(path).read_text(errors="replace").strip()
    except Exception as e:
        return f"UNREADABLE: {type(e).__name__}: {e}"


def sha(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except Exception as e:
        return f"UNREADABLE: {type(e).__name__}: {e}"


def main():
    facts = {
        "captured_unix_time": int(time.time()),
        "read_only": True,
        "uid": os.geteuid(),
        "identity": {
            "model": read("/proc/device-tree/model").replace("\x00", ""),
            "kernel": run(["uname", "-r"]),
            "boot_id": read("/proc/sys/kernel/random/boot_id"),
            "cmdline": read("/proc/cmdline"),
            "root_source": run(["findmnt", "-n", "-o", "SOURCE", "/"]),
            "mmc_cid": {str(p): read(p) for p in pathlib.Path("/sys/block").glob("mmcblk*/device/cid")},
        },
        "runtime": {
            "modules": run(["cat", "/proc/modules"]),
            "zocl_srcversion": read("/sys/module/zocl/srcversion"),
            "zocl_parameters": {"enable_xgq_ert": read("/sys/module/zocl/parameters/enable_xgq_ert")},
            "dfx_service": run(["systemctl", "show", "dfx-mgr.service", "-p", "ActiveState", "-p", "FragmentPath", "-p", "DropInPaths", "-p", "ExecStart", "-p", "ExecStartPre", "-p", "After", "-p", "Before", "-p", "Requires"]),
            "dfx_unit": read("/lib/systemd/system/dfx-mgr.service"),
            "dfx_unit_sha256": sha("/lib/systemd/system/dfx-mgr.service"),
            "dfx_manager_sha256": sha("/usr/bin/dfx-mgrd"),
            "module_dep_entry": run(["sh", "-c", "grep -E '(^|/)zocl\\.ko:' /lib/modules/$(uname -r)/modules.dep"]),
            "module_load_configs": {p: run(["sh", "-c", "if [ -f '$1' ]; then cat '$1'; elif [ -d '$1' ]; then find '$1' -maxdepth 2 -type f -print -exec cat {} \\; ; else echo MISSING; fi", "sh", p]) for p in ["/etc/modules", "/etc/modules-load.d", "/usr/lib/modules-load.d", "/lib/modules-load.d", "/etc/modprobe.d"]},
            "boot_order": run(["systemd-analyze", "critical-chain", "dfx-mgr.service"]),
            "initramfs_candidates": run(["sh", "-c", "ls -l /boot/*initramfs* /boot/*Image* 2>/dev/null"]),
            "initramfs_tool": run(["sh", "-c", "command -v lsinitramfs || command -v lsinitrd || command -v dracut || true"]),
            "initramfs_module_entries": run(["sh", "-c", "for f in /boot/ramdisk.cpio.gz.u-boot; do [ -f \"$f\" ] || continue; dd if=\"$f\" bs=64 skip=1 status=none | gzip -dc | cpio -it 2>/dev/null | grep -E '(^|/)(zocl([^/]*|$)|lib/modules|modules-load|modprobe\\.d)' || true; done"]),
            "boot_dtb_zocl_strings": run(["sh", "-c", "for f in /boot/system.dtb /boot/system-zynqmp-sck-kv-g-revB.dtb; do [ -f \"$f\" ] || continue; echo ===$f===; strings \"$f\" | grep -Ei 'zocl|embedded_sched' || true; done"]),
            "app_slots": run(["xmutil", "listapps"]),
            "board_id": run(["xmutil", "boardid"]),
            "drm": run(["sh", "-c", "for d in /sys/class/drm/card*/device/driver; do printf '%s ' \"$d\"; readlink -f \"$d\"; done"]),
            "processes": run(["sh", "-c", "ps -eo pid,comm,args | grep -E '[d]fx-mgrd|[v]ai_|[x]rt' || true"]),
            "module_holders": {str(p): read(p) for p in pathlib.Path("/sys/module/zocl/holders").glob("*")},
        },
        "stock_file_hashes": {},
        "gate": {
            "known_boot_order_status": "READ_ONLY_EVIDENCE_COLLECTED_COLD_BOOT_UNVERIFIED",
            "reason": "Review initramfs_module_entries, boot_dtb_zocl_strings, systemd dependencies and manager ExecStartPre. A cold boot is still needed to verify the actual candidate module load order.",
        },
    }
    for path in CFG.get("stock_hashes26", {}):
        facts["stock_file_hashes"][path] = sha(path)
    facts["static_expectations"] = {
        "expected_spare_card_cid": PLAN["expected_spare_card_cid"],
        "expected_kernel": PLAN["tested_kernel"],
        "expected_candidate_srcversion": PLAN["expected_zocl_srcversion"],
        "expected_original_srcversion": PLAN["baseline_zocl_srcversion"],
        "expected_original_manager_sha256": PLAN["baseline_manager_sha256"],
        "expected_firmware": PLAN["firmware"],
        "all_26_original_hashes_match": all(v == CFG["stock_hashes26"][k] for k, v in facts["stock_file_hashes"].items()),
    }
    facts["status"] = "REVIEW_REQUIRED" if os.geteuid() == 0 else "INCOMPLETE_NOT_ROOT"
    json.dump(facts, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
