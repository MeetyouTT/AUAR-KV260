"""Executable framework acceptance scenario. Every input/device is simulated."""
import time
from common.clock import SimulationClock
from common.contracts import FrameRef
from board.vision.frames import CapturedFrame
from .application import AuraRuntime


def wait_until(app, predicate, timeout_s=2.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.tick()
        if predicate():
            return True
        time.sleep(0.002)
    return False


def synthetic_frame(clock, epoch, frame_id, x=40, detections=True, embedding=None):
    ref = FrameRef(clock.domain, epoch, frame_id, clock.now_ms(), 640, 480)
    image = {"detections": [{"box": [x, 100, 80, 140], "score": 0.95}] if detections else []}
    if embedding is not None:
        image["embedding"] = embedding
    return CapturedFrame(ref, image)


def run_scenario(config, trace_path=None):
    if config["environment"] != "simulation" or config["vision"]["backend"] != "synthetic":
        raise ValueError("Acceptance scenario requires explicit synthetic simulation config")
    clock = SimulationClock()
    checks = {}
    with AuraRuntime(config, clock, trace_path) as app:
        app.identities.enroll("synthetic-visitor", "联调访客", (1.0, 0.0, 0.0, 0.0), consent=True)
        epoch = app.start_camera("demo-camera-1")
        for frame_id in range(1, 5):
            clock.advance(40)
            app.process_frame(synthetic_frame(clock, epoch, frame_id,
                                              x=40 if frame_id < 4 else 65, embedding=[1.0, 0.0, 0.0, 0.0]))
        checks["observed_track_and_virtual_permission"] = app.target is not None and app.guard.active
        checks["registered_synthetic_identity"] = app.identity_snapshot()["state"] == "KNOWN"
        token = app.ask("你好，汐蓝")
        checks["host_response_and_existing_ui"] = wait_until(app, lambda: app.session.playback_allowed(token))
        checks["playback_generation"] = app.playback_started(token) and app.playback_finished(token)
        before = app.trace.counts["dialogue.result"]
        cancelled = app.ask("这条联调回复将被取消")
        app.cancel("SCENARIO_CANCEL")
        discarded = wait_until(app, lambda: app.trace.counts["dialogue.result"] > before)
        checks["cancelled_reply_cannot_restart_playback"] = discarded and not app.session.playback_allowed(cancelled)
        clock.advance(1000)
        app.tick()
        checks["source_deadline_expiry"] = not app.guard.active and app.guard.reason == "SOURCE_EXPIRED"
        app.camera_lost("SCENARIO_DISCONNECT")
        app.start_camera("demo-camera-2")
        clock.advance(40)
        rejected = app.process_frame(synthetic_frame(clock, epoch, 5))
        checks["old_camera_epoch_rejected"] = not rejected["accepted"]
        for frame_id in (1, 2):
            clock.advance(40)
            app.process_frame(synthetic_frame(clock, "demo-camera-2", frame_id))
        checks["camera_recovers_with_new_observation"] = app.guard.active and app.target is not None
        checks["bounded_inline_events"] = app.bus.current_size == 0 and not app.bus.dropped_counts().get("__handler_error__")
        checks["no_physical_actuation"] = app.guard.physical_actuation is False
        snapshot = app.snapshot()
        snapshot["scenario_checks"] = checks
        snapshot["passed"] = all(checks.values())
        snapshot["evidence_scope"] = "PC_SYNTHETIC_SOFTWARE_INTEGRATION"
        snapshot["audio_note"] = "playback events only; no speaker or TTS executed"
        return snapshot
