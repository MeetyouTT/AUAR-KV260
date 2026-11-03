"""One pulse capability and calibrated angle contract; no device operations."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

BUILD_ID = 0x14202602
HARD_MIN_US = 500
HARD_MAX_US = 2500
CENTER_US = 1420
MIN_LEASE_MS = (HARD_MAX_US + 999) // 1000 + 1
FRAME_US = 20000
FRAME_STEP_US = 4
INITIAL_PWM_MINIMUM_LEASE_MS = (FRAME_US + HARD_MAX_US + 999) // 1000 + 1
PROFILE_SCHEMA = 'aura-pan-angle-profile-1'


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class AngleCalibration:
    center_us: int = CENTER_US
    negative_90_us: object = None
    positive_90_us: object = None
    endpoints_verified: bool = False
    boot_id: str = ''
    setup_id: str = ''
    evidence: str = ''

    def __post_init__(self):
        if type(self.center_us) is not int or self.center_us != CENTER_US:
            raise ValueError('User-confirmed center must remain 1420 us')
        if type(self.endpoints_verified) is not bool:
            raise ValueError('Endpoint verification must be explicit')
        endpoints = (self.negative_90_us, self.positive_90_us)
        for pulse in endpoints:
            if pulse is not None and (type(pulse) is not int or not HARD_MIN_US <= pulse <= HARD_MAX_US):
                raise ValueError('Endpoint pulse outside the declared hardware capability')
        if all(pulse is not None for pulse in endpoints):
            a, b = endpoints
            if not min(a, b) < self.center_us < max(a, b):
                raise ValueError('Two independent endpoints must bracket the center')
        if self.endpoints_verified:
            if (any(pulse is None for pulse in endpoints) or
                    any(not isinstance(v, str) or not v.strip() for v in
                        (self.boot_id, self.setup_id, self.evidence))):
                raise ValueError('Verified endpoints require values, boot/setup and evidence')

    def require_verified(self, boot_id):
        if not self.endpoints_verified or self.boot_id != boot_id:
            raise ValueError('左右90度端点尚未标定，或标定不属于当前启动；中点为1420µs')
        return self

    @property
    def pulse_bounds(self):
        if not self.endpoints_verified:
            raise ValueError('Cannot expose an unmeasured angular working range')
        return min(self.negative_90_us, self.positive_90_us), max(self.negative_90_us, self.positive_90_us)

    def pulse_for_angle(self, angle_deg, boot_id):
        self.require_verified(boot_id)
        if not finite(angle_deg) or not -90 <= angle_deg <= 90:
            raise ValueError('Angle must be within -90..90 degrees')
        endpoint = self.negative_90_us if angle_deg < 0 else self.positive_90_us
        return round(self.center_us + abs(angle_deg) / 90. * (endpoint - self.center_us))

    def angle_for_pulse(self, pulse_us, boot_id):
        self.require_verified(boot_id)
        low, high = self.pulse_bounds
        if not finite(pulse_us) or not low <= pulse_us <= high:
            raise ValueError('Pulse outside calibrated angular range')
        delta = pulse_us - self.center_us
        if delta == 0:
            return 0.
        if delta * (self.negative_90_us - self.center_us) > 0:
            return -90. * delta / (self.negative_90_us - self.center_us)
        return 90. * delta / (self.positive_90_us - self.center_us)


def load_profile(path):
    path = Path(path)
    if path.stat().st_size > 8192:
        raise ValueError('Axis profile too large')
    value = json.loads(path.read_text(encoding='utf-8'))
    keys = {'schema', 'build_id', 'hard_min_us', 'hard_max_us', 'requested_angle_range_deg', 'calibration'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('Invalid complete axis profile')
    if (value['schema'] != PROFILE_SCHEMA or type(value['build_id']) is not int or value['build_id'] != BUILD_ID
            or type(value['hard_min_us']) is not int or value['hard_min_us'] != HARD_MIN_US
            or type(value['hard_max_us']) is not int or value['hard_max_us'] != HARD_MAX_US
            or value['requested_angle_range_deg'] != [-90, 90]):
        raise ValueError('Axis profile and hardware identity disagree')
    try:
        return AngleCalibration(**value['calibration'])
    except TypeError as exc:
        raise ValueError('Invalid calibration fields') from exc
