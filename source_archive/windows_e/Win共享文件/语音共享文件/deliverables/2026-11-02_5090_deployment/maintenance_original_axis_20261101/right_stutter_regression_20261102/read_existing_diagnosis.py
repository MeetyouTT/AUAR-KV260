"""Bounded read of original status and existing telemetry; no new motion owner."""
import hashlib,http.client,json,os,subprocess,time
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura'
BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e';EXPECTED='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
start=time.monotonic();stop_sent=False
def request(method,path,body=None,port=8783):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        headers={'Origin':'http://127.0.0.1:'+str(port),'Host':'127.0.0.1:'+str(port)}
        if body is not None:body=json.dumps(body).encode();headers['Content-Type']='application/json'
        c.request(method,path,body=body,headers=headers);r=c.getresponse();data=r.read(2097153)
        assert len(data)<=2097152 and r.status==200
        return json.loads(data)
    finally:c.close()
STRINGS={'state','status','reason','decision','position','direction','recenter_phase','source_kind','kind','outcome','error_type','termination_reason','last_stop_reason','reference','left_reference','right_reference','target_kind','mode'}
DROP={'identity','person','person_id','person_name','name','text','transcript','target_key','track_id','embedding','embeddings','landmarks','image','images','box','boxes','source_path'}
def clean(v,key=''):
    if key in DROP:return None
    if isinstance(v,dict):return {k:clean(a,k) for k,a in v.items() if k not in DROP and (not isinstance(a,str) or k in STRINGS)}
    if isinstance(v,list):return [clean(a,key) for a in v[-2048:]]
    if isinstance(v,str):return v[:160] if key in STRINGS else None
    if isinstance(v,(int,float,bool)) or v is None:return v
    return None
def proc(pid):
    p=Path('/proc')/str(pid)
    try:
        parts=(p/'stat').read_text().rsplit(')',1)[1].split()
        return {'pid':int(pid),'birth_ticks':parts[19],'parent_pid':int(parts[1]),'command_sha256':sha(p/'cmdline'),'utime_ticks':int(parts[11]),'stime_ticks':int(parts[12]),'threads':int(parts[17]),'alive':True}
    except (FileNotFoundError,ProcessLookupError):return {'pid':pid,'alive':False}
def unit(n):
    r=subprocess.run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def projection(state):
    pan=state.get('manual_pan') or {};ff=pan.get('face_follow') or {}
    return {'sample_mono_ms':round(time.monotonic()*1000),'ui_page':state.get('ui_page'),'runtime_fault_count':(state.get('runtime_faults') or {}).get('count'),'pan':{k:clean(pan.get(k),k) for k in ['state','automatic_following','pulse_us','target_us','readback','backend_pid','history']},'pan_error_present':bool(pan.get('error')),'face_follow':{k:clean(ff.get(k),k) for k in ['state','status','active','running','pid','report_live','last_exit_code']},'report_path':ff.get('report'),'manual_owner':proc(pan['backend_pid']) if type(pan.get('backend_pid')) is int else None}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and sha(B/'startup/config.json')==EXPECTED
