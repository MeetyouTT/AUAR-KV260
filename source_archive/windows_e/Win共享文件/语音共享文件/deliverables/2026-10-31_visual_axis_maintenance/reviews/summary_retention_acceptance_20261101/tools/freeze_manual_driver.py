"""Freeze the prepared public-UI driver locally; no SSH and no production changes."""
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
    module_spec = importlib.util.spec_from_file_location('prepared_manual_driver', HERE / 'tools/start_manual_one_turn.py')
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source, owners, observer_sha = module.build_source()
    ast.parse(source.decode('utf-8'), feature_version=(3, 9))
    tests = json.loads((HERE / 'evidence/manual_entry_public_tests.json').read_bytes())
    assert tests['passed'] and tests['tests'] == 13 and tests['device_accessed'] is False
    assert tests['control_sha256'] == pin(HERE / 'remote/manual_one_turn_control.py')['sha256']
    folder = HERE / 'manual_driver'
    folder.mkdir(exist_ok=True)
    prepared = dict(schema='aura-manual-one-turn-preparation-1', status='PREPARED_NOT_DEVICE_TESTED',
                    source_sha256=hashlib.sha256(source).hexdigest(), source_bytes=len(source),
                    remote_python39_syntax=True, public_fake_tests=tests, expected_owners=owners,
                    observer_sha256=observer_sha, base_observer_sha256='8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819',
                    observer_changed_lines=14, original_privacy_projection_and_accepted_ack_logic_unchanged=True,
                    input_route='POST /api/command service_action record_start/record_stop',
                    automatic_toggle_used=False, direct_runtime_or_store_methods_used=False,
                    monitor_owned_directly_observable=False,
                    monitor_owned_limitation='visual_bound is overwritten by VoiceFirst.public; PAUSED/disabled/auto-disabled are public observations; monitor_owned=false is only a fixed-source invariant inference',
                    source_selection_config_clock_or_database_modified=False, manual_capture_max_seconds=20,
                    execution_requires=['target same-scope metadata admission and target summary/raw-body conditions',
                                        'user available before the 20-second capture starts',
                                        'fresh full source/owner/output preflight and public LOCAL RECORDING confirmation'],
                    on_user_speech_finished='create exact STOP.json in the active manual trial directory; one existing SSH control stream relays record_stop once',
                    on_capture_already_ended='no duplicate stop', on_observer_timeout='wait naturally; no cancel or pause toggle; pending if still active')
    (folder / 'PREPARATION.json').write_text(json.dumps(prepared, indent=2) + '\n', encoding='utf-8')
    note = '''# 手动单轮入口：仅完成本地准备

13 项公开假状态检查通过，远端组合源码通过 Python 3.9 语法解析。尚未用此驱动操作设备，不构成手动录音或同会话检索实测。

沿用 8ebb 观察器的原隐私投影及“首个被接受的新请求 + 匹配完整播放 ACK”判据，仅改为 PAUSED 状态下本地 RECORDING 的 READY 门槛，并加入单次停止控制。差异见 ../evidence/manual_observer_minimal.patch。

执行时只走现有 UI service_action 的 record_start/record_stop。先读取公共 ui_runtime 的 capability/modules，拒绝远端音频路由；开始后必须看到 local_recording.state=RECORDING。自动聆听保持 disabled/PAUSED，automatic_conversation.enabled=false。monitor_owned 无独立公共读回，不能以 visual_bound=false 代替；只能基于固定源码暂停不变量推导。

驱动默认只做本地组合检查。实际开启前需要目标范围和摘要／原文条件成立，并确认用户已准备好在 20 秒内说话。收到用户说完后，通过本次 trial 的 STOP.json 传一次停止控制；已自然结束则不重复停止。观察超时会自然等待，绝不取消正在回答的任务，也不切换自动聆听。

生产源码、配置、selection、时钟、数据库及原跟随控制器均不由此驱动修改。FROZEN_MANIFEST.json 固定材料，现役变化后会拒绝复用。
'''
    (folder / 'README.md').write_text(note, encoding='utf-8', newline='\n')
    files = [HERE / 'tools/start_manual_one_turn.py', HERE / 'tools/test_manual_one_turn.py',
             Path(__file__), HERE / 'remote/manual_one_turn_control.py', HERE / 'remote/live_observer_manual_accepted.py',
             HERE / 'evidence/manual_entry_public_tests.json', HERE / 'evidence/manual_observer_minimal.patch',
             folder / 'PREPARATION.json', folder / 'README.md',
             JOINT / 'remote/live_observer_caption_accepted.py', JOINT / 'remote/common.py',
             JOINT / 'package/subtitle_receipt/camera_binding_runtime.py',
             HERE / 'evidence/preflight_1793537147007232900.json',
             PROJECT / 'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json']
    manifest = dict(schema='aura-manual-one-turn-frozen-local-1', status='PREPARED_NOT_RUN',
                    combined_remote_sha256=prepared['source_sha256'], files=[pin(path) for path in files])
    path = folder / 'FROZEN_MANIFEST.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    module.verify_frozen_manifest()
    print(json.dumps(dict(status='LOCAL_PREPARATION_FROZEN', manifest=pin(path), preparation=pin(folder / 'PREPARATION.json'))))


if __name__ == '__main__':
    main()
