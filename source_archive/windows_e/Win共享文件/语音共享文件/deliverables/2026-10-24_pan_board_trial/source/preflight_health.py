import json,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as response:return json.load(response)
h=get(8790,'/health');g=get(8783,'/api/state');s=h['dpu_schedule'];i=h.get('identity',{})
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera':{'pid':h['pid'],'detected_frames':h.get('detected_frames'),'detection_hz':h.get('detection_hz'),
  'identity_ready':i.get('ready'),'worker_alive':i.get('face_targets',{}).get('worker_alive'),
  'schedule':{k:s.get(k) for k in ['native_critical','owner_fenced','primary_calls','primary_period_overruns','optional','native_runtime']},
  'feature_inference':{k:i.get('feature_inference',{}).get(k) for k in ['kind','ready','completed','deferred']},
  'gaps':i.get('face_targets',{}).get('freshness_metrics',{}).get('counters',{}).get('observed_gap_intervals')},
 'gui':{k:g.get(k) for k in ['phase','audio_output_state','playing','monitor_enabled','listening_enabled']},
 'manual_pan':{k:g.get('manual_pan',{}).get(k) for k in ['state','error','pulse_us','target_us','automatic_following']},
 'local_recording_state':g.get('local_recording',{}).get('state'),
 'transcription_pending':g.get('local_transcription',{}).get('service',{}).get('pending'),
 'services_modified':False,'new_dpu_jobs_submitted':0}
print(json.dumps(result,ensure_ascii=False))
