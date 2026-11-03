import base64,hashlib,json
from pathlib import Path
p=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602';s=json.loads(raw);a=Path(s['runtime'])/'aura';files={}
for rel,expected in s['component_sha256'].items():
 if rel.endswith('.py') and (('/audio/' in rel and 'frontend' in rel) or rel=='tools/gstreamer_audio_worker.py'):
  data=(a/rel).read_bytes();assert hashlib.sha256(data).hexdigest()==expected;files[rel]={'sha256':expected,'base64':base64.b64encode(data).decode()}
cmd=Path('/proc/394769/cmdline').read_bytes();assert hashlib.sha256(cmd).hexdigest()=='236c51091fd21c314c0ca2e1cb48fefde1181eda5cb0431b974f60941dfa943e';args=[v.decode() for v in cmd.rstrip(b'\0').split(b'\0')];flags={}
for key in ('--frontend-directory','--frontend-optimization'):
 if key in args:
  value=args[args.index(key)+1];q=Path(value);row={'value_is_public_path':value.startswith('/home/root/'),'exists':q.exists()}
  if value.startswith('/home/root/'):
   row['path']=value
   if q.is_file():
    assert q.stat().st_size<=1048576;data=q.read_bytes();row['sha256']=hashlib.sha256(data).hexdigest()
    if q.suffix=='.json':
     doc=json.loads(data);schema=doc.get('schema') if isinstance(doc,dict) else None;row['schema']=schema
     if isinstance(schema,str) and 'frontend' in schema and 'embedding' not in data.decode().lower():row['public_manifest_base64']=base64.b64encode(data).decode()
  else:row['nonpath_option_sha256']=hashlib.sha256(value.encode()).hexdigest()
  flags[key]=row
assert p.read_bytes()==raw
print(json.dumps({'status':'EXACT_CURRENT_AUDIO_FRONTEND_SOURCE_CAPTURE','startup_sha256':hashlib.sha256(raw).hexdigest(),'source_files':files,'frontend_worker_pid':394769,'public_runtime_flags':flags,'state_or_source_changes':False}))
