import ast,base64,gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=(HERE/'external_monitor.py').read_bytes();ast.parse(raw)
digest=hashlib.sha256(raw).hexdigest()
body='PAYLOAD='+repr(base64.b64encode(gzip.compress(raw,mtime=0)).decode())+'\nSOURCE_SHA='+repr(digest)+'\n'+'''
import base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
assert not sys.flags.optimize
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
wrapper=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(wrapper.read_bytes()).hexdigest()
ROOT=Path('/home/root/aura-native-wait-20261023/external')/digest[:16];ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
assert sys.argv[1:] in ([],['--run'])
assert not (ROOT/'report.json').exists(),'Never overwrite external evidence'
if sys.argv[1:]==['--run']:
 try:exec(compile(raw,'external-counter-monitor','exec'))
 except Exception as error:
  if not (ROOT/'report.json').exists():
   (ROOT/'report.json').write_text(json.dumps({'complete':True,'passed':False,'production_changes':False,'error':type(error).__name__+': '+str(error)})+'\\n')
  raise
else:
 unit='aura-external-sched-'+digest[:16]
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=85','--property=Nice=19',
  '/usr/bin/python3','-B',str(wrapper),'--run'],capture_output=True,text=True,timeout=8)
 assert result.returncode==0,result.stderr
 print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json'),'helper_sha256':digest,'duration_seconds':60,'production_changes':False}))
'''
ast.parse(body);(HERE/'external_check.py').write_text(body)
(HERE/'external-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(body.encode()).hexdigest(),
    'source_sha256':digest,'duration_seconds':60,'sampling_hz':100,'minimum_effective_hz':90,
    'maximum_cpu_one_core_percent':2.0,'production_changes':False},indent=2)+'\n')
print(json.dumps({'helper_sha256':hashlib.sha256(body.encode()).hexdigest(),'bytes':len(body)}))
