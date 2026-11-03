"""Offline analysis fixtures. Does not access UART or the live board."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003-retry1/agent_review')
SOURCE=ROOT/'analyze_live.py'
spec=importlib.util.spec_from_file_location('offline_analyzer',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
negative=ROOT/'analysis-first-failure-v2'
summary=json.loads((negative/'summary.json').read_text())
assert summary['overall_pass'] is False
assert summary['baseline_restored'] is True
assert summary['input_integrity']['passed'] is True
assert summary['functional']['all_queries_match'] is True
assert summary['functional']['all_top5_match'] is True
assert summary['cycles']['records']==0 and summary['sustained']['elapsed_seconds'] is None
assert summary['sampling']['overall']['RSS_kB']['first'] is None
checks=[{'id':'failed-main-test-restored-baseline-remains-distinct','passed':True},
        {'id':'missing-sustained-results-and-samples-not-zero-or-pass','passed':True}]
before=hashlib.sha256((negative/'summary.json').read_bytes()).hexdigest()
try:module.analyze(Path('/home/ghmd/kv260-runtime-live-20261003'),negative)
except FileExistsError:pass
else:raise AssertionError('Existing analysis was overwritten')
assert before==hashlib.sha256((negative/'summary.json').read_bytes()).hexdigest()
checks.append({'id':'existing-analysis-output-rejected-without-overwrite','passed':True})

# Extract the unchanged statistics helper and exercise explicit artificial rows.
tree=ast.parse(SOURCE.read_text())
main_func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='analyze')
stats=next(n for n in main_func.body if isinstance(n,ast.FunctionDef) and n.name=='stats')
namespace={};exec(compile(ast.Module(body=[stats],type_ignores=[]),'offline_stats','exec'),namespace)
rows=[]
for name,t,rss,available,slab,unreclaim in [('a',1,100,1000,50,20),('b',2,90,950,55,25),('c',4,110,990,52,21)]:
    rows.append({'source':name,'uptime_seconds':t,'watch_count':5,'RSS_kB':rss,
                 'MemAvailable_kB':available,'Slab_kB':slab,'SUnreclaim_kB':unreclaim})
values=namespace['stats'](rows)
assert values['RSS_kB']=={'first':100,'last':110,'min':90,'max':110}
assert values['MemAvailable_kB']=={'first':1000,'last':990,'min':950,'max':1000}
assert values['Slab_kB']=={'first':50,'last':52,'min':50,'max':55}
assert values['SUnreclaim_kB']=={'first':20,'last':21,'min':20,'max':25}
assert values['watch_count']=={'first':5,'last':5,'min':5,'max':5}
assert values['sample_uptime_span_seconds']==3 and values['largest_sample_gap_seconds']==2
checks.append({'id':'first-last-min-max-and-uptime-gap-statistics','passed':True,
               'scope':'Artificial values only; not live board samples'})

fixture=ROOT/'analysis-corrupt-copy-fixture'
fixture.mkdir(exist_ok=False)
old=Path('/home/ghmd/kv260-runtime-live-20261003')
shutil.copytree(str(old/'board_evidence'),str(fixture/'board_evidence'))
for name in ['board_evidence_manifest.json','board_evidence.tar.gz','package_manifest.json']:
    shutil.copy2(str(old/name),str(fixture/name))
raw=fixture/'board_evidence/agent_logs/60-restore/000002-restored-query.stdout'
raw.write_bytes(raw.read_bytes()+b'\n')
corrupt=module.analyze(fixture,fixture/'analysis')
assert corrupt['input_integrity']['passed'] is False
assert corrupt['overall_pass'] is False and corrupt['baseline_restored'] is False
assert any('Manifest mismatch' in row['message'] for row in corrupt['issues'])
checks.append({'id':'raw-stream-corruption-rejected-and-restoration-not-trusted','passed':True})
result={'scope':'Offline fixtures only; first failed dataset and a corrupt COPY, no board operations',
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'passed':True,'checks':checks}
(ROOT/'ANALYSIS_FIXTURE_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
