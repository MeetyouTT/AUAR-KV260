#!/usr/bin/env python3
"""Explicit board checks; default preflight does not access PL registers.

This helper does not install firmware, load/unload an application, or reboot.
identity/scratch require the M3 application to have been loaded separately.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
from datetime import datetime, timezone

APP = "kv260-benchmark-b4096-m3"
BASELINE = "kv260-benchmark-b4096"
TEST_CARD_CID = "0353445345333247805558c00401a100"
BASE = 0x80080000
EXPECTED_ID = (0x41555241, 0x00010000, 0xA5078450)
KNOWN_CLIENTS = {"test_jpeg_classification", "test_performance_classification",
                 "xdputil", "dpu_runner"}


def event(kind, **values):
    print(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                      "event": kind, **values}, sort_keys=True), flush=True)


def command(argv, timeout=20):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, timeout=timeout)
    event("command", argv=argv, returncode=result.returncode, output=result.stdout)
    if result.returncode:
        raise RuntimeError("Command failed: " + repr(argv))
    return result.stdout


def active_apps():
    output = command(["dfx-mgr-client", "-listPackage"])
    rows = [line.split() for line in output.splitlines()]
    rows = [row for row in rows if len(row) == 6 and row[1] == "XRT_FLAT"]
    if not rows:
        raise RuntimeError("Unrecognized package table; inspect the actual client version")
    return [row[0] for row in rows if row[-1].rstrip(",") == "0"]


def clients():
    result = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            argv = (path / "cmdline").read_bytes().split(b"\0")
            if any(Path(word.decode("utf-8", "replace")).name in KNOWN_CLIENTS
                   for word in argv[:2] if word):
                result.append(int(path.name))
        except (OSError, ValueError):
            continue
    return result


def kernel_memory_options():
    candidates = [Path("/proc/config.gz"), Path("/boot/config-" + platform.release())]
    for path in candidates:
        if path.is_file():
            data = (gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
                    if path.name.endswith(".gz") else path.read_text())
            names = ("CONFIG_DEVMEM", "CONFIG_STRICT_DEVMEM", "CONFIG_IO_STRICT_DEVMEM")
            return {"source": str(path), "lines": [line for line in data.splitlines()
                    if any(line.startswith(name + "=") or line == "# " + name + " is not set"
                           for name in names)]}
    return {"source": None, "lines": [], "status": "not available"}


def preflight():
    if platform.machine() != "aarch64" or os.geteuid() != 0:
        raise RuntimeError("Run on the KV260 as root; host MMIO is refused")
    cid = Path("/sys/block/mmcblk1/device/cid").read_text().strip()
    if cid != TEST_CARD_CID:
        raise RuntimeError("Unexpected SD card; keep the original card untouched")
    mounts = [line.split() for line in Path("/proc/mounts").read_text().splitlines()]
    if not any(row[0] == "/dev/mmcblk1p2" and row[1] == "/" for row in mounts):
        raise RuntimeError("Unexpected root filesystem")
    model = Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
    if "K26" not in model:
        raise RuntimeError("Unexpected board model")
    state = Path("/sys/class/fpga_manager/fpga0/state").read_text().strip()
    firmware = Path("/proc/device-tree/fpga-full/firmware-name").read_bytes().rstrip(b"\0").decode()
    apps = active_apps()
    busy = clients()
    busybox = shutil.which("busybox")
    applets = command([busybox, "--list"]).splitlines() if busybox else []
    has_devmem = "devmem" in applets
    mem = Path("/dev/mem")
    mem_present = mem.exists() and stat.S_ISCHR(mem.stat().st_mode)
    event("preflight", model=model, kernel=platform.release(), root_device="/dev/mmcblk1p2",
          test_card_identity_matches=True, active_apps=apps, fpga_manager_state=state,
          firmware_name=firmware, known_inference_clients=busy,
          busybox_devmem_applet_present=has_devmem, dev_mem_character_device=mem_present,
          kernel_memory_options=kernel_memory_options(), mmio_access_performed=False,
          actual_mmio_permission_and_bus_access="not yet verified")
    if apps not in ([BASELINE], [APP]):
        raise RuntimeError("Expected exactly one official or M3 active application")
    return apps, state, firmware, busy, busybox, has_devmem, mem_present


def candidate_gate(bundle, result):
    apps, state, firmware, busy, busybox, has_devmem, mem_present = result
    if apps != [APP] or state != "operating" or firmware != APP + ".bit.bin":
        raise RuntimeError("M3 is not the verified active configuration; MMIO refused")
    if busy:
        raise RuntimeError("Known inference clients are still running")
    if not has_devmem or not mem_present:
        raise RuntimeError("Required board memory access tool/device missing; do not change kernel flags")
    expected = json.loads((bundle / "provenance/runtime_manifest.json").read_text())
    if expected["application"] != APP or len(expected["runtime_files"]) != 4:
        raise RuntimeError("Unexpected manifest")
    for item in expected["runtime_files"]:
        relative = Path(item["path"])
        if relative.parent != Path("lib/firmware/xilinx") / APP:
            raise RuntimeError("Unexpected runtime path")
        path = Path("/") / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError("Installed firmware hash mismatch: " + str(path))
        event("installed_hash_match", path=str(path), sha256=digest)
    return busybox


def read32(busybox, offset):
    if offset not in (0, 4, 8, 12):
        raise RuntimeError("Address is outside the four-register allowlist")
    text = command([busybox, "devmem", hex(BASE + offset), "32"], timeout=5).strip()
    if re.fullmatch(r"0[xX][0-9a-fA-F]{1,8}", text) is None:
        raise RuntimeError("Unexpected devmem read output")
    value = int(text, 16)
    event("read32", address=hex(BASE + offset), value="0x%08x" % value)
    return value


def write_scratch(busybox, value):
    command([busybox, "devmem", hex(BASE + 12), "32", "0x%08x" % value], timeout=5)
    event("write32", address=hex(BASE + 12), value="0x%08x" % value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", choices=("preflight", "identity", "scratch"), default="preflight")
    parser.add_argument("--bundle-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    result = preflight()
    if args.stage == "preflight":
        event("preflight_pass", scope="metadata only; no PL register access or firmware switch")
        return
    busybox = candidate_gate(args.bundle_root, result)
    values = tuple(read32(busybox, offset) for offset in (0, 4, 8))
    if values != EXPECTED_ID:
        raise RuntimeError("M3 identity mismatch; SCRATCH writes refused")
    event("identity_pass", ip_id=hex(values[0]), abi_version=hex(values[1]), build_id=hex(values[2]))
    if args.stage == "identity":
        return
    original = read32(busybox, 12)
    event("scratch_original_saved", value="0x%08x" % original)
    try:
        for pattern in (0x00000000, 0xFFFFFFFF, 0x55AA33CC, 0xAA55CC33):
            write_scratch(busybox, pattern)
            if read32(busybox, 12) != pattern:
                raise RuntimeError("SCRATCH readback mismatch")
    finally:
        write_scratch(busybox, original)
        if read32(busybox, 12) != original:
            raise RuntimeError("Original SCRATCH value was not restored")
        event("scratch_original_restored", value="0x%08x" % original)
    event("scratch_pass", scope="four full-width patterns; no byte-strobe or protocol simulation")


def interrupted(signum, frame):
    raise KeyboardInterrupt("Received signal " + str(signum))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        event("failed", error=str(error), automatic_app_switch=False, automatic_reboot=False)
        sys.exit(1)
