import base64,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text())
script=r'''
import base64,json,os,subprocess
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])/'aura'
test=stage/'test_voice_first.py';test.write_bytes(base64.b64decode(TEST))
args=['python3','-B','-m','pytest','-q',str(test),
 'tests/framework/test_voice_barge_in.py','tests/framework/test_automatic_conversation.py',
 'tests/framework/test_board_recording.py','tests/framework/test_simple_enrollment.py',
 '-k','not http','--junitxml='+str(stage/'board_tests.xml')]
result=subprocess.run(args,cwd=root,env=dict(os.environ,PYTHONPATH=str(root),PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=120)
(stage/'board_tests.log').write_text(result.stdout+result.stderr)
print(json.dumps({'returncode':result.returncode,'log':result.stdout+result.stderr}))
'''.replace('CANDIDATE',repr(c)).replace('TEST',repr(base64.b64encode((H/'test_voice_first.py').read_bytes()).decode()))
v=json.loads(ssh('python3 -B -',script,timeout=135));(H/'board_tests.json').write_text(json.dumps(v,indent=2));print(v['log'][-8000:]);assert v['returncode']==0
