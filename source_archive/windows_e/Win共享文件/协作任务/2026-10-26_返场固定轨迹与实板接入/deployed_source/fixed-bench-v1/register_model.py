"""Independent VSRV/2 register/PWM/lease model for host tests only."""
import math
from vsrv_driver import BIND, REFERENCE, ARM, COMMIT, STOP, QUIESCE


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now
    def sleep(self, delay): self.now += delay


class Registers:
    def __init__(self, clock, initial_us=1420):
        self.clock = clock
        self.values = {0: 0x56535256, 4: 2, 8: 0x778d2512, 0x0c: 0, 0x28: 0,
                       0x2c: initial_us, 0x30: 0, 0x34: 0, 0x38: 40, 0x40: initial_us, 0x44: initial_us}
        self.expiry = self.next_frame = self.finish_at = None
        self.ms_origin = None
        self.writes, self.commits, self.pulses = [], [], []
        self.stops = self.quiesces = 0
        self.native_pause_s = self.shadow_pause_s = self.ack_read_pause_s = 0.
        self.quiesce_delay_s = .0008
        self.after_commit_mutation = None
        self.read_pause_used = False
        self.stop_error = self.commit_error = None

    def advance(self):
        now = self.clock()
        if self.values[0x0c] != 15:
            return
        if self.finish_at is None:
            while self.next_frame <= now + 1e-9 and self.next_frame < self.expiry:
                old, target = self.values[0x2c], self.values[0x44]
                self.values[0x2c] = old + max(-4, min(4, target - old))
                self.pulses.append((self.next_frame, self.values[0x2c]))
                self.next_frame += .02
        if self.finish_at is not None and now >= self.finish_at and self.finish_at < self.expiry:
            self.values.update({0x0c: 0, 0x30: 0})
        elif now >= self.expiry:
            self.values.update({0x0c: 64, 0x30: 0})
        else:
            self.values[0x30] = math.ceil((self.expiry - now) * 1000. - 1e-8)

    def read(self, offset):
        self.advance()
        return self.values.get(offset, 0)

    def read_many(self, offsets):
        self.advance()
        result = [self.values.get(offset, 0) for offset in offsets]
        if self.commits and self.values[0x0c] == 15 and not self.read_pause_used and 0x30 in offsets:
            self.read_pause_used = True
            self.clock.now += self.ack_read_pause_s
        return result

    def write(self, offset, value):
        self.advance()
        self.writes.append((self.clock(), offset, value))
        if offset != 0x24:
            self.values[offset] = value
            if offset == 0x1c:
                self.clock.now += self.shadow_pause_s
            return
        if value == STOP:
            self.stops += 1
            if self.stop_error is not None: raise self.stop_error
            self.values.update({0x0c: 0, 0x30: 0})
            self.finish_at = None
        elif value == BIND:
            assert self.values[0x0c] == 0
            self.values.update({0x0c: 8, 0x34: self.values[0x10], 0x38: self.values[0x14], 0x28: 0})
        elif value == REFERENCE:
            assert self.values[0x0c] == 8
            pulse = self.values[0x3c]
            self.values.update({0x0c: 12, 0x40: pulse, 0x2c: pulse, 0x44: pulse})
        elif value == ARM:
            assert self.values[0x0c] == 12
            self.values[0x0c] = 14
        elif value == COMMIT:
            if self.commit_error is not None: raise self.commit_error
            self.clock.now += self.native_pause_s
            self.advance()
            valid = (self.values[0x0c] in (14, 15) and self.values[0x10] == self.values[0x34]
                     and self.values[0x14] == self.values[0x38] and self.values[0x18] == self.values[0x28] + 1
                     and 1400 <= self.values[0x1c] <= 1600 and 3 <= self.values[0x20] <= 500)
            if not valid:
                self.values.update({0x0c: 32, 0x30: 0})
                return
            if self.values[0x0c] == 14:
                self.next_frame = self.clock() + .02
                self.ms_origin = self.clock()
                self.pulses.append((self.clock(), self.values[0x2c]))
            # RTL resets ms_phase only on first COMMIT. Renewals retain the
            # millisecond phase, so L represents more than L-1 and at most L ms.
            elapsed_ms = math.floor((self.clock() - self.ms_origin) * 1000. + 1e-8)
            self.expiry = self.ms_origin + (elapsed_ms + self.values[0x20]) / 1000.
            self.values.update({0x0c: 15, 0x28: self.values[0x18], 0x44: self.values[0x1c], 0x30: self.values[0x20]})
            self.commits.append(dict(time_s=self.clock(), expiry_s=self.expiry, target_us=self.values[0x44], lease_ms=self.values[0x20]))
            if self.after_commit_mutation is not None:
                self.values.update(self.after_commit_mutation)
        elif value == QUIESCE:
            self.quiesces += 1
            self.finish_at = self.clock() + self.quiesce_delay_s
        else:
            raise ValueError('Unknown modeled command')
