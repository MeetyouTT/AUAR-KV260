import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;DELIVERY=HERE.parents[1]
fresh=json.loads((HERE/'FRESH_NEW_BOOT_ASSESSMENT.json').read_text(encoding='utf-8'))
supplement=json.loads((HERE/'OWNER_AND_RELEASE_SUPPLEMENT.json').read_text(encoding='utf-8'))
v=fresh['board_result'];s=supplement['board_result'];pan=v['gui']['manual_pan']
assert v['boot_id']==s['boot_id']=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert v['startup_stable'] and s['startup_unchanged'] and v['startup_sha256_after']==s['startup_sha256']
assert not v['bad_components'] and not v['bad_controller_files'] and not v['board_mutations']
assert pan['automatic_following'] is False and not v['follow_processes']
assert pan['state']=='FAULT' and pan['readback'] is None
owners=[]
for owner in s['gui_family']+v['owners']:
    if not any(p['pid']==owner['pid'] for p in owners):owners.append(owner)
manual=v['pan_component_pins']['config/pan_manual.local.json']['config']
blockers=[
    dict(id='PL_VART_FDT_MISMATCH',observed=v['platform'],
        required='Original aura-visual-servo-b4096-wide-v1 firmware/overlay/VART set verified together in a coordinated future maintenance window.'),
    dict(id='OLD_BOOT_MANUAL_AND_FOLLOW_BINDINGS',manual_boot=manual.get('boot_id'),manual_fdt=manual.get('fdt_sha256'),
        follow_context=v['axis_context'],evidence=v['evidence'],
        required='Rebuild current-boot context/manual release/direction and human evidence through the original workflow; compare-and-swap current pan pins only after actual platform verification.'),
    dict(id='CURRENT_BOOT_REFERENCE_AND_DIRECTION_NOT_VALIDATED',current_readback=None,
        old_boot_pulse_or_stop_receipt_usable=False,
        required='After original joint-platform restore, execute original ID/STOP-only proof, establish the actual current stopped reference and bounded direction observation before any follow. No automatic reuse of old pulse width or current-boot measured=true claims.'),
    dict(id='LIVE_CAMERA_OWNS_VART_RENDER',camera_pid=v['camera'].get('pid'),
        camera_owner=next(o for o in owners if o['pid']==v['camera'].get('pid')),
        required='GUI/camera must be normally released by their current maintenance owner before any DFX. Preserve latest native checkpoint/seed/counters/marker; never replay a sealed old-boot checkpoint over current state.'),
    dict(id='FACE_READBACK_DEPENDS_ON_ACTUAL_CAMERA_OWNER',selected=v['selected_face_readback'],
        required='If future maintenance changes camera owner/run, rebind the latest selected source-pin set via the original verifier and current startup closure. Preserve identity fixes and fresh CPU candidate changes; do not restore the old 25-pin binding.'),
    dict(id='COORDINATION_FREEZE_ACTIVE',
        required='Identity registration and CPU maintenance retain GUI/camera/DFX ownership. Dedicated axis chat waits for explicit bilateral maintenance completion and a bounded retest window.'),
]
technical=dict(schema='aura-axis-new-boot-technical-handoff-1',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    observed_host_utc=fresh['host_utc'],owner_supplement_host_utc=supplement['host_utc'],
    status='FROZEN_NEW_BOOT_PLATFORM_INCOMPATIBLE_NO_MMIO_READBACK',boot_id=v['boot_id'],owners=owners,
    startup_sha256=v['startup_sha256_after'],components_verified=v['components_count'],
    controller_root=v['controller_root'],controller_manifest_sha256=v['controller_manifest_sha256'],
    controller_files_verified=v['controller_file_count'],pan_component_pins=v['pan_component_pins'],
    platform=v['platform'],compatibility=v['compatibility'],gui=v['gui'],camera=v['camera'],
    current_boot_register_stop_verified=False,hardware_flags=None,hardware_lease_left_ms=None,
    follow_running=False,axis_frozen=True,
    preserved_targets=dict(left=.4,right=.45,tolerance=.03,rearm_stability_ms=150,left_camera_trigger=.05,right_camera_trigger=.8064720153808593),
    current_zone=v['zone'],current_selected_face_readback=v['selected_face_readback'],
    source_release=s['original_release'],native_execution_config_metadata=s['current_camera_run'],
    blockers=blockers,required_future_sequence=[
        'Wait for identity and CPU owners to finish; coordinate a single maintenance window and capture fresh active sources, current startup and pan pins.',
        'Normally stop GUI and necessary camera owners through the existing paths; confirm no live VART/render/MMIO owners before original-client DFX.',
        'Restore the original wide platform through the original client; verify actual boot/FDT/firmware/VART/overlay/ZOCL pairing, without changing native recovery state.',
        'Run original ID_STOP_ONLY and create fresh measured platform context; use the original bounded initialization/direction procedure with observation to establish current-boot reference and direction.',
        'Apply a minimal versioned binding transaction against the latest startup; retain stable150 control25, left40/right45, current identity sources and approved CPU changes.',
        'Restore GUI/camera with current native checkpoint lifecycle and verified fresh selected source-pin closure; recheck trusted clock through the original guard.',
        'Dedicated axis owner performs coordinated bounded original-UI follow start/STOP; CPU owner only samples real dialogue plus 60-120s follow. Save actual new-boot STOP proof and user feedback.'
    ],
    board_wall_time_authority=False,board_wall_utc_diagnostic_only=v['board_wall_utc_untrusted'],
    timestamp_basis='Host UTC; board wall clock is 2021 and is not used as current-date authority. Original GUI HTTP-Date anchor policy is unchanged.',
    this_assessment=dict(board_mutations=False,axis_commands=0,services_changed=False,dfx_changed=False,
        source_config_changed=False,checkpoint_seed_counter_marker_read_or_changed=False,private_content_exported=False),
    evidence=dict(fresh=str(HERE/'FRESH_NEW_BOOT_ASSESSMENT.json'),owners_and_release=str(HERE/'OWNER_AND_RELEASE_SUPPLEMENT.json')),
    scope='Read-only technical assessment. No restoration, publication, STOP/ARM/COMMIT, reference setting, or motion performed.')
