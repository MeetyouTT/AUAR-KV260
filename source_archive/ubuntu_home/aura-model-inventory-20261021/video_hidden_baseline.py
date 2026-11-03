import json,os,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port=8783,path='/api/state'):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def page(name):
 data=json.dumps({'type':'ui_page','page':name}).encode()
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=data,
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with op.open(req,timeout=5) as r:assert json.load(r)['ok']
 deadline=time.monotonic()+3
 while time.monotonic()<deadline:
  if get()['ui_page']==name:return
  time.sleep(.1)
 raise RuntimeError('UI page did not change')
def snapshot():
 u=get();p=Path('/proc/450593');fields=(p/'stat').read_text().rsplit(') ',1)[1].split()
 threads={}
 for task in (p/'task').iterdir():
  try:
   if (task/'comm').read_text().strip().startswith('queue'):
    f=(task/'stat').read_text().rsplit(') ',1)[1].split()
    threads[task.name]={'name':(task/'comm').read_text().strip(),'ticks':int(f[11])+int(f[12])}
  except OSError:pass
 return {'time':time.monotonic(),'page':u['ui_page'],'preview':u.get('ui_runtime',{}).get('preview_metrics'),
         'avatar':u.get('avatar_display'),'ticks':int(fields[11])+int(fields[12]),'queue_threads':threads}
before=get();h=get(8790,'/health');original=before['ui_page']
assert original=='vision' and before['phase']=='IDLE' and before['audio_output_state']=='IDLE_READY'
assert not before['playing'] and not before['paused'] and not before.get('pending_job')
assert not before.get('handsfree_dialogue',{}).get('microphone_open')
assert before.get('local_recording',{}).get('state')=='IDLE'
out={'scope':'ORIGINAL_HIDDEN_PREVIEW_LIFECYCLE_DIAGNOSTIC_NOT_GAIN','camera_pid':h['pid'],'original_page':original,'phases':[]}
try:
 for target in ('vision','main'):
  page(target);time.sleep(.5);a=snapshot();time.sleep(5);b=snapshot();elapsed=b['time']-a['time']
  hz=os.sysconf('SC_CLK_TCK');queues=[]
  for tid,row in b['queue_threads'].items():
   if tid in a['queue_threads']:
    queues.append({'tid':tid,'name':row['name'],'one_core_percent':100*(row['ticks']-a['queue_threads'][tid]['ticks'])/hz/elapsed})
  out['phases'].append({'page':target,'duration':elapsed,'preview_frames_delta':b['preview']['displayed_frames']-a['preview']['displayed_frames'],
   'preview_update_hz':b['preview']['update_hz'],'preview_visible_flag':b['preview']['frame_visible'],
   'gui_process_one_core_percent':100*(b['ticks']-a['ticks'])/hz/elapsed,'queues':queues})
finally:page(original)
out['restored_page']=get()['ui_page'];after=get(8790,'/health')
out['camera_pid_after']=after['pid'];out['optional_after']=after['dpu_schedule']['optional']
assert after['pid']==h['pid'] and out['restored_page']==original
print(json.dumps(out))
