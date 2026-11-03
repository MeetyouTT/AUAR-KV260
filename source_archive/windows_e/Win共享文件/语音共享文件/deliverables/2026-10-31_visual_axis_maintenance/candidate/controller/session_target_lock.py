"""Anonymous face ownership survives stopped segments; this grants no motion.

The image controller remains responsible for quality and source authority. This
guard only rejects a changed owner/context or replay across controller resets.
Only constructing a new operator-requested session releases its target lock.
"""
from common.motion_observation import ObservationError, validate


class SessionTargetLock:
    def __init__(self):
        self.context = self.source = self.payload = None

    @staticmethod
    def context_of(packet):
        target = packet['target']
        return (packet['board_boot_id'], packet['service_epoch'], packet['camera_epoch'],
                packet['frame_width'], packet['frame_height'], packet['mirror_horizontal'],
                target['track_id'], target['track_generation'])

    @classmethod
    def payload_of(cls, packet):
        target = packet['target']
        return (packet['source_kind'], packet['target_kind'], cls.context_of(packet),
                tuple(target['box']), target['score'], packet.get('face_detection_mono_ms'))

    def check(self, packet, boot, now_ms, *, allow_fixture=False):
        """Return (failure reason, duplicate); never grant/extend image authority."""
        if self.context is None:
            return None, False
        if isinstance(packet, dict):
            # Preserve the original immediate-STOP fault classes. Only a
            # same-board visual owner change may use full-pulse QUIESCE.
            if packet.get('board_boot_id') != self.context[0]:
                return 'BOOT_CHANGED', False
            if packet.get('mirror_horizontal') is not True:
                return 'UNREVIEWED_ORIENTATION', False
            if (packet.get('frame_width'), packet.get('frame_height')) != self.context[3:5]:
                return 'FACE_GEOMETRY_CHANGED', False
            if (packet.get('service_epoch'), packet.get('camera_epoch')) != self.context[1:3]:
                return 'SESSION_FACE_CONTEXT_CHANGED', False
        try:
            checked = validate(packet, boot, now_ms, allow_fixture=allow_fixture)
        except ObservationError:
            # Preserve all existing malformed/lost/expired-source STOP paths.
            return None, False
        if self.context_of(checked) != self.context:
            return 'SESSION_FACE_TARGET_CHANGED', False
        source = (checked['source_frame_id'], checked['source_mono_ms'])
        if source == self.source:
            if self.payload_of(checked) != self.payload:
                return 'SESSION_SOURCE_MUTATED', False
            anchor = checked.get('face_detection_mono_ms')
            if type(anchor) is int and now_ms >= anchor + 500:
                return None, False  # The controller must execute its expiry STOP.
            return None, True
        if source[0] <= self.source[0] or source[1] <= self.source[1]:
            return 'SESSION_SOURCE_REORDERED', False
        return None, False

    def commit(self, packet):
        """Called only after the existing controller admits a new actual image."""
        self.context = self.context_of(packet)
        self.source = (packet['source_frame_id'], packet['source_mono_ms'])
        self.payload = self.payload_of(packet)

    def status(self):
        return dict(locked=self.context is not None,
            track_id=None if self.context is None else self.context[6],
            track_generation=None if self.context is None else self.context[7],
            reset_requires_new_session=True, identity_authenticated=False,
            personal_memory_authorized=False)
