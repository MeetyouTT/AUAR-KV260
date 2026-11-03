"""Single-axis visual control and an explicitly simulated command/readback port.

No MMIO, PWM driver, FPGA loader or real ARM is available here. Mapping and
polarity are illustrative simulation values, not measured servo calibration.
All times are supplied from one boot's monotonic clock; angles are commands.
"""
from collections import deque
from dataclasses import dataclass
import math
import threading
import uuid


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def clip(value, low, high):
    return max(low, min(high, value))


@dataclass(frozen=True)
class MotionConfig:
    config_id: str = 'SIM_ONLY_v1'
    tau_s: float = .1
    deadband: float = .04
    kp_deg_s: float = 20.
    max_rate_deg_s: float = 20.
    max_step_deg: float = 2.
    max_dt_s: float = .25
    freshness_s: float = .25
    submit_margin_s: float = .02
    min_lease_s: float = .01
    max_lease_s: float = .5
    min_angle_deg: float = -5.
    max_angle_deg: float = 5.
    polarity: int = 1
    center_us: float = 1500.
    us_per_deg: float = 10.
    min_us: float = 1400.
    max_us: float = 1600.
    frame_s: float = .02
    pulse_step_us: float = 4.

    def __post_init__(self):
        if not self.config_id or not all(finite(v) for k, v in vars(self).items() if k != 'config_id'):
            raise ValueError('Invalid simulation configuration')
        if (self.polarity not in (-1, 1) or self.tau_s <= 0 or not 0 <= self.deadband < 1
                or min(self.kp_deg_s, self.max_rate_deg_s, self.max_step_deg, self.max_dt_s,
                       self.min_lease_s, self.us_per_deg, self.frame_s, self.pulse_step_us) <= 0
                or not self.min_angle_deg <= 0 <= self.max_angle_deg
                or self.min_angle_deg >= self.max_angle_deg or self.min_us >= self.max_us
                or self.submit_margin_s <= 0
                or self.freshness_s <= self.submit_margin_s + self.min_lease_s
                or self.max_lease_s < self.min_lease_s
                or not self.min_us <= self.center_us + self.min_angle_deg*self.us_per_deg
                or not self.center_us + self.max_angle_deg*self.us_per_deg <= self.max_us):
            raise ValueError('Invalid simulation limits or mapping')

    def pulse(self, angle_mdeg):
        return self.center_us + angle_mdeg*self.us_per_deg/1000.


