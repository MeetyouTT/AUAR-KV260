"""Local metadata/provenance only. Does not import SSH, board, native or app clients."""
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath

HERE=Path(__file__).resolve().parent;MAINT=HERE.parent;D=MAINT.parent
OUT=HERE/'offline_wide_restore';OUT.mkdir(exist_ok=True)
ORIGINAL=D/'axis_follow_restore/original_sources'
CONTROL=MAINT/'left_stop40_20261102/recovery_stability_20261102_v3'
ROOT='/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154'
EXPECTED_MANIFEST='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
    p=OUT/name
    assert not p.exists(),'Preserve previous offline preparation'
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return p

scripts=[
 ('checkpoint_preflight',MAINT/'checkpoint_review/collect_current_prestop_readonly.py','Read-only pre-stop source/owner and public counter lower-bound recipe; historical pins need fresh inputs.'),
 ('normal_camera_stop',MAINT/'stop_original_camera.py','Original normal stop and final checkpoint presence; camera PID, lower bounds, startup and boot are historical.'),
 ('original_checkpoint_reader',D/'parallel_platform_review/checkpoint_readonly_call_recipe.py','Original read/validation recipe; adapt only fresh metadata arguments and retain all original validation semantics.'),
 ('complete_final_archive_validation',MAINT/'checkpoint_review/validate_current_final_complete_readonly.py','Full final/archive/cumulative validation; historical archive head/counts cannot be assumed for the new boot.'),
 ('seal_platform',MAINT/'seal_and_read_platform.py','Original exact-byte sealing and owner absence pattern; use actual new final, not old c6c8 final.'),
 ('remove',MAINT/'launch_original_remove.py','Existing systemd single-job supervision of the original DFX client; old boot/PID/startup/checkpoint/unit are invalid as current inputs.'),
 ('remove_readback',MAINT/'read_original_remove_result.py','Read same existing unit/result, exact reply and actual unload; no retry. Old InvocationID/PID are historical.'),
 ('load',MAINT/'launch_original_load.py','Original client loads original wide; verify 4 firmware + 3 driver pins. No new firmware/controller.'),
 ('load_readback',MAINT/'read_original_load_result.py','Exact client completion plus actual wide platform, VART, overlay and ZOCL; loader suffix is not fixed.'),
 ('id_stop_launch',MAINT/'launch_original_idstop.py','Fresh measured context then original ID_STOP_ONLY; historical load unit/InvocationID must be replaced by actual receipt.'),
 ('id_stop_program',ORIGINAL/'c9e91f74336c__bench_identity_stop.py','Original program: ID/ABI/build plus STOP only; no ARM/COMMIT/BIND/REFERENCE.'),
 ('protected_camera_restore',MAINT/'verify_idstop_start_camera.py','Original ID/STOP verification and normal camera start; fresh checkpoint consumption by original bootstrap, no seed rewrite.'),
 ('current_boot_pan_binding',MAINT/'reconnect_original_axis_config.py','Original versioned pan configuration transaction pattern. Preserve latest stable150/left40/right45 and current identity/CPU pins. Old copied quotes and direction claims are not new observations.'),
 ('face_binding_precheck',MAINT/'gui_binding_review/collect_gui_binding_precheck25.py','Original selected-source verifier pattern only; currently 26 pins, future count/set must come from fresh owner and approved sources.'),
 ('finite_initialization',ORIGINAL/'f23952abb189__bench_finite_step_deadline_fix.py','Existing 2s original finite entry; 1400..1600 commands, delta1..5us; initial may move from unknown physical position. Conditional, not scheduled by this plan.'),
 ('historical_80us_observation',ORIGINAL/'3538bef64957__bench_observed_80us_6s.py','Existing 80us/6s entry inventory only. Not default/mandatory; historical 20US label does not qualify as observed20 proof.'),
 ('manual_qualification',ORIGINAL/'ff0af06e7c90__manual_vsrv.py','Original release qualifications and exclusive register owner semantics.'),
 ('rated_range_qualification',ORIGINAL/'0124da5d3d82__rated_range_release.py','Original rated-range authorization plus actual current-boot platform proof. No fabricated observations.'),
 ('manual_live_base',ORIGINAL/'e0ed84cb0639__manual_live_config.py','boot/FDT/face config path are GUI base guards; changing those requires normal GUI restart, not reconnect-only.'),
 ('original_ui_handoff',ORIGINAL/'3ebb1b32368c__face_pan_controls.py','Original manual.close -> follow child -> confirmed exit -> manual reopen ownership handoff; follow command is toggle.'),
 ('latest_control_entry',CONTROL/'candidate/run_face_motion.py','Current stable150 original entry; optional left target and recovery gate; native original driver/limits retained.'),
 ('latest_target_core',CONTROL/'candidate/continuous_face_control.py','Current left40/right45 latching plus optional recovery parameter validation.'),
 ('latest_session',CONTROL/'candidate/continuous_session.py','Current original ARM/TTL/semantic-intent path plus recovery stability gate.'),
 ('unchanged_hardware_slew',CONTROL/'candidate/hardware_slew_session.py','Original 4us/20ms hardware slew and immediate protective stop unchanged.'),
 ('source_diagnostics',CONTROL/'candidate/run_input_diagnostics.py','Current verified original numeric face-stream diagnostics. The older prefixed archive copy has a byte hash mismatch and is excluded; no diagnostics run here.'),
]
catalog=[]
for role,p,notes in scripts:
    assert p.is_file(),str(p)
    data=p.read_bytes();ast.parse(data.decode('utf-8'))
    record=dict(role=role,local_path=str(p),sha256=sha(p),bytes=len(data),syntax_parsed_only=True,
                executed=False,notes=notes)
    prefix=p.name.split('__',1)[0]
    if '__' in p.name and len(prefix)==12:
        record['archived_filename_hash_prefix_matches']=record['sha256'].startswith(prefix)
        assert record['archived_filename_hash_prefix_matches']
    catalog.append(record)
