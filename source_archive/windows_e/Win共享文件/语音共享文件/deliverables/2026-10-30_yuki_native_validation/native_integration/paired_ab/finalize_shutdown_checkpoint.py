"""Validate local evidence and release the character test lease before power-off."""
from pathlib import Path
import datetime, hashlib, json, os, zipfile

ab=Path(__file__).parent
phase=ab.parent
base=phase.parent
coord=base.parent/'2026-10-30_board_owner/coordination'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
evidence=base/'evidence/native_integration/paired_ab'
windows=json.loads((ab/'shutdown-windows-cleanup.json').read_text(encoding='utf-8-sig'))
board=json.loads((evidence/'shutdown-board-check.json').read_text())
assert windows['status']==board['status']=='PASS'
assert not board['owned_processes_remaining']
archive=evidence/'pilot-v1-shutdown-evidence.zip'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==26
    target=evidence/'pilot-v1-shutdown'
    for info in z.infolist():
        rel=Path(info.filename)
        assert not rel.is_absolute() and '..' not in rel.parts
        dst=target/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(z.read(info))
freeze=json.loads((ab/'harness-delivery-nojpeg-v2.json').read_text())
assert all(hashlib.sha256((ab/p).read_bytes()).hexdigest()==h for p,h in freeze['files'].items())

receipt=dict(status='SHUTDOWN_READY_CHARACTER_RESOURCES_RELEASED',at_utc=now,
    temporary_windows_fixture_pid=32652,temporary_windows_fixture_exited=True,
    temporary_port_61584_released=True,production_windows_8796_preserved=True,
    remaining_owned_board_processes=[],uart_opened_by_character=False,
    production_ui_pid=918191,production_supervisor_pid=918139,camera_pid=1333,
    production_preservation_status='PASS',production_component_pins_checked=286,
    formal_resource_suite_started=False,nojpeg_board_control_started=False,
    resource_reduction_proven=False,production_deployed=False,
    local_pilot_archive_crc='PASS',local_pilot_archive_files=26,
    shutdown_executor='business_root_only',character_will_make_no_further_board_calls=True,
    board_wall_clock_untrusted=True,board_report_raw_wall_clock=board['at_utc'])
(ab/'shutdown-checkpoint.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')

text=f'''雪妃替换验证：断电前检查点（Windows UTC {now}）

当前结论
三项技术验证已完成：雪妃专用模型/网格与待机，遮罩和鼻部异常，原生 GTK/EGL 与实际 PCM 时钟及生命周期。
鼻部不合理白块已修复；原素材本身的少量鼻尖高光保留。300 秒原生 GTK 测试约 23.96fps，P99 61.43ms，取消闭嘴约37.33ms。
这证明本角色具备板端替换的技术基础，不证明比现役方案更省资源。生产形象未切换。

资源对比只完成一次短 pilot（每项预热3秒、计量15秒），不是正式重复实验：
                       旧 remote16      新 native16
进程族 CPU 秒/秒          0.2818           0.2384
进程族 PSS MiB            417.89           248.96
整板 CPU 秒/秒            2.4832           2.5096
可见 Mali 内存 MiB          0              32.56
帧率 fps                  15.83            16.03
整板 CPU 未降低，新方案有 GPU 内存成本；GPU busy 节点不更新，利用率必须写 UNKNOWN，不能写0%。
旧方案含诊断 JPEG，新方案不含；已写好仅关闭旧方案 JPEG 的独立控制组，尚未上板执行。
网络节省与板端计算成本分开报告；相机保持原样，pilot 中人脸身份处理计数未增长，不能外推到重人脸负载。

断电收尾已完成
1. 独立 Windows fixture PID32652（创建时间2026-10-30T13:55:55.516926Z）已按脚本/ready/创建时间核验并退出，61584已释放；现役 PID26024/8796 保持。
2. 板端临时 renderer/sampler 剩余0；现役 supervisor918139/UI918191/相机1333 保持。
3. 当前启动配置、启动器、10个运行源码、286项组件 pin、466个固定输入均通过保持审计。
4. pilot 原始26个 JSON/JSONL/log 已下载、CRC验证并展开，实际执行过的5个脚本原版另存 evidence/native_integration/paired_ab。
5. 未开麦、未输出物理音频、未操作机械/固件、未部署生产形象；UART未占用。测试窗口明确释放。
6. 由业务主控聊天统一关板卡和 Ubuntu；本聊天不再发板端命令，不主动关机。
板卡系统日期停留在2021年，保留原始字段并标记不可信；本检查点用 Windows UTC。性能计时用单调时钟。

下次上电后的明确工作
1. 重新申请串行测试窗口，重新采集 boot_id、现役 PID/入口/配置/源哈希和实际渲染模式。旧 boot/PID/端口不能复用。
2. 重启独立旧形象 Windows fixture，核验来源，获得新临时端口并更新 server-proof；绝不对现役8796发送测试渲染。
3. 保留 pilot-v1 及其源清单。NoJPEG v2 源码仅本机冻结，未上板；先复核冻结清单并同步隔离目录。
4. 当前 suite-formal.json 仍是旧8项草案且哈希已过期，禁止直接 --execute。改成12项 A B B A A B B A C B B C，每项预热10秒、测量60秒；A=旧，B=新，C=旧仅禁JPEG。
5. 对最新 telemetry.py/run_suite.py/NoJPEG v2 全部重新签名；analyze_results.py 是未以正式数据验证的草稿。先做一个有界 C 短探针确认 remote16、JPEG0、PCM/暂停/取消正常，再开始约22分钟正式组。
6. 保持同一423×438窗口、16fps、公开PCM/事件、原相机背景，区分冷启动和稳态。报告4组主配对及2组JPEG控制配对的均值、离散与方向。
7. 分别报告整板CPU、进程族CPU、PSS/RSS、Mali内存/利用率未知、帧P95/P99/掉帧、相机计数增量、显示服务CPU和网络。CPU/GPU/内存取舍不能合成一个未经定义的“省资源”。
8. 资源结论交用户决定，不自动切换。旧候选压缩包是技术验证冻结版、配置默认24fps；不能把16fps成本结果当作24fps部署成本证明。

文件入口
native_integration/README.txt 和 verification.json：技术验证。
native_integration/paired_ab/shutdown-checkpoint.json：机器可读收尾回执。
native_integration/paired_ab/shutdown-windows-cleanup.json：临时fixture退出及现役端口保持。
evidence/native_integration/paired_ab/shutdown-board-check.json：板端保持/进程审计。
evidence/native_integration/paired_ab/pilot-v1-shutdown-evidence.zip：26份原始pilot日志。
native_integration/paired_ab/harness-delivery-nojpeg-v2.json：下一轮源码冻结。
isolated-yuki-candidate-20261030.zip：未部署的技术候选，保持原SHA不重打包。
'''
(phase/'SHUTDOWN_RESUME.txt').write_text(text,encoding='utf-8')

