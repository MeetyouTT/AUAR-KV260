"""Validate an operator-recorded current reference; never creates evidence."""
import math
import re


def validate_receipt(value, *, boot_id, fdt_sha256, now):
    if value.get('schema') != 'aura-user-observed-fixed-reference-1':
        raise ValueError('CURRENT_REFERENCE_RECEIPT_REQUIRED')
    if value.get('boot_id') != boot_id or value.get('fdt_sha256') != fdt_sha256:
        raise ValueError('REFERENCE_CONTEXT_MISMATCH')
    if (value.get('user_present') is not True or value.get('confirmed_current_position') is not True
            or not isinstance(value.get('user_observation'), str) or not value['user_observation'].strip()):
        raise ValueError('CURRENT_USER_OBSERVATION_REQUIRED')
    if (value.get('reference_us') != 1420 or type(value.get('reference_us')) is not int
            or value.get('bounds_us') != [1402, 1420] or value.get('polarity') != 1
            or value.get('camera_moves_with_axis') is not True):
        raise ValueError('APPROVED_REFERENCE_AND_NARROW_WINDOW_REQUIRED')
    ident = value.get('authorization_id')
    if not isinstance(ident, str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', ident):
        raise ValueError('INVALID_AUTHORIZATION_ID')
    observed, expires = value.get('observed_mono_s'), value.get('expires_mono_s')
    authorized = value.get('authorization_recorded_mono_s', observed)
    if (not all(type(x) in (int, float) and math.isfinite(x) for x in (observed, authorized, expires, now))
            or not 0 <= observed <= authorized <= now or not now + 5 < expires <= authorized + 600):
        raise ValueError('REFERENCE_EXPIRED_OR_FUTURE')
    rb = value.get('stopped_readback')
    fields = ('flags', 'lease_left_ms', 'width_us', 'target_us', 'reference_us', 'session', 'epoch', 'ack_seq', 'reason')
    if (not isinstance(rb, dict) or any(type(rb.get(k)) is not int for k in fields)
            or any(rb[k] != 0 for k in ('flags', 'lease_left_ms', 'reason'))
            or rb['width_us'] != 1420 or rb['target_us'] != 1420
            or any(not 0 <= rb[k] <= 0xffffffff for k in ('session', 'epoch', 'ack_seq'))):
        raise ValueError('STOPPED_REFERENCE_NOT_CONFIRMED')
    return value


def same_stopped_readback(receipt, current):
    keys = ('flags', 'lease_left_ms', 'width_us', 'target_us', 'reference_us', 'session', 'epoch', 'ack_seq', 'reason')
    return all(current.get(k) == receipt['stopped_readback'].get(k) for k in keys)
