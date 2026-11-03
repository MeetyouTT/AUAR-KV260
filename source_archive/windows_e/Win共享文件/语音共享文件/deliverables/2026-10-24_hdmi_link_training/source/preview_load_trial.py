"""A/main, B/vision, A/main real-preview workload; no model restart."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

BOOT='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
SOURCE=Path(__file__).resolve();TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-display-sequence-20261024/preview-trial')/TOKEN
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
STOP=False


def atomic(path,value):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');os.replace(temp,path)
def get(port,path):
    with OP.open('http://127.0.0.1:'+str(port)+path,timeout=3) as stream:return json.load(stream)
def ui():return get(8783,'/api/state')
def idle(value):
    assert value['phase']=='IDLE' and value['audio_output_state']=='IDLE_READY'
    assert not value.get('playing') and not value.get('paused') and value.get('pending_job') is None
    assert value.get('local_recording',{}).get('state')=='IDLE'
    assert not value.get('handsfree_dialogue',{}).get('microphone_open')
    assert not value.get('manual_pan',{}).get('automatic_following')
def set_page(page):
    req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(dict(type='ui_page',page=page)).encode(),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with OP.open(req,timeout=4) as stream:assert json.load(stream)['ok']
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        if ui()['ui_page']==page:return
        time.sleep(.1)
    raise RuntimeError('Page did not settle')
def prop(unit,key):
    return subprocess.check_output(['systemctl','show',unit,'-p',key,'--value'],text=True,timeout=4).strip()
def camera():
    raw=get(8790,'/health');s=raw['dpu_schedule'];face=raw['identity']['face_targets']
    return dict(pid=raw['pid'],mono_ns=time.monotonic_ns(),frames=raw['detected_frames'],
        native=s.get('native_critical'),fenced=s['owner_fenced'],worker_alive=face['worker_alive'],
        primary_overruns=s['primary_period_overruns'],gaps=face['freshness_metrics']['counters']['observed_gap_intervals'],
        optional={kind:dict(completed=job['native_completed'],overruns=job['overruns'],disabled=job['disabled'])
            for kind,job in s['optional'].items()})
def cpu():
    rows=Path('/proc/stat').read_text().splitlines();result={}
    for row in rows:
        fields=row.split()
        if fields and fields[0].startswith('cpu') and (fields[0]=='cpu' or fields[0][3:].isdigit()):
            values=[int(v) for v in fields[1:9]];result[fields[0]]=[sum(values),values[3]+values[4]]
    return result
def group(leader):
    rows={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            f=(p/'stat').read_text().rsplit(') ',1)[1].split()
            rows[int(p.name)]=(int(f[1]),int(f[11])+int(f[12]),int(f[19]))
        except (OSError,ValueError,IndexError):pass
    members={leader}
    while True:
        more=members|{pid for pid,row in rows.items() if row[0] in members}
        if more==members:return {pid:rows[pid][1:] for pid in members if pid in rows}
        members=more
def restore():
    if not (ROOT/'meta.json').exists():return
    meta=json.loads((ROOT/'meta.json').read_text())
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==meta['boot']==BOOT
    assert prop('aura-avatar-ui.service','MainPID')==meta['gui_pid']
    value=ui()
    if value['ui_page'] not in ('vision',meta['original_page']):
        atomic(ROOT/'restore.json',dict(restored=False,reason='USER_CHANGED_PAGE'));return
    idle(value)
    if value['ui_page']!=meta['original_page']:set_page(meta['original_page'])
    atomic(ROOT/'restore.json',dict(restored=True,page=ui()['ui_page'],mono_ns=time.monotonic_ns()))
def measure(label,page,seconds,meta):
    idle(ui());set_page(page);time.sleep(.5)
    first_ui=ui();before=camera();first_cpu=cpu();first_group=group(int(meta['gui_pid']))
    started=time.monotonic();samples=[]
    while time.monotonic()-started<seconds:
        if STOP:raise RuntimeError('STOP_REQUESTED')
        time.sleep(min(2,max(0,seconds-(time.monotonic()-started))))
        value=ui();idle(value);assert value['ui_page']==page
        state=camera();assert state['pid']==meta['camera_pid'] and state['native'] and not state['fenced'] and state['worker_alive']
        assert state['primary_overruns']==before['primary_overruns'] and state['gaps']==before['gaps']
        assert all(state['optional'][k]['overruns']==v['overruns'] for k,v in before['optional'].items()),'Native overrun observed; stop this load phase'
        samples.append(dict(elapsed=time.monotonic()-started,frames=state['frames'],
            preview_frames=value['ui_runtime']['preview_metrics']['displayed_frames']))
    elapsed=time.monotonic()-started;after=camera();last_cpu=cpu();last_group=group(int(meta['gui_pid']));last_ui=ui()
    assert first_group.keys()==last_group.keys() and all(first_group[p][1]==last_group[p][1] for p in first_group)
    cpu_percent={}
    for key,(total,idle_ticks) in first_cpu.items():
        delta=last_cpu[key][0]-total;free=last_cpu[key][1]-idle_ticks
        cpu_percent[key]=100*(delta-free)/delta
    gui_percent=100*sum(last_group[p][0]-first_group[p][0] for p in first_group)/os.sysconf('SC_CLK_TCK')/elapsed
    counter_seconds=(after['mono_ns']-before['mono_ns'])/1e9
    return dict(label=label,page=page,seconds=elapsed,camera_counter_seconds=counter_seconds,
        before=before,after=after,yolo_hz=(after['frames']-before['frames'])/counter_seconds,
        cpu_busy_percent=cpu_percent,gui_group_one_core_percent=gui_percent,gui_group_board_percent=gui_percent/os.cpu_count(),
        group_pids=sorted(first_group),preview_hz=(last_ui['ui_runtime']['preview_metrics']['displayed_frames']-first_ui['ui_runtime']['preview_metrics']['displayed_frames'])/elapsed,
        avatar_hz=(last_ui['avatar_display']['received']-first_ui['avatar_display']['received'])/elapsed,
        last_rolling_avatar_p95_ms=last_ui['avatar_display']['p95_ms'],samples=samples,
        inference_gain_claimed=False)
def work():
    global STOP
    def stop(*unused):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    meta=json.loads((ROOT/'meta.json').read_text());report=dict(scope='REAL_PREVIEW_A_B_A_WORKLOAD_NOT_CODE_OPTIMIZATION_BENCHMARK',
        phase='RUNNING',phases=[],models_created=0,service_restarts=0,display_mode_commands=0,
        microphone_commands=0,servo_commands=0,original_page=meta['original_page'])
    try:
        for label,page,seconds in [('A1',meta['original_page'],60),('B','vision',180),('A2',meta['original_page'],60)]:
            report['active_phase']=label;atomic(ROOT/'progress.json',report)
            report['phases'].append(measure(label,page,seconds,meta));atomic(ROOT/'progress.json',report)
        report['passed']=True
    except BaseException as exc:
        report.update(passed=False,failure_type=type(exc).__name__,failure=str(exc))
    finally:
        try:restore()
        except Exception as exc:report['restore_failure_type']=type(exc).__name__
        if (ROOT/'restore.json').exists():report['restoration']=json.loads((ROOT/'restore.json').read_text())
        report['phase']='COMPLETE';atomic(ROOT/'result.json',report);atomic(ROOT/'progress.json',report)
        if report.get('restoration',{}).get('restored'):
            subprocess.run(['systemctl','stop','aura-preview-restore-'+TOKEN+'.timer'],capture_output=True,timeout=4)
def main():
    import sys
    if sys.argv[1:]==['--restore']:restore();return
    if sys.argv[1:]==['--work']:work();return
    assert not sys.argv[1:] and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    value=ui();idle(value);assert value['ui_page']=='main'
    state=camera();assert state['pid']==1291 and state['native'] and not state['fenced']
    assert not any(j['disabled'] for j in state['optional'].values())
    assert prop('aura-avatar-ui.service','MainPID')=='1407' and prop('xserver-nodm.service','MainPID')=='1403'
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    atomic(ROOT/'meta.json',dict(boot=BOOT,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        camera_pid=state['pid'],gui_pid='1407',original_page=value['ui_page']))
    subprocess.run(['systemd-run','--quiet','--unit=aura-preview-restore-'+TOKEN,'--on-active=390s',
        '/usr/bin/python3','-B',str(SOURCE),'--restore'],check=True,capture_output=True,timeout=5)
    unit='aura-preview-aba-'+TOKEN
    subprocess.run(['systemd-run','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot',
        '--property=RuntimeMaxSec=360','--property=TimeoutStopSec=10',
        '/usr/bin/python3','-B',str(SOURCE),'--work'],check=True,capture_output=True,timeout=5)
    print(json.dumps(dict(unit=unit,root=str(ROOT),original_page=value['ui_page'],phase='LAUNCHED',duration_seconds=300)))
if __name__=='__main__':main()
