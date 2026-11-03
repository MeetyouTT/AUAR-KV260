"""Read package metadata and effective runtime without opening audio devices."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import base64,ctypes.util,hashlib,importlib.util,json,platform,re,subprocess,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfgpath=Path(re.findall(r'--config (\S+)',unit)[-1])
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert str(cfgpath) in effective
root=Path(json.loads(cfgpath.read_text())['runtime'])
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
names=['aura/board/runtime/audio/automatic_capture.py','aura/board/runtime/audio/vad.py',
       'aura/board/runtime/audio/capture.py','aura/tools/barge_in_capture.py',
       'aura/tools/barge_in_recording.py','aura/board/runtime/audio/barge_verify.py']
print(json.dumps({'runtime':str(root),'config':str(cfgpath),
 'machine':platform.machine(),'python':platform.python_version(),
 'packages':{n:bool(importlib.util.find_spec(n)) for n in ('onnxruntime','sherpa_onnx','numpy','webrtcvad')},
 'native_libraries':{n:ctypes.util.find_library(n) for n in ('rnnoise','webrtc_audio_processing','speexdsp','onnxruntime')},
 'ui':{'phase':u['phase'],'audio_output_state':u['audio_output_state'],
       'monitor_enabled':u['handsfree_dialogue']['enabled']},
 'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
 'baseline_sources':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names[:2]},
 'microphone_opened_by_operator':False,'service_or_settings_changed':False}))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=20))
import base64,hashlib
for name,encoded in result.pop('baseline_sources').items():
    data=base64.b64decode(encoded)
    assert hashlib.sha256(data).hexdigest()==result['files'][name]
    target=HERE/'before'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==data
    else:target.write_bytes(data)
(HERE / 'board_inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
