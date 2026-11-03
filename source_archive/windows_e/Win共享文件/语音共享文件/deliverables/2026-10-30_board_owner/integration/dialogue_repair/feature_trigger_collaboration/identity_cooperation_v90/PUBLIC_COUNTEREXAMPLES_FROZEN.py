"""Public synthetic identities and fake encoder; no hardware, model or real DB."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest

from common.identity_links import validate_resolution
from common.voice_enrollment import identity_query_requested
from tools.provisional_voice import query_reply
from board.runtime.board_business import BoardBusinessConfig, create_board_business_runtime
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from common.conversation_selection import ConversationSelection
from tools.yuki_business_candidate import bind_runtime_pair
from tests.framework.test_board_speaker_business import (MODEL, Encoder, quality, capture,
    visual, packet, bind_existing_face_and_voice)
from tests.framework.test_simple_enrollment import snapshot as basic_snapshot

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('identity_public_inputs', H / 'board_integration_v17/worker.py')
public = importlib.util.module_from_spec(spec)
spec.loader.exec_module(public)
BOOT = 'public-synthetic-boot'


def conflict(meta):
    return validate_resolution(dict(version=1, context=meta, state='CONFLICT', reason='MODALITY_IDENTITIES_DISAGREE',
        person_id=None, name=None, modalities=['face', 'voice'], claim_scope='none', provisional=False,
        field_calibrated=False, identity_verified=False, personal_memory_allowed=False,
        single_speaker_verified=False), meta)


@pytest.mark.parametrize('question', ['我叫什么名字', '你还认识我吗', '我是谁呀', '你记得我的名字吗'])
def test_all_accepted_direct_questions_render_the_same_conflict(question):
    meta, _ = capture(1)
    assert identity_query_requested(question)
    assert query_reply(question, conflict(meta)) == query_reply('我是谁', conflict(meta))


class Scene:
    def __init__(self, clock):
        self.clock = clock
        self.frame = 100
        self.identity = 'public-face'
        self.name = '小林'
        self.face_count = 1
        self.track_generation = 1
        self.source_age = 10
        self.revision = 7
        self.other_face_link = False

    def snapshot(self):
        self.clock.now += .02
        self.frame += 1
        now = round(self.clock() * 1000)
        target = dict(camera_epoch='public-camera', track_id=1, track_generation=self.track_generation)
        value = basic_snapshot()
        value.update(board_boot_id=BOOT, service_epoch='public-service', sequence=self.frame,
            observed_mono_ms=now, preview=dict(camera_epoch='public-camera', frame_id=self.frame,
                captured_mono_ms=now-self.source_age))
        from board.interaction.ui_contract import validate_snapshot
        value['modules']['target'].update(selected=target, tracks=[dict(key=target, label='face')])
        value['modules']['vision']['people_count'] = self.face_count
        value['modules']['identity'].update(state='KNOWN', person_id=self.identity, display_name=self.name,
            db_version=self.revision, target_kind='face', face_count=self.face_count, face_target=target,
            face_targets=[dict(key=target, label='face')], target=target,
            source_frame_id=self.frame, source_mono_ms=now-self.source_age,
            face_preview=dict(target=target, frame_id=self.frame, captured_mono_ms=now-self.source_age, ttl_ms=2000),
            people=[dict(person_id=self.identity, display_name=self.name)], backend='DPU_SFACE_INT8')
        return validate_snapshot(value, BOOT, now)

    def read(self, meta, snapshot):
        value = packet(meta)
        value['gallery']['revision'] = self.revision
        fingerprint = ('b' if self.identity == 'public-face' else 'c') * 64
        value['current'] = dict(identity_id=self.identity, template_fingerprint=fingerprint)
        value['inventory'] = [['public-face', 'b'*64]]
        if self.other_face_link:
            value['inventory'].append(['public-face-b', 'c'*64])
        return value


class Harness:
    def __init__(self, root):
        self.clock = public.Mono()
        self.millis = patch('board.interaction.ui_contract.millis', lambda:round(self.clock()*1000))
        self.millis.start()
        timeline = public.PublicTimeline(BOOT, self.clock)
        self.client = public.SyntheticModelTransport()
        self.asr = public.ScriptedAsr()
        self.scene = Scene(self.clock)
        self.pair = public.public_pair(H / 'candidate_m03_v90_stage/public_runtime_v90')
        self.bundle = create_board_business_runtime(BoardBusinessConfig(str(root/'business'), (1793300000.,1793500000.)),
            BOOT, asr=self.asr, system_prompt=self.pair.selected_prompt,
            conversation_selection=ConversationSelection(root/'selection.json'), timeline=timeline,
            client=self.client, clock=self.clock, capture_idle=lambda:True,
            identity_snapshot=self.scene.snapshot, identity_command=lambda command: (_ for _ in ()).throw(
                AssertionError('Read-only public scenarios must not send enrollment commands')))
        bind_runtime_pair(self.bundle, self.pair)
        self.encoder = Encoder()
        self.service = BoardSpeakerBusiness.create(root/'speaker', encoder_factory=lambda:self.encoder,
            board_boot_id=BOOT, quality=quality, expected_model_id=MODEL, anonymous_config={'enabled':True},
            wall_clock=timeline.event_time, clock=self.clock, data_origin='synthetic')
        bind_existing_face_and_voice(self.service)  # Original signed-confirmation path, public fake face bridge.
        self.bundle.attach_speaker_business(self.service, face_readback=self.scene)
        self.bundle.jobs.select_conversation(resume=False)
        self.n = 0

    def say(self, text):
        self.n += 1
        self.clock.now += .2
        self.asr.text = text
        pcm = (1000+self.n).to_bytes(2,'little') * 48000
        clip = NS(capture_id='public-cooperation-'+str(self.n), audio=NS(sample_count=48000), pcm=pcm)
        self.bundle.jobs.capture_started(clip.capture_id)
        assert self.bundle.jobs.capture_owners[clip.capture_id] is not None
        meta = self.bundle.jobs.submit(clip)
        assert self.bundle.jobs.run_next()
        rows = []
        while True:
            value = self.bundle.jobs.poll()
            if value is None:
                break
            rows.append(value)
        assert not any('error' in row for row in rows), rows
        complete = next(row['network_complete'] for row in rows if 'network_complete' in row)
        self.bundle.jobs.acknowledge(meta, complete)
        self.bundle.jobs.drain_actions()
        assert self.bundle.jobs.last_ack['committed']
        self.service.pool.submit(lambda:None).result(2)  # Sole-worker barrier, not a new background owner.
        cid = self.bundle.jobs.conversation_selection.active
        value = self.service.analysis_result(meta, cid)
        spoken = ''.join(row['channel_event']['text'] for row in rows if row.get('channel_event',{}).get('kind')=='text')
        return spoken, value

    def add_other_public_face_link(self):
        def seed_only_public_fixture():
            registry = self.service.hub.binding.registry
            with registry._db(write=True) as db:
                db.execute('INSERT INTO linked_people VALUES(?,?,?,?,?)', ('e'*32,'测试乙','测试乙','ACTIVE',1000.))
                db.execute('INSERT INTO modality_links VALUES(?,?,?,?,?,?,?,?)',
                    ('e'*32,'face','gallery-'+'f'*32,'public-face-b','public-face-model',7,'c'*64,'ACTIVE'))
        self.service.pool.submit(seed_only_public_fixture).result(2)
        self.scene.revision = 8
        self.scene.other_face_link = True

    def close(self):
        try:
            self.bundle.close()
        finally:
            self.millis.stop()


def test_ordinary_paired_capture_keeps_its_current_face_link_evidence(tmp_path):
    h = Harness(tmp_path)
    try:
        before = h.encoder.calls
        _, value = h.say('雪妃，今天我们聊聊海风')
        assert value['status'] == 'COMPLETE'
        assert value['identity']['state'] == 'MATCH_CANDIDATE'
        assert value['identity']['claim_scope'] == 'visible_person'
        assert 'face' in value['identity']['modalities']
        assert h.encoder.calls == before+1
        assert value['personal_memory_allowed'] is False and not h.bundle.access.grants
        assert value['voice']['state'] == 'NOT_CALIBRATED'
    finally:
        h.close()


@pytest.mark.parametrize('question', ['我是谁', '我叫什么名字', '你还认识我吗', '我是谁呀'])
def test_actual_paired_identity_question_reports_face_voice_conflict(tmp_path, question):
    h = Harness(tmp_path)
    try:
        h.add_other_public_face_link()
        for n in range(3):
            h.say('第'+str(n)+'段公开合成普通聊天')
        h.scene.identity, h.scene.name = 'public-face-b', '测试乙'
        spoken, value = h.say('雪妃，'+question)
        assert value['status'] == 'COMPLETE'
        assert value['identity']['state'] == 'CONFLICT'
        assert '不一致' in spoken and '先不确定' in spoken
        assert '测试乙' not in spoken and '小林' not in spoken
        assert not h.bundle.access.grants
    finally:
        h.close()