class SimMotionPort:
    """In-memory acceptance, bounded slew and independently polled expiry model.

    Expiry advances when poll/submit is called, not in independent silicon.
    This models the intended semantics, not the experimental MFIT register ABI.
    """
    kind = 'SIMULATED'

    def __init__(self, config):
        self.config = config
        self.session = self.boot = self.epoch = None
        self.state, self.reason = 'DISARMED', 'STARTUP'
        self.referenced = self.active = False
        self.accepted_seq = self.accepted_mdeg = 0
        self.effective_us = self.target_us = config.center_us
        self.deadline = self.frame_time = self.last_now = None
        self.history = deque(maxlen=128)

    def stop(self, reason='STOP', fault=False):
        self.active = self.referenced = False
        self.state, self.reason = ('FAULT' if fault else 'DISARMED'), reason
        self.session = None
        self.deadline = None

    def poll(self, now):
        if not finite(now) or (self.last_now is not None and now < self.last_now):
            self.stop('INVALID_CLOCK', fault=True)
            raise ValueError('Invalid or reversed monotonic time')
        self.last_now = now
        if self.active and now >= self.deadline:
            self.stop('LEASE_EXPIRED', fault=True)
        elif self.active:
            frames = int((now-self.frame_time)/self.config.frame_s)
            if frames > 0:
                step = frames*self.config.pulse_step_us
                self.effective_us += clip(self.target_us-self.effective_us, -step, step)
                self.frame_time += frames*self.config.frame_s
        return self.status()

    def bind(self, boot, epoch, session, now):
        self.poll(now)
        if self.active or self.state in ('ARMED', 'TRACKING', 'AT_LIMIT') or not all(
                isinstance(v, str) and v for v in (boot, epoch, session)):
            raise ValueError('Cannot bind simulation session')
        self.boot, self.epoch, self.session = boot, epoch, session
        self.state, self.reason = 'NEEDS_REFERENCE', 'REFERENCE_REQUIRED'
        self.referenced = False
        self.accepted_seq = self.accepted_mdeg = 0

    def confirm_reference(self):
        if self.state != 'NEEDS_REFERENCE':
            raise ValueError('Simulation reference state required')
        self.referenced = True
        self.effective_us = self.target_us = self.config.center_us
        self.state, self.reason = 'DISARMED', 'SIM_REFERENCE_CONFIRMED'

    def arm_simulation(self):
        if self.state != 'DISARMED' or not self.session or not self.referenced:
            raise ValueError('Explicit simulation reference required')
        self.state, self.reason = 'ARMED', 'SIM_ARMED'

    def submit(self, command, now):
        self.poll(now)
        reason = None
        if self.state not in ('ARMED', 'TRACKING', 'AT_LIMIT') or not self.referenced:
            reason = 'NOT_ARMED'
        elif (command.get('boot_id'), command.get('camera_epoch'), command.get('session'),
              command.get('config_id')) != (self.boot, self.epoch, self.session, self.config.config_id):
            reason = 'CONTEXT_MISMATCH'
        elif not integer(command.get('seq'), 1) or command['seq'] != self.accepted_seq+1:
            reason = 'SEQUENCE_REJECTED'
        elif not isinstance(command.get('target_mdeg'), int) or isinstance(command['target_mdeg'], bool) or not (
                self.config.min_angle_deg*1000 <= command['target_mdeg'] <= self.config.max_angle_deg*1000):
            reason = 'ANGLE_RANGE'
        elif not integer(command.get('lease_us'), 1) or not (
                self.config.min_lease_s*1e6 <= command['lease_us'] <= self.config.max_lease_s*1e6):
            reason = 'LEASE_RANGE'
        if reason:
            return {'outcome': 'REJECTED', 'reason': reason, 'ack_seq': self.accepted_seq,
                    'accepted_mdeg': self.accepted_mdeg, 'scope': self.kind}
        self.accepted_seq, self.accepted_mdeg = command['seq'], command['target_mdeg']
        self.target_us = self.config.pulse(self.accepted_mdeg)
        if not self.active:
            self.frame_time = now
        self.active = True
        self.deadline = now + command['lease_us']/1e6
        limited = self.accepted_mdeg in (self.config.min_angle_deg*1000, self.config.max_angle_deg*1000)
        self.state, self.reason = ('AT_LIMIT' if limited else 'TRACKING'), 'SIM_ACCEPTED'
        self.history.append(dict(command, submitted_time=now, deadline=self.deadline))
        return {'outcome': 'ACCEPTED', 'reason': self.reason, 'ack_seq': self.accepted_seq,
                'accepted_mdeg': self.accepted_mdeg, 'scope': self.kind,
                'session': self.session, 'boot_id': self.boot, 'camera_epoch': self.epoch}

    def status(self):
        return {'scope': self.kind, 'state': self.state, 'reason': self.reason,
                'simulated_output_active': self.active, 'accepted_seq': self.accepted_seq,
                'accepted_command_mdeg': self.accepted_mdeg,
                'simulated_effective_pulse_us': self.effective_us,
                'simulated_target_pulse_us': self.target_us, 'simulated_deadline': self.deadline,
                'physical_actuation_authorized': False, 'motion_command_emitted': False}


