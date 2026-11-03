#!/usr/bin/env python3
"""Create and verify a fresh, English-path ZIP with a SHA256 file manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.out.resolve()
    if output == ROOT or ROOT in output.parents or output.exists():
        parser.error("use a new ZIP path outside the skill directory")
    files = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in ("__pycache__", ".git", ".pytest_cache") for part in relative.parts):
            continue
        if path.is_symlink():
            parser.error("symbolic links are not part of this release")
        if path.is_file():
            if not re.fullmatch(r"[a-z0-9_./-]+", relative.as_posix()):
                parser.error("nonconforming filename: " + relative.as_posix())
            files.append((path, "skill/pynq-contract-testgen/" + relative.as_posix()))
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for path, name in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in files:
            archive.write(path, name)
        manifest = "".join(value + "  " + name + "\n" for name, value in hashes.items())
        archive.writestr("checksums.sha256", manifest)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC verification failed")
        for name, expected in hashes.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise RuntimeError("archive content differs from manifest: " + name)
    size = output.stat().st_size
    report = {"status": "PASS" if size < 200000000 else "FAIL", "archive": str(output), "bytes": size,
              "limit_bytes_exclusive": 200000000, "source_files": len(files), "crc_and_sha256_verified": True,
              "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "board_verified": False}
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
