#!/usr/bin/env python3
"""Prepare and review a new, isolated M3 bundle using existing host artifacts.

No board connection, installation, firmware switch, or operating-system build.
Existing output directories are refused to preserve prior results.
"""
import ast
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent / "kv260-dpu41-control-20261001"
APP = "kv260-benchmark-b4096-m3"
BUNDLE = ROOT / "test_bundle"
REVIEW = ROOT / "evidence/m3_bundle_review"
DOWNLOADS = ROOT / "downloads"
FDT_BIN = Path("/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin")
DTC = Path("/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin/dtc")
DTC172 = PARENT / "dependencies/dtc-1.7.2"
EXPECTED = {
    "new_full_pl_bin": "a48a25265d280f268300f627e6408ec56707a70d4deebe46e358500cf17b2650",
    "new_metadata_xclbin": "875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3",
    "new_hwh": "088cca44b02e2b494f7a1f9e06f23ed3d5ea06782e94d982a4065eb0f8b9e4de",
    "new_arch": "6feb79ba36f1f030f7827d94cdd8b43ff03faec72dad8e4a4e4d72704ed8490e",
}
COMMANDS = []


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def run(argv, name, cwd=ROOT, env=None):
    start = datetime.now(timezone.utc).isoformat()
    result = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    log = REVIEW / (name + ".log")
    with log.open("x") as stream:
        stream.write(result.stdout)
        stream.write(result.stderr)
    COMMANDS.append({"argv": [str(a) for a in argv], "cwd": str(cwd), "start_utc": start,
                     "end_utc": datetime.now(timezone.utc).isoformat(),
                     "returncode": result.returncode, "log": str(log.relative_to(ROOT)),
                     "combined_output_sha256": digest(log)})
    require(result.returncode == 0, "Command failed: " + repr(argv) + "; see " + str(log))
    return result.stdout


def decompile(path, name):
    return run([DTC, "-I", "dtb", "-O", "dts", path], name)


