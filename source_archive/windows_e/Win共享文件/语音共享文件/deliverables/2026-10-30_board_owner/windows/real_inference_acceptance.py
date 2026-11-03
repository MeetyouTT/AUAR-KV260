"""Explicit public-text, loopback-only model acceptance; metadata evidence only.

Never stops a pre-existing process/model, changes admission thresholds, accesses
business stores, records audio/text results, opens a microphone or plays audio.
Candidate TTS children are owned and closed at the end of each independent case.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
AURA = PROJECT / 'aura'
sys.path.insert(0, str(AURA))
from common.model_inference_wire import Owner, decode_audio, validate_response
from tools.model_inference_host import InferenceHost, LocalModelBackend, make_server

VOICE_PYTHON = Path(r'C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe')


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(command, timeout=5):
    result = subprocess.run(command, capture_output=True, timeout=timeout,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('metadata_command_failed')
    return result.stdout.decode('utf-8-sig', errors='replace')


def memory():
    values = run(['nvidia-smi', '--query-gpu=uuid,memory.total,memory.free,memory.used',
                  '--format=csv,noheader,nounits'], timeout=2).strip().split(',')
    identity, total, free, used = [value.strip() for value in values]
    return dict(utc=utc(), gpu_uuid=identity, total_mib=int(total), free_mib=int(free), used_mib=int(used))


def ps_api(port):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
    try:
        conn.request('GET', '/api/ps')
        response = conn.getresponse()
        raw = response.read(1024*1024+1)
        if response.status != 200 or len(raw) > 1024*1024:
            raise ValueError('ps_api')
        rows = json.loads(raw).get('models', [])
        return [{key: row[key] for key in ('name', 'digest', 'size', 'size_vram', 'context_length', 'expires_at') if key in row}
                for row in rows]
    finally:
        conn.close()


def processes():
    command = r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@(Get-CimInstance Win32_Process -Filter "Name = 'ollama.exe' OR Name = 'llama-server.exe' OR Name = 'python.exe'" | ForEach-Object {
 [pscustomobject]@{pid=[int]$_.ProcessId;ppid=[int]$_.ParentProcessId;name=$_.Name;exe=$_.ExecutablePath;created_utc=$_.CreationDate.ToUniversalTime().ToString('o');command=$_.CommandLine}
}) | ConvertTo-Json -Depth 3 -Compress'''
    raw = json.loads(run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command]))
    rows = raw if isinstance(raw, list) else [raw]
    values = []
    for row in rows:
        command = row.pop('command') or ''
        role = 'model_or_python'
        if 'omnivoice_voice.py' in command:
            role = 'candidate_ram_tts' if '--memory-only' in command else 'production_cached_tts'
        elif 'voice_entry.py' in command or 'board_model_host.py' in command:
            role = 'production_voice_host'
        elif 'real_inference_acceptance.py' in command:
            role = 'acceptance_driver'
        elif 'llama-server' in command or ' runner ' in command:
            role = 'llm_runner'
        row.update(role=role, command_sha256=hashlib.sha256(command.encode('utf-8')).hexdigest())
        if role == 'llm_runner':
            # Only public model runtime arguments, never arbitrary command data.
            fields = {}
            for flag in ('model', 'ctx-size', 'n-gpu-layers', 'parallel', 'fit', 'fit-target', 'port', 'host'):
                match = re.search(r'--' + flag + r'(?:=|\s+)("[^"]*"|\S+)', command)
                if match:
                    fields[flag] = match.group(1).strip('"')
            row['runner_args'] = fields
        values.append(row)
    return values


def snapshot():
    result = dict(utc=utc())
    for name, fn in (('memory', memory), ('processes', processes),
                     ('project_ollama_ps', lambda: ps_api(11435)),
                     ('default_ollama_ps', lambda: ps_api(11434))):
        try:
            result[name] = fn()
        except Exception as exc:
            result[name] = {'error': type(exc).__name__}
    return result


class Monitor:
    def __init__(self):
        self.stopped = threading.Event()
        self.samples = []
        self.errors = 0
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stopped.is_set() and len(self.samples) < 2048:
            try:
                self.samples.append(memory())
            except Exception:
                self.errors += 1
            self.stopped.wait(.25)

    def start(self):
        self.thread.start()

    def finish(self):
        self.stopped.set()
        self.thread.join(3)
        return dict(samples=self.samples, errors=self.errors,
                    minimum_free_mib=min((row['free_mib'] for row in self.samples), default=None),
                    maximum_used_mib=max((row['used_mib'] for row in self.samples), default=None))


def base_request(kind, generation=1):
    body = dict(protocol_version=1, request_id=uuid.uuid4().hex,
                board_boot_id='public-acceptance-20261030', session_id='public-model-tests',
                generation=generation, budget_ms=300000 if kind == 'llm' else 120000)
    if kind == 'llm':
        # This driver acts as the synthetic board and supplies the full prompt.
        # Neither the host nor the backend adds a persona/history/database.
        from tools.dialogue_host_ollama import fast_system_prompt
        from common.device_policy import MODEL_HINT
        body.update(task='dialogue', options={'think': False, 'num_predict': 120},
                    messages=[{'role': 'system', 'content': fast_system_prompt()+MODEL_HINT},
                              {'role': 'user', 'content': '二加二等于几？请简短回答。'}])
    else:
        body['text'] = '这是公开文本的内存语音测试。'
    return body


def invoke(server, kind, body):
    began = time.monotonic()
    conn = http.client.HTTPConnection(*server.server_address, timeout=body['budget_ms']/1000+5)
    try:
        conn.request('POST', '/v1/inference/'+kind, json.dumps(body, ensure_ascii=False).encode('utf-8'),
                     {'Content-Type': 'application/json'})
        response = conn.getresponse()
        raw = response.read(8*1024*1024+1)
        if len(raw) > 8*1024*1024:
            raise ValueError('response_limit')
        payload = json.loads(raw)
        validate_response(payload, Owner.from_dict(body), kind)
        meta = dict(http_status=response.status, elapsed_seconds=round(time.monotonic()-began, 3),
                    ownership_verified=True, cache_control=response.getheader('Cache-Control'))
        if not payload['ok']:
            meta.update(status='blocked' if payload['error']['code'] in ('gpu_busy', 'foreground_busy') else 'failed',
                        error=payload['error'])
            return meta, None
        result = payload['result']
        if kind == 'llm':
            text = result['text']
            parsed = json.loads(text)
            reply = parsed.get('reply_text')
            valid = (isinstance(reply, str) and bool(reply.strip()) and len(reply) <= 240
                     and parsed.get('emotion') in ('neutral', 'friendly', 'happy', 'sad')
                     and parsed.get('avatar_action') == '' and ('四' in reply or '4' in reply))
            meta.update(status='passed' if valid else 'failed', output_json_valid=True,
                        reply_fields_valid=valid, expected_public_answer_valid=valid,
                        output_bytes=len(text.encode('utf-8')),
                        output_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                        metrics=result.get('metrics', {}))
            return meta, reply if valid else None
        pcm, rate = decode_audio(result['audio'])
        import array
        values = array.array('h')
        values.frombytes(pcm)
        if sys.byteorder != 'little':
            values.byteswap()
        peak = max(abs(value) for value in values)
        valid = rate == 24000 and bool(pcm) and peak > 0
        meta.update(status='passed' if valid else 'failed', audio_in_ram=True,
                    encoding='pcm_s16le', sample_rate=rate, channels=1,
                    samples=len(pcm)//2, duration_seconds=round(len(pcm)/2/rate, 3),
                    pcm_bytes=len(pcm), pcm_sha256=hashlib.sha256(pcm).hexdigest(), peak_s16=peak)
        return meta, None
    finally:
        conn.close()


def candidate_case(label, kinds, voice_python):
    backend = LocalModelBackend.from_config(voice_python=voice_python)
    models = InferenceHost(backend)
    server = make_server(('127.0.0.1', 0), models)
    serving = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
    serving.start()
    monitor = Monitor()
    monitor.start()
    record = dict(label=label, started_utc=utc(), bind_address='127.0.0.1', ephemeral_port=server.server_address[1],
                  phases=[], before=snapshot())
    reply = None
    try:
        for index, kind in enumerate(kinds):
            body = base_request(kind, generation=index+1)
            if kind == 'tts' and reply is not None:
                body['text'] = reply
            phase = {'kind': kind, 'budget_ms': body['budget_ms'], 'before_memory': memory()}
            try:
                outcome, next_reply = invoke(server, kind, body)
                phase.update(outcome)
                if next_reply is not None:
                    reply = next_reply
            except Exception as exc:
                phase.update(status='failed', exception_type=type(exc).__name__)
            phase['after_memory'] = memory()
            phase['backend_health'] = backend.health()
            phase['runtime_after'] = snapshot()
            record['phases'].append(phase)
            print(json.dumps({'case': label, 'kind': kind, 'status': phase['status'],
                              'http_status': phase.get('http_status'), 'error': phase.get('error'),
                              'elapsed_seconds': phase.get('elapsed_seconds')}, separators=(',', ':')), flush=True)
            if phase['status'] != 'passed':
                break
        record['owned_voice_pid'] = backend.voice.process.pid if backend.voice.process is not None else None
        record['status'] = ('passed' if len(record['phases']) == len(kinds)
                            and all(row['status'] == 'passed' for row in record['phases'])
                            else 'blocked' if any(row['status'] == 'blocked' for row in record['phases']) else 'failed')
    finally:
        reply = None
        server.shutdown()
        server.server_close()
        models.close()  # Only this candidate's OwnedSpeechJob/child is closed.
        serving.join(1)
        record['monitor'] = monitor.finish()
        record['after_close'] = snapshot()
        record['finished_utc'] = utc()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voice-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('tts', 'llm', 'chain', 'all'), default='all')
    args = parser.parse_args()
    destination = args.output.resolve()
    if HERE.resolve() not in destination.parents:
        raise ValueError('Evidence must remain in the authorized windows delivery directory')
    if not args.voice_python.is_file():
        raise ValueError('Existing voice runtime unavailable')
    evidence = dict(schema_version=1, started_utc=utc(), phase=args.phase, public_synthetic_text_only=True,
                    production_services_restarted=False, models_unloaded=False, physical_playback=False,
                    microphone_opened=False, business_database_opened=False, raw_results_persisted=False,
                    driver_pid=os.getpid(), voice_python=str(args.voice_python),
                    gpu_policy=json.loads((AURA/'config/gpu_runtime.local.json').read_text(encoding='utf-8')),
                    ollama_runtime_policy=json.loads((AURA/'config/ollama_runtime.local.json').read_text(encoding='utf-8')),
                    baseline=snapshot(), cases=[])
    destination.parent.mkdir(parents=True, exist_ok=True)
    def save():
        temporary = destination.with_suffix('.tmp.json')
        temporary.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(destination)
    save()
    plans = [('tts_standalone', ['tts']), ('llm_standalone', ['llm']), ('llm_then_ram_tts', ['llm', 'tts'])]
    selected = plans if args.phase == 'all' else [row for row in plans if row[0].startswith(args.phase) or args.phase == 'chain' and row[0] == 'llm_then_ram_tts']
    if args.phase == 'llm':
        selected = [plans[1]]
    for label, kinds in selected:
        evidence['cases'].append(candidate_case(label, kinds, args.voice_python))
        save()
    evidence['final'] = snapshot()
    before = evidence['baseline'].get('processes')
    after = evidence['final'].get('processes')
    if isinstance(before, list) and isinstance(after, list):
        end_keys = {(row['pid'], row['created_utc']) for row in after}
        evidence['baseline_processes_preserved'] = all((row['pid'], row['created_utc']) in end_keys for row in before)
        evidence['candidate_tts_remaining'] = [row for row in after if row['role'] == 'candidate_ram_tts']
    evidence['finished_utc'] = utc()
    save()
    print(json.dumps({'evidence': str(destination), 'cases': [{key: row[key] for key in ('label', 'status')} for row in evidence['cases']],
                      'baseline_processes_preserved': evidence.get('baseline_processes_preserved'),
                      'candidate_tts_remaining': len(evidence.get('candidate_tts_remaining', []))}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
