"""ROOT-ONLY fixed public LLM ABBA. Default prints plan; no IO to services.

Requires root's fresh proof that board UI/business writers are closed, then
checks host idle and the unique existing runner before/after EVERY request.
No TTS owner is constructed. GPU admission is retained. Never run in this chat.
"""
import argparse
import ast
import copy
from dataclasses import dataclass
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

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build_candidate import AURA, PROJECT, SOURCES

QUESTION = '请只给结果：六乘九等于多少？'
METRICS = frozenset({'prompt_eval_count','prompt_eval_cached_count','eval_count','load_duration_ms',
    'prompt_eval_duration_ms','eval_duration_ms','total_duration_ms','first_packet_ms','first_content_ms',
    'first_json_closed_ms','backend_done_ms','json_closed_to_done_ms','thinking_characters',
    'content_characters','trailing_whitespace_characters'})


class TrialError(RuntimeError): pass


def semantic_math(text):
    """Conservative public arithmetic whitelist; other valid prose = UNKNOWN."""
    compact = re.sub(r'[\s。！!，,：:；;]', '', text)
    if re.fullmatch(r'(?:(?:六乘九|6[乘×x*]9)(?:的)?(?:结果|答案)?)?(?:等于|结果是|结果为|答案是|答案为|是|为|=)?(?:54|五十四)', compact):
        return 'PASS'
    if re.search(r'(?:不是|不等于)(?:54|五十四)', compact):
        return 'FAIL'
    return 'UNKNOWN'


