"""Bounded, offline probes. Does not deploy or open any physical device.

Run core with -S: it must work without third-party Python packages.
ASR/VAD timings are Windows measurements, never predictions of Cortex-A53 speed.
"""
import argparse
import ast
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import wave
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
AURA = WORKSPACE / '语音共享文件' / 'aura'
FRONTEND = AURA.parents[0] / 'deliverables' / '2026-10-21_environment_frontend'
EXTERNAL = Path('D:/AIModels/audio-frontend-eval-20261021')
sys.path.insert(0, str(AURA))

def blocked(*args, **kwargs):
    raise RuntimeError('Network disabled during migration simulation')

socket.socket.connect = blocked
socket.create_connection = blocked

def write(name, value):
    (HERE / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(value, ensure_ascii=False), flush=True)

def memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
            *[(name, ctypes.c_size_t) for name in (
                'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]]
    if os.name != 'nt':
        return {'available': False}
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    ok = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo(
        ctypes.c_void_p(kernel.GetCurrentProcess()), ctypes.byref(counters), counters.cb)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return {'peak_working_set_mib': counters.PeakWorkingSetSize / 2**20,
            'current_private_mib': counters.PrivateUsage / 2**20,
            'peak_commit_mib': counters.PeakPagefileUsage / 2**20}

def stats(values):
    v = sorted(values)
    return {'count': len(v), 'median': statistics.median(v),
            'p95': v[int((len(v)-1)*.95)], 'max': max(v)}

def metadata():
    return {'os': platform.platform(), 'machine': platform.machine(),
            'python': platform.python_version(), 'executable': sys.executable,
            'network_blocked': True, 'board_accessed': False,
            'microphone_opened': False, 'playback_started': False,
            'production_changed': False}

def owner(n):
    return {'protocol': 'aura-asr-1', 'board_boot_id': 'simulation-only',
        'session_id': 'synthetic', 'request_id': 'migration-%s' % n,
        'generation': n, 'capture_id': 'synthetic-%s' % n,
        'sample_count': 3200, 'pcm_sha256': '0'*64, 'budget_ms': 5000}

def core_read():
    from common.conversation_store import ConversationStore
    from common.conversation_context import build_context
    store = ConversationStore(HERE / 'core_state' / 'synthetic.sqlite3')
    rows, facts = store.context_snapshot('a'*32)
    history, info = build_context('simulation-no-llm', rows, '我的项目叫什么？', memories=facts)
    assert any(f['value'] == '海风' for f in facts)
    assert '这个回答没有播放' not in json.dumps(history, ensure_ascii=False)
    return {'facts_recovered': len(facts), 'unplayed_answer_excluded': True,
            'budget_upper_bound': info['budget_upper_bound']}

def core():
    from common.conversation_store import ConversationStore
    from common.conversation_context import build_context
    from common.speaker_identity import SpeakerStore
    from common.thinking_policy import route, FeedbackGate
    from common.spoken_input import prepare_spoken_input
    state = HERE / 'core_state'
    state.mkdir(exist_ok=False)
    store = ConversationStore(state / 'synthetic.sqlite3')
    cid = 'a'*32
    checks = []
    meta = owner(0)
    store.begin(cid, meta, '记住：项目=海风', '记住：项目=海风')
    assert store.memory_command(meta, '记住：项目=海风')
    for i in range(1, 201):
        meta = owner(i)
        store.begin(cid, meta, '合成测试问题%d' % i, '合成测试问题%d' % i)
        store.generated(meta, '合成测试回答%d' % i, 480, '1'*64)
        assert store.played(meta, 480, '1'*64)
    pending = owner(201)
    store.begin(cid, pending, '最后一个测试问题', '最后一个测试问题')
    store.generated(pending, '这个回答没有播放', 480, '2'*64)
    child = subprocess.run([sys.executable, '-B', '-S', str(Path(__file__).resolve()), 'core-read'],
        capture_output=True, encoding='utf-8', timeout=20)
    assert child.returncode == 0, child.stderr
    restart = json.loads(child.stdout)
    checks.append('separate_process_restart_and_full_playback_ack')
    rows, facts = store.context_snapshot(cid)
    durations = []
    for _ in range(100):
        began = time.perf_counter()
        history, info = build_context('simulation-no-llm', rows, '我的项目叫什么？', memories=facts)
        durations.append((time.perf_counter()-began)*1000)
    assert info['budget_upper_bound'] <= info['context_limit']
    assert '海风' in json.dumps(history, ensure_ascii=False)
    checks.append('durable_fact_recall_and_context_budget')
    correction = owner(202)
    store.begin(cid, correction, '更正记忆：项目=暮色', '更正记忆：项目=暮色')
    store.memory_command(correction, '更正记忆：项目=暮色')
    try:
        store.played(pending, 480, '2'*64)
    except ValueError:
        pass
    else:
        raise AssertionError('Stale ACK crossed memory revision barrier')
    checks.append('memory_correction_rejects_stale_ack')
    other = owner(203)
    store.begin('b'*32, other, '访客合成问题', '访客合成问题')
    other_rows, other_facts = store.context_snapshot('b'*32)
    other_history, _ = build_context('simulation-no-llm', other_rows, '项目叫什么？', memories=other_facts)
    assert not other_facts and '暮色' not in json.dumps(other_history, ensure_ascii=False)
    checks.append('separate_conversation_does_not_receive_other_facts')
    forget = owner(204)
    store.begin(cid, forget, '忘记我的项目', '忘记我的项目')
    assert store.memory_command(forget, '忘记我的项目')
    rows, facts = store.context_snapshot(cid)
    history, _ = build_context('simulation-no-llm', rows, '我的项目叫什么？', memories=facts)
    assert not facts
    assert not any(word in json.dumps(history, ensure_ascii=False) for word in ('海风', '暮色'))
    checks.append('forgotten_fact_not_resurrected_by_context_retrieval')
    assert prepare_spoken_input('你好西兰，陪我聊聊')['text'].startswith('你好汐蓝')
    assert prepare_spoken_input('我的朋友叫西兰')['text'] == '我的朋友叫西兰'
    assert route('今天比较开心')['mode'] == 'chat'
    assert route('240元先八折减30元加12元运费，实付多少？')['mode'] == 'reasoning'
    gate = FeedbackGate({'feedback_after_ms': 0})
    gate.cancel()
    assert not gate.due(999)
    checks.append('spoken_alias_thinking_route_and_cancel_are_local_rules')
    dimension = 192
    a, b, c = ([1., 0., 0.] + [0.]*(dimension-3),
               [0., 1., 0.] + [0.]*(dimension-3),
               [0., 0., 1.] + [0.]*(dimension-3))
    speaker = SpeakerStore(state/'synthetic_speaker.sqlite3', 'synthetic-no-real-person', dimension, .7, .1, create=True)
    speaker.enroll('a', 'Synthetic A', a, consent=True, expected_revision=0)
    speaker.enroll('b', 'Synthetic B', b, consent=True, expected_revision=1)
    assert speaker.match(a).identity_id == 'a'
    assert speaker.match(c).state == 'UNKNOWN'
    assert speaker.match([1., 1.] + [0.]*(dimension-2)).state == 'AMBIGUOUS'
    speaker.close()
    speaker = SpeakerStore(state/'synthetic_speaker.sqlite3', 'synthetic-no-real-person', dimension, .7, .1)
    assert speaker.match(a).identity_id == 'a'
    assert speaker.delete('a', expected_revision=2)
    assert speaker.match(a).state == 'UNKNOWN'
    speaker.close()
    checks.append('192d_speaker_gallery_restart_unknown_ambiguity_delete')
    third_party = sorted(name for name in ('numpy', 'torch', 'onnxruntime', 'sherpa_onnx', 'speechbrain') if name in sys.modules)
    assert not third_party
    sources = []
    for mod in tuple(sys.modules.values()):
        file = getattr(mod, '__file__', None)
        if file and Path(file).suffix == '.py' and AURA.resolve() in Path(file).resolve().parents:
            p = Path(file).resolve()
            ast.parse(p.read_text(encoding='utf-8-sig'), feature_version=(3, 9))
            sources.append({'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                            'python39_syntax': 'pass'})
    result = metadata()
    result.update(status='PASS', checks=checks, check_count=len(checks),
        third_party_modules_loaded=third_party, separate_process_restart=restart,
        synthetic_turns=205, context_windows_ms=stats(durations), process_memory=memory(),
        core_source_manifest=sources, syntax_check_scope='Python 3.9 grammar only; not target ABI execution',
        warning='No ARM emulation; timings and memory are Windows process measurements')
    write('core', result)

def load_wav(path):
    with wave.open(str(path)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 16000)
        pcm = wav.readframes(wav.getnframes())
    return pcm

def asr():
    import numpy as np
    from board.runtime.audio.asr import SherpaOfflineRecognizer, AsrConfig
    root = AURA / 'models/asr/sherpa-onnx-paraformer-zh-2023-09-14'
    start = time.perf_counter()
    recognizer = SherpaOfflineRecognizer(AsrConfig(model_dir=str(root), prefer_int8=True, num_threads=1))
    load_ms = (time.perf_counter()-start)*1000
    rows = []
    for name in ('0.wav', '1.wav', '2.wav'):
        path = root/'test_wavs'/name
        raw = load_wav(path)
        samples = np.frombuffer(raw, dtype='<i2').astype(np.float32)/32768
        for repetition in range(2):
            started = time.perf_counter()
            stream = recognizer._recognizer.create_stream()
            stream.accept_waveform(16000, samples)
            recognizer._recognizer.decode_stream(stream)
            elapsed = time.perf_counter()-started
            text = str(stream.result.text or '').strip()
            assert text
            rows.append({'public_sample': name, 'sample_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'repetition': repetition, 'audio_seconds': len(raw)/32000,
                'decode_ms': elapsed*1000, 'rtf_windows': elapsed/(len(raw)/32000),
                'transcript': text, 'transcript_nonempty': True})
    model = Path(recognizer.model_path)
    result = metadata()
    result.update(status='WINDOWS_CPU_INFERENCE_PASS', num_threads=1,
        model_path=str(model), model_bytes=model.stat().st_size, model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
        load_ms=load_ms, rows=rows, process_memory=memory(),
        board_latency_proven=False, board_memory_proven=False,
        accuracy_scope='Three upstream public WAVs, nonempty/repeatable output; no WER or field claim')
    write('asr', result)

def vad():
    import numpy as np
    from board.runtime.audio.silero_gate import SileroFrameGate
    from board.runtime.audio.automatic_capture import SpeechEndpoint
    root = AURA / 'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs'
    rng = np.random.default_rng(261026)
    silence = np.zeros(8*16000, dtype='<i2').tobytes()
    noise = np.clip(rng.normal(0, 700, 8*16000), -32768, 32767).astype('<i2').tobytes()
    cases = [('synthetic_silence', silence, 'non_speech'), ('synthetic_white_noise', noise, 'non_speech')]
    for name in ('0.wav', '1.wav', '2.wav'):
        cases.append(('public_'+name, b'\0\0'*8000 + load_wav(root/name) + b'\0\0'*24000, 'speech'))
    rows = []
    for name, raw, expected in cases:
        start = time.perf_counter()
        gate = SileroFrameGate(EXTERNAL/'silero_vad_v5.onnx')
        load_ms = (time.perf_counter()-start)*1000
        endpoint = SpeechEndpoint(20, frame_classifier=gate)
        times, segments, starts = [], [], 0
        start = time.perf_counter()
        for offset in range(0, len(raw)-639, 640):
            before = endpoint.active
            began = time.perf_counter()
            segment = endpoint.feed(raw[offset:offset+640])
            times.append((time.perf_counter()-began)*1000)
            if endpoint.active and not before:
                starts += 1
            if segment is not None:
                end = offset + 640
                assert segment == raw[end-len(segment):end]
                segments.append(len(segment)/32000)
                endpoint = SpeechEndpoint(20, frame_classifier=gate)
        elapsed = time.perf_counter()-start
        success = (starts == 0 and not segments) if expected == 'non_speech' else (starts >= 1 and len(segments) >= 1 and not endpoint.active)
        rows.append({'case': name, 'expected': expected, 'expectation_pass': success,
            'audio_seconds': len(raw)/32000, 'starts': starts, 'segments_seconds': segments,
            'active_at_end': endpoint.active, 'pcm_exact': True, 'load_ms': load_ms,
            'feed_ms_windows': stats(times), 'rtf_windows': elapsed/(len(raw)/32000)})
    result = metadata()
    result.update(status='WINDOWS_CPU_INFERENCE_PASS' if all(r['expectation_pass'] for r in rows) else 'CASE_FAILURE',
        model='silero_vad_v5.onnx', num_threads=1, rows=rows, process_memory=memory(),
        board_realtime_proven_by_this_run=False,
        accuracy_scope='Public/synthetic samples only; no TV, bystander or room-noise rejection claim')
    write('vad', result)
    assert all(r['expectation_pass'] for r in rows), 'One or more VAD public/synthetic cases failed'

def compatibility():
    from unittest.mock import patch
    from types import SimpleNamespace
    from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer
    result = metadata()
    old = json.loads((FRONTEND/'board_inventory.json').read_text(encoding='utf-8'))
    result['target_historical'] = {k: old[k] for k in ('machine', 'python', 'packages', 'native_libraries')}
    result['target_historical']['scope'] = '2026-10-21 snapshot; not current board inventory'
    wheels = []
    for path in sorted(EXTERNAL.glob('*aarch64.whl')):
        native = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if '.so' not in name:
                    continue
                with archive.open(name) as item:
                    head = item.read(20)
                if head[:4] == b'\x7fELF':
                    endian = '<' if head[5] == 1 else '>'
                    machine = struct.unpack(endian+'H', head[18:20])[0]
                    native.append({'name': name, 'elf_machine': machine, 'aarch64': machine == 183})
        wheels.append({'filename': path.name, 'size_bytes': path.stat().st_size, 'native_libraries': native,
                       'execution_verified_this_run': False})
    result['existing_arm_wheels'] = wheels
    combo = json.loads((FRONTEND/'board_sdk_benchmark.json').read_text(encoding='utf-8'))
    standalone = json.loads((FRONTEND/'board_benchmark_v5.json').read_text(encoding='utf-8'))
    result['historical_board_combo'] = {'source': str(FRONTEND/'board_sdk_benchmark.json'),
        'wall_rtf': [r['wall_rtf'] for r in combo['rows']], 'new_board_test': False}
    result['historical_board_vad_alone'] = {'source': str(FRONTEND/'board_benchmark_v5.json'),
        'wall_rtf': [r['wall_rtf'] for r in standalone['rows']],
        'frame_p95_ms': [r['feed_p95_ms'] for r in standalone['rows']],
        'frame_max_ms': [r['feed_max_ms'] for r in standalone['rows']],
        'caveat': 'One strong-noise case split into two utterances; some frames exceeded 20ms', 'new_board_test': False}
    synth = OmniVoiceSynthesizer.__new__(OmniVoiceSynthesizer)
    synth.model = None
    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    try:
        with patch.dict(sys.modules, {'torch': fake_torch, 'omnivoice': SimpleNamespace(OmniVoice=object)}):
            synth.load()
    except RuntimeError as exc:
        result['current_tts_cpu_gate'] = {'cpu_rejected': True, 'error': str(exc),
            'scope': 'Executed original loader with injected CUDA-unavailable response; no TTS model loaded'}
    else:
        raise AssertionError('Expected current CUDA-only loader to reject CPU')
    config = json.loads((AURA/'config/model_storage.local.json').read_text(encoding='utf-8'))
    weights = sorted(Path(config['weights_directory']).glob('*.gguf'))
    result['llm_storage_metadata_only'] = [{'name': p.name, 'bytes': p.stat().st_size} for p in weights if p.is_file()]
    result['llm_weights_read_or_copied'] = False
    result['emulation'] = {'arm_guest_executed': False,
        'available_wsl_distribution': 'docker-desktop only', 'docker_engine_running': False,
        'scope': 'No configured ARM/PetaLinux guest used; no ARM timing inference from Windows'}
    result['status'] = 'STATIC_ABI_AND_HISTORICAL_EVIDENCE_COMPLETE'
    write('compatibility', result)

def lightweight_tts(kind='vits'):
    import numpy as np
    import sherpa_onnx
    from board.runtime.audio.tts import SherpaTtsBackend, TtsConfig
    # Reuse only the original model-construction method. Do not run the backend
    # constructor, query an audio device, call speak_async, or create path links.
    backend = SherpaTtsBackend.__new__(SherpaTtsBackend)
    backend.config = TtsConfig(num_threads=1)
    backend._sherpa = sherpa_onnx
    original_model = AURA/'models/tts'/('kokoro-int8-multi-lang-v1_1' if kind == 'kokoro' else 'vits-icefall-zh-aishell3')
    # kaldifst's Windows narrow-character path API cannot open the Chinese
    # workspace path. Stage only six existing non-LLM resources in the writable
    # ASCII task directory. No junction, environment, LLM or private data copy.
    ascii_root = Path('C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9').resolve()
    stage = Path(tempfile.mkdtemp(prefix=kind+'-migration-', dir=ascii_root)).resolve()
    assert stage.parent == ascii_root and str(stage).isascii()
    staged = []
    resources = [original_model/name for name in ('model.onnx', 'tokens.txt', 'lexicon.txt', 'date.fst', 'number.fst', 'phone.fst')]
    if kind == 'kokoro':
        resources = [original_model/name for name in ('model.int8.onnx', 'voices.bin', 'tokens.txt',
            'lexicon-zh.txt', 'lexicon-us-en.txt', 'lexicon-gb-en.txt', 'date-zh.fst', 'number-zh.fst', 'phone-zh.fst')]
        for directory in ('dict', 'espeak-ng-data'):
            resources.extend(p for p in (original_model/directory).rglob('*') if p.is_file())
    assert sum(p.stat().st_size for p in resources) < 400*2**20
    for resource in resources:
        assert not (getattr(resource.lstat(), 'st_file_attributes', 0) & 1024)
        target = stage/resource.relative_to(original_model)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(resource, target)
        assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(resource.read_bytes()).digest()
        staged.append(target)
    def cleanup():
        assert stage.resolve().parent == ascii_root
        for path in sorted(stage.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            assert stage in path.resolve().parents
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()
        stage.rmdir()
    backend.model_dir = stage
    started = time.perf_counter()
    try:
        tts = backend._build_tts()
    except BaseException:
        cleanup()
        raise
    load_ms = (time.perf_counter()-started)*1000
    rows = []
    output = HERE/('synthetic_kokoro_audio' if kind == 'kokoro' else 'synthetic_audio')
    output.mkdir(exist_ok=False)
    for i, text in enumerate(('你好，我是汐蓝。', '这是板端迁移测试，语音在本地生成。')):
        started = time.perf_counter()
        audio = tts.generate(text, sid=0, speed=1.)
        elapsed = time.perf_counter()-started
        values = np.asarray(audio.samples, dtype=np.float32)
        assert len(values) > audio.sample_rate/2 and np.isfinite(values).all() and np.max(np.abs(values)) > .001
        pcm = np.rint(np.clip(values, -1., 32767/32768)*32768).astype('<i2').tobytes()
        path = output/('%s_%d.wav' % (kind, i))
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(audio.sample_rate))
            wav.writeframes(pcm)
        rows.append({'text': text, 'sample_rate': int(audio.sample_rate), 'audio_seconds': len(values)/audio.sample_rate,
            'synthesis_ms_windows': elapsed*1000, 'rtf_windows': elapsed/(len(values)/audio.sample_rate),
            'output': str(path), 'output_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'finite_nonzero_waveform': True, 'human_listening_or_intelligibility_test': False})
    result = metadata()
    result.update(status='WINDOWS_CPU_WAVEFORM_SYNTHESIS_PASS', model=original_model.name,
        model_bytes=(original_model/('model.int8.onnx' if kind == 'kokoro' else 'model.onnx')).stat().st_size, num_threads=1,
        load_ms=load_ms, rows=rows, process_memory=memory(), original_omnivoice_voice_preserved=False,
        board_realtime_proven=False, audio_device_api_called=False,
        scope='Existing lightweight alternative generated fresh PCM; no production switch, no listening-quality claim',
        original_model_directory=str(original_model), temporary_non_llm_resource_copy=True,
        temporary_stage=str(stage))
    del tts
    cleanup()
    result['temporary_stage_removed'] = not stage.exists()
    write('kokoro_tts' if kind == 'kokoro' else 'lightweight_tts', result)

def tts_content(kind='vits'):
    import numpy as np
    from board.runtime.audio.asr import SherpaOfflineRecognizer, AsrConfig
    source = json.loads((HERE/('kokoro_tts.json' if kind == 'kokoro' else 'lightweight_tts.json')).read_text(encoding='utf-8'))
    root = AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14'
    recognizer = SherpaOfflineRecognizer(AsrConfig(model_dir=str(root), prefer_int8=True, num_threads=1))
    rows = []
    for row in source['rows']:
        path = Path(row['output'])
        with wave.open(str(path)) as wav:
            assert (wav.getnchannels(), wav.getsampwidth()) == (1, 2)
            rate = wav.getframerate()
            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32)/32768
        if rate != 16000:
            samples = np.interp(np.arange(round(len(samples)*16000/rate))*rate/16000,
                                np.arange(len(samples)), samples).astype(np.float32)
        stream = recognizer._recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        recognizer._recognizer.decode_stream(stream)
        text = str(stream.result.text or '').strip()
        assert text
        clean = lambda value: re.sub(r'[^\w\u4e00-\u9fff]', '', value)
        target, actual = clean(row['text']), clean(text)
        distance = list(range(len(actual)+1))
        for i, a in enumerate(target, 1):
            new = [i]
            for j, b in enumerate(actual, 1):
                new.append(min(new[-1]+1, distance[j]+1, distance[j-1]+int(a != b)))
            distance = new
        rows.append({'target': row['text'], 'asr_text': text,
            'character_edit_distance': distance[-1], 'target_characters': len(target),
            'exact_after_punctuation_normalization': target == actual})
    result = metadata()
    result.update(status='ASR_SELFCHECK_COMPLETE', rows=rows,
        scope='Automatic round-trip content observation, not human listening or independent TTS quality assessment')
    write('kokoro_content' if kind == 'kokoro' else 'tts_content', result)

def verify_sources():
    previous = json.loads((HERE/'core.json').read_text(encoding='utf-8'))
    rows = []
    for entry in previous['core_source_manifest']:
        current = hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()
        rows.append({'path': entry['path'], 'unchanged': current == entry['sha256'], 'sha256': current})
    write('source_recheck', {'all_unchanged': all(r['unchanged'] for r in rows), 'rows': rows})
    assert all(r['unchanged'] for r in rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['core', 'core-read', 'asr', 'vad', 'compatibility', 'lightweight-tts', 'tts-content', 'kokoro-tts', 'kokoro-content', 'verify-sources'])
    args = parser.parse_args()
    if args.task == 'core-read':
        print(json.dumps(core_read()))
    else:
        tasks = {'core': core, 'asr': asr, 'vad': vad, 'compatibility': compatibility,
            'lightweight-tts': lightweight_tts, 'tts-content': tts_content,
            'kokoro-tts': lambda: lightweight_tts('kokoro'), 'kokoro-content': lambda: tts_content('kokoro'),
            'verify-sources': verify_sources}
        try:
            tasks[args.task]()
        except Exception as exc:
            write(args.task + '_failure', {'status': 'FAILED', 'error_type': type(exc).__name__, 'error': str(exc), **metadata()})
            raise
