"""60-second idle main-page baseline. Only UI page selection may be changed."""
import statistics

def numeric_tree(obj,depth=0):
    if not isinstance(obj,dict):return {}
    out=numeric(obj)
    if depth<3:
        for k,v in obj.items():
            if isinstance(v,dict):out[k]=numeric_tree(v,depth+1)
    return out

def model_health():
    c=http.client.HTTPConnection('192.168.50.1',8797,timeout=2)
    try:
        c.request('GET','/health');r=c.getresponse();raw=r.read(262145)
        assert r.status==200 and len(raw)<=262144
        h=json.loads(raw)
        assert h.get('role')=='model_inference_only'
        return dict(available=True,metrics=numeric_tree(h),error=None)
    except Exception as exc:
        return dict(available=False,metrics={},error=type(exc).__name__)
    finally:c.close()

def process_table():
    out={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            out[int(path.name)]=dict(ppid=int(fields[1]),cpu_ticks=int(fields[11])+int(fields[12]),
                                     birth_ticks=int(fields[19]),rss_kb=int(fields[21])*os.sysconf('SC_PAGE_SIZE')/1024)
        except (OSError,ValueError,IndexError):pass
    return out

def processes():
    table=process_table();selected={v['pid'] for v in EXPECTED_OWNERS.values()}
    while True:
        new={pid for pid,row in table.items() if row['ppid'] in selected}
        if new<=selected:break
        selected |= new
    roles={v['pid']:k for k,v in EXPECTED_OWNERS.items()}
    # Observe existing audio processes only; never start an audio source or player.
    audio_tokens=('arecord','aplay','board_asr_frontend','board_audio_frontend','frontend_worker','board_speaker_worker')
    audio_pids=[]
    for pid in table:
        if pid==os.getpid():continue
        try:
            argv=(Path('/proc')/str(pid)/'cmdline').read_bytes().decode('utf-8','replace').split('\0')
        except OSError:continue
        basenames=[Path(arg).name for arg in argv[:4]]
        if any(any(token==name or name.startswith(token+'.') for name in basenames) for token in audio_tokens):
            selected.add(pid);audio_pids.append(pid);roles.setdefault(pid,'audio')
    output={}
    for pid in sorted(selected):
        if pid not in table:continue
        row=dict(table[pid],pid=pid,role=roles.get(pid,'owned_child'),pss_kb=None)
        try:
            for line in (Path('/proc')/str(pid)/'smaps_rollup').read_text().splitlines():
                if line.startswith('Pss:'):row['pss_kb']=int(line.split()[1]);break
        except OSError:pass
        output[str(pid)]=row
    return output,audio_pids

def cpu_board():
    lines=Path('/proc/stat').read_text().splitlines();values=[int(x) for x in lines[0].split()[1:9]]
    return dict(total_ticks=sum(values),busy_ticks=sum(values)-values[3]-values[4],
                logical_cpus=sum(line.startswith('cpu') and len(line.split()[0])>3 for line in lines))

def thread_sample(pid,tid):
    if type(tid) is not int or tid<1:return None
    try:
        fields=(Path('/proc')/str(pid)/'task'/str(tid)/'stat').read_text().rsplit(')',1)[1].split()
        return dict(tid=tid,cpu_ticks=int(fields[11])+int(fields[12]),birth_ticks=int(fields[19]))
    except (OSError,ValueError,IndexError):return None

def collect():
    began=time.monotonic();cpu_started=time.process_time()
    v=get_json(8783,'/api/state');health=get_json(8790,'/health')
    safe=assert_safe(v)
    assert safe['page']=='main'
    avatar=v.get('avatar_display',{})
    assert avatar.get('visible') is True and avatar.get('frame_scheduling_active') is True
    assert avatar.get('target_fps')==16
    assert health['pid']==430894 and health['dpu_schedule'].get('owner_fenced') is False
    renderer=v.get('avatar_renderer',{});b=v.get('board_business',{});memory=b.get('memory',{})
    dpu=health.get('dpu_schedule',{});identity=health.get('identity',{})
    proc,audio=processes();mh=model_health()
    row=dict(observed_mono=time.monotonic(),state=safe,ui_tick_ms=v.get('ui_tick_ms'),
             ui={k:numeric(v.get(k)) for k in ('ui_stage_timings_ms','ui_runtime_timings_ms','ui_settings_timings_ms','ui_callback_previous','ui_widget_writes')},
             avatar=numeric(avatar),avatar_presentation_state=avatar.get('presentation_state') if avatar.get('presentation_state') in ('visible','hidden','idle','unknown') else None,
             renderer=dict(metrics=numeric(renderer),timings_ms=numeric(renderer.get('timings_ms')),profile=numeric_tree(renderer.get('profile')),
                           worker_fault_count=renderer.get('worker_faults',{}).get('count')),
             processes=proc,audio_process_pids=audio,board_cpu=cpu_board(),
             threads=dict(gtk_main=thread_sample(496789,496789),renderer_worker=thread_sample(496789,renderer.get('worker_native_tid'))),
             camera={k:health.get(k) for k in ('capture_frames','detected_frames','preview_frames','observation_frame_id','capture_age_ms','observation_age_ms','capture_hz','detection_hz','preview_hz','last_inference_ms','native_primary_deferred')},
             camera_faults=dict(camera_error=bool(health.get('camera_error')),detector_error=bool(health.get('detector_error')),
                                preview_error=bool(health.get('preview_error')),identity_error=bool(identity.get('error')),
                                face_worker_faults=identity.get('face_targets',{}).get('worker_faults')),
             pipeline_stages={k:numeric(s) for k,s in health.get('pipeline_metrics',{}).get('stages',{}).items()},
             dpu=dict(metrics=numeric(dpu),optional=numeric_tree(dpu.get('optional')),
                      face_metrics=numeric(identity.get('face_targets')),feature_metrics=numeric(identity.get('feature_inference')),
                      identity_metrics={k:identity.get(k) for k in ('processed','discarded','deferred','pending_frames','last_inference_ms')}),
             memory=dict(metrics=numeric(memory),error_present=bool(memory.get('error')),retry=numeric(memory.get('retry_backoff')),
                         summary_code_present=bool(memory.get('summary_diagnostics',{}).get('code'))),
             visual_timeline=numeric(b.get('visual_timeline')),model_health=mh,
             observer=dict(cpu_ms=(time.process_time()-cpu_started)*1000,wall_ms=(time.monotonic()-began)*1000))
    return row

def stats(values):
    v=sorted(float(x) for x in values if finite(x))
    if not v:return dict(n=0,median=None,p95=None,maximum=None)
    return dict(n=len(v),median=statistics.median(v),p95=v[max(0,math.ceil(.95*len(v))-1)],maximum=v[-1])

def field_stats(rows,group):
    keys=sorted({k for row in rows for k in row.get(group,{})})
    return {key:stats([row.get(group,{}).get(key) for row in rows]) for key in keys}

def unique_rows(rows,key):
    found=set();out=[]
    for row in rows:
        token=key(row)
        if token is None or token in found:continue
        found.add(token);out.append(row)
    return out

def summarize(rows):
    elapsed=rows[-1]['observed_mono']-rows[0]['observed_mono'];hz=os.sysconf('SC_CLK_TCK')
    ui_rows=unique_rows(rows,lambda r:r['ui']['ui_callback_previous'].get('sequence'))
    draw_rows=unique_rows(rows,lambda r:r['avatar'].get('frames'))
    renderer_rows=unique_rows(rows,lambda r:r['renderer']['metrics'].get('sequence'))
    camera_rows=unique_rows(rows,lambda r:r['camera'].get('observation_frame_id'))
    board=[];per_process={};per_thread={}
    for a,b in zip(rows,rows[1:]):
        dt=b['observed_mono']-a['observed_mono'];tot=b['board_cpu']['total_ticks']-a['board_cpu']['total_ticks']
        if tot>0:board.append(100*(b['board_cpu']['busy_ticks']-a['board_cpu']['busy_ticks'])/tot)
        for pid,p in b['processes'].items():
            old=a['processes'].get(pid)
            if old and old['birth_ticks']==p['birth_ticks']:
                per_process.setdefault(pid,[]).append(100*(p['cpu_ticks']-old['cpu_ticks'])/hz/dt)
        for name,p in b['threads'].items():
            old=a['threads'].get(name)
            if p and old and p['tid']==old['tid'] and p['birth_ticks']==old['birth_ticks']:
                per_thread.setdefault(name,[]).append(100*(p['cpu_ticks']-old['cpu_ticks'])/hz/dt)
    procs={}
    for pid in sorted({k for row in rows for k in row['processes']}):
        ps=[row['processes'][pid] for row in rows if pid in row['processes']]
        procs[pid]=dict(role=ps[-1]['role'],birth_ticks=ps[-1]['birth_ticks'],cpu_one_core_percent=stats(per_process.get(pid,[])),
                       rss_kb=stats([p.get('rss_kb') for p in ps]),pss_kb=stats([p.get('pss_kb') for p in ps]))
    counts={}
    for name,group,fields in [('avatar','avatar',('frames','author_ticks','rejected_controls','stale_frames')),
                              ('camera','camera',('capture_frames','detected_frames','preview_frames')),
                              ('visual_timeline','visual_timeline',('steps','errors'))]:
        counts[name]={k:dict(first=rows[0][group].get(k),last=rows[-1][group].get(k),
                           delta=rows[-1][group][k]-rows[0][group][k],per_second=(rows[-1][group][k]-rows[0][group][k])/elapsed)
                      for k in fields if finite(rows[0][group].get(k)) and finite(rows[-1][group].get(k))}
    return dict(elapsed_seconds=elapsed,samples=len(rows),sampling_interval_target_seconds=2,
                unique_ui_publications=len(ui_rows),unique_avatar_frames=len(draw_rows),unique_renderer_sequences=len(renderer_rows),unique_camera_frames=len(camera_rows),
                board_cpu_busy_percent=stats(board),logical_cpus=rows[-1]['board_cpu']['logical_cpus'],
                processes=procs,threads_one_core_percent={k:stats(v) for k,v in per_thread.items()},
                ui={name:{k:stats([r['ui'][name].get(k) for r in ui_rows]) for k in sorted({k for r in ui_rows for k in r['ui'][name]}) if k not in ('sequence','completed_mono')}
                    for name in ('ui_stage_timings_ms','ui_runtime_timings_ms','ui_settings_timings_ms','ui_callback_previous','ui_widget_writes')},
                ui_tick_ms=stats([r['ui_tick_ms'] for r in ui_rows]),avatar=field_stats([dict(avatar=r['avatar']) for r in draw_rows],'avatar'),
                renderer_timings_ms=field_stats([dict(timing=r['renderer']['timings_ms']) for r in renderer_rows],'timing'),
                camera=field_stats(camera_rows,'camera'),counters=counts,
                memory_first=rows[0]['memory'],memory_last=rows[-1]['memory'],model_first=rows[0]['model_health'],model_last=rows[-1]['model_health'],
                dpu_first=rows[0]['dpu'],dpu_last=rows[-1]['dpu'],
                audio_processes_observed=sorted({p for r in rows for p in r['audio_process_pids']}),
                observer_cpu_ms=stats([r['observer']['cpu_ms'] for r in rows]),observer_wall_ms=stats([r['observer']['wall_ms'] for r in rows]),
                runtime_fault_count_max=max(r['state']['runtime_fault_count'] for r in rows if finite(r['state']['runtime_fault_count'])),
                renderer_fault_count_max=max((r['renderer']['worker_fault_count'] for r in rows if finite(r['renderer']['worker_fault_count'])),default=None),
                all_camera_fault_flags_clear=all(not any(v is True or (finite(v) and v>0) for v in r['camera_faults'].values()) for r in rows),
                all_main_visible_scheduling_active=all(r['state']['page']=='main' and r['avatar'].get('visible') is True and r['avatar'].get('frame_scheduling_active') is True for r in rows))

before,initial,health=preflight();original_page=before['state']['page']
assert original_page in ('main','vision','settings')
samples=[];error=None;restore_error=None
try:
    if original_page!='main':command_page('main');time.sleep(2)
    started=time.monotonic()
    for index in range(31):
        time.sleep(max(0.,started+2*index-time.monotonic()))
        samples.append(collect())
except Exception as exc:error=type(exc).__name__
finally:
    if original_page!='main':
        try:command_page(original_page);time.sleep(1)
        except Exception as exc:restore_error=type(exc).__name__

after=None;after_error=None
try:
    after,_,_=preflight()
    assert after['state']['page']==original_page
except Exception as exc:after_error=type(exc).__name__
result=dict(schema='aura-joint-idle-main-baseline-1',before=before,after=after,original_page=original_page,
            page_command_sent=original_page!='main',error=error,restore_error=restore_error,after_error=after_error,
            status='COMPLETE' if len(samples)==31 and not any((error,restore_error,after_error)) else 'INCOMPLETE',
            samples=samples,summary=summarize(samples) if len(samples)>1 else None,
            privacy=dict(raw_state_saved=False,text_saved=False,images_saved=False,audio_saved=False,identity_saved=False),
            scope=dict(duration_target_seconds=60,model_health_get_only=True,inference_requests_sent=0,
                       microphone_enabled=False,playback_started=False,camera_stopped=False,firmware_changed=False,
                       sources_or_thresholds_changed=False,animation_switched=False,target_fps_changed=False),
            caveats=['CPU process/thread percent uses 100% per one logical core; whole-board CPU uses 100% for all cores.',
                     'UI previous-callback timing is deduplicated by its callback sequence; stage timings belong to its containing publication and may describe the adjacent callback.',
                     'Avatar timing is deduplicated by native frames, renderer by renderer sequence, camera by observation frame id.',
                     'Pipeline stage and renderer profile quantiles remain reported rolling-window summaries, not individual new timing samples.',
                     'Native frames is the exposed presentation counter; distinct draw/swap event counters are unavailable.',
                     'GTK also owns business and paused audio logic; dedicated business/audio CPU cannot be inferred from shared process CPU.',
                     'No real dialogue was triggered; this baseline measures paused idle behavior, not user speech-to-first-audio latency.'])
print(json.dumps(result,allow_nan=False))
