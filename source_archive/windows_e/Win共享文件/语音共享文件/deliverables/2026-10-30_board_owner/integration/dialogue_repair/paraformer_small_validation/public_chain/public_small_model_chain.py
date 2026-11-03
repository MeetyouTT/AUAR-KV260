"""One frozen public WAV -> Small ASR -> complete ABC reply -> RAM TTS.

Root must guard PAUSED/mic=false, existing UI/camera/Windows owners, and impose
an external <=90 s hard deadline. This worker does not read API/state, Store,
microphone or speakers. No output transcript, reply, PCM or model downloads.
The result is not microphone-to-first-sound or a warmed ASR benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import signal
import sys
import time
import uuid

sys.dont_write_bytecode = True
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'
STARTUP_SHA = 'bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
MODEL_DIR = Path('/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6')
MODEL_SHA = '3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'
TOKENS_SHA = '4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa'
ASR_DEPS = Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps')
FIXTURE_DIR = Path('/home/root/aura-public-streaming-validation-20261031/synthetic-8a9983b6bb9f42c6')
MANIFEST_SHA = '7109ee213126f098a3a3da08bbc521beb0db54a21e0911be02e04f2010b9a869'
HELPER_SHA = '293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
WAV_SHA = '73a3f368db296aa1f11d0f586e6161829945d5df73f5680f06dc9a05395b3655'
PROMPT_SHA = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
PINS = {
    'board/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'board/runtime/__init__.py': 'e872d26327cffcd548d40793547880be7ed91b97c93b361fdcff3709f8f3f695',
    'board/runtime/audio/__init__.py': '8edaab47d81c8815e27a459af84ada028aa0265fd2d86f46131e091934b4c086',
    'tools/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'common/__init__.py': '9194622c40cccdf5c8db07fd11f4c472fcba36cfb935e5ab04396fe51b818cfe',
    'board/runtime/audio/board_asr.py': '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3',
    'board/runtime/board_dialogue.py': 'bce1f21962d083275d9e8a966f244d8c227d0d62e9a30314767453d04c05b475',
    'board/runtime/board_dialogue_client.py': '600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2',
    'board/runtime/compact_request_adapter.py': 'ea14001af904f80a4ca247cc5ee738f7418fd0bd0aa4ee30e5aaea13fbc31337',
    'common/board_timeline_clock.py': '93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02',
    'common/inference_output_contract.py': 'e07936da0f3e333c4a448a2b36b70cdfecb76939449c8cdbefffe11b9244c631',
    'common/model_inference_wire.py': '39306c53a967f21e318f34d5642f126e8f047ee90112ac5bb83f981965aab965',
    'common/reply_quality.py': '706d00b6aa15bf772a1d40c4e6fadefe677c2296a713fe02e75e554216090e3d',
    'tools/production_output_format.py': '0a0cc8c9fc3d0a29fbec5451603d8d6786b99e627e7c57c60c4049bb266f2463',
    'config/board_avatar_gtk.json': '8c35161e766c53728c75c592a074845e35e01502e8438aaf649b4a8e078a6101',
    'config/character_profile.local.json': '5dcac93339a56c549ef176e260b4ed7f01fdc3307059c53aa3784b7a382f09c3',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_bytes(path, expected, maximum=2 * 1024 * 1024):
    if (not path.is_absolute() or '..' in path.parts
            or any(p.is_symlink() for p in (path, *path.parents))
            or not path.is_file() or path.stat().st_size > maximum):
        raise ValueError('PIN_PATH_INVALID')
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError('PIN_MISMATCH')
    return raw


def public_input():
    helper_path = FIXTURE_DIR / 'quality_293b23f5dd350e5f.py'
    checked_bytes(helper_path, HELPER_SHA)
    spec = importlib.util.spec_from_file_location('_public_quality', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    manifest = json.loads(checked_bytes(FIXTURE_DIR / 'manifest.json', MANIFEST_SHA))
    validated = helper.validate_manifest(manifest)
    row, _, pcm = validated[0]
    if (row['id'] != 'S01' or row['sha256'] != WAV_SHA
            or row['samples'] != 41760 or row['rate'] != 16000):
        raise ValueError('PUBLIC_S01_MISMATCH')
    return helper, row, pcm


def runtime_inputs():
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT:
        raise ValueError('BOOT_MISMATCH')
    startup = json.loads(checked_bytes(ROOT / 'startup/config.json', STARTUP_SHA))
    code = ROOT / 'runtime/aura'
    for relative, expected in PINS.items():
        if startup['component_sha256'].get(relative) != expected:
            raise ValueError('SOURCE_MAPPING_MISMATCH')
        checked_bytes(code / relative, expected)
    cfg = json.loads((code / 'config/board_avatar_gtk.json').read_bytes())['board_business']
    if (cfg['asr_directory'] != str(MODEL_DIR) or cfg['asr_threads'] != 3
            or cfg['asr_variant'] != 'paraformer_small'
            or cfg['dialogue_output_format'] != 'dialogue_abc_v1'):
        raise ValueError('V16_ASR_CONFIGURATION_MISMATCH')
    profile = json.loads((code / 'config/character_profile.local.json').read_bytes())
    prompt = profile['persona_full_prompt']
    if sha(prompt.encode('utf-8')) != PROMPT_SHA:
        raise ValueError('PROMPT_MISMATCH')
    # Require a fresh process; do not replace modules already owned by a UI.
    if any(key == p or key.startswith(p + '.') for key in sys.modules
           for p in ('board', 'common', 'tools', 'sherpa_onnx')):
        raise ValueError('RUNTIME_ALREADY_IMPORTED')
    sys.path[:0] = [str(code), str(ASR_DEPS)]
    return cfg, prompt


def error_kind(exc):
    if isinstance(exc, TimeoutError):
        return 'TIMEOUT'
    if isinstance(exc, InterruptedError):
        return 'CANCELLED'
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return 'CONTRACT_OR_PIN_REJECTED'
    return 'RUNTIME_ERROR'


def run_case(*, asr_factory, client, prompt, pcm, reference, boot, deadline,
             wire, validate_reply, split_reply, quiet, clock=time.monotonic,
             cpu_clock=time.process_time, cancelled=lambda: False):
    """Injected dependencies allow fake-only tests of the exact control path."""
    owners, cancellations = [], []
    session = 'public-small-chain-' + uuid.uuid4().hex
    result = dict(status='FAIL', case_id='S01', timings={}, completed_tts_chunks=[],
                  owned_requests=[], cancellation=cancellations)
    phase = 'ASR_LOAD'

    def body():
        if cancelled():
            raise InterruptedError()
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError()
        return dict(protocol_version=1, request_id=uuid.uuid4().hex,
                    board_boot_id=boot, session_id=session, generation=1,
                    budget_ms=max(1, min(60000, int(remaining * 1000))))

    def send(kind, payload):
        payload = wire.validate_request(kind, payload)
        owner = wire.Owner.from_dict(payload)
        # Register before transport, including failures/partial responses.
        owners.append(owner)
        result['owned_requests'].append(dict(kind=kind, **owner.as_dict()))
        response = client.request(kind, payload, deadline=deadline, cancelled=cancelled)
        checked = wire.validate_response(response, owner, kind)
        if not checked['ok']:
            raise ValueError('REMOTE_FAILURE')
        if cancelled():
            raise InterruptedError()
        if clock() >= deadline:
            raise TimeoutError()
        return checked['result']

    try:
        started, cpu_started = clock(), cpu_clock()
        with quiet():
            asr = asr_factory()
        result['timings']['asr_model_load_and_pin_wall_ms'] = (clock() - started) * 1000
        result['timings']['asr_model_load_and_pin_cpu_ms'] = (cpu_clock() - cpu_started) * 1000
        phase = 'ASR_TRANSCRIBE'
        chain_start, cpu_started = clock(), cpu_clock()
        with quiet():
            recognized = asr.transcribe(pcm, sample_rate=16000, deadline=deadline,
                                        cancelled=cancelled)
        asr_done = clock()
        if not isinstance(recognized, str) or not recognized.strip():
            raise ValueError('EMPTY_ASR')
        result['timings']['asr_decode_wall_ms'] = (asr_done - chain_start) * 1000
        result['timings']['asr_decode_cpu_ms'] = (cpu_clock() - cpu_started) * 1000
        result['asr'] = dict(chars=len(recognized), text_sha256=sha(recognized.encode()),
                             reference_text_sha256=sha(reference.encode()),
                             exact_reference_match=recognized == reference)
        phase = 'LLM_COMPLETE_REPLY'
        payload = body()
        payload.update(task='dialogue', messages=[dict(role='system', content=prompt),
                                                 dict(role='user', content=recognized)],
                       options=dict(think=False, num_predict=120))
        llm_start = clock()
        model_result = send('llm', payload)
        llm_done = clock()
        reply = validate_reply(model_result['text'], recognized)
        pieces = split_reply(reply.text)
        text_validated = clock()
        result['timings'].update(llm_complete_rpc_ms=(llm_done - llm_start) * 1000,
            asr_completion_to_complete_validated_text_ms=(text_validated - asr_done) * 1000)
        metrics = model_result.get('metrics', {})
        result['llm_metrics'] = {k: v for k, v in metrics.items()
                                 if type(v) in (int, float) and math.isfinite(v)}
        result['reply'] = dict(chars=len(reply.text), text_sha256=sha(reply.text.encode()),
                               formal_contract_valid=True, sentence_chunks=len(pieces))
        phase = 'TTS_COMPLETE_RAM_AUDIO'
        audio_hash, samples, rpc_ms = hashlib.sha256(), 0, 0.0
        for index, text in enumerate(pieces):
            payload = body()
            payload['text'] = text
            sent = clock()
            audio_result = send('tts', payload)
            received = clock()
            audio = audio_result['audio']
            data, rate = wire.decode_audio(audio)
            if rate != 24000 or not data or audio['channels'] != 1 or audio['encoding'] != 'pcm_s16le':
                raise ValueError('TTS_FORMAT_REJECTED')
            if index == 0:
                first_ram_validated = clock()
                result['timings'].update(
                    asr_decode_start_to_first_ram_audio_ms=(first_ram_validated - chain_start) * 1000,
                    asr_completion_to_first_ram_audio_ms=(first_ram_validated - asr_done) * 1000)
            rpc_ms += (received - sent) * 1000
            audio_hash.update(data)
            samples += len(data) // 2
            result['completed_tts_chunks'].append(dict(index=index, samples=len(data) // 2,
                pcm_sha256=sha(data), request_wall_ms=(received - sent) * 1000))
            # Do not retain individual PCM or response base64 after validation.
            del data, audio, audio_result
        audio_done = clock()
        result['audio'] = dict(samples=samples, sample_rate=24000, channels=1,
                               encoding='pcm_s16le', pcm_sha256=audio_hash.hexdigest(),
                               duration_seconds=samples / 24000)
        result['timings'].update(tts_complete_rpc_sum_ms=rpc_ms,
            complete_validated_text_to_complete_ram_audio_ms=(audio_done - text_validated) * 1000,
            asr_completion_to_complete_ram_audio_ms=(audio_done - asr_done) * 1000,
            asr_decode_start_to_complete_ram_audio_ms=(audio_done - chain_start) * 1000)
        result['status'] = 'PASS_ONE_PUBLIC_SMALL_ASR_COMPLETE_REPLY_RAM_TTS'
    except Exception as exc:
        result.update(error_stage=phase, error_code=error_kind(exc))
    finally:
        cleanup_started = clock()
        for owner in owners:
            # Transport cancel is independently bounded to one second and
            # scoped to this process's exact boot/session/generation/request.
            try:
                reply = client.cancel(owner)
                checked = wire.validate_response(reply, owner, 'cancel')
                state = checked.get('result', {}).get('state') if checked['ok'] else None
                ok = checked['ok'] and state in ('completed', 'cancelled')
            except Exception:
                state, ok = None, False
            cancellations.append(dict(request_id=owner.request_id, confirmed=bool(ok),
                                      state=state if ok else 'UNCONFIRMED'))
        result['timings']['owned_cleanup_wall_ms'] = (clock() - cleanup_started) * 1000
        result['owned_cleanup_confirmed'] = all(x['confirmed'] for x in cancellations)
        if not result['owned_cleanup_confirmed']:
            result['status'] = 'FAIL_OWNED_CLEANUP_UNCONFIRMED'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-deadline-managed', action='store_true', required=True)
    parser.parse_args()
    # SIGALRM is only a Python-level backstop. Root must bound native inference
    # and this process externally; no child or production process is stopped.
    def expired(signum, frame):
        raise TimeoutError('SOFT_TIMEOUT')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.alarm(70)
    deadline = time.monotonic() + 65
    phase = 'INPUTS_AND_SOURCE_PINS'
    try:
        helper, row, pcm = public_input()
        cfg, prompt = runtime_inputs()
        from board.runtime.audio.board_asr import BoardParaformer
        from board.runtime.board_dialogue import validate_model_reply, split_sentences
        from board.runtime.board_dialogue_client import InferenceHttpClient
        from common.board_timeline_clock import StableTimelineClock
        from common import model_inference_wire as wire
        from tools.production_output_format import NegotiatedDialogueClient
        raw_client = InferenceHttpClient('192.168.50.1', 8797)
        timeline = StableTimelineClock(BOOT, raw_client.health_date_source_id(),
            raw_client.validate_sample, utc_bounds=cfg['utc_bounds'], monotonic=time.monotonic)
        phase = 'VERIFIED_FORMAT_NEGOTIATION'
        raw_client.sample_health_date(timeline, deadline=min(deadline, time.monotonic() + 3))
        client = NegotiatedDialogueClient(raw_client, system_prompt=prompt,
                                          mode=cfg['dialogue_output_format'])
        selection = client.public()
        if selection['negotiated_dialogue_format'] != 'dialogue_abc_v1':
            raise ValueError('FORMAL_ABC_NOT_NEGOTIATED')
        def asr_factory():
            import numpy
            import sherpa_onnx
            if numpy.__version__ != '1.21.2' or sherpa_onnx.__version__ != '1.13.8':
                raise ValueError('ASR_RUNTIME_VERSION_MISMATCH')
            for name, size in (('model.int8.onnx', 81828675), ('tokens.txt', 75352)):
                path = MODEL_DIR / name
                if any(p.is_symlink() for p in (path, *path.parents)) or path.stat().st_size != size:
                    raise ValueError('ASR_RESOURCE_LAYOUT_MISMATCH')
            return BoardParaformer(MODEL_DIR, model_sha256=MODEL_SHA,
                                   tokens_sha256=TOKENS_SHA, num_threads=3)
        result = run_case(asr_factory=asr_factory,
            client=client, prompt=prompt, pcm=pcm, reference=row['reference_text'],
            boot=BOOT, deadline=deadline, wire=wire, validate_reply=validate_model_reply,
            split_reply=split_sentences, quiet=helper.quiet_native)
        result.update(format_selection=selection, startup_sha256=STARTUP_SHA,
            asr_source_sha256=PINS['board/runtime/audio/board_asr.py'],
            asr_model_sha256=MODEL_SHA, asr_tokens_sha256=TOKENS_SHA, asr_threads=3,
            numpy_version=getattr(sys.modules.get('numpy'), '__version__', None),
            sherpa_version=getattr(sys.modules.get('sherpa_onnx'), '__version__', None),
            fixture_manifest_sha256=MANIFEST_SHA, fixture_wav_sha256=WAV_SHA,
            fixture_samples=row['samples'], fixture_sample_rate=row['rate'],
            prompt_sha256=PROMPT_SHA,
            transport_connections_remaining=len(raw_client._connections))
        if raw_client._connections:
            result['status'] = 'FAIL_TRANSPORT_CONNECTION_REMAINS'
    except Exception as exc:
        result = dict(status='FAIL', error_stage=phase, error_code=error_kind(exc))
    finally:
        signal.alarm(0)
    result.update(measurement_scope='single cold ASR load; ASR completion to complete text to complete RAM TTS',
        first_ram_audio_scope='first complete sentence PCM received and validated in RAM; not streaming first packet or speaker onset',
        public_synthetic=True, intended_not_human_verified=True, native_acoustic_acceptance=False,
        steady_state_latency=False, microphone_opened=False, audio_played=False,
        pcm_archived=False, store_accessed=False, permission_or_memory_actions_executed=False,
        production_services_modified=False, aggregate_model_counts_assumed=False,
        root_external_guard_and_timeout_required=True)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0 if result['status'].startswith('PASS_') else 2


if __name__ == '__main__':
    raise SystemExit(main())
