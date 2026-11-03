"""Explicit single 80us excursion and return in six seconds. Default is a plan."""
import argparse
import json
import os
from pathlib import Path
import sys
import time


def require(value,message):
    if not value:raise RuntimeError(message)


def run_roundtrip(io,device,origin,expected,events,clock=time.monotonic,sleep=time.sleep):
    require(type(origin) is int and 1400<=origin and origin+80<=1600,'80us roundtrip outside the existing range')
    before=device.status()
    require(before['flags']==0 and before['lease_left_ms']==0 and before['width_us']==origin,'Current stopped origin differs')
    require(all(before.get(k)==v for k,v in expected.items()),'Register context changed since the read-only check')
    require(before['epoch']<0xffffffff,'Epoch exhausted')
    session=int.from_bytes(os.urandom(4),'big') or 1
    epoch=before['epoch']+1
    finish=None
    try:
        device.stop()
        io.write(0x10,session);io.write(0x14,epoch);io.write(0x24,0x42494e44)
        state=device.status()
        require(state['flags']==8 and state['session']==session and state['epoch']==epoch and state['ack_seq']==0,'BIND not confirmed')
        io.write(0x3c,origin);io.write(0x24,0x52454621)
        state=device.status()
        require(state['flags']==12 and state['width_us']==origin and state['reference_us']==origin,'Reference differs from current command position')
        io.write(0x24,0x41524d21)
        require(device.status()['flags']==14,'ARM not confirmed')
        start=clock();seq=0
        for end_offset,target in ((1.,origin),(4.,origin+80),(6.,origin)):
            end=start+end_offset;count=0
            while clock()<end:
                submitted=clock()
                if end-submitted<=.025:
                    sleep(max(0.,end-submitted))
                    break
                state=device.status()
                require(state['session']==session and state['epoch']==epoch and state['ack_seq']==seq
                    and state['flags']&14==14 and state['reason']==0,'Lease/context lost; no automatic retry')
                seq+=1
                io.write(0x18,seq);io.write(0x1c,target);io.write(0x20,100)
                now=clock()
                require(0<=now-submitted<=.025 and now<end,'Late COMMIT refused')
                io.write(0x24,0x434d5421);state=device.status()
                require(state['active'] and state['reason']==0 and state['ack_seq']==seq
                    and state['target_us']==target and state['session']==session and state['epoch']==epoch,'Command ACK mismatch')
                events.append({'elapsed_ms':(clock()-start)*1000,'target_us':target,
                    'width_us':state['width_us'],'ack_seq':seq})
                count+=1;sleep(min(.04,max(0,end-clock())))
            state=device.status()
            require(count>=2 and state['active'] and state['width_us']==target,'Stage endpoint not reached')
        finish=device.finish()
        require(finish['flags']==0 and finish['lease_left_ms']==0,'Full-pulse finish not confirmed')
    finally:
        stopped=device.stop()
        require(stopped['flags']==0 and stopped['lease_left_ms']==0,'Final STOP not confirmed')
    return {'before':before,'finish':finish,'stopped':stopped,'origin_us':origin,
            'excursion_us':80,'commanded_sequence_us':[origin,origin+80,origin],
            'mechanical_reference_calibrated':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--confirmation')
    parser.add_argument('--manifest',type=Path);parser.add_argument('--manifest-sha256')
    parser.add_argument('--context',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--expected-state',type=Path)
    args=parser.parse_args()
    if not args.execute:
        print(json.dumps({'mode':'PLAN_ONLY','board_accessed':False,'excursion_us':80,
            'duration_s':6,'stages_seconds':[1,3,2],'returns_to_start':True,'automatic_repeat':False}));return
    require(args.confirmation=='OBSERVED_80US_RETURN_6S','Explicit 80us observation confirmation required')
    require(args.expected_state is not None,'Pinned current stopped registers required')
    sys.path.insert(0,str(args.manifest.resolve().parent))
    from bench_identity_stop import validated_context
    driver_root,manifest,boot=validated_context(args)
    expected=json.loads(args.expected_state.read_text())
    require(expected['boot_id']==boot,'Expected observation belongs to another boot')
    registers_expected=expected['registers']
    result={'boot_id':boot,'status':'STARTING','user_requested_excursion_us':80,
        'events':[],'automatic_following':False,'automatic_repeat':False,
        'external_waveform_verified':False,'physical_motion_verified':False,
        'mechanical_observation':'PENDING_USER'}
    with args.output.open('x') as output:
        try:
            sys.path.insert(0,str(driver_root))
            from vsrv_driver import VSRVDriver
            from vsrv_transport import NativeRegisters
            with NativeRegisters(driver_root/'libvsrv.so',manifest['payload_files']['libvsrv.so'],boot,manifest['runtime_files']) as io:
                device=VSRVDriver(io,0x10282601,boot)
                result['result']=run_roundtrip(io,device,registers_expected['width_us'],registers_expected,result['events'])
            result['status']='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
        except BaseException as error:
            result.update(status='FAILED_NO_AUTOMATIC_RETRY',error_type=type(error).__name__,error=str(error));raise
        finally:
            json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps({'status':result['status'],'report':str(args.output)}))


if __name__=='__main__':main()
