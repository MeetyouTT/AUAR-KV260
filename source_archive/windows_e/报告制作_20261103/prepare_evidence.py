from pathlib import Path
from datetime import datetime,timezone
import json,sys,csv,subprocess,re,shutil,hashlib
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
d=json.loads((R/'evidence/live_board_samples.json').read_text(encoding='utf-8'));rows=d['samples']
def q(a,p):
 a=sorted(a);pos=(len(a)-1)*p;i=int(pos);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(pos-i)
cpu=[]
for a,b in zip(rows,rows[1:]):
 z=[y-x for x,y in zip(a['cpu'],b['cpu'])];total=sum(z);busy=total-z[3]-z[4]
 cpu.append({'time_s':b['t']-rows[0]['t'],'cpu_pct':100*busy/total,'busy_ticks':busy,'total_ticks':total,
 'memory_used_gib':(b['mem_total_kib']-b['mem_available_kib'])/1048576,'capture_age_ms':b['camera']['capture_age_ms'],
 'observation_age_ms':b['camera']['observation_age_ms'],'last_inference_ms':b['camera']['last_inference_ms']})
ping=[float(x) for x in re.findall(r'time=([0-9.]+) ms',d['ping']['stdout'])]
schedule=rows[0]['schedule'];last=rows[-1]['schedule'];dt=d['monotonic_duration_s']
stats={'host_start_utc':d['host_start_utc'],'host_end_utc':d['host_end_utc'],'boot_id':d['boot_id'],'duration_s':dt,
 'cpu_intervals':len(cpu),'cpu_mean_pct':100*sum(x['busy_ticks'] for x in cpu)/sum(x['total_ticks'] for x in cpu),
 'cpu_p95_pct':q([x['cpu_pct'] for x in cpu],.95),'cpu_max_pct':max(x['cpu_pct'] for x in cpu),
 'memory_mean_used_gib':sum((x['mem_total_kib']-x['mem_available_kib'])/1048576 for x in rows)/len(rows),
 'memory_min_available_gib':min(x['mem_available_kib']/1048576 for x in rows),
 'camera_hz':(rows[-1]['camera']['capture_frames']-rows[0]['camera']['capture_frames'])/dt,
 'detected_hz':(rows[-1]['camera']['detected_frames']-rows[0]['camera']['detected_frames'])/dt,
 'primary_hz':(last['primary_calls']-schedule['primary_calls'])/dt,
 'primary_overrun_delta':last['primary_period_overruns']-schedule['primary_period_overruns'],
 'optional':{},'rtt_count':len(ping),'rtt_min_ms':min(ping),'rtt_mean_ms':sum(ping)/len(ping),
 'rtt_p50_ms':q(ping,.5),'rtt_p95_ms':q(ping,.95),'rtt_p99_ms':q(ping,.99),'rtt_max_ms':max(ping),
 'icmp_packet_loss_percent':0 if '0% packet loss' in d['ping']['stdout'] else None,
 'quantile_method':'linear interpolation at (n-1)*p; no one-way clock subtraction',
 'observation_age_p95_ms':q([x['camera']['observation_age_ms'] for x in rows],.95),
 'observation_age_max_ms':max(x['camera']['observation_age_ms'] for x in rows)}
for k,v in schedule.get('optional',{}).items():
 stats['optional'][k]={n:last['optional'][k].get(n,0)-v.get(n,0) for n in ['calls','native_completed','native_failures','period_overruns','completed'] if n in v}
 for n in list(stats['optional'][k]):
  if n in ['calls','native_completed','completed']:stats['optional'][k][n+'_hz']=stats['optional'][k][n]/dt
g=json.loads((R/'tmp_gui.json').read_text(encoding='utf-8'))
stats['gui']={k:g.get(k) for k in ['state','ui_page','dialogue_enabled','audio_output_state','runtime_faults']}
stats['gui']['listening_enabled']=g.get('automatic_conversation',{}).get('enabled')
stats['gui']['manual_pan']={k:v for k,v in g.get('manual_pan',{}).items() if k in ['state','enabled','following','follow_enabled','pulse_us','ready','error']}
stats['portrait']={k:g.get('portrait_offload',{}).get(k) for k in ['mode','ready','backend','target_fps','visible','sequence']}
b=json.loads((R/'tmp_board.json').read_text(encoding='utf-8'))
stats['runtime']={'config_sha256':b['config_sha256'],'runtime':b['config_fields']['runtime'],'component_count':b['component_count'],'python':b['python'],'alsa':b['alsa'],'os_release':b['os_release']}
(R/'evidence/live_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
with (R/'data/live_resources.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(cpu[0]));w.writeheader();w.writerows(cpu)
with (R/'data/live_rtt.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.writer(f);w.writerow(['icmp_sequence','rtt_ms']);w.writerows(enumerate(ping,1))
# Keep filtered summary and screen; remove temporary full API states from the deliverable tree.
for name in ['tmp_gui.json','tmp_board.json']:
 shutil.move(str(R/name),str(Path(r'E:\报告制作_20261103')/name))
# Collect exact new Ubuntu XSim receipts and final source-engineering evidence.
code=r'''from pathlib import Path
import json
base=Path('/home/ghmd/auar-techdoc-01a1a1a5/verification')
out={str(p.relative_to(base)):p.read_text() for p in base.rglob('*.json') if p.stat().st_size<200000}
print(json.dumps(out,ensure_ascii=False))
'''
r=subprocess.run(['ssh','aura-ubuntu','python3 -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
receipts=json.loads(r.stdout)
for name,t in receipts.items():
 p=R/'evidence/ubuntu_rtl'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
src=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_scheme_a_source_release_9a4f\auar_xuefei\report/evidence')
for p in src.glob('*'):shutil.copy2(p,R/'evidence'/('release_'+p.name))
print(json.dumps(stats,ensure_ascii=False,indent=2));print('rtl receipts',list(receipts))
