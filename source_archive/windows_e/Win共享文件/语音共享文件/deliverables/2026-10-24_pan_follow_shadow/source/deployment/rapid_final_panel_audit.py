"""Verify current manual availability and open its panel, without movement."""
import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));address='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
G=Path(s['gui_release']);cfg=json.loads((G/'startup/config.json').read_text());runtime=Path(cfg['runtime'])/'aura'
assert all(sha(runtime/p)==v for p,v in cfg['component_sha256'].items())
assert all(sha(p)==v for rows in s['units'].values() for p,v in rows.items()) and sha(s['gui_dropin'])==s['gui_dropin_sha256']
assert sha(s['database_path'])==s['database_sha256']
h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];r=m['readback'];d=h['dpu_schedule']
assert h['pid']==s['current_camera_pid'] and not d['owner_fenced'] and h['identity']['face_targets']['worker_alive']
assert m['state']=='READY' and m['pulse_us']==1425 and m['minimum_us']==1425 and m['maximum_us']==1445
assert r['flags']==0 and r['lease_left_ms']==0 and not r['active'] and not r['armed'] and not m['automatic_following'] and not m['history']
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()=='aura-visual-servo-b4096-v2.bit.bin'
request=urllib.request.Request(address+'/api/command',data=json.dumps({'type':'pan_dialog'}).encode(),headers={'Content-Type':'application/json','Origin':address})
with op.open(request,timeout=4) as q:assert json.load(q).get('ok')
time.sleep(.4)
final=get(8783,'/api/state')['manual_pan'];assert final['panel_open'] and final['state']=='READY' and not final['history']
s.update(final_panel_open=True,final_flags=final['readback']['flags'],final_lease_ms=final['readback']['lease_left_ms'],direction_verified=False,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':'CURRENT_BOOT_MANUAL_PANEL_READY_OBSERVED_RETURN_CONFIRMED','boot':s['boot'],
 'camera_pid':h['pid'],'gui_pid':s['current_gui_pid'],'firmware':'aura-visual-servo-b4096-v2.bit.bin',
 'manual_state':final['state'],'panel_open':True,'bounds_us':[1425,1445],'pulse_us':1425,'flags':final['readback']['flags'],'lease_ms':final['readback']['lease_left_ms'],
 'gui_component_pins_verified':len(cfg['component_sha256']),'identity_database_unchanged':True,'sface_phase':d['optional']['sface']['recovery']['phase'],
 'sface_overruns':d['optional']['sface']['overruns'],'direction_verified':False,'automatic_following':False,'movement_commands_sent_by_audit':0},sort_keys=True))
