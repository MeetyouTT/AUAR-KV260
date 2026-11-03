"""Record explicit user feedback and read-only, text-free runtime metadata."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORKSPACE = PROJECT.parent
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import json,re,subprocess,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config=Path(re.findall(r'--config (\S+)',unit)[-1])
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert str(config) in effective
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
hf=u['handsfree_dialogue'];b=u.get('voice_barge_in',{})
def numbers(value):
 if isinstance(value,dict):return {k:numbers(v) for k,v in value.items() if isinstance(v,(dict,list,int,float,bool))}
 if isinstance(value,list):return [numbers(v) for v in value if isinstance(v,(dict,list,int,float,bool))]
 return value
turns=[]
for t in u.get('turns',[]):
 turns.append({k:numbers(t[k]) for k in ('generation','audio_complete','request_to_answer_seconds','request_to_feedback_or_audio_seconds','server_metrics') if k in t})
print(json.dumps({'runtime':json.loads(config.read_text())['runtime'],
 'monitor_enabled':hf['enabled'],'handsfree_state':hf['state'],
 'diagnostics':hf.get('diagnostics',{}),'phase':u.get('phase'),
 'audio_output_state':u.get('audio_output_state'),
 'voice_barge_in':{k:b.get(k) for k in ('enabled','interrupted_turns','error','speech_verification','last_detection_to_stop_ms')},
 'completed_turns':u.get('automatic_conversation',{}).get('completed_turns'),
 'turn_timing_metadata':turns,'conversation_text_exported':False,
 'service_or_listening_changed':False}))
'''

try:
    snapshot = json.loads(ssh('python3 -B -', REMOTE, timeout=18))
except Exception as exc:
    snapshot = {'readback_unavailable': type(exc).__name__, 'service_or_listening_changed': False}
(HERE / 'human_acceptance_readback.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
acceptance = {
    'date': '2026-10-21',
    'status': 'HUMAN_CONTROLLED_SELF_PLAYBACK_AND_INTERRUPTION_PASSED',
    'active_runtime_at_test': '/home/root/aura-echo-verify-20261021/candidate-a3c8e50c2797/runtime',
    'question': '请正对汐蓝说“讲一个小故事”，先保持安静几秒，再在它回答时说“先停一下，你叫什么名字？”这次结果怎样？',
    'user_feedback': '安静时正常播放，插话后停下并回答新问题',
    'self_playback_continued_while_user_silent': True,
    'old_answer_stopped_on_user_interruption': True,
    'new_question_answer_audible': True,
    'basis': 'Explicit human feedback; diagnostic counters alone do not establish intent.',
    'scope': 'One controlled test on this build. Not television, multi-speaker, long-duration, or latency acceptance.',
    'human_latency_verified': False, 'long_duration_verified': False,
    'readback_evidence': 'human_acceptance_readback.json',
}
(HERE / 'human_acceptance.json').write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def add_note(path, marker, text, after_title=False):
    original = path.read_text(encoding='utf-8-sig')
    if marker in original:
        return
    note = marker + '\n' + text + '\n\n'
    if after_title:
        first, rest = original.split('\n', 1)
        original = first + '\n\n' + note + rest.lstrip('\n')
    else:
        original = note + original
    path.write_text(original, encoding='utf-8')


add_note(HERE / 'README.md', '<!-- human-acceptance-20261021 -->',
    '最新真人验收：用户明确反馈“安静时正常播放，插话后停下并回答新问题”。a3c8本次受控自身播音连续性及真人插话通过，见human_acceptance.json；延迟、噪声/多人和长稳仍未验收。以下部署时的“待复测”保留作阶段记录。', True)
add_note(PROJECT / 'AGENTS.md', '<!-- echo-human-accepted-20261021 -->',
    '- 用户已明确反馈“安静时正常播放，插话后停下并回答新问题”：a3c8当前版一次受控回声/真人打断验收通过，依据human_acceptance.json，不把计数当意图证明。旧部署快照/下方待复测为历史；当前summary以此真人反馈更新。首句延迟、噪声/多人及长稳仍未验收，保留当前监听选择；后续渲染继续从a3c8合并并保留取消前核验，PC首句/记忆规则保持。')
note = '[回声与插话真人验收（2026-10-21）](../语音共享文件/deliverables/2026-10-21_echo_barge_in/human_acceptance.json)：用户确认“安静时正常播放，插话后停下并回答新问题”，a3c8一次受控自身播音连续性和真人插话通过。回答延迟、噪声/多人和长稳仍待验收；下方待复测状态为历史。'
add_note(WORKSPACE / '语言模型分析/README.md', '<!-- echo-human-accepted-20261021 -->', note)
add_note(WORKSPACE / '语言模型分析/玩偶系统完成度评估_20261020.md', '<!-- echo-human-accepted-20261021 -->', note, True)
add_note(PROJECT / 'deliverables/2026-10-21_response_latency/README.md', '<!-- echo-human-accepted-20261021 -->',
    '用户已确认回声修复版“安静时正常播放，插话后停下并回答新问题”，本次受控连续性/插话通过。首句提速保持，主观回答等待仍待单独反馈，不把此次结果当延迟验收。', True)
print(json.dumps({'human_controlled_test_passed': True,
                  'readback': snapshot, 'human_latency_verified': False}, ensure_ascii=False))
