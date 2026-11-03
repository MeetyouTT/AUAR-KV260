"""Local arithmetic/source provenance only. Never imports project runtime."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]


def write(name, value):
    (HERE / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2,
                                        allow_nan=False) + '\n').encode('utf-8'))


def main():
    sources = [
        'aura/config/gpu_runtime.local.json',
        'aura/config/ollama_runtime.local.json',
        'aura/common/gpu_coordination.py',
        'aura/tools/voice_startup_guard.py',
        'aura/tools/model_inference_startup.py',
        'aura/tools/model_inference_host.py',
        'deliverables/2026-10-18_board_dialogue/project_ollama.py',
        'deliverables/2026-10-18_board_dialogue/project_ollama_process.json',
        'deliverables/2026-10-18_board_dialogue/project_ollama_stderr.log',
        'deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py',
        'deliverables/2026-10-30_board_owner/integration/production_model_host/production_runtime.py',
        'deliverables/2026-10-29_parallel_interaction/gpu_calibration.json',
        'deliverables/2026-10-29_parallel_interaction/public_gpu_baseline.json',
        'deliverables/2026-10-29_parallel_interaction/public_gpu_layout4g.json',
        'deliverables/2026-10-29_parallel_interaction/public_gpu_final_adaptive.json',
        'deliverables/2026-10-29_parallel_interaction/observation_layout_ready.json',
        'deliverables/2026-10-29_parallel_interaction/layout_config_before_layout4g.json',
    ]
    manifest = []
    for relative in sources:
        path = PROJECT / relative
        sha = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(block)
        manifest.append(dict(path=str(path), size=path.stat().st_size,
                             sha256=sha.hexdigest()))
    current = dict(total_mib=16311, used_mib=14023, free_mib=2288,
                   llm_reported_size_bytes=14528848851,
                   llm_gpu_bytes=11579215051,
                   tts_warm_reserved_bytes=2057306112,
                   tts_max_extra_reserved_bytes=211812352,
                   tts_cold_peak_reserved_bytes=4972347392)
    budget = dict(
        mode='read_only_local_review_no_inference',
        live_input_source='parent-provided fresh metadata, not queried by reviewer',
        live_sample_utc=None,
        input=current,
        byte_values_mib={key: value / (1024 ** 2) for key, value in current.items()
                         if key.endswith('_bytes')},
        unchanged_policy_mib=dict(reserve=768, llm_warm_extra=512,
                                  llm_cold_extra=12032, tts_warm_extra=384,
                                  tts_cold_extra=5120),
        instantaneous_arithmetic_only_mib=dict(
            llm_warm_required_free=1280, tts_warm_required_free=1152,
            overlapping_warm_required_free=1664, tts_cold_required_free=5888,
            added_residency_before_solo_llm_line=1008,
            added_residency_before_solo_tts_line=1136,
            added_residency_before_overlap_line=624,
            mixed_statistic_residual=14023 - (11579215051 + 2057306112) / (1024 ** 2)),
        historical=dict(original_gpu_bytes=13874694716,
                        original_min_free_mib=210,
                        fit2048_gpu_bytes=13594693466,
                        fit2048_observation_seconds=.64,
                        fit4096_final_min_free_mib=1656,
                        delta_to_original_gpu_mib=(13874694716-11579215051)/(1024**2),
                        logged_fit_layer53_mib=11042, logged_fit_layer54_mib=11199,
                        logged_layer_delta_mib=157),
        proposed_experiment_not_applied=dict(
            fit_target_mib=3968, expected_layer_goal_only='53 -> 54 if actual loader confirms',
            new_calibration_required=True, guaranteed_gain=False,
            explicit_num_gpu_override=False, other_models_unchanged=True),
    )
    write('budget.json', budget)
    write('source_manifest.json', dict(generated_utc=datetime.datetime.now(
        datetime.timezone.utc).isoformat(), sources=manifest,
        copied_model_files=0, private_databases_read=False,
        runtime_actions_performed=[]))
    outputs = {}
    for name in ('REVIEW.txt', 'budget.json', 'source_manifest.json', 'build_report.py'):
        path = HERE / name
        outputs[name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             size=path.stat().st_size)
    write('HANDOFF.json', dict(status='FROZEN_READ_ONLY_REVIEW', files=outputs,
                               production_configuration_changed=False,
                               inference_or_gpu_benchmark_performed=False,
                               daemon_or_model_restarted=False))
    print(json.dumps(dict(status='FROZEN_READ_ONLY_REVIEW', files=outputs),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
