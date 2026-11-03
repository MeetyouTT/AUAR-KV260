"""Prepare reviewed documentation updates from actual listening receipts only.

Default is read-only. --apply writes only the fixed local documentation list,
with before snapshots, hash checks, a journal and rollback on write failure.
No deployment, SSH, model, service, device, or business database imports/calls.
This source was prepared without executing this updater against real records.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
OWNER = HERE.parents[1]
INTEGRATION = HERE.parent
STATUS = 'FORMAL_AUTOMATIC_LISTENING_CAPTURE_VERIFIED_OPERATOR_AUDIO_PENDING'
TAG = 'board-business-live-20261030'
TARGETS = {
    'live': OWNER/'integration/PRODUCTION_BUSINESS_LIVE.json',
    'implementation': OWNER/'IMPLEMENTATION_STATE.json',
    'resume': OWNER/'integration/RESUME_VERIFICATION.json',
    'character': OWNER/'integration/CHARACTER_SWITCH.json',
    'coordination': OWNER/'coordination/runtime_windows.json',
    'agents': PROJECT/'AGENTS.md',
    'continuation': OWNER/'板端业务正式接管与实测接续_20261030.txt',
    'analysis': PROJECT.parent/'语言模型分析/README.md',
}


class ReceiptRejected(ValueError):
    pass


def require(test, code):
    if not test:
        raise ReceiptRejected(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'sha256_required')
    return value


def positive(value):
    require(type(value) is int and 0 < value <= 2147483647, 'positive_pid_or_count_required')
    return value


def local_receipt(path):
    path = Path(path).resolve()
    require(path.is_relative_to(INTEGRATION.resolve()) and path.suffix == '.json',
            'public_integration_json_receipt_required')
    require(path.is_file() and not path.is_symlink(), 'regular_receipt_required')
    raw = path.read_bytes()
    require(len(raw) <= 2*1024*1024, 'receipt_size_limit')
    value = json.loads(raw.decode('utf-8-sig'))
    require(isinstance(value, dict), 'receipt_object_required')
    return value, dict(path=str(path.relative_to(OWNER)).replace('\\', '/'), sha256=sha(raw))


def main_pid(value):
    candidates = [value[k] for k in ('main_pid', 'supervisor_pid') if k in value]
    require(bool(candidates) and len(set(candidates)) == 1, 'ready_owner_pid_required')
    return positive(candidates[0])


def business_options(installed):
    options = installed.get('business_options', {})
    require(isinstance(options, dict), 'business_options_object_required')
    keys = ('frontend_process', 'frontend_capture_process', 'frontend_optimization', 'capture_priority_nice', 'frontend_threads', 'asr_threads')
    result = {}
    for key in keys:
        if key not in options and key not in installed:
            continue
        value = options[key] if key in options else installed[key]
        if key in ('frontend_process', 'frontend_capture_process'):
            require(type(value) is bool, 'frontend_process_boolean_required')
        elif key == 'frontend_optimization':
            require(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_.-]{1,64}', value),
                    'frontend_optimization_metadata_required')
        elif key == 'capture_priority_nice':
            require(value is None or type(value) is int and -20 <= value <= 19,
                    'capture_priority_nice_invalid')
        else:
            require(type(value) is int and 1 <= value <= 64, 'frontend_threads_invalid')
        result[key] = value
    return result


def validate(installed, ready, live, control=None):
    """No gate is inferred from numeric diagnostics or a previous report."""
    require(live.get('continuous_capture_passed') is True, 'continuous_capture_not_passed')
    require(live.get('priority_scope_passed') is True, 'priority_scope_not_passed')
    require(live.get('physical_microphone_opened') is True, 'real_microphone_evidence_required')
    require(live.get('raw_audio_saved_or_transferred') is False, 'metadata_only_evidence_required')
    require(installed.get('automatic_listening') is True, 'automatic_listening_not_selected')
    require(installed.get('retention_enabled') is True, 'production_retention_mismatch')
    require(ready.get('status') == 'PRODUCTION_BOARD_BUSINESS_READY'
            and ready.get('data_origin') == 'board' and ready.get('guard_removed') is True,
            'production_ready_receipt_required')
    root = installed.get('target', installed.get('root'))
    require(isinstance(root, str) and root.startswith('/home/root/')
            and re.fullmatch('[A-Za-z0-9_./-]+', root)
            and '..' not in PurePosixPath(root).parts, 'board_root_required')
    require(ready.get('root') == root and live.get('root') == root, 'receipt_root_mismatch')
    startup = digest(installed.get('startup_sha256'))
    manifest = digest(installed.get('source_manifest_sha256'))
    pins = positive(installed.get('component_pins'))
    require(pins <= 10000, 'component_pin_count_limit')
    for key, expected in (('startup_sha256', startup), ('source_manifest_sha256', manifest),
                          ('component_pins', pins)):
        require(live.get(key) == expected, 'live_revision_binding_mismatch')
        require(key not in ready or ready[key] == expected, 'ready_revision_binding_mismatch')
    supervisor, gtk = main_pid(ready), positive(ready.get('gtk_pid'))
    unit = live.get('unit', {})
    require(isinstance(unit, dict) and unit.get('ActiveState') == 'active', 'unit_not_active')
    require(str(unit.get('MainPID')) == str(supervisor) and live.get('gtk_pid') == gtk,
            'live_process_binding_mismatch')
    boot = live.get('board_boot_id', live.get('boot_id', live.get('boot')))
    require(isinstance(boot, str) and re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot),
            'current_board_boot_required')
    camera = positive(live.get('camera_pid'))
    for receipt in (installed, ready):
        for key in ('board_boot_id', 'boot_id', 'boot'):
            require(key not in receipt or receipt[key] == boot, 'board_boot_mismatch')
        require('camera_pid' not in receipt or receipt['camera_pid'] == camera, 'camera_pid_mismatch')
    samples = live.get('samples')
    wake_required=installed.get('wake_word_required',True)
    require(type(wake_required) is bool,'wake_word_policy_boolean_required')
    conversation_mode=installed.get('conversation_mode','unspecified')
    require(conversation_mode in ('half_duplex','interruptible','unspecified'),'conversation_mode_required')
    require(isinstance(samples, list) and 2 <= len(samples) <= 256, 'bounded_live_samples_required')
    frames, armed = [], []
    for sample in samples:
        require(isinstance(sample, dict), 'live_sample_object_required')
        listening, diagnostic = sample.get('listening', {}), sample.get('diagnostics', {})
        require(listening.get('enabled') is True and listening.get('microphone_open') is True,
                'continuous_live_microphone_required')
        if not wake_required:
            require(listening.get('wake_word_required') is False and listening.get('entry_mode')=='direct_speech'
                    and listening.get('wake_words')==[] and listening.get('state')=='WAITING_SPEECH',
                    'direct_speech_capture_policy_required')
        if conversation_mode=='half_duplex':
            require(listening.get('conversation_mode')=='half_duplex' and listening.get('voice_barge_in') is False,
                    'half_duplex_policy_required')
        require(diagnostic.get('error_code') == 'none' and diagnostic.get('capture_state') == 'RECORDING'
                and diagnostic.get('input_queue', {}).get('capacity_frames') == 8,
                'continuous_capture_snapshot_mismatch')
        frames.append(positive(diagnostic.get('audio_frontend', {}).get('frames')))
        armed.append(positive(diagnostic.get('counters', {}).get('armed')))
    require(len(set(armed)) == 1 and all(b > a for a, b in zip(frames, frames[1:])),
            'continuous_capture_progress_mismatch')
    last = samples[-1]
    require(last.get('pan') == dict(automatic_following=False, state='FAULT', pulse_us=None),
            'pan_safety_metadata_mismatch')
    business = last.get('business', {})
    require(business.get('started') is True and business.get('closed') is False
            and business.get('writer_held') is True and business.get('receipt_verified') is True,
            'board_writer_receipt_required')
    require(last.get('character', {}).get('state') == 'READY'
            and last.get('character', {}).get('production_selected') is True, 'character_pair_not_ready')
    require(last.get('native', {}).get('visible') is True, 'native_display_not_visible')
    require(live.get('operator_dialogue_acceptance') is not True
            and live.get('physical_audio_acceptance_passed') is not True,
            'operator_acceptance_requires_separate_update')
    policy = dict(automatic_on_ready=True, no_start_button_required=True,
        wake_word_required=wake_required,entry_mode='wake_word' if wake_required else 'direct_speech',
        conversation_mode=conversation_mode,
        explicit_pause_persistence='not_verified_in_receipts',
        cancel_current_turn_rearm='not_verified_in_receipts',
        actual_restart_pause_verified=False, cold_boot_listening_verified=False)
    if control is not None:
        require(control.get('root') == root and control.get('startup_sha256') == startup,
                'control_revision_binding_required')
        require(main_pid(control) == supervisor and control.get('gtk_pid') == gtk,
                'control_process_binding_mismatch')
        if (control.get('pause_preference_false_observed') is True
                and control.get('resume_preference_true_observed') is True):
            policy['explicit_pause_persistence'] = 'actual_disk_preference_roundtrip_verified'
        if control.get('cancel_rearm_passed') is True:
            policy['cancel_current_turn_rearm'] = 'actual_cancel_rearm_verified'
        # A synthetic restart check is distinct from an actual service restart.
        policy['synthetic_restart_preference_check_passed'] = (
            control.get('synthetic_restart_preference_check_passed') is True)
    return dict(root=root, startup_sha256=startup, source_manifest_sha256=manifest,
        component_pins=pins, supervisor_pid=supervisor, gtk_pid=gtk, camera_pid=camera,
        board_boot_id=boot, configuration_sha256=(digest(installed['configuration_sha256'])
            if 'configuration_sha256' in installed else None),
        frontend_options=business_options(installed), listening_policy=policy,
        continuous_capture_passed=True, priority_scope_passed=True,
        physical_microphone_opened=True, microphone_open=True,
        physical_audio_acceptance_passed=False, operator_asr_acceptance_passed=False,
        operator_playback_acceptance_passed=False,
        physical_audio_played=(live['physical_audio_played'] if type(live.get('physical_audio_played')) is bool else None),
        playing=last.get('playing') if type(last.get('playing')) is bool else None,
        following=False, pan_state='FAULT', pulse_us=None, automatic_listening=True)


def historical_snapshot(value):
    keys = ('status', 'updated_utc', 'updated_at', 'root', 'runtime', 'startup_sha256',
        'source_manifest_sha256', 'component_pins', 'supervisor_pid', 'gtk_pid', 'camera_pid',
        'board_boot_id', 'physical_microphone_opened', 'physical_audio_acceptance_passed',
        'last_verified_ui_supervisor_pid', 'last_verified_gtk_pid', 'last_verified_camera_pid')
    return {key: value[key] for key in keys if key in value}


def archive(value, revision):
    value.setdefault('listening_revision_history', []).append(dict(
        superseded_by=revision, previous=historical_snapshot(value)))


def tagged(text, body, revision):
    start, end = '<!-- '+TAG+' -->', '<!-- /'+TAG+' -->'
    require(text.count(start) <= 1 and text.count(end) <= 1, 'ambiguous_current_document_block')
    new = start+'\n'+body+'\n'+end+'\n'
    if start not in text:
        require(end not in text, 'incomplete_document_block')
        return new+'\n'+text
    require(end in text and text.index(start) < text.index(end), 'incomplete_document_block')
    begin, finish = text.index(start), text.index(end)+len(end)
    old = text[begin+len(start):text.index(end)].strip()
    history = ('\n<!-- archived-board-business-live-'+revision+' -->\n'
               '以下为本次更新前的历史现役段，已由上方新回执替代：\n'+old+'\n'
               '<!-- /archived-board-business-live-'+revision+' -->\n')
    return new+history+text[:begin]+text[finish:]


def narrative(current, evidence):
    options = json.dumps(current['frontend_options'], ensure_ascii=False, sort_keys=True)
    policy = current['listening_policy']
    pause = ('实际暂停/恢复后的磁盘偏好false→true往返已核验'
             if policy['explicit_pause_persistence'] == 'actual_disk_preference_roundtrip_verified'
             else '显式暂停应持久；本次输入未包含磁盘偏好往返通过回执')
    cancel = ('实际取消本轮后自动rearm已核验'
              if policy['cancel_current_turn_rearm'] == 'actual_cancel_rearm_verified'
              else '取消本轮应自动rearm；本次输入未包含该控制语义通过回执')
    return ('- 板端正式业务当前入口：'+current['root']+'；startup SHA '+current['startup_sha256']+
        '，'+str(current['component_pins'])+'份组件，source manifest SHA '+current['source_manifest_sha256']+'。\n'
        '- 本次实读supervisor '+str(current['supervisor_pid'])+'、GTK '+str(current['gtk_pid'])+
        '、相机 '+str(current['camera_pid'])+'、boot '+current['board_boot_id']+'；PID仅为本次观测，下次先现读。\n'+
        ('- 就绪后自动打开麦克风并聆听唤醒词，无需开始按钮；' if policy['wake_word_required'] else
         '- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；')+
        '连续采集与优先级作用域两门槛均有真实通过回执。'+
        ('当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。' if policy['conversation_mode']=='half_duplex' else '')+
        pause+'；'+cancel+'。未新增实际冷启动/重启验收声明。\n'
        '- 采用的前端配置仅按最终installed回执记录：'+options+'；不将此前候选或静态hash当作已上线。\n'
        '- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；'+
        '采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。\n'
        '- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。\n'
        '- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：'+
        '；'.join(item['path']+' SHA '+item['sha256'] for item in evidence.values())+'。')


def prepare(installed_path, ready_path, live_path, control_path=None):
    values, evidence = {}, {}
    for key, path in (('installed', installed_path), ('ready', ready_path), ('live', live_path),
                      ('control', control_path)):
        if path is not None:
            values[key], evidence[key] = local_receipt(path)
    current = validate(values['installed'], values['ready'], values['live'], values.get('control'))
    proof = sha(json.dumps(evidence, sort_keys=True).encode('utf-8'))
    current.update(status=STATUS, updated_utc=datetime.now(timezone.utc).isoformat(),
                   evidence=evidence, evidence_digest=proof)
    revision = current['startup_sha256'][:16]+'-'+proof[:12]
    before = {key: path.read_bytes() for key, path in TARGETS.items()}
    require(all(not path.is_symlink() and path.is_file() for path in TARGETS.values()),
            'regular_document_targets_required')
    documents = {key: json.loads(before[key].decode('utf-8-sig')) for key in
                 ('live', 'implementation', 'resume', 'character', 'coordination')}
    require(all(isinstance(value, dict) for value in documents.values()), 'document_objects_required')
    if documents['live'].get('verified_listening', {}).get('evidence_digest') == proof:
        return {}, before, dict(status='ALREADY_RECORDED', evidence_digest=proof, revision=revision)
    result = {}
    live = documents['live']; archive(live, revision)
    live.update(current); live['verified_listening'] = current
    result['live'] = encoded(live)
    for key in ('implementation', 'resume'):
        value = documents[key]; archive(value, revision)
        value.update(status=STATUS, updated_utc=current['updated_utc'])
        prod = value.setdefault('production', {})
        prod.setdefault('listening_revision_history', []).append(dict(
            superseded_by=revision, previous=historical_snapshot(prod)))
        prod.update(root=current['root'], runtime=current['root'],
            startup_sha256=current['startup_sha256'], source_manifest_sha256=current['source_manifest_sha256'],
            component_pins=current['component_pins'], last_verified_ui_supervisor_pid=current['supervisor_pid'],
            last_verified_gtk_pid=current['gtk_pid'], last_verified_camera_pid=current['camera_pid'],
            physical_microphone_opened=True, microphone_or_playback_started=True,
            physical_audio_acceptance_passed=False, operator_asr_acceptance_passed=False,
            operator_playback_acceptance_passed=False, audio_played=current['physical_audio_played'],
            active_body_cleanup_enabled=True, body_cleanup_enabled=True)
        value['production_business_live'] = live
        value['verified_listening'] = current
        result[key] = encoded(value)
    character = documents['character']; archive(character, revision)
    character.update({key: current[key] for key in ('root', 'startup_sha256', 'source_manifest_sha256',
        'component_pins', 'supervisor_pid', 'gtk_pid', 'camera_pid', 'physical_microphone_opened',
        'physical_audio_acceptance_passed', 'microphone_open', 'playing', 'following', 'pan_state', 'pulse_us')})
    character.update(status=STATUS, updated_utc=current['updated_utc'], listening=True, verified_listening=current)
    result['character'] = encoded(character)
    coordination = documents['coordination']; archive(coordination, revision)
    coordination['updated_at'] = current['updated_utc']
    switch = coordination.setdefault('production_UI_switch', {})
    switch.update(runtime=current['root'], startup_sha256=current['startup_sha256'],
        source_manifest_sha256=current['source_manifest_sha256'], component_pins=current['component_pins'])
    coordination['verified_listening'] = current
    result['coordination'] = encoded(coordination)
    body = narrative(current, evidence)
    for key in ('agents', 'analysis'):
        text = before[key].decode('utf-8-sig')
        result[key] = tagged(text, body, revision).encode('utf-8')
    previous = before['continuation'].decode('utf-8-sig')
    result['continuation'] = ('板端自动聆听：最终真实采集回执已核，真人音频验收仍待完成。\n\n'+
        body+'\n\n以下保留更新前历史记录，其入口/PID/麦克风状态已由上方新回执替代。\n\n'+previous).encode('utf-8')
    return result, before, dict(status='VERIFIED_DOCUMENT_PLAN', source_only_preparation=True,
        revision=revision, evidence_digest=proof, current=current,
        changes=[dict(path=str(TARGETS[key]), before_sha256=sha(before[key]), after_sha256=sha(raw))
                 for key, raw in result.items()])


def atomic(path, raw):
    temp = path.with_name(path.name+'.verified-listening-new')
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(str(temp), str(path))
    finally:
        if temp.exists():
            temp.unlink()


def apply(result, before, report):
    if not result:
        return report
    # One fixed local document set; never derive a target from receipt data.
    for item in report['current']['evidence'].values():
        require(sha((OWNER/item['path']).read_bytes()) == item['sha256'], 'evidence_changed_since_prepare')
    for key in result:
        require(TARGETS[key].read_bytes() == before[key], 'document_changed_since_prepare')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt = HERE/'state_update_receipts'/(report['revision']+'-'+stamp)
    receipt.mkdir(parents=True, exist_ok=False)
    for key in result:
        (receipt/(key+'.before')).write_bytes(before[key])
    (receipt/'plan.json').write_bytes(encoded(report))
    changed = []
    try:
        for key, raw in result.items():
            require(TARGETS[key].read_bytes() == before[key], 'document_changed_during_apply')
            atomic(TARGETS[key], raw); changed.append(key)
        for key, raw in result.items():
            require(TARGETS[key].read_bytes() == raw, 'document_postwrite_hash_mismatch')
    except Exception:
        conflicts = []
        for key in reversed(changed):
            # Do not overwrite an independent concurrent documentation writer.
            if TARGETS[key].read_bytes() == result[key]:
                atomic(TARGETS[key], before[key])
            else:
                conflicts.append(key)
        (receipt/'result.json').write_bytes(encoded(dict(
            status='ROLLBACK_CONFLICT_REVIEW_REQUIRED' if conflicts else 'ROLLED_BACK',
            changed=changed, conflicts=conflicts)))
        raise
    (receipt/'result.json').write_bytes(encoded(dict(status='LOCAL_DOCUMENTS_UPDATED',
        revision=report['revision'], no_deployment_or_service_actions=True)))
    return dict(status='LOCAL_DOCUMENTS_UPDATED', receipt=str(receipt), changes=len(changed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', required=True, type=Path)
    parser.add_argument('--ready', required=True, type=Path)
    parser.add_argument('--live', required=True, type=Path)
    parser.add_argument('--control-semantics', type=Path)
    parser.add_argument('--apply', action='store_true', help='Explicit local documentation write after root review')
    args = parser.parse_args()
    result, before, report = prepare(args.installed, args.ready, args.live, args.control_semantics)
    print(json.dumps(apply(result, before, report) if args.apply else report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except ReceiptRejected as exc:
        raise SystemExit('REJECTED: '+str(exc))
