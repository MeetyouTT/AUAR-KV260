#!/usr/bin/env python3
"""Index newly built host artifacts and create a full PL BIN from the new BIT."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parent.parent
summary = json.loads((root / "evidence/host_review_summary.json").read_text())
if not summary["covered_timing_and_metadata_gate_pass"]:
    raise SystemExit("The covered timing/metadata gate failed; BIN preparation stopped")
overlay = Path("src/kv260/overlays/examples/benchmark/binary_container_1")
platform = Path("src/kv260/platforms/xilinx_kv260_ispMipiRx_vcu_DP_202220_1")
out = root / "artifacts"
out.mkdir(exist_ok=True)
bit = root / overlay / "sd_card/kv260_ispMipiRx_vcu_DP_wrapper.bit"
bif = out / "m3_full_pl.bif"
bif.write_text("all:\n{\n    [destination_device = pl] " + str(bit) + "\n}\n")
binary = out / "kv260-benchmark-b4096-m3.bit.bin"
command = ["bootgen", "-arch", "zynqmp", "-image", str(bif), "-o", str(binary), "-w"]
result = subprocess.run(command, text=True, capture_output=True)
(out / "bootgen.log").write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
parent_bin = root.parent / "kv260-dpu41-control-20261001/test_bundle/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.bit.bin"
with binary.open("rb") as f, parent_bin.open("rb") as reference:
    header_matches = f.read(64) == reference.read(64)
if not header_matches:
    raise SystemExit("Full PL BIN header differs from the board-validated parent")
paths = [
    ("new_platform_xpfm", platform / "kv260_ispMipiRx_vcu_DP.xpfm"),
    ("new_platform_xsa", platform / "hw/kv260_ispMipiRx_vcu_DP.xsa"),
    ("new_platform_spfm", platform / "sw/kv260_ispMipiRx_vcu_DP.spfm"),
    ("new_xo", overlay / "dpu.xo"),
    ("new_link_xsa", overlay / "dpu.xsa"),
    ("new_metadata_xclbin", overlay / "sd_card/dpu.xclbin"),
    ("new_bit", overlay / "sd_card/kv260_ispMipiRx_vcu_DP_wrapper.bit"),
    ("new_hwh", overlay / "sd_card/kv260_ispMipiRx_vcu_DP.hwh"),
    ("new_arch", overlay / "sd_card/arch.json"),
    ("new_routed_dcp", overlay / "link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp"),
    ("new_full_pl_bin", binary.relative_to(root)),
]
items = []
for role, name in paths:
    path = root / name
    data = path.read_bytes()
    items.append({"role": role, "path": str(name), "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest()})
manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
            "full_pl_bin_header_matches_validated_parent": header_matches,
            "scope": "Host build artifacts; DTBO/runtime bundle and board validation are separate steps",
            "bootgen_command": command, "bootgen_returncode": result.returncode, "artifacts": items}
(root / "evidence/artifacts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
(root / "evidence/ARTIFACTS.sha256").write_text("".join(
    item["sha256"] + "  " + item["path"] + "\n" for item in items))
subprocess.run(["sha256sum", "--check", "--quiet", "evidence/ARTIFACTS.sha256"], cwd=root, check=True)
print("New artifact hash verification passed:", len(items), "items")
print("New full PL BIN:", binary)
