import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd';G=Path('/home/root/aura-pan-wide-resume-20261029/gui-wide-v1');R=G.parent/'55152f95'
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=2) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
until=time.monotonic()+65;u=None
while time.monotonic()<until:
 try:
  candidate=get(8783,'/api/state')
  if candidate.get('manual_pan',{}).get('state')=='READY':u=candidate;break
 except Exception:pass
 time.sleep(.5)
assert u is not None,'Wide GUI not READY'
h=get(8790,'/health');m=u['manual_pan'];assert m['minimum_us']==500 and m['maximum_us']==2500
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and not m['automatic_following']
assert h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
cfg=json.loads((G/'startup/config.json').read_text());A=Path(cfg['runtime'])/'aura'
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==v for n,v in cfg['component_sha256'].items())
result={'status':'WIDE_DEPLOYED_GUI_READY_USER_EVALUATES_MOTION','boot_id':BOOT,'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),'gui':str(G),'gui_config_sha256':hashlib.sha256((G/'startup/config.json').read_bytes()).hexdigest(),'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),'camera':{k:h[k] for k in ['pid','capture_hz','detection_hz','camera_error','detector_error']},'identity_ready':h['identity']['ready'],'display':u['avatar_display'],'manual_pan':m,'phase':u['phase'],'audio_state':u['audio_output_state'],'listening_enabled':u['handsfree_dialogue']['enabled'],'microphone_open':u['handsfree_dialogue']['microphone_open'],'components_verified':len(cfg['component_sha256']),'faults':{'primary':h['dpu_schedule']['primary_period_overruns'],'optional':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()}},'physical_angle_measured':False,'additional_motor_test_requested':False,'ARM_or_COMMIT_sent_by_this_deployment':False}
(R/'final-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
