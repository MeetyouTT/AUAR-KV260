import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-boundary-nav-20261029')
s=json.loads((R/'state.json').read_text())
v=json.loads((R/'live-verification.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot_id']==v['boot_id']
assert v['status']=='PAGE_HIDE_ACK_AND_NATIVE_UNMAP_PASS'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
pins=s['payload_pins'];g=Path(s['gui']);e=Path(s['editor'])
assert sha(g/'startup/config.json')==s['gui_config_sha256']
for name in ['board_avatar_gtk.py','boundary_visibility.py']:assert sha(g/'runtime/aura/tools'/name)==pins[name]
for name in ['face_zone_editor.py','boundary_visibility.py']:assert sha(e/name)==pins[name]
for p,h in s['dropin_pins'].items():assert sha(p)==h
units={}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service','aura-face-zone-editor.service']:
    assert subprocess.check_output(['systemctl','is-active',unit],text=True).strip()=='active'
    units[unit]=int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True))
assert units['aura-camera-ui.service']==s['camera_pid']
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='READY'
assert u['manual_pan']['readback']['flags']==0
assert [u['manual_pan']['minimum_us'],u['manual_pan']['maximum_us']]==[500,2500]
s.update(phase='VERIFIED',board_wall_clock_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),live_verification_sha256=sha(R/'live-verification.json'),current_units=units)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'state':s,'page':u['ui_page'],'manual_state':u['manual_pan']['state'],'range_us':[500,2500],'motion_commands_sent':0}))