original_manifest_path=ORIGINAL/'6a4b645a5bbf__candidate-manifest.json'
assert sha(original_manifest_path)=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
original_manifest=json.loads(original_manifest_path.read_bytes())
assert len(original_manifest['runtime_files'])==4 and len(original_manifest['payload_files'])==3
cached_payload={
 'vsrv_driver.py':ORIGINAL/'4f48ad87fdf6__vsrv_driver.py',
 'vsrv_transport.py':ORIGINAL/'97f1ff27bd3e__vsrv_transport.py',
 'libvsrv.so':CONTROL/'candidate/libvsrv_batch.so',
}
payload_records=[]
for name,p in cached_payload.items():
    assert sha(p)==original_manifest['payload_files'][name]
    payload_records.append(dict(board_release_name=name,local_cached_path=str(p),sha256=sha(p),
        note='Cached batch-library filename has identical bytes; future board entry still uses original release/driver/libvsrv.so.' if name=='libvsrv.so' else 'Original cached driver source.'))
review=json.loads((CONTROL/'INDEPENDENT_REVIEW.json').read_bytes())
control_records=[]
for r in review['records']:
    p=CONTROL/'candidate'/r['file'];assert sha(p)==r['after']
    control_records.append(dict(relative=r['file'],local_path=str(p),sha256=sha(p),bytes=p.stat().st_size))
assert len(control_records)==25
prior_manifest=MAINT/'left_stop40_20261102/before/deployment-manifest.json'
control_manifest=copy.deepcopy(json.loads(prior_manifest.read_bytes()))
old_root=PurePosixPath('/home/root/aura-pan-wide-20261028/control-10282601-target45-9adb90c3')
by_name={r['relative']:r for r in control_records}
for f in control_manifest['files']:
    rel=str(PurePosixPath(f['destination']).relative_to(old_root));record=by_name[rel]
    f.update(destination=str(PurePosixPath(ROOT)/rel),sha256=record['sha256'],bytes=record['bytes'])
