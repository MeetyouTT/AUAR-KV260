"""Source-frame contract for pan control; never use UI refresh time as evidence."""
import copy
import math

PROTOCOL = 'aura-motion-observation-1'
PATH = '/v1/motion/observation'
MAX_AGE_MS = 250


class ObservationError(ValueError):
    pass


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 2**53-1


def validate(value, boot_id, now_ms, *, allow_fixture=False):
    def require(ok, reason):
        if not ok:
            raise ObservationError(reason)
    require(isinstance(value, dict) and value.get('protocol_version') == PROTOCOL, 'INVALID_PROTOCOL')
    require(integer(now_ms), 'INVALID_CLOCK')
    require(value.get('board_boot_id') == boot_id, 'BOOT_CHANGED')
    require(value.get('source_kind') == 'actual' or
            allow_fixture and value.get('source_kind') == 'fixture', 'NON_ACTUAL_SOURCE')
    for field in ('camera_epoch', 'service_epoch'):
        require(isinstance(value.get(field), str) and 0 < len(value[field]) <= 96, 'INVALID_CONTEXT')
    require(value.get('state') == 'READY', 'SOURCE_' + str(value.get('state', 'INVALID'))[:48])
    source = value.get('source_mono_ms')
    require(integer(source) and integer(value.get('source_frame_id'), 1), 'INVALID_SOURCE')
    require(0 <= now_ms-source < MAX_AGE_MS, 'SOURCE_EXPIRED')
    require(value.get('deadline_mono_ms') == source+MAX_AGE_MS, 'SOURCE_DEADLINE_CHANGED')
    require(value.get('mirror_horizontal') is True, 'UNREVIEWED_ORIENTATION')
    width, height = value.get('frame_width'), value.get('frame_height')
    require(integer(width, 2) and integer(height, 2) and width <= 4096 and height <= 2160, 'INVALID_GEOMETRY')
    target = value.get('target')
    require(isinstance(target, dict) and integer(target.get('track_id'), 1)
            and integer(target.get('track_generation'), 1), 'INVALID_TARGET')
    box = target.get('box')
    require(isinstance(box, list) and len(box) == 4 and all(number(x) for x in box), 'INVALID_BOX')
    x, y, w, h = box
    require(min(x, y) >= 0 and min(w, h) > 0 and x+w <= width and y+h <= height, 'INVALID_BOX')
    require(number(target.get('score')) and 0 <= target['score'] <= 1, 'INVALID_SCORE')
    return copy.deepcopy(value)
