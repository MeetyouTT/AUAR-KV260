#!/usr/bin/env python3
"""Prepare host-only evidence; never open or modify a board device."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evidence/deployment_review/compatibility_diagnosis"
BASELINE = Path("/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly")
ARCHIVE = Path("/home/ghmd/下载/Vitis-AI-3.0.zip")


def main():
    OUT.mkdir(exist_ok=True)
    copies = OUT / "official_vitis_ai_3_0_sources"
    copies.mkdir(exist_ok=True)
    source_paths = [
        "dpu/README.md",
        "dpu/ref_design_docs/README_DPUCZ_Vitis.md",
        "src/vai_runtime/target_factory/src/create_target_DPUCZDX8G_ISA1.cpp",
        "src/vai_runtime/target_factory/targets/DPUCZDX8G_ISA1_B4096.prototxt",
        "src/vai_runtime/vart/dpu-runner/src/dpu_runner_base_imp.cpp",
    ]
    with zipfile.ZipFile(ARCHIVE) as archive:
        for path in source_paths:
            target = copies / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read("Vitis-AI-3.0/" + path))

    current = int(json.loads((ROOT / "evidence/deployment_review/test_bundle/provenance/hardware/arch.json").read_text())["fingerprint"], 16)
    original = 0x101000056010407
    hwh = ET.parse(ROOT / "evidence/deployment_review/test_bundle/provenance/hardware/kv260_ispMipiRx_vcu_DP.hwh")
    dpu = next(x for x in hwh.getroot().iter("MODULE") if x.get("INSTANCE") == "DPUCZDX8G_1")
    params = {x.get("NAME"): x.get("VALUE") for x in dpu.findall("PARAMETERS/PARAMETER")}
    diagnosis = {
        "new_arch_fingerprint": hex(current),
        "baseline_model_and_previous_hardware_query_fingerprint": hex(original),
        "xor": hex(current ^ original),
        "differing_bits": [bit for bit in range(64) if (current ^ original) & (1 << bit)],
        "bit_30_definition": "SV_AM / save_engine.argmax in official Vitis AI 3.0 target factory",
        "new_save_argmax": bool(current & (1 << 30)),
        "baseline_save_argmax": bool(original & (1 << 30)),
        "hwh_parameters": {key: params[key] for key in ["SYS_IP_VER", "SYS_REGMAP_VER", "TIME_YEAR", "TIME_MONTH", "TIME_DAY", "ARCH_PP", "ARCH_ICP", "ARCH_OCP", "ALU_PARALLEL", "LOAD_PARALLEL", "C_BASEADDR", "C_HIGHADDR"]},
        "hardware_fingerprint_remeasured_this_turn": False,
        "scope": "No source, installed tools or board changes; compare generated metadata and existing baseline evidence only",
    }

    spec = importlib.util.spec_from_file_location("baseline_ext4_reader", BASELINE / "read_host_image.py")
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    metadata = json.loads((BASELINE / "host-image-partitions.json").read_text())
    filesystem = reader.Ext4(reader.IMAGE, metadata["partitions"][1]["offset"])
    extracted = []
    try:
        for path in [
            "/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo",
            "/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel",
        ]:
            data = filesystem.data(filesystem.lookup(path))
            dest = OUT / "baseline_image_files" / Path(path).name
            dest.parent.mkdir(exist_ok=True)
            dest.write_bytes(data)
            extracted.append({"path_in_image": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "output": str(dest.relative_to(ROOT))})
    finally:
        filesystem.f.close()
    diagnosis["baseline_image_files"] = extracted
    (OUT / "fingerprint_diagnosis.json").write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2) + "\n")

    raw = (ROOT / "evidence/deployment_review/routed_drc.rpt").read_text()
    rows = re.findall(r"^\| ([A-Z]+-\d+)\s*\| (Warning|Error|Critical Warning)\s*\| ([^|]+)\| (\d+)\s*\|", raw, re.M)
    assert sum(int(row[3]) for row in rows) == 579
    with (ROOT / "evidence/deployment_review/drc_rule_summary.tsv").open("w") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(["Rule", "Severity", "Description", "Count"])
        writer.writerows((rule, severity, description.strip(), count) for rule, severity, description, count in rows)
    manifest = {
        "status": "HOLD",
        "application_directory": "lib/firmware/xilinx/kv260-benchmark-b4096",
        "firmware_name": "kv260-benchmark-b4096.bit.bin",
        "shell_type": "XRT_FLAT",
        "num_slots": "1",
        "kernel": "DPUCZDX8G_1",
        "cu_base_address": "0xa0010000",
        "xclbin_uuid": "d698c28f-5d6b-9ffc-7777-99e332911f22",
        "arch_fingerprint": hex(current),
        "baseline_model_fingerprint": hex(original),
        "new_bin_generation": "bootgen -arch zynqmp -image candidate_bit.bif -process_bitstream bin",
    }
    (ROOT / "evidence/deployment_review/bundle_manifest.txt").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(diagnosis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
