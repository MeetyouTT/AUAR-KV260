"""Guard one candidate reboot and passively capture U-Boot/kernel startup."""
import hashlib
import importlib.util
import json
import re
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path

PACKAGE=Path(__file__).resolve().parent.parent
CAPTURE_SUFFIX='hdmi-candidate-warmboot'
STATUS_FILE='warmboot.json'
OPERATION='candidate_warmboot'
PREFLIGHT='''import hashlib,json,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='5cd17bb7-30da-4a4f-bf18-8167508de1f4'
root=Path('/boot/aura-hdmi-preinit-20261021')
meta=json.loads((root/'before.json').read_text())
assert hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()==meta['candidate_uenv_sha256']
assert hashlib.sha256((Path('/boot')/meta['candidate_image_name']).read_bytes()).hexdigest()==meta['candidate_image_sha256']
assert not Path('/sys/module/zynqmp_dpsub/parameters/initial_aux_delay_ms').exists()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
assert s['phase']=='IDLE' and not s.get('playing'), 'Application busy'
print(json.dumps({'candidate_files_verified':True,'ui_phase':s['phase']}))
'''
POSTCHECK='''import json,re,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url,keys):
 try:
  with op.open(url,timeout=2) as r:v=json.load(r)
  return {k:v.get(k) for k in keys}
 except Exception as e:return {'unavailable':type(e).__name__+': '+str(e)}
deadline=time.monotonic()+55
while time.monotonic()<deadline:
 u=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True,timeout=5)
 if u.count('ActiveState=active')==3:break
 time.sleep(1)
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'cmdline':Path('/proc/cmdline').read_text().strip(),'version':Path('/proc/version').read_text().strip(),'units':u,'parameters':{p.name:p.read_text().strip() for p in Path('/sys/module/zynqmp_dpsub/parameters').glob('*')}}
raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
v['edid_bytes']=len(raw)
v['display']=subprocess.run(['env','DISPLAY=:0','xrandr','--current'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10).stdout
v['gui']=get('http://127.0.0.1:8783/api/state',['phase','playing','ui_page','error','avatar_display'])
v['camera']=get('http://127.0.0.1:8790/health',['pid','capture_frames','capture_hz','detection_hz','identity_recognition','camera_error','detector_error'])
dmesg=subprocess.check_output(['dmesg'],text=True)
v['kernel_display']=[x for x in dmesg.splitlines() if 'AURA initial AUX' in x or re.search(r'zynqmp.*(dp|display)|aux.*(error|fail)|training.*(error|fail)',x,re.I)]
v['zocl_loaded']=Path('/sys/module/zocl').exists()
v['physical_fix_verified']=False
print(json.dumps(v))
'''


def main():
    spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
    wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
    mod=wire.transport_module()
    out=Path('/home/ghmd/aura-identity-dpu-check-20261018/evidence')/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+CAPTURE_SUFFIX)
    out.mkdir(parents=True)
    status=dict(evidence=str(out),operation=OPERATION,reboot_sent=False,root_prompt_seen=False,complete=False)
    uart=None
    try:
        with (out/'serial.raw').open('xb') as raw:
            try:
                uart=mod.UART(raw);uart.connect()
                rc,body,digest=uart.command(wire.wire(PREFLIGHT),'HDMIPRE',20)
                (out/'preflight.output').write_bytes(body)
                assert rc==0,body.decode(errors='replace')[-500:]
                status['preflight']=json.loads(body)
                # Echo is restored before Linux exits. No console input is sent
                # during bootloader countdown or kernel initialization.
                code="import subprocess;subprocess.run(['stty','echo'],check=True);subprocess.run(['systemctl','--no-block','reboot'],check=True)"
                uart.line('python3 -c '+shlex.quote(code));status['reboot_sent']=True
                start=last=time.monotonic();kernel_seen=False
                while time.monotonic()-start<220:
                    uart.receive(1)
                    kernel_seen=kernel_seen or b'Starting kernel' in uart.buf or b'Linux version ' in uart.buf
                    if kernel_seen and mod.PROMPT.search(uart.buf):
                        uart.shell_ready=True;status['root_prompt_seen']=True;break
                    if time.monotonic()-last>15:
                        print(json.dumps({'boot_wait_s':round(time.monotonic()-start,1),'kernel_seen':kernel_seen}),flush=True);last=time.monotonic()
                status['boot_elapsed_seconds']=round(time.monotonic()-start,3)
                status['kernel_seen']=kernel_seen
                text=uart.buf.decode(errors='replace')
                status['boot_evidence']=[x for x in text.splitlines() if 'AURA initial AUX' in x or 'Linux version ' in x or 'AURA initial AUX delay candidate' in x]
                assert status['root_prompt_seen'],'New Linux prompt was not observed; no further input sent'
                rc,body,digest=uart.command(wire.wire(POSTCHECK),'HDMIPOST',85)
                (out/'postcheck.output').write_bytes(body)
                assert rc==0,body.decode(errors='replace')[-1000:]
                v=json.loads(body);(out/'postcheck.json').write_text(json.dumps(v,indent=2)+'\n')
                status['postcheck']=v;status['complete']=True
                print(json.dumps(v),flush=True)
            finally:
                if uart:status['console_echo_restored']=uart.close()
    except Exception as exc:status['error']=str(exc)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    (PACKAGE/'evidence'/STATUS_FILE).write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    if not status['complete']:raise SystemExit(1)


if __name__=='__main__':main()
