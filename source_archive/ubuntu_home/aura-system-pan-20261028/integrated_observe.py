"""Numeric-only integrated status: no text, names, PCM or images."""
import json,time,urllib.request
from pathlib import Path
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];follow=m.get('face_follow') or {}
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime_s':float(Path('/proc/uptime').read_text().split()[0]),'camera':{k:h.get(k) for k in ['pid','capture_hz','detection_hz','capture_frames','detected_frames','camera_error','detector_error']},'identity_ready':h['identity']['ready'],'display':u['avatar_display'],'ui':{k:u.get(k) for k in ['phase','audio_output_state','playing']},'handsfree':{k:u['handsfree_dialogue'].get(k) for k in ['enabled','state','reason','microphone_open','visual_bound','conversation_entered']},'manual':{k:m.get(k) for k in ['state','automatic_following','pulse_us','minimum_us','maximum_us','readback','error']},'follow_report':follow.get('report')}
p=Path(follow.get('report','/nonexistent'))
if p.is_file():
 r=json.loads(p.read_text());x=r.get('result',{});d['follow']={k:x.get(k) for k in ['state','reason','active','fatal','pulse_us','target_us','commands_accepted','segments','range_us','elapsed_s','readback']};d['follow']['status']=r.get('status')
def numeric(value,depth=0):
 if depth>4:return None
 if isinstance(value,dict):return {k:numeric(v,depth+1) for k,v in value.items() if isinstance(v,(dict,int,float,bool)) and not any(w in k.lower() for w in ['token','profile','identity','name','key'])}
 if isinstance(value,(int,float,bool)):return value
 return None
d['timing_metrics']={k:numeric(u.get(k,{})) for k in ['metrics','streaming_reply','last_job','audio_frontend','voice_barge_in']}
d['dpu_faults']={'primary':h['dpu_schedule']['primary_period_overruns'],'optional':{k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()}}
print(json.dumps(d))
