"""Check the activated GTK process and real MCP01 capture while its sink stays open."""
import base64
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
deployment=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
assert deployment['status']=='DEPLOYED_READY'
remote=r'''
import base64,hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
root=Path(RUNTIME);stage=root.parent
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8783'+path,timeout=3) as response:return json.load(response)
def command(value):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',json.dumps(value).encode(),
       {'Origin':'http://127.0.0.1:8783','Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=5) as response:return json.load(response)
before=get('/api/state')
assert before['phase']=='IDLE' and not before['playing'] and not before['avatar_command_pending']
assert before['local_recording']['state']!='RECORDING' and not before['local_transcription']['service']['pending']
assert before['audio_output_state']=='IDLE_READY'
assert before['local_transcription']['service']['streaming'] and before['local_transcription']['service']['feedback_ready']
launch=json.loads((root/'launch.json').read_text());pid=launch['pid']
cmdline=Path('/proc')/str(pid)/'cmdline'
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in cmdline.read_bytes().split(b'\0')
report={'status':'RUNNING','gui_pid':pid,'runtime':str(root),'input_kind':'SHORT_MICROPHONE_DEVICE_TEST_CANCELLED_WITHOUT_TRANSCRIPTION',
        'before':before,'new_user_conversation_verified':False,'source_hashes':{}}
try:
    command({'type':'record_toggle'});deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        state=get('/api/state');recording=state['local_recording']
        if state.get('error') or recording.get('error'):raise RuntimeError(state.get('error') or recording['error'])
        if recording['state']=='RECORDING' and recording['sample_count']>=8000:
            report['capture_during_persistent_sink']={'sample_count':recording['sample_count'],
                 'sample_rate':16000,'audio_output_state':state['audio_output_state'],'error':recording['error']}
            break
        time.sleep(.1)
    else:raise RuntimeError('Real microphone did not produce samples')
finally:
    command({'type':'event','event':'cancel'})
deadline=time.monotonic()+8
while time.monotonic()<deadline:
    state=get('/api/state')
    if (state['local_recording']['state']=='CANCELLED' and state['phase']=='IDLE' and
            state['audio_output_state']=='IDLE_READY' and not state['local_transcription']['service']['pending']):break
    time.sleep(.1)
else:raise RuntimeError('Cancelled microphone test did not return to ready')
assert not state['error'] and not state['local_recording']['error']
manifest=json.loads((stage/'manifest.json').read_text())
for name,expected in manifest['files'].items():
    actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
    assert actual==expected,name
    report['source_hashes'][name]=actual
assert subprocess.check_output(['systemctl','is-active','aura-avatar-ui.service']).decode().strip()=='active'
sys.path.insert(0,str(root/'aura'))
from tools.board_screen_capture import capture
image_path=stage/'active_board.png';size=capture(image_path)
report.update(status='PASS_ACTIVE_GTK_PERSISTENT_SINK_AND_REAL_CAPTURE',after=state,screen_size=size)
(stage/'active_ui.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
report['screen_base64']=base64.b64encode(image_path.read_bytes()).decode()
print(json.dumps(report))
'''.replace('RUNTIME',repr(deployment['runtime']))
report=json.loads(ssh('python3 -',remote,timeout=45))
(HERE/'active_board.png').write_bytes(base64.b64decode(report.pop('screen_base64')))
(HERE/'active_ui.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key not in ('before','after','source_hashes')},ensure_ascii=False))
