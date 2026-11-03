"""Summarize complete measurements, including the rejected experiment."""
import datetime,json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
phases={}
for name,file in [('original','voice_before.json'),('rejected_r7','voice_after.json'),('intermediate_r8','voice_refined.json'),('final_r9','voice_trimmed_final.json')]:
 path=H/file
 if not path.exists():continue
 data=json.loads(path.read_text(encoding='utf-8'));assert data['status']=='PASS'
 rows=data['trials'];uncached=[r for r in rows if r['tts_cache_hits']==0]
 phase={'file':file,'revision':data['revision'],'trials':len(rows),'uncached_trials':len(uncached),
  'first_pcm_median_ms':statistics.median(r['first_pcm_ms'] for r in rows),
  'first_text_median_ms':statistics.median(r['first_text_ms'] for r in rows),
  'uncached_first_pcm_median_ms':statistics.median(r['first_pcm_ms'] for r in uncached) if uncached else None,
  'per_topic':{},'ollama_residency_unchanged_within_phase':data['models_before']==data['models_after'],
  'tts_cache_hits':sum(r['tts_cache_hits'] for r in rows),
  'maximum_estimated_network_supply_gap_ms':max(r['estimated_delivery_starvation_ms'] for r in rows),
  'history_context_messages':[r['supplemental_context_messages'] for r in rows]}
 if name=='final_r9':
  snapshots=[r.get('tts_cuda_idle_cache',{}) for r in uncached]
  snapshots=[s for s in snapshots if s.get('available')]
  first_observation=json.loads((H/'voice_trimmed.json').read_text(encoding='utf-8')).get('tts_cuda_idle_cache_before')
  phase['tts_idle_cuda_cache']={'first_ready_observation':first_observation,
   'first_ready_observation_file':'voice_trimmed.json',
   'before_final_measurement':data.get('tts_cuda_idle_cache_before'),
   'uncached_request_snapshots':len(snapshots),
   'released_bytes_per_request':[s['released_bytes'] for s in snapshots],
   'trim_ms_per_request':[s['trim_ms'] for s in snapshots],
   'allocated_bytes_after_inference':[s['allocated_bytes'] for s in snapshots],
   'note':'The first ready allocator observation remains a valid process counter even though the enclosing latency run failed its independent model-residency check. Never sum cached-hit snapshots; they can repeat a prior request. These are only this TTS process allocator blocks, not model weights or other applications.'}
 for topic in sorted({r['label'] for r in rows}):
  chosen=[r for r in rows if r['label']==topic]
  phase['per_topic'][topic]={'trials':len(chosen),'first_pcm_mean_ms':statistics.mean(r['first_pcm_ms'] for r in chosen),
   'tts_cache_hits':sum(r['tts_cache_hits'] for r in chosen),
   'context_messages':[r['supplemental_context_messages'] for r in chosen],
   'input_wav_sha256':sorted({r['input_wav_sha256'] for r in chosen})}
 phases[name]=phase
long_conversation={}
for key,name in [('intermediate_r8','live_controls_acceptance.json'),('final_r9','live_controls_acceptance_r9.json')]:
 path=H/name
 if not path.exists():continue
 data=json.loads(path.read_text(encoding='utf-8'))
 if data['status']!='PASS':continue
 long_conversation[key]=[{'label':r['label'],'first_pcm_ms':r['first_pcm_ms'],
  'tts_cache_hits':r.get('tts_cache_hits'),
  'history_messages':r['timing'].get('history_messages'),
  'prompt_eval_count':r['timing']['llm'].get('prompt_eval_count'),
  'prompt_eval_duration_ms':r['timing']['llm'].get('prompt_eval_duration_ms'),
  'eval_count':r['timing']['llm'].get('eval_count'),
  'eval_duration_ms':r['timing']['llm'].get('eval_duration_ms')} for r in data['turns'] if r['label'] in ('plain_today','recall_today','general_durable_question')]
report={'status':'FINAL' if 'final_r9' in phases and 'final_r9' in long_conversation else 'INTERIM',
 'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phases':phases,
 'long_conversation_model_turns':long_conversation,
 'method':'Same four public 16kHz WAVs, two rounds plus unscored warmup; actual ASR/27B/OmniVoice16 over existing voice channel. Unique anonymous boot/session, no microphone/playback/ACK or durable conversation.',
 'rejected_r7':'Compact serialization hint moved first speech text earlier but raised first PCM median from 4052.11 to 4352.65 ms. Fixed identical reply control was already minified in both variants and showed prompt-cache confounding. Do not claim intrinsic serialization speedup.',
 'accepted_scope':'Precise voice intent avoids timeline/archive injection for ordinary temporal chat. After completed OmniVoice inference, return only unused allocator cache, keep live weight tensors; report actual released bytes. Actual history, calendar API, permissions, source provenance and prior handoff fix remain.',
 'limits':['Small sequential free-answer samples; different generated replies and global resource fluctuations prevent causal claims of a general speedup.',
  'Cache-hit and uncached samples are explicitly separated. Runtime metrics do not measure microphone endpointing, physical playback or human experience.',
  'Estimated network supply gap is a RAM-delivery simulation, not proof of continuous physical playback.',
  'Other model processes were never unloaded or stopped by this task. Both original and r7 benchmark phases reported the default Ollama model already naturally absent.'],
 'overall_chat_latency_accepted':False,'full_project_accepted':False}
invalid=H/'voice_trimmed.json'
if invalid.exists():
 data=json.loads(invalid.read_text(encoding='utf-8'))
 report['invalidated_r9_measurement']={'file':invalid.name,'status':data['status'],'reason':data.get('error'),
  'functional_replies':len(data['trials']),'models_before':data.get('models_before'),'models_after':data.get('models_after'),
  'included_in_final_performance_statistics':False}
(H/'performance_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{x:v[x] for x in ('trials','uncached_trials','first_pcm_median_ms','uncached_first_pcm_median_ms','tts_cache_hits')} for k,v in phases.items()}))
