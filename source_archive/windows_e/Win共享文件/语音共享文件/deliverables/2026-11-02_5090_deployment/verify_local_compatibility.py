"""Bounded public compatibility probes for an already READY local model owner.

Never starts/stops a service, unloads a model, contacts the board, opens business
data, plays audio, or records prompt/response content. Evidence is metadata only.
"""
import datetime
import hashlib
import http.client
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
HOST = ROOT / 'deliverables/2026-10-30_board_owner/integration/production_model_host'
sys.path[:0] = [str(ROOT / 'aura'), str(HOST), str(ROOT / 'deliverables/2026-10-18_board_dialogue')]
from common.model_inference_wire import Owner, validate_response
from common.inference_output_contract import canonicalize_compact
from measure_models import gpu
import manage
from project_ollama import inspect_ownership


def read(path):
    return json.loads(Path(path).read_bytes())


def request(port, path, body=None, timeout=130):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('GET' if body is None else 'POST', path,
            None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8'),
            {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        if response.status != 200 or len(raw) > 4 * 1024 * 1024:
            raise RuntimeError('Bounded public compatibility HTTP request failed')
        return json.loads(raw)
    finally:
        connection.close()


def main():
    state = read(OUT / 'STATUS.json')
    ready = read(OUT / 'READY_LOCAL.json')
    if (state.get('complete') is not True
            or state.get('phase') != 'READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING'
            or ready.get('endpoint') != 'http://127.0.0.1:8797'):
        raise RuntimeError('Require the completed loopback-only deployment')
    owned = manage.status()
    if owned.get('status') != 'READY' or owned.get('owner_alive') is not True:
        raise RuntimeError('Current unique local owner is not READY')
    before = gpu()
    daemon = inspect_ownership()
    policy = read(ROOT / 'aura/config/ollama_runtime.local.json')
    version = request(11435, '/api/version', timeout=5)['version']
    if version != policy['ollama_version']:
        raise RuntimeError('Actual daemon version differs from its exact binding')
    source = '[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);'
    source += "$rows=@(Get-CimInstance Win32_Process -Filter 'ParentProcessId=" + str(daemon['pid'])
    source += "' | Where-Object {$_.Name -ieq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine);"
    source += 'ConvertTo-Json -InputObject $rows -Depth 4 -Compress'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', source],
        capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Cannot inspect current project-owned runner')
    rows = json.loads(result.stdout.decode('utf-8-sig'))
    if len(rows) != 1:
        raise RuntimeError('Require exactly one project-owned runner')
    runner = rows[0]
    port = re.search(r'(?:^|\s)--port\s+(\d+)(?:\s|$)', runner['CommandLine'])
    if port is None or not 1 <= int(port[1]) <= 65535:
        raise RuntimeError('Cannot prove current runner endpoint')
    props = request(int(port[1]), '/props', timeout=5)
    show = request(11435, '/api/show', {'model': state['model']}, timeout=5)
    model_path = re.search(r'^FROM\s+(.+)$', show['modelfile'], re.M)
    expected = Path(model_path[1].strip().strip('"')).resolve() if model_path else None
    external_blobs = (Path('D:/AIModels/Ollama-AURA') / 'blobs').resolve()
    if (expected is None or expected.parent != external_blobs
            or Path(props['model_path']).resolve() != expected
            or props.get('total_slots') != 1
            or props['default_generation_settings']['n_ctx'] != 2048):
        raise RuntimeError('Actual original model path/context/slot binding differs')
    residency = request(11435, '/api/ps', timeout=5)['models']
    if (len(residency) != 1 or residency[0]['name'] != state['model']
            or residency[0].get('size_vram', 0) <= 0
            or residency[0].get('context_length') != 2048):
        raise RuntimeError('Fixed GPU model residency differs')
    probe_owner = dict(board_boot_id='public-5090-compatibility',
        session_id='public-' + uuid.uuid4().hex, generation=1)
    probes = []
    for mode in ('dialogue_schema_v1', 'dialogue_abc_v1'):
        fields = ('reply_text', 'emotion', 'avatar_action') if mode == 'dialogue_schema_v1' else ('a', 'b', 'c')
        payload = dict(protocol_version=1, request_id='public-format-' + uuid.uuid4().hex,
            budget_ms=120000, task='dialogue', **probe_owner,
            options=dict(output_format=mode, think=False, num_predict=96),
            messages=[{'role': 'system', 'content': '这是公开部署验证。请只返回一个JSON对象，字段为'
                + '/'.join(fields) + '。回复用一句简短中文，情绪为friendly，动作为空字符串。'},
                {'role': 'user', 'content': '请简短说你已经准备好了。'}])
        started = time.monotonic()
        response = request(8797, '/v1/inference/llm', payload)
        validate_response(response, Owner.from_dict(payload), 'llm')
        if response.get('ok') is not True:
            raise RuntimeError('Public structured original-model response rejected')
        text = response['result']['text']
        decoded = json.loads(canonicalize_compact(text) if mode == 'dialogue_abc_v1' else text)
        if (set(decoded) != {'reply_text', 'emotion', 'avatar_action'}
                or not isinstance(decoded['reply_text'], str) or not decoded['reply_text'].strip()
                or decoded['emotion'] not in {'neutral', 'friendly', 'happy', 'sad'}
                or decoded['avatar_action'] != ''):
            raise RuntimeError('Public structured original-model content contract differs')
        probes.append(dict(mode=mode, passed=True, seconds=round(time.monotonic()-started, 3),
            response_characters=len(text), metrics=response['result'].get('metrics', {})))
        text = decoded = response = payload = None
    final = manage.status()
    if final.get('owner') != owned['owner'] or final.get('status') != 'READY':
        raise RuntimeError('Local model owner changed during compatibility probes')
    preflight = request(8797, '/v1/inference/preflight', timeout=5)
    if (preflight.get('tts_ready') is not True
            or preflight.get('tts_ownership', {}).get('owned_workers') != 1
            or preflight.get('tts_ownership', {}).get('external_workers') != 0
            or any(preflight.get('admission', {}).get(kind, {}).get('can_admit_now') is not True
                for kind in ('llm', 'tts'))):
        raise RuntimeError('Post-probe same-owner coexistence is not ready')
    report = dict(passed=True, completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='already-ready local owner, original 27B public output contracts and same resident OmniVoice16',
        endpoint=ready['endpoint'], model=state['model'], version=version, owner=owned['owner'],
        session_id=owned['session_id'], daemon_owner=daemon, runner=runner,
        runner_props=dict(build_info=props.get('build_info'), model_path=props['model_path'],
            total_slots=props['total_slots'], context_length=props['default_generation_settings']['n_ctx'],
            template_matches_ollama_show=props.get('chat_template') == show.get('template')),
        runner_executable_sha256=hashlib.sha256(Path(runner['ExecutablePath']).read_bytes()).hexdigest(),
        residency=residency, gpu_before=before, gpu_after=gpu(), public_format_probes=probes,
        preflight=preflight, business_database_opened=False, board_accessed=False,
        prompts_or_responses_archived=False, audio_played=False, services_started_or_stopped=False)
    path = OUT / 'local_compatibility_04013.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    print(json.dumps(dict(passed=True, evidence=str(path), owner=owned['owner'],
        version=version, runner_build=props.get('build_info'), gpu_after=report['gpu_after'], probes=probes)))


if __name__ == '__main__':
    main()
