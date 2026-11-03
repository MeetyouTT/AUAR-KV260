"""Actual worker main/tick under fake GLib/engine; no Gst/device/PCM files."""
import ast
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import queue
import sys
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def worker():
    package = ModuleType('tools'); package.__path__ = []
    dependency = ModuleType('tools.gstreamer_audio_engine')
    dependency.GstAudioEngine = object; dependency.REQUIRED_ELEMENTS = ()
    spec = importlib.util.spec_from_file_location('idle_worker_candidate', ROOT/'after/tools/gstreamer_audio_worker.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'tools': package, 'tools.gstreamer_audio_engine': dependency}):
        spec.loader.exec_module(module)
    return module


class Engine:
    def __init__(self, harness):
        self.h = harness; self.active = False; self.paused = False
        self.error = ''; self.poll_calls = self.released = self.reference_calls = 0
        self.commands = []
        self.value = dict(token=0, ready=False, done=False, error='', persistent=True,
            device_ready=True, device_state='IDLE_READY', audible=False, track=None,
            duration=0., device='public-fake', output_caps='fake-caps', clock_source='fake-sink')

    def poll(self):
        self.poll_calls += 1
        return self.snapshot()

    def snapshot(self):
        # Deliberately changing idle clocks/timers/metrics must not defeat gating.
        return dict(self.value, clock=self.h.now, answer_clock=self.h.now,
            started_at=self.h.now, answer_started_at=self.h.now,
            max_poll_gap_ms=self.poll_calls, diagnostic_counter=self.poll_calls)

    def command(self, value):
        self.commands.append(dict(value))
        if value['type'] == 'bad': raise ValueError('synthetic command rejected')
        self.value['token'] = value.get('token', self.value['token'])
        if value['type'] in ('stop', 'close'):
            self.active = self.paused = False
            self.value.update(device_state='IDLE_READY', ready=False, done=False, error='', duration=0.)
            if value['type'] == 'close': self.release()
        elif value['type'] == 'stream':
            self.active = True; self.value.update(device_state='WAITING_PCM', ready=False, done=False)
        return True

    def fail(self, error):
        self.error = error; self.active = False
        self.value.update(error=error, device_state='ERROR')

    def release(self): self.released += 1

    def take_references(self):
        self.reference_calls += 1
        return [dict(sequence=self.reference_calls, pcm=b'\x01\0'*480,
                     at=self.h.now, queued_end_ns=self.reference_calls*20000000)]


class Harness:
    def __init__(self, count=110, *, states=None, commands=None, echo=False, persistent=True,
                 block_state_once=False, eof_at=None, remove_active=False):
        self.module = worker(); self.now = 0.; self.count = count
        self.states = states or {}; self.schedule = commands or {}; self.echo = echo
        self.persistent = persistent; self.block_state_once = block_state_once
        self.eof_at = eof_at; self.bytes = bytearray(); self.write_calls = 0
        self.queue = queue.Queue(maxsize=32); self.eof = threading.Event()
        self.engine = Engine(self); self.steps = 0; self.interval = None; self.quitting = False
        if remove_active: del self.engine.active

    def write(self, fd, value):
        self.write_calls += 1
        if self.block_state_once and b'"kind": "state"' in value:
            self.block_state_once = False
            raise BlockingIOError()
        self.bytes.extend(value)
        return len(value)

    def run(self):
        h = self
        class Loop:
            def quit(self): h.quitting = True
            def run(self):
                for step in range(h.count):
                    h.now = step / 100
                    change = dict(h.states.get(step, {}))
                    for key in ('active', 'paused'):
                        if key in change: setattr(h.engine, key, change.pop(key))
                    h.engine.value.update(change)
                    for command in h.schedule.get(step, []): h.queue.put_nowait(command)
                    if step == h.eof_at: h.eof.set()
                    h.steps += 1
                    if h.callback() is False or h.quitting: break
        def timeout_add(interval, callback): h.interval = interval; h.callback = callback
        class Thread:
            def __init__(self, **kwargs): pass
            def start(self): pass  # Do not read a real stdin or create a thread.
        original_publisher = self.module.NonBlockingAudioPublisher
        def publisher():
            h.publisher = original_publisher(configure_fd=False, write=h.write, clock=lambda: h.now)
            return h.publisher
        persistent_module = ModuleType('tools.gstreamer_persistent_engine')
        persistent_module.PersistentGstAudioEngine = lambda *a, **kw: h.engine
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {'tools.gstreamer_persistent_engine': persistent_module}))
            stack.enter_context(patch.object(self.module, 'load_gst', return_value=(object(), SimpleNamespace(MainLoop=Loop, timeout_add=timeout_add))))
            stack.enter_context(patch.object(self.module, 'GstAudioEngine', side_effect=lambda *a, **kw:h.engine))
            stack.enter_context(patch.object(self.module, 'NonBlockingAudioPublisher', side_effect=publisher))
            stack.enter_context(patch.object(self.module, 'queue', SimpleNamespace(Queue=lambda **kw:h.queue, Empty=queue.Empty, Full=queue.Full)))
            stack.enter_context(patch.object(self.module, 'threading', SimpleNamespace(Event=lambda:h.eof, Thread=Thread)))
            stack.enter_context(patch.object(self.module, 'time', SimpleNamespace(monotonic=lambda:h.now, sleep=lambda _:None)))
            args = (['--persistent'] if self.persistent else []) + (['--echo-reference'] if self.echo else [])
            self.exit_code = self.module.main(args)
        self.messages = [json.loads(line[6:]) for line in self.bytes.decode().splitlines()]
        self.states_out = [v for v in self.messages if v['kind'] == 'state']
        return self


