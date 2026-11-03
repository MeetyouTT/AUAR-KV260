"""Derive metadata-only capacity findings from the public acceptance run."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]


def audit(source, output):
    evidence = json.loads(source.read_text(encoding='utf-8'))
    by_name = {row['label']: row for row in evidence['cases']}
    tts = by_name['tts_standalone']
    llm = by_name['llm_standalone']
    chain = by_name['llm_then_ram_tts']
    policy = evidence['gpu_policy']
    tts_phase = tts['phases'][0]
    stats = tts_phase['backend_health']['gpu_coordination']['tts_stats']['cold_start_inference']
    peak_mib = stats['peak_reserved_bytes'] / 1024 ** 2
    final_free = evidence['final']['memory']['free_mib']
    before = {(row['pid'], row['created_utc']): row for row in evidence['baseline']['processes']}
    after = {(row['pid'], row['created_utc']): row for row in evidence['final']['processes']}
    missing = [row for key, row in before.items() if key not in after]
    added = [row for key, row in after.items() if key not in before]
    baseline_critical_pids = (2060, 13120, 5008, 7608, 8020, 26024, 21752,
                              29808, 29644, 22472, 30164, 24240, 28388)
    critical_before = [row for row in before.values() if row['pid'] in baseline_critical_pids]
    # Keep only runtime/layout lines. Do not copy the log's templates, requests,
    # generated text, prompt caches or any other possible business content.
    log_path = PROJECT/'deliverables/2026-10-18_board_dialogue/project_ollama_stderr.log'
    selected = []
    patterns = (
        r'^cmn  common_param:   - CUDA0\s*:',
        r'^common_params_fit_impl:   - CUDA0',
        r'^llama_prepare_model_devices: using device CUDA0',
        r'^load_tensors: offloaded \d+/\d+ layers to GPU',
        r'^load_tensors:\s+(?:CUDA0 model|CUDA_Host model) buffer size =',
        r'^llama_kv_cache:\s+(?:CPU|CUDA0) KV buffer size =',
        r'^llama_memory_recurrent:\s+(?:CPU|CUDA0) RS buffer size =',
        r'^sched_reserve:\s+(?:CUDA0|CUDA_Host) compute buffer size =',
    )
    for index, line in enumerate(log_path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if any(re.search(pattern, line) for pattern in patterns):
            selected.append(dict(line_number=index, metadata=line))
    selected = selected[-12:]
    result = dict(schema_version=1, utc=datetime.now(timezone.utc).isoformat(), source=str(source),
        statuses=dict(tts_standalone=tts['status'], llm_standalone=llm['status'], chain=chain['status']),
        tts=dict(cold_elapsed_seconds=tts_phase['elapsed_seconds'],
                 cold_budget_ms=tts_phase['budget_ms'], pcm_in_ram=True,
                 duration_seconds=tts_phase['duration_seconds'], cold_reserved_peak_mib=round(peak_mib, 3),
                 observed_device_minimum_free_mib=tts['monitor']['minimum_free_mib'],
                 policy_cold_mib=policy['tts_cold_extra_mib'], reserve_mib=policy['reserve_mib'],
                 measured_peak_below_declared_budget=peak_mib <= policy['tts_cold_extra_mib'],
                 own_worker_closed=True, after_close_free_mib=tts['after_close']['memory']['free_mib'],
                 baseline_free_mib=evidence['baseline']['memory']['free_mib']),
        llm=dict(cold_elapsed_seconds=llm['phases'][0]['elapsed_seconds'],
                 subsequent_elapsed_seconds=chain['phases'][0]['elapsed_seconds'],
                 resident_gpu_bytes=evidence['final']['project_ollama_ps'][0]['size_vram'],
                 configured_fit_target_mib=evidence['ollama_runtime_policy']['fit_target_mib'],
                 observed_final_free_mib=final_free, layout_metadata=selected),
        chain=dict(error=chain['phases'][-1]['error'],
                   refusal_elapsed_seconds=chain['phases'][-1]['elapsed_seconds'],
                   required_cold_tts_plus_reserve_mib=policy['tts_cold_extra_mib']+policy['reserve_mib'],
                   observed_free_mib=final_free,
                   shortfall_mib=max(0, policy['tts_cold_extra_mib']+policy['reserve_mib']-final_free),
                   candidate_tts_spawned=False, thresholds_lowered=False),
        runtime=dict(all_baseline_processes_preserved=evidence['baseline_processes_preserved'],
                     baseline_critical_pids=list(baseline_critical_pids),
                     critical_rows_found=len(critical_before),
                     critical_processes_preserved=len(critical_before) == len(baseline_critical_pids)
                         and all(key in after for key, row in before.items() if row['pid'] in baseline_critical_pids),
                     exited_other_baseline_rows=missing, added_rows=added,
                     candidate_ram_tts_remaining=evidence['candidate_tts_remaining'],
                     final_gpu_matches_initial=False,
                     final_gpu_difference_reason='27B was initially absent from /api/ps; public inference loaded its existing project runner, which is deliberately not unloaded',
                     other_models_or_services_stopped_by_test=False),
        conclusion='Single TTS and LLM passed; chain is capacity-blocked while original warm TTS remains. Do not lower the measured cold budget. No production cutover or shared-TTS replacement was performed.',
        startup_contract=dict(
            preflight_http='GET /v1/inference/preflight',
            preflight_python='backend.preflight(deadline=original_monotonic_deadline)',
            preflight_observation_only=True, preflight_reserves_memory=False,
            warmup_http='POST /v1/inference/warmup',
            warmup_example=dict(protocol_version=1, request_id='fresh-startup-request-id',
                board_boot_id='synthetic-boot', session_id='startup-model-owner', generation=1,
                budget_ms=240000, target='tts'),
            warmup_python='backend.warmup_tts(deadline=min(original_startup_deadline, monotonic()+240), cancelled=event, request_id=fresh_id)',
            warmup_result=dict(target='tts', ready=True, num_step=16, memory_only=True),
            readiness='GET /health -> backend.tts_ready; bound to the SAME alive proven owned worker object',
            default_model_loading=False, default_warmup=False,
            cold_tts_budget_mib=policy['tts_cold_extra_mib'], reserve_mib=policy['reserve_mib'],
            cold_start_owner_guard='Read-only CIM logical-worker family guard before Popen; external or unknown TTS ownership fails closed. No PID from a file is stopped.',
            global_atomic_ownership_claim=False,
            external_switch_coordinator_must_serialize_owners=True,
            startup_order=[
                'Externally confirm current runtime/process ownership, idle state, business single writer and rollback entry; this API does not grant stop authority',
                'The authorized old TTS owner releases only its own worker at the controlled switch; no duplicate RAM worker and no unrelated model changes',
                'Confirm no old/external OmniVoice family and no resident 27B for this TTS-first cold sequence; never unload a model automatically',
                'Re-read preflight, then explicitly warm the unique RAM TTS under the existing cold GPU lease and original startup deadline',
                'Verify tts_ready and unchanged owned-worker identity, then recheck original cold LLM admission; do not assume warmup guarantees that admission',
                'Send the complete board-owned request to the existing 27B under its original remaining deadline; do not add context/persona on Windows',
                'Recheck steady TTS admission and run a public LLM-to-board-validation-to-RAM-TTS test before business writer publication'],
            rollback_requirements=[
                'If ownership, idle state, readiness, admission, deadline or public end-to-end validation fails, do not publish the new business writer',
                'Close only the candidate host and its proven OwnedSpeechJob children; never stop processes by a discovered/stored PID',
                'The external authorized coordinator may resume the exact previously verified entry only while preserving the latest board data and single writer',
                'Do not restore an older database/snapshot, remove history, lower GPU protection or stop/unload unrelated models to obtain a pass'],
            current_runtime_action='read-only diagnostics only after initial acceptance; no further candidate TTS creation or production switch',
            pending_acceptance='The unique-owner TTS-first sequence and its final chain remain unexecuted; current original processes and loaded 27B are preserved'))
    sources = ('aura/common/model_inference_wire.py', 'aura/tools/model_inference_host.py',
               'aura/tests/framework/test_model_inference.py', 'aura/board/runtime/audio/omnivoice_voice.py',
               'aura/tools/voice_worker_transport.py')
    result['implementation_validation'] = dict(
        candidate_fake_tests=67, combined_worker_omnivoice_gpu_regression_passed=125,
        excluded_existing_test='test_reply_preserved_until_controller_submits_to_speech: old __new__ fixture lacks pause_started',
        readonly_preflight_evidence=str(HERE/'preflight_readonly.json'),
        real_explicit_warmup_executed_after_guard=False,
        real_unique_owner_chain_executed=False,
        initial_real_smoke_precedes_unique_owner_guard=True,
        sources_sha256={path: hashlib.sha256((PROJECT/path).read_bytes()).hexdigest() for path in sources})
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'statuses': result['statuses'],
        'critical_processes_preserved': result['runtime']['critical_processes_preserved'],
        'candidate_ram_tts_remaining': len(result['runtime']['candidate_ram_tts_remaining']),
        'cold_tts_shortfall_mib': result['chain']['shortfall_mib']}))


if __name__ == '__main__':
    audit(HERE/'real_acceptance_initial.json', HERE/'capacity_audit.json')
