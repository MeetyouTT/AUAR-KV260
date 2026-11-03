"""Public synthetic sources, original Store, fake inference only."""
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
REPAIR = HERE.parent
BASE = REPAIR / 'animation_thinking_collaboration/runtime_v16'
sys.path.insert(0, str(BASE))
from common.board_memory import BoardMemoryStore, BoardMemoryWorker, CandidateRejected, validate_compaction_text
from common.model_inference_wire import Owner, make_response
from board.visual_timeline import VisualTimelineCollector


def policy(side):
    name = 'board.runtime.observation_' + side
    spec = importlib.util.spec_from_file_location(name, HERE / side / 'board/runtime/board_memory_policy.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BEFORE, AFTER = policy('before'), policy('after')
SCOPE = dict(kind='device', id='public-device')


class FakeClient:
    def __init__(self, text, hook=None):
        self.text, self.hook, self.calls = text, hook, []
    def request(self, kind, payload, **kwargs):
        self.calls.append(payload)
        if self.hook:
            self.hook()
        return make_response(Owner.from_dict(payload), result=dict(text=json.dumps(
            dict(summary=self.text, keywords=['公开测试']), ensure_ascii=False)))
    def cancel(self, owner):
        pass


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now = [1000.]
        self.store = BoardMemoryStore(Path(self.tmp.name) / 'public.sqlite3', clock=lambda: self.now[0])

    def append(self, event='public-visual', text='摄像头历史记录：桌旁有1把椅子。', **metadata):
        meta = dict(time_basis='host_received', evidence='visual_observation', source_id='legacy-device:public',
                    claims=[dict(field='source_kind', value='legacy_vlm_history'), dict(field='current', value=False)])
        meta.update(metadata)
        self.store.append_event(SCOPE, event, 'camera_observed', text, topic='legacy.visual_observation', metadata=meta)

    def worker(self, module, text, hook=None, **kwargs):
        self.now[0] = 1400.
        client = FakeClient(text, hook)
        summary = module.BoardSummaryClient(client, board_boot_id='public-boot', **kwargs)
        return BoardMemoryWorker(self.store, summary, idle=lambda: True), summary, client

    def counts(self):
        with closing(sqlite3.connect(self.store.path)) as db:
            return (db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0],
                    db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0])

    def test_original_legacy_visual_entry_reproduces_evidence_only_rejection(self):
        self.append()
        worker, summary, client = self.worker(BEFORE, '桌旁有1把椅子。')
        self.assertFalse(worker.step())
        self.assertEqual(('observation_evidence_missing',), summary.failure_metadata()['rejection_reasons'])
        self.assertEqual((1, 0), self.counts()); self.assertEqual(1, len(client.calls))

    def test_legacy_free_text_now_keeps_evidence_without_reinterpreting_as_count(self):
        self.append()
        worker, summary, client = self.worker(AFTER, '桌旁有1把椅子。')
        self.assertTrue(worker.step())
        self.assertEqual(1, len(client.calls)); self.assertEqual((0, 1), self.counts())
        value = self.store.history(SCOPE)[0]
        self.assertEqual('历史视觉观察摘要：桌旁有1把椅子。', value['text'])
        self.assertEqual(1, len(value['source_refs']))
        self.assertTrue(any(c['field'] == 'current' and c['value'] is False for c in value['claims']))
        self.assertNotEqual('structured_camera_counts', summary.metrics.get('summary_method'))

    def test_mixed_sources_labeled_as_mixed_not_all_camera_observations(self):
        self.append(text='历史视觉记录：桌上有2台设备。')
        self.store.append_event(SCOPE, 'public-statement', 'device_event', '用户计划明天检查2台设备，尚未完成。',
            topic='legacy.visual_observation', metadata=dict(evidence='statement', status='planned',
                negated=True, numbers=[2], source_id='legacy-device:public'))
        worker, summary, client = self.worker(AFTER, '桌上有2台设备；用户计划明天检查，尚未完成。')
        self.assertTrue(worker.step()); self.assertEqual(1, len(client.calls))
        value = self.store.history(SCOPE)[0]
        self.assertTrue(value['text'].startswith('混合历史记录（含视觉观察来源）：'))
        self.assertEqual(2, len(value['source_refs']))
        evidence = {c['value'] for c in value['claims'] if c['field'] == 'evidence'}
        self.assertEqual({'statement', 'visual_observation'}, evidence)

    def test_existing_observation_word_not_duplicated(self):
        self.append()
        worker, summary, client = self.worker(AFTER, '历史视觉记录：桌旁有1把椅子。')
        self.assertTrue(worker.step())
        self.assertEqual('历史视觉记录：桌旁有1把椅子。', self.store.history(SCOPE)[0]['text'])

    def test_nonvisual_text_not_relabelled(self):
        self.store.append_event(SCOPE, 'public-statement', 'device_event', '设备状态正常。',
            topic='设备', metadata=dict(evidence='device_confirmed'))
        worker, summary, client = self.worker(AFTER, '设备状态正常。')
        self.assertTrue(worker.step())
        self.assertEqual('设备状态正常。', self.store.history(SCOPE)[0]['text'])

    def test_all_other_protected_fields_still_reject_and_keep_bodies(self):
        cases = [
            ('公开甲计划检查42台设备，尚未完成。', dict(names=['公开甲'], numbers=[42], negated=True, status='planned'),
             '有人计划检查42台设备，尚未完成。', 'protected_name_missing'),
            ('公开甲计划检查42台设备，尚未完成。', dict(numbers=[42]),
             '公开甲计划检查41台设备，尚未完成。', 'protected_number_missing_or_changed'),
            ('公开甲尚未检查42台设备。', dict(numbers=[42], negated=True),
             '公开甲检查42台设备。', 'negation_missing'),
            ('公开甲计划检查42台设备。', dict(numbers=[42], status='planned'),
             '公开甲检查42台设备。', 'planned_status_missing'),
            ('公开甲已经完成42台设备检查。', dict(numbers=[42], status='completed'),
             '公开甲检查42台设备。', 'completed_status_missing'),
            ('公开甲取消42台设备检查。', dict(numbers=[42], status='cancelled'),
             '公开甲检查42台设备。', 'cancelled_status_missing')]
        for body, meta, reply, code in cases:
            with self.subTest(code=code):
                prepared = dict(scope=SCOPE, topic='legacy.visual_observation', start_utc=1000., end_utc=1000.,
                    schema_version=1, required_claims=[], sources=[dict(event_id='public-source', revision=1,
                    include_in_summary=True, recorded_utc=1000., source='camera_observed', text=body,
                    metadata=dict(evidence='visual_observation', **meta))])
                client = FakeClient(reply); summary = AFTER.BoardSummaryClient(client, board_boot_id='public-boot')
                with self.assertRaises(CandidateRejected) as caught: summary(prepared, lambda: False)
                self.assertIn(code, caught.exception.rejection_reasons)
                self.assertEqual(1, len(client.calls))

    def test_label_budget_counts_and_never_truncates_or_adds_inference_retry(self):
        self.append(text='历史视觉记录：公开设备正常。')
        worker, summary, client = self.worker(AFTER, 'A' * 60, final_summary_max_utf8_bytes=64)
        self.assertFalse(worker.step()); self.assertEqual((1, 0), self.counts())
        self.assertEqual(1, len(client.calls))
        self.assertEqual('context_limit', summary.failure_metadata()['code'])

    def test_legitimate_numeric_rejection_keeps_original_body_in_real_store(self):
        self.append(text='视觉历史：桌旁有42台设备。', numbers=[42])
        worker, summary, client = self.worker(AFTER, '桌旁有41台设备。')
        self.assertFalse(worker.step()); self.assertEqual((1, 0), self.counts())
        self.assertIn('protected_number_missing_or_changed', summary.failure_metadata()['rejection_reasons'])
        with closing(sqlite3.connect(self.store.path)) as db:
            body = db.execute('SELECT text FROM bm_bodies').fetchone()[0]
        self.assertEqual('视觉历史：桌旁有42台设备。', body)
        self.assertEqual(1, len(client.calls))

    def test_origin_label_cannot_satisfy_a_missing_protected_name(self):
        for name in ['历史', '视觉', '观察', '来源']:
            with self.subTest(name=name):
                summary = AFTER.BoardSummaryClient(FakeClient('设备正常。'), board_boot_id='public-boot')
                semantic = dict(summary='设备正常。', keywords=['公开'])
                sources = [dict(source='camera_observed', text='项目代号为' + name + '。',
                    protected=dict(evidence='visual_observation', names=[name]))]
                with self.assertRaises(CandidateRejected) as caught:
                    summary._observation_provenance(semantic, sources, maximum=768)
                self.assertEqual(('protected_name_missing',), caught.exception.rejection_reasons)

    def test_full_multipart_covers_all_bytes_before_original_atomic_commit(self):
        body = '历史视觉记录：设备正常。' * 160
        self.append(text=body)
        worker, summary, client = self.worker(AFTER, '设备正常。')
        self.assertTrue(worker.step()); self.assertGreater(len(client.calls), 1)
        self.assertEqual(len(body.encode('utf-8')), summary.metrics['covered_utf8_bytes'])
        self.assertTrue(summary.metrics['complete_source_coverage'])
        self.assertEqual((0, 1), self.counts())
        result = self.store.history(SCOPE)[0]
        validate_compaction_text(result['text'], [dict(include_in_summary=True, text=body,
            metadata=dict(evidence='visual_observation'))])
        self.assertEqual(1, len(result['source_refs']))
        self.assertLessEqual(len(result['text'].encode('utf-8')), summary.final_maximum)

    def test_structured_current_camera_route_stays_model_free(self):
        collector = VisualTimelineCollector('public-boot', self.store.append_event, SCOPE, utc_clock=lambda: self.now[0])
        for frame, stamp in [(1, 1000), (2, 1400), (3, 1800)]:
            collector.ingest_health(dict(board_boot_id='public-boot', service_epoch='public-service',
                camera_epoch='public-camera', role='DPU_YOLOX_PERSON_PREVIEW', detector=dict(count_kind='people'),
                observation_frame_id=frame, people_count=2, observation_age_ms=10, capture_age_ms=5,
                camera_error='', detector_error='', timestamp_kind='appsink_dequeue_monotonic'),
                requested_mono_ms=stamp, received_mono_ms=stamp+10)
        worker, summary, client = self.worker(AFTER, 'SHOULD_NOT_BE_CALLED')
        self.assertTrue(worker.step()); self.assertEqual([], client.calls)
        self.assertEqual('structured_camera_counts', summary.failure_metadata()['method'])

    def test_fragment_protected_annotation_keeps_observation_without_extra_model_call(self):
        client = FakeClient('相关历史记录。')
        summary = AFTER.BoardSummaryClient(client, board_boot_id='public-boot')
        summary.metrics = dict(model_calls=0)
        value = summary._infer([dict(source='camera_observed', protected=dict(evidence='visual_observation'))],
                               lambda: False, deadline=summary.clock()+30, multipart=True)
        self.assertTrue(value['summary'].startswith('历史视觉观察摘要：'))
        validate_compaction_text(value['summary'], [dict(include_in_summary=True, text='',
            metadata=dict(evidence='visual_observation'))])
        self.assertEqual(1, len(client.calls))

    def test_source_forget_or_lease_expiry_after_fake_model_keeps_no_summary(self):
        for change in ['forget', 'lease_expired', 'new_turn']:
            with self.subTest(change=change):
                with tempfile.TemporaryDirectory() as temp:
                    now=[1000.]; store=BoardMemoryStore(Path(temp)/'synthetic.sqlite3', clock=lambda: now[0])
                    store.append_event(SCOPE, 'public-source', 'camera_observed', '历史记录：有1台设备。',
                        topic='legacy.visual_observation', metadata=dict(evidence='visual_observation'))
                    now[0]=1400.
                    def hook():
                        if change == 'forget': store.forget(SCOPE, event_ids=['public-source'])
                        elif change == 'lease_expired': now[0]+=61
                        else: store.begin_turn(dict(kind='conversation', id='public-new'), 'public-turn', '新问题', generation=1)
                    summary=AFTER.BoardSummaryClient(FakeClient('有1台设备。', hook), board_boot_id='public-boot')
                    worker=BoardMemoryWorker(store, summary, idle=lambda: True)
                    self.assertFalse(worker.step()); self.assertEqual(0, store.health()['valid_summaries'])
                    if change != 'forget': self.assertGreaterEqual(store.health()['active_bodies'], 1)


if __name__ == '__main__': unittest.main()