control_manifest['scope']+='; optional left stop target latched by original trigger side; left 0.40 / right 0.45'
control_manifest['scope']+='; Python 3.9 compatible Optional annotation; decision logic unchanged'
control_manifest['scope']+='; opt-in 150ms and 3 admitted images plus new detection before rearm after protective interruption; original STOP/TTL/lease unchanged'
encoded=(json.dumps(control_manifest,sort_keys=True,indent=2)+'\n').encode()
assert hashlib.sha256(encoded).hexdigest()==EXPECTED_MANIFEST
manifest_copy=OUT/'CONTROL25_MANIFEST_RECONSTRUCTED_OFFLINE.json';assert not manifest_copy.exists();manifest_copy.write_bytes(encoded)
excluded_diagnostic=ORIGINAL/'e273e800d722__run_input_diagnostics.py'
excluded_record=dict(path=str(excluded_diagnostic),actual_sha256=sha(excluded_diagnostic),expected_prefix='e273e800d722',
    disposition='Excluded from trusted source catalog; current control25 run_input_diagnostics.py has the verified e273 full hash. Original archive bytes retained unchanged.')
catalog_path=write('SCRIPT_AND_CLOSURE_CATALOG.json',dict(schema='aura-wide-recovery-offline-catalog-1',
    mode='LOCAL_FILES_ONLY_NO_REMOTE_EXECUTION',scripts=catalog,original_release=dict(
        board_root='/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c',
        local_manifest=str(original_manifest_path),manifest_sha256=sha(original_manifest_path),
        runtime_files_expected_pins=original_manifest['runtime_files'],driver_payload_expected_pins=original_manifest['payload_files'],
        cached_payload_verified=payload_records,board_runtime_files_rehashed_this_turn=False),
    stable150_control=dict(board_root=ROOT,manifest_sha256=EXPECTED_MANIFEST,local_reconstructed_manifest=str(manifest_copy),
        local_manifest_sha_matches_last_published_receipt=True,files=control_records),
    historical_templates_executable_as_is=False,no_board_queries_or_mutations=True,excluded_archive_copy=excluded_record))
