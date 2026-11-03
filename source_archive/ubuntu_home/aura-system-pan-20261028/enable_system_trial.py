import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3';G=Path('/home/root/aura-system-pan-20261028/gui-continuity-v1');R=G.parent/'restore-5f167a36'
base='http://127.0.0.1:8783';op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
 with op.open(url,timeout=4) as r:return json.load(r)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Content-Type':'application/json','Origin':base})
 with op.open(q,timeout=5) as r:return json.load(r)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
cfg=json.loads((G/'startup/config.json').read_text());A=G/'runtime/aura'
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==s for n,s in cfg['component_sha256'].items())
assert str(G/'startup/launcher.py') in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
face=json.loads((A/'config/pan_face.local.json').read_text());assert face['manifest_sha256']=='e4701658fa75a0e08d1d3650f744d91c91ca6557ee0b861cffe7f6083bad5701'
u=get(base+'/api/state');m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0
assert u['phase']=='IDLE' and not u['playing'] and not u['handsfree_dialogue']['enabled']
services={}
for port in [8791,8792]:
 try:
  h=get('http://192.168.50.1:'+str(port)+'/health');services[str(port)]={k:h.get(k) for k in ['status','ready','model_ready','asr_ready','llm_ready','tts_ready']}
 except Exception as e:services[str(port)]={'error':type(e).__name__}
assert not any('error' in s for s in services.values()),'Windows voice health unavailable'
reply=command('pan_face_follow');assert reply.get('ok'),reply
try:
 verified=False
 for _ in range(40):
  time.sleep(.2);u=get(base+'/api/state');m=u['manual_pan'];f=m.get('face_follow') or {};p=Path(f.get('report','/nonexistent'))
  if m['automatic_following'] and p.is_file():
   doc=json.loads(p.read_text());verified=doc.get('consumer_manifest_sha256')==face['manifest_sha256'] and doc.get('status')=='CONTINUOUS_FACE_ZONE_RUNNING'
   if verified:break
 assert verified,'Current face process not verified'
 voice=command('conversation_toggle');assert voice.get('ok'),voice
 time.sleep(1);u=get(base+'/api/state')
 assert u['handsfree_dialogue']['enabled'],'Listening not enabled'
 result={'status':'INTEGRATED_TRIAL_RUNNING_NARROW_RANGE','boot_id':BOOT,'gui':str(G),'range_us':[1400,1600],'wide_range_applied':False,'follow_report':str(p),'controller_sha256':face['manifest_sha256'],'windows_health':services,'listening_enabled':u['handsfree_dialogue']['enabled'],'automatic_following':u['manual_pan']['automatic_following'],'readback':u['manual_pan'].get('readback'),'physical_motion_or_voice_quality_verified':False}
 with (R/'integrated-start.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
except BaseException:
 command('pan_stop')
 try:
  if get(base+'/api/state')['handsfree_dialogue']['enabled']:command('conversation_toggle')
 except Exception:pass
 raise
