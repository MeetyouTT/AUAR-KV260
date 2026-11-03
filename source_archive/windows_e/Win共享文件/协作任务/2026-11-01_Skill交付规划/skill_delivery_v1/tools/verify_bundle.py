"""Check bundle relative file hashes. No external paths, models or services."""
import argparse
import hashlib
import json
from pathlib import Path

def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
    errors = []
    for item in manifest.get("files", []):
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            errors.append("unsafe manifest path: " + str(rel))
            continue
        path = root / rel
        if path.is_symlink() or not path.is_file():
            errors.append("missing/non-regular file: " + str(rel))
            continue
        body = path.read_bytes()
        if len(body) != item["bytes"] or hashlib.sha256(body).hexdigest() != item["sha256"]:
            errors.append("content mismatch: " + str(rel))
    return {"status": "PASS" if not errors else "FAIL", "files_checked": len(manifest.get("files", [])),
            "errors": errors, "scope": "bundle_byte_integrity_only"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    try:
        result = verify(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "FAIL", "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
