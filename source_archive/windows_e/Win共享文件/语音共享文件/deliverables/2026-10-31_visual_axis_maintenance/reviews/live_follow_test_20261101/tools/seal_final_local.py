"""Seal saved device receipts and update local continuation entries; no device I/O."""
from pathlib import Path
import copy
import hashlib
import json
import os
from datetime import datetime, timezone

LIVE = Path(__file__).resolve().parents[1]
TASK = LIVE.parents[1]
PROJECT = TASK.parents[1]
OWNER = PROJECT / 'deliverables/2026-10-30_board_owner'
CANONICAL = OWNER / 'integration/production_business_acceptance'
DOCS = LIVE / 'docs_state_final'
SHARE = PROJECT.parent
THREAD = '01a195e4-58a7-72d3-b141-d5d373579f7f'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=sha(raw), bytes=len(raw))


def atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.axis-seal-tmp')
    assert not tmp.exists(), tmp
    with tmp.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def main():
    assert not DOCS.exists(), 'Preserve prior seal; refuse a second mutation.'
    final_path = LIVE / 'evidence/final_original_inventory_1793527480550065200.json'
    test_path = LIVE / 'evidence/test_original_gui_follow_1793527294434976800.json'
    ready_path = LIVE / 'evidence/original_publish_ready_1793527196434882700.json'
    bundle = LIVE / 'package/original_direction_fix'
    assert sha(final_path.read_bytes()) == 'cd4c6cd72d7a960a8baa47e0ef26bf30484328181b2bfb3fd26f96f82204fcae'
    assert sha(test_path.read_bytes()) == 'b7474d1dfee05fffbba1103055ff6db11d746332dce5777e7946e1f06b419ad6'
    inv = read(final_path)['result']
    test = read(test_path)['result']
    ready = read(ready_path)['result']
    spec = read(bundle / 'new_spec.json')
    frozen = read(bundle / 'publisher_bundle_manifest.json')
    for name, expected in frozen['files'].items():
        assert sha((bundle / name).read_bytes()) == expected, name
    assert sha((bundle / 'new_startup.json').read_bytes()) == inv['startup_sha256']
    assert sha((bundle / 'new_manifest.json').read_bytes()) == inv['manifest_sha256']
    assert spec['startup_sha256'] == inv['startup_sha256']
    assert spec['source_manifest_sha256'] == inv['manifest_sha256']
    assert spec['configuration_sha256'] == inv['configuration_sha256']
    assert ready['main_pid'] == inv['owners']['supervisor']['pid']
    assert ready['gtk_pid'] == inv['owners']['gtk']['pid']
    assert inv['output_closed'] and not inv['automatic_following']
    assert inv['all_component_bytes_match'] and inv['original_controller_unchanged']
    assert inv['control_polarity'] == 1 and inv['readback']['flags'] == 0
    assert test['result_reason'] == 'OPERATOR_STOP' and not test['error_present']
    assert sha((CANONICAL / 'spec.json').read_bytes()) == '9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1'
    old_spec = read(CANONICAL / 'spec.json')
    changed = sorted(k for k in spec['component_sha256'] if spec['component_sha256'][k] != old_spec['component_sha256'][k])
    assert changed == sorted(spec['axis_original_rebind']['changed_components'])
    assert len(changed) == 4 and len(spec['component_sha256']) == 380

    paths = [TASK/'LATEST_REVIEW.json', TASK/'README.md', PROJECT/'AGENTS.md', PROJECT/'README.md',
             CANONICAL/'spec.json', CANONICAL/'actual_ready.json', OWNER/'coordination/runtime_windows.json']
    before = []
    for path in paths:
        archived = DOCS / 'before' / path.relative_to(SHARE)
        raw = path.read_bytes()
        atomic(archived, raw)
        before.append(dict(original=ref(path), archive=ref(archived)))
    atomic(DOCS/'before_manifest.json', encoded(before))

    now = datetime.now(timezone.utc).isoformat()
    observed = read(final_path)['utc']
    report = dict(
        schema='aura-original-face-follow-handoff-1', sealed_utc=now, observed_utc=observed,
        status='ORIGINAL_FOLLOW_TEST_COMPLETE_USER_APPROXIMATE_ACCEPTANCE',
        user_feedback='差不多额', device_operator_thread=THREAD,
        device_commands_inflight=False, main_chat_device_operations_released_back=False,
        user_device_ownership_instruction='本窗口接管，主窗口停止设备操作',
        production_root=ready['root'], runtime_root=ready['root']+'/runtime/aura',
        startup_sha256=inv['startup_sha256'], source_manifest_sha256=inv['manifest_sha256'],
        configuration_sha256=inv['configuration_sha256'], current_spec=ref(bundle/'new_spec.json'),
        original_controller_root='/home/root/aura-pan-wide-20261028/control-10282601',
        final=inv, actual_short_follow_test={k:v for k,v in test.items() if k != 'samples'},
        evidence=dict(final_inventory=ref(final_path), actual_follow=ref(test_path), ready=ref(ready_path)),
        sources=dict(original_controller_unchanged=True, original_gui_follow_source_unchanged=True,
                     candidate_r2_selected_for_production=False, original_component_pins=380,
                     changed_configurations=changed, remaining_original_components_unchanged=376,
                     memory_v24_policy_sha256=spec['release_sources']['board/runtime/board_memory_policy.py']),
        camera_restoration=dict(original_camera_implementation_restored=True,
                                consumed_last_native_checkpoint_sha256='d8169b01ecc865b4a33dba0e9a65dd6bf3bf1c4518b931e0398ee0873f158cdd',
                                original_readback_pins_retained=22, current_pin_count=23,
                                database_or_template_exported=False,
                                threshold_changed=False,
                                threshold_scope='Existing camera SFace experimental threshold 0.50 and GUI identity threshold 0.85 are separate settings; neither changed.'),
        limitations=['Pulse width is a command/readback, not a measured physical angle or mechanical zero.',
                     'Only a short trial and approximate human acceptance; no long-duration or multi-person acceptance.',
                     'Identity backend READY is not personal identification; the trial identity remained UNKNOWN.',
                     'Native primary_period_overruns is cumulative 6; this final trial was 6 to 6.',
                     'The original controller is selected; isolated R2 trial reports do not describe production.'],
        preserved_history=['V1 probe path error and V2 correction', 'unpowered initial movement attempts and user correction',
                           'finite-test deadline and receipt-label failures', 'isolated R2 test then user selection of original',
                           'direction transaction failure journal and exact marker repair', 'all previous publication histories'],
        model_weights_moved=False, model_downloaded=False,
        next_use='Visual page original face-follow toggle; obtain fresh device/source/owner readback before later automated operations.',
        local_seal=dict(directory=str(DOCS), before_manifest=str(DOCS/'before_manifest.json')))
    atomic(LIVE/'HANDOFF.json', encoded(report))

    text = f'''# 原板端人脸随动实测收尾（2026-11-01）

已按用户要求恢复原板端跟随，并将人脸跟随方向从 -1 改为 +1。用户本轮反馈“差不多额”，据此保留设置并停止。最终保存观测为 {observed}（America/Los_Angeles 当地 02:04:40 PST），不代替下次新鲜读回。

## 实际结果

- 使用原控制器25个文件和原GUI跟随入口；源码逐字节未改。R2仅在独立测试目录试过，未选作生产版本。
- 最后一轮原版控制器报告时长26.389秒，接受112条命令、10个运动段，报告7次视觉中心完成。此数值属于软件报告，不是机械角度标定。
- 已执行原GUI停止：follow=false、READY，输出关闭，flags=0、lease=0、active=false、armed=false。脉宽读回1632µs，无机械中点或正前方角度声明。
- GUI运行故障0；原生累计period_overruns=6，最终短测6→6；未发生owner fence。
- 视觉页保留；语音仍PAUSED、enabled=false、mic=false、无播放。人脸识别后端可用，末轮身份UNKNOWN。

## 当前接续指纹

- 生产根：`{ready['root']}`，runtime为其`runtime/aura`。
- startup：`{inv['startup_sha256']}`。
- manifest：`{inv['manifest_sha256']}`；380项组件全部实际核对。
- GUI配置：`{inv['configuration_sha256']}`。
- spec：`{sha((bundle/'new_spec.json').read_bytes())}`。
- 相机430894 / birth4011213；supervisor496785 / birth4302772；GTK496789 / birth4302880；boot `{inv['boot']}`。完整命令指纹见结构化交接。
- 原wide固件和VART已恢复；FDT `{inv['fdt_sha256']}`。原相机以最后实际checkpoint恢复，旧readback的22项保留并追加本次runtime，未导出模板或私库。

相较原v24仅更新4项配置：GUI的现役相机readback、手动运行绑定、人脸跟随运行绑定、方向绑定；其余376项保持。记忆d6e策略、人格/动画和语音实现继续沿用。原相机实验阈值0.50与GUI身份阈值0.85属于不同设置，本轮均未更改。

## 证据与历史范围

- [最终实板读回](evidence/{final_path.name})，SHA `{sha(final_path.read_bytes())}`。
- [最终原版跟随试验](evidence/{test_path.name})，SHA `{sha(test_path.read_bytes())}`。
- 板端原报告：`{test['report_path']}`，SHA `{test['report_sha256']}`。
- [完整交接](HANDOFF.json)、[源码/配置冻结包](package/original_direction_fix/publisher_bundle_manifest.json)、[本地入口更新前原字节](docs_state_final/before_manifest.json)。所有早期失败、方向事务修复、独立候选试验及旧发布历史均保留。

最初未转动后用户明确说明未给舵机上电，不将该轮误记为已确诊机械故障。上电后人类反馈用于方向确认；反向反馈后才修改极性。没有测量机械零点、实际±90°范围、识别准确率或长期稳定性。

## 后续使用

可在视觉页用原“人脸跟随”入口开启。当前所有本轮设备命令已结束；按用户分工设备串行权暂留本窗口，主窗口继续只读，未自动转交操作权。后续自动操作先现读boot、进程完整指纹、380项源码闭包、固件/VART、暂停偏好和输出状态。旧v24发布器及旧平台探针的startup/相机PID属于历史，不能直接沿用。
'''
    atomic(LIVE/'HANDOFF.md', text.encode('utf-8'))

    atomic(CANONICAL/'spec.json', (bundle/'new_spec.json').read_bytes())
    atomic(CANONICAL/'actual_ready.json', encoded(ready))
    latest = dict(schema='aura-visual-axis-latest-local-review-2',
                  review='reviews/live_follow_test_20261101/HANDOFF.json',
                  summary='reviews/live_follow_test_20261101/HANDOFF.md',
                  actual_platform_receipt='reviews/live_follow_test_20261101/evidence/'+final_path.name,
                  actual_follow_receipt='reviews/live_follow_test_20261101/evidence/'+test_path.name,
                  production_controller='ORIGINAL_UNCHANGED_25_FILES', candidate_r2_deployed=False,
                  production_configurations_updated=True, following=False, output_closed=True,
                  user_acceptance='APPROXIMATE_SHORT_TEST', observed_utc=observed,
                  previous_reviews_preserved=True, current_live_state_claimed=False)
    atomic(TASK/'LATEST_REVIEW.json', encoded(latest))
    report_ref = dict(ref(LIVE/'HANDOFF.json'), revision='v24-original-follow-direction',
                      startup_sha256=inv['startup_sha256'], source_manifest_sha256=inv['manifest_sha256'],
                      configuration_sha256=inv['configuration_sha256'], component_pins=380,
                      status=report['status'], observations_are_not_full_acceptance=True)
    coord_path = OWNER/'coordination/runtime_windows.json'
    coord = read(coord_path)
    coord['continuation_history'].append(dict(original_bytes_archive=before[-1]['archive'],
                                             previous_current_observation=copy.deepcopy(coord['current_observation']),
                                             previous_status=coord['status'],
                                             superseded_by_revision='v24-original-follow-direction'))
    coord.update(startup_sha256=inv['startup_sha256'], source_manifest_sha256=inv['manifest_sha256'],
                 configuration_sha256=inv['configuration_sha256'], camera_pid=430894, camera_birth_ticks=4011213,
                 supervisor_pid=496785, gtk_pid=496789, board_boot_id=inv['boot'],
                 current_observation=report_ref, status=report['status'], updated_at=now, updated_utc=now,
                 last_device_observed_utc=observed, current_live_state_claimed=False,
                 finalization_stage='ORIGINAL_FOLLOW_STOPPED_DIRECTION_RETAINED',
                 device_operation_owner=dict(thread_id=THREAD, state='IDLE_NO_INFLIGHT_COMMANDS',
                                             user_instruction=report['user_device_ownership_instruction'],
                                             main_chat_read_only=True, automatically_returned_to_main=False),
                 verification_scope_notice='New owners/configuration and original follow short trial are recorded in current_observation. Voice, memory, display, model, benchmark and public-case observations below retain their original evidence scope; they were not repeated after this camera/GUI restart.')
    coord['retained_mechanical_boundary'] = dict(new_actuation_test_performed=True, required_state='STOPPED_OUTPUT_CLOSED',
                                                scope='Original follow short trial with approximate user acceptance',
                                                tracking_enabled=False, pan_state='READY', pulse_us=1632,
                                                control_polarity=1, mechanical_zero_calibrated=False,
                                                separate_axis_chat_status=report['status'], reference=report_ref)
    coord['performance_window'] = dict(state='AXIS_CHAT_IDLE_MAIN_READ_ONLY', holder_thread=THREAD,
                                      board_boot=inv['boot'], active_character_tests=False,
                                      allowed='Device serialization remains with the axis chat under direct user instruction; no commands in flight.',
                                      previous_record_in_before_archive=before[-1]['archive'])
    coord['operator_instruction'] = dict(publication_expected_listening_enabled=False,
                                         sole_publisher_thread=THREAD, publication_complete=True,
                                         spec=ref(CANONICAL/'spec.json'), publisher=None,
                                         usage='Saved original-follow restoration is complete. Do not replay historical v24 or restoration publishers; establish a fresh actual owner/source baseline for any later operation.')
    coord['verified_listening'] = dict(enabled=False, state='PAUSED', microphone_open=False,
                                       startup_sha256=inv['startup_sha256'], revision='v24-original-follow-direction',
                                       continuous_capture_passed=False, source=ref(final_path))
    for key in ('production_UI_switch', 'production_business_cutover'):
        coord[key].update(startup_sha256=inv['startup_sha256'], source_manifest_sha256=inv['manifest_sha256'],
                          configuration_sha256=inv['configuration_sha256'], current_observation=report_ref,
                          state=report['status'], updated_utc=now)
    coord['evidence'].append(report_ref)
    atomic(coord_path, encoded(coord))

    link = str(LIVE/'HANDOFF.md').replace('\\', '/')
    top = f'''<!-- visual-axis-current-20261101 -->
原板端人脸随动已恢复，按用户反馈将方向修正为+1；短测后用户反馈“差不多额”。当前保存观测为READY/follow=false、输出关闭、1632µs，视觉页可再开启原跟随。语音仍PAUSED/mic=false。相机430894、supervisor496785、GTK496789；旧PID与FAULT/null状态已由本次读回替代。

startup `{inv['startup_sha256']}`，manifest `{inv['manifest_sha256']}`，GUI配置 `{inv['configuration_sha256']}`，380项实读匹配。仅4项运行配置更新，原控制器25文件和全部Python/Native源码保持；v24记忆与人格/动画保持，R2未选作生产。

[最新实板交接]({link})。按用户安排，本窗口本轮操作已结束，设备串行权暂留本窗口、主窗口只读。下次先新鲜核对完整指纹；以下旧轮次的PID、startup、FAULT和未实测声明属于历史，原证据不迁作本轮验收。
<!-- /visual-axis-current-20261101 -->

'''
    for path in (PROJECT/'AGENTS.md', PROJECT/'README.md', TASK/'README.md'):
        raw = path.read_bytes()
        assert b'<!-- visual-axis-current-20261101 -->' not in raw
        atomic(path, top.encode('utf-8') + raw)

    changed_refs = [ref(p) for p in paths]
    atomic(DOCS/'SEAL.json', encoded(dict(schema='aura-local-axis-continuation-seal-1', sealed_utc=now,
                                         device_access_performed=False, before=before, after=changed_refs,
                                         handoff=ref(LIVE/'HANDOFF.json'), summary=ref(LIVE/'HANDOFF.md'),
                                         evidence=[ref(p) for p in sorted((LIVE/'evidence').glob('*.json'))])))
    assert (CANONICAL/'spec.json').read_bytes() == (bundle/'new_spec.json').read_bytes()
    assert read(CANONICAL/'actual_ready.json') == ready
    assert read(TASK/'LATEST_REVIEW.json')['following'] is False
    assert read(coord_path)['startup_sha256'] == inv['startup_sha256']
    for item in before:
        assert sha(Path(item['archive']['path']).read_bytes()) == item['original']['sha256']
    print(json.dumps(dict(status='LOCAL_CONTINUATION_SEALED', handoff=ref(LIVE/'HANDOFF.md'),
                          canonical_spec=ref(CANONICAL/'spec.json'), changed_entries=len(paths),
                          unchanged_original_components=376, device_access=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
