"""Copy only existing model-service Python sources into a fresh local directory."""
from pathlib import Path
import hashlib
import json
import shutil

source = Path(r"E:\项目\共享文件夹\项目\aura_fpga\host\model_service")
target = Path(r"E:\项目\tmp\aura_skill_review_20261007\portability_probe\host\model_service")
manifest = []
for path in sorted(source.rglob("*.py")):
    if "__pycache__" in path.parts:
        continue
    relative = path.relative_to(source)
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    manifest.append({"path": relative.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(target.parent.parent / "copied_source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Copied {len(manifest)} Python files to a fresh local test directory.")