def archive(destination, members):
    # Deterministic metadata; only regular files from the known member list.
    with destination.open("xb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for relative, path in sorted(members.items()):
                    require(path.is_file() and not path.is_symlink(), "Unexpected archive member")
                    data = path.read_bytes()
                    item = tarfile.TarInfo(relative)
                    item.size = len(data)
                    item.mode = 0o644
                    item.uid = item.gid = item.mtime = 0
                    tar.addfile(item, io.BytesIO(data))
    with tarfile.open(destination, "r:gz") as tar:
        require(set(tar.getnames()) == set(members), "Archive member set mismatch")
        for item in tar.getmembers():
            require(item.isfile() and not Path(item.name).is_absolute()
                    and ".." not in Path(item.name).parts, "Unsafe archive entry")
            require(hashlib.sha256(tar.extractfile(item).read()).hexdigest()
                    == digest(members[item.name]), "Archive content mismatch")
    return {"path": str(destination.relative_to(ROOT)), "bytes": destination.stat().st_size,
            "sha256": digest(destination), "regular_file_count": len(members),
            "member_names": sorted(members), "archive_content_validation": "PASS"}


def main():
    require(not BUNDLE.exists() and not REVIEW.exists(), "Existing bundle/review refused")
    archives = [DOWNLOADS / (APP + "-runtime.tar.gz"), DOWNLOADS / (APP + "-test-bundle.tar.gz")]
    require(not any(path.exists() for path in archives), "Existing archive refused")
    REVIEW.mkdir(parents=True)
    runtime = BUNDLE / "lib/firmware/xilinx" / APP
    prov = BUNDLE / "provenance"
    hardware = prov / "hardware"
    runtime.mkdir(parents=True)
    hardware.mkdir(parents=True)
    (BUNDLE / "board").mkdir()
    (BUNDLE / "docs").mkdir()
    DOWNLOADS.mkdir(exist_ok=True)

    # Preserve and check the sealed host evidence and the validated parent.
    for directory, index, name in [
        (ROOT, "evidence/ARTIFACTS.sha256", "m3_original_artifacts"),
        (ROOT, "evidence/REVIEW.sha256", "m3_original_review"),
        (PARENT, "evidence/ARTIFACTS.sha256", "parent_original_artifacts"),
        (PARENT, "evidence/candidate_board_20261002.sha256", "parent_original_board_evidence"),
    ]:
        run(["sha256sum", "-c", index], name, cwd=directory)

    record = json.loads((ROOT / "evidence/artifacts.json").read_text())
    source = {item["role"]: item for item in record["artifacts"]}
    require(len(source) == 11, "Expected eleven distinct original host artifacts")
    for role, item in source.items():
        path = ROOT / item["path"]
        require(ROOT in path.resolve().parents, "Unexpected source path")
        require(digest(path) == item["sha256"] and path.stat().st_size == item["bytes"],
                "Original source artifact changed: " + role)
    for role, expected in EXPECTED.items():
        require(source[role]["sha256"] == expected, "Wrong M3 build identity: " + role)
    review = json.loads((ROOT / "evidence/host_review_summary.json").read_text())
    identity = json.loads((ROOT / "evidence/build_identity.json").read_text())
    require(review["covered_timing_and_metadata_gate_pass"], "Host review gate failed")
    require(identity["build_id"] == "0xa5078450", "Unexpected register BUILD_ID")

    shutil.copy2(ROOT / source["new_full_pl_bin"]["path"], runtime / (APP + ".bit.bin"))
    shutil.copy2(ROOT / source["new_metadata_xclbin"]["path"], runtime / (APP + ".xclbin"))
    shutil.copy2(ROOT / source["new_hwh"]["path"], hardware / "kv260_ispMipiRx_vcu_DP.hwh")
    shutil.copy2(ROOT / source["new_arch"]["path"], hardware / "arch.json")
    baseline_bin = PARENT / "evidence/baseline-kv260-benchmark-b4096.bit.bin"
    require(digest(baseline_bin) == "7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f", "Original baseline BIN changed")
    with baseline_bin.open("rb") as original, (runtime / (APP + ".bit.bin")).open("rb") as new:
        require(original.read(64) == new.read(64), "Full PL BIN header format mismatch")

    original_dtbo = prov / "baseline-kv260-benchmark-b4096.dtbo"
    baseline_dtb = prov / "baseline-system.dtb"
    shutil.copy2(PARENT / "test_bundle/provenance/baseline-kv260-benchmark-b4096.dtbo", original_dtbo)
    shutil.copy2(PARENT / "test_bundle/provenance/baseline-system.dtb", baseline_dtb)
    require(digest(original_dtbo) == "36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35", "Baseline DTBO mismatch")
    require(digest(baseline_dtb) == "7b0ec669233e0a9b18f2e853dfe7610c58c18ed33e07fe7e682290bc574c7d32", "Baseline host image DTB mismatch")
    candidate_dtbo = runtime / (APP + ".dtbo")
    shutil.copy2(original_dtbo, candidate_dtbo)
    run([FDT_BIN / "fdtput", "-t", "s", candidate_dtbo, "/fragment@0/__overlay__",
         "firmware-name", APP + ".bit.bin"], "set_firmware_name")
    firmware = run([FDT_BIN / "fdtget", "-t", "s", candidate_dtbo,
                    "/fragment@0/__overlay__", "firmware-name"], "candidate_firmware_name").strip()
    require(firmware == APP + ".bit.bin", "Firmware name mismatch")
    properties = run([FDT_BIN / "fdtget", "-p", candidate_dtbo,
                      "/fragment@0/__overlay__"], "candidate_fpga_properties").splitlines()
    require("fpga-config-from-dmabuf" in properties and "partial-fpga-config" not in properties
            and "external-fpga-config" not in properties, "Unexpected FPGA loading flags")
    require(run([FDT_BIN / "fdtget", "-t", "s", candidate_dtbo,
                 "/__fixups__", "fpga_full"], "full_region_target").strip() == "/fragment@0:target:0", "Not targeting fpga_full")
    original_text = decompile(original_dtbo, "original_dtbo_decompile")
    candidate_text = decompile(candidate_dtbo, "candidate_dtbo_decompile")
    require(original_text.count("kv260-benchmark-b4096.bit.bin") == 1, "Unexpected baseline firmware occurrences")
    require(original_text.replace("kv260-benchmark-b4096.bit.bin", firmware) == candidate_text,
            "Unexpected semantic device-tree change")
    (prov / "candidate.decompiled.dts").write_text(candidate_text)
    roundtrip = REVIEW / "candidate-dts-roundtrip.dtbo"
    run([DTC, "-I", "dts", "-O", "dtb", "-o", roundtrip, prov / "candidate.decompiled.dts"],
        "candidate_dts_roundtrip_compile")
    require(decompile(roundtrip, "candidate_dts_roundtrip_decompile") == candidate_text,
            "Candidate DTS did not round-trip with the same semantics")
    merge_env = os.environ.copy()
    merge_env["LD_LIBRARY_PATH"] = str(DTC172 / "libfdt")
    original_merged = prov / "baseline-host-merged-system.dtb"
    candidate_merged = prov / "host-merged-system.dtb"
    run([DTC172 / "fdtoverlay", "-i", baseline_dtb, "-o", original_merged, original_dtbo],
        "baseline_host_merge", env=merge_env)
    run([DTC172 / "fdtoverlay", "-i", baseline_dtb, "-o", candidate_merged, candidate_dtbo],
        "candidate_host_merge", env=merge_env)
    merged_firmware = run([FDT_BIN / "fdtget", "-t", "s", candidate_merged,
                           "/fpga-full", "firmware-name"], "merged_firmware_name").strip()
    require(merged_firmware == firmware, "Merged firmware name mismatch")
    base_merged_text = decompile(original_merged, "baseline_merged_decompile")
    new_merged_text = decompile(candidate_merged, "candidate_merged_decompile")
    require(base_merged_text.replace("kv260-benchmark-b4096.bit.bin", firmware) == new_merged_text,
            "Merged DT has an unexpected semantic change")
    write_json(runtime / "shell.json", {"shell_type": "XRT_FLAT", "num_slots": "1"})

    hwh = ET.parse(hardware / "kv260_ispMipiRx_vcu_DP.hwh").getroot()
    modules = {node.get("INSTANCE"): node for node in hwh.iter("MODULE")}
    require("aura_m3_regs_0" in modules and "DPUCZDX8G_1" in modules, "Missing hardware module")
    ranges = {name: [dict(node.attrib) for node in hwh.iter("MEMRANGE") if node.get("INSTANCE") == name]
              for name in ("aura_m3_regs_0", "DPUCZDX8G_1")}
    for name, lo, hi in [("aura_m3_regs_0", 0x80080000, 0x80080FFF),
                         ("DPUCZDX8G_1", 0xA0010000, 0xA0010FFF)]:
        require(any(int(row["BASEVALUE"], 0) == lo and int(row["HIGHVALUE"], 0) == hi
                    for row in ranges[name]), "Hardware address mismatch")
    parameters = {item.get("NAME"): item.get("VALUE") for item in modules["DPUCZDX8G_1"].iter("PARAMETER")}
    require(int(parameters["SYS_IP_VER"], 0) == 0x41 and int(parameters["SAVE_ARGMAX_ENA"], 0) == 1,
            "DPU version/ARGMAX mismatch")
    arch = json.loads((hardware / "arch.json").read_text())
    require(arch["fingerprint"] == "0x101000056010407", "Architecture fingerprint mismatch")
    layout = json.loads((ROOT / "evidence/xclbin_IP_LAYOUT.json").read_text())["ip_layout"]
    require(int(layout["m_count"]) == 1 and len(layout["m_ip_data"]) == 1
            and int(layout["m_ip_data"][0]["m_base_address"], 0) == 0xA0010000,
            "XCLBIN layout mismatch")
    xclbin_info = (ROOT / "evidence/xclbin_info.txt").read_text()
    uuid = re.search(r"UUID \(xclbin\):\s+(\S+)", xclbin_info).group(1)
    require(uuid == "c5255f48-d8da-4df0-e36e-a7c7d21b9dd8", "Wrong candidate UUID")
    sections = re.search(r"Sections:\s+(.*?)\n=", xclbin_info, re.S).group(1)
    require("BITSTREAM" not in sections, "Unexpected embedded bitstream section")

    for filename in ("build_identity.json", "artifacts.json", "host_review_summary.json",
                     "xclbin_IP_LAYOUT.json", "xclbin_CONNECTIVITY.json", "xclbin_MEM_TOPOLOGY.json",
                     "xclbin_info.txt"):
        shutil.copy2(ROOT / "evidence" / filename, prov / filename)
    shutil.copy2(PARENT / "evidence/dtc_provenance.json", prov / "dtc_provenance.json")
    shutil.copy2(ROOT / "docs/M3_REGISTER_CONTRACT.md", BUNDLE / "docs/M3_REGISTER_CONTRACT.md")
    shutil.copy2(ROOT / "docs/M3_TEST_CARD_PLAN.md", BUNDLE / "docs/M3_TEST_CARD_PLAN.md")
    helper = ROOT / "board/m3_board_check.py"
    ast.parse(helper.read_text(), filename=str(helper))
    shutil.copy2(helper, BUNDLE / "board/m3_board_check.py")

    runtime_files = [{"path": str(path.relative_to(BUNDLE)), "bytes": path.stat().st_size,
                      "sha256": digest(path)} for path in sorted(runtime.iterdir())]
    inputs = {
        "/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel": "4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef",
        "/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt": "691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c",
        "/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg": "f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a",
        "/home/root/kv260-test-20261001/samoyed.list": "bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa",
        "/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification": "322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e",
        "/home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification": "b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4",
    }
    runtime_manifest = {
        "application": APP, "firmware_name": firmware, "shell_type": "XRT_FLAT", "slots": 1,
        "runtime_files": runtime_files, "xclbin_uuid": uuid,
        "dpu_fingerprint": arch["fingerprint"], "dpu_control_base": "0xa0010000",
        "m3_base": "0x80080000", "m3_register_expectations":
            {"0x00": "0x41555241", "0x04": "0x00010000", "0x08": identity["build_id"]},
        "source_identity_sha256": identity["source_identity_sha256"],
        "validated_test_inputs_sha256": inputs,
        "input_hash_evidence": "Parent evidence/test_card_board_20261001/19-baseline-classification.test_inputs.output",
        "board_operations_performed_this_run": False,
        "input_hashes_rechecked_on_board_this_run": False,
        "origins": {"bit_bin": "Copy of this M3 build's Bootgen full-PL BIN",
                    "xclbin": "Copy of this M3 build's metadata-only XCLBIN",
                    "dtbo": "Official image DTBO reused; only firmware-name changed using fdtput",
                    "shell_json": "XRT_FLAT, one slot; same semantic layout as validated parent",
                    "hwh_and_arch": "Copy of this M3 build's generated metadata"},
    }
    write_json(prov / "runtime_manifest.json", runtime_manifest)
    version = {name: run([path, flag], "version_" + name).strip() for name, path, flag in
               [("dtc", DTC, "--version"), ("fdtget", FDT_BIN / "fdtget", "-V"),
                ("fdtput", FDT_BIN / "fdtput", "-V")]}
    tools = {str(path): digest(path) for path in [DTC, FDT_BIN / "fdtget", FDT_BIN / "fdtput",
                                                  DTC172 / "fdtoverlay", DTC172 / "libfdt/libfdt.so.1.7.2"]}
    bundle_review = {
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Host packaging and static review only; no board switch, MMIO or inference",
        "application": APP, "reference_commit": identity["reference_commit"],
        "host_package_consistency_pass": True, "original_evidence_indexes_pass": True,
        "new_bin_and_xclbin_hashes_match_sealed_m3_build": True,
        "full_pl_bin_64byte_header_matches_official_baseline": True,
        "dtbo_only_semantic_change": "firmware-name", "dtbo_semantic_diff_pass": True,
        "candidate_dts_roundtrip_pass": True,
        "full_region_target": "fpga_full", "partial_fpga_config_present": False,
        "fpga_config_from_dmabuf_present": True, "host_original_and_candidate_merge_pass": True,
        "host_merged_semantic_diff_pass": True, "merged_firmware_name": merged_firmware,
        "hwh_address_ranges": ranges, "dpu_fingerprint": arch["fingerprint"],
        "xclbin_uuid": uuid, "xclbin_bitstream_section_present": False,
        "host_tool_versions": version, "host_tool_binary_sha256": tools,
        "host_merge_tool": "Isolated upstream DTC/libfdt 1.7.2, unchanged existing parent build",
        "legacy_merge_repeated": False, "board_helper_python_syntax_parse": "PASS",
        "board_helper_executed": False, "board_mmio_access_capability": "pending",
        "board_m3_register_and_dpu_coexistence": "not performed",
        "axi_protocol_simulation": "not performed",
        "complete_io_constraint_coverage_pass": review["complete_io_constraint_coverage_pass"],
        "open_issues": ["Parent-board overlay node reference leak remains unresolved",
                        "7 input-delay and 9 output-delay directions remain uncovered",
                        "621 actual DRC Warnings retained; setup margin is +0.009 ns",
                        "Long-term operation, PWM, external interfaces and concurrent MMIO/inference not validated"],
        "runtime_files": runtime_files,
    }
    write_json(prov / "bundle_review.json", bundle_review)
    write_json(REVIEW / "bundle_review.json", bundle_review)
    (BUNDLE / "README.md").write_text(
        "# KV260 M3 独立测试包\n\n"
        "本包包含新构建的 DPU＋最小 AXI-Lite 寄存器配置。主机打包与静态一致性核验通过；板端尚未加载和验收。\n\n"
        "先在本目录执行 `sha256sum -c SHA256SUMS`。只安装 `lib/firmware/xilinx/kv260-benchmark-b4096-m3/` 的四个运行文件，目标已存在则停止。\n\n"
        "`provenance` 是审阅资料，不可写入 /boot、SD 整盘或 QSPI。`board/m3_board_check.py` 默认仅检查元数据，不切换应用；identity/scratch 是候选加载后的显式步骤。\n\n"
        "完整操作、停点与恢复见 [M3_TEST_CARD_PLAN.md](docs/M3_TEST_CARD_PLAN.md)。旧 overlay 引用计数问题仍未解决，不能自动反复切换。\n")
    files = sorted(path for path in BUNDLE.rglob("*") if path.is_file())
    hashes = "".join(digest(path) + "  " + str(path.relative_to(BUNDLE)) + "\n" for path in files)
    (BUNDLE / "SHA256SUMS").write_text(hashes)
    run(["sha256sum", "-c", "SHA256SUMS"], "complete_bundle_hash_check", cwd=BUNDLE)
    runtime_hashes = REVIEW / "runtime-SHA256SUMS"
    runtime_hashes.write_text("".join(item["sha256"] + "  " + item["path"] + "\n" for item in runtime_files))
    runtime_members = {item["path"]: BUNDLE / item["path"] for item in runtime_files}
    runtime_members["SHA256SUMS"] = runtime_hashes
    archive_records = [archive(archives[0], runtime_members),
                       archive(archives[1], {str(path.relative_to(BUNDLE)): path for path in files + [BUNDLE / "SHA256SUMS"]})]
    write_json(REVIEW / "archive_manifest.json", {"application": APP, "archives": archive_records})
    write_json(REVIEW / "command_results.json", COMMANDS)
    print("M3 host test bundle prepared and checked; no board operations performed")
    print(json.dumps({"runtime_files": runtime_files, "bundle_hashed_file_count": len(files),
                      "archives": [{key: item[key] for key in ("path", "bytes", "sha256", "regular_file_count")}
                                   for item in archive_records]}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if REVIEW.exists():
            failure = REVIEW / "FAILED.json"
            if not failure.exists():
                write_json(failure, {"error": str(error), "commands": COMMANDS,
                                     "board_operations_performed": False})
        raise
