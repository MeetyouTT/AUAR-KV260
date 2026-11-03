#!/usr/bin/env python3
"""Run the existing aura-runtime-1 pipeline through the new board delivery gate."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config
from common.clock import SimulationClock
from board.runtime.application import AuraRuntime
from board.runtime.scenarios import synthetic_frame, wait_until
from host.model_service.backends import FixtureAsr, FixtureTts, FixtureVlm
from host.model_service.pipeline import ModelServicePipeline
from host.model_service.protocol import AudioFormat, AudioRef, ImageRef


def selftest():
    pipeline = ModelServicePipeline(FixtureAsr(), FixtureVlm(), FixtureTts())
    health = pipeline.startup()
    clock = SimulationClock()
    with AuraRuntime(load_config(), clock) as app:
        epoch = app.start_camera("media-selftest-camera")
        for frame_id in (1, 2):
            clock.advance(40)
            app.process_frame(synthetic_frame(clock, epoch, frame_id))
        app.attach_media_backend(pipeline.handle)
        audio = AudioRef(1, 0, 1600, AudioFormat(16000, 1, "S16_LE"))
        image_bytes = b"synthetic-image-fixture-not-a-real-camera-image"
        image = ImageRef(2, hashlib.sha256(image_bytes).hexdigest(), app.camera_epoch_number, 0)
        token = app.ask_media(audio, b"\0" * 3200, image, image_bytes, "联调问题")
        okay = wait_until(app, lambda: app.media_session.playback_allowed(token))
        response = app.last_media_response
        checks = {"fixture_health_flagged": health.is_fixture,
                  "three_stages_returned": bool(response and len(response.timings) == 3),
                  "binary_audio_checked": bool(response and len(response.segments) == 2),
                  "board_delivery_gate_passed": okay,
                  "physical_actuation_disabled": app.guard.physical_actuation is False}
        app.cancel("MEDIA_SELFTEST_CANCEL")
        checks["cancel_invalidates_audio"] = not app.media_session.playback_allowed(token)
        return {"passed": all(checks.values()), "checks": checks, "health": health.to_dict(),
                "evidence_scope": "PC_FIXTURE_MEDIA_PIPELINE", "real_asr_vlm_tts_executed": False,
                "physical_actuation": False}


if __name__ == "__main__":
    result = selftest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
