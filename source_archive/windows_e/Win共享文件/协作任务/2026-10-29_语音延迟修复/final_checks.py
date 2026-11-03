import sys,json,hashlib,time,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]/'语音共享文件'
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
board_health=json.loads(ssh('python3 -B -',"import urllib.request,json\nwith urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as r:print(json.dumps(json.load(r)))",timeout=15))
before=json.loads((H/'before.json').read_text(encoding='utf-8'))
after=json.loads((H/'after.json').read_text(encoding='utf-8'))
fingerprint=json.loads((H/'fingerprint_verification.json').read_text(encoding='utf-8'))
processes=json.loads((H/'final_processes.json').read_text(encoding='utf-8-sig'))
selection_path=P/'deliverables/2026-10-06_voice_selected_soft_young/selection.json'
selection=json.loads(selection_path.read_text(encoding='utf-8'))
reference_ok=hashlib.sha256((selection_path.parent/selection['reference_audio']).read_bytes()).hexdigest()==selection['reference_sha256']
checks={
 'board_reads_ready_false_switch':board_health['ready'] and board_health['latency_options']['compact_grammar'] is False,
 'same_r2':before['health']['service_revision']==board_health['service_revision']=='voice-timeline-20261028-r2',
 'only_target_config_changed':fingerprint['only_changed_key']==['compact_grammar'] and fingerprint['all_source_changes_explained_by_config'],
 'other_five_enabled':all(board_health['latency_options'][k] for k in ('reply_first','early_sentence','coalesce_chat','reuse_history','first_sentence_chat')),
 'asr_model_same':before['health']['asr_model']==board_health['asr_model'],
 'llm_model_same':before['health']['llm_model']==board_health['llm_model'],
 'omnivoice16_same':board_health['tts']==before['health']['tts']=='omnivoice' and board_health['num_step']==before['health']['num_step']==16,
 'voice_reference_hash_matches':reference_ok,
 'memory_capabilities_same':before['health']['capabilities']==board_health['capabilities'],
 'persistent_memory_counts_same':all(before['health']['conversation_memory'][k]==board_health['conversation_memory'][k] for k in ('conversations','turns')),
 'memory_summary_running':board_health['conversation_memory']['background_summaries']['running'],
 'other_listener_pids_same':all(x['before']==x['after'] for x in processes['other_listeners_unchanged']),
 'old_owned_processes_gone':not processes['old_owners_remaining'],
 'ui_camera_pids_same':all(before['board'][k]['MainPID']==after['board'][k]['MainPID'] for k in ('ui_service','camera_service')),
 'ui_camera_config_same':before['board']['config_sha256']==after['board']['config_sha256'] and before['board']['pins']==after['board']['pins'],
 'board_idle_pan_same':after['board']['preflight_ready'] and before['board']['pan']==after['board']['pan'],
 'service_idle':not board_health['busy'] and not board_health['dependencies']['tts']['request_active'],
}
tests=[]
for name in ('test_before','test_board_before','test_after','test_board_after'):
 v=json.loads((H/(name+'.json')).read_text(encoding='utf-8'))
 for i,r in enumerate(v['runs']):
  lm=r['host_timing']['llm']
  tests.append({'group':name,'run':i+1,'preparation_ms':lm['request_preparation_ms'],'first_clause_ready_ms':r['host_timing']['first_clause_ready_ms'],'client_text_ms':r['client_first_ms']['text'],'client_first_pcm_ms':r['client_first_ms']['audio'],'backend':lm['backend'],'fallback':lm.get('compact_grammar_fallback'),'tts_cache_hit':r['host_timing']['first_tts_cache_hit'],'tts_generation_ms':r['host_timing']['first_tts_generation_ms'],'input_sha256':lm['input_sha256'],'system_prompt_sha256':lm['system_prompt_sha256']})
checks['identical_asr_and_prompt']=len({r['input_sha256'] for r in tests})==len({r['system_prompt_sha256'] for r in tests})==1
checks['after_no_fallback']=all(r['backend']=='ollama' and r['fallback'] is None for r in tests if r['group'].endswith('after'))
first_ready='2026-10-29T08:12:33.9009144+00:00'
reload=json.loads((H/'reload.json').read_text(encoding='utf-8-sig'))
startup_ms=(datetime.datetime.fromisoformat(first_ready)-datetime.datetime.fromisoformat(reload['utc'].replace('Z','+00:00'))).total_seconds()*1000
v={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'all_checks_pass':all(checks.values()),'board_read_health':board_health,'startup_observation':{'first_ready_utc':first_ready,'source':'background polling exec session 33630; 2s poll with bounded HTTP timeout','stop_start_begin_utc':reload['utc'],'observed_reload_to_ready_ms':round(startup_ms,2),'not_a_request_latency':True},'tests':tests,'voice_reference_sha256':selection['reference_sha256']}
(H/'final_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':checks,'all_checks_pass':v['all_checks_pass'],'startup':v['startup_observation']},ensure_ascii=True))
assert all(checks.values())
