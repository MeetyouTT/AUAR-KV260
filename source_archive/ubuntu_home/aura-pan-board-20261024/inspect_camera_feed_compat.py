"""Inspect the active camera source contract without importing or changing it."""
import ast
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

pid = subprocess.check_output(
    ["systemctl", "show", "aura-camera-ui.service", "-p", "MainPID", "--value"],
    text=True,
).strip()
assert pid.isdigit() and int(pid) > 1
argv = shlex.split(Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode())
scripts = [Path(arg) for arg in argv if arg.endswith(".py") and Path(arg).is_file()]
assert scripts, "active camera command does not expose a Python entry path"
entry = scripts[-1]
if "ui_camera_service.py" in entry.name:
    source = entry
else:
    meta_path = entry.parent / "meta.json"
    meta = json.loads(meta_path.read_text())
    source = Path(meta["candidate_root"]) / "aura/board/vision/ui_camera_service.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == meta["candidate_ui_sha256"]

tree = ast.parse(source.read_bytes())
camera_state = next((node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "CameraState"), None)
assert camera_state is not None
attrs = set()
for node in ast.walk(camera_state):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        attrs.add(node.attr)
methods = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
required = {
    "lock", "clock", "processed_stamp", "observation_fid", "boot", "epoch",
    "camera_epoch", "capture_stamp", "camera_error", "detector_error",
    "requested_target", "observation", "selected_id",
}
print(json.dumps({
    "active_camera_python_entry_found": True,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "camera_state_present": True,
    "required_state_fields_present": sorted(required & attrs),
    "required_state_fields_missing": sorted(required - attrs),
    "handler_factory_present": "handler_for" in methods,
    "camera_main_present": "main" in methods,
}, sort_keys=True))
