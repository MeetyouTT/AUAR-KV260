import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
recovery=Path('/home/root/aura-gui-cpu-20261023/recovery/17a9303670780152/report.json')
r=json.loads(recovery.read_text());assert r['complete'] and r['passed']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
gui=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
experiment=Path('/home/root/aura-gui-cpu-20261023/5a47edaf1f81bd7e')
comparison=json.loads((experiment/'stdout.json').read_text())
assert comparison['quality_passed'] and not comparison['cpu_gate_passed']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
unchanged={name:sha(gui/name) for name in comparison['baseline_pins']}
assert unchanged==comparison['baseline_pins']
assert sha('/etc/systemd/system/aura-camera-ui.service')==r['unit_sha256']
assert sha('/home/root/.local/share/aura/handsfree_dialogue.json')==r['preference_sha256']
assert sha('/home/root/.local/share/aura/identities.sqlite3')=='e0d2113eb51171079978b1e63eb4263d5fb13235fec1839f7be778dab1520aa1'
services={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
    raw=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts']).decode().strip()
    services[name]=dict(line.split('=',1) for line in raw.splitlines())
    assert services[name]['ActiveState']=='active'
assert services['aura-avatar-ui.service']['MainPID']=='450525'
assert services['xserver-nodm.service']['MainPID']=='1077'
pid=int(services['aura-camera-ui.service']['MainPID']);assert pid==r['after']['pid']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as response:return json.load(response)
def ticks():
    cpu=[int(n) for n in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    procs={}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            fields=(proc/'stat').read_text().rsplit(') ',1)[1].split()
            procs[int(proc.name)]=(int(fields[1]),int(fields[11])+int(fields[12]))
        except (OSError,IndexError,ValueError):pass
    return cpu,procs
def group(procs,leader):
    members={leader}
    while True:
        new={p for p,(parent,_) in procs.items() if parent in members}|members
        if new==members:return {p:procs[p][1] for p in members if p in procs}
        members=new
start=time.monotonic();a,pa=ticks();time.sleep(10);b,pb=ticks();duration=time.monotonic()-start
total=sum(b)-sum(a);idle=b[3]+b[4]-a[3]-a[4]
cpu={'scope':'10_SECOND_UNPAIRED_NORMAL_OPERATION_NOT_OPTIMIZATION_GAIN','duration_seconds':duration,
     'whole_board_busy_percent':100*(1-idle/total),'groups':{}}
for name in services:
    leader=int(services[name]['MainPID']);before=group(pa,leader);after=group(pb,leader)
    assert before.keys()==after.keys(),('CPU group membership changed',name)
    delta=sum(after.values())-sum(before.values())
    cpu['groups'][name]={'pids':sorted(after),'whole_board_percent':100*delta/total,
                        'one_core_percent':100*delta/os.sysconf('SC_CLK_TCK')/duration}
h=get(8790,'/health');u=get(8783,'/api/state');s=h['dpu_schedule'];f=h['identity']['face_targets']
assert h['pid']==pid and not s['owner_fenced'] and h['identity']['ready'] and f['worker_alive']
units=('aura-current-camera-recovery-17a9303670780152.service','aura-current-camera-restore-17a9303670780152.timer',
       'aura-gui-exact-5a47edaf1f81bd7e.service','aura-gui-exact-574e5989f5a99517.service',
       'aura-gui-profile-24983f6b6508cadb.service')
states={unit:subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value']).decode().strip() for unit in units}
assert all(state in ('inactive','failed') for state in states.values())
check=subprocess.run(['/usr/bin/python3','-B',str(gui.parent/'restore_previous.py'),'--check'],capture_output=True,text=True,timeout=12)
assert check.returncode==0,check.stderr[-300:]
print(json.dumps({'passed':True,'boot':r['before'].get('boot','7924ac9f-311d-4fcd-98be-57bf023cf1aa'),
    'services':services,'unit_sha256':r['unit_sha256'],'gui_runtime':str(gui),'gui_candidate_deployed':False,
    'unchanged_gui_files':unchanged,'candidate_library_sha256':sha(experiment/'libaura_pixels.so'),
    'comparison_report_sha256':sha(experiment/'stdout.json'),'recovery_report_sha256':sha(recovery),
    'recovery':r,'cpu':cpu,'unit_states':states,'rollback_check':json.loads(check.stdout),
    'current':{'detection_hz':h['detection_hz'],'optional':s['optional'],'recovery':s['yunet_recovery'],
        'identity_ready':h['identity']['ready'],'feature_inference':h['identity']['feature_inference'],
        'face_backend':f['backend'],'worker_alive':f['worker_alive'],'worker_faults':f['worker_faults'],
        'freshness_counters':f['freshness_metrics']['counters'],'primary_overruns':s['primary_period_overruns'],
        'owner_fenced':s['owner_fenced']},'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')}}))
