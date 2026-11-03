"""Record only final verified latency revision and refresh current model owners."""
from datetime import datetime,timezone
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
PROJECT=HERE.parents[3]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    final=read(HERE/'final_runtime.json')
    live_path=HERE.parent/'PRODUCTION_BUSINESS_LIVE.json';live=read(live_path)
    assert live['startup_sha256']==final['board']['startup_sha256']
    assert live['continuous_capture_passed'] is True and live['priority_scope_passed'] is True
    assert final['board']['automatic_listening_enabled'] is True and final['board']['capture_error']=='none'
    assert final['windows']['status']=='READY' and final['windows']['keep_alive']==-1
    controls=[read(HERE/('control_round'+str(n)+'.json')) for n in (1,2)]
    for control in controls:
        assert control['startup_sha256']==live['startup_sha256'] and control['gtk_pid']==live['gtk_pid']
        assert all(control[key] is True for key in ('pause_preference_false_observed','resume_preference_true_observed',
            'cancel_rearm_passed','pause_closed_microphone','pause_released_owned_arecord','model_worker_reused_on_rearm'))
    comparison=read(HERE/'public_tts_comparison.json')
    asr2=read(HERE/'public_asr_diagnostic.json');asr3=read(HERE/'public_asr_threads3.json')
    result=dict(status='RESPONSE_LATENCY_REVISION_ACTIVE_OPERATOR_TIMING_PENDING',
        updated_utc=datetime.now(timezone.utc).isoformat(),startup_sha256=live['startup_sha256'],
        source_manifest_sha256=live['source_manifest_sha256'],component_pins=live['component_pins'],
        supervisor_pid=live['supervisor_pid'],gtk_pid=live['gtk_pid'],windows=final['windows'],
        ordinary_reply_sentence_streaming=True,complete_playback_ack_preserved=True,
        asr_threads=3,asr_same_public_wav_seconds=asr2['audio_seconds'],
        asr_threads2_ms=[x['asr_ms'] for x in asr2['runs']],
        asr_threads3_ms=[x['asr_ms'] for x in asr3['runs']],asr_comparison_gui_closed=True,
        tts_first_deliverable_before_ms=comparison['cases'][0]['first_deliverable_pcm_ms'],
        tts_first_deliverable_after_ms=comparison['cases'][1]['first_deliverable_pcm_ms'],
        full_llm_json_validation_retained=True,summary_retry_backoff_seconds=[3,6,12,24,48,60],
        cancelled_frame_control_ack_fixed=True,actual_pause_resume_cancel_rounds_passed=2,
        local_tests_unique_passed=84,local_test_subcases_passed=37,
        operator_asr_latency_acceptance=False,audible_first_sound_measured=False,
        long_run_fps_acceptance=False,weights_moved=False,private_data_replayed=False,
        evidence=['public_tts_comparison.json','public_asr_diagnostic.json','public_asr_threads3.json',
                  'model_warm.json','model_after.json','final_runtime.json','control_round1.json','control_round2.json',
                  'cancel_timeline_candidate/root_tests.xml'])
    backup=HERE/'final_document_before';backup.mkdir(exist_ok=False)
    targets=[live_path,OWNER/'IMPLEMENTATION_STATE.json',HERE.parent/'RESUME_VERIFICATION.json',
             HERE.parent/'CHARACTER_SWITCH.json',OWNER/'coordination/runtime_windows.json']
    for index,path in enumerate(targets):
        raw=path.read_bytes();(backup/(str(index)+'-'+path.name)).write_bytes(raw)
        data=json.loads(raw.decode('utf-8-sig'));data['response_latency']=result
        if path==live_path:data['windows_model_owner']=final['windows']
        if isinstance(data.get('production_business_live'),dict):
            data['production_business_live']['windows_model_owner']=final['windows']
            data['production_business_live']['response_latency']=result
        write(path,data)
    note=('- 响应优化已部署：ASR显式3线程、普通回答逐句TTS交付、27B keep_alive=-1、失败摘要3→6→12→24→48→60秒退避；模型/权重/阈值/原8帧队列/完整播放ACK不变。'
          '公开5.614625秒录音在GUI关闭时2线程4700/4718ms、3线程3741/4283ms；三句同文本真实TTS首段可交付2037→676ms，非扬声器首音或整机通过。'
          '计时入口board_business.dialogue.latency；现场ASR/听感、长稳仍待验。Windows当前host '+str(final['windows']['host_pid'])+
          '/TTS '+str(final['windows']['tts_pid'])+'/固定11435 daemon '+str(final['windows']['fixed_daemon_pid'])+'（下次现读）；详见integration/response_latency/STATUS.json。\n')
    for index,path in enumerate((PROJECT/'AGENTS.md',PROJECT.parent/'语言模型分析/README.md')):
        raw=path.read_bytes();(backup/('text'+str(index)+'.before')).write_bytes(raw)
        text=raw.decode('utf-8-sig');tag='<!-- /board-business-live-20261030 -->';assert text.count(tag)==1
        path.write_text(text.replace(tag,note+tag,1),encoding='utf-8')
    report=('响应延迟优化（2026-10-31）\n\n'+note+'\n'
        '当前板端startup '+live['startup_sha256']+'，'+str(live['component_pins'])+'份组件。\n'
        '识别对照只用固定公开录音，未读取用户语音；1线程约7.9秒更慢，未采用。3线程是本轮小样本结果，不能扩大为整机普遍提速。\n'
        '逐句播放仍先完整校验LLM输出。每句及背压出队重新核对有效记忆，失败或取消不确认完整播放。\n'
        '取消时原生计算可能比完整帧计数多推进一帧，原控制回执会因此误报。现仅对STOP/GATE_RELEASE闭合回执允许这一帧残留，FRAME校验保持。'
        '已通过两轮实机暂停/恢复/取消，复用同一模型工作进程并释放原采集进程；自动聆听恢复，12秒连续采集通过。\n'
        '27B暖态短问生成约4—5秒，主要是逐token解码；常驻避免另外冷加载，不代表消除该等待。'
        '已实读实际对话请求后的远期驻留期限，未人为等30分钟声称长时间空闲实测。\n'
        '正常Stop保留常驻27B；需要释放项目显存时用现有start_inference.ps1 -Action Stop -ReleaseOwnedModel，保持原所属模型/空闲校验。\n'
        '下一轮无需启动按钮，直接说“雪妃，请用三句简短的话告诉我去图书馆前要准备什么。”，随后读取纯metadata分段耗时；不归档原文/PCM。\n')
    (OWNER/'响应延迟优化_20261031.txt').write_text(report,encoding='utf-8')
    write(HERE/'STATUS.json',result)
    checkpoint=read(HERE/'WORK_IN_PROGRESS.json');checkpoint.update(status=result['status'],startup_sha256=live['startup_sha256'],
        source_manifest_sha256=live['source_manifest_sha256'],component_pins=live['component_pins'],board_ui='ACTIVE_AUTOMATIC_LISTENING_VERIFIED',pending=['operator dialogue latency and listening acceptance'])
    checkpoint['verified'].update(tests_unique_passed=84,tests_subcases_passed=37,actual_pause_resume_cancel_rounds_passed=2)
    write(HERE/'WORK_IN_PROGRESS.json',checkpoint)
    print(json.dumps(dict(status=result['status'],startup_sha256=result['startup_sha256'],report=str(OWNER/'响应延迟优化_20261031.txt')),ensure_ascii=True))
