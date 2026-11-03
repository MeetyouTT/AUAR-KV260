"""Explicit continuous face-zone control; each motion segment is bounded."""
import argparse,hashlib,http.client,json,os,signal,sys,time
from pathlib import Path


def atomic(path,value):
    temp=path.with_name(path.name+'.'+str(os.getpid()))
    with temp.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush()
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
    assert direction['axis_camera_mirrored_control_polarity']==1 and human['boot_id']==boot
    sys.path.insert(0,str(a.app_root.resolve()));sys.path.insert(0,str(root));sys.path.insert(0,str(Path(__file__).parent))
    from continuous_face_control import EdgeConfig
    from continuous_session import ContinuousSession
    from face_zone import camera_zone
    from vsrv_driver import PhysicalReference,VSRVDriver
    from batch_driver import BatchDriver
    from batch_transport import BatchRegisters
    from trajectory import Trajectory
    from face_stream import FaceStream
    zone_raw=a.zone_settings.read_bytes();zone=camera_zone(json.loads(zone_raw),boot)
    zone.update(left_reference='face_box_edge_2px_touch',right_reference='face_center')
    config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio'])
    consumer=Path(__file__).parent/'deployment-manifest.json';consumer_sha=hashlib.sha256(consumer.read_bytes()).hexdigest()
    cancelled=[False]
    def cancel(*args):cancelled[0]=True
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(str(a.output),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    report=dict(status='CONTINUOUS_FACE_ZONE_STARTING',boot_id=boot,consumer_manifest_sha256=consumer_sha,
      range_us=[config.minimum_us,config.maximum_us],zone=zone,target_kind='face',identity_required=False,
      control_parameters={'median_window':config.median_window,'position_filter_ms':config.filter_tau_ms,
        'velocity_filter_ms':config.velocity_filter_tau_ms,'velocity_gain_us':config.velocity_gain_us,
        'minimum_speed_us_s':config.minimum_speed_us_s,'base_speed_us_s':config.base_speed_us_s,
        'maximum_speed_us_s':config.maximum_speed_us_s,'maximum_acceleration_us_s2':config.maximum_acceleration_us_s2,
        'maximum_step_us':config.maximum_step_us,'maximum_jerk_us_s3':config.maximum_jerk_us_s3,
        'maximum_correction_per_outside_episode_us':config.maximum_correction_us,
        'initial_in_zone_pwm':'off; engage only on actual face-edge request',
        'position_filter':'OneEuroFilter with large-jump admission gate','control_tick_ms':20,
        'trajectory_authority':'same image stamp; original deadline; maximum 4us per admitted image',
        'zone_hold':'unchanged current width; no normal PWM power cycle',
        'jerk_exceptions':['face/source/hardware STOP','immediate safe-zone freeze','finite source displacement budget'],
        'feedback_reference':'current image face position velocity; no face extrapolation'},
      zone_settings_sha256=hashlib.sha256(zone_raw).hexdigest(),mechanical_zero_calibrated=False,
      external_waveform_verified=False,physical_visual_follow_verified=False,result={})
    started=time.monotonic();session=None;last_publish=0.;reason='OPERATOR_STOP'
    def publish(force=False):
        nonlocal last_publish
        now=time.monotonic()
        if force or now-last_publish>=.5:
            if session is not None:report['result']=session.status()
            atomic(a.output,report);last_publish=now
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
                'Observed direction; current stopped command; user face zone; no mechanical zero',1,True,True)
            trajectory_library=Path(__file__).parent/'libaura_trajectory.so'
            trajectory_pin=next(x['sha256'] for x in batch_manifest['files'] if x['destination']==str(trajectory_library))
            trajectory=Trajectory(trajectory_library,trajectory_pin)
            session=ContinuousSession(device,boot,config,reference,trajectory=trajectory);report['before']=dict(session.current)
            report['status']='CONTINUOUS_FACE_ZONE_RUNNING';publish(True)
            stream=FaceStream()
            try:
                while not cancelled[0] and not session.fatal:
                    turn_started=time.monotonic()
                    if a.duration and time.monotonic()-started>=a.duration:reason='DURATION_ENDED';break
                    if hashlib.sha256(a.zone_settings.read_bytes()).hexdigest()!=report['zone_settings_sha256']:
                        reason='BOUNDARY_CHANGED';break
                    for kind,payload in stream.drain():
                        if kind=='packet':session.step(payload)
                        elif kind=='disconnect':session.disconnected()
                        else:session.fail('STREAM_PROTOCOL_'+str(payload))
                        if session.fatal:break
                    session.tick();publish()
                    remaining=.02-(time.monotonic()-turn_started)
                    if remaining>0:time.sleep(remaining)
                if session.fatal:reason=session.reason
            finally:
                stream.close()
                final=session.close();report['result']=final
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
