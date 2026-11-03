"""Pure Python scene for the archived hardware-slew tests.

The packet/profile behavior follows the archived 2026-10-27 helper. Its native
Ruckig construction is replaced by an object that fails if called: the tested
hardware-slew mode must never use a PS trajectory. No hardware/module is mocked
into a production import, and no test assertions are changed.
"""
import copy
from types import SimpleNamespace
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession
from common.motion_observation import PROTOCOL


class UnusedTrajectory:
    def step(self, *args, **kwargs):
        raise AssertionError('Hardware-slew mode unexpectedly used PS trajectory')


def profile():
    return EdgeConfig(left_ratio=.1, maximum_correction_us=None, confirm_frames=2,
        maximum_speed_us_s=30., maximum_acceleration_us_s2=120., gain_us_s=200.,
        minimum_edge_speed_us_s=6., velocity_gain_us=24., prearm_confirmed_face=True,
        recenter_on_edge=True, target_center_ratio=.5, center_tolerance_ratio=.03)


class Scene:
    def __init__(self, reference=1469):
        from test_hardware_slew import FrameSlewDevice
        self.now = 10.
        self.fid = 0
        self.last = None
        self.device = FrameSlewDevice(lambda: self.now, reference)
        self.session = ContinuousSession(self.device, 'fixture-boot', profile(),
            lambda pulse: SimpleNamespace(reference_us=pulse), trajectory=UnusedTrajectory(),
            clock=lambda: self.now, allow_fixture=True)

    def packet(self, center=.5, **extra):
        self.fid += 1
        stamp = round(self.now * 1000) - 60
        value = dict(protocol_version=PROTOCOL, source_kind='fixture', target_kind='face',
            board_boot_id='fixture-boot', service_epoch='service', camera_epoch='camera',
            state='READY', source_frame_id=self.fid, source_mono_ms=stamp,
            deadline_mono_ms=stamp + 250, face_detection_mono_ms=stamp,
            frame_width=640, frame_height=480, mirror_horizontal=True,
            target=dict(track_id=1, track_generation=1,
                        box=[center * 640 - 40, 100., 80., 80.], score=.95))
        value.update(extra)
        if value['state'] != 'READY':
            value.update(target=None, source_frame_id=None, source_mono_ms=None,
                         deadline_mono_ms=None)
        self.last = copy.deepcopy(value)
        return value

    def tick(self, count=4):
        for _ in range(count):
            self.now += .02
            self.session.tick()

    def feed(self, centers, **extra):
        for center in centers:
            self.session.step(self.packet(center, **extra))
            self.tick()