class MotionService:
    """Validate real observations, compute commands and accept only matching ACKs."""
    def __init__(self, boot, epoch, config=None, port=None):
        if not all(isinstance(v, str) and v for v in (boot, epoch)):
            raise ValueError('Boot and camera epoch required')
        self.config = config or MotionConfig()
        self.port = port or SimMotionPort(self.config)
        if not isinstance(self.port, SimMotionPort) or self.port.config != self.config:
            raise ValueError('Only the matching simulated port is supported')
        self.boot, self.epoch = boot, epoch
        self.lock = threading.RLock()
        self.session = None
        self.accepted_mdeg = self.accepted_seq = 0
        self.last_frame = -1
        self.last_source_time = self.key = self.filtered = self.control_time = None
        self.reference_time = None
        self.attempts = self.acceptances = self.rejections = 0
        self.last_result = {'reason': 'SIM_NOT_ARMED'}

    def resume_simulation(self, now):
        """Explicit software-only recovery. No real permission is ever granted."""
        with self.lock:
            self.port.stop('SIM_EXPLICIT_RECOVERY')
            self.session = uuid.uuid4().hex
            self.port.bind(self.boot, self.epoch, self.session, now)
            self.port.confirm_reference()
            self.port.arm_simulation()
            self.accepted_mdeg = self.accepted_seq = 0
            self.last_frame = -1
            self.last_source_time = self.key = self.filtered = self.control_time = None
            self.reference_time = now
            self.last_result = {'reason': 'SIM_ARMED'}

    def stop(self, reason='STOP', fault=False):
        with self.lock:
            self.port.stop(reason, fault=fault)
            self.key = self.filtered = self.control_time = None
            self.last_result = {'reason': reason}
            return self.status()

    def poll(self, now):
        with self.lock:
            self.port.poll(now)
            return self.status()

    def status(self):
        with self.lock:
            return dict(self.port.status(), controller_accepted_mdeg=self.accepted_mdeg,
                        controller_accepted_seq=self.accepted_seq,
                        simulated_submit_attempts=self.attempts, simulated_acceptances=self.acceptances,
                        simulated_rejections=self.rejections, control=dict(self.last_result),
                        calibration_status='SIMULATION_PLACEHOLDER', config_id=self.config.config_id)

    def observe(self, snapshot, width, height, now, boot_id):
        with self.lock:
            self.port.poll(now)
            def reject(reason, stop=False, fault=False):
                if stop:
                    self.port.stop(reason, fault=fault)
                    self.key = self.filtered = self.control_time = None
                self.last_result = {'reason': reason, 'submitted_to_simulator': False}
                return self.status()
            if (boot_id != self.boot or not isinstance(snapshot, dict)
                    or snapshot.get('epoch') != self.epoch):
                return reject('CONTEXT_MISMATCH', True)
            fid, observed = snapshot.get('frame_id'), snapshot.get('observed_time')
            if (not integer(fid, 1) or not finite(observed) or not integer(width, 1)
                    or not integer(height, 1)):
                return reject('INVALID_FRAME', True)
            if fid <= self.last_frame or (self.last_source_time is not None and observed <= self.last_source_time):
                return reject('NO_NEW_OBSERVATION')
            self.last_frame, self.last_source_time = fid, observed
            if self.reference_time is not None and observed < self.reference_time:
                return reject('PRE_REFERENCE_OBSERVATION', True)
            if not 0 <= now-observed <= self.config.freshness_s:
                return reject('STALE_OBSERVATION', True)
            tracks = snapshot.get('tracks')
            if not isinstance(tracks, list) or not all(isinstance(t, dict) for t in tracks):
                return reject('INVALID_TRACKS', True)
            targets = [t for t in tracks if t.get('track_id') == snapshot.get('target_id')]
            if len(targets) != 1 or targets[0].get('visible') is not True or targets[0].get('confirmed') is not True:
                self.key = self.filtered = self.control_time = None
                # Before any command, ARMED has no output and may await a face.
                return reject('NO_OBSERVED_TARGET', self.port.active)
            target = targets[0]
            if (target.get('epoch') != self.epoch or target.get('frame_id') != fid
                    or target.get('observed_time') != observed
                    or not integer(target.get('track_id'), 1) or not integer(target.get('generation'), 1)):
                return reject('INVALID_TARGET_EVIDENCE', True)
            box = target.get('box')
            if (not isinstance(box, (list, tuple)) or len(box) != 4 or not all(finite(v) for v in box)
                    or not 0 <= box[0] < width or not 0 <= box[1] < height or min(box[2:]) <= 0
                    or box[0]+box[2] > width or box[1]+box[3] > height):
                return reject('INVALID_BOX', True)
            if self.port.state not in ('ARMED', 'TRACKING', 'AT_LIMIT'):
                return reject('SIM_REQUIRES_EXPLICIT_RESUME')
            key = (self.epoch, target['track_id'], target['generation'])
            error = ((box[0]+box[2]/2)-width/2)/(width/2)
            if self.key != key or self.control_time is None:
                if self.key is not None and self.port.active:
                    return reject('TARGET_CHANGED', True)
                self.key, self.filtered, self.control_time = key, error, observed
                return reject('TARGET_INITIALIZED')
            dt = observed-self.control_time
            if not 0 < dt <= self.config.max_dt_s:
                return reject('CONTROL_TIME_GAP', True)
            alpha = 1-math.exp(-dt/self.config.tau_s)
            self.filtered += alpha*(error-self.filtered)
            self.control_time = observed
            direction = 'CENTER' if abs(self.filtered) <= self.config.deadband else ('RIGHT' if self.filtered > 0 else 'LEFT')
            rate = 0. if direction == 'CENTER' else clip(self.config.kp_deg_s*self.filtered,
                                                       -self.config.max_rate_deg_s, self.config.max_rate_deg_s)
            delta = clip(self.config.polarity*rate*dt, -self.config.max_step_deg, self.config.max_step_deg)
            requested = round(1000*clip(self.accepted_mdeg/1000+delta,
                                        self.config.min_angle_deg, self.config.max_angle_deg))
            remaining = min(self.config.max_lease_s, self.config.freshness_s-(now-observed)-self.config.submit_margin_s)
            lease_us = math.floor(remaining*1e6)
            if lease_us < self.config.min_lease_s*1e6:
                return reject('INSUFFICIENT_FRESHNESS_BUDGET', True)
            command = {'boot_id': self.boot, 'camera_epoch': self.epoch, 'session': self.session,
                       'config_id': self.config.config_id, 'seq': self.accepted_seq+1,
                       'target_mdeg': requested, 'lease_us': lease_us,
                       'source_frame_id': fid, 'source_observed_time': observed,
                       'track_id': target['track_id'], 'track_generation': target['generation']}
            self.attempts += 1
            receipt = self.port.submit(command, now)
            matched = (receipt.get('scope') == 'SIMULATED' and receipt.get('ack_seq') == command['seq']
                       and receipt.get('accepted_mdeg') == requested
                       and receipt.get('session') == self.session and receipt.get('boot_id') == self.boot
                       and receipt.get('camera_epoch') == self.epoch)
            if receipt.get('outcome') == 'ACCEPTED' and matched:
                self.accepted_seq, self.accepted_mdeg = command['seq'], requested
                self.acceptances += 1
            elif (receipt.get('outcome') == 'REJECTED' and receipt.get('scope') == 'SIMULATED'
                  and receipt.get('ack_seq') == self.accepted_seq
                  and receipt.get('accepted_mdeg') == self.accepted_mdeg):
                self.rejections += 1
            else:
                self.port.stop('UNKNOWN_ACCEPTANCE', fault=True)
            result_reason = receipt.get('reason', 'UNKNOWN_ACCEPTANCE')
            if self.port.state == 'FAULT' and self.port.reason == 'UNKNOWN_ACCEPTANCE':
                result_reason = 'UNKNOWN_ACCEPTANCE'
            self.last_result = {'reason': result_reason,
                                'submitted_to_simulator': True, 'direction': direction,
                                'raw_error': error, 'filtered_error': self.filtered, 'dt_s': dt,
                                'requested_mdeg': requested, 'receipt': receipt, 'source': command}
            return self.status()
