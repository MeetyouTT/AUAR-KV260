"""Seal this already tested source-only overlay; no application imports."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def fp(path):
    raw=path.read_bytes();return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def main():
    manifest=json.loads((ROOT/'overlay_manifest.json').read_text(encoding='utf-8'))
    contract=ROOT.parent/'memory_candidate/STREAM_CONTRACT_HANDOFF.json'
    checked=json.loads(contract.read_text(encoding='utf-8'))
    if checked['tests']['combined_passed']!=57 or checked['tests']['combined_failed']!=0:
        raise ValueError('Final independent regression receipt required')
    for name,item in manifest['files'].items():
        if fp(ROOT/'after'/name)['sha256']!=item['sha256']:raise ValueError('Candidate source changed')
    output=dict(schema='aura.ordinary-tts-streaming-handoff.v1',status='FROZEN_SOURCE_AND_SYNTHETIC_CONTRACT_PASS',
        baseline_startup_sha256='ac9be342ffbf933a7e044e99f74ce6ddc45b947970f04741e3534744644bc1f7',
        hardware_executed=False,production_modified=False,files=manifest['files'],
        artifacts={name:fp(ROOT/name) for name in ('ordinary_streaming.overlay.zip','overlay_manifest.json',
            'extra_source_map.json','build_overlay.py','tests/test_streaming.py',
            'tests/test_stream_memory_contract.py','tests.xml','REVIEW.txt')},
        required_store=checked['prepared_api'],store_contract_receipt=dict(path=str(contract),**fp(contract)),
        tests=checked['tests'],
        interface='prepare_text(..., chunk_sink=None); same callback(chunk,reply,start_sample,token) as existing local sequence',
        unchanged_default='No sink keeps original buffering/native-rate plan; explicit converter keeps buffered bridge',
        streaming_admission=dict(full_reply_json=True,whole_text_limit=240,all_sentence_boundaries_preflight=True,
            generated_before_TTS=True,prepared_durable_API_required=True,native_rate=24000,max_samples=720000,
            unique_complete_playback_token=True,partial_ACK=False,queue_capacity=128,packet_backpressure_guard=True),
        timings=dict(path='board_business.dialogue.latency',origin='board_job_worker_start',
            measured=['asr_ms','admission_ms','route_ms','analysis_enqueue_ms','prepare.context_ms',
                'prepare.llm_rpc_ms','prepare.tts_rpc_ms','prepare.first_tts_ready_ms','first_audio_queued_ms','worker_total_ms'],
            speaker_first_audio_measured=False,contains_body_or_ids_or_pcm=False),
        limitations=['Complete LLM JSON is still required before first TTS; LLM token streaming is unchanged',
            'TTS requests remain sequential; gain depends on later sentences to overlap',
            'Failed preparation metrics may not reach Jobs latency before its exception handler',
            'Reasoning/identity local-sequence DIALOGUE_ROUTE fallback retains original buffered path',
            'Real TTS/first speaker audio, physical ASR and long-run acceptance remain root-owned'],
        supplemental_legacy_regression=dict(passed=70,failed=4,same_failed_cases_reproduced_on_unmodified_main=True,
            scope='Stale former-character aliases; not claimed as a passing full legacy suite',
            reports=['regression_tests.xml','legacy_baseline_tests.xml']))
    (ROOT/'HANDOFF.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(fp(ROOT/'HANDOFF.json')))
if __name__=='__main__':main()
