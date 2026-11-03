"""A persistent fake inference host must accept a restarted board summarizer.

Calls InferenceHost.handle directly with an in-memory fake backend: no sockets,
models, stores, audio, or process/service lifecycle actions.
"""
import json
import time

from common.model_inference_wire import Owner
from board.runtime.board_memory_policy import BoardSummaryClient
from tools.model_inference_host import InferenceHost


class Backend:
    def llm(self, payload, **kwargs):
        return dict(text='{"summary":"公开合成摘要。","keywords":["合成"]}')


class Client:
    def __init__(self, host):
        self.host = host
        self.replies = []
        self.owners = []

    def request(self, kind, payload, **kwargs):
        self.owners.append(Owner.from_dict(payload))
        _, reply = self.host.handle(kind, payload)
        self.replies.append(reply)
        return reply

    def cancel(self, owner):
        pass


def infer(summary):
    summary.metrics = dict(model_calls=0)
    return summary._infer([dict(source='user_said', text='公开资料。')], lambda: False,
        deadline=time.monotonic()+2)


def test_same_boot_restart_never_rewinds_persistent_host_generation():
    host = InferenceHost(Backend())
    try:
        client = Client(host)
        # A controlled restart completes after the previous worker has stopped;
        # advance its same-boot clock explicitly (no sleeps or clock reset).
        base_time = time.monotonic()
        now = [base_time]
        old = BoardSummaryClient(client, board_boot_id='synthetic-unchanged-boot', clock=lambda: now[0])
        assert infer(old)['summary'] == '公开合成摘要。'
        assert infer(old)['summary'] == '公开合成摘要。'
        # A board GUI/runtime restart recreates this object while the Windows
        # model-only host and the physical board boot remain unchanged.
        now[0] += .001
        new = BoardSummaryClient(client, board_boot_id='synthetic-unchanged-boot', clock=lambda: now[0])
        assert infer(new)['summary'] == '公开合成摘要。'
        assert client.owners[-1].generation > client.owners[-2].generation
        assert host.health()['owner_metadata'] == 1
        assert client.owners[-1].session_id == client.owners[-2].session_id == 'memory-worker'
    finally:
        host.close()