def abba(infer, guard, *, messages, candidate, validate_reply, decode_reply, cycles=1):
    if type(cycles) is not int or not 1 <= cycles <= 5:
        raise ValueError('invalid_cycle_count')
    immutable = copy.deepcopy(messages)
    rows = []
    for _ in range(cycles):
        for label in ('A', 'B', 'B', 'A'):
            guard()
            started = time.monotonic()
            row = {'trial_index':len(rows)+1,'arm':label,'complete_json':False,
                   'semantic_check':'NOT_RUN','error_code':'NONE'}
            try:
                # Exact same selected system/user messages in both arms.
                result = infer('json' if label == 'A' else candidate, copy.deepcopy(immutable))
                canonical = decode_reply(result['text'])
                reply = validate_reply(canonical, QUESTION)
                row.update(complete_json=True, semantic_check=semantic_math(reply.text),
                           reply_characters=len(reply.text),
                           metrics={key:value for key,value in result.get('metrics',{}).items()
                             if key in METRICS and type(value) in (int,float) and math.isfinite(value) and 0 <= value < 1e15})
            except TimeoutError:
                row['error_code'] = 'DEADLINE'
            except InterruptedError:
                row['error_code'] = 'CANCELLED'
            except Exception as exc:
                # All exceptions are mapped to a fixed code, no str(exc), no raw output.
                row['error_code'] = ('OUTPUT_TRUNCATED' if type(exc).__name__ == 'OutputTruncated'
                                     else 'INVALID_OR_FAILED_REPLY')
            row['llm_wall_ms'] = (time.monotonic()-started)*1000
            if messages != immutable:
                raise TrialError('PROMPT_MUTATED')
            guard()
            rows.append(row)
    return rows


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def fetch(url):
    request = urllib.request.Request(url, headers={'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=3) as response:
        raw = response.read(1024*1024+1)
    if len(raw) > 1024*1024: raise TrialError('METADATA_LIMIT')
    return json.loads(raw)


def selected_static_prompt(expected):
    profile = json.loads((AURA / 'config/character_profile.local.json').read_text(encoding='utf-8-sig'))
    prompt = profile['persona_full_prompt']
    digest = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    if digest != expected or digest != profile['persona_prompt_sha256']:
        raise TrialError('STATIC_PROMPT_PIN_MISMATCH')
    return prompt


def execute(args):
    if args.root_permit is None: raise TrialError('ROOT_PERMIT_REQUIRED')
    permit = json.loads(args.root_permit.read_text(encoding='utf-8-sig'))
    required = ('authorized_by_root','board_business_ui_closed','board_memory_writer_closed',
                'all_other_project_model_probes_stopped','preserve_53_of_66_layers_and_existing_fit',
                'model_request_body_logging_disabled')
    if any(permit.get(key) is not True for key in required): raise TrialError('ROOT_WINDOW_NOT_ESTABLISHED')
    issued = datetime.fromisoformat(permit['issued_utc'].replace('Z','+00:00'))
    if issued.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-issued).total_seconds() <= 120:
        raise TrialError('ROOT_PERMIT_NOT_FRESH')
    url = urlsplit(args.host_health_url)
    if url.scheme != 'http' or url.hostname not in ('192.168.50.1','127.0.0.1') or url.port != 8797 or url.path != '/health' or url.query or url.username:
        raise TrialError('HEALTH_ENDPOINT_REJECTED')
    if permit.get('model') != 'aura-qwen3.8-27b-abliterated:iq4_xs': raise TrialError('MODEL_REJECTED')
    for target, expected in SOURCES.items():
        # The board memory source is reference-only and MUST NOT be required
        # to match a later generation/diagnostic fix. Never copy it to live.
        if target == 'board/runtime/board_memory_policy.py': continue
        if hashlib.sha256((AURA/target).read_bytes()).hexdigest() != expected:
            raise TrialError('LIVE_PUBLIC_SOURCE_CHANGED')
    dependencies = json.loads((ROOT/'BENCH_DEPENDENCY_PINS.json').read_text(encoding='utf-8'))
    for target, expected in dependencies.items():
        if hashlib.sha256((AURA/target).read_bytes()).hexdigest() != expected:
            raise TrialError('BENCH_DEPENDENCY_CHANGED')
    prompt = selected_static_prompt(permit['expected_static_prompt_sha256'])
    sys.path.insert(0, str(AURA))
    import common
    import tools
    contract = load('common.inference_output_contract', ROOT/'candidate/inference_output_contract.py')
    wire = load('common.model_inference_wire', ROOT/'after/common/model_inference_wire.py')
    candidate_host = load('research_benchmark_host', ROOT/'after/tools/model_inference_host.py')
    native = load('research_native_metadata_only', AURA/'tools/native_grammar.py')
    from common.gpu_coordination import GpuPolicy, GpuCoordinator, NvidiaMemoryProbe, OllamaResidencyProbe
    validator_path = ROOT.parents[2]/'response_latency/streaming_candidate/after/board/runtime/board_dialogue.py'
    if hashlib.sha256(validator_path.read_bytes()).hexdigest() != 'bce1f21962d083275d9e8a966f244d8c227d0d62e9a30314767453d04c05b475':
        raise TrialError('REPLY_VALIDATOR_PIN_CHANGED')
    validate_model_reply = load('research_abba_reply_validator',validator_path).validate_model_reply

    source = ast.parse((AURA/'tools/dialogue_host_ollama.py').read_text(encoding='utf-8'))
    node = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'chat_body')
    legacy = types.ModuleType('tools.dialogue_host_ollama')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'public_seeded_chat_body', 'exec'),legacy.__dict__)
    original = legacy.chat_body
    def seeded(*a, **kw):
        body = original(*a, **kw)
        body['options']['seed'] = args.seed  # Test-process-only; no production seed/default edit.
        return body
    legacy.chat_body = seeded
    sys.modules['tools.dialogue_host_ollama'] = legacy

    if args.family == 'compact_schema':
        adapter_module = load('research_benchmark_adapter', ROOT/'candidate/compact_request_adapter.py')
        prompt = adapter_module.CompactRequestAdapter(object(), system_prompt=prompt,
            capabilities={'format_contract_version':1,'output_formats':list(contract.FORMATS)}).translated_prompt
        candidate = 'dialogue_abc_v1'
        decoder = contract.canonicalize_compact
    else:
        candidate, decoder = 'dialogue_schema_v1', lambda text:text
    messages = [{'role':'system','content':prompt},{'role':'user','content':QUESTION}]
    policy = GpuPolicy.from_dict(json.loads((AURA/'config/gpu_runtime.local.json').read_text(encoding='utf-8-sig')))
    gpu = GpuCoordinator(policy, NvidiaMemoryProbe(), llm_residency=OllamaResidencyProbe('http://127.0.0.1:11435',permit['model']))
    # Deliberately do not call LocalModelBackend.__init__: it would construct
    # another logical TTS owner. llm() only requires model, URL and GPU policy.
    backend = object.__new__(candidate_host.LocalModelBackend)
    backend.model, backend.ollama_host, backend.gpu = permit['model'], 'http://127.0.0.1:11435', gpu
    fingerprint = None
    def guard():
        nonlocal fingerprint
        health = fetch(args.host_health_url)
        if (health.get('role') != 'model_inference_only' or health.get('active') is not False
                or health.get('pending') != 0 or health.get('ok') is not True):
            raise TrialError('MODEL_HOST_NOT_IDLE')
        runner = native._discover(time.monotonic()+5)
        if runner['pid'] != permit.get('expected_runner_pid'):
            raise TrialError('RUNNER_CHANGED')
        storage = json.loads((AURA/'config/model_storage.local.json').read_text(encoding='utf-8-sig'))
        expected_blob = (Path(storage['ollama_directory'])/'blobs').resolve()
        if Path(runner['model_path']).resolve().parent != expected_blob:
            raise TrialError('EXTERNAL_MODEL_PATH_REJECTED')
        models = fetch('http://127.0.0.1:11435/api/ps').get('models',[])
        selected = [row for row in models if row.get('name') == permit['model'] or row.get('model') == permit['model']]
        if len(selected) != 1 or selected[0].get('context_length') != 2048:
            raise TrialError('RESIDENT_MODEL_OR_CONTEXT_REJECTED')
        row = selected[0]
        current = (row.get('size'), row.get('size_vram'), row.get('context_length'))
        if fingerprint is None: fingerprint = current
        elif current != fingerprint: raise TrialError('RESIDENCY_PARAMETERS_CHANGED')
    count = 0
    def infer(mode, selected_messages):
        nonlocal count
        count += 1
        payload = wire.validate_request('llm', dict(protocol_version=1,request_id='public-abba-'+str(count),
            board_boot_id='benchmark-only',session_id='benchmark-only',generation=count,
            budget_ms=args.deadline_ms,task='dialogue',messages=selected_messages,
            options={'think':False,'num_predict':120,'output_format':mode}))
        return backend.llm(payload,deadline=time.monotonic()+args.deadline_ms/1000,cancelled=threading.Event())
    guard()
    # First pilot is EXACTLY FOUR complete generations: no extra warm-up,
    # cache flush, model load/unload or hidden matrix.
    warmup = []
    rows = abba(infer,guard,messages=messages,candidate=candidate,validate_reply=validate_model_reply,
                decode_reply=decoder,cycles=args.cycles)
    result = {'schema':'aura.first-wait.public-abba.v1','family':args.family,'seed':args.seed,
        'num_predict':120,'num_ctx':2048,'think':False,'temperature':.6,
        'same_prompt_seed_budget_across_A_B':True,'same_as_current_production_prompt':args.family=='canonical_schema',
        'synthetic_public_question_code':'MUL_6_9_RESULT_ONLY','warmups':warmup,'trials':rows,
        'existing_runner_pid_unchanged':True,'resident_size_bytes':fingerprint[0],'resident_vram_bytes':fingerprint[1],
        'root_window_assertions_required':True,'cross_process_atomic_model_lock_claimed':False,
        'tts_requests':0,'audio_playback':False,'raw_prompt_reply_or_pcm_saved_by_script':False,
        'scope':'LLM-only public same-prompt experiment, not human or acoustic acceptance'}
    output_dir = ROOT/'benchmark_runs'; output_dir.mkdir(exist_ok=True)
    path = output_dir/('public_abba_'+uuid.uuid4().hex[:12]+'.json')
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return {'status':'ROOT_PUBLIC_ABBA_FINISHED','result_file':str(path),'trial_count':len(rows),
            'warmup_count':len(warmup),'all_complete':all(row['complete_json'] for row in rows),
            'all_semantic_checks_pass':all(row['semantic_check']=='PASS' for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--root-permit',type=Path)
    parser.add_argument('--family',choices=('canonical_schema','compact_schema'),default='canonical_schema')
    parser.add_argument('--cycles',type=int,choices=range(1,6),default=1)
    parser.add_argument('--seed',type=int,default=8701)
    parser.add_argument('--deadline-ms',type=int,default=30000)
    parser.add_argument('--host-health-url',default='http://192.168.50.1:8797/health')
    args = parser.parse_args()
    if not 1000 <= args.deadline_ms <= 300000: raise TrialError('INVALID_DEADLINE')
    if not args.execute:
        print(json.dumps({'status':'PLAN_ONLY_NO_SERVICES_OR_MODELS_CONTACTED','family':args.family,
            'order':'ABBA','warmups':0,'trials':4*args.cycles,'seed':args.seed,'num_predict':120,
            'same_prompt_across_A_B':True,'root_permit_required':True,'no_tts_playback_or_raw_text_logging':True}))
        return
    print(json.dumps(execute(args)))


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        code = str(exc) if isinstance(exc,TrialError) and re.fullmatch('[A-Z_]+',str(exc)) else 'BENCHMARK_ABORTED'
        print(json.dumps({'status':'ABORTED','error_code':code,'no_exception_details_or_model_text_printed':True}))
        raise SystemExit(1)
