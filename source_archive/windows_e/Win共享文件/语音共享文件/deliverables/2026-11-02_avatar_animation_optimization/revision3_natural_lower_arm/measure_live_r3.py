"""Passive 20 s native-swap counter/CPU sample. No control request."""
# IMPORT_DEVICE_READ_HEADER
import os
start_cfg=sha(P);g=unit('aura-avatar-ui.service');cam=unit('aura-camera-ui.service');go=owner(g['MainPID']);co=owner(cam['MainPID'])
cpus=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if p.joinpath('stat').read_text().rsplit(')',1)[1].split()[1]==g['MainPID']:cpus.append(int(p.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
def ticks(pid):
 a=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return int(a[11])+int(a[12])
hz=os.sysconf('SC_CLK_TCK');before={pid:ticks(pid) for pid in cpus+[int(g['MainPID'])]}
rows=[];started=time.monotonic()
for i in range(81):
 v=state();a=v['avatar_display'];h=v['handsfree_dialogue'];p=v['manual_pan']
 assert v['phase']=='IDLE' and not v['playing'] and not v['pending_job']
 assert h['enabled'] is False and h['microphone_open'] is False and p['automatic_following'] is False
 assert v['ui_page']=='main' and a['visible'] is True
 rows.append(dict(observed=time.monotonic(),display={k:a.get(k) for k in ('frames','paint_at','evaluate_ms','submit_ms','native_call_ms','gtk_callback_ms','egl_swap_ms','stale_frames','elapsed_dropped_seconds','mouth')},runtime_fault_count=v['runtime_faults']['count']))
 deadline=started+(i+1)*.25
 if i<80:time.sleep(max(0,deadline-time.monotonic()))
after={pid:ticks(pid) for pid in before};assert sha(P)==start_cfg and owner(g['MainPID'])==go and owner(cam['MainPID'])==co
dt=rows[-1]['observed']-rows[0]['observed'];first=rows[0]['display'];last=rows[-1]['display']
def pct(xs,q):
 a=sorted(xs);return a[int((len(a)-1)*q)]
out=dict(status='PASS_SAME_OWNER_PASSIVE_NATIVE_COUNTER_SAMPLE',startup_sha256=start_cfg,gui_owner=go,camera_owner=co,duration=dt,native_swaps=last['frames']-first['frames'],native_swap_fps=(last['frames']-first['frames'])/(last['paint_at']-first['paint_at']),gtk_process_cpu_percent={str(pid):(after[pid]-before[pid])/hz/dt*100 for pid in before},timings={k:{'p50':pct([x['display'][k] for x in rows],.5),'p95':pct([x['display'][k] for x in rows],.95),'max':max(x['display'][k] for x in rows)} for k in ('evaluate_ms','submit_ms','native_call_ms','gtk_callback_ms')},samples=rows,native_frames_are_real_swap_counter=True,sparse_samples_are_not_all_frame_interval_percentiles=True,raw_scene_content_exported=False)
print(json.dumps(out))
