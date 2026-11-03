"""Board delivery gate for the existing aura-runtime-1 binary media contract."""
from dataclasses import dataclass
import hashlib
import uuid
from common.contracts import finite, integer
from host.model_service.protocol import (
    QARequest, QAResponse, SegmentLedger, TargetKey, TargetLifecycle,
    validate_request, validate_response_for_delivery,
)


@dataclass(frozen=True)
class MediaRequestToken:
    request_id: int
    generation: int
    utterance_id: int
    target_key: object
    deadline_ms: int


class MediaSessionManager:
    def __init__(self, boot_id, generation_fn, timeout_ms, allow_fixture=False):
        self.boot_id, self.session_id = boot_id, uuid.uuid4().hex
        self.generation_fn = generation_fn
        self.timeout_ms, self.allow_fixture = timeout_ms, allow_fixture
        self.counter = 0
        self.active = self.playback_token = None
        self.ledger = SegmentLedger()

    def cancel(self):
        self.active = self.playback_token = None
        self.ledger.reset(-1, -1)

    def begin(self, audio, pcm, target_key, now_ms, image=None, image_bytes=None, question_text=None):
        sizes = {"S16_LE": 2, "S32_LE": 4, "F32_LE": 4}
        fmt = audio.fmt
        if (not integer(audio.audio_epoch, 1) or not integer(audio.first_sample_index)
                or not integer(audio.sample_count, 1) or not integer(fmt.rate_hz, 1)
                or not integer(fmt.channels, 1) or fmt.sample_format not in sizes
                or not isinstance(pcm, bytes) or len(pcm) > 16 * 1024 * 1024
                or len(pcm) != audio.sample_count * fmt.channels * sizes[fmt.sample_format]):
            raise ValueError("PCM format/sample count/payload mismatch")
        if image is not None:
            if (not isinstance(image_bytes, bytes) or not image_bytes or len(image_bytes) > 8 * 1024 * 1024
                    or hashlib.sha256(image_bytes).hexdigest() != image.sha256
                    or not integer(image.frame_id, 1) or not integer(image.camera_epoch, 1)
                    or not integer(image.age_ms)):
                raise ValueError("Image payload/reference mismatch")
        elif image_bytes is not None:
            raise ValueError("Image bytes require a source reference")
        self.counter += 1
        deadline = now_ms + self.timeout_ms
        token = MediaRequestToken(self.counter, self.generation_fn(), self.counter, target_key, deadline)
        target = TargetKey(target_key[1], target_key[2], TargetLifecycle.CONFIRMED) if target_key else None
        request = QARequest(self.boot_id, self.session_id, token.request_id, token.generation,
                            token.utterance_id, deadline * 1000000, audio, image, target, question_text)
        errors = validate_request(request)
        if errors:
            raise ValueError(errors[0].detail)
        self.active = token
        self.ledger.reset(token.request_id, token.generation)
        return token, {"__aura_media__": True, "request": request, "pcm": pcm, "image_bytes": image_bytes}

    def accept(self, token, response, now_ms, current_target_key):
        if token != self.active or token.generation != self.generation_fn():
            return {"accepted": False, "reason": "STALE_MEDIA_GENERATION"}
        if not isinstance(response, QAResponse):
            return {"accepted": False, "reason": "MEDIA_RESPONSE_TYPE"}
        if (response.generation != token.generation or response.utterance_id != token.utterance_id
                or response.board_deadline_ns != token.deadline_ms * 1000000):
            return {"accepted": False, "reason": "MEDIA_CONTEXT_OR_DEADLINE_MISMATCH"}
        error = validate_response_for_delivery(response, boot_id=self.boot_id, session_id=self.session_id,
                                              request_id=token.request_id, generation=token.generation,
                                              target_still_valid=current_target_key == token.target_key,
                                              expired=now_ms >= token.deadline_ms)
        if error is not None:
            return {"accepted": False, "reason": error.code.value}
        if not response.complete or response.error is not None:
            return {"accepted": False, "reason": response.error.code.value if response.error else "MEDIA_INCOMPLETE"}
        if response.is_fixture and not self.allow_fixture:
            return {"accepted": False, "reason": "FIXTURE_MEDIA_NOT_ALLOWED"}
        if not isinstance(response.answer_text, str) or not 0 < len(response.answer_text) <= 500:
            return {"accepted": False, "reason": "MEDIA_ANSWER_LENGTH"}
        if not 0 < len(response.segments) <= 256:
            return {"accepted": False, "reason": "MEDIA_SEGMENT_COUNT"}
        indices = [s.segment_index for s in response.segments]
        if any(not integer(index) for index in indices) or sorted(indices) != list(range(len(indices))):
            return {"accepted": False, "reason": "MEDIA_SEGMENT_GAP_OR_DUPLICATE"}
        total = 0
        expected_format = response.segments[0].fmt
        sizes = {"S16_LE": 2, "S32_LE": 4, "F32_LE": 4}
        for segment in response.segments:
            fmt = segment.fmt
            if (fmt != expected_format or not integer(fmt.rate_hz, 1) or not integer(fmt.channels, 1)
                    or fmt.sample_format not in sizes or not isinstance(segment.pcm, bytes)
                    or not segment.pcm or len(segment.pcm) % (fmt.channels * sizes[fmt.sample_format])):
                return {"accepted": False, "reason": "MEDIA_PCM_FORMAT"}
            total += len(segment.pcm)
        if total > 16 * 1024 * 1024 or any(not finite(t.duration_ms) or t.duration_ms < 0 for t in response.timings):
            return {"accepted": False, "reason": "MEDIA_SIZE_OR_TIMING"}
        for segment in response.segments:
            if not self.ledger.offer(response, segment):
                return {"accepted": False, "reason": "MEDIA_SEGMENT_REPLAY"}
        self.playback_token, self.active = token, None
        return {"accepted": True, "reason": "VALIDATED_MEDIA_RESPONSE", "is_fixture": response.is_fixture,
                "segment_count": len(response.segments), "pcm_bytes": total}

    def playback_allowed(self, token):
        return self.playback_token == token and token.generation == self.generation_fn()
