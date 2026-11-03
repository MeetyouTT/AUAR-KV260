"""Explicit, source-bound <=10s face-zone trial with finite enlarged travel."""
import argparse,hashlib,http.client,json,os,signal,sys,time
from pathlib import Path
from types import SimpleNamespace


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','context','app-root','output','direction-evidence','human-evidence','zone-settings'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--confirmation',required=True)
    p.add_argument('--zone-authorization',required=True)
    p.add_argument('--duration',type=float,default=10.)
    a=p.parse_args()
    if (a.confirmation!='FACE_EDGE_OBSERVED_RANGE' or a.zone_authorization!='FACE_ZONE_FINITE_FASTER'
            or not 0<a.duration<=10):
        p.error('Explicit finite face-zone trial required')
    sys.path.insert(0,str(a.manifest.resolve().parent))
    from bench_identity_stop import validated_context
    root,manifest,boot=validated_context(a)
    direction=json.loads(a.direction_evidence.read_text());human=json.loads(a.human_evidence.read_text())
    assert direction['boot_id']==boot and direction['status']=='HUMAN_DIRECTION_CONFIRMED'
    assert direction['axis_camera_mirrored_control_polarity']==1
    assert human['boot_id']==boot
    sys.path.insert(0,str(a.app_root.resolve()));sys.path.insert(0,str(root))
    from face_edge_control import FaceEdgeController,EdgeConfig
    from face_zone import camera_zone
    from face_motion import run_session
    from vsrv_driver import PhysicalReference,VSRVDriver
    from vsrv_transport import NativeRegisters
    cancelled=[False]
    def cancel(*args):cancelled[0]=True
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=.25)
    zone_raw=a.zone_settings.read_bytes();zone=camera_zone(json.loads(zone_raw),boot)
    config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio'])
    report={'status':'STARTING','boot_id':boot,'range_us':[config.minimum_us,config.maximum_us],
            'consumer_manifest_sha256':hashlib.sha256((Path(__file__).parent/'deployment-manifest.json').read_bytes()).hexdigest(),
            'zone':zone,'zone_settings_sha256':hashlib.sha256(zone_raw).hexdigest(),
            'control':{'maximum_speed_us_s':config.maximum_speed_us_s,'filter_tau_ms':config.filter_tau_ms},
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
                assert config.minimum_us<=before['width_us']<=config.maximum_us and before['flags']==0 and before['lease_left_ms']==0
                reference=PhysicalReference(boot,before['width_us'],'finite-current-command',
                    'Current stopped command; direction observed; user requests faster finite zone follow; no mechanical zero',1,True,True)
                control=FaceEdgeController(boot,before['width_us'],polarity=1,config=config)
                report['result']=run_session(device,reference,control,packets(),
                    int.from_bytes(os.urandom(4),'big') or 1,before['epoch']+1,
                    duration_s=a.duration,cancelled=lambda:cancelled[0])
            report['status']='FINITE_FACE_EDGE_SESSION_STOPPED'
        except BaseException as e:
            report.update(status='FAILED_NO_RETRY',error=type(e).__name__+': '+str(e)[:200])
        finally:
            connection.close();json.dump(report,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
    result=report.get('result',{});stopped=result.get('stopped',{})
    if (report['status']=='FINITE_FACE_EDGE_SESSION_STOPPED' and stopped.get('flags')==0
            and stopped.get('lease_left_ms')==0):
        receipt=a.zone_settings.parent/'face-stopped-readback.json'
        data={'report':str(a.output),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()}
        tmp=receipt.with_name(receipt.name+'.'+str(os.getpid()))
        tmp.write_text(json.dumps(data)+'\n');os.chmod(tmp,0o600);os.replace(tmp,receipt)
    print(json.dumps({k:v for k,v in report.items() if k!='result'}))
    return 1 if report['status']=='FAILED_NO_RETRY' else 0


if __name__=='__main__':raise SystemExit(main())
