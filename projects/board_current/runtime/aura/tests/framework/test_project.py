import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

from common.clock import SimulationClock
from common.config import PROJECT_ROOT, load_config, validate_config
from common.contracts import Detection, FrameRef, MotionCommand, PositionEvidence, TrackObservation
from board.fusion.freshness import FreshnessPolicy
from board.fusion.scheduler import SingleCuScheduler
from board.fusion.speaker import SpeakerSuggestion
from board.identity.store import IdentityStore
from board.motion.guard import SimulationGuard
from board.runtime.application import AuraRuntime
from board.runtime.event_bus import EventBus, EventEnvelope
from board.runtime.events import EventType
from board.runtime.scenarios import run_scenario, synthetic_frame, wait_until
from board.runtime.session import SessionManager
from board.vision.frames import LatestFrameSlot
from host.model_service.schema import LegacySchemaSubset, check
from tools.aura_project import doctor, replay


def observed(clock, frame_id=1, velocity=0.0):
    ref = FrameRef(clock.domain, "camera", frame_id, clock.now_ms(), 640, 480)
    return TrackObservation(ref, 1, 1, (40.0, 100.0, 80.0, 140.0), 0.95, velocity, True, True)


def response_for(token, **fields):
    value = {"protocol_version": "1.0", "request_id": token.request_id,
             "scene_seq_used": token.scene_seq, "reply_text": "你好", "emotion": "neutral",
             "avatar_action": "", "visual_claims": []}
    value.update(fields)
    return value


def session_request():
    manager = SessionManager(load_config()["dialogue"])
    scene = {"schema_version": "1.0", "scene_seq": 3, "captured_at_ms": 1000,
             "valid_until_ms": 1250, "camera_state": "online", "people_count": 1,
             "current_target": {"track_id": 1, "position": "left", "confidence": 0.9, "source_frame_id": 2}}
    token, request = manager.begin("你好", scene, ("camera", 1, 1), 1100)
    return manager, token, request


