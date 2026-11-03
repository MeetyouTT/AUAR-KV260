"""Only synthetic stores and fake vectors; exercise real sole-worker cleanup."""
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from tests.framework.test_board_business import Clock
from tests.framework.test_board_speaker_business import Encoder, MODEL, quality, capture, BOOT


def test_delayed_old_cleanup_preserves_later_committed_receipt_and_other_actor(tmp_path):
    vectors = []
    for coordinate in range(3):
        vector = [0.] * 192
        vector[coordinate] = 1.
        vectors.extend([vector] * 3)
    encoder = Encoder(vectors=vectors)
    clock = Clock()
    service = BoardSpeakerBusiness.create(tmp_path/'public-synthetic-only',
        encoder_factory=lambda: encoder, board_boot_id=BOOT,
        quality=quality, expected_model_id=MODEL,
        anonymous_config={'enabled': True}, wall_clock=lambda: 1793400000.,
        clock=clock, data_origin='synthetic')

    def say(actor, n, text):
        meta, pcm = capture(n)
        meta['session_id'] = actor
        meta['request_id'] = actor+'-'+str(n)
        return service.turn(meta, text, pcm), meta

    def enroll(actor, first, name):
        say(actor, first, '登记我的声纹，我叫'+name)
        for n in range(first+1, first+4):
            say(actor, n, '第'+str(n)+'段公开合成样本')
        reply, meta = say(actor, first+4, '确认保存声纹')
        assert '已保存' in reply
        return meta

    def snapshot():
        device = service.hub.speaker
        return (dict((actor, dict(value)) for actor, value in device.save_receipts.items()),
                len(device.store.people()))

    try:
        old = enroll('actor-a', 1, '测试甲')
        current = enroll('actor-a', 6, '测试丙')
        enroll('actor-b', 1, '测试乙')
        before, people = service.pool.submit(snapshot).result(timeout=2.)
        assert people == 3
        assert before[(BOOT, 'actor-a')]['generation'] == 10
        assert before[(BOOT, 'actor-b')]['generation'] == 5

        # A late _call cleanup uses the old request's actor+generation.  Run it
        # on the same sole worker after genuine later commits, as the queued
        # cleanup can arrive after an already-submitted newer operation.
        service.pool.submit(service._clear_status_receipt, old).result(timeout=2.)
        after, people = service.pool.submit(snapshot).result(timeout=2.)
        assert after == before and people == 3

        # Matching-generation cleanup invalidates only transient evidence.
        service.pool.submit(service._clear_status_receipt, current).result(timeout=2.)
        after, people = service.pool.submit(snapshot).result(timeout=2.)
        assert (BOOT, 'actor-a') not in after
        assert after[(BOOT, 'actor-b')] == before[(BOOT, 'actor-b')]
        assert people == 3
        reply, _ = say('actor-a', 11, '你有没有保存我的声纹？')
        assert '不能判断' in reply and '未保存' not in reply
        reply, _ = say('actor-b', 6, '你有没有保存我的声纹？')
        assert '已收到声纹保存提交回执' in reply
    finally:
        assert service.close(timeout=2.)
