"""AURA composition root. Call from one owner thread; IO workers use mailboxes."""
from dataclasses import asdict, replace
import time
import uuid
from common.clock import MonotonicClock
from common.config import project_path, validate_config
from board.fusion.freshness import FreshnessPolicy
from board.fusion.scheduler import SingleCuScheduler
from board.fusion.speaker import select_speaker
from board.fusion.targets import TargetSelector
from board.identity.store import IdentityStore
from board.motion.guard import SimulationGuard
from board.motion.service import MotionService
from board.vision.backends import create_detector
from board.vision.tracking import create_tracker
from board.interaction.ui_state import UiState
from host.model_service.client import AsyncModelClient
from .event_bus import EventBus, EventEnvelope
from .events import EventType
from .fsm import RuntimeFSM
from .project_log import ProjectTrace
from .session import SessionManager
from .media_session import MediaRequestToken, MediaSessionManager


class AuraRuntime:
    def __init__(self, config, clock=None, trace_path=None, detector=None, host_backend=None):
        self.config = validate_config(config)
        self.clock = clock or MonotonicClock()
        self.bus = EventBus(max_size=128, dispatch_async=False, now_ms_fn=self.clock.now_ms,
                            retain_sync_events=False)
        self.fsm = RuntimeFSM(bus=self.bus)
        self.ui = UiState(event_bus=self.bus)
        self.trace = ProjectTrace(config["release_id"], config["environment"], trace_path)
        self.detector = detector or create_detector(config["vision"])
        self.scheduler = SingleCuScheduler(config["scheduler"])
        self.freshness = FreshnessPolicy(config["freshness"])
        self.selector = TargetSelector(config["vision"]["target_policy"])
        self.guard = SimulationGuard(self.clock.domain, config["motion"]["backend"] == "simulation_guard")
        self.motion = MotionService(self.guard)
        self.session = SessionManager(config["dialogue"])
        self.media_session = MediaSessionManager(self.clock.domain, lambda: self.session.generation,
                                                 config["dialogue"]["timeout_ms"],
                                                 allow_fixture=config["environment"] == "simulation")
        self.host = None if config["dialogue"]["backend"] == "disabled" else AsyncModelClient(config["dialogue"], host_backend)
        identity = config["identity"]
        db_path = identity["database"]
        self.identities = IdentityStore(db_path if db_path == ":memory:" else project_path(db_path),
                                        identity["model_id"], identity["dimension"],
                                        identity["threshold"], identity["ambiguity_margin"])
        self.embedder = None
        self.camera_epoch = None
        self.camera_epoch_number = 0
        self.tracker = None
        self.last_frame = None
        self.tracks = []
        self.target = self.evidence = None
        self.identity_cache = None
        self.scene_seq = 0
        self.camera_online = False
        self.speaker_windows = {}
        self.last_response = None
        self.last_media_response = None
        self.closed = False
        self.ui.set_device("pl", "idle", "software simulation" if self.guard.enabled else "motion disabled")
        self.ui.set_device("audio", "idle", "MCP01 playback adapter pending")
        self.ui.set_device("npu", "idle", self.detector.kind)
        self.trace.record("runtime.started", self.clock.now_ms(), clock_domain=self.clock.domain,
                          detector=self.detector.kind, physical_actuation=False)

    def _emit(self, event_type, payload=None):
        self.bus.publish(EventEnvelope(event_type, "aura-runtime", self.clock.now_ms(), payload or {}))

    def start_camera(self, epoch=None):
        if self.camera_epoch is not None:
            self.camera_lost("CAMERA_EPOCH_CHANGED")
        self.cancel("CAMERA_EPOCH_CHANGED")
        self.camera_epoch = epoch or uuid.uuid4().hex
        self.camera_epoch_number += 1
        self.guard.recover(self.camera_epoch)
        self.tracker = create_tracker(self.camera_epoch, self.config["vision"])
        self.last_frame = None
        self.tracks = []
        self.target = self.evidence = self.identity_cache = None
        self.selector.reset()
        self.speaker_windows.clear()
        self.camera_online = False
        self.trace.record("camera.epoch", self.clock.now_ms(), camera_epoch=self.camera_epoch)
        return self.camera_epoch

    def process_frame(self, frame):
        if self.closed:
            raise RuntimeError("Runtime closed")
        now = self.clock.now_ms()
        ref = frame.ref
        previous = self.last_frame.ref if self.last_frame else None
        reason = None
        if ref.clock_domain != self.clock.domain or ref.camera_epoch != self.camera_epoch:
            reason = "FOREIGN_CLOCK_OR_CAMERA_EPOCH"
        elif ref.captured_at_ms > now:
            reason = "FUTURE_SOURCE_TIME"
        elif previous and (ref.frame_id <= previous.frame_id or ref.captured_at_ms <= previous.captured_at_ms):
            reason = "SOURCE_NOT_ADVANCING"
        cap = (self.config["freshness"]["fixed_ms"] if self.config["freshness"]["policy"] == "fixed"
               else self.config["freshness"]["calibration"]["cap_ms"])
        if reason is None and now - ref.captured_at_ms >= cap:
            reason = "INPUT_SOURCE_EXPIRED"
        if reason:
            self.trace.record("frame.rejected", now, frame=ref.to_dict(), reason=reason)
            self.tick()
            return {"accepted": False, "reason": reason}
        started = self.clock.now_ms()
        try:
            detections = self.scheduler.run("detection", lambda: self.detector.detect(frame))
            tracks = self.tracker.update(ref, detections)
        except Exception:
            self.camera_lost("DETECTOR_OR_TRACKER_FAILURE")
            raise
        old_key = self.target.target_key if self.target else None
        old_presence = bool(self.tracks)
        self.last_frame, self.tracks = frame, tracks
        self.target = self.selector.select(tracks)
        key = self.target.target_key if self.target else None
        if old_key != key:
            self.cancel("TARGET_GENERATION_CHANGED")
            self.identity_cache = None
        self.evidence = self.freshness.evidence(self.target) if self.target else None
        now = self.clock.now_ms()
        motion_result = self.motion.update(self.evidence, now)
        self.scene_seq += 1
        if not self.camera_online:
            if self.fsm.state.value == "CAMERA_LOST":
                self._emit(EventType.CAMERA_RECOVERED)
            self.camera_online = True
        self.ui.set_device("camera", "ready", ref.timestamp_semantics)
        if bool(tracks) != old_presence:
            self._emit(EventType.SCENE_PERSON_ENTER if tracks else EventType.SCENE_PERSON_EXIT)
        elif old_key != key and self.target:
            self._emit(EventType.SCENE_TARGET_UPDATE)
        try:
            self._recognize_if_available(frame)
        except Exception as exc:
            # An identity task failure must not tear down the detection loop.
            self.identity_cache = None
            self.trace.record("identity.error", self.clock.now_ms(), error=str(exc))
        scene = self.scene_state()
        self._emit(EventType.SCENE_STATE, scene)
        self.trace.record("frame.processed", now, frame=ref.to_dict(), inference_started_ms=started,
                          inference_completed_ms=now, detections=[asdict(d) for d in detections],
                          tracks=[asdict(t) for t in tracks],
                          detector=self.detector.kind, tracker=self.tracker.kind,
                          target_key=key, deadline_ms=self.evidence.deadline_ms if self.evidence else None,
                          motion=motion_result, identity=self.identity_snapshot())
        self.tick()
        return {"accepted": True, "scene": scene, "motion": motion_result}

    def _recognize_if_available(self, frame):
        cfg = self.config["identity"]
        if cfg["backend"] == "disabled" or self.target is None or self.evidence is None:
            return
        cached = self.identity_cache
        now = self.clock.now_ms()
        if cached and (cached[0] == self.target.target_key and cached[1].revision == self.identities.revision
                       and now < cached[2]):
            return
        admission = self.scheduler.admit_identity(now, self.evidence.deadline_ms)
        self.trace.record("identity.admission", now, **asdict(admission))
        if not admission.allowed:
            return
        if cfg["backend"] == "synthetic":
            vector = frame.image.get("embedding") if isinstance(frame.image, dict) else None
            if vector is None:
                return
            extract = lambda: vector
        else:
            if self.embedder is None:
                from board.identity.backends import CpuSFaceEmbedder
                self.embedder = CpuSFaceEmbedder(cfg, self.detector)
            extract = lambda: self.embedder.extract(frame, self.target)
        embedding = self.scheduler.run("identity", extract)
        result = self.identities.match(embedding)
        self.identity_cache = (self.target.target_key, result, self.clock.now_ms() + cfg["cache_ttl_ms"])
        self.trace.record("identity.matched", self.clock.now_ms(), target_key=self.target.target_key,
                          state=result.state, model_id=cfg["model_id"], store_revision=result.revision)

    def identity_snapshot(self):
        cached = self.identity_cache
        if (cached and self.target and cached[0] == self.target.target_key
                and cached[1].revision == self.identities.revision and self.clock.now_ms() < cached[2]):
            return asdict(cached[1])
        return {"state": "UNKNOWN", "model_id": self.config["identity"]["model_id"]}

    def scene_state(self):
        now = self.clock.now_ms()
        ref = self.last_frame.ref if self.last_frame else None
        valid = self.evidence.deadline_ms if self.evidence else ((ref.captured_at_ms if ref else now) + self.config["freshness"]["fixed_ms"])
        scene = {"schema_version": "1.0", "scene_seq": self.scene_seq,
                 "captured_at_ms": ref.captured_at_ms if ref else now, "valid_until_ms": valid,
                 "camera_state": "online" if self.camera_online else "lost",
                 "people_count": len(self.tracks) if self.camera_online else 0, "recent_events": [],
                 "uncertainty": ["CPU_FACE_REFERENCE"] if self.detector.kind == "CPU_YUNET_REFERENCE" else []}
        if self.target and self.evidence and self.evidence.usable(now, self.clock.domain):
            box = self.target.box
            error = (box[0] + box[2] / 2 - self.target.frame.width / 2) / (self.target.frame.width / 2)
            scene["current_target"] = {"track_id": self.target.track_id,
                                       "position": "center" if abs(error) <= 0.1 else ("left" if error < 0 else "right"),
                                       "confidence": self.target.score, "source_frame_id": self.target.frame.frame_id}
        elif self.target:
            scene["uncertainty"].append("POSITION_SOURCE_EXPIRED")
        return scene

    def ask(self, transcript):
        if self.host is None:
            raise RuntimeError("Dialogue backend disabled")
        self.cancel("NEW_DIALOGUE_ROUND")
        key = self.target.target_key if self.target else None
        token, request = self.session.begin(transcript, self.scene_state(), key, self.clock.now_ms())
        self._emit(EventType.AUDIO_KWS_DETECTED)
        self._emit(EventType.AUDIO_VAD_END)
        self._emit(EventType.DIALOGUE_REQUEST_SENT, {"request_id": token.request_id})
        self.host.submit(token, request)
        self.trace.record("dialogue.requested", self.clock.now_ms(), request_id=token.request_id,
                          generation=token.generation, target_key=key, protocol_version="1.0", media="text_only")
        return token

    def accept_response(self, token, response):
        key = self.target.target_key if self.target else None
        result = self.session.accept(token, response, self.clock.now_ms(), key)
        self.trace.record("dialogue.result", self.clock.now_ms(), request_id=token.request_id, **result)
        if result["accepted"]:
            self.last_response = response
            self._emit(EventType.DIALOGUE_RESPONSE_RECEIVED, response)
        return result

    def attach_media_backend(self, backend):
        if self.host is None:
            raise RuntimeError("Enable a host worker before attaching a media backend")
        self.host.media_backend = backend

    def ask_media(self, audio, pcm, image=None, image_bytes=None, question_text=None):
        if self.host is None or self.host.media_backend is None:
            raise RuntimeError("Media backend/transport not attached")
        if image is not None:
            if (not self.camera_online or self.last_frame is None
                    or image.frame_id != self.last_frame.ref.frame_id
                    or image.camera_epoch != self.camera_epoch_number):
                raise ValueError("Media image must refer to the current camera source")
            # The board owns source age. A caller cannot refresh an old image by
            # supplying age_ms=0; the VLM receives age in the board clock domain.
            age_ms = self.clock.now_ms() - self.last_frame.ref.captured_at_ms
            if age_ms < 0:
                raise ValueError("Media image source time is in the future")
            image = replace(image, age_ms=age_ms)
        self.cancel("NEW_MEDIA_ROUND")
        key = self.target.target_key if self.target else None
        token, payload = self.media_session.begin(audio, pcm, key, self.clock.now_ms(), image, image_bytes, question_text)
        self._emit(EventType.AUDIO_KWS_DETECTED)
        self._emit(EventType.AUDIO_VAD_END)
        self.host.submit(token, payload)
        self.trace.record("media.requested", self.clock.now_ms(), request_id=token.request_id,
                          generation=token.generation, protocol_version="aura-runtime-1",
                          target_key=key, audio_samples=audio.sample_count)
        return token

    def accept_media_response(self, token, response):
        key = self.target.target_key if self.target else None
        result = self.media_session.accept(token, response, self.clock.now_ms(), key)
        self.trace.record("media.result", self.clock.now_ms(), request_id=token.request_id, **result)
        if result["accepted"]:
            self.last_media_response = response
            self.last_response = {"reply_text": response.answer_text, "emotion": "neutral", "avatar_action": ""}
            self._emit(EventType.DIALOGUE_RESPONSE_RECEIVED, self.last_response)
        return result

    def playback_started(self, token):
        if not (self.session.playback_allowed(token) or self.media_session.playback_allowed(token)):
            return False
        self._emit(EventType.AUDIO_PLAYBACK_START, self.last_response or {})
        return True

    def playback_finished(self, token):
        if not (self.session.playback_allowed(token) or self.media_session.playback_allowed(token)):
            return False
        self._emit(EventType.AUDIO_PLAYBACK_STOP)
        self.session.playback_token = None
        self.media_session.playback_token = None
        return True

    def cancel(self, reason="USER_CANCEL"):
        was_active = (self.session.pending is not None or self.session.playback_token is not None
                      or self.media_session.active is not None or self.media_session.playback_token is not None)
        self.session.cancel()
        self.media_session.cancel()
        if was_active:
            self._emit(EventType.AUDIO_CANCEL_REQUESTED)
            self.ui.set_dialogue(thinking=False)
        self.trace.record("dialogue.cancelled", self.clock.now_ms(), reason=reason,
                          generation=self.session.generation)

    def camera_lost(self, reason="CAMERA_LOST"):
        self.cancel(reason)
        self.guard.stop(reason)
        self.camera_online = False
        self.tracks = []
        self.target = self.evidence = self.identity_cache = None
        self.selector.reset()
        self.speaker_windows.clear()
        self._emit(EventType.CAMERA_LOST)
        self.trace.record("camera.lost", self.clock.now_ms(), reason=reason)

    def register_speaker_window(self, window_id, started_at_ms, ended_at_ms, deadline_ms):
        from board.fusion.speaker import SpeakerSuggestion
        window = SpeakerSuggestion(window_id, self.clock.domain, self.camera_epoch,
                                   started_at_ms, ended_at_ms, deadline_ms, ())
        now = self.clock.now_ms()
        if not ended_at_ms <= now < deadline_ms or window_id in self.speaker_windows:
            raise ValueError("Speaker window must be new and current")
        self.speaker_windows = {k: v for k, v in self.speaker_windows.items() if now < v[0].deadline_ms}
        if len(self.speaker_windows) >= 16:
            raise RuntimeError("Speaker window mailbox full")
        self.speaker_windows[window_id] = (window, {t.target_key for t in self.tracks})
        return window

    def apply_speaker_suggestion(self, suggestion):
        registered = self.speaker_windows.get(suggestion.window_id)
        if registered is None:
            result = {"accepted": False, "reason": "UNKNOWN_SPEAKER_WINDOW"}
        else:
            window, keys = registered
            current = self.clock.now_ms()
            same_window = (window.clock_domain, window.camera_epoch, window.started_at_ms, window.ended_at_ms, window.deadline_ms) == (
                suggestion.clock_domain, suggestion.camera_epoch, suggestion.started_at_ms, suggestion.ended_at_ms, suggestion.deadline_ms)
            if not same_window or any((suggestion.camera_epoch, tid, gen) not in keys for tid, gen, score in suggestion.candidates):
                result = {"accepted": False, "reason": "SPEAKER_WINDOW_REFERENCE_MISMATCH"}
            else:
                result = select_speaker(suggestion, current, self.clock.domain, self.camera_epoch, self.tracks,
                                        self.config["dialogue"]["speaker_threshold"], self.config["dialogue"]["speaker_margin"])
                if result["accepted"]:
                    target = next(t for t in self.tracks if t.target_key == result["target_key"])
                    evidence = self.freshness.evidence(target)
                    if not evidence.usable(current, self.clock.domain):
                        result = {"accepted": False, "reason": "CURRENT_POSITION_EXPIRED"}
                    else:
                        old_key = self.target.target_key if self.target else None
                        self.selector.manual_key = target.target_key
                        self.target, self.evidence = target, evidence
                        if old_key != target.target_key:
                            self.cancel("SPEAKER_TARGET_CHANGED")
                            self.identity_cache = None
                        self.motion.update(evidence, current)
                        self._emit(EventType.SCENE_STATE, self.scene_state())
                self.speaker_windows.pop(suggestion.window_id, None)
        self.trace.record("speaker.result", self.clock.now_ms(), window_id=suggestion.window_id, **result)
        return result

    def tick(self):
        self.guard.poll(self.clock.now_ms())
        if self.host:
            for token, response, error in self.host.poll():
                if isinstance(token, MediaRequestToken):
                    if error:
                        self.trace.record("media.error", self.clock.now_ms(), request_id=token.request_id, error=error)
                        if token == self.media_session.active:
                            self._emit(EventType.DIALOGUE_ERROR)
                            self.cancel("MEDIA_HOST_ERROR")
                    else:
                        result = self.accept_media_response(token, response)
                        if not result["accepted"] and token == self.media_session.active:
                            self._emit(EventType.DIALOGUE_ERROR)
                            self.cancel(result["reason"])
                    continue
                if error:
                    self.trace.record("dialogue.error", self.clock.now_ms(), request_id=token.request_id, error=error)
                    if token == self.session.pending:
                        self._emit(EventType.DIALOGUE_ERROR)
                        self.cancel("HOST_ERROR")
                else:
                    result = self.accept_response(token, response)
                    if not result["accepted"] and token == self.session.pending:
                        self._emit(EventType.DIALOGUE_ERROR)
                        self.cancel(result["reason"])
        pending = self.session.pending
        if pending and self.clock.now_ms() >= pending.deadline_ms:
            self._emit(EventType.DIALOGUE_TIMEOUT)
            self.cancel("RESPONSE_TIMEOUT")
        media_pending = self.media_session.active
        if media_pending and self.clock.now_ms() >= media_pending.deadline_ms:
            self._emit(EventType.DIALOGUE_TIMEOUT)
            self.cancel("MEDIA_RESPONSE_TIMEOUT")

    def snapshot(self):
        self.tick()
        return {"schema_version": "aura-project-state-1", "release_id": self.config["release_id"],
                "environment": self.config["environment"], "clock_domain": self.clock.domain,
                "runtime_state": self.fsm.state.value, "scene": self.scene_state(),
                "identity": self.identity_snapshot(), "motion": self.guard.snapshot(),
                "scheduler": self.scheduler.snapshot(), "ui": self.ui.to_dict(),
                "trace_counts": dict(self.trace.counts), "physical_actuation": False,
                "position_evidence_fresh": bool(self.evidence and self.evidence.usable(self.clock.now_ms(), self.clock.domain)),
                "media_backends": {"dialogue": self.config["dialogue"]["backend"],
                                   "runtime_media_port": "attached" if self.host and self.host.media_backend else "not_attached",
                                   "mcp01": "not_connected", "vlm": "not_connected", "light_asd": "port_only"}}

    def close(self):
        if self.closed:
            return
        self.cancel("SHUTDOWN")
        self.guard.stop("SHUTDOWN")
        if self.host:
            self.host.close()
        self.identities.close()
        self.fsm.unbind_bus()
        self.bus.stop()
        self.trace.record("runtime.stopped", self.clock.now_ms(), physical_actuation=False)
        self.trace.close()
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
