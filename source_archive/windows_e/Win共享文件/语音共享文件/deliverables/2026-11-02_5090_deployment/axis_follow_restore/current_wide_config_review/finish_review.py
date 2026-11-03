"""Seal the read-only review and original command recipes; never board operations."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AXIS = HERE.parent
config = json.loads((HERE / 'CURRENT_AXIS_CONFIG_READONLY.json').read_text(encoding='utf-8'))['board_result']
contract = json.loads((HERE / 'FACE_DIAGNOSTIC_CONTRACT_READONLY.json').read_text(encoding='utf-8'))['board_result']
settings = json.loads((HERE / 'DIAGNOSTIC_SETTINGS.json').read_text(encoding='utf-8'))
source_index = json.loads((AXIS / 'source_index.json').read_text(encoding='utf-8'))
commands = {
    'diagnostic': ['env', 'PYTHONPATH=/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura',
        '/usr/bin/python3', '-B', '/home/root/aura-pan-wide-20261028/control-10282601/run_input_diagnostics.py',
        '--settings', '<root-created-diagnostic-only-settings>', '--output', '<new-exclusive-output>', '--duration', '15'],
    'finite_initialization': ['env', 'PYTHONPATH=/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c',
        '/usr/bin/python3', '-B', '/home/root/aura-axis-priority-20261101-3c94e7a0/bench_finite_step_deadline_fix.py',
        '--execute', '--confirmation', 'OBSERVED_FINITE_2S', '--initial-us', '<current-operator-selected-pulse>',
        '--target-us', '<explicit-target-1-to-5us-away>',
        '--manifest', '/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/candidate-manifest.json',
        '--manifest-sha256', '6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf',
        '--context', '<actual-current-wide-context>', '--output', '<new-exclusive-finite-report>'],
    'direction_roundtrip': ['/usr/bin/python3', '-B',
        '/home/root/aura-axis-priority-20261101-3c94e7a0/bench_observed_80us_6s.py',
        '--execute', '--confirmation', 'OBSERVED_80US_RETURN_6S',
        '--manifest', '/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/candidate-manifest.json',
        '--manifest-sha256', '6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf',
        '--context', '<actual-current-wide-context>', '--expected-state', '<current-boot-complete-stopped-registers>',
        '--output', '<new-exclusive-roundtrip-report>'],
    'finite_follow_after_observation': ['/usr/bin/python3', '-B',
        '/home/root/aura-pan-wide-20261028/control-10282601/run_face_motion.py',
        '--manifest', '/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/candidate-manifest.json',
        '--manifest-sha256', '6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf',
        '--context', '<actual-current-wide-context>',
        '--app-root', '/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura',
        '--direction-evidence', '<actual-current-boot-observed-direction>',
        '--human-evidence', '<current-physical-observation-and-authorized-scope>',
        '--zone-settings', '<current-production-zone-after-root-verification>',
        '--output', '<new-exclusive-follow-report>', '--confirmation', 'FACE_ZONE_CONTINUOUS', '--duration', '25'],
}
summary = {
    'schema': 'aura-original-axis-current-wide-config-review-1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'READ_ONLY_REVIEW_COMPLETE_NO_MOTION_AUTHORITY_CREATED',
    'boot_id': config['boot_id'], 'startup_sha256_observed': config['startup_sha256'],
    'original_controller_files_verified': config['original_control_files_verified'],
    'gui_can_restore_with_original_mechanical_fault': True,
    'original_pan_platform_guard_precedes_native_registers': True,
    'manual_config_current_boot': config['current_boot_manual_binding_valid'],
    'direction_current_boot_observed': config['current_boot_direction_evidence'],
    'zone_current_boot_bound': config['current_boot_zone_binding_valid'],
    'current_platform': config['current_platform'],
    'diagnostic_settings': settings,
    'current_face_source_geometry_verified': contract['filtered_current_packet'],
    'diagnostic_native_timing_integer_allowlist': ['task', 'submitted', 'completed', 'outcome', 'business_ready',
        'result_fresh', 'start_ns', 'native_return_ns', 'release_decision_ns', 'after_unlock_ns'],
    'original_benches': {path: {'sha256': entry['sha256'], 'local_path': entry['local_path']}
        for path, entry in source_index.items() if path.endswith(('bench_finite_step_deadline_fix.py', 'bench_observed_80us_6s.py', 'run_face_motion.py'))},
    'commands_not_executed': commands,
    'physical_requirements': {
        'motor_power_currently_disconnected_by_user': True,
        'installation_unchanged_observation_and_clearance_confirmed': True,
        'finite_initial_pulse_requires_current_operator_selection': True,
        'finite_initialization_may_move_from_unknown_actual_position': True,
        'new_actual_position_or_direction_not_claimed': True,
        'stopped_1500_register_is_not_a_physical_center': True,
    },
    'board_writes_or_service_actions_or_MMIO': False,
    'diagnostic_or_motion_executed': False,
    'new_controller_or_framework_created': False,
    'private_identity_memory_or_image_data_read_or_exported': False,
}
with (HERE / 'REVIEW.json').open('x', encoding='utf-8') as stream:
    json.dump(summary, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''原板端转轴在当前wide平台上的配置审阅（root唯一操作）

结论：原25项控制器完整，当前wide/operating/VART已只读核对。现pan_manual、direction、zone仍绑定旧bebd；不要把旧物理观察改UUID当本次事实。GUI可以先恢复，原机械guard将保持FAULT隔离，不必为了页面启动生成新物理reference。

只读实证
- 当前boot903cfade-b93c-48fa-804e-379be1967313、startup0f2a319a…；原4配置与被选来源均按当前380清单实读核SHA，原25控制器全匹配。
- 新相机79866/birth2265436的motion首包经内存过滤确认640x480、mirrored=true、actual。没有导出target/box/personID/name/图像。
- 原InputTiming只留计数、期限、技术帧号；detector_timing虽然整dict进入报告，原face_timing源码的nested native只允许固定字段的int，其余均为计时/计数。FaceStream.diagnostics只有队列数与等待时间；fatal是异常类型/固定原因。公开源码与过滤首包见FACE_DIAGNOSTIC_CONTRACT_READONLY.json。

GUI为何可先恢复
原ManualPan.work在独立线程中打开ManualVSRV，失败捕获为FAULT。ManualVSRV.__enter__先verify_platform，再构造NativeRegisters；现旧boot与当前boot不同，verify_platform在MMIO前拒绝。FacePanProcess.start又要求manual READY且flags0/lease0，不能从该FAULT自动跟随。正常页面、音频和业务可以恢复；原automatic_following_enabled=true本身不会自动start。
现manual release分支为USER_RATED_RANGE_VSRV2：它只表示用户已授权500..2500软件范围，明示physical_range_verified=false、mechanical_reference_calibrated=false。它的原验证器允许用当前真实ID/STOP、当前boot/FDT与明确范围授权组成新元数据release，并不要求测得机械零；但这不是物理参考或方向通过。root若选择此分支，必须依据当前事实和用户仍有效的原范围授权写新证据，不能复制旧platform_proof或把旧direction写成新观察。暂不需要这一分支即可恢复GUI。

可以现在准备的元数据
1. 当前wide context来自真实boot/FDT/动态FW/VART/成套文件和原ID_STOP；本次FDT仍是base tree，SHA相同不能单独证明overlay加载。
2. 输入诊断专用zone可复用同一未变的GUI/原用户边界几何，绑定已实读新640x480镜像源。已在本机制作face-zone-input-diagnostics-903c.json，SHA见DIAGNOSTIC_SETTINGS.json；只用于输入诊断，不替换生产zone，也不作为运动授权。原纯camera_zone函数本机核映射[0.1,0.80647201538]、内容区[92,112,400,300]。
3. 原方向polarity+1和human-evidence均为旧boot事实。安装未动能支持把它们作为下一次试验的预期，不能填HUMAN_DIRECTION_CONFIRMED到新boot。

15秒只读输入诊断
root先独占新路径保存诊断settings（该落盘由root执行），核原run_input_diagnostics.py SHA e273e800d722b09cf034fc53d21be121f5cacf6f5939577366546c8042493f00及25项来源；保持真实相机owner不变。命令：
env PYTHONPATH=/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura /usr/bin/python3 -B /home/root/aura-pan-wide-20261028/control-10282601/run_input_diagnostics.py --settings <root新建诊断settings> --output <新的独占诊断文件> --duration 15
该原程序只连现有face-stream、做纯软件计算并写报告；1450是数学起点，不是实际脉宽或机械参考。它不导入driver、不取转轴锁、无MMIO/ARM/COMMIT。诊断速度数学与正式hardware_slew有别，结果仅用来分辨新源图/检测锚过期、HTTP/队列和准入原因。

原物理短测入口（仅处方，未执行；完整argv在REVIEW.json）
- 原bench_finite_step_deadline_fix.py SHA f23952abb189e2e826db7f78ff81296a81a4b57c17684258499227d215dc6dc4，--execute --confirmation OBSERVED_FINITE_2S --initial-us <当前操作员选定> --target-us <差1..5us> --manifest <原candidate-manifest> --manifest-sha256 6a4b... --context <本次真实context> --output <新独占report>。需PYTHONPATH指向原release以解析bench_identity_stop。总2秒，初始/目标均1400..1600、lease100ms、期满QUIESCE+STOP；它会真实BIND/REFERENCE/ARM/COMMIT。初始选择会把命令置到该脉宽，可能从未知实物位置转动；不是仅5us的实物安全保证。须先有转轴动力重新接通和现场观察、当前选择事实，不能默认把reset1500当实物中心。
- 原bench_observed_80us_6s.py SHA 3538bef649574da5607aa54ffbfdee5e103fc4f1db1ebb468eade239500b876c，--execute --confirmation OBSERVED_80US_RETURN_6S --manifest ... --manifest-sha256 ... --context <本次context> --expected-state <本次真实完整STOP寄存器> --output <新独占report>。origin取实际stopped.width_us，要求1400<=origin<=1520（origin+80<=1600），完整寄存器逐值相等；1秒origin、3秒origin+80、2秒回origin，然后QUIESCE+STOP。源码最终status误写20US，实际是80us，验收按events/excursion_us=80及用户观察，不能沿用旧expected-state。
- 上述初始化/返回都不测真实角度或机械零。方向必须由当前实际回程和用户面向相机视角的观察记录，源report SHA与本boot关联。原follow会用当前停止命令作相对reference，不需要伪称物理零；须有本次有效方向/人类证据和新zone才可调用原run_face_motion，先用有限--duration 25，不直接持续0模式。

停止接口
原GUI POST /api/command {"type":"pan_stop"}沿原Origin/Host校验直接调用self.pan.stop()。pan_face_follow是toggle而非设置enabled，未知结果时不能反复toggle来停止。原pan_jog仍要求真实GTK输入token，不绕过它。有限试验本身异常/退出都原STOP，不自动retry。

本任务没有板端写入、服务动作、MMIO、锁获取、模型调用、运动或真实身份/记忆库访问。除四份公开源及一个过滤motion元数据包，未新增相机采集/影像导出。现有配置/控制器没有被改动。
'''
with (HERE / 'REVIEW.txt').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps({'report': str(HERE / 'REVIEW.txt'),
                  'report_sha256': hashlib.sha256((HERE / 'REVIEW.txt').read_bytes()).hexdigest(),
                  'settings_sha256': settings['sha256'], 'board_mutations': False}, ensure_ascii=True))
