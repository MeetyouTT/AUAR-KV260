"""Record subjective latency acceptance without changing running services."""
import json
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORKSPACE = PROJECT.parent
acceptance = {
    'date': '2026-10-21',
    'status': 'HUMAN_LATENCY_IMPROVEMENT_ACCEPTED',
    'question': '刚才这版从你说完到听到汐蓝开口，和之前相比怎样？',
    'user_feedback': '明显快了，等待可以接受',
    'human_latency_verified': True,
    'scope': 'Explicit subjective feedback for the current first-sentence optimization plus echo guard. Not a new measured latency threshold or long-duration acceptance.',
    'active_runtime_at_test': '/home/root/aura-echo-verify-20261021/candidate-a3c8e50c2797/runtime',
    'first_sentence_chat_enabled': True,
    'echo_and_barge_in_acceptance': '../2026-10-21_echo_barge_in/human_acceptance.json',
    'long_duration_verified': False,
    'services_or_listening_changed': False,
}
(HERE / 'human_latency_acceptance.json').write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepend(path, text, after_title=False):
    original = path.read_text(encoding='utf-8-sig')
    marker = '<!-- latency-human-accepted-20261021 -->'
    if marker in original:
        return
    note = marker + '\n' + text + '\n\n'
    if after_title:
        title, rest = original.split('\n', 1)
        original = title + '\n\n' + note + rest.lstrip('\n')
    else:
        original = note + original
    path.write_text(original, encoding='utf-8')


prepend(HERE / 'README.md', '最新真人反馈：“明显快了，等待可以接受”，当前首句优化与回声保护组合的主观延迟体验验收通过，见human_latency_acceptance.json。此前用户也确认“安静时正常播放，插话后停下并回答新问题”。不把主观通过当固定秒数、噪声/多人或长稳通过；下方待反馈为历史阶段记录。', True)
prepend(PROJECT / 'deliverables/2026-10-21_echo_barge_in/README.md', '用户进一步确认回答延迟“明显快了，等待可以接受”，本轮主观延迟体验通过；与此前“安静时正常播放，插话后停下并回答新问题”共同构成当前组合的受控验收。见../2026-10-21_response_latency/human_latency_acceptance.json。噪声/多人和长稳仍未验收。', True)
prepend(PROJECT / 'AGENTS.md', '- 最新明确反馈：“明显快了，等待可以接受”，当前首句优化+回声核验组合的主观延迟验收通过，证据deliverables/2026-10-21_response_latency/human_latency_acceptance.json。此前安静播放和真人插话亦已通过。保持当前运行方案及免点击选择；不为继续压数值主动切换模型或中断服务。下方“延迟待反馈”仅为历史。噪声/多人、重复自身台词、个人长期记忆及持续实聊长稳仍不能填通过。')
note = '[回答延迟真人验收（2026-10-21）](../语音共享文件/deliverables/2026-10-21_response_latency/human_latency_acceptance.json)：用户确认“明显快了，等待可以接受”。结合此前安静播放和真人插话通过，当前首句优化与回声保护组合受控体验验收通过。噪声/多人和持续实聊长稳仍未验收；下方待反馈状态保留作历史。'
prepend(WORKSPACE / '语言模型分析/README.md', note)
prepend(WORKSPACE / '语言模型分析/玩偶系统完成度评估_20261020.md', note, True)
runpy.run_path(str(PROJECT / 'deliverables/2026-10-21_echo_barge_in/finalize_metadata.py'), run_name='__main__')
latency = json.loads((HERE / 'verification_summary.json').read_text(encoding='utf-8'))
echo = json.loads((PROJECT / 'deliverables/2026-10-21_echo_barge_in/verification_summary.json').read_text(encoding='utf-8'))
assert latency['human_latency_verified'] and echo['human_latency_verified']
assert echo['human_echo_verified'] and echo['human_barge_in_verified_on_this_build']
assert not latency['long_duration_verified'] and not echo['long_duration_verified']
print(json.dumps({'latency_status': latency['status'], 'echo_status': echo['status'], 'long_duration_verified': False}))
