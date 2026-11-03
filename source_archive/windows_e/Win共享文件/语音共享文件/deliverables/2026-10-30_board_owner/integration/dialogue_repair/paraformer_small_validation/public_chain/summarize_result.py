"""Freeze measured public inference timings without claiming physical latency."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'ACTUAL_CHAIN_1793454952793344600.json'
raw=source.read_bytes();evidence=json.loads(raw);r=evidence['result']
assert evidence['exit_code']==0 and r['status']=='PASS_ONE_PUBLIC_SMALL_ASR_COMPLETE_REPLY_RAM_TTS'
assert evidence['manual_pause_preserved'] and evidence['model_owners_unchanged'] and evidence['owners_unchanged']
assert r['owned_cleanup_confirmed'] and r['transport_connections_remaining']==0
public_without_punctuation='你好请用两句话介绍你自己'
assert hashlib.sha256(public_without_punctuation.encode()).hexdigest()==r['asr']['text_sha256']
t=r['timings']
report=dict(status='ONE_PUBLIC_V16_INFERENCE_CHAIN_PASSED',
    evidence=dict(file=source.name,sha256=hashlib.sha256(raw).hexdigest()),
    startup_sha256=r['startup_sha256'],asr_variant='paraformer_small',asr_threads=3,
    measured_seconds={
        'asr_decode':t['asr_decode_wall_ms']/1000,
        'llm_complete_rpc':t['llm_complete_rpc_ms']/1000,
        'tts_first_chunk_rpc':r['completed_tts_chunks'][0]['request_wall_ms']/1000,
        'asr_decode_start_to_first_ram_audio':t['asr_decode_start_to_first_ram_audio_ms']/1000,
        'asr_decode_start_to_all_ram_audio':t['asr_decode_start_to_complete_ram_audio_ms']/1000,
        'asr_load_and_pin_validation_separate':t['asr_model_load_and_pin_wall_ms']/1000,
    },llm_metrics=r['llm_metrics'],reply_characters=r['reply']['chars'],tts_chunks=r['reply']['sentence_chunks'],
    input=dict(public_synthetic=True,duration_seconds=r['fixture_samples']/r['fixture_sample_rate'],
               raw_reference_equal=False,public_reference_without_punctuation_hash_equal=True),
    preserved=dict(manual_pause=True,microphone_open=False,production_ui_camera_owners=True,
                   windows_model_owners=True,owned_requests_cleaned=True,remaining_transport_connections=0),
    background_activity_changed=evidence['background_activity_changed'],
    interpretation='In this public single case, complete LLM generation is now the largest measured per-turn stage.',
    limits=[
        'One cold-child ASR decode; model loading and pin checks are reported separately, not counted as per-turn recognition.',
        'Public WAV enters ASR directly; physical microphone, frontend/endpoint, production Jobs routing, context/permission/Store work and playback/ACK are outside this probe.',
        'The existing persona and negotiated reply contract are used; no real conversation history or retrieved memory is supplied.',
        'First RAM audio is synthesized data availability, not first network packet, audio enqueue or first acoustic sound.',
        'Background activity changed; this is neither a controlled before/after comparison nor human waiting/accuracy acceptance.',
        'The allocation micro-optimization was rejected after its separate queue overflow and remains undeployed.',
    ])
target=HERE/'RESULT.json';assert not target.exists()
target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result=str(target),status=report['status'],sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
