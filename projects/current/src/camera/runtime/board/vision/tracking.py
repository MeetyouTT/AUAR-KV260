"""IoU reference reuse and optional author-API ByteTrack integration."""
from types import SimpleNamespace
from common.contracts import TrackObservation
from .reference_core import FaceTracks, valid_box


class IouReferenceTracker:
    kind = "IOU_REFERENCE_NOT_BYTETRACK"

    def __init__(self, epoch, config):
        self.tracker = FaceTracks(epoch, lost_s=config["lost_ms"] / 1000.0,
                                  confirm_observations=config["confirm_observations"])
        self.last_visible = set()
        self.generations = {}

    def update(self, frame, detections):
        # FaceTracks uses the box and score only; synthetic landmarks are not
        # exposed as face landmarks and are never used by identity inference.
        rows = [list(d.box) + [0.0] * 10 + [d.score] for d in detections]
        result = self.tracker.update(rows, frame.frame_id, frame.captured_at_ms / 1000.0,
                                     frame.width, frame.height)
        # Lost/predicted boxes never become new source observations.
        observed = []
        for t in result["tracks"]:
            if not t["visible"] or t["frame_id"] != frame.frame_id:
                continue
            tid = t["track_id"]
            generation = self.generations.get(tid, 0)
            if tid not in self.last_visible:
                generation += 1
            self.generations[tid] = generation
            observed.append(TrackObservation(frame, tid, generation, tuple(t["box"]),
                                             t["score"], t["velocity"][0], True, t["confirmed"]))
        self.last_visible = {t.track_id for t in observed}
        retained = set(self.tracker.tracks)
        self.generations = {k: v for k, v in self.generations.items() if k in retained}
        return observed


class ByteTrackAdapter:
    kind = "BYTETRACK_AUTHOR_API"

    def __init__(self, epoch, config, tracker=None):
        if tracker is None:
            from yolox.tracker.byte_tracker import BYTETracker
            args = SimpleNamespace(track_thresh=config["track_threshold"],
                                   track_buffer=config["track_buffer"],
                                   match_thresh=config["match_threshold"], mot20=False)
            tracker = BYTETracker(args, frame_rate=config["frame_rate"])
        self.tracker, self.previous = tracker, {}
        self._last_frame = None
        self._last_time = None
        self._update_index = 0

    def update(self, frame, detections):
        import numpy as np
        if self._last_frame is not None and (frame.frame_id <= self._last_frame or frame.captured_at_ms <= self._last_time):
            raise ValueError("ByteTrack source must advance")
        rows = [[d.box[0], d.box[1], d.box[0] + d.box[2], d.box[1] + d.box[3], d.score]
                for d in detections]
        # Preserve low-score detections; call update even on an empty (0,5) array.
        array = np.asarray(rows, dtype=np.float32).reshape(-1, 5)
        self._update_index += 1
        output = self.tracker.update(array, (frame.height, frame.width), (frame.height, frame.width))
        result = []
        for t in output:
            if not t.is_activated or t.frame_id != self.tracker.frame_id:
                continue
            key = int(t.track_id)
            box = valid_box(tuple(float(v) for v in t.tlwh), frame.width, frame.height)
            if box is None:
                continue
            old = self.previous.get(key)
            generation, velocity = (old[0] if old else 1), 0.0
            if old and old[3] != self._update_index - 1:
                generation += 1  # conservative ownership reset after a visibility gap
            elif old:
                dt = (frame.captured_at_ms - old[1]) / 1000.0
                velocity = (box[0] + box[2] / 2 - old[2]) / dt
            self.previous[key] = (generation, frame.captured_at_ms, box[0] + box[2] / 2, self._update_index)
            result.append(TrackObservation(frame, key, generation, tuple(box), float(t.score), velocity, True, True))
        self._last_frame, self._last_time = frame.frame_id, frame.captured_at_ms
        # Bound retained history to IDs still in the author's active/lost lists.
        retained = {int(t.track_id) for t in list(getattr(self.tracker, "tracked_stracks", []))
                    + list(getattr(self.tracker, "lost_stracks", []))} | {t.track_id for t in result}
        self.previous = {k: v for k, v in self.previous.items() if k in retained}
        return result


def create_tracker(epoch, config):
    if config["tracker"] == "bytetrack":
        return ByteTrackAdapter(epoch, config)
    return IouReferenceTracker(epoch, config)
