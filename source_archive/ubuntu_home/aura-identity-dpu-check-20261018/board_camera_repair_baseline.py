"""Freeze exact runtime hashes and inspect voice/audio ownership before repair."""
import base64,gzip,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2/startup')
root=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura')
conf=json.loads((p/'config.json').read_text());art={};hashes={}
for n in ['config.json','launcher.py']:
 data=(p/n).read_bytes();hashes[n]=hashlib.sha256(data).hexdigest();raw=gzip.compress(data,mtime=0)
 art[n+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
bad=[rel for rel,sha in conf['component_sha256'].items() if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=sha]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
def choose(v,keys):return {k:v.get(k) for k in keys}
v={'config_hashes':hashes,'component_count':len(conf['component_sha256']),'hash_mismatches':bad,
 'gui':choose(s,['phase','playing','ui_page','error','avatar_command_pending','diagnostic_job']),
 'connection':choose(s.get('ui_runtime',{}),['link','error','preview_error','pending_count']),
 'handsfree':choose(s.get('handsfree_dialogue',{}),['state','enabled','visual_bound','conversation_entered','error']),
 'transcription':choose(s.get('local_transcription',{}),['state','error']),
 'voice_service':choose(s.get('local_transcription',{}).get('service',{}),['state','available','connected','error','conversation','streaming']),
 'barge_in':choose(s.get('voice_barge_in',{}),['state','listening','echo_reference_ready','error']),
 'owners':{},'thermal':{},'artifacts':art}
for q in Path('/proc').iterdir():
 if not q.name.isdigit():continue
 for f in (q/'fd').glob('*'):
  try:
   dest=os.readlink(str(f))
   if dest.startswith(('/dev/video','/dev/snd/pcm','/dev/dri/')):v['owners'].setdefault(q.name,[]).append(dest)
  except OSError:pass
for q in Path('/sys/class/thermal').glob('thermal_zone*'):
 try:v['thermal'][q.name]={'type':(q/'type').read_text().strip(),'temp':(q/'temp').read_text().strip()}
 except OSError:pass
for n in ['cpu','memory','io']:
 q=Path('/proc/pressure')/n
 if q.exists():v['pressure_'+n]=q.read_text()
print(json.dumps(v),flush=True)
