"""Reconcile ONLY saved public metadata and root-reported human feedback.
No device, network, model, private database or production path is accessed.
"""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
PROGRESS=H.parent/'progress_followup_20261031'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    baseline_path=PROGRESS/'feature_baseline_1793460222716595900.json'
    before_path=PROGRESS/'feature_before_visual.json'
    visual_path=PROGRESS/'feature_after_visual.json'
    speaker_path=PROGRESS/'feature_after_voice_status.json'
    baseline=json.loads(baseline_path.read_bytes());actual=baseline['result']['integration_result']
    before=json.loads(before_path.read_bytes());visual=json.loads(visual_path.read_bytes());speaker=json.loads(speaker_path.read_bytes())
    assert actual['worker_sha256']=='7d5ff31d1f56cb567fd630c35056a1a33f9d239f520ad92975f47e10149153df'
    assert actual['execution_host']=='board' and actual['passed']==22 and actual['failed']==1
    assert [c['id'] for c in actual['cases'] if c['status']=='FAIL']==['H01_bounded_history_retrieval']
    assert baseline['owners_unchanged'] and actual['workers_closed'] and actual['owned_temporary_database_removed']
    assert before['visual']['queries']==0 and visual['visual']['queries']==1
    assert visual['visual']['last_kind']=='current_person_count' and visual['voice_route']['generation']==42
    assert visual['playback_ack']['committed'] and not visual['latency']['ordinary_prepare']
    assert visual['audio']['turn_underrun_packets']==0
    evidence={p.name:dict(path=str(p),sha256=sha(p)) for p in (baseline_path,before_path,visual_path,speaker_path)}
    candidates={}
    for name in ('candidate_h01','candidate_d01','candidate_m03','candidate_speaker_close'):
        path=H/name/'HANDOFF.json';manifest=H/name/'SOURCE_MANIFEST.json'
        candidates[name]=dict(handoff=name+'/HANDOFF.json',handoff_sha256=sha(path),
            source_manifest=name+'/SOURCE_MANIFEST.json',source_manifest_sha256=sha(manifest),
            deployed=False)
    report=dict(schema='aura.feature-trigger-progress.v17.public-arm-and-human.v1',
        status='V17_PUBLIC_ARM_BASELINE_HISTORY_GAP_H01_FIX_READY_FOR_ROOT_ARM_REPLAY',
        evidence=evidence,baseline=dict(startup_sha256=actual['verification']['startup_sha256'],
            source_manifest_sha256=actual['verification']['source_manifest_sha256'],
            boot_id=actual['verification']['boot_id'],worker_sha256=actual['worker_sha256'],
            cases_total=23,test_assertions_passed=22,feature_cases_passed=20,feature_cases_failed=1,
            expected_missing_capability_confirmations=['G01_date_delete_current_gap','G02_reasoning_current_gap'],
            missing_handler_confirmations_are_not_functional_acceptance=True,
            sole_failure='H01_bounded_history_retrieval: current query wins limited history/context budget over public target source',
            fixture_limits=actual['limits'],owners_unchanged=True,temporary_store_removed=True),
        human=dict(visual_current_count=dict(user_reported_correct=True,route_generation=42,
            queries_before=0,queries_after=1,ordinary_prepare=False,complete_ack=True,turn_underrun_packets=0),
            speaker_status=dict(user_reported_correct_uncalibrated_response=True,field_calibration_pending=True,
                exact_speaker_turn_ack_not_captured=True,subsequent_snapshot_generation=48,
                subsequent_snapshot_transcript_characters=3,do_not_attribute_subsequent_ordinary_ack_to_speaker_query=True),
            short_reply=dict(root_reported_user_feedback='声音连续，等待可以接受',
                acceptance_scope='that short conversation only; not 16fps/long-run/physical first-audio measurement'),
            provenance='Direct human feedback relayed by authorized main/root chat; saved public snapshots independently inspected'),
        local_candidates=candidates,
        board_h01_runner=dict(path='candidate_h01/board_runner.py',sha256=sha(H/'candidate_h01/board_runner.py'),
            stage_manifest='candidate_h01/BOARD_STAGE_MANIFEST.json',actual_board_result_pending=True),
        production_ownership='Root alone operates devices/models/publishing. This chat writes only independent local sources and reports.',
        current_listening_state='Not freshly read here. User authorized root to resume; saved per-test pause receipts remain historical.',
        constraints=dict(llm_weights_external_D_AIModels=True,no_new_model=True,no_private_templates_or_recordings_copied=True,
            no_local_device_or_model_operation=True,no_production_file_modified=True,
            board_memory_policy_or_concurrent_summary_candidate_modified=False))
    archive=H/'history_pre_public_progress_v17';archive.mkdir(exist_ok=True)
    for name in ('TEST_MATRIX.json','HANDOFF.json','ACK.json','功能触发核查短报告.txt'):
        old=H/name;dest=archive/name
        if old.is_file() and not dest.exists():dest.write_bytes(old.read_bytes())
    write(H/'PUBLIC_FEATURE_PROGRESS.json',report)
    matrix=json.loads((H/'TEST_MATRIX.json').read_bytes())
    matrix['status']='V17_HUMAN_VISUAL_VERIFIED_ARM_PUBLIC_HISTORY_FAILURE_LOCAL_FIXES_PREPARED'
    matrix['latest_progress']='PUBLIC_FEATURE_PROGRESS.json'
    matrix['arm_public_baseline']=report['baseline']
    mapping={
        'V01':['V01_current_fresh_stable_count'],'V02':['V02_spatial_unsupported'],
        'V04':['V03_object_unsupported'],'V05':['V06_history_count'],
        'V07':['V04_zero_is_not_absence','V05_camera_unavailable'],
        'S03':['S02_explicit_start','S04_sample_1','S04_sample_2','S04_sample_3'],
        'S04':['S05_store_commit_final_consent'],
        'S08':['S01_readonly_no_receipt','S03_readonly_during_enrollment','S06_receipt_next_turn'],
        'S09':['S07_receipt_ttl_does_not_delete'],
        'M01':['M01_remember','M02_correct','M03_current_fact','M04_forget'],
        'M02':['H01_bounded_history_retrieval'],
        'M03':['G01_date_delete_current_gap'],'D01':['G02_reasoning_current_gap'],
        'P01':['M05_personal_without_grant']}
    cases={c['id']:c for c in actual['cases']}
    for row in matrix.get('rows',matrix.get('cases',[])):
        name=row['id']
        if name in mapping:
            selected=mapping[name]
            row['isolated_arm_public_execution']=dict(evidence='PUBLIC_FEATURE_PROGRESS.json',
                worker_case_ids=selected,status='failed_source_retrieval' if name=='M02' else
                    'missing_gate_confirmed_not_functional_pass' if name in ('M03','D01') else 'passed_with_fixture_inputs',
                production_classes=True,production_private_store=False,real_asr_camera_encoder_tts=False,
                playback_consumption='simulated_with_original_complete_receipt_guards')
        if name=='V01':
            row['real_execution']=dict(status='verified_v17_current_person_count_route_and_complete_ack',evidence='PUBLIC_FEATURE_PROGRESS.json',generation=42)
            row['human_acceptance']=dict(status='user_confirmed_current_count_correct',evidence='PUBLIC_FEATURE_PROGRESS.json')
        elif name=='S01':
            row['human_acceptance']=dict(status='user_confirmed_uncalibrated_status_answer',exact_round_ack_verified=False,
                calibration_pending=True,evidence='PUBLIC_FEATURE_PROGRESS.json')
        elif name=='M02':
            row['gap']='Actual ARM public H01: current query occupies history/context budget; exact two-source H01 candidate passed local 23/23 +172 tests, root isolated ARM replay pending.'
            row['pending_candidate']='candidate_h01/HANDOFF.json'
        elif name=='M03':row['pending_candidate']='candidate_m03/HANDOFF.json'
        elif name=='D01':row['pending_candidate']='candidate_d01/HANDOFF.json'
        elif name=='L01':
            row['latest_instruction']='User authorized root resume; this chat has not operated listening controls or freshly read live state.'
        elif name=='R01':
            row['human_acceptance']=dict(status='partial_short_reply_continuity_and_wait_user_confirmed',
                pending=['physical first sound','screen physical FPS','long stability'],evidence='PUBLIC_FEATURE_PROGRESS.json')
    write(H/'TEST_MATRIX.json',matrix)
    for name in ('HANDOFF.json','ACK.json'):
        path=H/name;value=json.loads(path.read_bytes())
        value['latest_public_feature_progress']='PUBLIC_FEATURE_PROGRESS.json'
        value['latest_user_instruction']='Main/root authorized to resume listening; earlier pause snapshots are historical.'
        value['latest_local_candidates']=candidates
        write(path,value)
    summary='''v17功能触发进度（仅本窗口独立报告，生产仍由主窗口维护）
真人视觉人数回答正确；v17 gen42有queries0→1、current_person_count、ordinary_prepare=false、完整ACK和本轮欠载0的对应metadata。
真人短答声音连续、等待可接受，仅限该次短对话。声纹尚未校准的回答获用户确认；随后3字普通轮ACK不能绑定到声纹询问，现场校准仍待验。
root实际ARM独立临时公开库：23个断言22通过、历史来源H01失败。两项通过只是确认日期删除/推理handler缺失；实际功能分支20通过、1失败、2缺口。ASR/相机/编码器/模型/播放消费均为fixture，原路由/SQLite/ACK类实际在ARM运行，不能当真人模型校准或私库验收。
H01精确两文件候选：在SQL限量与计数前排除当前查询；原worker23断言未改全过，172相关本地测试通过；独立板端overlay runner已交root。
D01最小原27B推理接入：80相关本地测试通过，2048/120保持；真实think支持、完整JSON、正确率和延迟待root单独实测，未上线。
M03单日日期预览/确认候选：16定向/183组合回归通过；原scope、60秒、预览完整ACK、同actor/grant、原事务指纹与幂等保留。未改原Store schema，未上线。
声纹关闭另发现queued Future.cancel同步回调改动遍历字典；独立一行tuple快照候选，基线2例确定失败→25项通过。reset本身无此缺陷，未改。
本窗口没有操作设备、模型、生产私库或发布。LLM权重仍项目外D:/AIModels。完整证据与候选指纹见PUBLIC_FEATURE_PROGRESS.json；既有文档原字节归档history_pre_public_progress_v17。
'''
    (H/'功能触发核查短报告.txt').write_text(summary,encoding='utf-8')
    print(json.dumps(dict(status=report['status'],matrix_rows=len(matrix.get('rows',matrix.get('cases',[]))),production_changed=False)))


if __name__=='__main__':main()
