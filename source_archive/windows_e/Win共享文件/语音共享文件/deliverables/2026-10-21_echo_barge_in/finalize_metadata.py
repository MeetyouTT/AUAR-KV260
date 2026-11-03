"""Archive only the verified source files and factual deployment evidence."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORKSPACE = PROJECT.parent


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepend_once(path, marker, text, after_title=False):
    original = path.read_text(encoding='utf-8-sig')
    if marker in original:
        return
    addition = marker + '\n' + text.strip() + '\n\n'
    if after_title:
        title, tail = original.split('\n', 1)
        original = title + '\n\n' + addition + tail.lstrip('\n')
    else:
        original = addition + original
    path.write_text(original, encoding='utf-8')


deployment = read_json(HERE / 'deployment.json')
candidate = read_json(HERE / 'candidate.json')
names = [
    'aura/tools/barge_in_capture.py',
    'aura/tools/barge_in_recording.py',
    'aura/board/runtime/audio/barge_verify.py',
    'aura/tests/framework/test_barge_verification.py',
]
manifest = {}
for name in names:
    source = PROJECT / name
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == candidate['files'][name], name
    target = HERE / 'candidate_sources' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    manifest[name] = digest
write_json(HERE / 'source_manifest.json', {
    'date': '2026-10-21', 'runtime': deployment['runtime'],
    'files': manifest, 'contains_models_or_private_data': False,
})
probe = deployment['acoustic_probe']
summary = {
    'date': '2026-10-21',
    'status': 'DEPLOYED_LISTENING_RESTORED_WAITING_HUMAN_ECHO_AND_BARGE_IN_RETEST',
    'actual_runtime_ui': deployment['runtime'],
    'monitor_enabled': deployment['monitor_enabled'],
    'pc_tests_passed': 104, 'pc_tests_skipped': 1,
    'board_tests_passed': 304,
    'board_preflight_passed': candidate['preflight_passed'],
    'full_hidden_gtk_passed': True,
    'controlled_playback': {
        'seconds': probe['seconds'],
        'confirmed_interruptions': probe['confirmed_interruptions'],
        'reference_frames': probe['reference_frames'],
        'reference_gaps': probe['reference_gaps'],
        'verification_checks': probe['speech_verification']['stats']['checks'],
        'actual_cpu_asr_invoked_during_this_playback': False,
        'limitation': 'No candidate occurred; this quiet run did not exercise live ASR rejection.',
        'raw_probe_field_correction': 'deployment.json actual_cpu_asr_used is an erroneous static configuration flag; checks=0 is authoritative. Raw evidence retained.',
    },
    'actual_cpu_asr_reference_validation_passed': True,
    'human_echo_verified': False,
    'human_barge_in_verified_on_this_build': False,
    'human_latency_verified': False,
    'long_duration_verified': False,
    'pc_restarted': deployment['pc_restarted'],
    'pc_first_sentence_chat_preserved': True,
    'camera_unchanged': deployment['camera_unchanged'],
    'identity_database_unchanged': deployment['identity_database_unchanged'],
    'operator_microphone_audio_saved': False,
    'llm_weights_copied': False,
    'evidence': ['deployment.json', 'tests_pc.log', 'tests_log.log',
                 'preflight_log.log', 'smoke.json', 'asr_reference_validation.json',
                 'quiet_reproduction.json', 'source_manifest.json'],
    'limitations': [
        'Confirmation adds roughly several hundred milliseconds; cancellation callback timing excludes this wait.',
        'Unclear or unavailable ASR preserves old output and may miss a genuine interruption.',
        'A user repeating current output may be conservatively rejected.',
        'Television, multiple speakers, and sustained conversation remain unverified.',
    ],
}
acceptance_path = HERE / 'human_acceptance.json'
human_accepted = acceptance_path.exists() and read_json(acceptance_path).get('status') == 'HUMAN_CONTROLLED_SELF_PLAYBACK_AND_INTERRUPTION_PASSED'
latency_acceptance_path = PROJECT / 'deliverables/2026-10-21_response_latency/human_latency_acceptance.json'
latency_accepted = latency_acceptance_path.exists() and read_json(latency_acceptance_path).get('human_latency_verified') is True
if human_accepted:
    summary.update(status='HUMAN_CONTROLLED_ECHO_AND_BARGE_IN_PASSED_LATENCY_PENDING',
                   human_echo_verified=True, human_barge_in_verified_on_this_build=True,
                   human_acceptance_scope='One controlled test, per explicit user feedback.')
    summary['evidence'].extend(['human_acceptance.json', 'human_acceptance_readback.json'])
if latency_accepted:
    summary['human_latency_verified'] = True
    summary['human_latency_acceptance'] = '../2026-10-21_response_latency/human_latency_acceptance.json'
    if human_accepted:
        summary['status'] = 'HUMAN_CONTROLLED_ECHO_BARGE_IN_AND_LATENCY_PASSED'
write_json(HERE / 'verification_summary.json', summary)
observation_path = PROJECT / 'deliverables/2026-10-20_listening_timing/passive_trial_20261021_012529.json'
if observation_path.exists():
    rows = read_json(observation_path)['rows']
    observation = {
        'source': str(observation_path), 'samples': len(rows),
        'states': sorted({row['handsfree']['state'] for row in rows}),
        'submitted_at_end': rows[-1]['handsfree']['diagnostics']['submitted'],
        'interrupted_at_end': rows[-1]['barge_in']['interrupted_turns'],
        'monitor_enabled_at_end': rows[-1]['handsfree']['enabled'],
        'human_verified': False,
        'scope': '35-second passive metadata observation; no submitted dialogue, so no human echo or latency acceptance.',
    }
    write_json(HERE / 'passive_trial_summary.json', observation)
    summary['passive_trial'] = observation
    summary['evidence'].append('passive_trial_summary.json')
    write_json(HERE / 'verification_summary.json', summary)
with zipfile.ZipFile(HERE / 'verified_changes.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in names:
        archive.write(HERE / 'candidate_sources' / name, name)
    archive.write(HERE / 'source_manifest.json', 'source_manifest.json')
    archive.write(HERE / 'verification_summary.json', 'verification_summary.json')
    if human_accepted:
        archive.write(acceptance_path, 'human_acceptance.json')
    if latency_accepted:
        archive.write(latency_acceptance_path, 'human_latency_acceptance.json')

latency_dir = PROJECT / 'deliverables/2026-10-21_response_latency'
latency = read_json(latency_dir / 'verification_summary.json')
latency['status'] = ('ECHO_AND_BARGE_IN_HUMAN_PASSED_WAITING_LATENCY_FEEDBACK' if human_accepted
                     else 'LATENCY_DEPLOYED_ECHO_GUARD_ADDED_WAITING_HUMAN_RETEST')
if latency_accepted:
    latency['status'] = 'HUMAN_LATENCY_ACCEPTED_WITH_ECHO_AND_BARGE_IN_FIX'
latency['followup_echo_guard_human_verified'] = human_accepted
latency.setdefault('actual_runtime_ui_at_latency_deployment', latency['actual_runtime_ui'])
latency['actual_runtime_ui'] = deployment['runtime']
latency['reported_echo_failure_before_fix'] = '我注意到你刚刚把自己发出的声音当成我在说话而中断了语音输出'
latency['human_feedback'] = (read_json(latency_acceptance_path)['user_feedback'] if latency_accepted
                             else latency['reported_echo_failure_before_fix'])
latency['human_latency_verified'] = latency_accepted
if latency_accepted:
    latency['human_latency_acceptance'] = 'human_latency_acceptance.json'
    if 'human_latency_acceptance.json' not in latency['evidence']:
        latency['evidence'].append('human_latency_acceptance.json')
latency['followup_echo_guard'] = '../2026-10-21_echo_barge_in/verification_summary.json'
write_json(latency_dir / 'verification_summary.json', latency)
prepend_once(latency_dir / 'README.md', '<!-- echo-followup-20261021 -->',
    '最新真人反馈为“我注意到你刚刚把自己发出的声音当成我在说话而中断了语音输出”。首句优化保留，但本轮真人延迟/连续性未通过验收。已部署板端取消前转写核验保护并恢复监听；安静播放单次无误触发，尚待真人插话复测。见[回声修复记录](../2026-10-21_echo_barge_in/README.md)。', True)

prepend_once(PROJECT / 'AGENTS.md', '<!-- echo-barge-verify-20261021 -->', '''
- 用户反馈自身播音被误当插话，已优先部署取消前ASR核验。当前有效UI根 `/home/root/aura-echo-verify-20261021/candidate-a3c8e50c2797/runtime`，新增独立 `zzzz-aura-echo-verify-20261021.conf`，原4个drop-in保留。以后渲染/动作候选必须从新根合并，保留新增 `board/runtime/audio/barge_verify.py` 及修改的 `tools/barge_in_capture.py`、`tools/barge_in_recording.py`，不能用e064旧候选覆盖。疑似语音先积累约600ms有界窗口，最多一个异步转写/1.5秒，匹配自身正文或不明确/失败则保留回答；不同新话才取消并沿原完整PCM提交。ACK交接不得将未核验候选直接提交；保留聆听时序/身份归属/记忆/原渲染/pan。代价是几百毫秒确认时间，重复台词可能被保守忽略，非声纹/完整双讲识别。
- 104项PC通过/1跳过、304项板端/预检/完整隐藏GTK通过；实际CPU ASR自身0.8/1.6秒片段判echo，另一问题判new_speech。用户再次明确安静立即测试后，实放9.21秒、0确认插话、461参考帧/0断流，但checks=0，不能写实际触发ASR否决或真人验收通过。原probe actual_cpu_asr_used静态标记错误已在清单/README解释，原始证据不改。正式已恢复免点击true，PC首句配置/记忆保持；未重启PC/相机，camera PID987/epoch d457a35735144f038b08b933c0033c9e及身份库SHA保持。真人安静播放+插话与延迟仍待本版本复测。动画任务已获授权同步，避开用户开口窗口，旧10帧候选需合入新保护。证据 `deliverables/2026-10-21_echo_barge_in/README.md`、`deployment.json`、`verification_summary.json`。未保存额外麦克风音频/复制模型；大语言模型仍D盘。
<!-- /echo-barge-verify-20261021 -->
''')
note = '[回声误打断修复（2026-10-21）](../语音共享文件/deliverables/2026-10-21_echo_barge_in/README.md)：用户报告自身播音被当成插话，已上线取消前转写核验保护，当前UI为a3c8，免点击监听开启，原PC首句优化保留。104项PC/304项板端及隐藏界面通过；安静实放9.21秒未误触发，但无待核验候选，不能称现场ASR否决或真人通过。真人安静播放、真实插话及延迟待复测；长稳仍未验收。下方旧根与阶段验收保留作历史。'
prepend_once(WORKSPACE / '语言模型分析/README.md', '<!-- echo-current-20261021 -->', note)
prepend_once(WORKSPACE / '语言模型分析/玩偶系统完成度评估_20261020.md', '<!-- echo-current-20261021 -->', note, True)
print(json.dumps({'runtime': deployment['runtime'], 'archived_files': len(names),
                  'human_verified': human_accepted, 'metadata_updated': True}, ensure_ascii=False))
