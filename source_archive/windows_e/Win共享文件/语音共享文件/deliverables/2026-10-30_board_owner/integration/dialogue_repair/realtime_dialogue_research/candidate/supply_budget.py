"""Pure metadata replay for *post-guard* ordered PCM packet availability.

No PCM accepted or generated; no runtime buffering or playback code.
Output is an idealized supply schedule, not acoustic or device evidence.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Packet:
    arrival_ms: float
    samples: int


def _number(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def validate_packets(records):
    if not isinstance(records, (list, tuple)) or not 1 <= len(records) <= 1500:
        raise ValueError('invalid_packet_count')
    packets, last, total = [], -1., 0
    for record in records:
        if not isinstance(record, dict) or set(record) != {'arrival_ms', 'samples'}:
            raise ValueError('invalid_packet_fields')
        arrival, samples = record['arrival_ms'], record['samples']
        if (not _number(arrival, 300000) or arrival < last
                or type(samples) is not int or not 1 <= samples <= 480):
            raise ValueError('invalid_packet_value')
        total += samples
        if total > 720000:
            raise ValueError('invalid_total_samples')
        packets.append(Packet(float(arrival), samples))
        last = arrival
    return packets


@dataclass(frozen=True)
class SupplyEstimate:
    packet_count: int
    samples: int
    start_reserve_ms: float
    first_play_ms: float
    last_play_end_ms: float
    total_supply_gap_ms: float
    longest_supply_gap_ms: float
    supply_gap_count: int
    required_extra_start_ms: float
    peak_pending_audio_ms: float
    pending_within_limit: bool
    evidence_kind: str = 'IDEALIZED_METADATA_REPLAY_NOT_DEVICE_OR_ACOUSTIC'

    def as_dict(self):
        return asdict(self)


def estimate_supply(records, *, start_reserve_ms=0, pending_limit_ms=240):
    """Compare at most 240ms EXTRA initial reserve; never conceal slow supply.

    required_extra_start_ms = max_i(a_i - sum(previous audio durations)) - a_0
    is the minimum extra initial delay for gap-free ideal playout with unlimited
    staging. An actual bounded player can require more care. pending_limit_ms
    is a PROPOSED comparison limit, not the current appsrc/capture queue limit.

    Packet arrivals are AFTER existing fresh authorization checks. If replaying
    TTS completion times instead, the results would wrongly omit guard, queue,
    IPC and scheduling delay. Capture and device buffers are not modeled.
    """
    if not _number(start_reserve_ms, 240) or not _number(pending_limit_ms, 30000):
        raise ValueError('invalid_budget')
    packets = validate_packets(records)
    durations = [packet.samples / 24 for packet in packets]
    first = packets[0].arrival_ms + start_reserve_ms
    now, elapsed, required = first, 0., packets[0].arrival_ms
    gaps, starts, ends, prefix = [], [], [], [0.]
    for packet, duration in zip(packets, durations):
        required = max(required, packet.arrival_ms - elapsed)
        if packet.arrival_ms > now + 1e-9:
            gaps.append(packet.arrival_ms - now)
            now = packet.arrival_ms
        starts.append(now)
        now += duration
        ends.append(now)
        elapsed += duration
        prefix.append(elapsed)
    peak, arrived = 0., 0.
    for packet, duration in zip(packets, durations):
        arrived += duration
        completed = bisect_right(ends, packet.arrival_ms)
        played = prefix[completed]
        if completed < len(packets):
            played += max(0., min(durations[completed], packet.arrival_ms - starts[completed]))
        peak = max(peak, arrived - played)
    return SupplyEstimate(len(packets), sum(p.samples for p in packets),
        float(start_reserve_ms), first, now, sum(gaps), max(gaps, default=0.), len(gaps),
        max(0., required - packets[0].arrival_ms), peak, peak <= pending_limit_ms + 1e-9)
