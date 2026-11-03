import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-v6/face_zone_editor.py')
assert hashlib.sha256(P.read_bytes()).hexdigest()=='f86ae1c490971a055618cb61fc74766e14ae4541d6295805b1482ad939fcbb0c'
s=json.loads((R/'state.json').read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
unit='aura-face-zone-editor.service'
subprocess.run(['systemctl','stop',unit],check=True,capture_output=True,timeout=10)
assert subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()=='0'
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(P),'--settings',str(R/'face-zone-settings.json')],check=True,capture_output=True,timeout=6)
time.sleep(1)
trace=json.loads((R/'face-zone-display-status.json').read_text())
assert get(8783,'/api/state')['manual_pan']['readback']==m['readback']
s.update(zone_editor_version=6,boundary_live_diagnostics=str(R/'face-zone-display-status.json'),face_input_match_unresolved=True,
 latest_boundary_feedback='User crossed both lines during 20s test, but no ARM/COMMIT; test not accepted')
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'ZONE_HINT_V6_ACTIVE_OUTPUT_STOPPED','display':trace,'manual_readback':m['readback'],'motor_commands_sent':0,
 'camera_pid':h['pid'],'gui_restarted':False,'new_editor_pid':subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()}))
