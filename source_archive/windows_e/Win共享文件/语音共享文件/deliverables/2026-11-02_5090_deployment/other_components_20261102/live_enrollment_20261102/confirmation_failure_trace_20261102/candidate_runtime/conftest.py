"""Test-only full ACK and explicit next logical frame for old synchronous fixtures.

No production source or test assertions are changed. The older in-memory
fixtures omitted six ACK ownership fields and never advanced source timestamps.
"""
import copy

import pytest

from tests.framework import test_simple_enrollment as simple
from tests.framework import test_sampling_voice as sampling


def install_producer(flow):
    original = flow.snapshot
    initial = original()
    tick = [initial['observed_mono_ms']]
    sequence = [initial['sequence']]
    def produce():
        tick[0] += 1
        sequence[0] += 1
        value = original()
        value['sequence'] = max(sequence[0], value['sequence'])
        value['observed_mono_ms'] = tick[0]
        return value
    flow.snapshot = produce
    flow.now_ms = lambda: tick[0]


def full_start_ack(original):
    def command(self, value):
        result = original(self, value)
        if value['action'] == 'identity_sample_start':
            fields = ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')
            ack = {key: value[key] for key in fields}
            ack.update(accepted=result['accepted'], detail=result.get('detail','synthetic start accepted'))
            return ack
        return result
    return command


@pytest.fixture(autouse=True)
def full_original_start_contract(monkeypatch):
    monkeypatch.setattr(simple.SimpleFlowTests, 'command', full_start_ack(simple.SimpleFlowTests.command))
    original = simple.SimpleFlowTests.setUp
    def setup(self):
        original(self)
        install_producer(self.flow)
    monkeypatch.setattr(simple.SimpleFlowTests, 'setUp', setup)

    monkeypatch.setattr(sampling.FlowFixture, 'command', full_start_ack(sampling.FlowFixture.command))
    original_init = sampling.FlowFixture.__init__
    def initialize(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        install_producer(self.flow)
    monkeypatch.setattr(sampling.FlowFixture, '__init__', initialize)

    original_board = simple.BoardSimpleFlowTests.setUp
    def board_setup(self):
        original_board(self)
        original_snapshot = self.flow.snapshot
        def produce():
            # Advance the synthetic camera's actual monotonic source clock.
            self.case.c.now += 1
            return original_snapshot()
        self.flow.snapshot = produce
    monkeypatch.setattr(simple.BoardSimpleFlowTests, 'setUp', board_setup)
