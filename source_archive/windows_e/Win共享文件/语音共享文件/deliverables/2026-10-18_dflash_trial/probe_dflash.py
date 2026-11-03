"""Independent same-weight runner A/B. Invoked only by run_exclusive.ps1."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from tools.dialogue_stream import ReplyDecoder, REPLY_FIRST_FIELDS, stream_body
from tools.native_grammar import GRAMMAR, VERIFIED_BUILD
from common.reply_quality import possible_question_echo

MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
TARGET = Path('D:/AIModels/Ollama-AURA/blobs/sha256-d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9')
DRAFT = Path(json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))['draft_directory'])/'Qwen3.8-27B-DFlash2-Q4_K_M.gguf'
SERVER = Path('C:/Users/35870/AppData/Local/Programs/Ollama/lib/ollama/llama-server.exe')
BASE = 'http://127.0.0.1:51888'
REPORT = {'actual_27b': True, 'actual_tts': False, 'actual_playback': False, 'production_changed': False, 'target': str(TARGET), 'draft': str(DRAFT), 'cases': [], 'runners': []}
REPORT_PATH = HERE / 'probe_cuda.json'


def save():
    REPORT_PATH.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')


def api(path, body=None, timeout=10):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def gpu():
    r = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
    return r.stdout.strip()


def run_case(variant, text, *, temperature=.6, history=None, test_kind='chat', predict=120, repeat=0):
    original = stream_body(MODEL, history or [], text, reply_first=True)
    rendered = api('/apply-template', {'messages': original['messages'], 'chat_template_kwargs': {'enable_thinking': False}, 'enable_thinking': False, 'add_generation_prompt': True})
    assert rendered['prompt'].endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n')
    body = {'prompt': rendered['prompt'], 'stream': True, 'n_predict': predict, 'temperature': temperature, 'top_k': 20, 'top_p': .95, 'min_p': 0., 'repeat_penalty': 1., 'seed': 42, 'cache_prompt': True, 'n_keep': 4, 'grammar': GRAMMAR}
    decoder = ReplyDecoder(field_names=REPLY_FIRST_FIELDS)
    row = {'variant': variant, 'input': text, 'temperature': temperature, 'kind': test_kind, 'repeat': repeat, 'prompt_sha256': hashlib.sha256(body['prompt'].encode()).hexdigest(), 'first_pcm_ms': None}
    conn = http.client.HTTPConnection('127.0.0.1', 51888, timeout=90)
    started = time.perf_counter()
    try:
        conn.request('POST', '/completion', json.dumps(body).encode(), {'Content-Type': 'application/json'})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}: {response.read(4000)!r}')
        while True:
            line = response.readline(65537)
            if not line or len(line) > 65536:
                raise RuntimeError('Incomplete or oversized SSE')
            if not line.startswith(b'data:'):
                continue
            packet = json.loads(line[5:])
            if packet.get('error'):
                raise RuntimeError(str(packet['error']))
            delta = packet.get('content') or ''
            if delta:
                row.setdefault('first_raw_ms', round((time.perf_counter() - started) * 1000, 2))
            spoken = decoder.feed(delta)
            now = round((time.perf_counter() - started) * 1000, 2)
            if spoken:
                row.setdefault('first_reply_ms', now)
            if 'reply_text' in decoder.values:
                row.setdefault('speech_ready_ms', now)
            if packet.get('stop'):
                reply = decoder.finish()
                row.update(reply=reply, raw_reply=decoder.buffer, total_ms=now, timings=packet.get('timings'), tokens_predicted=packet.get('tokens_predicted'), stop=packet.get('stop_type'), stopped_limit=packet.get('stopped_limit'), question_echo=possible_question_echo(text, reply['reply_text']))
                break
        row['valid_json'] = True
    except Exception as exc:
        row['error'] = type(exc).__name__ + ': ' + str(exc)[:2000]
    finally:
        conn.close()
    REPORT['cases'].append(row)
    save()
    print(json.dumps(row, ensure_ascii=True), flush=True)
    if 'error' in row:
        raise RuntimeError(row['error'])
    return row


def launch(variant, index):
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', 51888)) != 0, 'Experimental port occupied'
    command = [str(SERVER), '--model', str(TARGET), '--host', '127.0.0.1', '--port', '51888', '--offline', '--no-webui', '--ctx-size', '2048', '--parallel', '1', '--load-mode', 'none', '--cache-type-k', 'q8_0', '--cache-type-v', 'q8_0', '--flash-attn', 'on', '--batch-size', '512', '--ubatch-size', '512', '--context-shift', '--keep', '4', '--gpu-layers', 'all', '--fit', 'off', '--device', 'CUDA0', '--log-verbosity', '4']
    if variant in ('dflash', 'dflash_cpu'):
        command += ['--spec-type', 'draft-dflash', '--spec-draft-model', str(DRAFT), '--spec-draft-n-max', '7', '--spec-draft-ngl', 'all']
        if variant == 'dflash_cpu':
            command[-1] = '0'
            command += ['--spec-draft-device', 'none']
    if variant == 'mtp':
        command += ['--spec-type','draft-mtp','--spec-draft-n-max','3']
    backend = SERVER.parent / 'cuda_v13' / 'ggml-cuda.dll'
    assert backend.is_file()
    env=dict(os.environ)
    env['GGML_BACKEND_PATH']=str(backend)
    env['PATH']=str(SERVER.parent)+os.pathsep+str(backend.parent)+os.pathsep+env.get('PATH','')
    log = (HERE / f'runner-cuda-{index}-{variant}.log').open('w', encoding='utf-8')
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    row = {'variant': variant, 'index': index, 'command': command, 'pid': process.pid, 'log': log.name}
    REPORT['runners'].append(row)
    start = time.monotonic()
    try:
        while time.monotonic() - start < 150:
            if process.poll() is not None:
                raise RuntimeError(f'{variant} runner exited {process.returncode}; inspect {log.name}')
            try:
                if api('/health', timeout=1).get('status') == 'ok':
                    break
            except Exception:
                pass
            time.sleep(.25)
        else:
            raise TimeoutError('Runner startup deadline')
        props = api('/props')
        assert Path(props['model_path']).resolve() == TARGET.resolve()
        assert props['build_info'] == VERIFIED_BUILD
        assert props['default_generation_settings']['n_ctx'] == 2048 and props['total_slots'] == 1
        expected_template = (HERE / 'original_template.txt').read_text(encoding='utf-8')
        assert props['chat_template'] == expected_template, 'Template changed'
        memory=gpu()
        assert int(memory.split(',')[0])>12000, 'Expected full 27B GPU allocation; no CPU fallback allowed'
        row.update(ready_ms=round((time.monotonic() - start) * 1000, 2), gpu_memory=memory, build=props['build_info'],cuda_backend=str(backend))
        save()
        print(json.dumps({'runner_ready': row}, ensure_ascii=True), flush=True)
        # Same first warmup on each launch; retained but excluded from steady-state summaries.
        run_case(variant, '你好汐蓝，今天过得怎么样', test_kind='warmup')
        return process, log
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
        save()
        raise


def main():
    assert TARGET.stat().st_size == 14403496864
    manifest = json.loads((HERE / 'draft_download.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'VERIFIED' and Path(manifest['file']).resolve() == DRAFT.resolve()
    assert DRAFT.stat().st_size == manifest['bytes']
    REPORT['gpu_before'] = gpu()
    for index, variant in enumerate(('baseline', 'dflash', 'dflash', 'baseline')):
        if variant in REPORT.get('candidate_failures',{}):continue
        try:process, log = launch(variant, index)
        except Exception as exc:
            if variant=='baseline':raise
            REPORT.setdefault('candidate_failures',{})[variant]=type(exc).__name__+': '+str(exc)
            save();continue
        try:
            for text in ('你好汐蓝，今天过得怎么样', '今天比较开心，陪我聊聊', '今天有点累，想和你说说话'):
                run_case(variant, text, repeat=index)
            for text in ('请记住，我喜欢绿色。', '请重复这句话：今天比较开心，陪我聊聊。'):
                run_case(variant, text, temperature=0., test_kind='greedy', repeat=index)
            if index in (2,3):
                pipeline(variant)
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            log.close()
            REPORT['gpu_after_runner'] = gpu()
            save()
    if not REPORT.get('pipeline', {}).get('dflash', {}).get('success', False):
        for extra_index,extra in enumerate(('dflash_cpu','mtp'),4):
            try:process,log=launch(extra,extra_index)
            except Exception as exc:
                REPORT.setdefault('candidate_failures',{})[extra]=type(exc).__name__+': '+str(exc)
                save();continue
            try:
                for text in ('今天比较开心，陪我聊聊', '今天有点累，想和你说说话'):
                    run_case(extra, text, test_kind='extra_chat', repeat=extra_index)
                for text in ('请记住，我喜欢绿色。','请重复这句话：今天比较开心，陪我聊聊。'):
                    run_case(extra,text,temperature=0.,test_kind='greedy',repeat=extra_index)
                pipeline(extra)
            finally:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)
                log.close();save()
    REPORT['summary'] = {}
    for variant in ('baseline', 'dflash'):
        rows = [r for r in REPORT['cases'] if r['variant'] == variant and r['kind'] == 'chat']
        REPORT['summary'][variant] = {'n': len(rows), 'speech_ready_median_ms': statistics.median(r['speech_ready_ms'] for r in rows) if rows else None, 'total_median_ms': statistics.median(r['total_ms'] for r in rows) if rows else None, 'question_echo_count': sum(r['question_echo'] for r in rows), 'speech_ready_values_ms': [r['speech_ready_ms'] for r in rows]}
    greedy = [r for r in REPORT['cases'] if r['kind'] == 'greedy']
    REPORT['greedy_parity'] = {text: len({r['raw_reply'] for r in greedy if r['input'] == text}) == 1 for text in sorted({r['input'] for r in greedy})}
    REPORT['status'] = 'PROBE_COMPLETE_NOT_DEPLOYED'
    save()
    print(json.dumps({'summary': REPORT['summary'], 'greedy_parity': REPORT['greedy_parity']}, ensure_ascii=True), flush=True)


def pipeline(variant):
    process=None
    try:
        process=subprocess.Popen([sys.executable,'-B','-u',str(HERE/'pipeline_probe.py'),variant],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        stdout,stderr=process.communicate(timeout=300)
        (HERE/('pipeline-'+variant+'.stdout.log')).write_text(stdout,encoding='utf-8')
        (HERE/('pipeline-'+variant+'.stderr.log')).write_text(stderr,encoding='utf-8')
        row={'success':process.returncode==0,'returncode':process.returncode,'gpu_after':gpu()}
    except Exception as exc:
        if process is not None and process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
            process.communicate(timeout=10)
        row={'success':False,'error':type(exc).__name__+': '+str(exc)}
    REPORT.setdefault('pipeline',{})[variant]=row
    save()
    print(json.dumps({'pipeline':variant,**row},ensure_ascii=True),flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        REPORT['status'] = 'PROBE_FAILED_NOT_DEPLOYED'
        REPORT['error'] = type(exc).__name__ + ': ' + str(exc)
        save()
        raise
