"""Derive honest, scoped timing comparisons from immutable before/after receipts."""
import datetime,hashlib,json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda name:json.loads((H/name).read_text(encoding='utf-8'))
before,after,plan,exp=map(read,('benchmark_before.json','benchmark_after.json','source_plan.json','experiment.json'))
assert before['status']==after['status']=='PASS'
assert before['health_before']['source_fingerprint']==plan['production_fingerprint']
assert after['health_before']['source_fingerprint']==plan['candidate_fingerprint']
assert before['context_contract']==after['context_contract']=={'explicit_fact':{'颜色偏好':'绿色'},'prior_played_dialogue':[]}
assert after['cleanup']['status']=='PASS' and after['cleanup']['action']=='all' and after['cleanup']['removed_only_public_attempts']
fact_rows=before['trials']+after['trials']
control_rows=before['controls']+after['controls']
assert len(before['trials'])==len(after['trials'])==4 and len(before['controls'])==len(after['controls'])==2
assert len({r['input_sha256'] for r in fact_rows})==1
assert len({r['input_sha256'] for r in control_rows})==1
assert all('绿色' in r['reply'] and r['sample_count']>0 and not r['playback_ack_sent'] for r in fact_rows)
assert all(r['sample_count']>0 and not r['playback_ack_sent'] for r in control_rows)
assert hashlib.sha256((H/'fixed_fact_question.wav').read_bytes()).hexdigest()==fact_rows[0]['input_sha256']
baseline_llm=[r['timing']['llm'] for r in before['trials']]
assert len({r['input_sha256'] for r in baseline_llm})==1
assert len({tuple(r['timing']['conversation_context']['explicit_fact_sources']) for r in before['trials']})==1
assert all(r['backend']=='ollama' for r in baseline_llm)
assert all(r['timing']['llm']['backend']=='conversation_memory_command' for r in after['trials'])
assert all(r['tts_cache_hits']==0 and r['timing']['first_tts_cache_hit'] is False for r in before['trials'])
assert after['trials'][0]['tts_cache_hits']==0 and after['trials'][0]['timing']['first_tts_cache_hit'] is False
assert all(r['tts_cache_hits']==1 and r['timing']['first_tts_cache_hit'] is True for r in after['trials'][1:])
assert len({r['timing']['llm']['input_sha256'] for r in control_rows})==1
assert all(r['timing']['llm']['backend']=='ollama' and r['tts_cache_hits']==0 for r in control_rows)
cleanups=[read(path.name) for path in sorted(H.glob('cleanup_*.json'))]
assert cleanups and all(r['status']=='PASS' and r['removed_only_public_attempts'] for r in cleanups)
def summary(rows):
 return {'samples':len(rows),'first_text_ms':[r['first_text_ms'] for r in rows],
         'first_pcm_ms':[r['first_pcm_ms'] for r in rows],
         'median_first_text_ms':statistics.median(r['first_text_ms'] for r in rows),
         'median_first_pcm_ms':statistics.median(r['first_pcm_ms'] for r in rows),
         'tts_cache_hits':[r['tts_cache_hits'] for r in rows]}
b,a=summary(before['trials'][1:]),summary(after['trials'][1:])
report={'status':'PASS','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Explicit current fact, same WAV and same persistent conversation fact. Software first PCM, no acoustic playback.',
 'fact_input_sha256':fact_rows[0]['input_sha256'],'context_contract':before['context_contract'],
 'persistent_fact_source':before['trials'][0]['timing']['conversation_context']['explicit_fact_sources'],
 'same_source_conversation_before_after':exp['cid'],
 'baseline_prompt_input_sha256':baseline_llm[0]['input_sha256'],
 'repeat_before':b,'repeat_after':a,
 'repeat_first_pcm_reduction_percent':round((1-a['median_first_pcm_ms']/b['median_first_pcm_ms'])*100,2),
 'repeat_first_text_reduction_percent':round((1-a['median_first_text_ms']/b['median_first_text_ms'])*100,2),
 'initial_cache_miss':{'samples_per_version':1,'before_first_pcm_ms':before['trials'][0]['first_pcm_ms'],
    'after_first_pcm_ms':after['trials'][0]['first_pcm_ms'],'same_output_text':False,'service_cold_start':False},
 'cache_caveat':'After repeat results reuse identical TTS PCM; before responses vary with LLM and have no TTS cache hits. This measures the complete fact-answer path, not raw LLM or TTS acceleration.',
 'general_chat_control':{'input_sha256':control_rows[0]['input_sha256'],
    'identical_prompt_input_sha256':control_rows[0]['timing']['llm']['input_sha256'],
    'before':summary(before['controls']),'after':summary(after['controls']),
    'improvement_demonstrated':False,'after_slower_in_this_small_sample':True,
    'cause_confirmed':False,'note':'Same request input, stochastic different replies on a shared machine; no broad latency guarantee.'},
 'public_rows_cleaned':True,'mic_opened':False,'playback':False,'playback_ack_sent':False,
 'board_migration':False,'whole_project_complete':False}
(H/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'repeat_first_pcm_ms':[b['median_first_pcm_ms'],a['median_first_pcm_ms']],
 'reduction_percent':report['repeat_first_pcm_reduction_percent'],'general_chat_improved':False}))
