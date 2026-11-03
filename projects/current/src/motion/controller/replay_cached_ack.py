"""Compare frozen drivers with a 20ms PWM latch and independent lease clock."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root',type=Path,default=HERE.parent/'continuous_v10r14_candidate')
    parser.add_argument('--candidate-root',type=Path,default=HERE)
    parser.add_argument('--driver-root',type=Path,default=HERE.parent/'offline_host_driver')
    args=parser.parse_args()
    sys.path[:0]=[str(args.candidate_root),str(args.driver_root),str(HERE)]
    fixture=load('cached_ack_fixture',HERE/'test_cached_ack_freshness.py')
    old=load('cached_ack_baseline',args.baseline_root/'deadline_driver.py').DeadlineDriver
    new=load('cached_ack_candidate',args.candidate_root/'deadline_driver.py').DeadlineDriver
    rows=[]
    cases=[('cached_pause_25ms',dict(cached_pause=.025)),('cached_pause_80ms',dict(cached_pause=.08)),
           ('native_delay_25ms',dict(native_pause=.025)),('native_delay_300ms',dict(native_pause=.3)),
           ('true_expiry',dict(cached_pause=.3)),('fresh_read_pause_30ms',dict(cached_pause=.025,fresh_pause=.03)),
           ('fresh_read_short_pause',dict(cached_pause=.025,fresh_pause=.005)),('ordinary',{})]
    for name,settings in cases:
        results=[]
        for driver in (old,new):
            device,io,now,status=fixture.rig(driver,**settings)
            result=device.submit(1470,10.,minimum_lease_ms=23)
            final=status()
            results.append(dict(outcome=result['outcome'],reason=result.get('reason'),
                actual_hardware_expiry=io.expiry,original_source_deadline=10.25,
                commits=len(io.commits),stops=io.stops,final_readback=final,pulse_outputs=io.pulses,
                readback_rechecks=getattr(device,'readback_rechecks',0),
                false_alarms_avoided=getattr(device,'readback_false_alarms_avoided',0),
                physical_verified=False))
        before,after=results
        if name in ('cached_pause_25ms','cached_pause_80ms','fresh_read_short_pause'):
            assert before['outcome']=='REJECTED' and after['outcome']=='ACCEPTED'
            assert before['actual_hardware_expiry']==after['actual_hardware_expiry']<10.25
            assert after['commits']==1 and after['stops']==0
        elif name=='ordinary':assert before['outcome']==after['outcome']=='ACCEPTED'
        else:assert before['outcome']==after['outcome']=='REJECTED'
        rows.append(dict(scenario=name,baseline=before,candidate=after))
    print(json.dumps(dict(status='CACHED_ACK_PAIRED_REPLAY_PASS',cases=rows,physical_verified=False,
        scope='software independent hardware lease and 20ms PWM model; no MMIO, camera, DPU or board access'),indent=2))


if __name__=='__main__':main()
