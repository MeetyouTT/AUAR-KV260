"""ROOT-ONLY isolated Windows pilot. Default is dry; never starts TTS or a service.

ABBA: four ABC/AB requests. D01: one exact canonical/think=True request.
These are separate invocations, with separate fresh root permits/results.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import threading
import time
import types
import urllib.request
from urllib.parse import urlsplit
import uuid

HERE = Path(__file__).resolve().parent
AURA = HERE.parents[4]/'aura'
MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
PINS_SHA = '2e967f5dece97e888d5da7e32781d759c343ccfc49c10618e01384e1990d24a7'
D01_QUESTION = '17乘23等于多少？请给出结果。'
FLAGS = ('authorized_by_root', 'board_business_ui_closed', 'board_memory_writer_closed',
    'all_other_project_model_probes_stopped', 'preserve_53_of_66_layers_and_existing_fit',
    'model_request_body_logging_disabled')
ERRORS = frozenset(('ROOT_PERMIT_REQUIRED', 'ROOT_WINDOW_NOT_ESTABLISHED',
    'ROOT_PERMIT_NOT_FRESH', 'MODEL_REJECTED', 'HEALTH_ENDPOINT_REJECTED',
    'SOURCE_PIN_CHANGED', 'STATIC_PROMPT_PIN_MISMATCH', 'MODEL_HOST_NOT_IDLE',
    'RUNNER_CHANGED', 'EXTERNAL_MODEL_PATH_REJECTED', 'RESIDENT_MODEL_OR_CONTEXT_REJECTED',
    'RESIDENCY_PARAMETERS_CHANGED', 'METADATA_LIMIT', 'ROOT_GUARD_FAILED',
    'DEADLINE', 'CANCELLED', 'OUTPUT_TRUNCATED', 'BACKEND_HTTP_REJECTED',
    'INVALID_OR_FAILED_REPLY', 'SEMANTIC_UNVERIFIED', 'PROBE_FAILED'))
METRICS = frozenset(('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count',
    'load_duration_ms', 'prompt_eval_duration_ms', 'eval_duration_ms', 'total_duration_ms',
    'first_packet_ms', 'first_content_ms', 'first_json_closed_ms', 'backend_done_ms',
    'json_closed_to_done_ms', 'thinking_characters', 'content_characters',
    'trailing_whitespace_characters'))


class TrialError(RuntimeError):
    def __init__(self, code):
        self.code = code if code in ERRORS else 'PROBE_FAILED'
        super().__init__(self.code)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise TrialError('PROBE_FAILED')
        value[key] = item
    return value


def read_json(path, limit=65536):
    raw = path.read_bytes()
    if len(raw) > limit: raise TrialError('METADATA_LIMIT')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)


def safe_metrics(value):
    return {key:item for key,item in value.items() if key in METRICS
        and type(item) in (int,float) and math.isfinite(item) and 0 <= item < 1e15}


def validate_permit(permit, *, now=None):
    if not isinstance(permit, dict) or any(permit.get(k) is not True for k in FLAGS):
        raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    try:
        issued = datetime.fromisoformat(permit['issued_utc'].replace('Z', '+00:00'))
    except (KeyError, AttributeError, ValueError, TypeError):
        raise TrialError('ROOT_PERMIT_NOT_FRESH') from None
    now = now or datetime.now(timezone.utc)
    if issued.tzinfo is None or not 0 <= (now-issued).total_seconds() <= 120:
        raise TrialError('ROOT_PERMIT_NOT_FRESH')
    if permit.get('model') != MODEL: raise TrialError('MODEL_REJECTED')
    if type(permit.get('expected_runner_pid')) is not int or permit['expected_runner_pid'] <= 0:
        raise TrialError('RUNNER_CHANGED')
    evidence = permit.get('evidence', {})
    if not isinstance(evidence, dict): raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    unit = evidence.get('unit', {})
    if not isinstance(unit, dict): raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    if (unit.get('MainPID') != '0' or unit.get('ActiveState') != 'inactive' or unit.get('Job') != ''
            or unit.get('SendSIGKILL') != 'no' or unit.get('TimeoutStopUSec') != 'infinity'
            or evidence.get('writer_lock_observed_free') is not True
            or not re.fullmatch(r'[0-9a-f]{64}', evidence.get('startup_sha256', ''))
            or not re.fullmatch(r'[0-9a-f-]{36}', evidence.get('board_boot_id', ''))):
        raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    return permit


def verified_sources():
    pins_path = HERE/'ROOT_PROBE_PINS.json'
    if sha(pins_path) != PINS_SHA: raise TrialError('SOURCE_PIN_CHANGED')
    pins = read_json(pins_path)
    for relative, digest in pins['live_sources'].items():
        if sha(AURA/relative) != digest: raise TrialError('SOURCE_PIN_CHANGED')
    if sha(HERE/'SOURCE_MANIFEST.json') != pins['candidate_manifest_sha256']:
        raise TrialError('SOURCE_PIN_CHANGED')
    for relative, digest in pins['candidate_sources'].items():
        if sha(HERE/'after'/relative) != digest: raise TrialError('SOURCE_PIN_CHANGED')
    for name in ('legacy_guard_runner', 'validator'):
        if sha(Path(pins[name]['path'])) != pins[name]['sha256']:
            raise TrialError('SOURCE_PIN_CHANGED')
    if sha(HERE/'public_abba.py') != pins['public_core_sha256']:
        raise TrialError('SOURCE_PIN_CHANGED')
    return pins


def reuse_guard_helpers(pins):
    """Reuse exact pinned pure helper AST, not old execute()/old source pins."""
    source = ast.parse(Path(pins['legacy_guard_runner']['path']).read_bytes())
    names = {'NoRedirect', 'fetch', 'selected_static_prompt'}
    nodes = [n for n in source.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    if {n.name for n in nodes} != names: raise TrialError('SOURCE_PIN_CHANGED')
    namespace = dict(urllib=urllib, json=json, AURA=AURA, hashlib=hashlib, TrialError=TrialError)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pinned_root_guard_helpers', 'exec'), namespace)
    return namespace['fetch'], namespace['selected_static_prompt']


def seeded_chat_body(seed=8701):
    tree = ast.parse((AURA/'tools/dialogue_host_ollama.py').read_bytes())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'chat_body')
    module = types.ModuleType('tools.dialogue_host_ollama')
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'public_seeded_chat_body', 'exec'), module.__dict__)
    original = module.chat_body
    def seeded(*args, **kwargs):
        body = original(*args, **kwargs)
        body['options']['seed'] = seed
        return body
    module.chat_body = seeded
    sys.modules[module.__name__] = module  # Isolated probe process only.


def prepare_backend(pins, experiment, permit):
    sys.path.insert(0, str(AURA))
    import common
    import tools
    import board.runtime
    base = HERE/'after' if experiment == 'abba' else HERE/'before'
    contract = load('common.inference_output_contract', base/'common/inference_output_contract.py')
    wire = load('common.model_inference_wire', AURA/'common/model_inference_wire.py')
    if experiment == 'abba':
        load('board.runtime.compact_request_adapter', HERE/'after/board/runtime/compact_request_adapter.py')
    host = load('root_isolated_probe_host', base/'tools/model_inference_host.py')
    validator = load('board.runtime.board_dialogue', Path(pins['validator']['path'])).validate_model_reply
    native = load('root_metadata_runner', AURA/'tools/native_grammar.py')
    from common.gpu_coordination import GpuPolicy, GpuCoordinator, NvidiaMemoryProbe, OllamaResidencyProbe
    policy = GpuPolicy.from_dict(read_json(AURA/'config/gpu_runtime.local.json'))
    if policy.mode not in ('adaptive', 'serial'): raise TrialError('SOURCE_PIN_CHANGED')
    gpu = GpuCoordinator(policy, NvidiaMemoryProbe(),
        llm_residency=OllamaResidencyProbe('http://127.0.0.1:11435', MODEL))
    # Never call constructor/from_config: no second logical or actual TTS owner.
    backend = object.__new__(host.LocalModelBackend)
    backend.model, backend.ollama_host, backend.gpu = MODEL, 'http://127.0.0.1:11435', gpu
    seeded_chat_body()
    return SimpleBundle(backend, host, contract, wire, validator, native)


class SimpleBundle:
    def __init__(self, backend, host, contract, wire, validator, native):
        self.backend, self.host, self.contract, self.wire = backend, host, contract, wire
        self.validator, self.native = validator, native


def owner_guard(fetch, discover, health_url, permit, expected_blob, observations):
    fingerprint = None
    def guard():
        nonlocal fingerprint
        health = fetch(health_url)
        backend = health.get('backend', {})
        if (health.get('role') != 'model_inference_only' or health.get('active') is not False
                or type(health.get('pending')) is not int or health['pending'] != 0 or health.get('ok') is not True
                or health.get('request_logging') is not False
                or backend.get('model') != MODEL or backend.get('tts') != 'omnivoice'
                or backend.get('num_step') != 16 or backend.get('tts_ready') is not True):
            raise TrialError('MODEL_HOST_NOT_IDLE')
        runner = discover(time.monotonic()+5)
        if runner['pid'] != permit['expected_runner_pid']: raise TrialError('RUNNER_CHANGED')
        if Path(runner['model_path']).resolve().parent != expected_blob:
            raise TrialError('EXTERNAL_MODEL_PATH_REJECTED')
        models = fetch('http://127.0.0.1:11435/api/ps').get('models', [])
        selected = [r for r in models if r.get('name') == MODEL or r.get('model') == MODEL]
        if len(selected) != 1 or selected[0].get('context_length') != 2048:
            raise TrialError('RESIDENT_MODEL_OR_CONTEXT_REJECTED')
        row = selected[0]
        current = (row.get('size'), row.get('size_vram'), row.get('context_length'))
        if any(type(n) is not int or n <= 0 for n in current):
            raise TrialError('RESIDENT_MODEL_OR_CONTEXT_REJECTED')
        if fingerprint is None: fingerprint = current
        elif fingerprint != current: raise TrialError('RESIDENCY_PARAMETERS_CHANGED')
        observations.append(dict(runner_pid=runner['pid'], resident_size_bytes=current[0],
            resident_vram_bytes=current[1], context_length=current[2], host_idle=True, tts16_ready=True))
    return guard


@contextmanager
def observe_d01(bundle, metadata):
    """Numerical packet observation only; restore HTTPResponse even on failure."""
    original = bundle.host.http.client.HTTPResponse
    observer = bundle.contract.StreamObservation(time.monotonic())
    class Response(original):
        def __init__(self, sock, *args, **kwargs):
            self._record_d01 = isinstance(sock, bundle.host._ResponseSocket)
            super().__init__(sock, *args, **kwargs)
        def begin(self):
            super().begin()
            if self._record_d01 and type(self.status) is int and 100 <= self.status <= 599:
                metadata['http_status'] = self.status
        def readline(self, *args, **kwargs):
            raw = super().readline(*args, **kwargs)
            if raw and self._record_d01:
                try: packet = json.loads(raw)
                except (ValueError, TypeError): return raw
                if isinstance(packet, dict):
                    observer.packet(packet, time.monotonic())
                    if packet.get('done') is True:
                        metadata['backend_done'] = True
                        metadata['ended_by_length'] = packet.get('done_reason') == 'length'
                        for key in ('prompt_eval_count', 'eval_count'):
                            value = packet.get(key)
                            if type(value) is int and value >= 0: metadata[key] = value
                        for key in ('load_duration', 'prompt_eval_duration', 'eval_duration', 'total_duration'):
                            value = packet.get(key)
                            if type(value) in (int,float) and math.isfinite(value) and value >= 0:
                                metadata[key+'_ms'] = value/1e6
                        try: metadata.update(observer.finish(packet))
                        except bundle.contract.OutputTruncated: pass
            return raw
    bundle.host.http.client.HTTPResponse = Response
    try: yield metadata
    finally:
        bundle.host.http.client.HTTPResponse = original
        metadata.update(safe_metrics(observer.values))


def d01_semantics(text):
    compact = re.sub(r'[\s。！!，,：:；;]', '', text)
    return bool(re.fullmatch(r'(?:(?:17(?:乘以|乘|×|\*)23|十七乘(?:以)?二十三)'
        r'(?:的)?(?:结果|答案)?)?(?:等于|结果是|结果为|答案是|答案为|是|为|=)?(?:391|三百九十一)', compact))


def run_d01(bundle, prompt, infer):
    row = dict(case_id='D01', think_requested=True, wire_format='json', reply_contract='canonical',
        complete_json=False, semantic_check='NOT_RUN', error_code='NONE', request_count=1)
    metadata = {}
    started = time.monotonic()
    try:
        # Exact production behavior: think bypasses compact; canonical prompt
        # and no output_format. Never relabel AB/ABC as a supported think wire.
        with observe_d01(bundle, metadata):
            result = infer(None, [dict(role='system', content=prompt),
                                 dict(role='user', content=D01_QUESTION)], think=True)
        if metadata.get('ended_by_length'): raise bundle.contract.OutputTruncated('backend_output_truncated')
        reply = bundle.validator(result['text'], D01_QUESTION)
        row.update(complete_json=True, semantic_check='PASS' if d01_semantics(reply.text) else 'UNKNOWN',
                   reply_characters=len(reply.text), reply_sha256=hashlib.sha256(reply.text.encode()).hexdigest())
        metadata.update(safe_metrics(result.get('metrics', {})))
    except TimeoutError: row['error_code'] = 'DEADLINE'
    except InterruptedError: row['error_code'] = 'CANCELLED'
    except bundle.contract.OutputTruncated: row['error_code'] = 'OUTPUT_TRUNCATED'
    except Exception:
        row['error_code'] = 'BACKEND_HTTP_REJECTED' if metadata.get('http_status',200) >= 400 else 'INVALID_OR_FAILED_REPLY'
    finally:
        row.update(llm_wall_ms=(time.monotonic()-started)*1000, metrics=safe_metrics(metadata),
            http_status=metadata.get('http_status'), backend_done=metadata.get('backend_done',False),
            think_request_accepted=metadata.get('http_status') == 200,
            thinking_output_observed=metadata.get('thinking_characters',0) > 0,
            no_hidden_retry=True)
    return row


def plan(experiment):
    return dict(status='DRY_NO_MODELS_SERVICES_OR_DEVICES_CONTACTED', experiment=experiment,
        requests=4 if experiment=='abba' else 1, deadline_ms=30000, seed=8701,
        num_ctx=2048, num_predict=120, temperature=.6,
        think=experiment=='d01', order=['ABC','AB','AB','ABC'] if experiment=='abba' else ['D01'],
        reply_contract='ABC_vs_AB' if experiment=='abba' else 'canonical',
        wire_format='explicit_compact' if experiment=='abba' else 'json',
        fresh_root_permit_required=True, tts_instances_constructed=0,
        services_started_or_stopped=False, production_sources_modified=False)


def execute(args):
    if args.root_permit is None: raise TrialError('ROOT_PERMIT_REQUIRED')
    permit = validate_permit(read_json(args.root_permit))
    target = urlsplit(args.host_health_url)
    if (target.scheme != 'http' or target.hostname not in ('127.0.0.1','192.168.50.1')
            or target.port != 8797 or target.path != '/health' or target.query
            or target.fragment or target.username or target.password):
        raise TrialError('HEALTH_ENDPOINT_REJECTED')
    pins = verified_sources()
    if permit['evidence']['startup_sha256'] != pins['baseline_startup_sha256']:
        raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    fetch, read_prompt = reuse_guard_helpers(pins)
    if permit.get('expected_static_prompt_sha256') != pins['static_prompt_sha256']:
        raise TrialError('STATIC_PROMPT_PIN_MISMATCH')
    prompt = read_prompt(permit['expected_static_prompt_sha256'])
    bundle = prepare_backend(pins, args.experiment, permit)
    storage = read_json(AURA/'config/model_storage.local.json')
    expected_blob = (Path(storage['ollama_directory'])/'blobs').resolve()
    observations = []
    guard = owner_guard(fetch, bundle.native._discover, args.host_health_url, permit, expected_blob, observations)
    result = dict(schema='aura.root-public-compact-or-think-probe.v1', experiment=args.experiment,
        seed=8701, num_ctx=2048, num_predict=120, temperature=.6, deadline_ms=30000,
        tts_requests=0, tts_instances_constructed=0, microphone_opened=False, audio_played=False,
        real_store_accessed=False, production_modified=False, raw_prompt_reply_or_pcm_archived=False,
        cross_process_atomic_model_lock_claimed=False, root_exclusive_window_required=True,
        startup_sha256=permit['evidence']['startup_sha256'], root_permit_sha256=sha(args.root_permit),
        static_prompt_sha256=pins['static_prompt_sha256'], source_pins_sha256=PINS_SHA,
        guard_observations=observations, error_code='NONE', backend_finally_cleanup_retained=True)
    counter, speech = 0, []
    def infer(mode, messages, *, think=False):
        nonlocal counter
        counter += 1
        options = dict(think=think, num_predict=120)
        if mode is not None: options['output_format'] = mode
        payload = bundle.wire.validate_request('llm', dict(protocol_version=1,
            request_id='public-probe-'+str(counter), board_boot_id='benchmark-only',
            session_id='benchmark-only', generation=counter, budget_ms=30000,
            task='dialogue', messages=messages, options=options))
        cancelled = threading.Event()
        try:
            value = bundle.backend.llm(payload, deadline=time.monotonic()+30, cancelled=cancelled)
            if mode is not None:
                canonical = bundle.contract.canonicalize_compact(value['text'], mode=mode)
                reply = bundle.validator(canonical, messages[-1]['content'])
                speech.append(dict(index=counter, mode=mode, chars=len(reply.text),
                    sha256=hashlib.sha256(reply.text.encode()).hexdigest()))
            return value
        finally:
            cancelled.set()  # The original bounded backend already closed its socket/GPU lease.
    try:
        guard()
        if args.experiment == 'abba':
            core = load('root_public_twofield_core', HERE/'public_abba.py')
            result['study'] = core.run_public_abba(infer, guard, system_prompt=prompt)
            result['speech_comparisons'] = speech
            result['all_cross_arm_speech_identical'] = len(speech)==4 and len({r['sha256'] for r in speech})==1
        else:
            result['study'] = run_d01(bundle, prompt, infer)
        if args.experiment == 'abba':
            result['checks_passed'] = result['study']['all_complete'] and result['study']['all_semantic_pass']
            if not result['checks_passed']:
                result['error_code'] = next((r['error_code'] for r in result['study']['trials']
                    if r['error_code'] != 'NONE'), 'SEMANTIC_UNVERIFIED')
        else:
            row = result['study']
            result['checks_passed'] = bool(row['complete_json'] and row['semantic_check']=='PASS'
                and row['backend_done'] and row['think_request_accepted'])
            if not result['checks_passed']:
                result['error_code'] = row['error_code'] if row['error_code'] != 'NONE' else 'SEMANTIC_UNVERIFIED'
        result['status'] = 'FINISHED_NO_GAIN_CLAIM'
    except BaseException as exc:
        result['status'] = 'ABORTED_NO_GAIN_CLAIM'
        result['error_code'] = exc.code if isinstance(exc,TrialError) else 'CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'PROBE_FAILED'
    finally:
        result['model_requests_attempted'] = counter
        try: guard(); result['post_guard_passed'] = True
        except BaseException: result['post_guard_passed'] = False; result['error_code'] = 'ROOT_GUARD_FAILED'
    output_dir = HERE/'root_benchmark_runs'
    output_dir.mkdir(exist_ok=True)
    path = output_dir/(args.experiment+'_'+uuid.uuid4().hex[:12]+'.json')
    path.write_bytes((json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
    return dict(status=result['status'], experiment=args.experiment, result_file=str(path),
        model_requests_attempted=counter, post_guard_passed=result['post_guard_passed'],
        checks_passed=result.get('checks_passed',False), error_code=result['error_code'])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', choices=('abba','d01'), default='abba')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--root-permit', type=Path)
    parser.add_argument('--host-health-url', default='http://127.0.0.1:8797/health')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(plan(args.experiment),ensure_ascii=False)); return 0
    try:
        value = execute(args)
        print(json.dumps(value,ensure_ascii=False))
        return 0 if value['status'].startswith('FINISHED') and value['post_guard_passed'] and value['checks_passed'] else 1
    except BaseException as exc:
        code = exc.code if isinstance(exc,TrialError) else 'CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'PROBE_FAILED'
        print(json.dumps(dict(status='ABORTED',error_code=code,no_raw_details=True)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
