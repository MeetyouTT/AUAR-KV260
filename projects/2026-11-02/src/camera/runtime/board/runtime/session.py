"""Board-owned request, target and playback generations; host clocks unused."""
import copy
from dataclasses import dataclass
import uuid
from board.runtime.validator import ValidationChain, ValidationContext
from host.model_service.schema import LegacySchemaSubset


@dataclass(frozen=True)
class RequestToken:
    request_id: str
    generation: int
    target_key: object
    scene_seq: int
    deadline_ms: int


class SessionManager:
    def __init__(self, config):
        self.config = config
        self.generation = 0
        self.pending = None
        self.request = None
        self.playback_token = None
        self.validator = ValidationChain(schema=LegacySchemaSubset())

    def cancel(self):
        self.generation += 1
        self.pending = self.request = self.playback_token = None

    def begin(self, transcript, scene, target_key, now_ms):
        if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 2000:
            raise ValueError("Expected a nonempty transcript <=2000 characters")
        self.cancel()
        request_id = uuid.uuid4().hex
        deadline = now_ms + self.config["timeout_ms"]
        # This is dialogue context validity, not the short position deadline.
        scene = copy.deepcopy(scene)
        scene["valid_until_ms"] = deadline
        request = {"protocol_version": "1.0", "request_id": request_id,
                   "audio_generation_id": self.generation, "transcript": transcript.strip(),
                   "scene_state": scene, "allowed_emotions": list(self.config["allowed_emotions"]),
                   "allowed_avatar_actions": list(self.config["allowed_avatar_actions"])}
        result = self.validator.validate_request(request)
        if not result.ok:
            raise ValueError("Invalid legacy request: " + str(result.to_dict()))
        token = RequestToken(request_id, self.generation, target_key, scene["scene_seq"], deadline)
        self.pending, self.request = token, copy.deepcopy(request)
        return token, request

    def accept(self, token, response, now_ms, current_target_key):
        if token != self.pending or token.generation != self.generation:
            return {"accepted": False, "reason": "STALE_REQUEST_GENERATION"}
        if now_ms >= token.deadline_ms:
            return {"accepted": False, "reason": "RESPONSE_EXPIRED"}
        if token.target_key != current_target_key:
            return {"accepted": False, "reason": "TARGET_GENERATION_CHANGED"}
        result = self.validator.schema.validate_response(response)
        if not result.ok:
            return {"accepted": False, "reason": "RESPONSE_SCHEMA", "issues": result.to_dict()}
        if response.get("scene_seq_used") != token.scene_seq:
            return {"accepted": False, "reason": "SCENE_REFERENCE_MISMATCH"}
        # V1 carries text/scene metadata only, not actual image/audio media.
        if response.get("visual_claims"):
            return {"accepted": False, "reason": "IMAGE_BACKEND_NOT_ATTACHED"}
        ctx = ValidationContext(request_id=token.request_id, scene_state=self.request["scene_state"],
                                scene_seq=token.scene_seq, audio_generation_id=self.generation,
                                request_audio_generation_id=token.generation, now_ms=now_ms,
                                max_reply_len=500, allowed_emotions=tuple(self.config["allowed_emotions"]),
                                allowed_avatar_actions=tuple(self.config["allowed_avatar_actions"]))
        result = self.validator.validate_response(response, ctx)
        if not result.ok:
            return {"accepted": False, "reason": "RESPONSE_VALIDATION", "issues": result.to_dict()}
        self.playback_token = token
        self.pending = self.request = None
        return {"accepted": True, "reason": "VALIDATED_TEXT_RESPONSE"}

    def playback_allowed(self, token):
        return token == self.playback_token and token.generation == self.generation