phases=[
 dict(order=0,name='Registration idle handoff',owner='Identity chat -> CPU coordinator',
      requires=['Human registration/ASR confirmation repair finished or explicitly idle; no active sampling, recording, playback or pending dialogue work.',
                'Latest complete startup SHA/pins and approved identity source changes, including announced f507 generation, captured at handoff; do not reuse 9a9a/680f/1177.',
                'GUI/camera/listening maintenance ownership explicitly handed back. No template/voiceprint/name/content export.']),
 dict(order=1,name='Protected normal stop',owner='Current GUI/camera owner under CPU coordination',
      requires=['Original GUI and necessary camera services normally stop, no pending Job and no forced kill; actual old owners confirmed exited.',
                'New actual a6d final checkpoint is created by original shutdown; source PID/birth and captured mono timestamp match the stop intent.',
                'Original full reader plus full archive/cumulative recovery/feature counter validation against pre-stop lower bounds; exact bytes preserved and sealed on board; original pointers and consumption markers untouched.',
                'No live VART/native/MMIO/render/DPU owners and no unreadable live process; native final validation and ownership evidence handed to axis owner.']),
 dict(order=2,name='Original platform restore',owner='Dedicated axis/platform operator after explicit handback',
      requires=['Fresh actual boot/startup/pan pins/client/daemon identities and exact current final sealed bytes. New unique transaction and units; no old903c action replay.',
                'Original client remove slot0 once; same-unit completion plus exact original reply and actual overlay/ZOCL/render teardown verified.',
                'Original client load original wide once; 4 FW + 3 driver hashes, dynamic firmware/overlay identity/ZOCL/render and exact VART verified; raw completion outputs retained.',
                'No automatic retry on unknown outcome. Current actual FDT SHA measured and bound; no assumption it must equal old d68 or change during DFX.']),
 dict(order=3,name='Fresh ID/STOP and protected camera restore',owner='Axis verifies ID/STOP; CPU/maintenance owner restores camera after explicit phase handback',
      requires=['Original ID_STOP_ONLY on actual wide before camera restarts; ID0x56535256 ABI2 build0x10282601, flags0/lease0, ARM/COMMIT/BIND/REFERENCE false.',
                'This proves register stop, not physical center/direction. No reuse of old1492us as a new physical reference.',
                'Camera original bootstrap consumes the latest actual normal-stop final through its existing lifecycle. No old c6c8 restore, seed/counter/marker rewrite or relaxed validation.',
                'Capture fresh camera PID/birth/run/epochs and selected face source-pin closure from latest approved sources. Current historical selected26 is a reference, not a hardcoded future pin set.']),
 dict(order=4,name='New-boot bounded reference/direction and pan transaction',owner='Dedicated axis owner; GUI manual lock must be released',
      requires=['Observed original bounded procedure establishes current-boot reference/direction as needed; initial pulse is explicitly chosen from actual physical circumstances, never reset1500 assumed as measured center.',
                'Existing 2s and 80us/6s tools are capability inventory only; this plan schedules no movement and no automatic round trip.',
                'Version only required current-boot pan context/release/evidence/pins against latest full startup, preserving left40/right45/stable150, latest identity fixes and selected-source closure.',
                'CPU/GUI owner normally restarts GUI once for changed manual boot/FDT base, verifies new owners/clock and READY stopped. pan_stop stops output but does not release the manual lock; external bench needs normal close.']),
 dict(order=5,name='Same-wide baseline before CPU candidates',owner='CPU coordinator samples; dedicated axis owner alone starts/stops bounded follow',
      requires=['Remain same actual kernel boot and verified wide platform; original current identity sources plus unoptimized camera/GTK establish the new baseline.',
                'Match camera format/capture/preview settings, UI page, model/service config, microphone/playback/follow workload and performance sampling method.',
                'Use the coordinated two real dialogue rounds plus 60-120s original follow; store timing/counters only. Original UI start exactly once after fresh READY/followfalse/flags0/lease0; bounded duration or explicit original STOP.',
                'Save actual final STOP proof and numeric input timing/interruptions/gate events; no old903c or a6 benchmark sample used as the causal before measurement.']),
 dict(order=6,name='CPU candidate publication and matched after',owner='CPU coordinator owns candidate transaction; axis owner retains motion control',
      requires=['Axis STOP confirmed and follow off before service publication. Protected camera normal-stop/final lifecycle repeated only if camera candidate needs it; GTK-only change does not itself require camera stop.',
                'Apply approved candidate diffs against fresh sources/pins; preserve pan bytes/control25/new-boot evidence and latest registration fix; restore fresh camera owner/source closure and GUI.',
                'No reboot or DFX between baseline and after. Repeat matched workload and same measurement method on the same wide platform. If boot/platform changes, start a new matched comparison.',
                'No repeated physical initialization merely for a GUI/camera restart while same FPGA/boot/reference remains valid; always fresh register readback and owner checks.']),
]
plan=dict(schema='aura-offline-wide-recovery-and-cpu-test-plan-1',generated_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    mode='OFFLINE_PLANNING_ONLY',ready_to_execute=False,axis_publication_and_motion_frozen=True,
    board_queries_this_turn=0,board_actions_this_turn=0,ssh_calls_this_turn=0,
    context=dict(target_boot_from_last_observation='a6d4a069-e9b0-4065-8df7-dc23556b168e',
        last_board_observation_host_utc='2026-11-02T11:25:18.354332+00:00',
        last_observed_platform='kv260-benchmark-b4096; pan FAULT/followfalse/readbacknull',
        coordination_update='Registration owns GUI/camera/listening; announced startup prefix f507; CPU candidates uninstalled. These are relayed facts, not new board verification.'),
    catalog=str(catalog_path),phases=phases,
    retained_axis=dict(root=ROOT,manifest_sha256=EXPECTED_MANIFEST,left_target=.4,right_target=.45,tolerance=.03,
        rearm_stability_ms=150,hardware_step_us=4,hardware_frame_ms=20,image_ttl_ms=250,anchor_ttl_ms=500),
    original_client=dict(path='/usr/bin/dfx-mgr-client',historical_sha256='a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7',
        remove_argv=['/usr/bin/dfx-mgr-client','-remove','0'],load_argv=['/usr/bin/dfx-mgr-client','-load','aura-visual-servo-b4096-wide-v1'],
        exact_remove_success_stdout='remove from slot 0 returns: 0 (Ok)\n',
        exact_load_success_stdout='aura-visual-servo-b4096-wide-v1: loaded to slot 0\n',
        caveat='Client returncode0 and daemon reply0 are insufficient without actual paired platform teardown/load verification; preserve original daemon/ZOCL repair.'),
    unresolved_fresh_inputs=['Registration idle and ownership handback','Full latest startup and source pin set after identity repair',
        'Protected normal-stop new final/archives/counter proof and actual old owners exited',
        'Fresh daemon/client/boot and zero hardware owners','Actual post-wide platform context and original ID/STOP proof',
        'Observed current-boot reference/direction as required','New camera/GUI owners and selected-source closure','Same-wide before/after performance windows'],
    no_auto_authorization='This local plan does not authorize or dispatch any board query, stop/start, DFX, checkpoint operation or motion. Wait for explicit coordinated handback.',
    cpu_attribution=dict(same_boot_required=True,same_wide_platform_required=True,
        historical_903c_82_5_percent_baseline_usable_for_causal_before_after=False,
        a6d_benchmark_baseline_usable_for_wide_cpu_before_after=False,reset_comparison_if_platform_or_boot_changes=True),
    fdt_scope='Flat /sys/firmware/fdt may remain unchanged across an overlay switch. Bind its actually measured SHA but verify dynamic firmware/overlay/VART/ZOCL together; never substitute old d68 or require a hash change.',
    source_and_private_state_preservation='No new controller/firmware; no native checkpoint/seed/counter/marker fabrication or restore from old snapshot; preserve live identity library and current source fixes; all new records numeric/code metadata only.')
