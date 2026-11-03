"""Face edge controller evaluation. Reads anonymous faces and never opens IO."""
import argparse,collections,dataclasses,http.client,json,os,statistics,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-root',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--duration',type=float,default=10.)
    a=p.parse_args()
    if os.uname().machine!='aarch64' or not 0<a.duration<=10 or not a.app_root.is_dir():
        p.error('KV260 app root and 0<duration<=10 required')
    sys.path.insert(0,str(a.app_root.resolve()))
    from face_edge_control import EdgeConfig,FaceEdgeController
    cfg=json.loads(a.config.read_text())
    assert cfg['mode']=='FACE_EDGE_SHADOW' and cfg['physical_actuation_enabled'] is False
    assert set(cfg['controller'])=={f.name for f in dataclasses.fields(EdgeConfig)}
    control=FaceEdgeController(Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cfg['reference_command_us'],polarity=cfg['polarity'],config=EdgeConfig(**cfg['controller']))
    output=a.output.resolve();output.parent.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(output.parent,0o700)
    fd=os.open(str(output),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    counts=collections.Counter();modes=collections.Counter();seen=set();ages=[];pulses=[];speeds=[];error=None;start=time.monotonic()
    c=http.client.HTTPConnection('127.0.0.1',8790,timeout=.3)
    try:
        with os.fdopen(fd,'w') as log:
            c.request('GET','/v1/motion/face-stream?duration_ms='+str(round(a.duration*1000)))
            response=c.getresponse()
            if response.status!=200:raise RuntimeError('Face source HTTP '+str(response.status))
            while time.monotonic()-start<a.duration:
                raw=response.readline(8193)
                if not raw:break
                if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Unbounded face packet')
                packet=json.loads(raw);now=int(time.monotonic()*1000);counts[str(packet.get('state'))]+=1
                if packet.get('state')=='READY':
                    seen.add((packet['camera_epoch'],packet['source_frame_id']));ages.append(now-packet['source_mono_ms'])
                status=control.observe(packet,now);modes[status['state']]+=1
                if status['new_source']:pulses.append(status['pulse_us']);speeds.append(abs(status['velocity_us_s']))
                log.write(json.dumps(status,separators=(',',':'))+'\n');log.flush()
                if control.stopped:break
    except Exception as e:error=type(e).__name__+': '+str(e)[:100]
    finally:
        c.close()
        if not control.stopped:control.stop('INPUT_ERROR' if error else 'TIME_LIMIT')
    elapsed=time.monotonic()-start
    result={'status':'ERROR' if error else 'FACE_EDGE_SHADOW_FINISHED','error':error,'elapsed_s':round(elapsed,3),
        'full_duration_completed':control.reason=='TIME_LIMIT' and elapsed>=a.duration-.15,
        'target_kind':'face','identity_matching_required':False,'state_counts':dict(counts),'control_modes':dict(modes),
        'distinct_ready_sources':len(seen),'source_age_ms_max':max(ages) if ages else None,'source_age_ms_p50':statistics.median(ages) if ages else None,
        'enter_margin':control.config.enter_margin,'exit_margin':control.config.exit_margin,'maximum_speed_us_s':max(speeds) if speeds else 0,
        'proposal_min_us':min(pulses) if pulses else None,'proposal_max_us':max(pulses) if pulses else None,
        'final_reason':control.reason,'final_command_us':control.pulse_us,'physical_actuation':False,'register_writes':0}
    sf=os.open(str(output)+'.summary.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(sf,'w') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return 1 if error else 0

if __name__=='__main__':raise SystemExit(main())
