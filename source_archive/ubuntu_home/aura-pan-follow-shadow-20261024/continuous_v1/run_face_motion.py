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
    from vsrv_transport import NativeRegisters
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
        with NativeRegisters(root/'libvsrv.so',manifest['payload_files']['libvsrv.so'],boot,manifest['runtime_files']) as io:
            device=VSRVDriver(io,0x778d2512,boot)
            reference=lambda pulse:PhysicalReference(boot,pulse,'continuous-current-stopped-command',
                'Observed direction; current stopped command; user face zone; no mechanical zero',1,True,True)
            session=ContinuousSession(device,boot,config,reference);report['before']=dict(session.current)
            report['status']='CONTINUOUS_FACE_ZONE_RUNNING';publish(True)
            try:
                while not cancelled[0] and not session.fatal:
                    if a.duration and time.monotonic()-started>=a.duration:reason='DURATION_ENDED';break
                    if hashlib.sha256(a.zone_settings.read_bytes()).hexdigest()!=report['zone_settings_sha256']:
                        reason='BOUNDARY_CHANGED';break
                    connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=.25);window=time.monotonic()
                    try:
                        connection.request('GET','/v1/motion/face-stream?duration_ms=10000')
                        response=connection.getresponse()
                        if response.status!=200:raise OSError('Face stream temporarily unavailable')
                        while not cancelled[0] and not session.fatal:
                            if a.duration and time.monotonic()-started>=a.duration:reason='DURATION_ENDED';cancelled[0]=True;break
                            if hashlib.sha256(a.zone_settings.read_bytes()).hexdigest()!=report['zone_settings_sha256']:
                                reason='BOUNDARY_CHANGED';cancelled[0]=True;break
                            raw=response.readline(8193)
                            if not raw:
                                if time.monotonic()-window<9.5:session.disconnected()
                                break
                            if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Invalid face stream packet')
                            packet=json.loads(raw);session.step(packet);publish()
                    except (OSError,TimeoutError,http.client.HTTPException):
                        session.disconnected();publish()
                        if not cancelled[0]:time.sleep(.1)
                    finally:connection.close()
                if session.fatal:reason=session.reason
            finally:
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
