"""Reconcile completed root evidence into project handoff metadata only."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
STATUS='NATIVE_PERSONA_POTENTIAL_CONFIRMED_PUBLIC_PIPE_PASSES_DISPLAY_TARGET_PENDING'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    restored=read(HERE/'resume_ui_trial_round2/actual_restore_finalized.json')
    assert restored['own_guard_removed'] and restored['original_unit_properties_restored'] and restored['normal_candidate_close']
    runs=[read(HERE/'resume_yuki_pipe_capacity'/name) for name in ('actual_round2_run.json','actual_round2_run_repeat.json')]
    assert all(r['result']['status']=='PASS_DETACHED_GUI_PUBLIC_PIPE_ONLY' for r in runs)
    samples=[read(HERE/'resume_ui_trial_round2'/name) for name in ('20261031T020939-actual-native-sample.json','20261031T021339-actual-native-sample.json')]
    persona=read(HERE/'resume_ui_trial/actual_public_persona_chain.json')
    assert persona['status']=='PASS_PUBLIC_PERSONA_TRANSPORT_ONLY'
    report=dict(updated_utc=now,status=STATUS,formal_replacement_selected=False,
        report=str(BASE/'character_persona_candidate/替换评审_20261031.txt'),
        profile_version='xuefei-yuki-board-v1-candidate',prompt_utf8_bytes=978,
        source_archive_sha256='2c25b6a91a635a9bb70eef00cdc180829c503cdba3382135f8366c72e3242334',
        assembly_inspection_sha256='58d39ed8757f93c1780bf59408bf0fe15d42ffae4da5a2dbf97218925bedf7cf',
        formal_renderer_fixture=dict(cpu_reduction_percent=20.05,pss_reduction_mib=189.24,mali_increase_mib=32.58,whole_board_cpu_benefit_inconclusive=True),
        native_samples=[dict(label=label,whole_board_cpu_cores=r['whole_board_cpu_cores'],ui_group_cpu_cores=r['ui_group_cpu_cores'],
            ui_group_pss_mib=r['ui_group_pss_mib'],native_swap_fps=r['native_state_sample']['fps']['visible_swap_fps'],
            person_count_boundaries=[v['camera_workload'].get('camera',{}).get('people_count') for v in r['resources']]) for label,r in zip(('idle','additional_public_probe'),samples)],
        public_audio=[dict(status=r['result']['status'],queue_peak=r['result']['probe_result']['input_queue']['peak_frames'],
            capacity_frames=8,nice=0,frontend_ms=r['result']['probe_result']['frontend_processing_ms'],
            asr=r['result']['probe_result']['asr'],person_count_boundaries=[r['result']['probe_result']['production_context'][key].get('camera',{}).get('people_count') for key in ('before','after')]) for r in runs],
        limitations=['Not a matched old-local16/new-local16 complete-business A/B','Not continuous-person load or physical microphone/playback acceptance',
            'Additional public probe has duplicate model sessions','Audio-load native swap14.21fps remains below16 target; ASR latency remains material',
            'No physical scanout or per-frame percentile measurement'],
        persona_real_cases=persona['cases'],persona_gui_binding_verified=True,real_business_database_migrated=False,production_detail_cleanup_enabled=False,
        original_restored=restored,windows_model_session='c684d464149148dfbf3f89c452db2ba3',
        dashboard=dict(visible_pid=21456,actual_model_host_pid=20548,tts_pid=11796,fixed_daemon_pid=24148,unrelated_ollama_pid=22672,portrait_pid=22420),
        identity_ids_or_templates_sent_to_windows=False)
    write(HERE/'CHARACTER_REVIEW.json',report)
    remaining=['Stable native16 display under complete business/audio load and matched old-local16/new-local16 resource A/B',
        'Continuous person in view, physical microphone/playback/lipsync/cancel and latency acceptance',
        'Consistent real migration plus single-writer handoff and summary-first detail cleanup acceptance',
        'Production Windows business retirement and durable model-only startup']
    for path in (BASE/'IMPLEMENTATION_STATE.json',HERE/'RESUME_VERIFICATION.json'):
        value=read(path);value['updated_utc']=now;value['status']=STATUS
        value['remaining_gates' if path.name=='IMPLEMENTATION_STATE.json' else 'remaining']=remaining
        value['character_integrated_review']=report
        value.setdefault('production',{}).update(last_verified_ui_supervisor_pid=487238,last_verified_gtk_pid=487470,
            last_verified_camera_pid=260102,original_entry_restored_after_synthetic_gui_trials=True,own_runtime_guards_removed=True,
            permanent_character_or_persona_switch=False)
        write(path,value)
    selected=[HERE/'CHARACTER_REVIEW.json',BASE/'character_persona_candidate/替换评审_20261031.txt',
        HERE/'resume_ui_trial_round2/actual_restore_finalized.json',HERE/'resume_ui_trial_round2/manifest.json',
        HERE/'resume_yuki_run_assembly/actual_staged_r3.json',HERE/'resume_ui_trial/actual_public_persona_chain.json',
        HERE/'resume_yuki_pipe_capacity/actual_round2_run.json',HERE/'resume_yuki_pipe_capacity/actual_round2_run_repeat.json',
        HERE/'resume_ui_trial_round2/20261031T020939-actual-native-sample.json',HERE/'resume_ui_trial_round2/20261031T021339-actual-native-sample.json',
        HERE/'run_ui_round2.py',HERE/'run_yuki_sample_round2.py',HERE/'run_yuki_public_pipe.py',HERE/'finalize_ui_round2_restore.py',
        HERE/'save_character_review.py',HERE/'resume_yuki_business_candidate_v2/yuki_business.source_candidate.zip']
    manifest={str(p.relative_to(BASE)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in selected}
    write(HERE/'CHARACTER_REVIEW_MANIFEST.json',dict(updated_utc=now,files=manifest,model_weights_included=False))
    print(json.dumps(dict(status=STATUS,source_and_evidence_files=len(manifest),original_ui_restored=True,production_replacement=False)))

if __name__=='__main__':main()
