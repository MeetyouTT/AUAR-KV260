def verify_short_ordinary_worker_on_arm():
    import struct
    import tempfile
    import threading
    from types import SimpleNamespace
    from board.runtime.board_speaker_business import BoardSpeakerBusiness, ordinary_voice_segment
    from common.speaker_identity import voiced_pcm
    from board.runtime.board_dialogue import BoardReply, address_reply
    import webrtcvad
    original_vad_module = sys.modules['webrtcvad']
    raw, details = ordinary_voice_segment(b'\x00\x00' * 52800)
    assert raw is None and details['voiced_ms'] == 0
    class Vad:
        def __init__(self, mode):
            assert mode == 2
        def is_speech(self, frame, rate):
            return True
    class Encoder:
        model_id = 'synthetic-ecapa-arm-check'
        dimension = 192
        calls = 0
        def encode(self, pcm):
            self.calls += 1
            marker = struct.unpack('<h', pcm[:2])[0]
            index = {1: 0, 2: 1}.get(marker, 2)
            return tuple(float(n == index) for n in range(192))
    encoder = Encoder()
    sys.modules['webrtcvad'] = SimpleNamespace(Vad=Vad)
    checks = []
    try:
        with tempfile.TemporaryDirectory(prefix='aura-short-voice-synthetic-') as temporary:
            private = Path(temporary) / 'synthetic-only'
            service = BoardSpeakerBusiness.create(private, encoder_factory=lambda: encoder,
                board_boot_id='synthetic-arm-boot', quality=voiced_pcm, expected_model_id=encoder.model_id,
                anonymous_config={'enabled': True}, calibration=dict(threshold=.35, margin=.1,
                    consistency=.6, field_calibrated=False), clock=time.monotonic,
                wall_clock=time.time, data_origin='synthetic')
            try:
                def enroll_fixture():
                    for index, name in enumerate(('合成甲', '合成乙')):
                        service.hub.speaker.store.original.enroll('synthetic-' + str(index), name,
                            tuple(float(n == index) for n in range(192)), consent=True)
                    service._refresh_public()
                service.pool.submit(enroll_fixture).result(3)
                cid = 'a' * 32
                for generation, (marker, seconds, name) in enumerate((
                        (1, 2.52, '合成甲'), (2, 2.1, '合成乙'), (1, 1.2, None),
                        (3, 2.1, None), (1, 1.8, '合成甲')), 1):
                    count = round(seconds * 16000)
                    pcm = struct.pack('<hh', marker, generation) + b'\x01\x00' * (count - 2)
                    meta = dict(protocol='aura-asr-1', board_boot_id='synthetic-arm-boot',
                        session_id='synthetic-arm-session', request_id='synthetic-request-' + str(generation),
                        generation=generation, capture_id='synthetic-capture-' + str(generation),
                        sample_count=count, pcm_sha256=hashlib.sha256(pcm).hexdigest(), budget_ms=120000)
                    cancel = threading.Event()
                    service.submit_analysis(meta, pcm, cid, cancel_event=cancel, deadline=time.monotonic() + 4)
                    service.pool.submit(lambda: None).result(3)
                    owner = {key: meta[key] for key in ('board_boot_id', 'session_id', 'generation', 'request_id')}
                    hint = service.conversation_address(owner, cid, cancel_event=cancel, deadline=time.monotonic() + 2)
                    assert (hint['display_name'] if hint else None) == name
                    reply = address_reply(BoardReply('这是合成检查。'), name)
                    assert reply.text == (name + '，' if name else '') + '这是合成检查。'
                    assert service.public()['conversation_address']['personal_memory_allowed'] is False
                    checks.append(True)
                assert encoder.calls == 4
                assert not service.hub.progressive_speaker.provisional.streaks
                assert not service.hub.progressive_speaker.provisional.results
                try:
                    voiced_pcm(b'\x01\x00' * 40320)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Original enrollment duration gate was relaxed')
            finally:
                assert service.close(timeout=3)
    finally:
        sys.modules['webrtcvad'] = original_vad_module
    return dict(cases_passed=len(checks), one_embedding_per_eligible_capture=True,
        unknown_and_too_short_clear_previous_name=True, enrollment_gate_preserved=True,
        actual_private_stores_accessed=False, real_user_audio_used=False,
        original_worker_closed=True, temporary_synthetic_files_removed=True)