class IdleWorkerTests(unittest.TestCase):
    def test_idle_initial_and_one_second_heartbeat_despite_dynamic_clocks(self):
        h = Harness().run()
        self.assertEqual(h.interval, 10)
        self.assertEqual(h.engine.poll_calls, 111)  # one warmup check +110 original ticks
        self.assertEqual(len(h.states_out), 2)
        self.assertEqual([s['clock'] for s in h.states_out], [0., 1.])
        self.assertEqual(h.publisher.messages, 3)  # boot +two states; IPC count is not gate input
        self.assertEqual(h.exit_code, 0)

    def test_token_and_logical_idle_changes_publish_without_heartbeat_wait(self):
        h = Harness(6, states={1:{'token':1}, 2:{'done':True,'ready':True}, 3:{'duration':.4}}).run()
        self.assertEqual([s['clock'] for s in h.states_out], [0., .01, .02, .03])
        self.assertEqual(h.states_out[2]['done'], True)

    def test_active_waiting_pcm_and_paused_retain_every_original_tick(self):
        h = Harness(8, states={0:{'active':True,'device_state':'WAITING_PCM'},
            3:{'device_state':'PLAYING','audible':True},
            5:{'paused':True,'device_state':'PAUSED','audible':False}}).run()
        self.assertEqual(len(h.states_out), 8)
        self.assertEqual(h.engine.poll_calls, 9)

    def test_eos_first_idle_done_state_is_immediate_then_gated(self):
        h = Harness(7, states={0:{'active':True,'device_state':'PLAYING','audible':True},
            2:{'active':False,'device_state':'IDLE_READY','audible':False,'ready':True,'done':True}}).run()
        self.assertEqual([s['clock'] for s in h.states_out], [0., .01, .02])
        self.assertTrue(h.states_out[-1]['done'])

    def test_even_repeated_unchanged_stop_command_publishes_same_tick(self):
        h = Harness(6, commands={2:[{'type':'stop','token':0}],4:[{'type':'stop','token':0}]}).run()
        self.assertEqual([s['clock'] for s in h.states_out], [0., .02, .04])
        self.assertEqual(len(h.engine.commands), 2)

    def test_poll_error_state_is_immediate_and_not_idle_throttled(self):
        h = Harness(6, states={2:{'error':'synthetic failure','device_state':'ERROR'}}).run()
        self.assertEqual([s['clock'] for s in h.states_out], [0., .02, .03, .04, .05])
        self.assertEqual(h.states_out[1]['error'], 'synthetic failure')

    def test_exception_notification_and_identical_idle_recovery_are_immediate(self):
        h = Harness(5, commands={2:[{'type':'bad','token':0}]},
                    states={3:{'error':'','device_state':'IDLE_READY'}}).run()
        self.assertEqual([s['clock'] for s in h.states_out], [0., .02, .03])
        self.assertIn('ValueError', h.states_out[1]['error'])

    def test_not_ready_and_nonpersistent_missing_active_keep_original_frequency(self):
        h = Harness(5, states={0:{'device_ready':False}}).run()
        self.assertEqual(len(h.states_out), 5)
        h = Harness(5, persistent=False, remove_active=True).run()
        self.assertEqual(len(h.states_out), 5)

    def test_pending_stdout_is_flushed_on_skipped_idle_tick(self):
        h = Harness(3, block_state_once=True).run()
        self.assertEqual(len(h.states_out), 1)
        self.assertEqual(h.states_out[0]['clock'], 0.)
        self.assertEqual(h.publisher.snapshot()['pending_bytes'], 0)
        self.assertEqual(h.publisher.blocked_writes, 1)

    def test_echo_reference_drain_and_pcm_publication_keep_every_tick(self):
        h = Harness(6, echo=True).run()
        self.assertEqual(h.engine.reference_calls, 6)
        references = [m for m in h.messages if m['kind'] == 'reference']
        self.assertEqual([m['sequence'] for m in references], list(range(1,7)))
        self.assertEqual(len(h.states_out), 1)

    def test_close_and_eof_release_on_their_tick_without_waiting_for_heartbeat(self):
        for options in ({'commands':{2:[{'type':'close','token':1}]}}, {'eof_at':2}):
            with self.subTest(options=options):
                h = Harness(10, **options).run()
                self.assertEqual(h.steps, 3)
                self.assertGreaterEqual(h.engine.released, 1)
                self.assertTrue(h.quitting)

    def test_publisher_and_loader_are_identical_and_python39_parses(self):
        before = ast.parse((ROOT/'before/tools/gstreamer_audio_worker.py').read_bytes())
        after = ast.parse((ROOT/'after/tools/gstreamer_audio_worker.py').read_bytes(), feature_version=(3,9))
        for name in ('NonBlockingAudioPublisher', 'load_gst', 'emit'):
            left = next(n for n in before.body if getattr(n, 'name', '') == name)
            right = next(n for n in after.body if getattr(n, 'name', '') == name)
            self.assertEqual(ast.dump(left, include_attributes=False), ast.dump(right, include_attributes=False))


if __name__ == '__main__': unittest.main()
