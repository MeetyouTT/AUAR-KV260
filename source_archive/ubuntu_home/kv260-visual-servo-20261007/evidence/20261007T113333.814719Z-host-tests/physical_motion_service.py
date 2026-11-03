"""Inference-thread bridge for an explicitly referenced VSRV driver.

No device opening, bitstream loading, default reference or implicit ARM.
Stopping PWM terminates new commands; it does not measure the shaft or
guarantee instantaneous mechanical braking.
"""
import threading
from face_servo_control import FaceServoController


class PhysicalMotionService:
    def __init__(self, driver, camera_epoch):
        self.lock = threading.RLock()
        self.controller = FaceServoController(driver, camera_epoch)
        self.driver = driver
        self.last_event = {'outcome': 'WAITING', 'reason': 'AWAITING_CONFIRMED_FACE'}
        self.last_readback = driver.status()
        if (self.last_readback['flags'] & 15 != 14
                or self.last_readback['reference_us'] != self.controller.origin):
            driver.stop()
            raise RuntimeError('An inactive, explicitly referenced and armed driver is required')

    def observe(self, snapshot, width, height, now, boot_id):
        with self.lock:
            before = self.driver.ack_seq
            self.last_event = self.controller.observe(snapshot, width, height, now, boot_id)
            self.last_readback = self.driver.status()
            # Driver only increments after an exact matching acknowledgement.
            if self.driver.ack_seq < before:
                raise RuntimeError('Acknowledgement sequence moved backwards')
            return self.status()

    def poll(self, now):
        with self.lock:
            self.last_readback = self.driver.status()
            if not self.controller.stopped and self.last_readback['flags'] & 14 != 14:
                self.last_event = self.controller.stop('HARDWARE_PERMISSION_ENDED')
                self.last_readback = self.driver.status()
            return self.status()

    def stop(self, reason):
        with self.lock:
            self.last_event = self.controller.stop(reason)
            self.last_readback = self.driver.status()
            return self.status()

    def status(self):
        with self.lock:
            active = self.last_readback['active'] and not self.controller.stopped
            at_limit = self.controller.accepted_us in (self.controller.low, self.controller.high)
            return {
                'scope': 'PHYSICAL_VSRV_BENCH',
                'state': 'DISARMED' if self.controller.stopped else ('AT_LIMIT' if active and at_limit else 'TRACKING' if active else 'ARMED'),
                'reason': self.last_event.get('reason', self.last_event['outcome']),
                'control': dict(self.last_event),
                'actuation_authorized': not self.controller.stopped and self.last_readback['armed'],
                'motion_command_emitted': self.driver.commit_attempts > 0,
                'physical_submit_attempts': self.driver.commit_attempts,
                'controller_accepted_seq': self.driver.ack_seq,
                'controller_accepted_us': self.controller.accepted_us,
                'relative_pulse_us': self.controller.accepted_us - self.controller.origin,
                'readback': dict(self.last_readback),
                'mechanical_angle_measured': False,
            }
