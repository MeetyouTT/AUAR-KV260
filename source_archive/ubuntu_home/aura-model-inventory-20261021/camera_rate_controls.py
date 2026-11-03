import json,shutil,subprocess,urllib.request
from pathlib import Path
device='/dev/v4l/by-id/usb-HD_720P_Webcam_HD_720P_Webcam_20130901-video-index0'
out={'device':device,'controls_read_only':True,'v4l2_ctl_available':bool(shutil.which('v4l2-ctl'))}
if out['v4l2_ctl_available']:
    for name,args in [('current_format',['--get-fmt-video']),('current_frame_interval',['--get-parm']),('controls',['--list-ctrls-menus'])]:
        p=subprocess.run(['v4l2-ctl','--device',device]+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=4)
        out[name]={'exit_code':p.returncode,'output':p.stdout.decode()[:10000]}
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
out['health']={k:s.get(k) for k in ['pid','capture_frames','capture_hz','detection_hz','camera_error','detector_error']}
print(json.dumps(out))
