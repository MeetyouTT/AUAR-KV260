"""Convert X-server input times conservatively; never freshen queued intent."""
import math
import time


class InputFreshness:
    MAX_AGE_S = .25
    HEARTBEAT_LIMIT_S = .2
    ROUND_TRIP_LIMIT_S = .1

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.last_heartbeat = clock()
        self.blocked_until = self.last_heartbeat + self.MAX_AGE_S

    def heartbeat(self):
        now = self.clock()
        if not 0 <= now-self.last_heartbeat <= self.HEARTBEAT_LIMIT_S:
            self.blocked_until = now + self.MAX_AGE_S
        self.last_heartbeat = now

    def source_time(self, event_ms, server_ms, before, after):
        if (type(event_ms) is not int or type(server_ms) is not int
                or not 0 < event_ms <= 0xffffffff or not 0 < server_ms <= 0xffffffff):
            raise ValueError('缺少原始点击时间，请重新点击')
        if (type(before) not in (int, float) or type(after) not in (int, float)
                or not math.isfinite(before) or not math.isfinite(after)
                or not 0 <= after-before <= self.ROUND_TRIP_LIMIT_S):
            raise ValueError('界面响应过慢，请稍后重新点击')
        age = ((server_ms-event_ms) & 0xffffffff) / 1000
        # before, rather than after, deliberately includes round-trip latency.
        source = before-age
        now = self.clock()
        if (now < self.blocked_until or not 0 <= now-self.last_heartbeat <= self.HEARTBEAT_LIMIT_S
                or not 0 <= now-source <= self.MAX_AGE_S):
            raise ValueError('点击已经过期或界面刚恢复，请重新点击')
        return source