plan_path=write('OFFLINE_WIDE_RECOVERY_PLAN.json',plan)
text='''原 wide 恢复与 CPU 同平台复测：纯离线编排

本轮仅本地读源码、AST解析、计算哈希和整理文档；0 SSH、0板端查询、0停启/DFX/轴操作。保持冻结。登记对话当前持GUI/相机/聆听权，CPU root协调，轴对话不竞争维护权。f507为对方最新消息，不是本轮实读。当前物理状态仍引用11:25的a6d/benchmark/FAULT/null快照。

已核可复用链路
1. checkpoint_review/collect_current_prestop_readonly.py + stop_original_camera.py + 原checkpoint reader/complete final archive validator：观察累计下界→原正常停机产生真实final→全量原验证→原字节封存。旧1333/2359、c6c8、18层archive、旧下界均不可填成本次输入；不写seed/计数/marker，不恢复旧snapshot。
2. launch_original_remove.py / read_original_remove_result.py：原dfx-mgr-client -remove 0，原systemd唯一unit托管、独占intent/stdout/stderr、无自动重启；未知结果只读同一unit reconcile。RC0不是成功充分条件，完整stdout和实际overlay/ZOCL/render卸载均须验证。
3. launch_original_load.py / read_original_load_result.py：原client -load aura-visual-servo-b4096-wide-v1，原4FW+3driver闭包；合并核固件名、operating、唯一实际wide overlay、ZOCL父子/derived render、精确VART。不要重启/替换原daemon或手工unbind。
4. launch_original_idstop.py / 原bench_identity_stop.py：真实wide后、恢复相机前，以新实际context做ID_STOP_ONLY；ID/ABI/build和flags0/lease0，ARM/COMMIT/BIND/REFERENCE均false。寄存器复位1500不是实体中点。
5. verify_idstop_start_camera.py、gui_binding_review原verifier和reconnect_original_axis_config.py提供恢复相机、最新source闭包及pan事务的既有模式。所有历史固定boot/PID/startup/InvocationID/旧引用都必须用交接时真实新证据重建；旧脚本不能直接执行。保留最新身份修复、control25、左.40/右.45/stable150。
6. 原有限初始化/观察入口和原UI随动入口均已列目录。2s/1..5us和80us/6s只是已有能力清单，本方案不安排动作或无关往返。初始命令可能从未知实体位置运动，应在必要观察阶段按实际姿态选定。20US误标签不能把80us报告变成20us资格。

FDT关键判据
/sys/firmware/fdt可能是基底flat blob，切换overlay后不保证SHA变化。后续绑定实际测得的新context SHA，同时核动态固件/overlay/VART/ZOCL；不能硬套旧d68，也不能把“SHA没变”单独当失败。

交接顺序
A 登记对话：真人确认修复结束或明确idle；无采样/录音/播放/待处理对话；完整最新startup/source pins交给CPU root。私库保持原地，不导出身份内容。
B 当前GUI/相机维护者：正常停GUI和必要相机，交付新boot真实final、原全量reader+归档+累计下界验证及无owner/Job凭证。CPU root收到后再明确把平台窗口交给轴对话。
C 轴对话：唯一平台/轴写入者，分阶段原remove→实际卸载→原load→成套wide读回→原ID_STOP_ONLY。CPU root不并发改平台。
D 约定阶段交还CPU/GUI维护者按原native生命周期恢复相机，核新PID/run及最新选用source闭包；轴对话按需做本boot原有界参考/方向观察和最新pan事务。GUI原manual base变boot/FDT后须正常重启一次；pan_stop只停输出，不释放手动锁，外部bench需正常close。
E 先保持CPU候选未部署，在同a6d、同wide、当前身份代码和原相机/GTK上采新before。root采样，轴对话唯一有界开启/STOP；两轮真人对话和60–120秒原跟随按同窗约定记录数值。
F 轴STOP确认后，CPU root按原事务发布候选；相机改动需要再一次受保护正常stop/final生命周期，GTK-only不因此强制停相机。保留新pan和control25、最新身份修复、原保护。仍同boot同wide，按同页面/输入规格/显示/模型配置/负载/采样法做after。期间不重启板卡或切平台；若变化则重建比较。仅GUI/相机重启且原PL/reference有效时，不为重复测量再初始化实体；仍须新鲜owner和寄存器核验。

CPU归因边界
旧903c的82.5%只作历史参考；a6d benchmark也不能作为wide后CPU优化的因果before。before必须在wide恢复后、候选安装前；after保持同一次boot、同wide、匹配场景和同一计量方法。回执应同时给出实际帧率/源龄、丢帧/错误、全流程ACK、跟随中断与STOP，不能只看CPU下降。

本地闭包核验
原candidate-manifest 6a4b…原字节匹配；3driver缓存字节匹配manifest；当前stable150的25项缓存逐一匹配，并离线重建manifest得到9cd35b96…与已发布回执一致。4FW只核已封存manifest中的期望SHA，本轮未读板端/固件文件，执行窗口仍需新鲜全量核验。
旧original_sources中e273前缀诊断副本实际SHA为b81d，不作为权威源使用；本目录选用当前control25内已验证e273原字节，旧副本未改。详细路径/完整SHA/阶段责任与未决输入见SCRIPT_AND_CLOSURE_CATALOG.json、OFFLINE_WIDE_RECOVERY_PLAN.json。本目录没有生成可直接执行的板端新恢复器。
'''
(OUT/'OFFLINE_WIDE_RECOVERY_PLAN.txt').write_text(text,encoding='utf-8')
current_path=D/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes()
(OUT/'AXIS_CURRENT_HANDOFF.before_offline_plan.json').write_bytes(old)
current=json.loads(old)
current['offline_wide_recovery_preparation']=dict(generated_host_utc=plan['generated_host_utc'],plan=str(plan_path),catalog=str(catalog_path),
    board_queries_this_turn=0,board_actions_this_turn=0,ssh_calls_this_turn=0,executable_prepared=False,
    same_boot_same_wide_cpu_comparison_required=True,announced_identity_startup_prefix='f507',announced_not_freshly_verified=True)
current['next_action']='Remain frozen; wait for registration idle, latest-source handoff and protected camera normal-stop proof. Then explicit bilateral platform window and original wide recovery; collect a same-boot same-wide CPU baseline before any CPU candidate publication.'
tmp=current_path.with_name('.'+current_path.name+'.offline.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
print(json.dumps(dict(mode=plan['mode'],ready_to_execute=False,plan=str(plan_path),scripts_catalogued=len(catalog),
    original_manifest_verified=True,cached_driver_payloads_verified=3,cached_control_files_verified=25,
    reconstructed_control_manifest_sha256=EXPECTED_MANIFEST,board_queries_this_turn=0,board_actions_this_turn=0),ensure_ascii=False,indent=2))
