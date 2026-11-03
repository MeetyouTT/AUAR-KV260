"""Explicit continuous face-zone control; each motion segment is bounded."""
import argparse,collections,hashlib,http.client,json,os,signal,sys,time
from pathlib import Path


def atomic(path,value):
    temp=path.with_name(path.name+'.'+str(os.getpid()))
    raw=json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n'
    with temp.open('x') as f:f.write(raw);f.flush()
    os.chmod(temp,0o600);os.replace(temp,path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','context','app-root','output','direction-evidence','human-evidence','zone-settings'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True);p.add_argument('--confirmation',required=True)
    p.add_argument('--duration',type=float,default=0.)
    a=p.parse_args()
    if a.confirmation!='FACE_ZONE_CONTINUOUS' or not 0<=a.duration<=300:
        p.error('Explicit continuous mode or finite 0..300 second observation required')
    sys.path.insert(0,str(a.manifest.resolve().parent))
    from bench_identity_stop import validated_context
    root,manifest,boot=validated_context(a)
    direction=json.loads(a.direction_evidence.read_text());human=json.loads(a.human_evidence.read_text())
    assert direction['boot_id']==boot and direction['status']=='HUMAN_DIRECTION_CONFIRMED'
    polarity=direction['axis_camera_mirrored_control_polarity']
    assert type(polarity) is int and polarity in (-1,1) and human['boot_id']==boot
    sys.path.insert(0,str(a.app_root.resolve()));sys.path.insert(0,str(root));sys.path.insert(0,str(Path(__file__).parent))
    from continuous_face_control import EdgeConfig
    from continuous_session import ContinuousSession
    from face_zone import camera_zone
    from vsrv_driver import PhysicalReference,VSRVDriver
    from deadline_driver import DeadlineDriver as BatchDriver
    from batch_transport import BatchRegisters
    from trajectory import Trajectory
    from face_stream import FaceStream
    from live_report import bounded_live_report
    from input_timing import InputTiming
    zone_raw=a.zone_settings.read_bytes();zone=camera_zone(json.loads(zone_raw),boot)
    zone.update(left_reference='face_box_left_edge_user_line',right_reference='face_center')
    config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio'],maximum_correction_us=None,confirm_frames=2,
                      maximum_speed_us_s=20.,velocity_gain_us=12.,prearm_confirmed_face=True)
    consumer=Path(__file__).parent/'deployment-manifest.json';consumer_sha=hashlib.sha256(consumer.read_bytes()).hexdigest()
    cancelled=[False]
    def cancel(*args):cancelled[0]=True
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(str(a.output),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    report=dict(status='CONTINUOUS_FACE_ZONE_STARTING',boot_id=boot,consumer_manifest_sha256=consumer_sha,
      range_us=[config.minimum_us,config.maximum_us],zone=zone,target_kind='face',identity_required=False,
      control_polarity=polarity,direction_evidence_sha256=hashlib.sha256(a.direction_evidence.read_bytes()).hexdigest(),
      control_parameters={'prearm_confirmed_face':config.prearm_confirmed_face,'confirm_frames':config.confirm_frames,
        'effective_one_euro':dict(min_cutoff_hz=config.one_euro_min_cutoff_hz,beta=config.one_euro_beta,
            derivative_cutoff_hz=config.one_euro_derivative_cutoff_hz,width_beta=config.one_euro_width_beta),
        'legacy_compatibility_fields':dict(filter_tau_ms=config.filter_tau_ms,velocity_filter_tau_ms=config.velocity_filter_tau_ms,
            median_window=config.median_window,used_for_control=False),'velocity_gain_us':config.velocity_gain_us,
        'minimum_speed_us_s':config.minimum_speed_us_s,'base_speed_us_s':config.base_speed_us_s,
        'maximum_speed_us_s':config.maximum_speed_us_s,'maximum_acceleration_us_s2':config.maximum_acceleration_us_s2,
        'maximum_step_us':config.maximum_step_us,'maximum_jerk_us_s3':config.maximum_jerk_us_s3,
        'maximum_correction_per_outside_episode_us':config.maximum_correction_us,
        'correction_rearm_stable_inside_ms':250,'correction_rearm_minimum_distinct_images':3,
        'authority_deadline':'minimum of image source plus 250ms and detection anchor plus 500ms',
        'fresh_image_low_lease_renewal':'unchanged target immediately when old lease <=40ms; new source required',
        'confirmed_edge_speed_floor_us_s':2.,
        'initial_in_zone_pwm':'off; prepare ARM on confirmed face; no COMMIT until actual face-edge displacement',
        'initial_equal_target_pwm':'off until a distinct trajectory target is ready',
        'visual_loss_stop':'PL QUIESCE completes current pulse only; original hardware expiry remains',
        'position_filter':'OneEuroFilter with large-jump admission gate','control_tick_ms':20,
        'trajectory_authority':'same image stamp; original image/anchor deadline; maximum 4us per admitted image',
        'zone_hold':'unchanged current width; no normal PWM power cycle',
        'jerk_exceptions':['face/source/hardware STOP','immediate safe-zone freeze','finite source displacement budget'],
        'feedback_reference':'current image face position velocity; no face extrapolation'},
      zone_settings_sha256=hashlib.sha256(zone_raw).hexdigest(),mechanical_zero_calibrated=False,
      external_waveform_verified=False,physical_visual_follow_verified=False,result={})
    started=time.monotonic();session=None;last_publish=0.;reason='OPERATOR_STOP'
    packet_states=collections.Counter();raw_positions=collections.Counter();decisions=collections.Counter()
    observation_trace=collections.deque(maxlen=512);last_observation=None
    source_timing=InputTiming();stream=None;device=None
    timing=dict(publish_count=0,last_publish_ms=0.,maximum_publish_ms=0.,
                maximum_control_turn_ms=0.,control_turns_over_100ms=0,maximum_packet_step_ms=0.,maximum_tick_ms=0.)
    def publish(force=False):
        nonlocal last_publish
        now=time.monotonic()
        if force or now-last_publish>=.5:
            began=time.monotonic()
            result=session.status() if session is not None else {}
            summary=dict(packet_states=dict(packet_states),raw_positions=dict(raw_positions),decisions=dict(decisions))
            report['input_timing']=source_timing.snapshot()
            if stream is not None:report['reader_queue']=stream.diagnostics()
            if device is not None:report['submission_timing']=dict(delayed_submissions=device.delayed_submissions,
                last_delayed_submission=device.last_delayed_submission,
                absolute_source_deadline_guaranteed_by_hardware=False)
            atomic(a.output,bounded_live_report(report,result,observation_trace,summary,timing))
            elapsed=(time.monotonic()-began)*1000
            timing.update(publish_count=timing['publish_count']+1,last_publish_ms=round(elapsed,3),
                          maximum_publish_ms=max(timing['maximum_publish_ms'],round(elapsed,3)))
            last_publish=time.monotonic()
    try:
        batch_library=Path(__file__).parent/'libvsrv_batch.so'
        batch_manifest=json.loads(consumer.read_text())
        batch_pin=next(x['sha256'] for x in batch_manifest['files'] if x['destination']==str(batch_library))
        with BatchRegisters(batch_library,batch_pin,boot,manifest['runtime_files']) as io:
            device=BatchDriver(io,0x778d2512,boot)
            # Same owner, registers and checks. Only read grouping differs;
            # no ARM/COMMIT is issued during this finite latency comparison.
            legacy=VSRVDriver(io,0x778d2512,boot)
            measurements={'per_word_status_ms':[],'batch_status_ms':[]}
            for _ in range(3):
                for name,reader in [('per_word_status_ms',legacy),('batch_status_ms',device)]:
                    began=time.monotonic();checked=reader.status()
                    measurements[name].append(round((time.monotonic()-began)*1000,3))
                    assert checked['flags']==0 and checked['lease_left_ms']==0
            report['read_only_status_benchmark_ms']=measurements
            reference=lambda pulse:PhysicalReference(boot,pulse,'continuous-current-stopped-command',
                'Observed direction; current stopped command; user face zone; no mechanical zero',polarity,True,True)
            trajectory_library=Path(__file__).parent/'libaura_trajectory.so'
            trajectory_pin=next(x['sha256'] for x in batch_manifest['files'] if x['destination']==str(trajectory_library))
            trajectory=Trajectory(trajectory_library,trajectory_pin)
            session=ContinuousSession(device,boot,config,reference,trajectory=trajectory,polarity=polarity);report['before']=dict(session.current)
            report['status']='CONTINUOUS_FACE_ZONE_RUNNING';publish(True)
            stream=FaceStream()
            try:
                while not cancelled[0] and not session.fatal:
                    turn_started=time.monotonic()
                    if a.duration and time.monotonic()-started>=a.duration:reason='DURATION_ENDED';break
                    if hashlib.sha256(a.zone_settings.read_bytes()).hexdigest()!=report['zone_settings_sha256']:
                        reason='BOUNDARY_CHANGED';break
                    for kind,payload in stream.drain():
                        if kind=='packet':
                            packet_states[payload.get('state','INVALID')]+=1
                            began_step=time.monotonic();session.step(payload);decision=session.status()
                            timing['maximum_packet_step_ms']=max(timing['maximum_packet_step_ms'],round((time.monotonic()-began_step)*1000,3))
                            source_timing.observe(payload,decision,int(time.monotonic()*1000))
                            decisions[decision['reason']]+=1
                            box=(payload.get('target') or {}).get('box');width=payload.get('frame_width')
                            center=(box[0]+box[2]/2)/width if box and width else None
                            position=('LEFT' if box[0]/width<=zone['left_ratio'] else 'RIGHT' if center>zone['right_ratio'] else 'INSIDE') if center is not None else 'UNCONFIRMED'
                            raw_positions[position]+=1
                            key=(payload.get('source_frame_id'),payload.get('source_mono_ms'),payload.get('state'),decision['reason'])
                            if key!=last_observation:
                                now_ms=int(time.monotonic()*1000);source=payload.get('source_mono_ms');anchor=payload.get('face_detection_mono_ms')
                                observation_trace.append(dict(received_mono_ms=now_ms,state=payload.get('state'),position=position,face_center_ratio=center,
                                    face_left_ratio=box[0]/width if box and width else None,
                                    source_frame_id=payload.get('source_frame_id'),source_age_ms=now_ms-source if type(source) is int else None,
                                    detection_age_ms=now_ms-anchor if type(anchor) is int else None,decision=decision['reason'],
                                    confirmed_sources=decision['control']['confirmed_sources'],tracking_reason=(payload.get('face_tracking') or {}).get('reason')))
                                last_observation=key
                        elif kind=='disconnect':session.disconnected()
                        else:session.fail('STREAM_PROTOCOL_'+str(payload))
                        if session.fatal:break
                    began_tick=time.monotonic();session.tick()
                    timing['maximum_tick_ms']=max(timing['maximum_tick_ms'],round((time.monotonic()-began_tick)*1000,3))
                    publish()
                    turn_ms=(time.monotonic()-turn_started)*1000
                    timing['maximum_control_turn_ms']=max(timing['maximum_control_turn_ms'],round(turn_ms,3))
                    if turn_ms>100:timing['control_turns_over_100ms']+=1
                    remaining=.02-turn_ms/1000
                    if remaining>0:time.sleep(remaining)
                if session.fatal:reason=session.reason
            finally:
                stream.close()
                report['pre_stop_result']=session.status()
                final=session.close();report['result']=final
                report['input_summary']=dict(packet_states=dict(packet_states),raw_positions=dict(raw_positions),decisions=dict(decisions))
                report['observation_trace']=list(observation_trace)
                report['telemetry']=dict(timing)
                report['input_timing']=source_timing.snapshot()
                report['reader_queue']=stream.diagnostics()
                report['result'].update(reason=reason,stopped=final['readback'])
                report['status']='CONTINUOUS_FACE_ZONE_STOPPED';atomic(a.output,report)
    except BaseException as exc:
        report.update(status='CONTINUOUS_FACE_ZONE_FAILED',error=type(exc).__name__+': '+str(exc)[:250])
        atomic(a.output,report)
    result=report.get('result',{});stopped=result.get('stopped',{})
    if report['status']=='CONTINUOUS_FACE_ZONE_STOPPED' and stopped.get('flags')==0 and stopped.get('lease_left_ms')==0:
        receipt=a.zone_settings.parent/'face-stopped-readback.json'
        atomic(receipt,{'report':str(a.output),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()})
    print(json.dumps({k:report.get(k) for k in ('status','error','boot_id','range_us')}))
    return int(report['status']=='CONTINUOUS_FACE_ZONE_FAILED')


if __name__=='__main__':raise SystemExit(main())