vpath=phase/'verification.json'
v=json.loads(vpath.read_text(encoding='utf-8-sig'))
v.update(resource_reduction_proven=False,replacement_decision='PENDING_REPEATED_RESOURCE_AB_AND_USER_DECISION',shutdown_checkpoint=receipt,shutdown_resume='SHUTDOWN_RESUME.txt')
vpath.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
progress_path=phase/'PROGRESS.json'
progress=json.loads(progress_path.read_text(encoding='utf-8-sig'))
progress.update(status='CHECKPOINTED_FOR_USER_POWER_OFF_RESOURCE_AB_INCOMPLETE',updated_at_utc=now,shutdown_ready=True,resource_reduction_proven=False,formal_12_case_suite_started=False,resume_file=str(phase/'SHUTDOWN_RESUME.txt'))
progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
readme=phase/'README.txt'
prior=readme.read_text(encoding='utf-8-sig')
marker='断电检查点已保存；正式重复资源A/B尚未运行，不得据pilot决定替换。续接请先读 SHUTDOWN_RESUME.txt。\n\n'
if not prior.startswith(marker):readme.write_text(marker+prior,encoding='utf-8')

ack_path=coord/'character_ack.json'
ack=json.loads(ack_path.read_text(encoding='utf-8-sig'))
ack.update(status='SHUTDOWN_READY_CHARACTER_RESOURCES_RELEASED',updated_at_utc=now,written_at_utc=now,shutdown_ready=True,shutdown_checkpoint=receipt,shutdown_resume_file=str(phase/'SHUTDOWN_RESUME.txt'))
w=ack['resource_windows']
w.update(active_board_cpu_gpu_tests=False,active_performance_sampling=False,board_sampler_pid=None,board_case_pid=None,
    isolated_windows_server_pid=None,isolated_windows_server_port=None,all_character_validation_processes_exited=True,
    performance_window='RELEASED_FOR_USER_POWER_OFF',UART='RELEASED_NOT_OPENED_BY_CHARACTER',remaining_now='No active tests. Resource AB deferred to next powered session; local checkpoint saved.',
    current_phase='SHUTDOWN_READY; owned fixture exited, board workers0, evidence copied. No further board calls; main business root may perform orderly host shutdown.',
    expected_start_utc=None,expected_end_utc=None)
ack['shutdown_coordination'].update(state='SHUTDOWN_READY',remaining_owned_pids=[],cleanup_proofs=[str(ab/'shutdown-windows-cleanup.json'),str(evidence/'shutdown-board-check.json')],released_at_utc=now)
ack['paired_ab_plan']['status']='NOT_STARTED_FORMAL_REQUIRES_RESEAL_AFTER_REBOOT'
temp=ack_path.with_suffix('.tmp')
temp.write_text(json.dumps(ack,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,ack_path)
print(json.dumps(receipt,ensure_ascii=False))
