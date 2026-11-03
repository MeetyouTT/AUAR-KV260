"""Archive text evidence only, never weights, environments or SSH keys."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
restored=json.loads((HERE/'restored.json').read_text(encoding='utf-8'))
assert restored['status']=='ORIGINAL_RESTORED_RUNTIME_UNCHANGED_EXTERNAL_DRAFT_PATH_RECORDED_REAL_27B_REPLY_PASS'
for name in ('memory_schedule.json','trim_cache.json','cuda_graph.json','graph_validation.json'):
    value=json.loads((HERE/name).read_text(encoding='utf-8'))
    assert value['status']=='COMPLETE_NOT_DEPLOYED'
    assert all(value['audio_parity'].values()) and all(value['reply_parity'].values())
for path in HERE.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
graph=json.loads((HERE/'graph_validation.json').read_text(encoding='utf-8'))
summary={'status':'TRIAL_COMPLETE_NO_RUNTIME_CANDIDATE_ADOPTED','three_second_end_to_end_goal_achieved':False,'user_fresh_listening_in_this_trial':False,'original_27b_preserved':True,'tts16_reference_preserved':True,'production_runtime_code_preserved':True,'storage_config_change':'External draft directory recorded; target and Ollama directories unchanged','gpu_dflash_adopted':False,'tts_parking_adopted':False,'cache_trim_adopted':False,'cuda_graph_adopted':False,'graph_extended_summary':graph['summary'],'graph_audio_parity':graph['audio_parity'],'restored_status':restored['status'],'current_camera_pid':restored['board']['camera']['pid'],'limitations':['Software host first-PCM metrics exclude fresh ASR capture and acoustic board onset.','Warmup drift and small samples; no reliable production speedup established.','DFlash detailed aggregate overwritten by auxiliary helper; retained console summary and independent runner/pipeline evidence documented in README.'],'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ('.py','.ps1','.md')}}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
allowed={'.py','.ps1','.json','.md','.txt','.log'}
files=[p for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in allowed]
assert all(p.resolve().parent==HERE.resolve() and p.stat().st_size<5*1024*1024 for p in files)
with zipfile.ZipFile(HERE/'trial_evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in files:archive.write(path,path.name)
with zipfile.ZipFile(HERE/'trial_evidence.zip') as archive:
    assert archive.testzip() is None
print(json.dumps({'status':summary['status'],'text_evidence_files':len(files),'archive_bytes':(HERE/'trial_evidence.zip').stat().st_size,'source_comparison':len(restored['accepted_source_comparison']),'runtime_candidates_adopted':0,'graph_cases':len(graph['cases'])}))
