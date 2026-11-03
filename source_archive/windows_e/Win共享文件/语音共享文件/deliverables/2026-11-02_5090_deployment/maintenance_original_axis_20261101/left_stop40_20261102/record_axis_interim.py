import datetime
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;FIX=HERE/'py39_fix';DELIVERY=HERE.parents[1]
final=json.loads((FIX/'FINAL_LIVE.json').read_text(encoding='utf-8'))
analysis=json.loads((FIX/'JITTER_ANALYSIS.json').read_text(encoding='utf-8'))
current=dict(schema='aura-axis-dedicated-chat-handoff-1',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    operator='Dedicated axis chat; sole board axis writer; original project chat read-only',
    status='LEFT40_RIGHT45_DEPLOYED_JITTER_STOP_REARM_FIX_IN_PROGRESS',
    current_release=final['controller_root'],startup_sha256=final['startup_sha256'],
    face_config_sha256=final['face_config_sha256'],controller_manifest_sha256=final['controller_manifest_sha256'],
    boot_id=final['boot_id'],owners=final['owners'],latest_observed_following=final['following'],
    latest_observed_pan_state=final['pan_state'],latest_observed_readback=final['current_readback'],
    latest_observation_utc=final['utc'],last_report=final['report'],last_report_result=final['report_result'],
    runtime_fault_count=analysis['runtime_faults']['count'],
    targets=dict(left=.4,right=.45,tolerance=.03,left_trigger=.05,right_camera_trigger=.8064720153808593),
    validation=dict(windows_python310=31,board_python39=31,components=380,selected_files=25,
        actual_new_report_observed=True,left_trigger_minus1_target40_observed=True,right_trigger_plus1_target45_observed=True,
        physical_stop_position_acceptance='User feedback now says left side normal; user-view directions not equated to PWM sign'),
    latest_user_feedback='Right turn stutters: stops briefly then continues; left turn reported normal (original typo interpreted).',
    jitter_findings=dict(latest_run_s=24.293,normal_visual_completions=8,interrupted_segments=5,
        interruption_reasons=dict(SOURCE_UNCONFIRMED=2,SOURCE_HORIZON_ENDED=1,CONTROL_TICK_LATE=1,SOURCE_SUBMISSION_EXPIRED=1),
        restart_gaps_ms=[170,319,189,73,71],same_segment_endpoint_reversals_observed=0,
        mechanical_load_proven=False,direction_mapping='User-view right has not been equated with PWM increase/decrease'),
    next_action='Prepare and test minimal opt-in recovery stability gate in original core/session/entry. Immediate STOP, original TTL/lease, targets retained.',
    evidence=dict(initial_static_review=str(HERE/'INDEPENDENT_REVIEW.json'),python39_fix=str(FIX),
        published=str(FIX/'APPLIED.json'),board_pure_tests=str(FIX/'PURE_TESTS_BOARD_PY39.json'),
        latest_readback=str(FIX/'FINAL_LIVE.json'),jitter_numeric=str(FIX/'JITTER_NUMERIC_EVIDENCE.json'),
        jitter_analysis=str(FIX/'JITTER_ANALYSIS.json')),
    compatibility_history='First candidate failed before device output because float | None is invalid on board Python 3.9; fixed with typing.Optional. All failure evidence retained.',
    concurrency_boundary='Only axis delivery records and AXIS_CURRENT_HANDOFF.json are maintained here; global AGENTS/README/DEPLOYMENT_CURRENT left to original chat.')
p=DELIVERY/'AXIS_CURRENT_HANDOFF.json'
if p.exists():
    backup=HERE/('AXIS_CURRENT_HANDOFF.before-'+datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S%f')+'.json')
    backup.write_bytes(p.read_bytes())
tmp=p.with_name('.'+p.name+'.axis.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(p)
print(json.dumps(dict(path=str(p),status=current['status'],following=current['latest_observed_following'],runtime_fault_count=current['runtime_fault_count'])))
