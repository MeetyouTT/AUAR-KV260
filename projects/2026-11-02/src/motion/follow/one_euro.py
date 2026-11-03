"""One Euro scalar math using actual source time; no IO or command authority.

For AURA, values are image-width ratios and timestamps are source seconds.
This replaces the position median/EMA rather than being appended to them.
Formula reference: casiez/OneEuroFilter cpp at commit
d78925584245597f2aa9c4c01a802eb0f0b77fb9 (lastFilteredValue derivative).
"""
import math


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class OneEuroFilter:
    def __init__(self, min_cutoff_hz=1.0, beta=6.0, derivative_cutoff_hz=1.0):
        if (not all(_finite(x) for x in (min_cutoff_hz, beta, derivative_cutoff_hz))
                or min_cutoff_hz <= 0 or beta < 0 or derivative_cutoff_hz <= 0):
            raise ValueError('Finite positive cutoffs and nonnegative beta required')
        self.min_cutoff_hz = float(min_cutoff_hz)
        self.beta = float(beta)
        self.derivative_cutoff_hz = float(derivative_cutoff_hz)
        self.reset()

    def reset(self):
        self.timestamp_s = self.value = None
        self.derivative_ratio_s = 0.0
        self.cutoff_hz = self.min_cutoff_hz

    @staticmethod
    def alpha(cutoff_hz, dt_s):
        return 1.0 / (1.0 + 1.0/(2.0*math.pi*cutoff_hz*dt_s))

    def filter(self, value_ratio, timestamp_s):
        if (not _finite(value_ratio) or not _finite(timestamp_s)
                or (self.timestamp_s is not None and timestamp_s <= self.timestamp_s)):
            raise ValueError('Finite value and strictly increasing actual source time required')
        if self.timestamp_s is None:
            self.timestamp_s, self.value = float(timestamp_s), float(value_ratio)
            return self.value
        dt_s = timestamp_s-self.timestamp_s
        derivative = (value_ratio-self.value)/dt_s
        derivative_alpha = self.alpha(self.derivative_cutoff_hz, dt_s)
        smoothed_derivative = (derivative_alpha*derivative
                               + (1.0-derivative_alpha)*self.derivative_ratio_s)
        cutoff = self.min_cutoff_hz+self.beta*abs(smoothed_derivative)
        position_alpha = self.alpha(cutoff, dt_s)
        result = position_alpha*value_ratio+(1.0-position_alpha)*self.value
        if not all(math.isfinite(x) for x in (result, smoothed_derivative, cutoff)):
            raise ValueError('Unrepresentable sample interval or value')
        self.timestamp_s, self.value = float(timestamp_s), result
        self.derivative_ratio_s, self.cutoff_hz = smoothed_derivative, cutoff
        return result

    __call__ = filter
