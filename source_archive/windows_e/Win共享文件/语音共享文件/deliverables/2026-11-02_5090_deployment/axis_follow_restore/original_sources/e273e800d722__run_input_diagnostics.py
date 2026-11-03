"""Read-only face-source timing: no actuator imports, locks, ARM or MMIO."""
import argparse,json,sys,time
from pathlib import Path
from face_stream import FaceStream
from face_zone import camera_zone
from continuous_face_control import EdgeConfig,FaceEdgeController
from input_timing import InputTiming


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--settings',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--duration',type=float,default=15.)
    a=p.parse_args()
    if not 1<=a.duration<=30:p.error('Use 1..30 seconds')
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    zone=camera_zone(json.loads(a.settings.read_text()),boot)
    config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio'],confirm_frames=2,
                      maximum_correction_us=None,maximum_speed_us_s=20.,minimum_edge_speed_us_s=6.,velocity_gain_us=12.)
    control=FaceEdgeController(boot,1450,config=config,polarity=1);timing=InputTiming()
    start=time.monotonic();reasons={};fatal=None;max_turn=0.
    with a.output.open('x') as output:
        stream=FaceStream()
        try:
            while time.monotonic()-start<a.duration:
                began=time.monotonic()
                for kind,packet in stream.drain():
                    if kind=='packet':
                        status=control.observe(packet,int(time.monotonic()*1000))
                        timing.observe(packet,dict(reason=status['reason'],control=status),int(time.monotonic()*1000))
                        reasons[status['reason']]=reasons.get(status['reason'],0)+1
                        if control.stopped:control=FaceEdgeController(boot,1450,config=config,polarity=1)
                    elif kind=='disconnect':control=FaceEdgeController(boot,1450,config=config,polarity=1)
                    else:fatal=str(packet)
                max_turn=max(max_turn,(time.monotonic()-began)*1000)
                if fatal:break
                time.sleep(.01)
        finally:stream.close()
        report=dict(scope='actual face packets, read-only software perception; no actuator imported',boot_id=boot,
            duration_s=round(time.monotonic()-start,3),input_timing=timing.snapshot(),reader_queue=stream.diagnostics(),
            decisions=reasons,maximum_turn_ms=round(max_turn,3),fatal=fatal,
            MMIO_opened=False,ARM_sent=False,COMMIT_sent=False,
            actuator_module_loaded=any(x in sys.modules for x in ('vsrv_driver','vsrv_transport','deadline_driver')))
        json.dump(report,output,separators=(',',':'));output.write('\n')
    print(json.dumps({'status':'INPUT_DIAGNOSTICS_DONE','output':str(a.output),'duration_s':report['duration_s'],'fatal':fatal}))


if __name__=='__main__':main()
