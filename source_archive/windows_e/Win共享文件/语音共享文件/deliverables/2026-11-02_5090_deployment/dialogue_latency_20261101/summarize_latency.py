"""Summarize two completed live turns, excluding the pre-observation baseline."""
import datetime
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'observation02/observations.jsonl'
rows=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
events=[r for r in rows if r.get('event')=='TURN_COMPLETED']
assert len(events)==2
baseline=next(r for r in rows if r['event']=='BASELINE')
assert all(e['turn_hash']!=baseline['baseline']['ack']['turn_hash'] for e in events)
turns=[]
for event in events:
    group=[r for r in rows if r.get('event')=='SAMPLE' and r.get('turn_hash')==event['turn_hash']]
    complete=[r for r in group if r.get('latency',{}).get('complete') is True]
    assert complete
    final=complete[-1];latency=final['latency'];prepare=latency['prepare']
    assert latency['error_class']=='none'
    ack=[r for r in group if r['ack']['turn_hash']==event['turn_hash'] and r['ack']['committed'] is True]
    assert ack
    capture=next(r['recording_metadata'] for r in group if r.get('recording_metadata'))
    speaking=next(r for r in group if r.get('phase')=='SPEAKING')
    turns.append({'ordinal':event['ordinal'],'asr_ms':latency['asr_ms'],
        'context_ms':prepare['context_ms'],'llm_rpc_ms':prepare['llm_rpc_ms'],'llm_calls':prepare['llm_calls'],
        'tts_rpc_ms':prepare['tts_rpc_ms'],'tts_calls':prepare['tts_calls'],
        'first_tts_ready_from_prepare_ms':prepare['first_tts_ready_ms'],
        'first_audio_queued_from_worker_ms':latency['first_audio_queued_ms'],
        'worker_total_ms':latency['worker_total_ms'],
        'capture_duration_seconds':capture['duration_seconds'],
        'capture_complete_to_observed_speaking_ms':speaking['board_mono']*1000-capture['ended_mono_ms'],
        'full_playback_ack_committed':True,
        'progress_backpressure_wait_ms':final['job_diagnostics']['progress_wait_ms'],
        'current_turn_underrun_packets':final['audio_output']['turn_underrun_packets'],
        'current_turn_late_rebases':final['audio_output']['turn_late_rebases'],
        'guard_total_over_whole_response_ms':final['job_diagnostics']['guard_total_ms'],
        'speaker_first_audio_acoustically_measured':False})
means={key:sum(t[key] for t in turns)/2 for key in ('asr_ms','context_ms','llm_rpc_ms','tts_rpc_ms',
    'first_audio_queued_from_worker_ms','capture_complete_to_observed_speaking_ms')}
result={'schema':'aura-two-live-turn-latency-result-1',
    'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'measurement_source':str(source),'completed_turns':2,'baseline_turn_excluded':True,
    'both_full_playback_receipts_committed':True,'turns':turns,'means_ms':means,
    'largest_measured_generation_stage':'full_llm_rpc','next_largest':'board_asr',
    'measured_pipeline':'ASR then complete LLM response then first TTS PCM',
    'sample_interval_seconds':0.25,'speech_end_acoustic_timestamp_available':False,
    'speaker_first_audio_acoustically_measured':False,
    'queue_backpressure_observed':False,'new_turn_underruns_observed':False,
    'raw_text_audio_or_identity_exported':False,
    'limits':['two short human turns only','RPC times include transfer and service-side waiting',
        'capture completion is not an acoustic timestamp of the final spoken syllable',
        'SPEAKING is a sampled software playback state, not measured physical first sound',
        'cumulative guard processing overlaps later audio events and must not be added wholesale to first-audio latency']}
target=HERE/'TWO_TURN_LATENCY.json';assert not target.exists()
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['两轮真人对话延迟（洛杉矶2026-11-01）',
    '两轮均完成并取得新committed播放回执，采样前的旧轮已排除。',
    '主要等待来自LLM完整回复，其次ASR，再次TTS；这几段在当前首句通路串行累计。','']
for t in turns:
    lines.append('第%d轮：ASR %.3fs；上下文 %.3fs；LLM RPC %.3fs；TTS RPC %.3fs（%d次）；worker开始到首音频入队 %.3fs；录音完成到观察到SPEAKING约%.3fs。'%(
        t['ordinal'],t['asr_ms']/1000,t['context_ms']/1000,t['llm_rpc_ms']/1000,t['tts_rpc_ms']/1000,
        t['tts_calls'],t['first_audio_queued_from_worker_ms']/1000,t['capture_complete_to_observed_speaking_ms']/1000))
lines.extend(['','两轮队列回压等待0，本轮欠载0，未见播放队列堵塞证据；全程guard累计约0.85秒跨多个音频事件执行，与后续播放重叠，不能全部加到首声上。',
    '采样分辨率约250ms。SPEAKING只是软件状态，本次没有声学测量扬声器首声，也没有精确真人末字时间，录音收尾/静音判定无法独立精确拆分。',
    '优先优化方向：保留原27B/OmniVoice16与参数，先检查完整LLM回复到首句TTS的串行衔接；其次评估板端ASR耗时。上下文仅26–129ms，当前证据不支持将它列为主要等待。',
    '身份协同及转轴优化已交专门子代理；转轴按用户最新要求只沿用板端原固件、驱动、控制器和跟随链路。'])
(HERE/'LATENCY_REPORT.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'turns':turns,'means_ms':means,'report':str(HERE/'LATENCY_REPORT.txt')}))
