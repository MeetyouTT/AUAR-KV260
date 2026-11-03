"""Keep a final metadata receipt and append the current no-wake policy."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
PROJECT=HERE.parents[3]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

if __name__=='__main__':
    current=read(HERE.parent/'PRODUCTION_BUSINESS_LIVE.json')
    policy=current['listening_policy']
    assert policy['wake_word_required'] is False and policy['entry_mode']=='direct_speech'
    installed=read(HERE.parent/'listening_entry_fix/actual_automatic-listening-v4-direct-speech.json')
    assert current['startup_sha256']==installed['startup_sha256']
    control=read(HERE.parent/'listening_entry_fix/actual_control_semantics.json')
    assert control['startup_sha256']==current['startup_sha256'] and control['wake_word_required'] is False
    assert all(control[k] is True for k in ('pause_preference_false_observed','resume_preference_true_observed',
        'cancel_rearm_passed','pause_closed_microphone','pause_released_owned_arecord','model_worker_reused_on_rearm'))
    assert current['continuous_capture_passed'] is True and current['priority_scope_passed'] is True
    receipts={}
    for name,path in (
        ('installed',HERE.parent/'listening_entry_fix/actual_automatic-listening-v4-direct-speech.json'),
        ('ready',HERE.parent/'production_business_acceptance/actual_ready.json'),
        ('control',HERE.parent/'listening_entry_fix/actual_control_semantics.json'),
        ('live',HERE.parent/'listening_entry_fix/actual_live_listening.json')):
        raw=path.read_bytes();out=HERE/('actual_'+name+'.json')
        if out.exists():assert out.read_bytes()==raw
        else:out.write_bytes(raw)
        receipts[name]=dict(path=out.name,sha256=hashlib.sha256(raw).hexdigest())
    result=dict(status='DIRECT_SPEECH_ACTIVE',startup_sha256=current['startup_sha256'],
        source_manifest_sha256=current['source_manifest_sha256'],component_pins=current['component_pins'],
        board_boot_id=current['board_boot_id'],supervisor_pid=current['supervisor_pid'],gtk_pid=current['gtk_pid'],
        camera_pid=current['camera_pid'],wake_word_required=False,entry_mode='direct_speech',
        automatic_listening=True,explicit_pause_persisted=True,cancel_rearm_verified=True,
        continuous_capture_verified=True,physical_dialogue_acceptance=False,
        identity_permissions_changed=False,private_data_replayed=False,previous_latency_changes_retained=True,
        evidence=receipts)
    (HERE/'STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    note=('- 用户已要求取消唤醒词：正式入口为direct_speech，wake_word_required=false，wake_words为空。'
        '开机就绪后直接说话，首句仍检查有效音频、ASR及当前会话归属；角色称呼不再作为进入条件。'
        '身份权限、播放完整回执和防自收音保持；前轮ASR3线程、逐句TTS及模型常驻保留。'
        '实机自动聆听、暂停/恢复/取消和12秒连续采集通过，真人首句对话尚待现场验证。'
        '来源：integration/direct_speech_entry/STATUS.json。\n')
    for path in (PROJECT/'AGENTS.md',PROJECT.parent/'语言模型分析/README.md'):
        text=path.read_text(encoding='utf-8-sig');tag='<!-- /board-business-live-20261030 -->'
        assert text.count(tag)==1
        if note not in text:path.write_text(text.replace(tag,note+tag,1),encoding='utf-8')
    report=('免唤醒词对话已启用\n\n'+note+'\n当前startup '+current['startup_sha256']+'。\n'
        '直接测试：“请用三句简短的话告诉我去图书馆前要准备什么。”\n'
        '不需要先喊“雪妃”，也不需要点击开始聆听；显式暂停后需恢复聆听。\n')
    (OWNER/'取消唤醒词_20261031.txt').write_text(report,encoding='utf-8')
    print(json.dumps(result))
