#!/usr/bin/env python3
"""Create a hash inventory for release-relevant local KV260 artifacts."""
from pathlib import Path
import hashlib
import os
import subprocess

OUT = Path("/home/ghmd/kv260_full_image_audit_20260926_codex/reports/artifact_inventory.tsv")
selected = {}

def add(path, group):
    p = Path(path)
    if p.is_file():
        selected[str(p.resolve())] = group

def add_glob(root, patterns, group, recursive=True):
    root = Path(root)
    if not root.exists():
        return
    paths = root.rglob("*") if recursive else root.glob("*")
    for p in paths:
        if p.is_file() and any(p.match(pattern) for pattern in patterns):
            add(p, group)

petalinux = Path("/home/ghmd/work/petalinux-kv260-dpu")
images = petalinux / "images/linux"
for name in (
    "BOOT.BIN", "image.ub", "boot.scr", "bootgen.bif", "system.bit", "system.dtb",
    "Image", "Image.gz", "fit-dtb.blob", "rootfs.manifest", "rootfs.cpio",
    "rootfs.cpio.gz", "rootfs.cpio.gz.u-boot", "rootfs.ext4", "rootfs.jffs2",
    "rootfs.tar.gz", "zynqmp_fsbl.elf", "pmufw.elf", "bl31.elf", "u-boot.elf",
    "u-boot.bin", "u-boot-dtb.elf", "u-boot-dtb.bin", "vmlinux",
):
    add(images / name, "petalinux-images-linux")
add(petalinux / "project-spec/hw-description/system.xsa", "petalinux-hardware-description")
add(petalinux / "project-spec/hw-description/kv260_dpu_clockfix.bit", "petalinux-hardware-description")
add(petalinux / "project-spec/configs/config", "petalinux-config")
add(petalinux / "project-spec/meta-user/conf/petalinuxbsp.conf", "petalinux-config")
add(petalinux / "components/plnx_workspace/device-tree/device-tree/pl.dtsi", "petalinux-device-tree-source")

hw = Path("/home/ghmd/work/kv260_dpu_b2304_uram")
add(hw / "kv260_dpu.xpr", "original-vivado-project")
add(hw / "kv260_dpu.srcs/sources_1/bd/kv260_dpu_bd/kv260_dpu_bd.bd", "original-vivado-project")
add(hw / "kv260_dpu.gen/sources_1/bd/kv260_dpu_bd/ip/kv260_dpu_bd_dpu_0_0/kv260_dpu_bd_dpu_0_0.dcp", "original-dpu-ip-ooc-checkpoint")
add(hw / "kv260_dpu.runs/kv260_dpu_bd_dpu_0_0_synth_1/kv260_dpu_bd_dpu_0_0.dcp", "original-dpu-ip-ooc-checkpoint")
add_glob(hw / "output", ["*.bit", "*.xsa", "*.pdi"], "original-vivado-output", recursive=False)
add_glob(hw / "kv260_dpu.runs", ["*.dcp", "*.bit"], "original-vivado-runs")

rebuild = Path("/home/ghmd/kv260_clockfix_rebuild_20260926")
add_glob(rebuild, ["*.bit", "*.xsa", "*.pdi", "*.hwh", "*.dcp", "*.bif"], "fresh-rebuild-hardware-artifacts")
add_glob(rebuild / "kv260_dpu.gen/sources_1/bd/kv260_dpu_bd", ["*.bd", "*.xci", "arch.json"], "fresh-rebuild-generated-sources")
add(rebuild / "REPORT.md", "fresh-rebuild-report")
add(rebuild / "BUILD_COMMANDS.md", "fresh-rebuild-command-record")
add(rebuild / "reports/SHA256SUMS.txt", "fresh-rebuild-hash-record")
add(rebuild / "reports/reset_interface_comparison.txt", "fresh-rebuild-reset-evidence")
add(rebuild / "reports/final_routed_reset_gate.txt", "fresh-rebuild-reset-evidence")
add(rebuild / "reports/synth_dpu_reset_connectivity.txt", "fresh-rebuild-reset-evidence")

models = Path("/home/ghmd/work/models/resnet50-b2304")
add_glob(models, ["*.xmodel", "*.onnx", "meta.json", "quant_info.json"], "resnet50-source-and-compiled-model")
verified = Path("/home/ghmd/kv260_resnet50_verified_rebuild_20260926")
add_glob(verified, ["*.xmodel", "meta.json", "hashes.sha256", "compile_provenance.txt"], "resnet50-verified-model")
add(Path("/home/ghmd/kv260_quantized_diag_run/quantized/deployable.pth"), "qat-cpu-checkpoint")
float_check = Path("/home/ghmd/kv260_float_check_offline_run/kv260_float_check")
for name in ("cat2.jpg", "input.bin", "check_float.py", "run_check.sh", "README.txt", "SOURCE.md"):
    add(float_check / name, "fixed-input-and-preprocess")
for name in ("check_quantized.py", "run_quantized.sh", "run_attempt1.log", "run.log"):
    add(Path("/home/ghmd/kv260_quantized_diag_run") / name, "qat-cpu-check")

for name in ("Xilinx_Unified_2022.2_1014_8888_Lin64.bin.digests", "download-manifest.md"):
    add(Path("/home/ghmd/Downloads/AMD_KV260_2022.2/01_unified_installer") / name, "official-tool-installer-metadata")
for name in ("image.ub.old", "system.dtb.old"):
    add(Path("/home/ghmd/kv260-sd-backup-20260924.9ZTIEc") / name, "sd-backup-files")
for name in ("serial-boot.log",):
    add(Path("/home/ghmd/work/kv260-boot-audit-current") / name, "prior-board-boot-log")
add(Path("/home/ghmd/work/kv260-boot-audit-live/report.txt"), "prior-board-readonly-report")

# Existing independently created audit evidence, copied byte-for-byte into this
# diagnostic directory for traceability; the original files remain untouched.
prior_audit = Path("/home/ghmd/Downloads/kv260_audit_deepseek_20260926")
for rel in (
    "REPORT.md",
    "reports/ip_ooc_and_new_routed_reset_topology.txt",
    "reports/orig_routed_reset_query.txt",
    "reports/opt_stage_and_orig_dangling.txt",
    "reports/model_and_input_hashes.txt",
    "logs/impl_opt_keywords.txt",
    "query_ip_ooc_and_new_routed.tcl",
    "extract/boot_serial_key_lines.txt",
    "extract/ip_sv_inst_block.txt",
    "extract/new_sim_netlist_inst_context.txt",
    "extract/ip_rtl_reset_lines.txt",
    "logs/evidence_simnetlist_diff.txt",
):
    add(prior_audit / rel, "prior-full-image-audit-evidence")

add_glob(
    Path("/home/ghmd/work/models/resnet50-b2304/source/pt_resnet50_imagenet_224_224_8.2G_3.0"),
    ["*.py", "*.json", "*.txt", "*.md", "*.sh"],
    "resnet50-source-code-and-metadata",
)

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as out:
    out.write("group\tfile_type\tbytes\tsha256\tabsolute_path\n")
    for path, group in sorted(selected.items()):
        st = os.stat(path)
        detected_type = subprocess.run(
            ["file", "--brief", path], check=True, capture_output=True, text=True
        ).stdout.strip().replace("\t", " ")
        out.write(f"{group}\t{detected_type}\t{st.st_size}\t{digest(path)}\t{path}\n")
print(f"INVENTORY={OUT} FILES={len(selected)}")
