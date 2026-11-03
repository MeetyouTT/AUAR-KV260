issued=time.monotonic();reply=req('pan_stop');snapshots=[];deadline=time.monotonic()+5
while time.monotonic()<deadline:
 s=snap(req());snapshots.append(s);p=s['pan'];rb=p.get('readback') or {}
 if p.get('state')=='READY' and p.get('automatic_following') is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0:break
 time.sleep(.12)
final=snapshots[-1];p=final['pan'];rb=p.get('readback') or {}
stopped=p.get('state')=='READY' and p.get('automatic_following') is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0
report,digest=read_report(final['report'])
strings={'state','status','reason','decision','position','direction','recenter_phase','source_kind','kind','outcome','error_type','reference','left_reference','right_reference','target_kind','mode'}
drop={'identity','person','person_id','name','text','transcript','target_key','track_id','embedding','landmarks','image','box','boxes'}
def clean(v,k=''):
 if k in drop:return None
 if isinstance(v,dict):return {a:clean(b,a) for a,b in v.items() if a not in drop and (not isinstance(b,str) or a in strings)}
 if isinstance(v,list):return [clean(a,k) for a in v[-2048:]]
 if isinstance(v,str):return v[:160] if k in strings else None
 return v if isinstance(v,(int,float,bool)) or v is None else None
keys=['status','before','result','pre_stop_result','input_summary','control_parameters','zone','input_timing','reader_queue','submission_timing','live_writer','read_only_status_benchmark_ms','observation_trace','telemetry']
safe={k:clean(report.get(k),k) for k in keys if k in report}
print(json.dumps({'status':'ORIGINAL_20S_REPRO_STOPPED' if stopped else 'STOP_REQUIRES_READONLY_RECONCILIATION','STOP_submitted_once':True,'stop_issued_mono_ms':round(issued*1000),'final':final,'stop_snapshots':snapshots,'report':final['report'],'report_sha256':digest,'report_data':safe,'startup_sha256_after':sha(B/'startup/config.json'),'source_config_or_audio_changed':False,'new_initialization_submitted':False,'all_calls_complete':True}))
