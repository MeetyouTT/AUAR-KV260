import importlib.util,json,subprocess,sys,time,urllib.request
from pathlib import Path
stage=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd');payload=stage/'payload'
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4) as response:before=json.load(response)
# Load only staged tracking; no camera open or DPU creation.
sys.path.insert(0,str(payload/'aura'))
test_source='import sys,unittest;sys.path.insert(0,"/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura");import board.vision;board.vision.__path__.insert(0,'+repr(str(payload/'aura/board/vision'))+');suite=unittest.defaultTestLoader.discover("tests/framework",pattern="test_person_bytetrack.py");result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())'
result=subprocess.run(['python3','-B','-c',test_source],
    cwd=str(payload/'aura'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=45)
assert result.returncode==0,result.stdout
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4) as response:after=json.load(response)
assert before['pid']==after['pid'] and before['camera_epoch']==after['camera_epoch']
assert after['capture_frames']>before['capture_frames']
source=payload/'board_profile.py'
if source.exists():
    p=subprocess.run(['python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40)
    assert p.returncode==0,p.stdout
    baseline=json.loads(p.stdout)
else:baseline=None
print(json.dumps({'status':'PASS','test_log':result.stdout,'before':before,'after':after,'profile':baseline}))