startup=json.loads((B/'startup/config.json').read_bytes());pins=startup['component_sha256'];assert len(pins)==380 and all(sha(A/n)==v for n,v in pins.items())
face=json.loads((A/'config/pan_face.local.json').read_bytes());root=Path(face['release_root']);manifest=root/'deployment-manifest.json'
assert sha(manifest)==face['manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
files=json.loads(manifest.read_bytes())['files'];assert len(files)==25 and all(sha(f['destination'])==f['sha256'] for f in files)
first=request('GET','/api/state');before=projection(first);pan=first.get('manual_pan') or {};rb=pan.get('readback') or {}
if pan.get('automatic_following') is True or pan.get('state') in ['MOVING','STOPPING'] or (type(rb.get('flags')) is int and rb['flags']!=0) or (type(rb.get('lease_left_ms')) is int and rb['lease_left_ms']!=0):
    stop_sent=True;stop_response=request('POST','/api/command',{'type':'pan_stop'})
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        current=request('GET','/api/state');p=current.get('manual_pan') or {};r=p.get('readback') or {}
        if p.get('state')=='READY' and p.get('automatic_following') is False and r.get('flags')==0 and r.get('lease_left_ms')==0:break
        time.sleep(.12)
paths=[]
if before.get('report_path'):paths.append(Path(before['report_path']))
paths.extend(sorted((root/'runs').glob('ui-*/trial.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:80])
reports=[];seen=set()
for path in paths:
    if time.monotonic()-start>20:break
    if str(path) in seen:continue
    seen.add(str(path))
    try:
        path.relative_to(root/'runs');assert path.is_file() and not path.is_symlink() and path.stat().st_size<=8388608
        raw=path.read_bytes();r=json.loads(raw)
    except (OSError,ValueError,AssertionError):continue
    if r.get('boot_id')!=BOOT:continue
    chosen={k:clean(r.get(k),k) for k in ['status','result','control_parameters','zone','input_timing','reader_queue','submission_timing','live_writer','read_only_status_benchmark_ms','observation_trace','telemetry','timing','maximum_control_turn_ms','max_control_turn_ms','detector_timing','packet_states','raw_positions','decisions'] if k in r}
    reports.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'boot_id':r.get('boot_id'),'consumer_manifest_sha256':r.get('consumer_manifest_sha256'),'control_polarity':r.get('control_polarity'),'error_present':bool(r.get('error')),'root_keys':list(r),'data':chosen})
reports.sort(key=lambda r:(r['path']==before.get('report_path'),((r['data'].get('result') or {}).get('heartbeat_mono_ms') or 0)),reverse=True)
reports=reports[:4]
gui=unit('aura-avatar-ui.service');cam=unit('aura-camera-ui.service');owners={'GUI':proc(int(gui['MainPID'])),'camera':proc(int(cam['MainPID']))}
launch=Path(startup['runtime'])/'launch.json'
if launch.is_file():owners['GTK']=proc(json.loads(launch.read_bytes())['pid'])
samples=[]
for n in range(2):
    s=request('GET','/api/state');h=request('GET','/health',port=8790)
    samples.append({'gui':projection(s),'camera':{k:h.get(k) for k in ['pid','board_boot_id','capture_frames','detected_frames','motion_sequence','camera_error','detector_error','preview_error']},'owners':{name:proc(v['pid']) for name,v in owners.items()},'loadavg':Path('/proc/loadavg').read_text().split()[:3]})
    if n==0:time.sleep(.6)
last=samples[-1]['gui'];p=last['pan'];rb=p.get('readback') or {};stopped=p.get('state')=='READY' and p.get('automatic_following') is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0
zone=Path(face['arguments']['zone-settings']);manual=json.loads((A/'config/pan_manual.local.json').read_bytes());direction=json.loads((A/'config/pan_direction.current.json').read_bytes())
print(json.dumps({'status':'EXISTING_TELEMETRY_CAPTURED_STOPPED' if stopped else 'EXISTING_TELEMETRY_CAPTURED_STATE_REQUIRES_ROOT','duration_s':round(time.monotonic()-start,3),'boot_id':BOOT,'startup_sha256':EXPECTED,'source380_verified':True,'control25_verified':True,'current_component_sha256':pins,'current_pan_config_sha256':{k:sha(A/k) for k in ['config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json']},'current_face_config':face,'zone_path':str(zone),'zone_sha256':sha(zone),'zone':json.loads(zone.read_bytes()),'manual_parameters':{k:manual.get(k) for k in ['enabled','automatic_following_enabled','manual_minimum_us','manual_maximum_us','maximum_step_us','maximum_duration_s','left_button_pulse_sign','center_reference_us','center_reference_source']},'direction':{k:direction.get(k) for k in ['boot_id','axis_camera_mirrored_control_polarity','status','current_boot_motion_measured']},'before':before,'samples':samples,'reports':reports,'original_STOP_submissions':int(stop_sent),'new_motion_started':False,'initialization_or_REFERENCE_or_ARM_or_COMMIT_submitted':False,'new_MMIO_owner':False,'source_or_config_changed':False,'final_stopped_READY':stopped,'all_observation_calls_complete':True}))
