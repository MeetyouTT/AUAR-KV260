"""Bounded source archive: distinguish mitigation, native stress, and hearing."""
import hashlib,json,re,statistics,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
baseline=read('baseline_manifest.json')
for name,digest in baseline['preserved'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
for name in ('aura/tools/dialogue_host_ollama.py','aura/common/spoken_input.py'):
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==baseline['before'][name],name
match=re.search(r'(\d+) passed, (\d+) subtests passed in ([\d.]+)s',(HERE/'tests.log').read_text(encoding='utf-8-sig'))
assert match and int(match[1])==138 and int(match[2])==26
tasks=read('task_validation.json');assert tasks['all_checks_pass']
assert tasks['turns'][-1]['history_messages']==8 and tasks['four_round_memory_correct']
assert tasks['seeded_repair']['metrics']['quality_retry_count']==1
assert tasks['seeded_repair']['metrics']['quality_attempts'][0]['possible_question_echo']
assert not tasks['seeded_repair']['metrics']['possible_question_echo']
normal=read('normal_gate_profile.json')
assert normal['same_seed_same_replies'] and normal['normal_guarded_no_retry']
host=read('quality_host.json');assert len(host['cases'])==2 and not host['actual_playback']
stages=[]
for row in host['cases']:
    timing=row['end']['timing'];llm=timing['llm']
    assert not llm['possible_question_echo'] and llm['quality_retry_count'] in (0,1)
    assert not row['playback_ack_sent'] and row['end']['clauses']==1
    stages.append({'reply':row['reply'],'recognition_ms':timing['recognition_ms'],
       'speech_ready_ms':timing['first_clause_ready_ms'],'tts_request_ms':timing['first_tts_request_ms'],
       'tts_cache_hit':timing['first_tts_cache_hit'],'request_to_first_pcm_ms':row['request_to_first_pcm_ms'],
       'quality_retry_count':llm['quality_retry_count']})
names=list(dict.fromkeys([*baseline['before'],*baseline['preserved'],'aura/common/reply_quality.py','aura/tests/framework/test_reply_quality.py']))
summary={'status':'PASS_CHAT_PROTECTION_UNIT_NATIVE_HTTP_DEPLOYED_FRESH_PLAYBACK_LISTENING_PENDING',
 'scope':'narrow complete-question copying in ordinary streamed chat',
 'general_root_cause_status':'OPEN; generation-stage copying reproduced; underlying causes not fully isolated',
 'quality_mitigation':'one bounded repair before copied question can escape; normal requests use one inference',
 'tests':{'passed':int(match[1]),'subtests_passed':int(match[2]),'seconds':float(match[3])},
 'actual_native_tasks':tasks,'normal_gate_profile':normal,'actual_http_stages':stages,
 'host_health':read('host_ready.json'),'user_listening_accepted':False,'acoustic_onset_measured':False,
 'limitations':['narrow >=8 normalized character exact-question pattern, heuristic task exceptions',
    'native reasoning and legacy complete-WAV route retain previous behavior',
    'repair adds latency to an affected turn; second failure returns an error',
    'native seeded bad-candidate stress is not a physical board repair-path acceptance',
    'small normal-path timing samples do not prove fixed speedup','one-second effective answer not achieved'],
 'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
if (HERE/'live_playback.json').is_file():
    live=read('live_playback.json');assert live['status']=='PASS_FRESH_CHAT_PLAYBACK'
    llm=live['turn']['server_metrics']['timing']['llm']
    assert llm['quality_retry_count'] in (0,1) and not llm['possible_question_echo']
    assert live['turn']['audio_complete'] and live['playback_ack']['committed'] and live['camera_preserved']
    summary['fresh_production_chat']=live
    summary['status']='PASS_CHAT_PROTECTION_FRESH_PLAYBACK_LISTENING_PENDING'
    if (HERE/'listening.json').is_file():
        hearing=read('listening.json');assert hearing['request_id']==live['playback_ack']['request_id']
        summary['listening']=hearing
        if hearing.get('accepted'):
            summary['user_listening_accepted']=True
            summary['status']='PASS_CHAT_PROTECTION_TESTS_NATIVE_HTTP_FRESH_PLAYBACK_AND_LISTENING'
encoded=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
(HERE/'verification_summary.json').write_text(encoded,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析'
(analysis/'防复述保护与延迟核查_实测摘要_20261018.json').write_text(encoded,encoding='utf-8')
(analysis/'防复述保护与延迟核查_20261018.md').write_text((HERE/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
with zipfile.ZipFile(HERE/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:archive.write(ROOT/name,name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py','.ps1','.md','.json','.log'} and path.stat().st_size<5_000_000:
            archive.write(path,str(path.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(HERE/'verified_source.zip') as archive:assert archive.testzip() is None
print(json.dumps({'status':summary['status'],'tests':summary['tests'],'stages':stages,'listening':summary['user_listening_accepted']},ensure_ascii=True))
