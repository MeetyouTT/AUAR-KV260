"""Try higher native handoff rates, restore the last accepted rate on failure."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import http.client,json,statistics,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);assert json.loads((stage/'deployment.json').read_text())['status']=='COMMITTED'
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def idle():
    s=state();assert s.get('phase')=='IDLE' and s.get('audio_output_state')=='IDLE_READY' and not s.get('error')
    assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue'].get('microphone_open')
    pan=s.get('manual_pan',{})
    assert pan.get('automatic_following') is False and pan.get('state') not in ('MOVING','STOPPING') and not pan.get('readback',{}).get('active')
    assert s['portrait_offload']['selected'] and s['portrait_offload']['mode']=='remote',s['portrait_offload']
    assert s['avatar_display'].get('age_ms',9999)<1000
    return s
def set_fps(fps):
    body=json.dumps({'type':'portrait_fps','fps':fps}).encode()
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=body,
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=5) as f:result=json.load(f)
    assert result['ok'],result
    identity=result['command_id'];deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        s=state();rows=s.get('avatar_renderer',{}).get('command_results',[])
        row=next((x for x in rows if x['command_id']==identity),None)
        if row:
            assert row['ok'] and s['portrait_offload']['target_fps']==fps,row
            return
        time.sleep(.1)
    raise TimeoutError('Frame-rate intent was not applied')
def measure(seconds):
    rows=[];began=time.monotonic()
    while time.monotonic()-began<seconds:
        s=idle();d=s['avatar_display'];rows.append({'at':time.monotonic(),'received':d['received'],'p95_ms':d['p95_ms'],
            'p99_ms':d['p99_ms'],'remote_age_ms':s['portrait_offload']['frame_age_ms']});time.sleep(1)
    return {'fps':(rows[-1]['received']-rows[0]['received'])/(rows[-1]['at']-rows[0]['at']),
        'p95_ms':statistics.median(x['p95_ms'] for x in rows),'p99_ms':statistics.median(x['p99_ms'] for x in rows),
        'max_remote_age_ms':max(x['remote_age_ms'] or 0 for x in rows),'rows':rows}
guard=r"""
import json,urllib.request
from pathlib import Path
stage=Path(STAGE)
if (stage/'fps_finished').exists():raise SystemExit(0)
request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=b'{"type":"portrait_fps","fps":12}',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
try:
    with urllib.request.urlopen(request,timeout=5) as f:result=f.read(8192)
    (stage/'fps_guard_restored.json').write_text(result.decode())
except Exception as exc:(stage/'fps_guard_failed.txt').write_text(repr(exc))
""".replace('STAGE',repr(str(stage)))
watchdog='aura-portrait-fps-'+stage.name[:10];(stage/'fps_guard.py').write_text(guard)
subprocess.run(['systemd-run','--unit='+watchdog,'--on-active=180','/usr/bin/python3','-B',str(stage/'fps_guard.py')],check=True,capture_output=True,timeout=15)
report={'status':'RUNNING','best_fps':12,'trials':[]};best=12
try:
    idle()
    for fps,warm in ((16,20),(24,15)):
        set_fps(fps);end=time.monotonic()+warm
        while time.monotonic()<end:idle();time.sleep(.5)
        sample=measure(35);gate={'min_fps':fps*.95,'max_p95_ms':1250/fps,'max_p99_ms':2000/fps}
        passed=sample['fps']>=gate['min_fps'] and sample['p95_ms']<=gate['max_p95_ms'] and sample['p99_ms']<=gate['max_p99_ms']
        report['trials'].append({'target':fps,'passed':passed,'sample':sample,'gate':gate})
        if not passed:set_fps(best);break
        best=fps;report['best_fps']=best;(stage/'fps_steps.json').write_text(json.dumps(report,indent=2))
    report.update(status='COMPLETE',best_fps=best,microphone=False,physical_audio=False,physical_motion=False)
except Exception as exc:
    report.update(status='RESTORED_LAST_ACCEPTED',best_fps=best,error=repr(exc));set_fps(best)
finally:
    (stage/'fps_steps.json').write_text(json.dumps(report,indent=2));(stage/'fps_finished').write_text(str(best))
    subprocess.run(['systemctl','stop',watchdog+'.timer',watchdog+'.service'],capture_output=True,timeout=15)
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c))
compile(script,'<portrait-fps-steps>','exec')
v=json.loads(ssh('python3 -B -',script,timeout=170));(HERE/'fps_steps.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps({**{k:x for k,x in v.items() if k!='trials'},'trials':[
    {**x,'sample':{k:z for k,z in x['sample'].items() if k!='rows'}} for x in v['trials']]}))
