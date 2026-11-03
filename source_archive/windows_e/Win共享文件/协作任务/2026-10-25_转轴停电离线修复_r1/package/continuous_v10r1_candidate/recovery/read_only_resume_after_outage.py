"""Collect new-boot evidence only. Never enables motion or edits a service."""
import hashlib,json,os,platform,subprocess,urllib.request
from pathlib import Path

OLD_BOOT='463c9307-5e47-49b0-b22f-5fd3fc21451c'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5')


def read(path,binary=False):
    try:return Path(path).read_bytes() if binary else Path(path).read_text().strip()
    except OSError:return None


def main():
    if platform.machine()!='aarch64' or os.geteuid()!=0:
        print(json.dumps(dict(status='HOST_EXECUTION_REFUSED',board_accessed=False,motion_authorized=False)))
        return 2
    boot=read('/proc/sys/kernel/random/boot_id')
    result=dict(status='READ_ONLY_POST_OUTAGE_INSPECTION',board_boot_id=boot,
        changed_from_historical_boot=boot is not None and boot!=OLD_BOOT,
        historical_boot_id=OLD_BOOT,MMIO_opened=False,ARM=0,COMMIT=0,
        services_modified=False,motion_authorized=False)
    fdt=read('/sys/firmware/fdt',True)
    firmware=read('/proc/device-tree/fpga-full/firmware-name',True)
    result['platform']=dict(fdt_sha256=hashlib.sha256(fdt).hexdigest() if fdt is not None else None,
        firmware=firmware.rstrip(b'\0').decode(errors='replace') if firmware is not None else None,
        fpga_state=read('/sys/class/fpga_manager/fpga0/state'),vart_config=read('/etc/vart.conf'))
    result['units']={}
    for unit in ['aura-camera-ui.service','aura-avatar-ui.service','aura-face-zone-editor.service']:
        call=subprocess.run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState',
            '-p','Result','-p','ExecMainStatus','-p','NRestarts'],capture_output=True,text=True,timeout=4)
        result['units'][unit]=dict(returncode=call.returncode,
            properties=dict(line.split('=',1) for line in call.stdout.splitlines() if '=' in line))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for name,port,path in [('camera',8790,'/health'),('ui',8783,'/api/state')]:
        try:
            with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as response:value=json.load(response)
            if name=='camera':
                schedule=value.get('dpu_schedule') or {};identity=value.get('identity') or {}
                result[name]=dict(reachable=True,pid=value.get('pid'),identity_ready=identity.get('ready'),
                    owner_fenced=schedule.get('owner_fenced'),primary_overruns=schedule.get('primary_period_overruns'),
                    optional_overruns={k:v.get('overruns') for k,v in schedule.get('optional',{}).items()})
            else:
                manual=value.get('manual_pan') or {}
                result[name]=dict(reachable=True,manual_state=manual.get('state'),error=manual.get('error'),
                    automatic_following=manual.get('automatic_following'),readback=manual.get('readback'))
        except Exception as error:result[name]=dict(reachable=False,error_type=type(error).__name__)
    result['historical_release_files']={}
    for path in [F/'continuous-v9/deployment-manifest.json',F/'face-source-v11/deployment-manifest.json',
                 F/'zone-editor-v5/face_zone_editor.py']:
        raw=read(path,True)
        result['historical_release_files'][str(path)]=hashlib.sha256(raw).hexdigest() if raw is not None else None
    for name,path in [('manual_config',N/'runtime/aura/config/pan_manual.local.json'),
                      ('zone_settings',N.parent/'face-zone-settings.json')]:
        try:
            value=json.loads(Path(path).read_text())
            result[name]=dict(path=str(path),boot_matches_current=value.get('boot_id',value.get('board_boot_id'))==boot)
        except Exception as error:result[name]=dict(path=str(path),error_type=type(error).__name__)
    result['next_step']='Review new boot, firmware, preserved faults and current stopped state; do not reuse old motion permission.'
    print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
