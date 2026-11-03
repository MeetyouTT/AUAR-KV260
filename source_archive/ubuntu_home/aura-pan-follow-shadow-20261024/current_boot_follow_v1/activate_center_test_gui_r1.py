"""Apply the finite 20s test configuration; GUI startup never starts following."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((R/'state.json').read_text());assert s['phase']=='FACE_CENTER_BOTH_BOUNDARIES_STAGED_OUTPUT_STOPPED' and s['shadow_r3_pass']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert sha(s['shadow_r3_report'])==s['shadow_r3_report_sha256']
proxy=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-follow-v1/face_pan_controls_observed.py')
assert sha(proxy)=='9374b8d37e60c967aa3b248f9540ce511aa7d5b0b8cc2e56e2d88ac0451adb55'
assert json.loads((R/'direction-calibration.json').read_text())['axis_camera_mirrored_control_polarity']==-1
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert sha(c)==s['startup_config_sha256'] and all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
manual=A/'config/pan_manual.local.json';mc=json.loads(manual.read_text());assert mc['automatic_following_enabled'] is False
backup=G/'before-current-follow-v1';assert not (backup/'manual-before-enable.json').exists()
(backup/'manual-before-enable.json').write_bytes(manual.read_bytes());mc['automatic_following_enabled']=True;mc['left_button_pulse_sign']=-1
tmp=manual.with_name(manual.name+'.enable');tmp.write_text(json.dumps(mc,indent=2)+'\n');os.replace(tmp,manual)
cfg['component_sha256']['config/pan_manual.local.json']=sha(manual)
target=A/'tools/face_pan_controls.py';tmp=target.with_name(target.name+'.observed');tmp.write_bytes(proxy.read_bytes());os.replace(tmp,target)
cfg['component_sha256']['tools/face_pan_controls.py']=sha(target)
tmp=c.with_name(c.name+'.enable');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(tmp,c)
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(G/'startup/launcher.py'),'--config',str(c),'--preflight'],env=env,capture_output=True,text=True,timeout=30)
assert p.returncode==0,p.stderr[-800:]
subprocess.run(['systemctl','stop','--no-block','aura-avatar-ui.service'],check=True,capture_output=True)
def pid():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
end=time.monotonic()+35
while pid()!='0' and time.monotonic()<end:time.sleep(.2)
assert pid()=='0';subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True)
s.update(phase='FACE_CENTER_GUI_TEST_STARTING',startup_config_sha256=sha(c),pre_follow_readback=m['readback'],automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'configured_test_duration_s':20,'control_polarity':-1,'automatic_following_started':False,'motor_commands_sent':0}))