technical_path=HERE/'NEW_BOOT_TECHNICAL_HANDOFF.json'
technical_path.write_text(json.dumps(technical,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
note='''新 boot 转轴只读技术交接（洛杉矶2026-11-02）

仍冻结转轴开启和发布。未触碰GUI/相机/DFX维护权；本轮0板端动作、0轴命令、0配置或源文件修改，也未读取或修改native检查点、seed、计数和marker，未导出私有内容。

主机11:25:18 UTC实读boot a6d4a069-e9b0-4065-8df7-dc23556b168e。当前startup 9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a；380项组件匹配。GUI supervisor2142/birth76636，GTK2151/birth76768；相机1332/birth2236。完整命令指纹见JSON。

实际固件kv260-benchmark-b4096.bit.bin，VART和overlay也为benchmark；FDT ed0e2ace1f5bda2b937a61f5f8a5ef05cf01065a24627b23ca2de6614948542f。原转轴要求wide组合，当前不匹配。相机1332仍加载原VART/native operator并持renderD128，当前不能执行DFX。

原stable150控制root和25文件完整，manifest仍9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9。左停点.40、右.45、稳定恢复150ms参数保持。pan_manual boot/FDT、follow context、direction与human evidence均仍是903c旧boot；不能只改boot字段直接运动，也不能恢复旧1492us或把旧方向实测写成本boot通过。

GUI当前跟随false，转轴FAULT，pulse/readback均null。仅确认无跟随进程和原保护失配；本boot没有新鲜寄存器STOP回读，不能填写flags0/lease0。旧903c STOP仅历史。

边界editor当前1471已按原行为生成a6d4 zone，左右几何保持；zone SHA已变为9f227159bf3d0e1d16e16f0d63377a40c37897029274bf029f656b5815c5e2bd，后续应新鲜核对，不能硬用旧815f。身份26pin现99c53c59，run b9656e，全部source pin匹配；未来若换相机PID/run，应通过原verifier重绑最新闭包，不回退旧25pin或覆盖登记/CPU优化新源。

后续顺序：先等身份登记及CPU维护完成并明确交还维护窗口；正常释放GUI/相机及VART/render owner后，沿原client成套恢复wide并核实际FDT/固件/VART/overlay/ZOCL；原ID_STOP_ONLY、新context、当前停止参考与有界方向观察；按最新startup/pan pins版本化更新绑定，保留原控制25与最新身份/CPU改动；原native生命周期恢复相机/GUI、重新核选用source闭包和原时钟guard；最后由唯一轴owner有界开启/STOP，root只读采样。不得重放旧封存seed或重写计数/marker。

板墙钟2021仅诊断，技术交接使用主机UTC；未修改墙钟或原HTTP-Date可信锚策略。
'''
(HERE/'NEW_BOOT_TECHNICAL_HANDOFF.txt').write_text(note,encoding='utf-8')
current_path=DELIVERY/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes()
(HERE/'AXIS_CURRENT_HANDOFF.before_new_boot_assessment.json').write_bytes(old)
current=json.loads(old)
historical=dict(boot_id=current.get('boot_id'),observed_utc=current.get('latest_observation_utc'),
    readback=current.get('latest_observed_readback'),last_report=current.get('last_report'),last_report_result=current.get('last_report_result'))
current.update(status=technical['status'],updated_utc=technical['host_utc'],boot_id=v['boot_id'],owners=owners,follow_processes=[],
    startup_sha256=v['startup_sha256_after'],current_release=v['controller_root'],controller_manifest_sha256=v['controller_manifest_sha256'],
    face_config_sha256=v['pan_component_pins']['config/pan_face.local.json']['actual_sha256'],
    latest_observation_utc=fresh['host_utc'],latest_observed_following=False,latest_observed_pan_state='FAULT',
    latest_observed_readback=None,ui_page=v['gui'].get('ui_page'),runtime_fault_count=v['gui'].get('runtime_fault_count'),
    previous_boot_stop_historical_only=historical,last_report=None,last_report_status='NO_CURRENT_BOOT_AXIS_REPORT',last_report_result=None,
    current_boot_stop_verified=False,current_platform=v['platform'],binding_compatibility=v['compatibility'],
    new_boot_technical_handoff=str(technical_path),pan_component_pins={k:r['actual_sha256'] for k,r in v['pan_component_pins'].items()},
    current_zone_sha256=v['zone']['sha256'],current_face_readback=v['selected_face_readback'],
    next_action='Remain frozen; identity and CPU maintenance owners retain GUI/camera/DFX. After explicit bilateral handback, follow the original joint-platform recovery and new-boot ID/STOP/reference/direction validation before bounded follow.')
current['coordination_freeze'].update(axis_publication=True,follow_start=True,current_turn_axis_commands=0,
    old_stop_proof_current=False,current_boot_register_readback=None,technical_handoff=str(technical_path),
    resume_condition='After identity registration and CPU maintenance, explicit bilateral coordination and fresh actual platform/owner/pin checks.')
tmp=current_path.with_name('.'+current_path.name+'.newboot.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
coord_path=DELIVERY/'cpu_optimization_20261102/AXIS_COORDINATION_HANDOFF.json'
if coord_path.exists():(HERE/'AXIS_COORDINATION_HANDOFF.pre_reboot_historical.json').write_bytes(coord_path.read_bytes())
coord=dict(schema='aura-axis-cpu-coordination-handoff-2',host_utc=technical['host_utc'],observation_host_utc=fresh['host_utc'],
    status=technical['status'],boot_id=v['boot_id'],startup_sha256=v['startup_sha256_after'],owners=owners,
    controller_root=v['controller_root'],controller_manifest_sha256=v['controller_manifest_sha256'],
    pan_component_pins=current['pan_component_pins'],gui=v['gui'],platform=v['platform'],compatibility=v['compatibility'],
    axis_commands_this_turn=0,board_mutations=False,freeze=dict(axis_publication=True,follow_start=True),
    current_boot_flags=None,current_boot_lease_left_ms=None,current_boot_stop_verified=False,
    old_903c_stop_proof='Historical only; archived in the technical handoff directory.',
    technical_handoff=str(technical_path),latest_axis_handoff=str(current_path),
    maintenance_owner='Identity chat currently owns GUI/camera recovery and registration; CPU root resumes after coordination. Axis chat does not compete for GUI/camera/DFX.',
    retest_owner='Dedicated axis chat retains sole axis start/STOP; no motion before original new-boot recovery and coordinated handback.')
coord_path.write_text(json.dumps(coord,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=technical['status'],technical_handoff=str(technical_path),boot_id=v['boot_id'],
    firmware=v['platform']['firmware_name'],following=False,pan_state='FAULT',current_boot_stop_verified=False,
    components=380,control_files=25,board_mutations=False,axis_commands=0),ensure_ascii=False,indent=2))
