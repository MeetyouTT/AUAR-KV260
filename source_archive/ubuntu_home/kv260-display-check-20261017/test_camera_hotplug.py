"""Exercise one selected webcam's USB deauthorization and automatic recovery."""
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=2) as stream:
        return json.load(stream)


def service():
    return subprocess.check_output(['systemctl','show','aura-camera-ui.service',
        '-p','ActiveState','-p','SubState','-p','NRestarts','-p','MainPID'],text=True)


camera='http://127.0.0.1:8790'
gui='http://127.0.0.1:8783'
before=get(camera,'/health')
assert before['capture_frames']>=3 and not before['camera_error'],before
dev=before['device']
assert dev['usb']=={'idVendor':'0c45','idProduct':'6341','serial':'20130901'},dev
usb=Path('/sys/bus/usb/devices')/dev['usb_path']
assert all((usb/k).read_text().strip()==v for k,v in dev['usb'].items())
auth=usb/'authorized'
assert auth.read_text().strip()=='1'
gui_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
status_before=service()
lost=None
try:
    auth.write_text('0')
    time.sleep(14)
    ui=get(gui,'/api/state')
    lost={'service':service(),'fixed_link_exists':Path(dev['configured']).exists(),
          'frame_visible':ui['ui_runtime']['frame_visible'],'link':ui['ui_runtime']['link']}
finally:
    if auth.exists():auth.write_text('1')
deadline=time.monotonic()+16
after=None
while time.monotonic()<deadline:
    try:
        after=get(camera,'/health')
        if after['capture_frames']>=3 and after['camera_epoch']!=before['camera_epoch']:break
    except (OSError,ValueError):pass
    time.sleep(.3)
assert after and after['capture_frames']>=3,after
time.sleep(2)
final=get(camera,'/health');ui=get(gui,'/api/state')
old_url='/v1/ui/preview.jpg?camera_epoch='+before['camera_epoch']+'&frame_id='+str(before['observation_frame_id'])
try:
    urllib.request.urlopen(camera+old_url,timeout=2).close();old_status=200
except urllib.error.HTTPError as exc:old_status=exc.code
gui_after=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
ok=(not lost['fixed_link_exists'] and not lost['frame_visible'] and 'ActiveState=failed' not in lost['service']
    and final['capture_frames']>after['capture_frames'] and final['detected_frames']>after['detected_frames']
    and final['device']['configured']==dev['configured'] and final['camera_epoch']!=before['camera_epoch']
    and not any(final[k] for k in ['camera_error','detector_error','preview_error'])
    and ui['ui_runtime']['frame_visible'] and ui['ui_runtime']['link']=='READY'
    and gui_pid==gui_after and old_status==404)
print(json.dumps({'passed':bool(ok),'scope':'USB_AUTHORIZED_SIMULATED_UNPLUG_REPLUG',
 'before':before,'lost':lost,'after':after,'final':final,'service_before':status_before,
 'service_final':service(),'old_preview_status':old_status,'gui_pid_before':gui_pid,'gui_pid_after':gui_after,
 'ui_page':ui['ui_page'],'ui_preview':ui['ui_runtime']['preview_metrics']},ensure_ascii=False))
raise SystemExit(0 if ok else 1)
