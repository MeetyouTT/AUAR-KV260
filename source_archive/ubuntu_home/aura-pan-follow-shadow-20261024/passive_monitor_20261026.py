"""Bounded read-only liveness log. No actuator, service changes, or recovery."""
import argparse,json,os,subprocess,time,urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=7200)
    parser.add_argument('--camera-pid',type=int,required=True)
    parser.add_argument('--gui-pid',type=int,required=True)
    args=parser.parse_args()
    assert 5<=args.seconds<=7200
    args.output.mkdir(mode=0o700)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(port,path):
        with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as response:
            return json.load(response)
    began=time.monotonic();count=errors=0;last_journal=-60.;reason='DURATION_ENDED'
    status=dict(status='RUNNING',pid=os.getpid(),expected_camera_pid=args.camera_pid,
        expected_gui_pid=args.gui_pid,requested_seconds=args.seconds,samples=0,
        motor_commands=0,automatic_recovery=False,scope='HTTP metadata and bounded kernel counts; no images, identity labels or audio')
    def save():
        status.update(elapsed_s=round(time.monotonic()-began,3),samples=count)
        tmp=args.output/'status.json.tmp'
        tmp.write_text(json.dumps(status,indent=2)+'\n');tmp.replace(args.output/'status.json')
    save()
    try:
        with (args.output/'samples.jsonl').open('x',buffering=1) as log:
            while time.monotonic()-began<args.seconds:
                turn=time.monotonic();row=dict(elapsed_s=round(turn-began,3),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                try:
                    health=get(8790,'/health');ui=get(8783,'/api/state')
                    obs=get(8790,'/v1/motion/face/observation');manual=ui['manual_pan']
                    schedule=health['dpu_schedule'];rb=manual.get('readback') or {}
                    row.update(camera_pid=health['pid'],identity_ready=health['identity']['ready'],
                        owner_fenced=schedule['owner_fenced'],primary_overruns=schedule['primary_period_overruns'],
                        optional_overruns={k:schedule['optional'][k]['overruns'] for k in ('yunet','sface')},
                        face_state=obs['state'],phase=ui.get('phase'),audio_state=ui.get('audio_output_state'),
                        automatic_following=manual['automatic_following'],manual_state=manual['state'],
                        pulse_us=rb.get('width_us'),flags=rb.get('flags'),lease_ms=rb.get('lease_left_ms'),
                        loadavg=[round(v,2) for v in os.getloadavg()])
                    gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
                    row['gui_pid']=gui;errors=0
                    if health['pid']!=args.camera_pid or gui!=args.gui_pid:
                        reason='RUNTIME_OWNER_CHANGED';log.write(json.dumps(row)+'\n');count+=1;break
                except Exception as exc:
                    errors+=1;row['error']=type(exc).__name__+': '+str(exc)[:160]
                if turn-began-last_journal>=60:
                    job=subprocess.run(['journalctl','-k','--since','60 seconds ago','-n','200','--no-pager','-o','cat'],
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=3)
                    lines=job.stdout.splitlines()
                    row.update(kernel_window_s=60,kernel_lines_sampled=len(lines),kernel_sample_capped=len(lines)>=200,
                        xhci_buffer_warnings=sum("couldn't access mem fast enough" in line for line in lines))
                    last_journal=turn-began
                log.write(json.dumps(row,separators=(',',':'))+'\n');count+=1
                status['latest']=row;save()
                if errors>=3:reason='THREE_CONSECUTIVE_READ_ERRORS';break
                time.sleep(max(0.,min(5-(time.monotonic()-turn),args.seconds-(time.monotonic()-began))))
    except BaseException as exc:
        reason='MONITOR_ERROR';status['error']=type(exc).__name__+': '+str(exc)[:160]
    finally:
        status.update(status='ENDED',reason=reason);save()


if __name__=='__main__':main()
