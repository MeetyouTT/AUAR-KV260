"""Freeze only local R2 material; preserve the failed R1 package and evidence."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[3]
JOINT = HERE.parent / 'joint_performance_20261101'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    spec = importlib.util.spec_from_file_location('prepared_manual_r2', HERE / 'tools/start_manual_one_turn_r2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, owners, observer_sha = module.build_source()
    ast.parse(source.decode(), feature_version=(3, 9))
    test_path = HERE / 'evidence/manual_entry_r2_public_tests.json'
    tests = json.loads(test_path.read_bytes())
    assert tests['passed'] and tests['tests'] == 15 and tests['device_accessed'] is False
    assert tests['driver_sha256'] == pin(HERE / 'tools/start_manual_one_turn_r2.py')['sha256']
    folder = HERE / 'manual_driver_r2'
    folder.mkdir(exist_ok=True)
    report = dict(schema='aura-manual-r2-isolated-namespace-preparation-1', status='PREPARED_NOT_DEVICE_TESTED',
                  combined_remote_sha256=hashlib.sha256(source).hexdigest(), source_bytes=len(source),
                  control_sha256=pin(HERE / 'remote/manual_one_turn_control.py')['sha256'],
                  observer_sha256=observer_sha, owners=owners, tests=pin(test_path),
                  r1_frozen_files_and_failed_evidence_preserved=True,
                  regression=['R1 SOURCE replaces select module with function: AttributeError reproduced',
                              'R1 SOURCE replaces state() helper with dictionary: TypeError reproduced',
                              'R2 actual REMOTE completes 3 SOURCE samples, accepted target, full ACK, cleanup and final guard'],
                  fix='common, control and observer execute in separate dictionaries; injected control functions retain control globals',
                  allowed_commands=['service_action record_start', 'service_action record_stop'],
                  automatic_toggle_select_or_cancel_added=False, production_files_modified=False,
                  actual_device_retest_pending=True, monitor_owned_directly_observable=False)
    report_path = folder / 'PREPARATION.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    note = '''# R2：隔离命名空间，仅完成本地验证

R1 已真实失败：内嵌 SOURCE 覆盖 select 模块和 state() 检查函数，导致第二轮轮询 AttributeError、最终检查 TypeError。R1 冻结文件、原观察失败、用户“位置不对或不记得”反馈均保留；观察错误不能证明回答错误的原因。

R2 只把 common、control、observer 的执行字典隔离。现有 79af 控制代码、4a01 观察代码及 UI record_start/stop 不变，无 toggle、select_conversation 或 cancel。15 项本地公开测试通过，包含真实 SOURCE 三轮、accepted request、完整 ACK、自然收尾和最终 guard；尚未实机重试。

任何实机重试仍需新鲜完整 guard、用户就位和明确的重试安排。当前保持暂停，先按授权恢复 R1 回答的哈希和同范围证据。monitor_owned 无公共直接读回的限制保留。
'''
    (folder / 'README.md').write_text(note, encoding='utf-8', newline='\n')
    paths = [HERE / 'tools/start_manual_one_turn_r2.py', HERE / 'tools/test_manual_one_turn_r2.py',
             HERE / 'tools/test_manual_one_turn.py', Path(__file__), HERE / 'remote/manual_one_turn_control.py',
             HERE / 'remote/live_observer_manual_accepted.py', test_path,
             HERE / 'evidence/manual_driver_r2_namespace.patch', report_path, folder / 'README.md',
             JOINT / 'remote/live_observer_caption_accepted.py', JOINT / 'remote/common.py',
             JOINT / 'package/subtitle_receipt/camera_binding_runtime.py',
             HERE / 'evidence/preflight_1793537147007232900.json',
             PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json']
    manifest = dict(schema='aura-manual-r2-frozen-local-1', status='PREPARED_NOT_RUN',
                    combined_remote_sha256=report['combined_remote_sha256'], files=[pin(path) for path in paths])
    manifest_path = folder / 'FROZEN_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    module.verify_frozen_manifest()
    print(json.dumps(dict(status='MANUAL_R2_FROZEN_NOT_RUN', manifest=pin(manifest_path), preparation=pin(report_path))))


if __name__ == '__main__':
    main()
