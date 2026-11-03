"""Read the chosen line and test RT permission in this short-lived process only."""
import json,os,time
from pathlib import Path
p=Path('/home/root/aura-pan-current-20261024/463c9307/face-zone-settings.json');value=json.loads(p.read_text())
old=os.sched_getscheduler(0);params=os.sched_getparam(0);report={'policy_before':old,'supported':False}
try:
 os.sched_setscheduler(0,os.SCHED_FIFO,os.sched_param(10));report.update(supported=True,policy_during=os.sched_getscheduler(0))
except OSError as exc:report.update(error=type(exc).__name__,errno=exc.errno)
finally:os.sched_setscheduler(0,old,params)
report['policy_restored']=os.sched_getscheduler(0)==old
x,y,w,h=value['viewport'];content_w=min(w,h*value['frame_width']/value['frame_height']);offset=(w-content_w)/2
right=(value['right_ratio']*w-offset)/content_w
print(json.dumps({'zone':value,'right_ratio_in_camera_image':right,'video_content_rect':[x+offset,y,content_w,h],'rt_permission':report,'motor_commands':0}))
