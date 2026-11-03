"""Only public synthetic stores/PCM and fake encoders; no real model/device."""
import importlib.util
import json
from pathlib import Path
import struct

import pytest

HERE = Path(__file__).resolve().parent
FEATURE = HERE.parent
QUESTION = '你已经帮我把声纹登记保存成功了吗？'


@pytest.mark.parametrize('change', ['expired', 'revision'])
def test_same_current_speaker_request_rechecks_status_after_receipt_invalidated(tmp_path, change):
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from tests.framework.test_board_business import Clock
    from tests.framework.test_board_speaker_business import Encoder, MODEL, quality, capture
    clock = Clock()
    service = BoardSpeakerBusiness.create(tmp_path/'public-speaker', encoder_factory=Encoder,
        board_boot_id='test-boot', quality=quality, expected_model_id=MODEL,
        anonymous_config={'enabled': True}, wall_clock=lambda: 1793400000.,
        clock=clock, data_origin='synthetic')
    def say(n, text):
        meta, pcm = capture(n, boot='test-boot'); meta['budget_ms'] = 120000
        return service.turn(meta, text, pcm, deadline=clock()+120, is_current=lambda: True)
    try:
        say(1, '登记我的声纹，我叫测试甲')
        for n in (2, 3, 4): say(n, '不同的公开合成句子')
        say(5, '确认保存声纹')
        meta, pcm = capture(6, boot='test-boot'); meta['budget_ms'] = 120000
        original_deadline = clock()+120
        first = service.turn(meta, QUESTION, pcm, deadline=original_deadline, is_current=lambda: True)
        assert '已收到声纹保存提交回执' in first
        if change == 'expired':
            clock.now += 60.1
        else:
            def revise():
                with service.hub.speaker.store.db:
                    service.hub.speaker.store.db.execute(
                        "UPDATE metadata SET value=value+1 WHERE key='revision'")
            service.pool.submit(revise).result(1)
        # Same valid actor/meta, original deadline remains live, _submit accepts
        # exact replay. A fresh request provides a control for status semantics.
        replay = service.turn(meta, QUESTION, pcm, deadline=original_deadline, is_current=lambda: True)
        fresh = say(7, QUESTION)
        facts = dict(change=change, original_deadline_still_live=clock()<original_deadline,
            repeated_request_positive='已收到声纹保存提交回执' in replay,
            fresh_request_unknown='不能判断' in fresh, private_store_accessed=False)
        (HERE/('replay_'+change+'.json')).write_text(json.dumps(facts, indent=2)+'\n', encoding='utf-8')
        assert '不能判断' in replay, facts
    finally:
        service.close()


def test_unmatched_natural_status_question_during_enrollment_does_not_sample(tmp_path):
    from board.runtime.board_business import BoardBusinessConfig, BoardBusinessRuntime
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from common.conversation_selection import ConversationSelection
    from tests.framework.test_board_business import Clock, Timeline, Client, Asr, drain
    from tests.framework.test_board_speaker_business import Encoder, MODEL, quality
    from tools.yuki_business_candidate import bind_runtime_pair
    from common.feature_intents import speaker_query_requested
    source = FEATURE.parent.parent/'resume_yuki_business_candidate_v2/test_candidate_contracts.py'
    spec = importlib.util.spec_from_file_location('independent_v2_pair', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    pair, _, _ = module.pair_ready()
    clock, timeline, client = Clock(), Timeline(), Client()
    bundle = BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'public-business'),
        (1793300000., 1793500000.)), 'test-boot', asr=Asr(), system_prompt=pair.selected_prompt,
        conversation_selection=ConversationSelection(tmp_path/'public-selection.json'),
        timeline=timeline, client=client, clock=clock, capture_idle=lambda: True,
        identity_snapshot=lambda: None, identity_command=lambda command: None)
    bind_runtime_pair(bundle, pair)
    business = BoardSpeakerBusiness.create(tmp_path/'public-speaker', encoder_factory=Encoder,
        board_boot_id='test-boot', quality=quality, expected_model_id=MODEL,
        anonymous_config={'enabled': True}, wall_clock=timeline.event_time,
        clock=clock, data_origin='synthetic')
    bundle.attach_speaker_business(business); bundle.jobs.select_conversation(resume=False)
    def say(n, text):
        bundle.jobs.asr.text = text
        pcm = struct.pack('<h', n*1000)*48000
        meta = bundle.jobs.submit(type('Clip', (), dict(capture_id='review-'+str(n),
            audio=type('Audio', (), dict(sample_count=48000))(), pcm=pcm))())
        assert bundle.jobs.run_next()
        values = drain(bundle.jobs)
        assert not any('error' in row for row in values), values
        complete = next(row['network_complete'] for row in values if 'network_complete' in row)
        bundle.jobs.acknowledge(meta, complete); bundle.jobs.drain_actions()
        assert bundle.jobs.last_ack['committed']
        return meta
    def samples(meta):
        def read():
            row = business.hub.speaker.sessions.get(business.hub.speaker.key(meta))
            return len(row['vectors']) if row and 'vectors' in row else None
        return business.pool.submit(read).result(1)
    try:
        meta = say(1, '雪妃，登记我的声纹，我叫测试乙')
        before = samples(meta); assert before == 0
        text = '你有没有保存我的声纹？'
        meta = say(2, text)
        after = samples(meta)
        facts = dict(query_matched=speaker_query_requested(text), samples_before=before,
            samples_after=after, ack_committed=True, profile_grants=len(bundle.access.grants),
            private_store_accessed=False)
        (HERE/'unmatched_query.json').write_text(json.dumps(facts, indent=2)+'\n', encoding='utf-8')
        assert after == before, facts
    finally:
        bundle.close()
