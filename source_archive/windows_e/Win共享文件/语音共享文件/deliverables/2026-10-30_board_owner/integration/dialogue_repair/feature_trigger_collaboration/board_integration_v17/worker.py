"""Root-run, isolated public integration using exact v17 production classes.

Default execution has NO network, model, microphone, camera or physical player.
All durable state is new synthetic state in one owned temporary directory.
The actual paired route, handlers, SQLite stores and complete ACK guards run.
No production factory/private bootstrap is called. Native readiness, ASR,
encoder, camera-health input and playback consumption are explicit fixtures.
"""
import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import traceback
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
STARTUP = '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
MANIFEST = '38a267a4f8d504803587c8be353452b146f1e232e926ac4e061a5e2832b33620'
MAPPING = '348c435302e4e855d9bf4ef354f0b26d56ef9dfac64438a4fb11f70b5f6e63af'
PROMPT = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
MODEL = 'ecapa-voxceleb-' + 'a'*64  # Synthetic encoder ID; never a real model.
PUBLIC_CONFIGS = {'config/character_profile.local.json', 'config/persona.xuefei.candidate.json',
                  'config/yuki_pair.formal.json', 'config/yuki_accepted_prompt.baseline.txt'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def persist(path, value):
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(tmp, path)


def require(condition, code):
    if not condition:
        raise AssertionError(code)


def verify(args):
    raw = args.mapping.read_bytes()
    require(sha(raw) == MAPPING, 'mapping_changed')
    mapping = json.loads(raw)
    require(mapping['startup_sha256'] == STARTUP and mapping['source_manifest_sha256'] == MANIFEST,
            'different_release')
    pins = mapping['component_pins']
    require(len(pins) == 379, 'component_count_changed')
    root = args.runtime_root.resolve(strict=True)
    files = {rel: digest for rel, digest in pins.items() if rel.endswith('.py') or rel in PUBLIC_CONFIGS}
    for rel, digest in files.items():
        path = root/rel
        require(not path.is_symlink() and path.resolve().is_relative_to(root), 'source_path_escape')
        require(sha(path.read_bytes()) == digest, 'runtime_source_changed:'+rel)
    if args.local_replay:
        boot, bounds = 'public-local-v17', [1793300000., 1793500000.]
    else:
        require(sys.platform == 'linux' and args.coordinated_slot, 'root_board_slot_required')
        require(args.startup_config is not None, 'startup_required')
        startup_raw = args.startup_config.read_bytes()
        require(sha(startup_raw) == STARTUP, 'startup_changed')
        require(json.loads(startup_raw)['component_sha256'] == pins, 'startup_pins_changed')
        config = root/'config/board_avatar_gtk.json'
        require(not config.is_symlink() and sha(config.read_bytes()) == pins['config/board_avatar_gtk.json'],
                'board_config_changed')
        bounds = json.loads(config.read_bytes())['board_business']['utc_bounds']
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(len(bounds) == 2 and bounds[0] < 1793400000. < bounds[1], 'synthetic_utc_out_of_bounds')
    return dict(runtime_root=str(root), startup_sha256=STARTUP, source_manifest_sha256=MANIFEST,
                mapping_sha256=MAPPING, components=379, verified_public_files=len(files), boot_id=boot,
                utc_bounds=bounds, live_startup_checked=not args.local_replay)


class Mono:
    def __init__(self):
        self.now = 10.
    def __call__(self):
        return self.now


class PublicTimeline:
    """Explicit synthetic clock; never presented as a verified live UTC anchor."""
    def __init__(self, boot, mono):
        self.boot_id, self.monotonic = boot, mono
    def event_time(self):
        return 1793400000. + self.monotonic()
    def safe_for_compaction(self):
        return True
    def compaction_guard(self):
        return nullcontext()
    def quality_snapshot(self):
        return {'status': 'synthetic_test_clock'}


class ScriptedAsr:
    model_sha256 = 'a'*64
    text = ''
    def transcribe(self, pcm, **kwargs):
        require(not kwargs['cancelled'](), 'asr_cancelled')
        return self.text


class SyntheticEncoder:
    dimension, model_id = 192, MODEL
    def __init__(self):
        self.calls = 0
    def encode(self, pcm):
        self.calls += 1
        return [1., 0.] + [0.]*190


def synthetic_quality(pcm):
    return pcm, {'vad_speech_seconds': 3.}


class SyntheticModelTransport:
    host, port = '192.168.50.1', 8797
    def __init__(self):
        self.calls, self.cancels = [], []
    def request(self, kind, payload, **kwargs):
        from common.model_inference_wire import Owner, validate_request, make_response, audio_payload
        payload = validate_request(kind, payload)
        require(not kwargs['cancelled'](), 'model_cancelled')
        self.calls.append((kind, payload))
        result = (dict(text=json.dumps(dict(reply_text='只依据本次返回的公开历史回答。',
                  emotion='friendly', avatar_action=''), ensure_ascii=False)) if kind == 'llm' else
                  dict(audio=audio_payload(b'\x01\x00'*2400, 24000)))
        return make_response(Owner.from_dict(payload), result=result)
    def cancel(self, owner):
        self.cancels.append(owner)


class PublicCameraReader:
    source_kind = 'fixture'
    def __init__(self, boot, mono):
        self.boot, self.clock = boot, mono
        self.count, self.frame, self.down = 2, 0, False
    def read(self, **kwargs):
        from board.runtime.visual_memory import CameraHealthSample, _projection
        if self.down:
            raise OSError('public_fixture_unavailable')
        self.frame += 1
        data = dict(board_boot_id=self.boot, service_epoch='public-service', camera_epoch='public-camera',
            role='DPU_YOLOX_PERSON_PREVIEW', detector={'count_kind': 'people'},
            observation_frame_id=self.frame, people_count=self.count,
            observation_age_ms=10, capture_age_ms=5, camera_error='', detector_error='',
            timestamp_kind='appsink_dequeue_monotonic')
        now = self.clock()*1000
        return CameraHealthSample(_projection(data), now, now, 'fixture')
    def close(self):
        pass


def public_pair(root):
    # Read only hash-verified public persona resources. Full formal prepare_pair
    # also reads legacy settings; intentionally do not call that production IO.
    from tools.formal_yuki import CandidatePair
    from tools.board_persona_candidate import load_candidate
    meta = json.loads((root/'config/yuki_pair.formal.json').read_bytes())
    identity = meta['identity']
    persona = load_candidate(root/'config/persona.xuefei.candidate.json',
        expected_config_sha256=identity['persona_config_sha256'],
        expected_profile_version=identity['profile_version'],
        accepted_system_prompt=(root/'config/yuki_accepted_prompt.baseline.txt').read_text(encoding='utf-8'))
    require(sha(persona.system_prompt.encode()) == identity['prompt_sha256'] == PROMPT, 'persona_changed')
    pair = CandidatePair(root, meta, persona)
    pair.attach_mailbox(SimpleNamespace(lock=threading.RLock(), ready=True, _drawn=False))
    pair.observe_native_frame({'frames': 1})  # Explicit fixture; no EGL or rendering acceptance.
    pair.require_ready()
    return pair


class Harness:
    def __init__(self, root, temp, boot):
        from board.runtime.board_business import BoardBusinessConfig, BoardBusinessRuntime
        from board.runtime.board_speaker_business import BoardSpeakerBusiness
        from board.runtime.visual_memory import VisualTimelineWorker
        from board.runtime.visual_policy import LocalVisualQueries
        from common.conversation_selection import ConversationSelection
        from tools.yuki_business_candidate import bind_runtime_pair
        self.clock = Mono()
        self.timeline = PublicTimeline(boot, self.clock)
        self.transport, self.asr, self.encoder = SyntheticModelTransport(), ScriptedAsr(), SyntheticEncoder()
        self.pair = public_pair(root)
        self.bundle = BoardBusinessRuntime(BoardBusinessConfig(str(temp/'business'), (1793300000., 1793500000.)),
            boot, asr=self.asr, system_prompt=self.pair.selected_prompt,
            conversation_selection=ConversationSelection(temp/'selection.json'), timeline=self.timeline,
            client=self.transport, clock=self.clock, capture_idle=lambda: True,
            identity_snapshot=lambda: None, identity_command=lambda command: None)
        bind_runtime_pair(self.bundle, self.pair)
        self.service = BoardSpeakerBusiness.create(temp/'speaker', encoder_factory=lambda: self.encoder,
            board_boot_id=boot, quality=synthetic_quality, expected_model_id=MODEL,
            anonymous_config={'enabled': True}, wall_clock=self.timeline.event_time,
            clock=self.clock, data_origin='synthetic')
        self.bundle.attach_speaker_business(self.service)
        self.reader = PublicCameraReader(boot, self.clock)
        self.visual = VisualTimelineWorker(boot, self.bundle.store, self.timeline,
            device_id='public-integration-v17', reader=self.reader, monotonic=self.clock, allow_fixture=True)
        self.bundle.visual_memory = self.visual
        self.policy = LocalVisualQueries(self.bundle.store, self.visual, self.timeline)
        self.bundle.visual_policy = self.policy
        self.bundle.jobs.special_handlers['structured_visual_query'] = self.policy
        self.bundle.jobs.visual_intent_matcher = self.policy.requested
        self.trace = []
        for name, original in tuple(self.bundle.jobs.special_handlers.items()):
            self.bundle.jobs.special_handlers[name] = self.observer(name, original)
        self.bundle.jobs.select_conversation(resume=False)
        self.n = 0

    def observer(self, name, original):
        trace = self.trace
        class Observer:
            def __call__(self, text, **kwargs):
                trace.append(name)
                return original(text, **kwargs)
            def __getattr__(self, key):
                return getattr(original, key)
        return Observer()

    @property
    def scope(self):
        return dict(kind='conversation', id=self.bundle.jobs.conversation_selection.active)

    def speaker_state(self):
        def inspect():
            device = self.service.hub.speaker
            return dict(people=len(device.store.people()), revision=device.store.revision,
                receipts=len(getattr(device, 'save_receipts', {})), stages=[s['stage'] for s in device.sessions.values()],
                samples=sum(len(s['vectors']) for s in device.sessions.values()))
        return self.service.pool.submit(inspect).result(3)

    def stable(self, count):
        self.reader.down, self.reader.count = False, count
        values = []
        for _ in range(3):
            self.clock.now += .35
            values.append(self.visual.step())
        require(self.visual.current_observation() is not None, 'fixture_not_stable')
        return values

    def say(self, text, *, route=None, contains=None, reject_bad_ack=False, expected_error=None):
        self.n += 1
        self.asr.text = text
        before, calls = len(self.trace), len(self.transport.calls)
        pcm = struct.pack('<h', 1000+self.n)*48000
        meta = self.bundle.jobs.submit(SimpleNamespace(capture_id='public-v17-'+str(self.n),
            audio=SimpleNamespace(sample_count=48000), pcm=pcm))
        require(self.bundle.jobs.run_next(), 'job_not_run')
        rows = []
        while True:
            value = self.bundle.jobs.poll()
            if value is None:
                break
            rows.append(value)
        errors = [row for row in rows if 'error' in row]
        if expected_error:
            require(errors and any(expected_error in str(e) for e in errors), 'expected_capability_not_observed')
            self.bundle.jobs.drain_actions()
            return dict(input=text, expected_capability_error=expected_error, error_observed=True,
                        full_ack=False, routes=self.trace[before:])
        require(not errors, 'job_error:'+str(errors))
        spoken = ''.join(row['channel_event']['text'] for row in rows
                         if row.get('channel_event', {}).get('kind') == 'text')
        complete = next(row['network_complete'] for row in rows if 'network_complete' in row)
        audio = b''.join(row['pcm'] for row in rows if row.get('channel_event', {}).get('kind') == 'audio')
        require(sha(audio) == complete['pcm_sha256'] and len(audio)//2 == complete['sample_count'],
                'whole_stream_hash_mismatch')
        require(complete['sample_count'] > 0, 'empty_stream')
        bad_rejected = False
        if reject_bad_ack:
            bad = dict(complete, sample_count=complete['sample_count']-1)
            try:
                self.bundle.jobs.acknowledge(meta, bad)
            except (ValueError, InterruptedError):
                bad_rejected = True
            require(bad_rejected, 'partial_ack_accepted')
        self.bundle.jobs.acknowledge(meta, complete)
        self.bundle.jobs.drain_actions()
        require(self.bundle.jobs.last_ack.get('committed') is True, 'complete_ack_not_committed')
        actual_routes = self.trace[before:]
        if route:
            require(route in actual_routes, 'wrong_route:'+repr(actual_routes))
        if contains:
            require(contains in spoken, 'wrong_public_reply:'+spoken)
        require(not self.bundle.access.grants, 'unexpected_profile_grant')
        return dict(input=text, reply=spoken, routes=actual_routes, full_ack=True,
            partial_ack_rejected=bad_rejected, pcm_sha256=complete['pcm_sha256'], samples=complete['sample_count'],
            model_rpc_kinds=[kind for kind, _ in self.transport.calls[calls:]], profile_grants=0)

    def close(self):
        self.bundle.close()
        require(self.bundle.close_complete and not self.service.pool._threads.intersection(
            {thread for thread in threading.enumerate() if thread.is_alive()}), 'speaker_worker_not_closed')


def run_cases(h, record):
    def case(name, fn):
        row = dict(id=name, status='running')
        record['cases'].append(row)
        persist(record['_output'], {k:v for k,v in record.items() if not k.startswith('_')})
        try:
            row['evidence'] = fn()
            row['status'] = 'PASS'
        except Exception as exc:
            row.update(status='FAIL', error_class=type(exc).__name__, error=str(exc)[:2000],
                       public_test_traceback=traceback.format_exc(limit=5))
        persist(record['_output'], {k:v for k,v in record.items() if not k.startswith('_')})

    def vision():
        h.stable(2)
        return h.say('雪妃，现在镜头里有几个人？', route='structured_visual_query', contains='2个人体目标', reject_bad_ack=True)
    case('V01_current_fresh_stable_count', vision)
    case('V02_spatial_unsupported', lambda: h.say('雪妃，左边有几个人？', route='structured_visual_query', contains='无法判断方位'))
    case('V03_object_unsupported', lambda: h.say('雪妃，我手里是什么物品？', route='structured_visual_query', contains='物品'))
    def zero():
        h.stable(0)
        return h.say('雪妃，现在镜头里有人吗？', route='structured_visual_query', contains='不能据此断定没人')
    case('V04_zero_is_not_absence', zero)
    def outage():
        h.reader.down = True
        h.clock.now += .35
        h.visual.step()
        return h.say('雪妃，现在镜头里有几个人？', route='structured_visual_query', contains='暂时不能判断')
    case('V05_camera_unavailable', outage)
    case('V06_history_count', lambda: h.say('雪妃，最近5分钟镜头里有几个人？', route='structured_visual_query', contains='观察记录'))
    def missing_receipt():
        before = h.speaker_state()
        answer = h.say('雪妃，你已经帮我把声纹登记保存成功了吗？', route='speaker_identity', contains='不能判断')
        require(h.speaker_state() == before, 'query_mutated_speaker_state')
        return answer
    case('S01_readonly_no_receipt', missing_receipt)
    case('S02_explicit_start', lambda: h.say('雪妃，登记我的声纹，我叫公开测试甲', route='speaker_identity', contains='分三次'))
    def during():
        before = h.speaker_state()
        answer = h.say('雪妃，你有没有保存我的声纹？', route='speaker_identity', contains='仍在采样')
        require(h.speaker_state() == before, 'readonly_query_became_sample')
        return answer
    case('S03_readonly_during_enrollment', during)
    for index in range(3):
        case('S04_sample_'+str(index+1), lambda index=index: h.say('雪妃，第'+str(index+1)+'段公开合成测试语音。',
            route='identity_enrollment', contains='确认保存声纹' if index == 2 else '再说一句'))
    def consent():
        require(h.speaker_state()['people'] == 0, 'saved_before_consent')
        answer = h.say('雪妃，确认保存声纹', route='identity_enrollment', contains='不会据此自动打开私人记忆')
        require(h.speaker_state()['people'] == 1, 'original_store_commit_missing')
        return dict(turn=answer, store=h.speaker_state(), encoder='synthetic_not_calibration')
    case('S05_store_commit_final_consent', consent)
    case('S06_receipt_next_turn', lambda: h.say('雪妃，我的声纹保存成功了吗？', route='speaker_identity', contains='已收到声纹保存提交回执'))
    def expired():
        h.clock.now += 61.
        answer = h.say('雪妃，我的声纹保存成功了吗？', route='speaker_identity', contains='不能判断')
        require(h.speaker_state()['people'] == 1, 'receipt_ttl_deleted_template')
        return answer
    case('S07_receipt_ttl_does_not_delete', expired)
    def memory_set():
        answer = h.say('雪妃，记住：项目是海风。', contains='已记住')
        require(any(f['key']=='项目' and f['value']=='海风' for f in h.bundle.store.context(h.scope)['facts']), 'fact_not_saved')
        return answer
    case('M01_remember', memory_set)
    def memory_correct():
        answer = h.say('雪妃，更正记忆：项目是晨星。', contains='已记住')
        facts = h.bundle.store.context(h.scope)['facts']
        require(any(f['value']=='晨星' for f in facts) and all(f['value']!='海风' for f in facts), 'fact_not_corrected')
        return dict(turn=answer, versions=len(h.bundle.store.fact_history(h.scope, '项目')))
    case('M02_correct', memory_correct)
    case('M03_current_fact', lambda: h.say('雪妃，我的项目是什么？', contains='晨星'))
    def forget():
        answer = h.say('雪妃，忘记项目。', contains='已忘记')
        require(not h.bundle.store.context(h.scope)['facts'], 'fact_still_searchable')
        return answer
    case('M04_forget', forget)
    def history():
        h.bundle.store.append_event(h.scope, 'public-history-only', 'user_said', '公开历史标记：海鸥。', topic='公开历史')
        answer = h.say('雪妃，查询今天海鸥记录')
        requests = [payload for kind,payload in h.transport.calls if kind=='llm']
        require(requests and any('公开历史标记' in m['content'] for m in requests[-1]['messages']),
                'history_not_in_model_context:'+repr(h.bundle.controller.context_builder.metrics))
        return dict(turn=answer, context_metrics=h.bundle.controller.context_builder.metrics,
                    semantic_model_answer_verified=False)
    case('H01_bounded_history_retrieval', history)
    case('M05_personal_without_grant', lambda: h.say('雪妃，长期记住：项目是秘密。', contains='请先选择并授权'))
    case('G01_date_delete_current_gap', lambda: h.say('雪妃，删除昨天的对话记录', expected_error='history_delete_preview'))
    case('G02_reasoning_current_gap', lambda: h.say('雪妃，帮我计算17乘以23', expected_error='reasoning_dialogue'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--startup-config', type=Path)
    parser.add_argument('--mapping', type=Path, default=HERE/'source_mapping.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--coordinated-slot')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--local-replay', action='store_true')
    args = parser.parse_args()
    require(args.output.is_absolute() and not args.output.exists(), 'fresh_absolute_output_required')
    verification = verify(args)
    sys.path.insert(0, str(args.runtime_root.resolve()))
    if args.check_only:
        persist(args.output, dict(status='PUBLIC_SOURCES_VERIFIED_NO_BUSINESS_RUN', verification=verification))
        return 0
    record = dict(schema='aura.public-production-class-integration.v17.1', status='RUNNING',
        execution_host='local_windows' if args.local_replay else 'board', coordinated_slot=args.coordinated_slot,
        verification=verification, worker_sha256=sha(Path(__file__).read_bytes()), cases=[],
        limits=dict(public_synthetic_only=True, production_classes=True, production_private_store_opened=False,
            production_factory_started=False, physical_devices_opened=False, real_models_called=False,
            real_asr=False, real_speaker_embedding=False, native_readiness='explicit_fixture',
            camera_health='explicit_fixture', utc_clock='explicit_synthetic',
            playback='simulated_complete_consumption_with_real_receipt_validation',
            physical_playback_verified=False, profile_grants_issued=False, production_controls_changed=False),
        _output=args.output)
    persist(args.output, {k:v for k,v in record.items() if not k.startswith('_')})
    parent = None if args.local_replay else '/dev/shm'
    harness = None
    try:
        with tempfile.TemporaryDirectory(prefix='aura-public-v17-', dir=parent) as temp:
            temp_path = Path(temp).resolve()
            os.chmod(temp_path, 0o700)
            require(not temp_path.is_relative_to(args.runtime_root.resolve()), 'temp_inside_production')
            harness = Harness(args.runtime_root.resolve(), temp_path, verification['boot_id'])
            try:
                run_cases(harness, record)
            finally:
                harness.close()
                record['workers_closed'] = True
        record['owned_temporary_database_removed'] = not temp_path.exists()
        record['status'] = 'PASS' if all(c['status']=='PASS' for c in record['cases']) else 'FAIL'
        record['passed'] = sum(c['status']=='PASS' for c in record['cases'])
        record['failed'] = sum(c['status']=='FAIL' for c in record['cases'])
    except Exception as exc:
        record.update(status='FAIL', error_class=type(exc).__name__, error=str(exc)[:2000],
                      public_test_traceback=traceback.format_exc(limit=6))
    persist(args.output, {k:v for k,v in record.items() if not k.startswith('_')})
    print(json.dumps(dict(status=record['status'], passed=record.get('passed'), failed=record.get('failed'),
                          output=str(args.output)), ensure_ascii=False))
    return 0 if record['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
