"""Independent public-only M03 counterexamples; no models/devices/network.

These safety assertions are expected to fail against candidate_m03/26015f4.
Only a TemporaryDirectory SQLite Store and explicit in-memory PCM are used.
"""
import importlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
COLLAB = HERE.parent
PROJECT = COLLAB.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))
sys.path.insert(0, str(COLLAB / 'board_integration_v17/local_runtime_v17'))
for name, paths in (
    ('common', ['candidate_h01/after/common']),
    ('board.runtime', ['candidate_m03/after/board/runtime', 'candidate_h01/after/board/runtime']),
):
    module = importlib.import_module(name)
    module.__path__ = [str(COLLAB / value) for value in paths] + list(module.__path__)

from board.runtime.board_dialogue import BoardDialogueController
from board.runtime.history_delete import LocalHistoryDelete
from common.board_memory import BoardMemoryStore
from common.model_inference_wire import Owner, audio_payload, make_response


class Mono:
    def __init__(self):
        self.now = 10.

    def __call__(self):
        return self.now


class Timeline:
    def __init__(self, mono):
        self.monotonic = mono
        self.utc = datetime(2026, 10, 31, 12, tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()

    def event_time(self):
        return self.utc


class RamTts:
    def request(self, kind, payload, **kwargs):
        assert kind == 'tts' and not kwargs['cancelled']()
        return make_response(Owner.from_dict(payload), result={'audio': audio_payload(b'\x01\x00' * 24, 24000)})

    def cancel(self, owner):
        pass


class DeleteBoundaryReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aura-public-m03-review-')
        self.addCleanup(self.temp.cleanup)
        self.mono = Mono()
        self.timeline = Timeline(self.mono)
        self.now = self.timeline.utc
        self.store = BoardMemoryStore(Path(self.temp.name) / 'public.sqlite3', clock=self.timeline.event_time)
        self.scope = {'kind': 'conversation', 'id': 'public-m03-boundary'}
        self.controller = BoardDialogueController(self.store, RamTts(), board_boot_id='public-review-boot',
            system_prompt='Public synthetic review only.', clock=self.mono)
        self.handler = LocalHistoryDelete(self.store, self.timeline, clock=self.mono)
        self.generation = 0

    def append(self, event_id, utc):
        self.timeline.utc = utc
        self.store.append_event(self.scope, event_id, 'user_said', '公开日期边界测试内容。')
        self.timeline.utc = self.now

    def say(self, text):
        self.generation += 1
        job = SimpleNamespace(scope=self.scope, deadline=self.mono() + 30., meta={
            'board_boot_id': 'public-review-boot', 'session_id': 'public-review-session',
            'generation': self.generation, 'request_id': 'public-command-' + str(self.generation)})
        import threading
        plan = self.handler(text, job=job, controller=self.controller, is_current=lambda: True,
            cancel_event=threading.Event())
        self.controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256, samples=plan.samples)
        return plan.reply.text

    def state(self, event_id):
        with self.store._db() as db:
            return db.execute('SELECT state FROM bm_events WHERE event_id=?', (event_id,)).fetchone()[0]

    def test_yesterday_must_not_delete_today_exact_midnight(self):
        midnight = datetime(2026, 10, 31, tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()
        self.append('public-yesterday', midnight - 60.)
        self.append('public-today-midnight', midnight)
        self.say('删除昨天的对话记录')
        self.say('确认删除记录')
        self.assertEqual(self.state('public-yesterday'), 'forgotten')
        self.assertEqual(self.state('public-today-midnight'), 'valid',
            'Single-day deletion included the following day midnight.')

    def test_new_today_source_after_advancing_time_must_invalidate_preview(self):
        self.append('public-existing-today', self.now - 60.)
        self.say('删除今天的对话记录')
        self.mono.now += 1.
        self.now += 1.
        self.append('public-new-today', self.now)
        self.say('确认删除记录')
        self.assertEqual(self.state('public-existing-today'), 'valid',
            'Today end was frozen at preview now, so the new same-day source escaped change detection.')
        self.assertEqual(self.state('public-new-today'), 'valid')

    def test_associated_fact_value_must_not_remain_recallable_after_date_delete(self):
        self.append('public-fact-root', self.now - 60.)
        self.store.correct(self.scope, '项目', '公开关联值海风', source_event_ids=('public-fact-root',))
        self.say('删除今天的对话记录')
        self.say('确认删除记录')
        self.assertEqual(self.state('public-fact-root'), 'forgotten')
        self.assertEqual(self.store.context(self.scope)['facts'], [])
        recall = self.store.history(self.scope, search='公开关联值海风')
        self.assertFalse(any('公开关联值海风' in row['text'] for row in recall),
            'A valid memory_command body still exposes the forgotten associated fact through history.')

    def test_preview_expiring_during_write_acquisition_must_not_delete(self):
        self.append('public-ttl-target', self.now - 60.)
        self.say('删除今天的对话记录')
        self.mono.now += 59.9
        original = self.store._db
        advanced = False

        @contextmanager
        def delayed_write(write=False):
            nonlocal advanced
            with original(write) as db:
                if write and not advanced:
                    status = db.execute("SELECT count(*) FROM bm_turns WHERE turn_id='public-command-2'").fetchone()[0]
                    if status:
                        # Model only the elapsed monotonic time after BEGIN
                        # acquired; no real wait, lock contention or I/O load.
                        self.mono.now += .2
                        advanced = True
                yield db

        self.store._db = delayed_write
        self.say('确认删除记录')
        self.assertTrue(advanced)
        self.assertEqual(self.state('public-ttl-target'), 'valid',
            'A preview older than 60 seconds was deleted after write acquisition.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
