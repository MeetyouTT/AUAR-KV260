"""Publish the local-only checkpoint; preserve every earlier report byte."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BALANCE = HERE.parent
PROJECT = HERE.parents[5]
RET = PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/summary_retention_acceptance_20261101'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(path, expected):
    raw = path.read_bytes()
    assert sha(raw) == expected, str(path)
    return json.loads(raw)


handoff_path = RET/'SOFTWARE_ONLY_HANDOFF.json'
handoff = checked(handoff_path, 'fd0c7bac3a5f54c1845a536fba1152ec58d14969aece5557d3947e203a8f1e77')
assert handoff['status'] == 'SOFTWARE_CHECKS_DONE_HARDWARE_READY_PENDING'
for key in ('canonical_state', 'pending_readiness', 'applied_spec', 'probe',
            'observer', 'observer_adapter', 'production_apply_bundle', 'source_recovery_publisher'):
    row = handoff[key]
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], key
canonical = json.loads(Path(handoff['canonical_state']['path']).read_bytes())
assert canonical['status'] == 'FILES_APPLIED_READY_PENDING_MCP01'
assert canonical['files_applied'] is True and canonical['production_ready'] is False
assert canonical['unit_last_observed']['MainPID'] == 0
assert canonical['publication_guard_retained'] is True
assert canonical['startup_retries_and_hardware_polling_stopped'] is True
for key in ('source_accepted_arm', 'source_application', 'readiness_pending_evidence',
            'original_audio_failure_evidence', 'hardware_absence_evidence'):
    row = canonical[key]
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], key
observer_manifest = checked(RET/'observer_ec12/FROZEN_MANIFEST.json',
    'd63c5b100238f140eed2c32d0219a04ca9ed32f73d00ab2e8bdd314607949f74')
for row in observer_manifest['files']:
    path = Path(row['path'])
    assert path.is_relative_to(PROJECT)
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], str(path)
review_path = HERE/'ROOT_EC12_SOFTWARE_REVIEW.json'
review_raw = review_path.read_bytes()
review = json.loads(review_raw)
assert review['status'] == 'LOCAL_SOFTWARE_CHECKS_PASS_LIVE_REQUIRES_AUDIO_HARDWARE_AND_READY'
assert review['probe_sha256'] == 'e0ae0a807db2bdecf6cae166924704d55f5a9b95a9972a8bfb0d96376ebac3df'
assert review['observer_adapter_sha256'] == handoff['observer_adapter']['sha256']
assert review['public_probe_tests']['passed'] is True and review['observer_composition_tests']['passed'] is True
retention = json.loads((HERE/'RETENTION_RESULT.json').read_bytes())
assert retention['status'] == 'STORAGE_PASS_RECALL_PENDING'

previous_path = BALANCE/'joint_balance_status.json'
previous_raw = previous_path.read_bytes()
previous = json.loads(previous_raw)
assert previous['current_startup_sha256'].startswith('22317f79')
archive = HERE/'archive'
archive.mkdir(exist_ok=True)
previous_archive = archive/('joint_balance_before_ec12_'+sha(previous_raw)[:16]+'.json')
with previous_archive.open('xb') as handle:
    handle.write(previous_raw)

report_path = HERE/'软件检查与恢复说明.md'
report = f'''# 软件检查与恢复说明

记录日期：2026-11-01。软件检查完成；板端新文件已应用，MCP01 USB声卡缺失导致音频初始化失败，界面尚未就绪。按用户“暂时无法连接，先完成软件检查”的要求，已停止启动重试与硬件轮询。发布保护保留，未切换声卡配置。

| 项目 | 已有证据 | 待验证范围 |
| --- | --- | --- |
| 暂停后继续当前对话 | 54fa单源修复；本地与实际aarch64/Python3.9均9项公开方法测试通过 | 新界面运行后的真实同会话验证 |
| 发布与回退 | 10项本地事务检查通过；三目标已写入，另379项源码保持 | 声卡恢复后的原服务启动及实际READY |
| 五分钟后保留摘要、删除原文 | 上一22317运行实例中，同一公开输入在115.80秒时用户/助手正文各1行，自然333.44秒后各0行；同一有效摘要及已提交任务匹配 | 新版本同会话精确追问 |
| 新版记忆检查程序 | 只更新启动指纹并增加54fa源指纹；SQL及原同会话门槛保持；6项公开内存SQLite测试通过 | 新公开输入后才执行实机只读检查 |
| 正常聆听观察程序 | 原8ebb观察代码不变；6项组合测试通过，核对完整播放回执、前后会话哈希、拒绝错误回执与未就绪启动 | 接回声卡后做正常语音测试 |

此前两栏字幕、完整声音、人数查询和最近三轮温水记忆的成功结果保留为22317/de04版本的历史验收。此前超过五分钟追问出现答错，但输入与追问属于不同会话，不能据此判断同会话摘要检索成功或失败；失败记录和用户的操作反馈均保留。新修复不等于现场召回已通过。

当前应用的startup为`{canonical['applied_startup_sha256']}`，voice_first源为`{canonical['applied_voice_first_sha256']}`。最新设备记录为主管MainPID=0、unit failed、GUI接口不可用、MCP01未枚举。原暂停偏好及转轴关闭状态只标注其最后实际读回时点；没有把旧运行中的PAUSED页面冒充当前仍在运行。主窗口全程未访问设备、模型或私人数据库。

接回MCP01后，由原设备窗口先做一次新鲜的启动、源码与进程核对，再沿现有保护事务启动原服务。实际READY后，确认当前会话被原入口合法恢复，做公开输入“你好，我把杯子放在桌子左边了。”；完整播放后暂停，等待自然五分钟压缩，再通过正常继续入口问“回忆一下今天我把杯子放在哪里了？”。核对同会话、识别语义、字幕和声音，结束后暂停。测试期间无需手动点击暂停或继续。

设备交接：[SOFTWARE_ONLY_HANDOFF.json]({handoff_path.as_posix()})。本地复核：[ROOT_EC12_SOFTWARE_REVIEW.json]({review_path.as_posix()})。存储半段：[RETENTION_RESULT.json]({(HERE/'RETENTION_RESULT.json').as_posix()})。前序完整记录：[测试接续计划.md]({(HERE/'测试接续计划.md').as_posix()})。

本轮没有增加或搬移语言模型、没有重跑整机性能基准。声纹校准、物理熄屏、多小时稳定性与新版本现场召回仍不作通过声明。
'''
with report_path.open('x', encoding='utf-8') as handle:
    handle.write(report)

status = dict(schema='aura-joint-balance-status-2',
    status='FILES_APPLIED_READY_PENDING_MCP01_SOFTWARE_CHECKS_PASS',
    current_startup_sha256=canonical['applied_startup_sha256'],
    current_manifest_sha256=canonical['applied_manifest_sha256'],
    current_spec_sha256=handoff['applied_spec']['sha256'],
    current_voice_first_source_sha256=canonical['applied_voice_first_sha256'],
    files_applied=True, production_ready=False, current_supervisor_pid=None, current_gtk_pid=None,
    unit_last_observed=canonical['unit_last_observed'], gui_api_last_observed_available=False,
    publication_guard_retained=True, startup_retries_and_hardware_polling_stopped=True,
    saved_listening_preference=canonical['saved_listening_preference'],
    output_state=canonical['output_state'],
    device_operator_thread='01a195e4-58a7-72d3-b141-d5d373579f7f', main_thread_device_access=False,
    software_checks=handoff['software_checks'], root_review=dict(path=str(review_path), sha256=sha(review_raw)),
    memory_storage_assessment=retention,
    new_same_scope_live_recall_accepted=False, all_functionality_accepted=False,
    last_accepted_startup_sha256=previous['current_startup_sha256'],
    previous_joint_validation=dict(path=str(previous_archive), sha256=sha(previous_raw), historical=True),
    software_handoff=dict(path=str(handoff_path), sha256=sha(handoff_path.read_bytes())),
    canonical_state=handoff['canonical_state'],
    model_download_or_move=False, production_dialogue_audio_images_or_templates_exported=False,
    report=str(report_path))
assert previous_path.read_bytes() == previous_raw
previous_path.write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def prepend_preserving(target, marker, prefix, backup_name):
    old = target.read_bytes()
    assert marker.encode() not in old
    backup = archive/backup_name
    with backup.open('xb') as handle:
        handle.write(old)
    added = prefix.encode('utf-8')
    assert target.read_bytes() == old
    target.write_bytes(added+old)
    assert target.read_bytes()[len(added):] == backup.read_bytes()
    return dict(path=str(target), previous_sha256=sha(old), backup=str(backup),
                updated_sha256=sha(target.read_bytes()), old_bytes_preserved=True)

marker = '<!-- ec12-software-check-ready-pending-20261101 -->'
prefix = f'''{marker}
2026-11-01接续状态：暂停后继续当前对话的软件修复已通过检查并写入板端，MCP01 USB声卡缺失，原音频初始化失败，界面尚未就绪。启动重试与硬件轮询已停止。自然五分钟删除原文、保留有效摘要的存储部分已在上一运行实例验证；新版本同会话精确追问待声卡恢复。

[软件检查与恢复说明]({report_path.as_posix()}) · [当前状态]({previous_path.as_posix()})

以下旧段落按其原记录时点保留，不代表当前界面仍在运行或新版本已经READY。
<!-- /ec12-software-check-ready-pending-20261101 -->

'''
records = [prepend_preserving(BALANCE/'优化与验收进度.md', marker, prefix, '优化与验收进度_before_ec12.md'),
           prepend_preserving(Path('E:/Win共享文件/语言模型分析/README.md'), marker, prefix, 'analysis_index_before_ec12.md')]
receipt = dict(schema='aura-root-local-software-check-publication-1',
    status=status['status'], observer_manifest_checked=True,
    observer_manifest_sha256=handoff['observer']['sha256'],
    software_handoff_sha256=sha(handoff_path.read_bytes()),
    report=str(report_path), current_status=str(previous_path), preserved_updates=records,
    device_or_model_or_private_database_access=False)
(HERE/'SOFTWARE_CHECK_PUBLICATION.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
