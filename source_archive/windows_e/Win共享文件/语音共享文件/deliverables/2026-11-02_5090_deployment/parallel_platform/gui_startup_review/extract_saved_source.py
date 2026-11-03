"""Materialize already collected public source for static analysis, locally only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE / "installed_source"
count = 0
for basename in ("gui_bootstrap_01.json", "gui_dependencies_01.json", "gui_selected_context_01.json", "gui_safety_closure_01.json"):
    payload = json.loads((HERE / basename).read_text(encoding="utf-8"))["board_result"]
    for record in payload["files"].values():
        if "text" not in record:
            continue
        raw = record["text"].encode("utf-8")
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
        path = record["path"]
        marker = "/runtime/aura/"
        if marker in path:
            relative = path.split(marker, 1)[1]
        elif "/startup/" in path:
            relative = "startup/" + path.split("/startup/", 1)[1]
        elif "/manual-release/release.json" in path:
            relative = "selected_manual_release.json"
        else:
            raise AssertionError(path)
        target = DEST / relative
        assert target.resolve().is_relative_to(DEST.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == raw
        else:
            target.write_bytes(raw)
        count += 1
print(json.dumps({"source_records_verified": count, "destination": str(DEST), "board_mutations": False}))
