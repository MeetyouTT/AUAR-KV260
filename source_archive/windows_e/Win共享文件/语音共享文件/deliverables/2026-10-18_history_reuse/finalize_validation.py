"""Archive bounded source/evidence; retain the open intermittent echo defect."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
baseline=read('baseline_manifest.json')
for name,digest in baseline['preserved'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
tests=re.search(r'(\d+) passed, (\d+) subtests passed in ([\d.]+)s',(HERE/'tests.log').read_text(encoding='utf-8-sig'))
assert tests and int(tests[1])==118 and int(tests[2])==26
profile=read('history_profile.json')
assert profile['all_memory_updates_correct'] and len(profile['traces'])==4
live=read('live_memory.json')
assert live['status']=='PASS_TWO_FRESH_MEMORY_TURNS_EXACT_HISTORY'
assert len(live['turns'])==2
for row in live['turns']:
    assert row['playback_ack']['committed'] and row['turn']['audio_complete']
    assert row['turn']['thinking_mode']=='chat' and not row['turn']['thinking_feedback']
    assert row['turn']['server_metrics']['clauses']==1 and row['camera_preserved']
last=live['turns'][-1]
assert '绿' in last['turn']['text']
assert last['turn']['server_metrics']['timing']['history_format']=='exact_json'
hearing=read('listening.json')
assert hearing['accepted'] and hearing['request_id']==last['playback_ack']['request_id']
equivalence=read('first_turn_equivalence.json')
assert equivalence['body_equal_before']
assert len(equivalence['cases'])==2 and all(c['same_reply'] for c in equivalence['cases'])
source_names=[*baseline['before'],*baseline['preserved'],'aura/tests/framework/test_history_reuse.py']
summary={'status':'PASS_HISTORY_REUSE_MEMORY_PLAYBACK_AND_LISTENING_WITH_OPEN_REPLY_QUALITY_ISSUE',
 'tests':{'passed':int(tests[1]),'subtests_passed':int(tests[2]),'seconds':float(tests[3])},
 'native_model_profile':profile['summary'],'memory_update_correct':True,
 'fresh_production_memory':live,'listening':hearing,'user_listening_accepted':True,
 'first_turn_equivalence':equivalence,
 'open_quality_issue':{'status':'OPEN','issue':'intermittent greeting question echo',
   'echoes_in_initial_http_probes':2,'initial_http_probes':3,'cache_used_on_affected_turns':False,
   'root_cause':'not_fully_established','excluded_from_speedup_claims':True},
 'limitations':['small controlled native sample','no direct KV cache hit counter',
   'live turns have different content and possible nearby diagnostic traffic; not a speed A/B',
   'volatile four-round memory, not persistent long-term memory','one-second effective answer not achieved'],
 'acoustic_onset_measured':False,
 'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names},
 'preserved_source_sha256':baseline['preserved']}
encoded=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
(HERE/'verification_summary.json').write_text(encoded,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析'
(analysis/'多轮历史复用优化_实测摘要_20261018.json').write_text(encoded,encoding='utf-8')
(analysis/'多轮历史复用优化_20261018.md').write_text((HERE/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
with zipfile.ZipFile(HERE/'verified_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in source_names:archive.write(ROOT/name,name)
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in {'.py','.ps1','.md','.json','.log'} and path.stat().st_size<5_000_000:
            archive.write(path,str(path.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(HERE/'verified_source.zip') as archive:assert archive.testzip() is None
print(json.dumps({'status':summary['status'],'tests':summary['tests'],'live_reply':last['turn']['text']},ensure_ascii=True))
