"""Bounded /proc ALSA pointer and kernel-warning counts; no device opens.

This does not attach to the business worker, query its GStreamer objects,
change any service, replay PCM, acknowledge faults, or attempt recovery.
"""
import argparse
import datetime
import json
import re
import subprocess
import time
from pathlib import Path


def read(path):
    try:return path.read_text()
    except OSError as exc:return 'READ_ERROR '+type(exc).__name__+': '+str(exc)[:100]


def fields(raw):
    result={}
    for line in raw.splitlines():
        if ':' not in line:continue
        key,value=(part.strip() for part in line.split(':',1))
        if key in ('state','owner_pid','delay','avail','avail_max','hw_ptr','appl_ptr','trigger_time'):
            result[key]=int(value) if re.fullmatch(r'-?\d+',value) else value
    if not result:result['raw_state']=raw.strip()[:100]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcm-root',type=Path,default=Path('/proc/asound/card1/pcm0p/sub0'))
    parser.add_argument('--seconds',type=float,default=3.)
    args=parser.parse_args()
    assert .5<=args.seconds<=5
    root=args.pcm_root.resolve(strict=True)
    assert str(root).startswith('/proc/asound/')
    hw=read(root/'hw_params');sw=read(root/'sw_params')
    started=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc)
    rows=[]
    while True:
        rows.append(dict(elapsed_s=round(time.monotonic()-started,4),
                         **fields(read(root/'status'))))
        left=args.seconds-(time.monotonic()-started)
        if left<=0:break
        time.sleep(min(.25,left))
    first,last=rows[0],rows[-1]
    span=last['elapsed_s']-first['elapsed_s']
    delta={}
    for key in ('hw_ptr','appl_ptr'):
        if type(first.get(key)) is int and type(last.get(key)) is int:
            value=last[key]-first[key]
            delta[key+'_raw_delta']=value
            if value>=0 and span>0:delta[key+'_frames_per_s']=round(value/span,2)
    journal=dict(available=False)
    try:
        job=subprocess.run(['journalctl','-k','--since',utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            '-n','300','--no-pager','-o','json'],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=2)
        entries=[json.loads(line) for line in job.stdout.splitlines() if line.startswith('{')]
        needle="HC couldn't access mem fast enough for slot 4 ep 3"
        journal=dict(available=job.returncode==0,since_utc=utc.isoformat(),
                     sampled_entries=len(entries),sample_capped=len(entries)>=300,
                     slot4_ep3_warning_count=sum(needle in str(e.get('MESSAGE','')) for e in entries))
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        journal['error']=type(exc).__name__+': '+str(exc)[:100]
    print(json.dumps(dict(status='READONLY_PCM_PROGRESS',pcm_root=str(root),
        duration_s=round(time.monotonic()-started,3),hw_params=hw,sw_params=sw,
        samples=rows,raw_pointer_delta=delta,kernel=journal,
        internal_appsrc_queue_observed=False,device_audio_opened=False,service_changes=0,
        scope='numeric ALSA status and bounded kernel counts only; pointer progress is not USB transport or acoustic acceptance'),indent=2))


if __name__=='__main__':main()