class ContractTests(unittest.TestCase):
    def test_bool_frame_id_and_nonfinite_detection_rejected(self):
        with self.assertRaises(ValueError):
            FrameRef("clock", "cam", True, 1, 640, 480)
        with self.assertRaises(ValueError):
            Detection((0, 0, 80, float("nan")), 0.9)

    def test_profiles_parse_and_physical_flag_rejected(self):
        for name in ("sim", "reference", "kv260", "experiment.sim"):
            load_config("config/runtime." + name + ".json")
        data = load_config()
        data["motion"]["physical_actuation"] = True
        with self.assertRaises(ValueError):
            validate_config(data)

    def test_variable_live_configuration_requires_calibration(self):
        config = load_config("config/runtime.reference.json")
        config["freshness"]["policy"] = "variable"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_synthetic_detector_cannot_be_labeled_real(self):
        config = load_config()
        config["environment"] = "kv260"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_source_imports_and_model_hashes_match(self):
        manifest = json.loads((PROJECT_ROOT / "config/source_import_manifest.json").read_text(encoding="utf-8"))
        for item in manifest["imports"]:
            raw = (PROJECT_ROOT / item["target"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item.get("target_sha256", item["source_sha256"]))
        self.assertTrue(all(item["hash_verified"] for item in doctor(load_config())["reference_models"]))

    def test_kv260_readiness_reports_missing_real_adapter(self):
        value = doctor(load_config("config/runtime.kv260.json"))
        self.assertFalse(value["ready_for_selected_profile"])
        self.assertFalse(value["capabilities"]["physical_actuation"])
        self.assertTrue(any("DPU entrypoint" in item for item in value["issues"]))


class FreshnessTests(unittest.TestCase):
    def test_expiry_equality_and_foreign_clock_rejected(self):
        clock = SimulationClock()
        e = FreshnessPolicy(load_config()["freshness"]).evidence(observed(clock))
        self.assertTrue(e.usable(e.deadline_ms - 1, clock.domain))
        self.assertFalse(e.usable(e.deadline_ms, clock.domain))
        self.assertFalse(e.usable(clock.now_ms(), "foreign-host"))

    def test_speed_shortens_candidate_validity(self):
        clock = SimulationClock()
        cfg = load_config("config/runtime.experiment.sim.json")["freshness"]
        slow = FreshnessPolicy(cfg).evidence(observed(clock, velocity=0.0))
        fast = FreshnessPolicy(cfg).evidence(observed(clock, velocity=-600.0))
        self.assertLess(fast.deadline_ms, slow.deadline_ms)

    def test_recomputing_same_source_cannot_extend_deadline(self):
        clock = SimulationClock()
        cfg = load_config()["freshness"]
        policy = FreshnessPolicy(cfg)
        track = observed(clock)
        first = policy.evidence(track)
        cfg["fixed_ms"] = 500
        self.assertEqual(policy.evidence(track).deadline_ms, first.deadline_ms)

    def test_prediction_does_not_authorize_motion(self):
        clock = SimulationClock()
        track = replace(observed(clock), visible=False)
        e = FreshnessPolicy(load_config()["freshness"]).evidence(track)
        self.assertFalse(e.usable(clock.now_ms(), clock.domain))


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.clock = SimulationClock()
        self.guard = SimulationGuard(self.clock.domain)
        self.guard.recover("camera")
        self.track = observed(self.clock)
        self.guard.select_target(self.track.target_key)
        self.evidence = PositionEvidence(self.track, self.clock.now_ms() + 250, "fixed")

    def command(self, seq=1, evidence=None, **fields):
        command = MotionCommand(self.guard.session_id, self.guard.recovery_generation, seq,
                                evidence or self.evidence, 0.1)
        return replace(command, **fields)

    def test_replay_and_old_recovery_context_rejected(self):
        command = self.command()
        self.assertTrue(self.guard.submit(command, self.clock.now_ms())["accepted"])
        self.assertEqual(self.guard.submit(command, self.clock.now_ms())["reason"], "REPLAY_OR_SEQUENCE")
        self.guard.recover("camera")
        self.assertEqual(self.guard.submit(command, self.clock.now_ms())["reason"], "CONTEXT_MISMATCH")

    def test_recovery_requires_new_observation(self):
        self.guard.submit(self.command(), self.clock.now_ms())
        self.guard.recover("camera")
        self.guard.select_target(self.track.target_key)
        self.assertEqual(self.guard.submit(self.command(), self.clock.now_ms())["reason"], "NEW_OBSERVATION_REQUIRED_AFTER_RECOVERY")

    def test_same_source_extension_rejected(self):
        self.guard.submit(self.command(), self.clock.now_ms())
        extended = replace(self.evidence, deadline_ms=self.evidence.deadline_ms + 100)
        self.assertEqual(self.guard.submit(self.command(2, extended), self.clock.now_ms())["reason"], "SOURCE_DEADLINE_EXTENSION")

    def test_camera_and_target_generation_rejected(self):
        foreign = replace(self.track, frame=replace(self.track.frame, camera_epoch="old-camera"))
        foreign_evidence = replace(self.evidence, track=foreign)
        self.assertEqual(self.guard.submit(self.command(evidence=foreign_evidence), self.clock.now_ms())["reason"], "CAMERA_OR_TARGET_GENERATION_MISMATCH")
        changed = replace(self.evidence, track=replace(self.track, generation=2))
        self.assertFalse(self.guard.submit(self.command(evidence=changed), self.clock.now_ms())["accepted"])

    def test_expiry_and_axis_range(self):
        self.assertFalse(self.guard.submit(self.command(requested_axis=2.0), self.clock.now_ms())["accepted"])
        self.guard.submit(self.command(), self.clock.now_ms())
        status = self.guard.poll(self.evidence.deadline_ms)
        self.assertFalse(status["active"])
        self.assertEqual(status["reason"], "SOURCE_EXPIRED")

    def test_reversed_clock_stops_permission(self):
        self.guard.submit(self.command(), self.clock.now_ms())
        with self.assertRaises(ValueError):
            self.guard.poll(self.clock.now_ms() - 1)
        self.assertFalse(self.guard.active)


class SchedulerTests(unittest.TestCase):
    def test_admission_reserves_next_detection_and_margin(self):
        scheduler = SingleCuScheduler(load_config("config/runtime.experiment.sim.json")["scheduler"])
        required = scheduler.admit_identity(1000, 2000).required_ms
        self.assertFalse(scheduler.admit_identity(1000, 1000 + required).allowed)
        self.assertTrue(scheduler.admit_identity(1000, 1001 + required).allowed)

    def test_periodic_baseline_does_not_starve_identity(self):
        scheduler = SingleCuScheduler(load_config()["scheduler"])
        self.assertFalse(scheduler.admit_identity(1000, 1250).allowed)
        for _ in range(2):
            scheduler.run("detection", lambda: None)
        self.assertTrue(scheduler.admit_identity(1000, 1250).allowed)
        scheduler.run("identity", lambda: None)
        self.assertFalse(scheduler.admit_identity(1000, 1250).allowed)

    def test_concurrent_inference_is_not_started(self):
        scheduler = SingleCuScheduler(load_config()["scheduler"])
        entered, release = threading.Event(), threading.Event()
        def blocking():
            entered.set()
            release.wait(1)
        worker = threading.Thread(target=lambda: scheduler.run("detection", blocking))
        worker.start()
        self.assertTrue(entered.wait(0.5))
        try:
            with self.assertRaises(RuntimeError):
                scheduler.run("identity", lambda: None)
        finally:
            release.set()
            worker.join(1)

    def test_measured_overrun_changes_reservation(self):
        scheduler = SingleCuScheduler(load_config()["scheduler"])
        scheduler.observe("identity", 400)
        self.assertEqual(scheduler.estimated_ms("identity"), 400)
        self.assertEqual(scheduler.overruns["identity"], 1)


class IdentityTests(unittest.TestCase):
    def store(self, path=":memory:", model="synthetic"):
        store = IdentityStore(path, model, 4, 0.85, 0.1)
        self.addCleanup(store.close)
        return store

    def test_explicit_enrollment_unknown_known_delete(self):
        store = self.store()
        vector = (1.0, 0.0, 0.0, 0.0)
        self.assertEqual(store.match(vector).state, "UNKNOWN")
        with self.assertRaises(ValueError):
            store.enroll("visitor", "访客", vector)
        store.enroll("visitor", "访客", vector, consent=True)
        matched = store.match(vector)
        self.assertEqual(matched.state, "KNOWN")
        store.delete("visitor")
        self.assertGreater(store.revision, matched.revision)
        self.assertEqual(store.match(vector).state, "UNKNOWN")

    def test_ambiguity_and_invalid_vectors(self):
        store = self.store()
        for key in ("a", "b"):
            store.enroll(key, key, (1.0, 0.0, 0.0, 0.0), consent=True)
        self.assertEqual(store.match((1.0, 0.0, 0.0, 0.0)).state, "AMBIGUOUS")
        for bad in ((0, 0, 0, 0), (1, 0), (1, float("inf"), 0, 0)):
            with self.assertRaises(ValueError):
                store.match(bad)

    def test_persistence_and_model_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "identities.sqlite3"
            first = IdentityStore(path, "model-a", 4, 0.85, 0.1)
            first.enroll("visitor", "访客", (1, 0, 0, 0), consent=True)
            first.close()
            with_model_a = IdentityStore(path, "model-a", 4, 0.85, 0.1)
            with_model_b = IdentityStore(path, "model-b", 4, 0.85, 0.1)
            try:
                self.assertEqual(with_model_a.match((1, 0, 0, 0)).state, "KNOWN")
                self.assertEqual(with_model_b.match((1, 0, 0, 0)).state, "UNKNOWN")
            finally:
                with_model_a.close()
                with_model_b.close()


class SessionTests(unittest.TestCase):
    def test_dialogue_lifetime_is_independent_of_position_lifetime(self):
        manager, token, request = session_request()
        self.assertGreater(request["scene_state"]["valid_until_ms"], 1250)
        result = manager.accept(token, response_for(token), 2000, token.target_key)
        self.assertTrue(result["accepted"])
        self.assertFalse(manager.accept(token, response_for(token), 2001, token.target_key)["accepted"])

    def test_cancelled_or_changed_target_reply_rejected(self):
        manager, token, _ = session_request()
        result = manager.accept(token, response_for(token), 1200, ("camera", 1, 2))
        self.assertEqual(result["reason"], "TARGET_GENERATION_CHANGED")
        manager.cancel()
        self.assertFalse(manager.accept(token, response_for(token), 1200, token.target_key)["accepted"])

    def test_expiry_equality_rejected(self):
        manager, token, _ = session_request()
        self.assertEqual(manager.accept(token, response_for(token), token.deadline_ms, token.target_key)["reason"], "RESPONSE_EXPIRED")

    def test_scene_mismatch_unattached_visual_claim_and_control_denied(self):
        manager, token, _ = session_request()
        for changes in ({"scene_seq_used": 2}, {"visual_claims": [{"fact": "person_present"}]},
                        {"control_requests": [{"pwm": 1500}]}, {"protocol_version": "wrong"}, {"scene_seq_used": True}):
            result = manager.accept(token, response_for(token, **changes), 1200, token.target_key)
            self.assertFalse(result["accepted"], changes)

    def test_schema_subset_rejects_unknown_keywords(self):
        with self.assertRaises(ValueError):
            check("text", {"type": "string", "pattern": "unsafe_to_ignore"}, {})
        schema = LegacySchemaSubset()
        manager, token, _ = session_request()
        self.assertFalse(schema.validate_response(response_for(token, unexpected=True)).ok)


class IntegrationTests(unittest.TestCase):
    def test_full_fixed_and_variable_software_scenarios(self):
        for profile in ("config/runtime.sim.json", "config/runtime.experiment.sim.json"):
            value = run_scenario(load_config(profile))
            self.assertTrue(value["passed"], value["scenario_checks"])
            self.assertEqual(value["evidence_scope"], "PC_SYNTHETIC_SOFTWARE_INTEGRATION")

    def test_latest_frame_slot_keeps_only_newest(self):
        clock, slot = SimulationClock(), LatestFrameSlot()
        for frame_id in range(1, 101):
            slot.put(synthetic_frame(clock, "camera", frame_id))
        self.assertEqual(slot.dropped, 99)
        self.assertEqual(slot.take().ref.frame_id, 100)
        self.assertIsNone(slot.take())

    def test_lost_track_requires_new_generation_and_real_observation(self):
        clock = SimulationClock()
        with AuraRuntime(load_config(), clock) as app:
            epoch = app.start_camera("camera")
            for frame_id in (1, 2):
                clock.advance(40)
                app.process_frame(synthetic_frame(clock, epoch, frame_id))
            original = app.target.target_key
            clock.advance(40)
            app.process_frame(synthetic_frame(clock, epoch, 3, detections=False))
            self.assertIsNone(app.target)
            self.assertFalse(app.guard.active)
            clock.advance(40)
            app.process_frame(synthetic_frame(clock, epoch, 4))
            self.assertNotEqual(app.target.target_key, original)

    def test_identity_failure_does_not_stop_detection(self):
        clock = SimulationClock()
        with AuraRuntime(load_config(), clock) as app:
            epoch = app.start_camera("camera")
            for frame_id in (1, 2, 3):
                clock.advance(40)
                accepted = app.process_frame(synthetic_frame(clock, epoch, frame_id, embedding=[0, 0]))
                self.assertTrue(accepted["accepted"])
            self.assertGreater(app.trace.counts["identity.error"], 0)
            self.assertTrue(app.guard.active)

    def test_async_slow_host_does_not_block_local_expiry(self):
        entered, release = threading.Event(), threading.Event()
        def backend(request):
            entered.set()
            release.wait(1)
            return {"protocol_version": "1.0", "request_id": request["request_id"],
                    "scene_seq_used": request["scene_state"]["scene_seq"], "reply_text": "你好"}
        clock = SimulationClock()
        with AuraRuntime(load_config(), clock, host_backend=backend) as app:
            epoch = app.start_camera("camera")
            for frame_id in (1, 2):
                clock.advance(40)
                app.process_frame(synthetic_frame(clock, epoch, frame_id))
            token = app.ask("你好")
            self.assertTrue(entered.wait(0.5))
            clock.advance(300)
            app.tick()
            self.assertFalse(app.guard.active)
            app.cancel()
            release.set()
            self.assertTrue(wait_until(app, lambda: app.trace.counts["dialogue.result"] > 0))
            self.assertFalse(app.session.playback_allowed(token))

    def test_speaker_requires_registered_window_current_generation_and_margin(self):
        clock = SimulationClock()
        with AuraRuntime(load_config(), clock) as app:
            epoch = app.start_camera("camera")
            for frame_id in (1, 2):
                clock.advance(40)
                app.process_frame(synthetic_frame(clock, epoch, frame_id))
            window = app.register_speaker_window("window", clock.now_ms()-40, clock.now_ms(), clock.now_ms()+500)
            suggestion = replace(window, candidates=((app.target.track_id, app.target.generation, 0.95),))
            self.assertTrue(app.apply_speaker_suggestion(suggestion)["accepted"])
            self.assertFalse(app.apply_speaker_suggestion(suggestion)["accepted"])
            window = app.register_speaker_window("expired-position", clock.now_ms()-40, clock.now_ms(), clock.now_ms()+500)
            clock.advance(300)
            self.assertFalse(app.apply_speaker_suggestion(replace(window, candidates=((1, 1, 0.95),)))["accepted"])

    def test_replay_and_trace_are_marked_software_and_contain_no_raw_media(self):
        with tempfile.TemporaryDirectory() as temp:
            result = replay(load_config(), PROJECT_ROOT / "data/golden/framework_frames.jsonl", Path(temp))
            self.assertEqual(result["replay_records"], 6)
            self.assertFalse(result["physical_actuation"])
            records = [json.loads(line) for line in (Path(temp)/"trace.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(row["environment"] == "simulation" for row in records))
            self.assertFalse(any("image" in row or "transcript" in row for row in records))

    def test_inline_bus_cannot_fill_and_default_diagnostics_are_preserved(self):
        bus = EventBus(max_size=2, retain_sync_events=False)
        seen = []
        bus.subscribe(lambda event: seen.append(event.event_type))
        for _ in range(1000):
            bus.publish(EventEnvelope(EventType.AUDIO_CANCEL_REQUESTED, "test", 1))
        self.assertEqual(len(seen), 1000)
        self.assertEqual(bus.current_size, 0)
        diagnostics = EventBus(max_size=2)
        diagnostics.publish(EventEnvelope("test", "test", 1))
        self.assertEqual(diagnostics.current_size, 1)


if __name__ == "__main__":
    unittest.main()
