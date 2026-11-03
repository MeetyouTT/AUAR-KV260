"""Metadata/documentation only. Archive exact old bytes before current updates."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import uuid

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
INTEGRATION=REPAIR.parent
OWNER=INTEGRATION.parent
PROJECT=OWNER.parents[1]
SHARED=PROJECT.parent
ANALYSIS=SHARED/'语言模型分析'
STARTUP='67d03ca40d709d22d761706bfca51a55e352adf86763ced7fb5eb5a688123a55'
MANIFEST='8312169b6747d6f0e1c2c8a73c20ecee6cd7b949083f977871412a96390c2e73'
V14='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a'
CONFIG='faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7'
BOOT='8100a7fd-0c6a-46c4-82b8-f874988a1521'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def record(path,raw=None):
    raw=path.read_bytes() if raw is None else raw
    return dict(path=str(path.resolve()),sha256=sha(raw),bytes=len(raw))
def atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.part-'+uuid.uuid4().hex)
    try:
        with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
def exact_archive(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('existing_archive_differs')
    else:
        with path.open('xb') as stream:stream.write(raw)
    return record(path,raw)


def block(raw,name,text,archives):
    begin=('<!-- '+name+' -->').encode();end=('<!-- /'+name+' -->').encode()
    if raw.count(begin)!=1 or raw.count(end)!=1:raise ValueError('current_marker_not_unique')
    left=raw.index(begin);right=raw.index(end,left)
    inner=raw[left+len(begin):right]
    old=raw[left:right+len(end)]
    key='archived-'+name+'-v14-'+sha(inner)[:12]
    archive=(b'\n\n<!-- '+key.encode()+b' -->\n'+
        '以下旧v14当前段原文逐字保留为历史；仅适用于其原startup。\n'.encode()+inner+
        b'\n<!-- /'+key.encode()+b' -->')
    current=begin+b'\n'+text.encode('utf-8')+b'\n'+end
    archives.append(dict(marker=name,old_block_sha256=sha(old),old_body_sha256=sha(inner),
                         archived_body_present=True))
    return raw[:left]+current+archive+raw[right+len(end):]


def main():
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    inputs={
      'revision':REPAIR/'idle_cpu_integration/revision.json',
      'installed':INTEGRATION/'listening_entry_fix/actual_automatic-listening-v15-idle-cpu.json',
      'idle_before':REPAIR/'idle_v14_before.json','idle_after':REPAIR/'idle_v15_after.json',
      'initial':REPAIR/'v15_initial.json','final_restore':REPAIR/'v15_final_probe.json',
      'operator_window':REPAIR/'v15_operator_window.json',
      'live':INTEGRATION/'listening_entry_fix/actual_live_listening.json',
      'controls':INTEGRATION/'listening_entry_fix/actual_control_semantics.json',
      'asr_decision':REPAIR/'first_wait_streaming_validation/DECISION.json'}
    if (REPAIR/'v15_operator_feedback.json').exists():inputs['later_feedback_probe']=REPAIR/'v15_operator_feedback.json'
    raw_inputs={name:path.read_bytes() for name,path in inputs.items()}
    values={name:json.loads(raw) for name,raw in raw_inputs.items()}
    installed,final,live,controls=(values[name] for name in ('installed','final_restore','live','controls'))
    for value in (installed,final,live,controls,values['idle_after']):
        if value['startup_sha256']!=STARTUP:raise ValueError('v15_evidence_startup_mismatch')
    if installed['source_manifest_sha256']!=MANIFEST or installed['configuration_sha256']!=CONFIG:
        raise ValueError('v15_publication_identity_mismatch')
    if not live['continuous_capture_passed'] or not live['priority_scope_passed']:
        raise ValueError('actual_listening_gates_not_passed')
    for key in ('pause_preference_false_observed','resume_preference_true_observed','cancel_rearm_passed',
                'pause_closed_microphone','pause_released_owned_arecord','model_worker_reused_on_rearm'):
        if controls.get(key) is not True:raise ValueError('actual_control_gate_not_passed')
    if not (final['phase']=='IDLE' and final['playing'] is False and final['listening']['state']=='WAITING_SPEECH'
            and final['listening']['enabled'] is True and final['listening']['microphone_open'] is True
            and final['runtime_faults']['count']==0):raise ValueError('final_restore_snapshot_mismatch')
    samples=values['operator_window']['samples']
    if len(samples)!=30 or any(s['startup_sha256']!=STARTUP for s in samples):raise ValueError('operator_window_mismatch')
    docs={
      'project_AGENTS.md':PROJECT/'AGENTS.md','project_README.md':PROJECT/'README.md',
      'analysis_README.md':ANALYSIS/'README.md','dialogue_STATUS.json':REPAIR/'STATUS.json',
      'IMPLEMENTATION_STATE.json':OWNER/'IMPLEMENTATION_STATE.json',
      'owner_continuation.txt':OWNER/'板端业务正式接管与实测接续_20261030.txt',
      'performance_plan.txt':REPAIR/'板端性能分配与优化计划.txt'}
    raw_docs={name:path.read_bytes() for name,path in docs.items()}
    archive_records={name:exact_archive(HERE/'before'/name,raw) for name,raw in raw_docs.items()}
    evidence={name:exact_archive(HERE/'evidence'/ (name+'.json'),raw_inputs[name]) for name in inputs}
    atomic(HERE/'before_manifest.json',encoded(archive_records))
    old_status=json.loads(raw_docs['dialogue_STATUS.json'])
    old_implementation=json.loads(raw_docs['IMPLEMENTATION_STATE.json'])
    before,after=values['idle_before'],values['idle_after']
    feedback=dict(audio_continuity_user_confirmed=True,waiting_improvement=False,
        source='root relay of latest user feedback: continuity confirmed, waiting still long',
        precise_turn_timing_association='pending root stage correlation',
        later_feedback_probe_is_not_automatically_the_confirmed_turn=True,
        audible_first_sound_measured=False,full_physical_dialogue_acceptance=False)
    acceptance=dict(continuous_capture_passed=True,priority_scope_passed=True,controls_verified=True,
        pause_resume_disk_preference_verified=True,cancel_rearm_verified=True,owned_arecord_release_verified=True,
        model_worker_reused_verified=True,audio_continuity_user_confirmed=True,waiting_improvement=False,
        operator_asr_acceptance_passed=False,full_physical_dialogue_acceptance=False,
        audible_first_sound_measured=False,cold_boot_listening_verified=False,
        actual_restart_pause_verified=False,multi_hour_stability_verified=False)
    resource=dict(before=dict(revision='v14',seconds=before['duration_seconds'],
            cpu_busy_percent=before['cpu']['cpu']['busy_percent'],
            native_completion_rate_per_second=before['observed_native_fps'],
            native_counter_before=before['state_before']['native']['frames'],
            native_counter_after=before['state_after']['native']['frames']),
        after=dict(revision='v15',seconds=after['duration_seconds'],
            cpu_busy_percent=after['cpu']['cpu']['busy_percent'],
            native_completion_rate_per_second=after['observed_native_fps'],
            native_counter_before=after['state_before']['native']['frames'],
            native_counter_after=after['state_after']['native']['frames']),
        cpu_change_percentage_points=round(after['cpu']['cpu']['busy_percent']-before['cpu']['cpu']['busy_percent'],2),
        controlled_abba=False,whole_board_performance_improvement_proven=False,
        native_counter_rate_is_physical_display_fps=False,target_fps=16,target_16fps_acceptance_passed=False,
        limitation='Two separate approximately8s listening observations; workload/startup/counters differ; no causal or waiting-speed claim.')
    quality=[dict(engine=item['engine'],intended_text_edit_distance=item['intended_text_edit_distance'],
                  reference_characters=item['reference_characters']) for item in values['asr_decision']['quality']]
    observation=dict(schema='aura.current-observation.v15',status='V15_CURRENT_USER_CONTINUITY_CONFIRMED_WAITING_NOT_IMPROVED',
        updated_utc=utc,revision='v15',root=installed['target'],startup_sha256=STARTUP,source_manifest_sha256=MANIFEST,
        configuration_sha256=CONFIG,component_pins=378,board_boot_id=BOOT,
        supervisor_pid=970372,gtk_pid=970411,frontend_worker_pid=970467,camera_pid=260102,camera_birth_ticks=784437,
        pids_are_snapshot_only=True,current_live_state_claimed=False,
        data_origin='board',retention_enabled=True,wake_word_required=False,automatic_listening=True,
        conversation_mode='half_duplex',voice_barge_in=False,business_options=installed['business_options'],
        current_revision_acceptance=acceptance,user_feedback=feedback,
        final_restore_snapshot=dict(observed_mono=final['observed_mono'],phase=final['phase'],playing=final['playing'],
            listening=final['listening'],runtime_fault_count=final['runtime_faults']['count'],
            capture_failures=final['capture_performance'].get('capture_failures'),
            memory_process_counters=final['memory'],memory_retry=final['memory_retry'],
            scope='Saved final restore snapshot; later human rounds do not replace this historical checkpoint.'),
        memory_counter_scope='Current process counters only; do not subtract v14 completed493 or older snapshots.',
        operator_window=dict(samples=len(samples),seconds=samples[-1]['observed_mono']-samples[0]['observed_mono'],
            submitted_values=sorted(set(s['safe_capture']['counters']['submitted'] for s in samples)),
            listening_states=sorted(set(s['listening']['state'] for s in samples)),
            any_playing=any(s['playing'] for s in samples),
            scope='No human round in this window; later user continuity feedback is a separate source.'),
        resource_observation=resource,
        asr_candidates=dict(production='formal_paraformer_3threads',new_streaming_models_deployed=False,
            reference_kind='public synthetic intended text, not human verified transcript gold',quality=quality,
            ctc_coexist=values['asr_decision']['ctc_coexist'],
            transducer_realtime_skipped_due_to_quality_result=values['asr_decision']['transducer_realtime_skipped_due_to_quality_result']),
        windows_model_health=dict(source='root-reported fresh read-only LAN health',endpoint='192.168.50.1:8797',
            role='model_inference_only',ok=True,fixed_27b_iq4_xs_resident=True,omnivoice_num_step=16,tts_ready=True,
            services_changed_by_documentation_task=False),
        unchanged_boundaries=dict(weights_outside_shared_directory=True,model_or_threshold_or_queue_changed=False,
            capture_frames=8,target_fps=16,following=False,pan_state='FAULT',pulse_us=None,
            no_business_or_identity_grant_bypass=True,no_private_database_replay=True),evidence=evidence,
        previous_observation=record(REPAIR/'current_observation_v14.json'),
        documentation_only=True,model_device_or_private_db_actions_by_documentation_task=[])
    observation_path=REPAIR/'current_observation_v15.json'
    atomic(observation_path,encoded(observation))
    reference=dict(path='语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v15.json',
        path_base=str(SHARED),sha256=record(observation_path)['sha256'],status=observation['status'],revision='v15',
        startup_sha256=STARTUP,source_manifest_sha256=MANIFEST,configuration_sha256=CONFIG,component_pins=378,
        observations_are_not_full_acceptance=True)
    summary=(f'- 现役v15：{installed["target"]}；startup SHA {STARTUP}，378份组件；manifest SHA {MANIFEST}；config SHA {CONFIG}未改。\n'
        f'- 恢复回执mono{final["observed_mono"]:.9f}：IDLE/no playing、自动WAITING_SPEECH/enabled=true/mic=true，无唤醒词、半双工，GUI故障0；supervisor970372/GTK970411/frontend970467、camera260102/birth784437，同boot {BOOT}。均是保存时点，下次必须现读。\n'
        '- v15连续采集、优先级作用域、磁盘暂停false→恢复true、取消rearm、arecord释放及worker复用均通过；不代替冷启动/暂停重启/多小时长稳。\n'
        '- 用户最新确认声音连续，仍认为等待过长：audio_continuity_user_confirmed=true、waiting_improvement=false；具体真人轮次/阶段计时关联待核，不把后续THINKING的ASR数或旧ACK硬挂该反馈。扬声器首声尚未声学测量，不能宣布完整对话验收。\n'
        '- 两段约8秒监听观察CPU83.98%→82.33%，仅-1.65个百分点；native完成计数速率3.37→6.27次/秒，不是屏幕物理FPS且未达16目标，不构成严格A/B或等待提速证明。\n'
        '- 正式保持原Paraformer3线程、combined前端1线程/capture nice-10、原8帧；板端业务/存储/雪妃显示，Windows仅现有27B与OmniVoice16，权重仍D:/AIModels。两种新流式ASR未上线；合成意图107字对照差异3/7/12不是人工gold，CTC另有1秒credit失败。\n'
        '- 最终恢复时本进程memory completed74/discarded1/streak0无error、capture failures0；不得与v14累计493等直接相减。跟随false、机械FAULT/null、身份与每包权限/完整ACK边界保留。\n'
        '- 接续以integration/dialogue_repair/current_observation_v15.json和idle_cpu_integration/v15_current_note.txt为准；旧v14正文及文档原字节归档于docs_state_v15/before。')
    note=('v15当前恢复与空闲减负观察（只依据已保存metadata）\n\n'+summary+
        '\n\n本版只替换GTK旧字幕写入点与常驻音频重复idle状态IPC两个源。原audio poll/ALSA静音/echo reference、播放active/error/EOS、字幕TTL/取消/Store提交后失效均保留。\n'
        '30次约60秒operator_window采样没有提交或播放，不是用户确认轮；后续用户确认声音连续但等待仍长，与该空闲窗口分开记录。未宣称本版降低实际首声等待。\n'
        '两段资源观察不是同条件ABBA；native是draw/swap完成计数观测，不是物理扫描/显示FPS。两个候选模型质量仅相对合成意图文本，均未上线；正式仍原3线程识别。\n'
        f'当前观测JSON SHA {reference["sha256"]}。本次仅更新文档及白名单metadata，未操作服务、硬件、模型或私库。\n').encode('utf-8')
    note_path=REPAIR/'idle_cpu_integration/v15_current_note.txt'
    analysis_note=ANALYSIS/'板端空闲CPU减负与v15当前观测_20261031.txt'
    atomic(note_path,note);atomic(analysis_note,note)
    archived_blocks=[]
    outputs={}
    outputs['project_AGENTS.md']=block(raw_docs['project_AGENTS.md'],'board-business-live-20261030',summary,archived_blocks)
    readme=('现役v15（378组件）已恢复自动聆听；连续采集、优先级及暂停/恢复/取消控制通过。用户确认声音连续，但等待仍长，不能声称首声已改善。正式仍原Paraformer3线程、27B/OmniVoice16；两新ASR未上线。\n\n'
        '本版只减少重复idle音频IPC和旧字幕覆盖，保持16fps目标、视觉身份、原8帧与权限/完整ACK。两段8秒CPU83.98%→82.33%仅观察；native完成计数3.37→6.27次/秒不等于屏幕FPS。详见[当前观测](deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v15.json)、[v15短报告](deliverables/2026-10-30_board_owner/integration/dialogue_repair/idle_cpu_integration/v15_current_note.txt)及[状态](deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json)。旧v14段逐字归档，PID下次现读，权重仍D盘。')
    outputs['project_README.md']=block(raw_docs['project_README.md'],'dialogue-current-20261031',readme,archived_blocks)
    analysis=block(raw_docs['analysis_README.md'],'board-business-live-20261030',summary,archived_blocks)
    analysis=block(analysis,'performance-dialogue-plan-20261031',
        '- [性能与对话平衡优化方案（2026-10-31）](性能与对话平衡优化方案_20261031.txt)：保留基于v10的阶段规划；现役v15，以当前观测和对应回执区分已部署、观察结果与未验收项。',archived_blocks)
    link=('<!-- idle-cpu-v15-report-20261031 -->\n'
        '- [板端空闲CPU减负与v15当前观测](板端空闲CPU减负与v15当前观测_20261031.txt)：v15已恢复，声音连续获用户确认但等待仍长；两段8秒CPU/native计数观察不构成提速或16fps通过。\n'
        '<!-- /idle-cpu-v15-report-20261031 -->\n\n').encode('utf-8')
    outputs['analysis_README.md']=link+analysis
    status=dict(old_status)
    history=list(status.get('continuation_history',[]))
    history.append(dict(status=old_status['status'],startup_sha256=V14,
        archive=archive_records['dialogue_STATUS.json'],scope='Exact fullv14 metadata preserved; no gates inherited byv15'))
    status.update(status=observation['status'],updated_utc=utc,current_revision='v15',startup_sha256=STARTUP,
        source_manifest_sha256=MANIFEST,configuration_sha256=CONFIG,component_pins=378,
        main_pid=970372,gtk_pid=970411,frontend_worker_pid=970467,camera_pid=260102,camera_birth_ticks=784437,
        board_boot_id=BOOT,current_observation=reference,continuation_history=history,
        controls_verified=True,short_capture_verified=True,continuous_capture_passed=True,priority_scope_passed=True,
        full_physical_dialogue_acceptance=False,multi_hour_stability_verified=False,
        controlled_whole_board_cpu_reduction_proven=False,current_revision_acceptance=acceptance,
        latest_human_feedback=feedback,latest_memory_runtime_counters=dict(process_revision='v15',observed_mono=final['observed_mono'],
            completed=74,discarded=1,failure_streak=0,counters_are_process_local=True),later_capture_failure_count=0,
        verification_scope_notice='v15 continuous/control/priority passed. User confirms continuous sound; waiting not improved. First-audible timing, turn association and multi-hour stability unverified.',
        evidence=dict(installed=evidence['installed'],live=evidence['live'],controls=evidence['controls'],
                      final_restore=evidence['final_restore'],operator_window=evidence['operator_window']),
        current_live_state_claimed=False)
    outputs['dialogue_STATUS.json']=encoded(status)
    implementation=dict(old_implementation)
    implementation['continuation_history']=list(implementation.get('continuation_history',[]))+[
        dict(status=old_implementation['status'],startup_sha256=V14,archive=archive_records['IMPLEMENTATION_STATE.json'])]
    implementation.update(status=observation['status'],updated_utc=utc,current_observation=reference,
        verification_scope_notice=status['verification_scope_notice'])
    production=dict(implementation['production'])
    production.update(startup_sha256=STARTUP,source_manifest_sha256=MANIFEST,configuration_sha256=CONFIG,component_pins=378,
        last_verified_ui_supervisor_pid=970372,last_verified_gtk_pid=970411,last_verified_camera_pid=260102,
        last_observed_ui_supervisor_pid=970372,last_observed_gtk_pid=970411,last_observed_camera_pid=260102,
        last_observed_camera_birth_ticks=784437,last_verified_pid_fields_revision='v15 saved observation only',
        current_observation=reference,audio_continuity_user_confirmed=True,waiting_improvement=False)
    implementation['production']=production
    implementation['verified_listening']=dict(revision='v15',startup_sha256=STARTUP,
        continuous_capture_passed=True,priority_scope_passed=True,controls_verified=True,
        operator_dialogue_acceptance=False,evidence=dict(live=evidence['live'],controls=evidence['controls']))
    implementation['response_latency']=dict(revision='v15',startup_sha256=STARTUP,
        ordinary_reply_sentence_streaming=True,dialogue_output_format='dialogue_abc_v1',
        audio_continuity_user_confirmed=True,waiting_improvement=False,audible_first_sound_measured=False,
        feedback_turn_timing_association='pending root stage correlation',current_observation=reference)
    outputs['IMPLEMENTATION_STATE.json']=encoded(implementation)
    prefix=('v15当前接续：两源空闲减负已发布，声音连续获用户确认，等待仍长。\n\n'+summary+
        '\n\n以下完整原文为v14及更早历史，不能把其PID/计数或验收直接用于v15：\n\n').encode('utf-8')
    outputs['owner_continuation.txt']=prefix+raw_docs['owner_continuation.txt']
    outputs['performance_plan.txt']=('v15当前补充（下方原阶段规划全文保留）：\n'
        '已发布idle音频状态IPC门控与生产字幕单写者修复，当前startup67d03ca4/378pins；声音连续获用户确认、等待仍长。'
        '两段约8秒CPU83.98%→82.33%，native完成计数3.37→6.27次/秒非物理FPS，不证明等待提速或16fps通过。'
        '详见idle_cpu_integration/v15_current_note.txt和current_observation_v15.json；原Paraformer3线程和全部阈值/队列/身份保持。\n\n').encode('utf-8')+raw_docs['performance_plan.txt']
    for name,path in docs.items():
        if path.read_bytes()!=raw_docs[name]:raise ValueError('document_changed_concurrently')
    for name,path in docs.items():atomic(path,outputs[name])
    checks=dict(status='CORE_V15_DOCUMENTS_UPDATED_TIMING_ASSOCIATION_PENDING',
        exact_archives_verified=all(Path(v['path']).read_bytes()==raw_docs[k] for k,v in archive_records.items()),
        archived_blocks=archived_blocks,outputs={str(path):record(path) for path in docs.values()},
        observation=record(observation_path),report=record(note_path),analysis_report=record(analysis_note),
        model_source_or_device_or_private_db_changed=False,
        final_owner_acceptance_touched=False,feedback_turn_link_pending=True)
    atomic(HERE/'update_receipt.json',encoded(checks))
    print(json.dumps(dict(status=checks['status'],observation=record(observation_path),
        modified_documents=[str(path) for path in docs.values()],exact_archives_verified=checks['exact_archives_verified']),ensure_ascii=False))


if __name__=='__main__':main()
