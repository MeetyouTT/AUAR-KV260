import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='16a07283-9e14-45e6-816d-3bda4cf333a7'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='FAULT'
proof=json.loads((R/'id-stop.json').read_text());assert proof['boot_id']==boot and proof['after_stop']['flags']==0 and proof['identity_stop_passed']
assert json.loads((R/'state.json').read_text())['phase']=='JOINT_NATIVE_RUNNING_GUI_STARTING'
S=F/'shadow-v10r1';lib=S/'libaura_trajectory.so';source=F/'continuous-v9/libaura_trajectory.so'
assert sha(source)=='d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a' and not lib.exists()
with lib.open('xb') as out:out.write(source.read_bytes())
m=S/'manifest.json';assert sha(m)=='f78e60013e8c909185ac2ea3fff254ee144015f6b5d100634e8ea67f26aaf150'
assert all(sha(S/n)==h for n,h in json.loads(m.read_text())['files'].items())
old=Path('/home/root/aura-pan-current-20261024/463c9307/face-zone-settings.json');settings=json.loads(old.read_text())
assert settings['left_camera_ratio']==.1 and settings['right_ratio']==.7158253629442671
settings.update(board_boot_id=boot,updated_mono_ms=int(time.monotonic()*1000))
p=R/'face-zone-settings.json'
with p.open('x') as f:json.dump(settings,f,indent=2);f.write('\n')
editor=F/'zone-editor-v5/face_zone_editor.py';assert sha(editor)=='c35b328e62e93b4c9f2b852a1cbdd58a1805bd2cdcd2e126e1b92ea4084ce5a9'
assert subprocess.check_output(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','--value'],text=True).strip()=='0'
subprocess.run(['systemd-run','--quiet','--collect','--unit=aura-face-zone-editor','--property=Restart=no','/usr/bin/python3','-B',str(editor),'--settings',str(p)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
print(json.dumps({'status':'NEW_BOOT_SHADOW_AND_BOUNDARY_READY','boot':boot,'settings':str(p),'source_pins_verified':len(json.loads(m.read_text())['files']),
 'editor_restarted_only':True,'physical_ARM':0,'physical_COMMIT':0,'MMIO_opened':False,'shadow_manifest_sha256':sha(m)}))
