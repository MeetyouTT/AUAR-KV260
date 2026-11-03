"""Run the two Windows-skipped audio cases against the deployed Linux modules."""
import ast,base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
code=[];hashes={}
for relative,names in (
    ('tests/framework/test_voice_barge_in.py',{'test_real_speex_rejects_simulated_echo_and_keeps_near_end_speech'}),
    ('tests/framework/test_automatic_conversation.py',{'frames','AutomaticCaptureLifecycleTests'})):
    text=(AURA/relative).read_text(encoding='utf-8')
    hashes[relative]=hashlib.sha256(text.encode()).hexdigest()
    for node in ast.parse(text).body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names:
            node.decorator_list=[];code.append(ast.unparse(node))
payload=base64.b64encode('\n\n'.join(code).encode()).decode()
script=r'''
import audioop,base64,ctypes.util,io,json,socket,sys,tempfile,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,'/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
from board.runtime.audio.automatic_capture import AutomaticMcp01Capture
native=ctypes.util.find_library('speexdsp');assert native,'SpeexDSP missing on board'
old_find=ctypes.util.find_library
ctypes.util.find_library=lambda name:native if name=='speexdsp' else old_find(name)
temporary=Path('/home/root/aura-system-auto-tests-20261026/audio-fixtures')
temporary.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(temporary)
def audit(event,args):
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.system','os.exec'):
        raise RuntimeError('External activity forbidden: '+event)
    if event=='open' and isinstance(args[0],str) and args[0].startswith('/dev/'):
        raise RuntimeError('Audio device access forbidden')
sys.addaudithook(audit)
exec(compile(base64.b64decode('PAYLOAD').decode(),'<unchanged-audio-test-bodies>','exec'))
suite=unittest.TestSuite([unittest.FunctionTestCase(test_real_speex_rejects_simulated_echo_and_keeps_near_end_speech)])
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(AutomaticCaptureLifecycleTests))
out=io.StringIO();r=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
print(json.dumps(dict(status='PASS' if r.wasSuccessful() else 'FAIL',tests_run=r.testsRun,log=out.getvalue(),
                     native_speex=native,microphone_used=False,playback=False,subprocesses_in_tests=False,
                     production_modules_used=True,simulated_echo_only=True)))
'''.replace('PAYLOAD',payload)
value=json.loads(ssh('python3 -B -',script,timeout=40));value['test_source_sha256']=hashes
(HERE/'board_audio_auto.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
raise SystemExit(0 if value['status']=='PASS' else 1)
