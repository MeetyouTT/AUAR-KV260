#!/usr/bin/env python3
"""Compare compiled ZOCL modules with the factory module; no loading or MMIO."""
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CROSS = "/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def elf_sections(path):
    data = Path(path).read_bytes()
    if data[:6] != b"\x7fELF\x02\x01":
        raise RuntimeError("Not a little endian ELF64 module")
    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    shoff, shentsize, shnum, shstrndx = header[5], header[10], header[11], header[12]
    headers = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize) for i in range(shnum)]
    strings = data[headers[shstrndx][4]:headers[shstrndx][4] + headers[shstrndx][5]]
    sections = {}
    for item in headers:
        name = strings[item[0]:].split(b"\0", 1)[0].decode()
        if name in {".text", ".rodata", ".data", ".modinfo"}:
            sections[name] = {"bytes": item[5], "sha256": hashlib.sha256(data[item[4]:item[4] + item[5]]).hexdigest()}
    return sections


def main():
    output = ROOT / "evidence" / "module_review"
    output.mkdir(parents=True, exist_ok=False)
    symvers = ROOT / "build" / "kernel" / "Module.symvers"
    exports = {line.split()[1] for line in symvers.read_text().splitlines() if len(line.split()) >= 4}
    review = {"scope": "Host compile and ELF review only; driver not loaded on board", "modules": {},
              "kernel_symvers_sha256": sha(symvers), "checks": {}, "board_verified": False}
    wanted = {"zocl_find_pdev", "subdev_create_cu", "cu_probe", "cu_remove", "configure_irq", "user_manage_irq", "zocl_drm_platform_remove"}

    def command(name, argv):
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / (name + ".log")).write_bytes(p.stdout)
        if p.returncode:
            raise RuntimeError("Review command failed: " + name)
        return p.stdout.decode(errors="replace")

    for label, path in (("image", ROOT / "evidence" / "image_files" / "zocl.ko"),
                        ("baseline", ROOT / "artifacts" / "baseline" / "zocl.ko"),
                        ("patched", ROOT / "artifacts" / "patched" / "zocl.ko")):
        metadata = command(label + "-modinfo", ["/sbin/modinfo", str(path)])
        modinfo = {line.split(":", 1)[0]: line.split(":", 1)[1].strip() for line in metadata.splitlines() if ":" in line}
        undefined = command(label + "-imports", [CROSS + "nm", "-u", str(path)])
        imports = sorted({line.split()[-1] for line in undefined.splitlines() if line.split() and line.split()[0] == "U"})
        elf = command(label + "-elf", [CROSS + "readelf", "-h", "-SW", str(path)])
        assembly = command(label + "-disassembly", [CROSS + "objdump", "-dr", str(path)])
        functions = {}
        headers = list(re.finditer(r"^[0-9a-f]+ <([^>]+)>:\s*$", assembly, re.M))
        for index, match in enumerate(headers):
            if match[1] not in wanted:
                continue
            end = headers[index + 1].start() if index + 1 < len(headers) else len(assembly)
            body = assembly[match.start():end]
            (output / (label + "-function-" + match[1] + ".log")).write_text(body)
            functions[match[1]] = dict(collections.Counter(re.findall(r"R_AARCH64_(?:CALL26|JUMP26)\s+(\S+)", body)))
        review["modules"][label] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path),
            "vermagic": modinfo.get("vermagic"), "srcversion": modinfo.get("srcversion"), "name": modinfo.get("name"),
            "depends": modinfo.get("depends"), "strong_imports": imports, "missing_kernel_exports": sorted(set(imports) - exports),
            "aarch64_relocatable": bool(re.search(r"Machine:\s+AArch64", elf) and re.search(r"Type:\s+REL", elf)),
            "symbol_versions_section": bool(re.search(r"\s__versions\s", elf)), "function_call_counts": functions,
            "section_hashes": elf_sections(path)}

    image, baseline, patched = (review["modules"][label] for label in ("image", "baseline", "patched"))
    review["checks"] = {"all_aarch64_relocatable": all(m["aarch64_relocatable"] for m in review["modules"].values()),
        "all_vermagic_equal": image["vermagic"] == baseline["vermagic"] == patched["vermagic"] == "5.15.36-xilinx-v2022.2 SMP mod_unload aarch64",
        "baseline_srcversion_matches_image": baseline["srcversion"] == image["srcversion"],
        "baseline_imports_match_image": baseline["strong_imports"] == image["strong_imports"],
        "patched_imports_match_baseline": baseline["strong_imports"] == patched["strong_imports"],
        "all_strong_imports_resolved_in_rebuilt_kernel": not any(m["missing_kernel_exports"] for m in review["modules"].values()),
        "no_symbol_version_section_matches_config": not any(m["symbol_versions_section"] for m in review["modules"].values()),
        "all_module_names_zocl": all(m["name"] == "zocl" for m in review["modules"].values())}
    review["import_differences"] = {"baseline_added_vs_image": sorted(set(baseline["strong_imports"]) - set(image["strong_imports"])),
        "baseline_removed_vs_image": sorted(set(image["strong_imports"]) - set(baseline["strong_imports"])),
        "patched_added_vs_baseline": sorted(set(patched["strong_imports"]) - set(baseline["strong_imports"])),
        "patched_removed_vs_baseline": sorted(set(baseline["strong_imports"]) - set(patched["strong_imports"]))}
    review["host_review_passed"] = all(review["checks"].values())
    review["baseline_section_comparison"] = {name: baseline["section_hashes"].get(name) == image["section_hashes"].get(name)
        for name in sorted(set(baseline["section_hashes"]) | set(image["section_hashes"]))}
    (output / "review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "checks": review["checks"], "import_differences": review["import_differences"],
                      "board_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
