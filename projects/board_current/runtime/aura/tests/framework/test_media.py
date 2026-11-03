from dataclasses import replace
import hashlib
import unittest
from common.clock import SimulationClock
from common.config import load_config
from board.runtime.application import AuraRuntime
from board.runtime.media_session import MediaSessionManager
from board.runtime.scenarios import synthetic_frame, wait_until
from host.model_service.backends import FixtureAsr, FixtureVlm, FixtureTts
from host.model_service.pipeline import ModelServicePipeline
from host.model_service.protocol import AudioFormat, AudioRef, ImageRef
from tools.aura_host import selftest


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.clock = SimulationClock()
        self.generation = 1
        self.session = MediaSessionManager(self.clock.domain, lambda: self.generation, 15000, allow_fixture=True)
        self.pipeline = ModelServicePipeline(FixtureAsr(), FixtureVlm(), FixtureTts())
        self.pipeline.startup()
        self.audio = AudioRef(1, 0, 1600, AudioFormat(16000, 1, "S16_LE"))

    def request_and_response(self):
        token, payload = self.session.begin(self.audio, b"\0" * 3200, None, self.clock.now_ms(), question_text="联调")
        response = self.pipeline.handle(payload["request"], pcm=payload["pcm"])
        return token, response

    def test_existing_media_pipeline_reaches_authoritative_ui_gate(self):
        self.assertTrue(selftest()["passed"])

    def test_cancelled_and_future_generations_rejected(self):
        token, response = self.request_and_response()
        response.generation += 1
        self.assertFalse(self.session.accept(token, response, self.clock.now_ms(), None)["accepted"])
        response.generation = token.generation
        self.generation += 1
        self.assertFalse(self.session.accept(token, response, self.clock.now_ms(), None)["accepted"])

    def test_payload_deadline_extension_and_bad_segment_rejected(self):
        token, response = self.request_and_response()
        response.board_deadline_ns += 1000000
        self.assertFalse(self.session.accept(token, response, self.clock.now_ms(), None)["accepted"])
        response.board_deadline_ns = token.deadline_ms * 1000000
        response.segments[1] = replace(response.segments[1], segment_index=0)
        self.assertFalse(self.session.accept(token, response, self.clock.now_ms(), None)["accepted"])
        with self.assertRaises(ValueError):
            self.session.begin(self.audio, b"bad", None, self.clock.now_ms())

    def test_fixture_audio_cannot_be_mislabeled_real(self):
        token, response = self.request_and_response()
        self.session.allow_fixture = False
        self.assertEqual(self.session.accept(token, response, self.clock.now_ms(), None)["reason"], "FIXTURE_MEDIA_NOT_ALLOWED")

    def test_board_computes_image_age_and_rejects_disconnected_source(self):
        seen = []
        def backend(request, **payload):
            seen.append(request)
            return self.pipeline.handle(request, **payload)
        with AuraRuntime(load_config(), self.clock) as app:
            epoch = app.start_camera("image-age-test")
            app.process_frame(synthetic_frame(self.clock, epoch, 1))
            app.attach_media_backend(backend)
            image_bytes = b"synthetic-image"
            image = ImageRef(1, hashlib.sha256(image_bytes).hexdigest(), app.camera_epoch_number, 0)
            self.clock.advance(100)
            token = app.ask_media(self.audio, b"\0" * 3200, image, image_bytes)
            self.assertTrue(wait_until(app, lambda: app.media_session.playback_allowed(token)))
            self.assertEqual(seen[0].image.age_ms, 100)
            app.camera_lost()
            with self.assertRaises(ValueError):
                app.ask_media(self.audio, b"\0" * 3200, image, image_bytes)


if __name__ == "__main__":
    unittest.main()
