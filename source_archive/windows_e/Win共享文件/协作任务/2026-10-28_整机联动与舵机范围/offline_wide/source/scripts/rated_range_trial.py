"""Bounded attended nominal travel check; not a visual-source command stream."""
import argparse,hashlib,json,os,secrets,signal,sys,time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['manifest','context','reference','controller','output','authorization']:
        parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--confirmation',required=True)
    args=parser.parse_args()
    if args.confirmation!='ATTENDED_RATED_180':raise ValueError('Explicit rated-range trial required')
    sys.path.insert(0,str(args.manifest.parent))
    from bench_identity_stop import validated_context
    root,manifest,boot=validated_context(args)
    auth=json.loads(args.authorization.read_text());ref=json.loads(args.reference.read_text())
    assert auth['boot_id']==boot and auth['bounds_us']==[500,2500] and auth['clearance_confirmed'] is True
    assert auth['requested_angles_deg']==[-90,90] and ref['boot_id']==boot
    expected=ref['stopped_readback'];assert expected['flags']==0 and expected['lease_left_ms']==0
    sys.path.insert(0,str(root));sys.path.insert(0,str(args.controller))
    from vsrv_driver import PhysicalReference
    from batch_transport import BatchRegisters
    from batch_driver import BatchDriver
    cancelled=[False]
    def cancel(*unused):cancelled[0]=True
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    report={'status':'STARTING','boot_id':boot,'source':'EXPLICIT_ATTENDED_NOMINAL_RANGE_SEQUENCE','sequence_us':[1500,500,1500,2500,1500],
            'nominal_angles_deg':[0,-90,0,90,0],'physical_angles_measured':False,'commands':0,'phases':[],'error':None,'stop_confirmed':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f)
    def save():
        p=args.output.with_name(args.output.name+'.tmp');p.write_text(json.dumps(report,indent=2)+'\n');os.replace(p,args.output)
    start=time.monotonic();device=None
    try:
        with BatchRegisters(root/'libvsrv.so',manifest['payload_files']['libvsrv.so'],boot,manifest['runtime_files']) as io:
            device=BatchDriver(io,0x10282601,boot);before=device.status();assert before==expected
            reference=PhysicalReference(boot,before['width_us'],'same-boot-reconfiguration-continuity',
                'Stopped pre-reconfiguration command retained; user confirms unchanged setup; no encoder measurement',1,True,True)
            device.confirm_and_arm(reference,secrets.randbelow(0xfffffffe)+1,before['epoch']+1,authorized=True)
            report.update(status='RUNNING',before=before);save()
            try:
                for index,target in enumerate(report['sequence_us']):
                    phase_start=time.monotonic();initial=device.status()['width_us'];arrived=None;hold=.7
                    deadline=phase_start+abs(target-initial)/200.+2.0
                    phase={'index':index,'target_us':target,'initial_us':initial,'commands':0,'start_mono_s':phase_start}
                    report['phases'].append(phase)
                    while True:
                        if cancelled[0] or time.monotonic()-start>35:raise RuntimeError('Operator stop or total deadline')
                        if time.monotonic()>deadline:raise RuntimeError('Rated phase did not arrive in budget')
                        stamp=time.monotonic()
                        result=device.submit(target,stamp,freshness_s=.12,margin_s=.02)
                        if result['outcome']!='ACCEPTED':raise RuntimeError('Command rejected: '+str(result.get('reason')))
                        now=time.monotonic();rb=device.status();phase['commands']+=1;report['commands']+=1
                        phase['last_readback']=rb
                        if rb['width_us']==target:
                            if arrived is None:arrived=now;phase['arrived_mono_s']=now
                            if now-arrived>=hold:break
                        else:arrived=None
                        if phase['commands']%10==0:save()
                        time.sleep(.020)
                    phase['finished_mono_s']=time.monotonic();save()
                report['status']='NOMINAL_ENDPOINT_COMMANDS_COMPLETED_PENDING_HUMAN'
                device.finish()
            finally:
                stopped=device.stop();report['stopped_readback']=stopped
                report['stop_confirmed']=stopped['flags']==0 and stopped['lease_left_ms']==0
    except BaseException as error:
        report['status']='FAILED_STOPPED_OR_REQUIRES_CHECK';report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        report['elapsed_s']=time.monotonic()-start;save()
    assert report['stop_confirmed'] and report['stopped_readback']['width_us']==1500
    print(json.dumps({'status':report['status'],'commands':report['commands'],'elapsed_s':report['elapsed_s'],'stopped_readback':report['stopped_readback'],'physical_angles_measured':False}))

if __name__=='__main__':main()
