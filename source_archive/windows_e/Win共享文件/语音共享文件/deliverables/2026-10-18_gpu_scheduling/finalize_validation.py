"""Finalize tested compact-route evidence without overstating timing benefit."""
import hashlib,json,re,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
baseline=read('baseline_manifest.json')
for name,digest in baseline['preserved'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
tests=re.search(r'(\d+) passed, (\d+) subtests passed in ([\d.]+)s',(HERE/'tests.log').read_text(encoding='utf-8-sig'))
assert tests and int(tests[1])==150 and int(tests[2])==26
tasks=read('native_validation.json');assert tasks['all_checks_pass']
assert tasks['turns'][-1]['history_messages']==8 and tasks['four_round_memory_correct']
assert all(t['metrics']['backend']=='llama_native_compact' for t in tasks['turns'])
assert tasks['injected_copy_repair']['metrics']['quality_retry_count']==1
integrated=read('integrated_profile.json')
assert integrated['free_generation'] and integrated['audio_bit_identical'] and len(integrated['cases'])==4
for case in integrated['cases']:
    assert case['end']['tts_cache_hits']==0 and not case['playback_ack_sent']
    assert case['end']['timing']['llm']['quality_retry_count']==0
    assert case['end']['timing']['llm']['backend']==('llama_native_compact' if case['variant']=='compact' else 'ollama')
assert len({case['reply'] for case in integrated['cases']})==1
live=read('live_playback.json');assert live['status']=='PASS_FRESH_CHAT_PLAYBACK'
assert live['playback_ack']['committed'] and live['turn']['audio_complete'] and live['camera_preserved']
assert live['turn']['thinking_mode']=='chat' and not live['turn']['thinking_feedback']
assert live['turn']['server_metrics']['clauses']==1
assert live['turn']['server_metrics']['timing']['llm']['backend']=='llama_native_compact'
assert not live['turn']['server_metrics']['timing']['llm']['possible_question_echo']
assert live['board_boot_id']==read('board_preflight.json')['camera']['board_boot_id']
listening=read('listening.json');assert listening['accepted'] and listening['request_id']==live['playback_ack']['request_id']
http=read('compact_host.json');assert len(http['cases'])==2 and not http['actual_playback']
for row in http['cases']:
    assert not row['playback_ack_sent'] and row['end']['timing']['llm']['backend']=='llama_native_compact'
health=read('host_ready.json');assert health['latency_options']['compact_grammar'] and health['ready']
config=json.loads((ROOT/'aura/config/voice_latency.json').read_text(encoding='utf-8-sig'))
assert config==health['latency_options']
names=list(dict.fromkeys([*baseline['before'],*baseline['preserved'],'aura/tools/native_grammar.py','aura/tests/framework/test_native_grammar.py']))
old=integrated['summary']['ollama']['first_pcm_ms'];new=integrated['summary']['compact']['first_pcm_ms']
summary={'status':'PASS_COMPACT_GRAMMAR_UNIT_NATIVE_HTTP_FRESH_PLAYBACK_AND_LISTENING',
 'tests':{'passed':int(tests[1]),'subtests_passed':int(tests[2]),'seconds':float(tests[3])},
 'active_feature':config,'host_health_at_deploy':health,
 'controlled_integrated':{'samples_per_variant':2,'summary':integrated['summary'],
  'same_reply':True,'audio_bit_identical':True,'tts_cache_hits':0,'actual_playback':False,
  'first_pcm_median_delta_ms':round(old-new,2),'delta_percent':round((old-new)/old*100,2),
  'statistical_significance_established':False,'fixed_latency_guarantee':False},
 'native_functional_validation':tasks,
 'fixed_output_grammar_profile':read('grammar_pipeline_profile.json')['summary'],
 'rejected_serial_scheduling':read('pipeline_profile.json')['summary'],
 'rejected_field_omission':{'report':'../2026-10-18_static_action/native_profile.json','deployed':False,'reason':'question copies and no speech-ready improvement'},
 'actual_http_cases':http,'fresh_production_chat':live,'listening':listening,
 'user_listening_accepted':True,'acoustic_onset_measured':False,
 'limitations':['small two-sample-per-variant integrated comparison; ranges overlap',
  'Ollama internal runner API build pinned; discovery/validation failure falls back before inference',
  'initial discovery cost exists; warm profiles exclude startup and service warmup covers it',
  'native reasoning/legacy complete WAV route remain on prior path',
  'known-copy mitigation is not general answer quality proof','one-second effective answer not achieved'],
 'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names},
 'preserved_source_sha256':baseline['preserved']}
encoded=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
(HERE/'verification_summary.json').write_text(encoded,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析'
(analysis/'紧凑JSON与GPU调度_实测摘要_20261018.json').write_text(encoded,encoding='utf-8')
(analysis/'紧凑JSON与GPU调度_20261018.md').write_text((HERE/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
with zipfile.ZipFile(HERE/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:archive.write(ROOT/name,name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py','.ps1','.md','.json','.log'} and path.stat().st_size<5_000_000:
            archive.write(path,str(path.relative_to(ROOT)).replace('\\','/'))
    rejected=ROOT/'deliverables/2026-10-18_static_action'
    for path in sorted(rejected.iterdir()):
        if path.is_file() and path.suffix in {'.py','.md','.json'}:
            archive.write(path,str(path.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(HERE/'verified_source.zip') as archive:
    assert archive.testzip() is None
    assert not any(name.lower().endswith(('.gguf','.safetensors','.onnx','.pt','.bin','.pem')) for name in archive.namelist())
print(json.dumps({'status':summary['status'],'tests':summary['tests'],
 'controlled_first_pcm_ms':{'ollama':old,'compact':new},
 'live_answer_seconds':live['turn']['request_to_answer_seconds'],'listening':True},ensure_ascii=True))
