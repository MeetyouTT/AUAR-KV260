"""Validate an ASD suggestion against the current board-owned track window."""
from dataclasses import dataclass
from common.contracts import finite, integer


@dataclass(frozen=True)
class SpeakerSuggestion:
    window_id: str
    clock_domain: str
    camera_epoch: str
    started_at_ms: int
    ended_at_ms: int
    deadline_ms: int
    candidates: tuple  # ((track_id, generation, score), ...)

    def __post_init__(self):
        if (not self.window_id or not self.clock_domain or not self.camera_epoch
                or not all(integer(v) for v in (self.started_at_ms, self.ended_at_ms, self.deadline_ms))
                or not self.started_at_ms <= self.ended_at_ms < self.deadline_ms):
            raise ValueError("Invalid audio/video window")
        for track_id, generation, score in self.candidates:
            if not integer(track_id, 1) or not integer(generation, 1) or not finite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid speaker candidate")


def select_speaker(suggestion, now_ms, clock_domain, camera_epoch, tracks, threshold, margin):
    if (suggestion.clock_domain != clock_domain or suggestion.camera_epoch != camera_epoch
            or not suggestion.ended_at_ms <= now_ms < suggestion.deadline_ms):
        return {"accepted": False, "reason": "SPEAKER_WINDOW_EXPIRED_OR_FOREIGN"}
    visible = {t.target_key: t for t in tracks if t.visible and t.confirmed}
    candidates = sorted(((score, (camera_epoch, tid, generation)) for tid, generation, score in suggestion.candidates), reverse=True)
    if len({key for _, key in candidates}) != len(candidates):
        return {"accepted": False, "reason": "DUPLICATE_SPEAKER_TARGET"}
    if not candidates or candidates[0][0] < threshold:
        return {"accepted": False, "reason": "NO_CONFIDENT_SPEAKER"}
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < margin:
        return {"accepted": False, "reason": "SPEAKER_AMBIGUOUS"}
    key = candidates[0][1]
    if key not in visible:
        return {"accepted": False, "reason": "SPEAKER_TRACK_GENERATION_STALE"}
    return {"accepted": True, "target_key": key, "reason": "CURRENT_TRACK_CONFIRMED"}
