"""Record a coordination report locally; perform no board or service calls."""
import datetime
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE.parents[1];OUT=HERE/'offline_wide_restore'
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
event=dict(schema='aura-axis-received-cpu-window-status-1',recorded_host_utc=stamp,
    source_chat='01a19b1a-6a07-7781-8af9-aacacb1c8ca4',basis='Coordination message; no fresh board query by axis chat',
    reported_boot_id='a6d4a069-e9b0-4065-8df7-dc23556b168e',reported_platform='benchmark',
    reported_startup_sha256='e49436a8ada938c071b484ac04302134ac29420172457da6a2c544c841d77217',
    gtk_two_source_candidate_committed=True,camera_candidate_deployed=False,
    reported_benchmark_before=dict(duration_s=40,cpu_percent_total_board=82.591),
    reported_gui='Two original clock sample_rtt_exceeded startup failures; fresh failed state accepted by identity chat',
    cpu_after_measurement_available=False,overall_cpu_benefit_claimed=False,
    current_maintenance_owner='Identity chat: original clock recovery and enrollment-entry split',
    reported_camera_pid_unchanged=1332,reported_native_checkpoint_history_changed=False,
    axis_and_platform_frozen=True,axis_chat_board_queries_this_turn=0,axis_chat_board_actions_this_turn=0,
    required_baseline_choice=dict(
        keep_committed_gtk='A later wide before/after retaining this GTK measures only subsequent approved changes, such as camera optimization; do not attribute it to GTK.',
        evaluate_combined_gtk_camera='Coordinator may first restore only the two saved original GTK source bytes and corresponding current pins in a proper handoff window, preserving identity/pan/native changes, then take unoptimized wide before and publish the approved pair for matched after.',
        action_now='No rollback, publication, board query or workload is scheduled. Coordinator chooses and records the baseline variant after identity maintenance handback.'))
p=OUT/'REPORTED_GTK_CPU_WINDOW_HANDOFF.json';assert not p.exists();p.write_text(json.dumps(event,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
plan_path=OUT/'OFFLINE_WIDE_RECOVERY_PLAN.json';old=plan_path.read_bytes()
(OUT/'OFFLINE_WIDE_RECOVERY_PLAN.before_reported_e494.json').write_bytes(old)
plan=json.loads(old);plan['amended_host_utc']=stamp;plan['latest_coordination_report']=event
plan['context']['earlier_coordination_update_historical']=plan['context']['coordination_update']
plan['context']['coordination_update']='GTK two-source candidate committed to reported e494 startup; GUI clock startup failed twice; maintenance returned to identity chat. Camera candidate uninstalled. This is relayed state, not a new board observation.'
plan['cpu_attribution'].update(gtk_already_committed_in_report=True,benchmark_after_available=False,
    benchmark_before_after_benefit_proven=False,wide_baseline_variant_requires_explicit_record=True,
    possible_estimands=['Subsequent camera-only incremental effect with committed GTK held constant',
                        'Combined approved GTK+camera effect after coordinator establishes and records an original-GTK wide baseline'])
for phase in plan['phases']:
    if phase['order']==5:
        phase['name']='Same-wide baseline with explicit GTK variant'
        phase['requires'][0]='Same actual boot and verified wide platform. Record the GTK variant: retain committed GTK for only subsequent-change attribution, or coordinator restores only the two original GTK bytes/pins first for combined evaluation; preserve all identity/pan/native changes.'
    elif phase['order']==6:
        phase['requires'].append('After/before claims must match the recorded GTK baseline variant; retaining optimized GTK on both sides cannot measure GTK benefit.')
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text_path=OUT/'OFFLINE_WIDE_RECOVERY_PLAN.txt';text=text_path.read_text(encoding='utf-8')
(OUT/'OFFLINE_WIDE_RECOVERY_PLAN.before_reported_e494.txt').write_text(text,encoding='utf-8')
notice='''最新协调消息补记（本地记录，无板端查询）
CPU窗口已结束并归还登记对话。报告称GTK两源+pins已提交至e49436a8ada938c071b484ac04302134ac29420172457da6a2c544c841d77217，原GUI因Date sample_rtt_exceeded两次启动失败；无after，不能声称整板CPU收益。相机候选未部署，camera1332未停；登记对话继续clock恢复与入口拆分。轴/平台保持冻结。

基线方案须按新事实修订：若保留这版GTK，后续wide before/after只能归因到随后新增改动（如相机），不能测出GTK收益。若要测GTK+相机组合收益，应由协调者在合法维护窗口只恢复这两个GTK原字节与相应最新pins，保留身份/轴/native改动，再建立原GTK的wide before，之后发布组合并测matched after。现在不安排回滚或板端动作。
原before是a6d benchmark 40s/82.591%，仅有before；不同平台基线及旧903c数字不用于wide优化的因果对比。以下原规划中的“候选未部署”视为历史前提，阶段E/F执行前以本段选择并记录的GTK版本为准。

'''
text_path.write_text(notice+text,encoding='utf-8')
current_path=D/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes()
(OUT/'AXIS_CURRENT_HANDOFF.before_reported_e494.json').write_bytes(old)
current=json.loads(old)
current['latest_coordination_report']=event
current['offline_wide_recovery_preparation']['latest_update_host_utc']=stamp
current['offline_wide_recovery_preparation']['gtk_baseline_variant_note']=str(p)
current['next_action']='Remain frozen. Identity chat owns clock recovery and enrollment-entry split. Await explicit maintenance handback and protected current-owner normal-stop/fresh-final proof, then coordinate original wide recovery. Record GTK baseline variant before matched wide CPU measurements.'
tmp=current_path.with_name('.'+current_path.name+'.reportedgtk.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
coord_path=D/'cpu_optimization_20261102/AXIS_COORDINATION_HANDOFF.json'
if coord_path.exists():
    old=coord_path.read_bytes();(OUT/'AXIS_COORDINATION_HANDOFF.before_reported_e494.json').write_bytes(old)
    coord=json.loads(old);coord['latest_coordination_report']=event
    coord_path.write_text(json.dumps(coord,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(record=str(p),axis_platform_frozen=True,board_queries=0,board_actions=0,
    reported_startup_sha256=event['reported_startup_sha256'],overall_cpu_benefit_claimed=False,
    measured_axis_state_fields_preserved=True),ensure_ascii=False,indent=2))
