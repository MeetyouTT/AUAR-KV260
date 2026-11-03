"""Select existing numeric diagnostics only. No device calls."""
from pathlib import Path
import json,hashlib,csv

ROOT=Path(__file__).resolve().parent.parent
BASE=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/visual_artifact_fix_20261102')
OUT=ROOT/'diagnostic_data';OUT.mkdir(exist_ok=True)
sources=[]
def read(name):
 p=BASE/name;raw=p.read_bytes();sources.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)});return json.loads(raw)

aba=read('AUDIO_CONTENTION_ABA_1_RESULT.json');analysis=read('AUDIO_CONTENTION_ABA_1_ANALYSIS.json')
assert analysis['source_result_sha256']==sources[0]['sha256']
proc=read('PROCESS_CPU_CURRENT_ON_1_RESULT.json');ident=read('HIGH_CPU_PROGRAM_IDENTITIES_1_RESULT.json')
a=aba['board_result'];p=proc['board_result'];rows=a['samples'];t0=rows[0]['mono_ms'];hz=a['clock_ticks_per_second']
chosen=[];phase_stats=[]
for phase in ['A_LISTEN_ON','B_LISTEN_OFF','C_LISTEN_ON']:
 group=[r for r in rows if r['phase']==phase];first,last=group[0],group[-1];span=(last['mono_ms']-first['mono_ms'])/1000
 stats={'phase':phase,'n':len(group),'span_s':span,'first_elapsed_s':(first['mono_ms']-t0)/1000,'last_elapsed_s':(last['mono_ms']-t0)/1000,'preview_counter_delta':last['displayed_frames']-first['displayed_frames']}
 stats['software_preview_counter_rate_hz']=stats['preview_counter_delta']/span
 assert stats['preview_counter_delta']==analysis['phase_results'][phase]['display_counter_delta']
 for role in ['GUI','camera']:
  x,y=first[role+'_process'],last[role+'_process']
  stats[role+'_cpu_percent_single_core_100']=((y['utime_ticks']+y['stime_ticks'])-(x['utime_ticks']+x['stime_ticks']))/hz/span*100
  stats[role+'_main_rq_wait_percent_of_elapsed']=(y['main_thread_runqueue_ns']-x['main_thread_runqueue_ns'])/(span*1e9)*100
  assert abs(stats[role+'_cpu_percent_single_core_100']-analysis['phase_results'][phase][role+'_process_cpu_percent'])<.15
  assert abs(stats[role+'_main_rq_wait_percent_of_elapsed']-analysis['phase_results'][phase][role+'_process_main_rq_wait_percent'])<.15
 phase_stats.append(stats)
 for r in group:
  chosen.append({'phase':phase,'elapsed_s':(r['mono_ms']-t0)/1000,'raw_header_age_ms':r['raw_header']['raw_header_age_ms'],'face_source_age_ms':r.get('face_source_age_ms'),'face_detection_age_ms':r.get('face_detection_age_ms'),'displayed_frames':r.get('displayed_frames'),'gui_request_ms':r['request_ms'].get('GUI'),'camera_request_ms':r['request_ms'].get('camera'),'face_request_ms':r['request_ms'].get('face')})
programs={r['pid']:r for r in ident['board_result']['programs']}
processes=[]
category_labels={'camera_native':'相机与视觉服务','GUI_GTK':'GTK界面与业务','audio_related':'音频播放进程','display_server':'X11显示服务','face_overlay_editor':'人脸位置编辑器','this_metadata_probe':'本次元数据探针','GUI_supervisor':'GUI监管进程','audio_capture':'音频采集进程'}
for r in p['processes']:
 label=category_labels.get(r['category'],'其他进程 PID '+str(r['pid']))
 program=programs.get(r['pid'])
 if program:
  assert program['command_sha256']==r['command_sha256']
  names=[Path(x).name for x in program['public_program_paths']]
  if 'board_frontend_process.py' in names:label='音频前端进程'
 processes.append({'pid':r['pid'],'label':label,'cpu_percent_single_core_100':r['cpu_percent'],'category':r['category']})
data={'kind':'existing_short_diagnostic_not_180s_acceptance','original_sources':sources,'boot_id':a['boot_id'],'startup_sha256':a['startup_sha256'],'original_listening_restored':a['original_listening_restored'],'axis_commands_sent':a['axis_commands_sent'],'source_or_model_or_axis_parameters_changed':a['source_or_camera_or_model_or_axis_parameters_changed'],'physical_scanout_measured':False,'phases':phase_stats,'samples':chosen,'process_snapshot':{'duration_s':p['actual_seconds'],'processes':processes},'formal_180s_resource_measurement':'NOT_MEASURED','DPU_hardware_busy_measurement':'NOT_MEASURED','temperature':'No temperature sensor values in these source records'}
(OUT/'DIAGNOSTIC_INPUT.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for filename,values in [('短时诊断_72快照.csv',chosen),('短时诊断_分段统计.csv',phase_stats),('短时诊断_进程CPU.csv',processes)]:
 with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
print(json.dumps({'samples':len(chosen),'phase_stats':phase_stats,'snapshot_duration_s':p['actual_seconds'],'no_new_board_access':True},ensure_ascii=False))
