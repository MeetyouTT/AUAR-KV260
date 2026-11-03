#!/usr/bin/env python3
"""Unified AURA project entry: doctor, demo, replay, camera and dialogue."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.clock import MonotonicClock, SimulationClock
from common.config import load_config, project_path
from board.runtime.application import AuraRuntime
from board.runtime.scenarios import run_scenario, synthetic_frame, wait_until
from board.vision.frames import CapturedFrame
from common.contracts import FrameRef


def dependency_exists(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def doctor(config):
    issues = []
    v = config["vision"]
    required = []
    if v["backend"] == "cpu_yunet":
        required += ["numpy", "cv2"]
    if v["tracker"] == "bytetrack":
        required += ["numpy", "yolox.tracker.byte_tracker"]
    dependencies = {name: dependency_exists(name) for name in required}
    issues += ["Missing dependency: " + name for name, present in dependencies.items() if not present]
    if v["backend"] != "synthetic":
        path = project_path(v["model"])
        expected = v.get("model_sha256")
        if not path.is_file():
            issues.append("Missing project model: " + v["model"])
        elif not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            issues.append("Model SHA256 missing/mismatch")
    if v["backend"] == "dpu_plugin":
        for key in ("entrypoint", "arch_fingerprint"):
            if not v.get(key):
                issues.append("DPU " + key + " not configured")
    models = json.loads((ROOT / "config/model_manifest.json").read_text(encoding="utf-8"))
    model_checks = []
    for item in models["models"]:
        if item.get("path") and item.get("sha256"):
            path = project_path(item["path"])
            okay = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
            model_checks.append({"id": item["id"], "hash_verified": okay})
    return {"schema_version": "aura-readiness-1", "release_id": config["release_id"],
            "environment": config["environment"], "ready_for_selected_profile": not issues,
            "dependencies": dependencies, "reference_models": model_checks, "issues": issues,
            "capabilities": {"runtime_composition": "implemented", "sqlite_identity": "implemented",
                             "freshness_and_admission": "software_implemented_calibration_pending",
                             "camera": "adapter_available_not_opened", "dpu_project_model": "pending",
                             "bytetrack": "adapter_available_dependency_and_board_tests_pending",
                             "mcp01": "not_integrated", "vlm": "not_integrated", "light_asd": "result_port_only",
                             "pl_absolute_source_deadline": "not_implemented_in_imported_rtl",
                             "physical_actuation": False},
            "inspection_scope": "local_files_and_dependency_presence_no_device_access"}


def output_directory(value):
    path = Path(value) if value else ROOT / "metrics/raw" / ("framework-" + uuid.uuid4().hex[:12])
    path.mkdir(parents=True, exist_ok=False)
    return path


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def replay(config, path, out):
    if config["environment"] != "simulation" or config["vision"]["backend"] != "synthetic":
        raise ValueError("Replay requires a simulation profile; it does not open a real device")
    clock = SimulationClock(0)
    count = 0
    with AuraRuntime(config, clock, out / "trace.jsonl") as app:
        epoch = app.start_camera("replay-camera")
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                if len(line) > 1024 * 1024:
                    raise ValueError("Replay record exceeds 1 MiB")
                if not line.strip():
                    continue
                row = json.loads(line)
                if row["at_ms"] < clock.now_ms():
                    raise ValueError("Replay time must advance monotonically")
                clock.advance(row["at_ms"] - clock.now_ms())
                count += 1
                ref = FrameRef(clock.domain, epoch, row.get("frame_id", count), row["at_ms"],
                               row.get("width", 640), row.get("height", 480))
                app.process_frame(CapturedFrame(ref, {"detections": row["detections"], **({"embedding": row["embedding"]} if "embedding" in row else {})}))
        if count == 0:
            raise ValueError("Replay contains no frames")
        result = app.snapshot()
        result.update({"replay_records": count, "evidence_scope": "PC_REPLAY_SOFTWARE_INTEGRATION"})
    return result


def run_camera(config, seconds, out):
    if config["vision"]["backend"] == "synthetic":
        raise ValueError("Camera command requires a reference/KV260 profile")
    from board.vision.capture import OpenCVCamera
    clock = MonotonicClock()
    with AuraRuntime(config, clock, out / "trace.jsonl") as app:
        camera = OpenCVCamera(config["vision"], clock)
        processed = 0
        try:
            camera.start()
            app.start_camera(camera.epoch)
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                if camera.error:
                    app.camera_lost(camera.error)
                    raise RuntimeError(camera.error)
                frame = camera.slot.take()
                if frame is not None:
                    accepted = app.process_frame(frame)
                    processed += int(accepted["accepted"])
                else:
                    app.tick()
                    time.sleep(0.005)
            result = app.snapshot()
            result.update({"camera_frames_processed": processed, "latest_frames_replaced": camera.slot.dropped,
                           "passed": processed > 0,
                           "evidence_scope": "REAL_CAMERA_SOFTWARE_REFERENCE_MOTION_DISABLED"})
            return result
        finally:
            camera.close()


def gui(config):
    if config["environment"] != "simulation" or config["vision"]["backend"] != "synthetic":
        raise ValueError("GUI bootstrap currently accepts simulation profile only")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QInputDialog
    from PySide6.QtGui import QKeySequence, QShortcut
    from board.interaction.qt_app import MainWindow
    qt = QApplication.instance() or QApplication(sys.argv)
    clock = MonotonicClock()
    with AuraRuntime(config, clock) as app:
        epoch = app.start_camera("gui-simulation")
        window = MainWindow(app.ui, event_bus=app.bus)
        window.setWindowTitle("AURA·汐蓝 · 框架联调（模拟输入）")
        state = {"frame_id": 0, "presence": True}
        timer = QTimer(window)
        def refresh():
            state["frame_id"] += 1
            app.process_frame(synthetic_frame(clock, epoch, state["frame_id"], detections=state["presence"]))
        def ask_text():
            text, okay = QInputDialog.getText(window, "汐蓝对话联调", "输入文字（实际麦克风尚未接入）")
            if okay and text:
                app.ask(text)
        def toggle_presence():
            state["presence"] = not state["presence"]
        shortcuts = []
        for key, callback in (("Return", ask_text), ("Escape", lambda: app.cancel()), ("Space", toggle_presence)):
            shortcut = QShortcut(QKeySequence(key), window)
            shortcut.activated.connect(callback)
            shortcuts.append(shortcut)
        timer.timeout.connect(refresh)
        timer.start(100)
        window.show()
        return qt.exec()


def main(argv=None):
    parser = argparse.ArgumentParser(description="AURA 项目统一入口")
    parser.add_argument("--config", default="config/runtime.sim.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="只读检查配置、模型和依赖")
    demo = commands.add_parser("demo", help="无需硬件运行完整联调场景")
    demo.add_argument("--out")
    replay_parser = commands.add_parser("replay", help="回放明确标记的检测记录")
    replay_parser.add_argument("input")
    replay_parser.add_argument("--out")
    camera = commands.add_parser("camera", help="运行真实相机参考链；运动始终禁用")
    camera.add_argument("--seconds", type=float, default=5.0)
    camera.add_argument("--out")
    dialogue = commands.add_parser("dialogue", help="通过现有主机协议完成文字联调")
    dialogue.add_argument("--text", required=True)
    commands.add_parser("ui", help="复用已有汐蓝 Qt 界面的框架联调")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "doctor":
            result = doctor(config)
            emit(result)
            return 0 if result["ready_for_selected_profile"] else 2
        if args.command == "ui":
            return gui(config)
        if args.command == "dialogue":
            with AuraRuntime(config) as app:
                token = app.ask(args.text)
                okay = wait_until(app, lambda: app.session.playback_allowed(token), timeout_s=config["dialogue"]["timeout_ms"] / 1000.0 + 0.5)
                emit({"accepted": okay, "response": app.last_response, "media": "text_only", "physical_actuation": False})
                return 0 if okay else 2
        out = output_directory(args.out)
        if args.command == "demo":
            result = run_scenario(config, out / "trace.jsonl")
        elif args.command == "replay":
            result = replay(config, project_path(args.input), out)
        else:
            if not 0 < args.seconds <= 300:
                raise ValueError("Camera duration must be in (0,300] seconds")
            result = run_camera(config, args.seconds, out)
        (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        emit({"output": str(out), "passed": result.get("passed", True), "scope": result.get("evidence_scope"),
              "checks": result.get("scenario_checks", {}), "physical_actuation": False})
        return 0 if result.get("passed", True) else 1
    except (OSError, ValueError, KeyError, ImportError, RuntimeError, TypeError) as exc:
        emit({"error": str(exc), "command": args.command, "physical_actuation": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
