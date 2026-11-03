"""Live face observations, virtual device only. No physical driver is loaded."""
import argparse,collections,fcntl,hashlib,json,math,os,platform,signal,sys,time,urllib.request
from pathlib import Path
from types import SimpleNamespace


def get(port,path):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as stream:return json.load(stream)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--settings',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--duration',type=float,default=10.)
    parser.add_argument('--confirmation',required=True)
    a=parser.parse_args()
    if platform.machine()!='aarch64' or os.geteuid()!=0:
        parser.error('Board-only LIVE observation; no connection attempted on host')
    if a.confirmation!='SHADOW_ONLY' or not 0<a.duration<=30:
        parser.error('Finite 0..30s SHADOW_ONLY confirmation required')
    root=Path(__file__).resolve().parent;manifest=root/'manifest.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=a.manifest_sha256:raise RuntimeError('Shadow manifest changed')
    pins=json.loads(manifest.read_text())['files']
    for name,digest in pins.items():
        path=root/name;path.resolve().relative_to(root)
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError('Shadow file changed: '+name)
    sys.path.insert(0,str(root))
    from continuous_face_control import EdgeConfig
    from continuous_session import ContinuousSession
    from trajectory import Trajectory
    from shadow_device import ShadowDevice
    from face_zone import camera_zone
    from face_stream import FaceStream
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    raw_settings=a.settings.read_bytes();zone=camera_zone(json.loads(raw_settings),boot)
    initial=get(8783,'/api/state')['manual_pan']
    if initial.get('automatic_following') or initial.get('state') in ('MOVING','CONNECTING','STOPPING'):
        raise RuntimeError('Real controller must be idle before shadow')
    # Reserve the same lock physical writers require, without opening MMIO.
    # There is no hardware register object, physical ARM or COMMIT path here.
    with Path('/run/aura-vsrv.lock').open('a+') as exclusion:
        fcntl.flock(exclusion,fcntl.LOCK_EX|fcntl.LOCK_NB)
        device=ShadowDevice(1500)
        trajectory=Trajectory(root/'libaura_trajectory.so',pins['libaura_trajectory.so'])
        session=ContinuousSession(device,boot,EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio']),
            lambda pulse:SimpleNamespace(reference_us=pulse),trajectory=trajectory)
        stream=None;cancelled=[False];states=collections.Counter();reasons=collections.Counter();ages=[];packets=0
        packet_contracts=collections.deque(maxlen=12)
        signal.signal(signal.SIGTERM,lambda *_:cancelled.__setitem__(0,True))
        signal.signal(signal.SIGINT,lambda *_:cancelled.__setitem__(0,True))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as output:
            started=time.monotonic();status='SHADOW_RUNNING';error=None
            try:
                stream=FaceStream()
                while not cancelled[0] and not session.fatal and time.monotonic()-started<a.duration:
                    began=time.monotonic()
                    if a.settings.read_bytes()!=raw_settings:raise RuntimeError('Boundary changed during shadow')
                    for kind,packet in stream.drain():
                        if kind=='packet':
                            packets+=1;states[packet.get('state','INVALID')]+=1
                            packet_contracts.append(dict(received_mono_ms=int(time.monotonic()*1000),
                                **{k:packet.get(k) for k in ('state','source_kind','target_kind','source_frame_id',
                                    'source_mono_ms','face_detection_mono_ms','evaluated_mono_ms','deadline_mono_ms')}))
                            tracking=packet.get('face_tracking') or {};reasons[tracking.get('reason','NONE')]+=1
                            if packet.get('state')=='READY' and type(packet.get('source_mono_ms')) is int:
                                ages.append(round(time.monotonic()*1000)-packet['source_mono_ms'])
                            session.step(packet)
                        elif kind=='disconnect':session.disconnected()
                        else:session.fail('STREAM_PROTOCOL_'+str(packet))
                        if session.fatal:break
                    session.tick()
                    delay=.02-(time.monotonic()-began)
                    if delay>0:time.sleep(delay)
                status='SHADOW_FAULT' if session.fatal else 'SHADOW_FINISHED'
            except Exception as exception:
                status='SHADOW_FAILED';error=type(exception).__name__+': '+str(exception)[:240]
            finally:
                if stream is not None:stream.close()
                before_close=session.status();result=session.close()
                forbidden=[name for name in sys.modules if name in ('vsrv_driver','vsrv_transport','batch_transport','pulse_driver')]
                try:final=get(8783,'/api/state')['manual_pan']
                except Exception as exception:
                    final={};status='SHADOW_FAILED';error='Final UI read failed: '+type(exception).__name__
                report=dict(status=status,error=error,scope='actual face images, command math and virtual device only',
                    board_boot_id=boot,manifest_sha256=a.manifest_sha256,zone=zone,duration_s=round(time.monotonic()-started,3),
                    virtual_reference_us=1500,reference_is_physical_calibration=False,packets=packets,
                    packet_states=dict(states),tracking_reasons=dict(reasons),
                    source_age_ms=dict(count=len(ages),minimum=min(ages),maximum=max(ages)) if ages else dict(count=0),
                    result=result,simulated_arms=device.arms,simulated_commits=device.commits,
                    terminal_reason_before_close=before_close['reason'],packet_contracts=list(packet_contracts),
                    simulated_commands=device.commands,physical_driver_modules=forbidden,
                    real_manual_before={k:initial.get(k) for k in ('state','automatic_following','readback')},
                    real_manual_after={k:final.get(k) for k in ('state','automatic_following','readback')},
                    MMIO_opened=False,physical_ARM=0,physical_COMMIT=0,physical_motion_verified=False)
                if forbidden:report.update(status='SHADOW_FAILED',error='Physical module unexpectedly imported')
                if final.get('automatic_following'):
                    report.update(status='SHADOW_FAILED',error='External automatic controller became active')
                json.dump(report,output,indent=2);output.write('\n')
    print(json.dumps({k:report[k] for k in ('status','duration_s','packets','simulated_arms','simulated_commits','MMIO_opened','physical_ARM','physical_COMMIT')}))
    return int(report['status'] not in ('SHADOW_FINISHED',))


if __name__=='__main__':raise SystemExit(main())
