"""Explicit, source-bound <=10s face-edge trial in the already observed range."""
import argparse,hashlib,http.client,json,os,signal,sys,time
from pathlib import Path
from types import SimpleNamespace


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','context','app-root','output','direction-evidence','human-evidence'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--confirmation',required=True)
    p.add_argument('--duration',type=float,default=10.)
    a=p.parse_args()
    if a.confirmation!='FACE_EDGE_OBSERVED_RANGE' or not 0<a.duration<=10:
        p.error('Explicit finite observed-range trial required')
    sys.path.insert(0,str(a.manifest.resolve().parent))
    from bench_identity_stop import validated_context
    root,manifest,boot=validated_context(a)
    direction=json.loads(a.direction_evidence.read_text());human=json.loads(a.human_evidence.read_text())
    assert direction['boot_id']==boot and direction['status']=='HUMAN_DIRECTION_CONFIRMED'
    assert direction['axis_camera_mirrored_control_polarity']==1
    assert human['boot_id']==boot
    sys.path.insert(0,str(a.app_root.resolve()));sys.path.insert(0,str(root))
    from face_edge_control import FaceEdgeController
    from face_motion import run_session
    from vsrv_driver import PhysicalReference,VSRVDriver
    from vsrv_transport import NativeRegisters
    cancelled=[False]
    def cancel(*args):cancelled[0]=True
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=.25)
    report={'status':'STARTING','boot_id':boot,'range_us':[1425,1445],
            'target_kind':'face','identity_required':False,'external_waveform_verified':False,
            'physical_visual_follow_verified':False,'mechanical_zero_calibrated':False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(str(a.output),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as output:
        try:
            connection.request('GET','/v1/motion/face-stream?duration_ms='+str(round(a.duration*1000)))
            response=connection.getresponse();assert response.status==200
            def packets():
                while not cancelled[0]:
                    raw=response.readline(8193)
                    if not raw:return
                    if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Invalid face packet')
                    yield json.loads(raw)
            with NativeRegisters(root/'libvsrv.so',manifest['payload_files']['libvsrv.so'],boot,manifest['runtime_files']) as io:
                device=VSRVDriver(io,0x778d2512,boot);before=device.status()
                assert 1425<=before['width_us']<=1445 and before['flags']==0 and before['lease_left_ms']==0
                reference=PhysicalReference(boot,before['width_us'],'finite-current-command',
                    'Current boot user-observed 1425..1445us return and direction; no mechanical zero',1,True,True)
                control=FaceEdgeController(boot,before['width_us'],polarity=1)
                report['result']=run_session(device,reference,control,packets(),
                    int.from_bytes(os.urandom(4),'big') or 1,before['epoch']+1,
                    duration_s=a.duration,cancelled=lambda:cancelled[0])
            report['status']='FINITE_FACE_EDGE_SESSION_STOPPED'
        except BaseException as e:
            report.update(status='FAILED_NO_RETRY',error=type(e).__name__+': '+str(e)[:200])
        finally:
            connection.close();json.dump(report,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
    print(json.dumps({k:v for k,v in report.items() if k!='result'}))
    return 1 if report['status']=='FAILED_NO_RETRY' else 0


if __name__=='__main__':raise SystemExit(main())
