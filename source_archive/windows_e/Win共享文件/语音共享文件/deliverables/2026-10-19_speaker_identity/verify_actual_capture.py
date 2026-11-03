"""Use the real CLI with three consented MCP01 clips and one separate query."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import argparse
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--experiment',type=Path,default=HERE/'actual_experiment.json')
parser.add_argument('--prefix',default='actual')
args=parser.parse_args()
if not re.fullmatch('[a-z0-9_]+',args.prefix):parser.error('Invalid report prefix')
config=json.loads(args.experiment.read_text(encoding='utf-8'))
sid=config['session_id']
recordings=ROOT/'声纹测试录音'/sid
database=Path('D:/AIModels/speaker-identity/runtime')/('speaker-test-'+sid+'.sqlite3')
if database.exists():raise ValueError('Use a fresh actual-test database; never overwrite')
common=[sys.executable,'-B',str(ROOT/'aura/tools/speaker_identity.py')]
options=['--model-directory','D:/AIModels/speaker-identity/ecapa','--database',str(database),
         '--threshold',str(config['threshold']),'--margin',str(config['ambiguity_margin'])]
environment=dict(os.environ,HF_HUB_OFFLINE='1',HF_HOME='D:/AIModels/speaker-identity/hf-cache',
                 TORCH_HOME='D:/AIModels/speaker-identity/torch-cache',PYTHONIOENCODING='utf-8')
result={'scope':config['scope'],'field_calibrated':False,'production_deployed':False,
        'session_id':sid,'database':str(database),'thresholds':{
            key:config[key] for key in ('threshold','ambiguity_margin','enrollment_consistency')},
        'clips':{},'status':'PENDING'}
for index in (1,2,3,4):
    path=recordings/('clip-%02d.wav'%index)
    result['clips'][str(index)]={'wav_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                'role':'enrollment' if index<4 else 'independent_within_session_query'}
commands=[('enroll',common+['enroll',*options,'--person-id','speaker-test-'+sid,
                          '--name',config['display_name'],'--consent','--expected-revision','0',
                          '--consistency',str(config['enrollment_consistency']),
                          *[str(recordings/('clip-%02d.wav'%i)) for i in (1,2,3)]]),
          ('query',common+['query',*options,str(recordings/'clip-04.wav')])]
for action,command in commands:
    started=time.perf_counter()
    process=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env=environment,timeout=90)
    (HERE/(args.prefix+'_'+action+'_stderr.log')).write_text(process.stderr,encoding='utf-8')
    result[action]={'exit_code':process.returncode,'wall_ms':round((time.perf_counter()-started)*1000,2)}
    if process.returncode:
        result[action]['error_tail']=process.stderr[-1000:]
        result['status']='FAIL_'+action.upper()
        break
    value=json.loads(process.stdout)
    (HERE/(args.prefix+'_'+action+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    result[action]['response']=value
if result['status']=='PENDING':
    query=result['query']['response']['result']
    result['status']='PASS_WITHIN_SESSION_ONLY' if query['state']=='KNOWN' and query['identity_id']=='speaker-test-'+sid else 'FAIL_INDEPENDENT_QUERY'
result['limitations']=['Only one actual speaker, one recording session and one independent query.',
                       'No actual-microphone stranger negatives or cross-session/cross-day acceptance.',
                       'Thresholds are experimental and not deployed to production.']
(HERE/(args.prefix+'_capture_verification.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if result['status']!='PASS_WITHIN_SESSION_ONLY':raise SystemExit(1)
